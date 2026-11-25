#!@GJS@ -m
// SPDX-License-Identifier: GPL-2.0-or-later
// Standalone process: never imports Shell UI and never reads account credentials.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import System from 'system';
import {normalizeRateLimits} from './quota.js';

const MAX_RESPONSE_BYTES = 1024 * 1024;
const directory = Gio.File.new_for_uri(import.meta.url).get_parent();
const cancellable = new Gio.Cancellable();
const loop = new GLib.MainLoop(null, false);
let exitCode = 0;
let timedOut = false;

function binaryPath() {
    const explicit = (ARGV[0] ?? '').trim();
    if (explicit)
        return GLib.path_is_absolute(explicit) && GLib.file_test(explicit, GLib.FileTest.IS_EXECUTABLE)
            ? explicit : null;
    const detected = GLib.find_program_in_path('codex');
    if (detected)
        return detected;
    // The graphical session may omit the current user's CLI installation directories.
    for (const relative of ['.local/bin/codex', '.npm-global/bin/codex']) {
        const path = GLib.build_filenamev([GLib.get_home_dir(), relative]);
        if (GLib.file_test(path, GLib.FileTest.IS_EXECUTABLE) &&
            GLib.file_test(path, GLib.FileTest.IS_REGULAR))
            return path;
    }
    // Preserve installations made before the configurable path was introduced.
    const saved = directory.get_child('codex-path.txt');
    if (saved.query_exists(null)) {
        const [, bytes] = saved.load_contents(null);
        const path = new TextDecoder().decode(bytes).trim();
        if (GLib.path_is_absolute(path) && GLib.file_test(path, GLib.FileTest.IS_EXECUTABLE))
            return path;
    }
    return null;
}

function asyncCall(object, method, finish, ...args) {
    return new Promise((resolve, reject) => {
        object[method](...args, (source, result) => {
            try {
                resolve(source[finish](result));
            } catch (error) {
                reject(error);
            }
        });
    });
}

async function readQuota(binary) {
    const launcher = new Gio.SubprocessLauncher({flags:
        Gio.SubprocessFlags.STDIN_PIPE | Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE});
    // npm installations may need the Node executable beside the selected Codex launcher.
    launcher.setenv('PATH', `${GLib.path_get_dirname(binary)}:${GLib.getenv('PATH') || '/usr/bin:/bin'}`, true);
    const process = launcher.spawnv([binary, 'app-server']);
    const input = process.get_stdout_pipe();
    const output = process.get_stdin_pipe();
    let pending = new Uint8Array();
    let received = 0;
    const decoder = new TextDecoder();
    const send = message => asyncCall(output, 'write_all_async', 'write_all_finish',
        new TextEncoder().encode(`${JSON.stringify(message)}\n`), GLib.PRIORITY_DEFAULT, cancellable);
    async function response(id) {
        while (true) {
            cancellable.set_error_if_cancelled();
            const index = pending.indexOf(10);
            if (index !== -1) {
                const line = decoder.decode(pending.slice(0, index));
                pending = pending.slice(index + 1);
                if (!line.trim())
                    continue;
                const message = JSON.parse(line);
                if (!message || message.id !== id)
                    continue;
                if (message.error)
                    throw new Error(message.error.message || 'RPC error');
                if (!Object.prototype.hasOwnProperty.call(message, 'result'))
                    throw new Error('Missing RPC result');
                return message.result;
            }
            const bytes = await asyncCall(input, 'read_bytes_async', 'read_bytes_finish',
                8192, GLib.PRIORITY_DEFAULT, cancellable);
            if (!bytes.get_size())
                throw new Error('Codex closed the connection');
            received += bytes.get_size();
            if (received > MAX_RESPONSE_BYTES)
                throw new Error('Codex response too large');
            const combined = new Uint8Array(pending.length + bytes.get_size());
            combined.set(pending);
            combined.set(bytes.toArray(), pending.length);
            pending = combined;
        }
    }
    try {
        await send({id: 1, method: 'initialize', params: {clientInfo: {
            name: 'codex_gnome_quota', title: 'Codex GNOME Quota', version: '0.2.0',
        }}});
        await response(1);
        await send({method: 'initialized', params: {}});
        await send({id: 2, method: 'account/rateLimits/read'});
        return normalizeRateLimits(await response(2), Math.floor(Date.now() / 1000));
    } finally {
        // Force termination also handles servers that ignore SIGTERM; always reap.
        process.force_exit();
        await asyncCall(process, 'wait_async', 'wait_finish', null);
        input.close(null);
        output.close(null);
    }
}

const timeout = Number(ARGV[1] ?? 15000);
const timeoutId = GLib.timeout_add(GLib.PRIORITY_DEFAULT,
    Number.isFinite(timeout) && timeout > 0 ? timeout : 15000, () => {
        timedOut = true;
        cancellable.cancel();
        return GLib.SOURCE_CONTINUE;
    });
let signalAdd;
try {
    signalAdd = imports.gi.GLibUnix.signal_add_full;
} catch {
    // GLibUnix was introduced after GNOME 42.
    signalAdd = GLib.unix_signal_add;
}
const signalId = signalAdd(GLib.PRIORITY_DEFAULT, 15, () => {
    cancellable.cancel();
    return GLib.SOURCE_CONTINUE;
});
(async () => {
    try {
        const binary = binaryPath();
        if (!binary)
            throw new Error('Codex CLI não encontrado; configure o caminho nas preferências');
        print(JSON.stringify(await readQuota(binary)));
    } catch (error) {
        exitCode = 1;
        const detail = String(error.message);
        const message = timedOut ? 'Tempo esgotado ao consultar o Codex'
            : /auth/i.test(detail) ? 'Entre na sua assinatura pelo Codex CLI'
                : detail.startsWith('Codex CLI') ? detail : 'Não foi possível ler a cota do Codex';
        print(JSON.stringify({status: 'error', message}));
    } finally {
        GLib.Source.remove(timeoutId);
        GLib.Source.remove(signalId);
        loop.quit();
    }
})();
// A missing binary finishes synchronously; avoid entering a loop after quit().
if (exitCode === 0)
    loop.run();
System.exit(exitCode);
