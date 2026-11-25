import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

import {watchRefreshInterval} from '../refresh.js';

if (GLib.getenv('GSETTINGS_BACKEND') !== 'memory')
    throw new Error('Run with GSETTINGS_BACKEND=memory to isolate user settings');

let checks = 0;
function equal(actual, expected, message) {
    if (actual !== expected)
        throw new Error(`${message}: expected ${expected}, got ${actual}`);
    checks++;
}
const directory = Gio.File.new_for_uri(import.meta.url).get_parent().get_parent();
const source = Gio.SettingsSchemaSource.new_from_directory(
    directory.get_child('schemas').get_path(), Gio.SettingsSchemaSource.get_default(), false);
const schema = source.lookup('org.gnome.shell.extensions.codex-quota', false);
const settings = new Gio.Settings({settings_schema: schema});
equal(settings.get_int('refresh-interval'), 60, 'default one-minute interval');
const key = schema.get_key('refresh-interval');
for (const [value, valid] of [[29, false], [30, true], [60, true], [900, true], [901, false]])
    equal(key.range_check(new GLib.Variant('i', value)), valid, `interval ${value}`);

// Control time deterministically; configuration changes use real Gio.Settings.
let nextId = 0;
const timers = new Map();
const clock = {
    PRIORITY_DEFAULT: GLib.PRIORITY_DEFAULT,
    SOURCE_CONTINUE: GLib.SOURCE_CONTINUE,
    timeout_add_seconds(_priority, seconds, callback) {
        const id = ++nextId;
        timers.set(id, {seconds, callback});
        return id;
    },
    Source: {
        remove(id) {
            equal(timers.delete(id), true, 'only remove an existing source');
        },
    },
};
let refreshes = 0;
const stop = watchRefreshInterval(settings, () => refreshes++, clock);
equal(timers.size, 1, 'one timer on activation');
equal([...timers.values()][0].seconds, 60, 'initial schedule');
equal([...timers.values()][0].callback(), GLib.SOURCE_CONTINUE, 'timer keeps recurring');
equal(refreshes, 1, 'timer triggers refresh');

settings.set_int('refresh-interval', 30);
equal(timers.size, 1, 'reschedule replaces old timer');
equal([...timers.values()][0].seconds, 30, 'shorter interval applies live');
settings.set_int('refresh-interval', 900);
equal(timers.size, 1, 'longer interval still has a single timer');
equal([...timers.values()][0].seconds, 900, 'longer interval applies live');
const scheduleCount = nextId;
settings.set_int('icon-size', 20);
equal(nextId, scheduleCount, 'appearance does not reset refresh timer');
equal(refreshes, 1, 'changing settings does not start extra requests');
settings.reset('refresh-interval');
equal([...timers.values()][0].seconds, 60, 'default can be restored');
stop();
equal(timers.size, 0, 'disable removes timer');
settings.set_int('refresh-interval', 30);
equal(timers.size, 0, 'disable disconnects settings observer');
settings.reset('refresh-interval');
settings.reset('icon-size');

print(`refresh: ${checks} checks passed`);
