import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GdkPixbuf from 'gi://GdkPixbuf';

import {LOGO_STYLES, watchAppearance} from '../appearance.js';

let checks = 0;
function equal(actual, expected, message) {
    if (actual !== expected)
        throw new Error(`${message}: expected ${expected}, got ${actual}`);
    checks++;
}

if (GLib.getenv('GSETTINGS_BACKEND') !== 'memory')
    throw new Error('Run with GSETTINGS_BACKEND=memory to isolate user settings');

const directory = Gio.File.new_for_uri(import.meta.url).get_parent().get_parent();
const source = Gio.SettingsSchemaSource.new_from_directory(
    directory.get_child('schemas').get_path(), Gio.SettingsSchemaSource.get_default(), false);
const schema = source.lookup('org.gnome.shell.extensions.codex-quota', false);
const settings = new Gio.Settings({settings_schema: schema});

equal(settings.get_int('icon-size'), 16, 'default size');
equal(settings.get_int('logo-style'), 0, 'default color logo');
const sizeKey = schema.get_key('icon-size');
for (const [size, valid] of [[11, false], [12, true], [16, true], [24, true], [25, false]])
    equal(sizeKey.range_check(new GLib.Variant('i', size)), valid, `size ${size}`);
const styleKey = schema.get_key('logo-style');
equal(styleKey.range_check(new GLib.Variant('i', -1)), false, 'negative style rejected');
equal(styleKey.range_check(new GLib.Variant('i', LOGO_STYLES.length)), false,
    'unknown style rejected');

const updates = [];
const stop = watchAppearance(settings, appearance => updates.push(appearance));
equal(updates.length, 1, 'appearance applied on enable');
equal(updates[0].file, 'quota-panel-color.svg', 'initial logo');
equal(updates[0].size, 16, 'initial size');

settings.set_int('icon-size', 24);
equal(updates.length, 2, 'size change applies once');
equal(updates[1].size, 24, 'new size is applied');
for (let index = 0; index < LOGO_STYLES.length; index++) {
    settings.set_int('logo-style', index);
    const appearance = updates.at(-1);
    equal(appearance.file, LOGO_STYLES[index].file, `logo ${index} applied`);
    equal(appearance.style, index === 0 ? 'regular' : 'symbolic', `logo ${index} style`);
    const pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
        directory.get_child(appearance.file).get_path(), appearance.size, appearance.size, true);
    equal(pixbuf.width, 24, `logo ${index} decodes at configured size`);
}

const sibling = new Gio.Settings({settings_schema: schema});
equal(sibling.get_int('icon-size'), 24, 'settings shared with another consumer');
const beforeStop = updates.length;
stop();
settings.set_int('icon-size', 12);
settings.set_int('logo-style', 0);
equal(updates.length, beforeStop, 'disabled observer receives no changes');
settings.reset('icon-size');
settings.reset('logo-style');
equal(settings.get_int('icon-size'), 16, 'restore default size');
equal(settings.get_int('logo-style'), 0, 'restore default logo');

print(`appearance: ${checks} checks passed`);
