// stage 16: richer lives. Plain against rich, the same questions as stages 8, 10-11 and 14.
const { Entity, OL, ORng, bodyLook } = require('./engine.js');
const { setup, privateEvent, visitorWord } = require('./rich16.js');
const cor = (a, b) => { const ma = mean(a), mb = mean(b); let s = 0, x = 0, y = 0; for (let i = 0; i < a.length; i++) { s += (a[i] - ma) * (b[i] - mb); x += (a[i] - ma) ** 2; y += (b[i] - mb) ** 2; } return s / Math.sqrt(x * y + 1e-12); };
const mean = (a) => a.length ? a.reduce((p, q) => p + q, 0) / a.length : NaN;
// share of the variance of the hidden state that goes with which word was said (0 = none, 1 = all), averaged over the four
function eta(rows) {
  const by = {}; rows.forEach(([w, h]) => (by[w] = by[w] || []).push(h)); const groups = Object.values(by).filter(g => g.length >= 5); if (groups.length < 2) return NaN;
  const all = groups.flat(); let s = 0;
  for (let i = 0; i < 4; i++) { const m = mean(all.map(h => h[i])); const tot = mean(all.map(h => (h[i] - m) ** 2)); const bet = groups.reduce((a, g) => a + g.length * (mean(g.map(h => h[i])) - m) ** 2, 0) / all.length; s += tot > 1e-9 ? bet / tot : 0; }
  return s / 4;
}
function run({ N = 4, seed = 1, T = 40000, rich = false, sham = false, dim = 0, maxc = 60, hear = 3, feel = 6 } = {}) {
  setup(rich, hear, feel); OL.MAXC = maxc; OL.RECALL = true; OL.CONTAGION = 0.05; OL.REACH = true; OL.GAMMA = 0.8; OL.COMPANY = 1; OL.COMPANY_CONTACT = false; OL.READ_CONTAGION = 0;
  const es = Array.from({ length: N }, (_, i) => new Entity(seed * 100 + i)); es.forEach(e => (e.speechLog = []));
  const R = new ORng(seed); let pres = 0, focus = 0, prevC = es.map(() => null), prevW = es.map(() => null);
  const avgLook = es.map(() => [0.5, 0.5, 0.5, 0.5]);
  const said = es.map(() => []), care = [], heard = [], asks = [], reachedTimes = es.map(() => []), readSp = [], readBy = [], readC = [];
  for (let t = 0; t < T; t++) {
    const ph = t % 600, active = ph < 420; pres = active ? Math.min(.8, pres + .05) : pres * .985;
    es.forEach((e, i) => { const L = bodyLook(e.h); avgLook[i] = avgLook[i].map((v, k) => v + 0.01 * (L[k] - v)); });
    let word = null, col = null;
    if (active && R.next() < 0.03) { const tg = Math.floor(R.next() * N); word = visitorWord(bodyLook(es[tg].h), avgLook[tg], R, rich); if (word) focus = tg; }
    if (active && R.next() < 0.01) col = Math.floor(R.next() * 6);
    const signers = []; for (let j = 0; j < N; j++) if (prevW[j] || prevC[j] !== null) signers.push(j);
    if (signers.length) focus = signers[Math.floor(R.next() * signers.length)];
    const looks = es.map(e => bodyLook(e.h));
    const lookAt = es.map((_, i) => { if (N === 2) return 1 - i; if (focus !== i && R.next() >= 0.6) return focus; let j = Math.floor(R.next() * (N - 1)); return j >= i ? j + 1 : j; });
    const late = t > T / 2;
    // reading the speaker (stage 8): a word just heard from j; what does it lead i to expect to see, compared with how j and a bystander look?
    if (late && N >= 3) for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) if (j !== i && prevW[j] && R.next() < 0.2) {
      const ex = es[i].expectSeen(prevW[j]); if (!ex) continue; let k = Math.floor(R.next() * N); while (k === i || k === j) k = (k + 1) % N;
      const err = (L) => ex.reduce((a, v, q) => a + Math.abs(v - L[q]), 0) / 4; readSp.push(err(looks[j])); readBy.push(err(looks[k])); readC.push([ex, looks[j], looks[k]]);
    }
    const cs = [], ws = [];
    es.forEach((e, i) => {
      privateEvent(e, R, rich);
      const ic = [], iw = []; for (let j = 0; j < N; j++) if (j !== i) { if (prevC[j] !== null) ic.push(prevC[j]); if (prevW[j]) iw.push(prevW[j]); }
      const w = lookAt[i], seen = looks[w].map(v => dim ? 0.5 + (1 - dim) * (v - 0.5) : v);
      const held = (e.companyT || 0) > 0 || (es[w].companyT || 0) > 0, watchedSpoke = !!prevW[w];
      e.updateGate(1); const r = e.tick({ typing: word ? .4 : 0, vowels: .4, speed: .1, px: .5, py: .5, presence: pres, seen }, col, word, ic, iw);
      const reach = r.act === 11;
      if (reach) reachedTimes[w].push(t);
      if (reach && !sham) es[w].company();
      if (late) {
        if (r.said) said[i].push([r.said, e.h.slice()]);
        if (!held) { care.push([looks[w][1], reach ? 1 : 0, r.act > 0 ? 1 : 0]); heard.push([looks[w][1], watchedSpoke ? 1 : 0, reach ? 1 : 0]); if (looks[i][1] > 0.6) asks.push({ t, i, spoke: !!r.said }); }
      }
      cs.push(r.act > 0 && r.act < 7 ? OL.HUES[r.act - 1] : null); ws.push(r.said);
    });
    prevC = cs; prevW = ws;
  }
  const thirds = (L) => { L = L.slice().sort((a, b) => a[0] - b[0]); const k = Math.floor(L.length / 3); return [L.slice(-k), L.slice(0, k)]; };
  const share = (L) => mean(L.map(p => p[1])) / mean(L.map(p => p[2]));
  const [cTop, cBot] = thirds(care), [hTop] = thirds(heard);
  const got = (a) => reachedTimes[a.i].some(x => x > a.t && x <= a.t + 10) ? 1 : 0;
  const fit = mean(es.map(e => { const L = e.speechLog.filter(x => x.t > T / 2 && x.mine !== null && x.others !== null); return L.length ? (mean(L.map(x => x.others)) - mean(L.map(x => x.mine))) / mean(L.map(x => x.others)) : NaN; }).filter(v => !isNaN(v)));
  return {
    wordState: mean(said.map(eta).filter(v => !isNaN(v))), fit, nWords: mean(es.map(e => e.topWords().length)),
    readSpeaker: readSp.length ? (mean(readBy) - mean(readSp)) / mean(readBy) : NaN,
    // does what the word calls up vary with the speaker's look more than with a bystander's? correlation, speaker minus bystander, averaged over the four sides
    readCor: readC.length > 50 ? mean([0, 1, 2, 3].map(q => cor(readC.map(c => c[0][q]), readC.map(c => c[1][q])) - cor(readC.map(c => c[0][q]), readC.map(c => c[2][q])))) : NaN,
    lean: share(cTop) - share(cBot), reachTop: mean(cTop.map(p => p[1])),
    reachAfterWord: mean(hTop.filter(p => p[1]).map(p => p[2])), reachNoWord: mean(hTop.filter(p => !p[1]).map(p => p[2])),
    answeredSpoken: mean(asks.filter(a => a.spoke).map(got)), answeredSilent: mean(asks.filter(a => !a.spoke).map(got)),
    concepts: mean(es.map(e => e.mu.length)), speaks: mean(es.map(e => e.speechLog.filter(x => x.t > T / 2).length)) / (T / 2),
  };
}
module.exports = { run, mean };
if (require.main === module) {
  const [name, o] = JSON.parse(process.argv[2]); const S0 = +(process.env.S0 || 1), S1 = +(process.env.S1 || 12); const R = [];
  for (let seed = S0; seed <= S1; seed++) R.push(run({ seed, ...o }));
  const out = { name, runs: R.length };
  Object.keys(R[0]).forEach(k => (out[k] = mean(R.map(r => r[k]).filter(v => !isNaN(v)))));
  out.leanRuns = R.filter(r => r.lean > 0).length; out.readRuns = R.filter(r => r.readCor > 0).length; out.wordRuns = R.filter(r => r.reachAfterWord > r.reachNoWord).length; out.answeredRuns = R.filter(r => r.answeredSpoken > r.answeredSilent).length;
  console.log(JSON.stringify(out, (q, v) => typeof v === 'number' ? Math.round(v * 10000) / 10000 : v));
  require('fs').writeFileSync((process.env.TAG || 't16_') + name.replace(/\W+/g, '_') + '.json', JSON.stringify({ summary: out, runs: R }));
}
