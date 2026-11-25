export function durationLabel(minutes) {
    if (!Number.isInteger(minutes) || minutes <= 0)
        return 'janela sem duração';
    if (minutes % 1440 === 0)
        return `${minutes / 1440} d`;
    if (minutes % 60 === 0)
        return `${minutes / 60} h`;
    return `${minutes} min`;
}

export function resetLabel(timestamp) {
    if (!Number.isInteger(timestamp) || timestamp <= 0)
        return 'Renovação indisponível';
    const date = new Date(timestamp * 1000);
    if (Number.isNaN(date.getTime()))
        return 'Renovação indisponível';
    return `Renova em ${date.toLocaleString('pt-BR', {dateStyle: 'short', timeStyle: 'short'})}`;
}

export function windowLabel(window) {
    const duration = durationLabel(window.durationMinutes);
    const used = Number.isFinite(window.usedPercent)
        ? `${window.usedPercent}% usado`
        : 'uso indisponível';
    return `${duration} · ${used}`;
}

export function summaryLabel(quota) {
    if (quota.status !== 'ok')
        return '—';
    const buckets = quota.buckets ?? [];
    const bucket = buckets.find(entry => entry.id === 'codex') ?? buckets[0];
    const session = bucket?.windows?.find(entry => entry.durationMinutes === 300);
    if (!Number.isFinite(session?.usedPercent))
        return '—';
    return `${session.usedPercent}%`;
}
