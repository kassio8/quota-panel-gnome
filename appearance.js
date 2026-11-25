export const LOGO_STYLES = [
    {title: 'Colorida', file: 'quota-panel-color.svg', style: 'regular'},
    {title: 'Monocromática', file: 'quota-panel-symbolic.svg', style: 'symbolic'},
    {title: 'Terminal', file: 'quota-panel-terminal-symbolic.svg', style: 'symbolic'},
];

export function watchAppearance(settings, apply) {
    const update = () => apply({
        ...LOGO_STYLES[settings.get_int('logo-style')],
        size: settings.get_int('icon-size'),
    });
    update();
    const signals = ['icon-size', 'logo-style'].map(key =>
        settings.connect(`changed::${key}`, update));
    return () => signals.forEach(id => settings.disconnect(id));
}
