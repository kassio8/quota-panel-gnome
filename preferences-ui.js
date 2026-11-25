// SPDX-License-Identifier: GPL-2.0-or-later
import Adw from 'gi://Adw?version=1';
import Gio from 'gi://Gio';
import Gtk from 'gi://Gtk?version=4.0';
import {LOGO_STYLES} from './appearance.js';

// ActionRow and SpinButton are available with libadwaita 1.1 / GNOME 42.
function spinRow({title, subtitle, ...properties}) {
    const row = new Adw.ActionRow({title, subtitle});
    row._spin = new Gtk.SpinButton({...properties, valign: Gtk.Align.CENTER});
    row.add_suffix(row._spin);
    row.activatable_widget = row._spin;
    return row;
}

export function fillPreferences(window, settings) {
    window.set_default_size(520, 520);
    window._settings = settings;
    const page = new Adw.PreferencesPage({
        title: 'Geral',
        icon_name: 'preferences-system-symbolic',
    });
    window.add(page);
    const group = new Adw.PreferencesGroup({
        title: 'Logo no painel',
        description: 'As alterações são salvas e aplicadas na hora.',
    });
    page.add(group);

    const logo = new Adw.ComboRow({
        title: 'Tipo de logo',
        subtitle: 'As opções monocromáticas acompanham o tema do painel.',
        model: Gtk.StringList.new(LOGO_STYLES.map(style => style.title)),
    });
    group.add(logo);
    settings.bind('logo-style', logo, 'selected', Gio.SettingsBindFlags.DEFAULT);

    const size = spinRow({
        title: 'Tamanho da logo',
        subtitle: 'De 12 a 24 pixels. O padrão é 16.',
        adjustment: new Gtk.Adjustment({
            lower: 12,
            upper: 24,
            step_increment: 1,
            page_increment: 2,
        }),
        digits: 0,
        numeric: true,
        snap_to_ticks: true,
    });
    group.add(size);
    settings.bind('icon-size', size._spin, 'value', Gio.SettingsBindFlags.DEFAULT);

    const reset = new Gtk.Button({
        label: 'Restaurar padrão',
        valign: Gtk.Align.CENTER,
    });
    reset.connect('clicked', () => {
        settings.reset('icon-size');
        settings.reset('logo-style');
    });
    const resetRow = new Adw.ActionRow({
        title: 'Valores padrão',
        subtitle: 'Logo colorida, 16 pixels.',
        activatable_widget: reset,
    });
    resetRow.add_suffix(reset);
    group.add(resetRow);

    const updates = new Adw.PreferencesGroup({
        title: 'Atualização automática',
        description: 'Intervalos menores fazem mais consultas e iniciam mais processos curtos.',
    });
    page.add(updates);
    const interval = spinRow({
        title: 'Intervalo entre consultas',
        subtitle: 'Em segundos, de 30 a 900. Padrão: 60 (1 minuto).',
        adjustment: new Gtk.Adjustment({
            lower: 30,
            upper: 900,
            step_increment: 30,
            page_increment: 60,
        }),
        digits: 0,
        numeric: true,
    });
    updates.add(interval);
    settings.bind('refresh-interval', interval._spin, 'value', Gio.SettingsBindFlags.DEFAULT);

    const connection = new Adw.PreferencesGroup({title: 'Codex CLI'});
    const pathRow = new Adw.ActionRow({
        title: 'Caminho do executável',
        subtitle: 'Instale o Codex CLI e faça login. Vazio usa a detecção automática.',
    });
    const path = new Gtk.Entry({
        valign: Gtk.Align.CENTER,
        placeholder_text: '/caminho/para/codex',
        hexpand: true,
    });
    pathRow.add_suffix(path);
    pathRow.activatable_widget = path;
    settings.bind('codex-path', path, 'text', Gio.SettingsBindFlags.DEFAULT);
    connection.add(pathRow);
    page.add(connection);

    const about = new Adw.PreferencesGroup({title: 'Sobre'});
    about.add(new Adw.ActionRow({
        title: 'Criador',
        subtitle: 'kassio8',
    }));
    page.add(about);
}
