import GLib from 'gi://GLib';

export function watchRefreshInterval(settings, refresh, clock = GLib) {
    let timerId = 0;
    const reschedule = () => {
        if (timerId)
            clock.Source.remove(timerId);
        timerId = clock.timeout_add_seconds(
            clock.PRIORITY_DEFAULT, settings.get_int('refresh-interval'), () => {
                refresh();
                return clock.SOURCE_CONTINUE;
            });
    };
    reschedule();
    const signalId = settings.connect('changed::refresh-interval', reschedule);
    return () => {
        settings.disconnect(signalId);
        if (timerId) {
            clock.Source.remove(timerId);
            timerId = 0;
        }
    };
}
