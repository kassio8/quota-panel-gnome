import {normalizeRateLimits} from '../quota.js';

let checks = 0;
function equal(actual, expected, name) {
    if (JSON.stringify(actual) !== JSON.stringify(expected))
        throw new Error(`${name}: ${JSON.stringify(actual)}`);
    checks++;
}
for (const invalid of [null, [], true, 'invalid']) {
    let rejected = false;
    try { normalizeRateLimits(invalid, 10); } catch { rejected = true; }
    equal(rejected, true, 'invalid payload rejected');
}
for (const value of [null, true, false, -1, 101, '42']) {
    const result = normalizeRateLimits({rateLimits: {primary: {
        usedPercent: value, windowDurationMins: true, resetsAt: false,
    }}}, 10);
    equal(result.status, 'unavailable', 'invalid percentage unavailable');
    equal(result.buckets[0].windows[0], {durationMinutes: null, usedPercent: null, resetsAt: null},
        'booleans and invalid numbers never become quota');
}
const result = normalizeRateLimits({ordinaryUsageAllowed: false, rateLimitsByLimitId: {
    other: {limitName: 'Outro modelo', primary: {usedPercent: 4, windowDurationMins: 60}},
    codex: {primary: {usedPercent: 0, windowDurationMins: 300, resetsAt: 123},
        secondary: {usedPercent: 45, windowDurationMins: 10080}},
}, rateLimits: {primary: {usedPercent: 99}}}, 10);
equal(result.buckets.map(bucket => bucket.id), ['codex', 'other'], 'all buckets, Codex first');
equal(result.buckets[0].windows.map(window => window.usedPercent), [0, 45], 'zero and weekly preserved');
equal(result.ordinaryUsageAllowed, false, 'ordinary usage flag preserved');
equal(result.checkedAt, 10, 'timestamp preserved');
equal(normalizeRateLimits({rateLimitsByLimitId: {}, rateLimits: {primary: {usedPercent: 99}}}, 10).buckets,
    [], 'empty multi view does not fall back to stale legacy data');
print(`quota: ${checks} checks passed`);
