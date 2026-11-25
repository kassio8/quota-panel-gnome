import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

import {resetLabel, summaryLabel, windowLabel} from './presentation.js';
import {watchAppearance} from './appearance.js';
import {watchRefreshInterval} from './refresh.js';

const PROCESS_TIMEOUT_SECONDS = 20;

export default class CodexQuotaExtension extends Extension {
    enable() {
        this._generation = (this._generation ?? 0) + 1;
        this._indicator = new PanelMenu.Button(0.0, this.metadata.name, false);
        const box = new St.BoxLayout({style_class: 'panel-status-menu-box'});
        this._icon = new St.Icon({
            style_class: 'system-status-icon',
            accessible_name: 'Quota Panel',
        });
        box.add_child(this._icon);
        this._settings = this.getSettings();
        this._stopAppearance = watchAppearance(this._settings, appearance => {
            this._icon.gicon = new Gio.FileIcon({file: this.dir.get_child(appearance.file)});
            this._icon.style = `icon-size: ${appearance.size}px; -st-icon-style: ${appearance.style};`;
        });
        this._label = new St.Label({
            text: '…',
            y_align: Clutter.ActorAlign.CENTER,
        });
        box.add_child(this._label);
        this._indicator.add_child(box);
        Main.panel.addToStatusArea(this.uuid, this._indicator);

        this._render({status: 'unavailable', message: 'Consultando cota…', buckets: []});
        this._refresh();
        this._stopRefresh = watchRefreshInterval(this._settings, () => this._refresh());
    }

    disable() {
        this._generation++;
        this._stopAppearance?.();
        this._stopAppearance = null;
        this._stopRefresh?.();
        this._stopRefresh = null;
        this._settings = null;
        if (this._watchdogId) {
            GLib.Source.remove(this._watchdogId);
            this._watchdogId = 0;
        }
        if (this._process) {
            this._process.send_signal(15);
            this._process = null;
        }
        this._indicator?.destroy();
        this._indicator = null;
        this._icon = null;
        this._label = null;
        this._busy = false;
    }

    async _refresh() {
        if (this._busy || !this._indicator)
            return;
        this._busy = true;
        const generation = this._generation;
        let timedOut = false;

        try {
            const process = Gio.Subprocess.new(
                ['gjs', '-m', GLib.build_filenamev([this.path, 'reader.js']),
                    this._settings.get_string('codex-path')],
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE
            );
            this._process = process;
            this._watchdogId = GLib.timeout_add_seconds(
                GLib.PRIORITY_DEFAULT, PROCESS_TIMEOUT_SECONDS, () => {
                    this._watchdogId = 0;
                    timedOut = true;
                    process.send_signal(15);
                    return GLib.SOURCE_REMOVE;
                }
            );

            const stdout = await new Promise((resolve, reject) => {
                process.communicate_utf8_async(null, null, (source, result) => {
                    try {
                        const [, output] = source.communicate_utf8_finish(result);
                        resolve(output);
                    } catch (error) {
                        reject(error);
                    }
                });
            });
            if (generation !== this._generation)
                return;
            if (timedOut)
                throw new Error('Tempo esgotado ao consultar o Codex');
            const quota = JSON.parse(stdout);
            if (!['ok', 'unavailable', 'error'].includes(quota.status))
                throw new Error('Resposta inválida do leitor');
            this._render(quota);
        } catch (error) {
            if (generation === this._generation) {
                const message = timedOut
                    ? 'Tempo esgotado ao consultar o Codex'
                    : 'Não foi possível consultar a cota';
                this._render({status: 'error', message, buckets: []});
                console.warn(`Quota Panel: ${error}`);
            }
        } finally {
            if (generation === this._generation) {
                if (this._watchdogId) {
                    GLib.Source.remove(this._watchdogId);
                    this._watchdogId = 0;
                }
                this._process = null;
                this._busy = false;
            }
        }
    }

    _addRow(text) {
        this._indicator.menu.addMenuItem(new PopupMenu.PopupMenuItem(text, {
            reactive: false,
            can_focus: false,
        }));
    }

    _render(quota) {
        if (!this._indicator)
            return;
        this._label.text = summaryLabel(quota);
        const menu = this._indicator.menu;
        menu.removeAll();

        if (quota.status === 'error') {
            this._addRow(quota.message ?? 'Cota indisponível');
        } else {
            if (quota.ordinaryUsageAllowed === false)
                this._addRow('Uso incluído indisponível nesta conta');
            if (quota.status === 'unavailable')
                this._addRow(quota.message ?? 'Cota indisponível');

            for (const bucket of quota.buckets ?? []) {
                if (!Array.isArray(bucket.windows) || !bucket.windows.length)
                    continue;
                menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem(bucket.name));
                for (const window of bucket.windows) {
                    this._addRow(windowLabel(window));
                    this._addRow(resetLabel(window.resetsAt));
                }
            }
            if (Number.isInteger(quota.checkedAt)) {
                const time = new Date(quota.checkedAt * 1000)
                    .toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'});
                menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
                this._addRow(`Atualizado às ${time}`);
            }
        }

        menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        menu.addAction('Atualizar agora', () => this._refresh());
        menu.addAction('Configurações…', () => this.openPreferences());
    }
}
