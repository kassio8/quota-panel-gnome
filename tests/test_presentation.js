import {durationLabel, resetLabel, summaryLabel, windowLabel} from '../presentation.js';

function equal(actual, expected, name) {
    if (actual !== expected)
        throw new Error(`${name}: expected ${expected}, got ${actual}`);
}

equal(durationLabel(300), '5 h', 'five hour duration');
equal(durationLabel(10080), '7 d', 'weekly duration');
equal(durationLabel(null), 'janela sem duração', 'missing duration');
equal(windowLabel({durationMinutes: 300, usedPercent: null}),
    '5 h · uso indisponível', 'missing percentage');
equal(windowLabel({durationMinutes: 60, usedPercent: 72}),
    '1 h · 72% usado', 'available percentage');
equal(resetLabel(null), 'Renovação indisponível', 'missing reset');
equal(summaryLabel({status: 'error'}), '—', 'error summary');
equal(summaryLabel({status: 'ok', buckets: [{
    id: 'codex', name: 'Codex', windows: [
        {durationMinutes: 300, usedPercent: 32},
        {durationMinutes: 1440, usedPercent: 45},
        {durationMinutes: 10080, usedPercent: 71},
    ],
}]}), '32%', 'five-hour Codex window');
equal(summaryLabel({status: 'ok', buckets: [{
    id: 'codex', name: 'Codex', windows: [
        {durationMinutes: 60, usedPercent: 32},
        {durationMinutes: 10080, usedPercent: 71},
    ],
}]}), '—', 'no five-hour window');

equal(summaryLabel({status: 'ok', buckets: [{
    id: 'codex', name: 'Codex', windows: [
        {durationMinutes: 10080, usedPercent: 16},
        {durationMinutes: 300, usedPercent: 4},
    ],
}]}), '4%', 'screenshot: five-hour usage, no Codex text');
equal(summaryLabel({status: 'ok', buckets: [{
    id: 'codex', name: 'Codex', windows: [
        {durationMinutes: 300, usedPercent: null},
        {durationMinutes: 10080, usedPercent: 16},
    ],
}]}), '—', 'missing session usage never falls back to weekly usage');
equal(summaryLabel({status: 'ok', buckets: [{
    id: 'codex', name: 'Codex', windows: [{durationMinutes: 300, usedPercent: 0}],
}]}), '0%', 'zero session usage is available');

print('presentation: 12 checks passed');
