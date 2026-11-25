// Exercise the real async controller; Shell UI, process and clock are simulated.
// This cannot validate GNOME APIs or replace an actual desktop session.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');

function controller() {
    const processes = [];
    const timers = new Map();
    const rendered = [];
    let nextId = 0;
    const GLib = {
        PRIORITY_DEFAULT: 0, SOURCE_REMOVE: false,
        build_filenamev: parts => parts.join('/'),
        timeout_add_seconds(_priority, _seconds, callback) {
            timers.set(++nextId, callback);
            return nextId;
        },
        Source: {remove: id => assert.equal(timers.delete(id), true)},
    };
    const Gio = {
        SubprocessFlags: {STDOUT_PIPE: 1, STDERR_PIPE: 2},
        Subprocess: {new(argv) {
            assert.deepEqual(Array.from(argv), ['gjs', '-m', '/extension/reader.js', '/bin/codex with spaces']);
            const process = {
                signals: [],
                send_signal(signal) { this.signals.push(signal); },
                communicate_utf8_async(_input, _cancel, callback) { this.callback = callback; },
                communicate_utf8_finish(result) {
                    if (result instanceof Error)
                        throw result;
                    return [true, result, ''];
                },
                finish(result) { this.callback(this, result); },
            };
            processes.push(process);
            return process;
        }},
    };
    // Keep production methods unchanged; replace only imports unavailable outside Shell.
    const source = fs.readFileSync(path.join(__dirname, '../extension.js'), 'utf8')
        .replace(/^import .*;\n/gm, '')
        .replace('export default class', 'class');
    const Extension = vm.runInNewContext(`${source}\nCodexQuotaExtension;`, {
        Extension: class {}, Gio, GLib, console: {warn() {}},
    });
    const extension = new Extension();
    Object.assign(extension, {
        path: '/extension', _generation: 1,
        _settings: {get_string: () => '/bin/codex with spaces'},
        _indicator: {destroy() { this.destroyed = true; }},
        _render: quota => rendered.push(quota),
    });
    return {extension, processes, timers, rendered};
}

test('concurrent refreshes start only one process; completion permits another', async () => {
    const {extension, processes, timers, rendered} = controller();
    const first = extension._refresh();
    const duplicate = extension._refresh();
    assert.equal(processes.length, 1);
    await duplicate;
    processes[0].finish('{"status":"ok","buckets":[]}');
    await first;
    assert.equal(rendered[0].status, 'ok');
    assert.equal(timers.size, 0);
    const second = extension._refresh();
    assert.equal(processes.length, 2);
    processes[1].finish('{"status":"unavailable"}');
    await second;
    assert.equal(rendered[1].status, 'unavailable');
});

test('disable removes resources and stale completion cannot overwrite a new query', async () => {
    const {extension, processes, timers, rendered} = controller();
    const oldIndicator = extension._indicator;
    let stopped = 0;
    extension._stopAppearance = () => stopped++;
    extension._stopRefresh = () => stopped++;
    const old = extension._refresh();
    extension.disable();
    assert.equal(stopped, 2);
    assert.equal(oldIndicator.destroyed, true);
    assert.deepEqual(processes[0].signals, [15]);
    assert.equal(timers.size, 0);
    await extension._refresh();
    assert.equal(processes.length, 1);
    // Restore the external state that enable() establishes, without simulating widgets.
    extension._generation++;
    extension._indicator = {destroy() {}};
    extension._settings = {get_string: () => '/bin/codex with spaces'};
    const current = extension._refresh();
    processes[0].finish('{"status":"ok","checkedAt":1}');
    await old;
    assert.equal(rendered.length, 0);
    assert.equal(extension._busy, true);
    assert.equal(timers.size, 1);
    processes[1].finish('{"status":"ok","checkedAt":2}');
    await current;
    assert.equal(rendered[0].checkedAt, 2);
    assert.equal(timers.size, 0);
});

test('watchdog rejects late success and allows retry after process completion', async () => {
    const {extension, processes, timers, rendered} = controller();
    const pending = extension._refresh();
    const [id, callback] = [...timers][0];
    assert.equal(callback(), false);
    timers.delete(id); // Main loop removes SOURCE_REMOVE after the callback.
    assert.deepEqual(processes[0].signals, [15]);
    processes[0].finish('{"status":"ok"}');
    await pending;
    assert.equal(rendered[0].status, 'error');
    assert.match(rendered[0].message, /Tempo esgotado/);
    assert.equal(extension._busy, false);
    assert.equal(extension._process, null);
    const retry = extension._refresh();
    assert.equal(processes.length, 2);
    processes[1].finish('{"status":"ok"}');
    await retry;
    assert.equal(rendered[1].status, 'ok');
});

test('malformed output, unknown status and IO errors clear old data and release busy state', async () => {
    for (const response of ['invalid', '{"status":"unknown"}', new Error('IO failed')]) {
        const {extension, processes, timers, rendered} = controller();
        const pending = extension._refresh();
        processes[0].finish(response);
        await pending;
        assert.equal(rendered[0].status, 'error');
        assert.equal(rendered[0].buckets.length, 0);
        assert.equal(extension._busy, false);
        assert.equal(timers.size, 0);
    }
});
