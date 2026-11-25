// SPDX-License-Identifier: GPL-2.0-or-later
import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';
import {fillPreferences} from './preferences-ui.js';

export default class CodexQuotaPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        fillPreferences(window, this.getSettings());
    }
}
