// SPDX-License-Identifier: GPL-2.0-or-later
const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const positiveInteger = value => Number.isInteger(value) && value > 0 ? value : null;

export function normalizeRateLimits(result, checkedAt) {
    if (!isObject(result))
        throw new Error('Invalid rate limit response');
    const snapshots = isObject(result.rateLimitsByLimitId)
        ? Object.entries(result.rateLimitsByLimitId)
        : isObject(result.rateLimits)
            ? [[result.rateLimits.limitId || 'codex', result.rateLimits]] : [];
    const buckets = [];
    for (const [id, snapshot] of snapshots) {
        if (!isObject(snapshot))
            continue;
        const windows = ['primary', 'secondary'].map(slot => snapshot[slot])
            .filter(isObject).map(window => ({
                durationMinutes: positiveInteger(window.windowDurationMins),
                usedPercent: Number.isFinite(window.usedPercent) &&
                    window.usedPercent >= 0 && window.usedPercent <= 100 ? window.usedPercent : null,
                resetsAt: positiveInteger(window.resetsAt),
            }));
        if (!windows.length)
            continue;
        windows.sort((a, b) => (a.durationMinutes ?? Infinity) - (b.durationMinutes ?? Infinity));
        const name = typeof snapshot.limitName === 'string' && snapshot.limitName.trim()
            ? snapshot.limitName : id === 'codex' ? 'Codex' : String(id);
        buckets.push({id: String(id), name, windows});
    }
    buckets.sort((a, b) => Number(a.id !== 'codex') - Number(b.id !== 'codex') ||
        a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
    const quota = {
        status: buckets.some(bucket => bucket.windows.some(window => window.usedPercent !== null))
            ? 'ok' : 'unavailable',
        checkedAt,
        ordinaryUsageAllowed: typeof result.ordinaryUsageAllowed === 'boolean' ? result.ordinaryUsageAllowed : null,
        buckets,
    };
    if (quota.status === 'unavailable')
        quota.message = 'O Codex não informou percentuais de cota';
    return quota;
}
