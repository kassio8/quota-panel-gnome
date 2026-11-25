import Adw from 'gi://Adw?version=1';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GIRepository from 'gi://GIRepository?version=2.0';
import Gtk from 'gi://Gtk?version=4.0';

import {LOGO_STYLES} from '../appearance.js';

if (GLib.getenv('GSETTINGS_BACKEND') !== 'memory')
    throw new Error('Run with GSETTINGS_BACKEND=memory to isolate user settings');

// Load the same GNOME 46 base class used by the preferences service,
// without starting that service or connecting to the user's desktop.
GIRepository.Repository.prepend_search_path('/usr/lib/gnome-shell/girepository-1.0');
GIRepository.Repository.prepend_library_path('/usr/lib/gnome-shell');
for (const resource of ['org.gnome.Shell.Extensions.src.gresource',
    'gnome-shell-dbus-interfaces.gresource'])
    Gio.resources_register(Gio.Resource.load(`/usr/share/gnome-shell/${resource}`));

const {default: Preferences} = await import('../prefs.js');
const directory = Gio.File.new_for_uri(import.meta.url).get_parent().get_parent();
const [, bytes] = directory.get_child('metadata.json').load_contents(null);
const preferences = new Preferences({
    ...JSON.parse(new TextDecoder().decode(bytes)),
    dir: directory,
    path: directory.get_path(),
});
const settings = preferences.getSettings();
let checks = 0;
function equal(actual, expected, message) {
    if (actual !== expected)
        throw new Error(`${message}: expected ${expected}, got ${actual}`);
    checks++;
}

// Check the native widget APIs, and exercise both numeric GSettings mappings
// with GTK models that work without a display server.
equal(Gtk.SpinButton.list_properties().some(property => property.name === 'value'), true,
    'GTK supports legacy-compatible SpinButton value');
equal(Adw.ComboRow.list_properties().some(property => property.name === 'selected'), true,
    'installed Adwaita supports ComboRow selected');
const adjustment = new Gtk.Adjustment({lower: 12, upper: 24, step_increment: 1});
settings.bind('icon-size', adjustment, 'value', Gio.SettingsBindFlags.DEFAULT);
equal(adjustment.value, 16, 'size default loads into GTK');
adjustment.value = 24;
equal(settings.get_int('icon-size'), 24, 'GTK size writes GSettings');
settings.set_int('icon-size', 12);
equal(adjustment.value, 12, 'GSettings size updates GTK');

const selection = new Gtk.SingleSelection({
    model: Gtk.StringList.new(LOGO_STYLES.map(style => style.title)),
});
settings.bind('logo-style', selection, 'selected', Gio.SettingsBindFlags.DEFAULT);
equal(selection.selected, 0, 'logo default loads into GTK');
selection.selected = 2;
equal(settings.get_int('logo-style'), 2, 'GTK logo writes GSettings');
settings.set_int('logo-style', 1);
equal(selection.selected, 1, 'GSettings logo updates GTK');
settings.reset('icon-size');
settings.reset('logo-style');
equal(adjustment.value, 16, 'reset size updates GTK');
equal(selection.selected, 0, 'reset logo updates GTK');
Gio.Settings.unbind(adjustment, 'value');
Gio.Settings.unbind(selection, 'selected');

const interval = new Gtk.Adjustment({lower: 30, upper: 900, step_increment: 30});
settings.bind('refresh-interval', interval, 'value', Gio.SettingsBindFlags.DEFAULT);
equal(interval.value, 60, 'refresh default loads into GTK');
interval.value = 30;
equal(settings.get_int('refresh-interval'), 30, 'GTK refresh interval writes GSettings');
settings.set_int('refresh-interval', 900);
equal(interval.value, 900, 'GSettings refresh interval updates GTK');
settings.reset('refresh-interval');
equal(interval.value, 60, 'refresh interval default can be restored');
Gio.Settings.unbind(interval, 'value');

const path = new Gtk.EntryBuffer();
settings.bind('codex-path', path, 'text', Gio.SettingsBindFlags.DEFAULT);
equal(path.text, '', 'automatic Codex path by default');
path.text = '/tmp/codex with spaces';
equal(settings.get_string('codex-path'), path.text, 'custom executable path persists');
settings.reset('codex-path');
equal(path.text, '', 'reset restores automatic discovery');
Gio.Settings.unbind(path, 'text');

print(`preferences: ${checks} native API/binding checks passed; window not rendered`);
