// stage 20: symbiosis. One body, two components. The Olvasó reads the body from inside; the Processor reads the world and nothing of itself.
// The body has two needs that take turns (charge = food, contact = warmth); each resource is only there while its cue is lit.
// modes: 'processor'  the Processor alone: sees the cues, chooses what to fetch
//        'olvaso'     the Olvasó alone: sees the same cues (as outside channels) and fetches with its own colour acts
//        'pair'       the Processor sees the cues and the Olvasó's latest colour; the Olvasó only marks
//        'scrambled'  as pair, but the colour the Processor sees is random (control)
//        'oracle'     the Processor is told which need is draining (upper bound)
//        'reading'    the Processor sees which pattern the Olvasó reads itself as (its self-interpretation)
//        'feeling'    the Processor sees the raw felt channels instead (uninterpreted inside)
//        'readingScrambled' as reading, but a random pattern (control)
const { Entity, OL, ORng, bodyLook } = require('./engine.js');
const mean = (a) => a.length ? a.reduce((p, q) => p + q, 0) / a.length : NaN;
const SET = OL.SET;
function run({ seed = 1, T = 30000, mode = 'pair', drain = 0.004, gain = 0.12, every = 5, eps = 0.05, ambiguous = false } = {}) {
  Object.assign(OL, { RECALL: false, CONTAGION: 0, REACH: false, GAMMA: 0.8, COMPANY: 1, READ_CONTAGION: 0, VOICES: false, SALIENCE: 0, HEAR: 3, FEEL: 6, NX: 18, NY: 8, NWORDS: 4, MAXC: 60 });
  const e = new Entity(seed * 100 + 7), R = new ORng(seed * 7 + 1);
  // ambiguous body: low charge and low contact feel exactly alike from inside (the felt channels see only their sum);
  // which one is draining is set by the season, which shows outside (one more outside channel the Olvasó sees)
  if (ambiguous) e.A = e.A.map(row => { const v = (row[0] + row[2]) / 2; return [v, row[1], v, row[3]]; });
  let season = 0;
  let need = 0, cue = [true, false], lastColour = 6; // 0..5 = hue index, 6 = none lately
  let colourAge = 99;
  const Q = new Map(), N = new Map(); // the Processor: a contextual bandit (context -> value of fetch nothing / A / B)
  const qget = (c) => { if (!Q.has(c)) { Q.set(c, [0, 0, 0]); N.set(c, [0, 0, 0]); } return Q.get(c); };
  let pending = null; const dist = [], late = [], byNeed = [[0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0]], fetches = { right: 0, wrong: 0, empty: 0 };
  const distress = () => e.distress();
  for (let t = 0; t < T; t++) {
    if (R.next() < 1 / 300) { need = 1 - need; season = need; }    // what matters changes (and with it the season)
    for (let k = 0; k < 2; k++) if (R.next() < 1 / 60) cue[k] = R.next() < 0.5; // resources come and go
    if (need === 0) e.h[0] = Math.max(0, e.h[0] - drain); else e.h[2] = Math.max(0, e.h[2] - drain);
    const sense = { typing: 0, vowels: 0.4, speed: ambiguous ? (season ? 0.9 : 0.1) : 0.1, px: cue[0] ? 0.9 : 0.1, py: cue[1] ? 0.9 : 0.1, presence: 0.42, seen: null, noBody: false };
    e.updateGate(1);
    const r = e.tick(sense, null, null, [], []);
    const colour = r.act >= 1 && r.act <= 6 ? r.act - 1 : null;
    if (colour !== null) { lastColour = colour; colourAge = 0; } else if (++colourAge > 10) lastColour = 6;
    if (t > T / 2 && colour !== null) byNeed[need][colour]++;
    // fetching
    let fetch = 0; // 0 nothing, 1 food (A), 2 warmth (B)
    if (mode === 'olvaso') { if (colour !== null) fetch = colour < 3 ? 1 : 2; }
    else if (t % every === 0) {
      if (pending) { const rw = pending.d0 - distress(); const q = Q.get(pending.c), n = N.get(pending.c); n[pending.a]++; q[pending.a] += (rw - q[pending.a]) / Math.min(n[pending.a], 50); pending = null; }
      const seenColour = mode === 'pair' ? lastColour : mode === 'scrambled' ? Math.floor(R.next() * 7) : mode === 'oracle' ? need
        : mode === 'reading' ? e.reading                                   // the Olvasó's own reading: which pattern it reads itself as now
        : mode === 'feeling' ? r.y.slice(0, 6).map(v => (v > 0 ? 1 : 0)).join('') // the raw felt channels, uninterpreted (sign of each)
        : mode === 'processorSeason' ? season    // the Processor sees the season itself (relay check)
        : mode === 'readingScrambled' ? Math.floor(R.next() * Math.max(1, e.mu.length)) : 0;
      const c = `${cue[0] ? 1 : 0}${cue[1] ? 1 : 0}|${mode === 'processor' ? '-' : seenColour}`;
      const q = qget(c); let a = 0; if (R.next() < eps) a = Math.floor(R.next() * 3); else { for (let k = 1; k < 3; k++) if (q[k] > q[a]) a = k; }
      fetch = a; pending = { c, a, d0: distress() };
    }
    if (fetch) {
      const k = fetch - 1;
      if (!cue[k]) fetches.empty++;
      else { if (k === 0) e.h[0] = Math.min(1, e.h[0] + gain); else e.h[2] = Math.min(1, e.h[2] + gain); if (k === need) fetches.right++; else fetches.wrong++; }
    }
    if (t > T / 2) late.push(distress());
  }
  // how much the Olvasó's colours say about which need is draining (0 = nothing, 1 = everything): mutual information / entropy of need
  const tot = byNeed.flat().reduce((a, b) => a + b, 0); let mi = 0;
  if (tot > 50) { const pn = byNeed.map(r => r.reduce((a, b) => a + b, 0) / tot); for (let c = 0; c < 7; c++) { const pc = (byNeed[0][c] + byNeed[1][c]) / tot; for (let n = 0; n < 2; n++) { const p = byNeed[n][c] / tot; if (p > 0) mi += p * Math.log(p / (pn[n] * pc)); } } const hn = -pn.reduce((a, p) => a + (p > 0 ? p * Math.log(p) : 0), 0); mi = hn > 0 ? mi / hn : 0; } else mi = NaN;
  run.Q = Q; run.N = N;
  return { distress: mean(late), danger: mean(late.map(d => d > 0.35 ? 1 : 0)), colourSaysNeed: mi, marks: tot / (T / 2), right: fetches.right, wrong: fetches.wrong, empty: fetches.empty };
}
module.exports = { run, mean };
if (require.main === module) {
  const [name, o] = JSON.parse(process.argv[2]); const S0 = +(process.env.S0 || 1), S1 = +(process.env.S1 || 12); const R = [];
  for (let seed = S0; seed <= S1; seed++) R.push(run({ seed, ...o }));
  const out = { name, runs: R.length }; Object.keys(R[0]).forEach(k => (out[k] = mean(R.map(r => r[k]).filter(v => !isNaN(v)))));
  console.log(JSON.stringify(out, (q, v) => typeof v === 'number' ? Math.round(v * 10000) / 10000 : v));
  require('fs').writeFileSync((process.env.TAG || 't20_') + name.replace(/\W+/g, '_') + '.json', JSON.stringify({ summary: out, runs: R }));
}
