// stage 14: asking. Does a trembling one's word become a request?
const { Entity, OL, ORng, bodyLook } = require('./engine.js');
const mean = (a) => a.length ? a.reduce((p, q) => p + q, 0) / a.length : NaN;
function run({ N = 2, seed = 1, T = 40000, sham = false, contagion = 0.05, dim = 0, readC = 0 } = {}) {
  OL.READ_CONTAGION = readC; OL.RECALL = true; OL.CONTAGION = contagion; OL.REACH = true; OL.GAMMA = 0.8; OL.COMPANY = 1; OL.COMPANY_CONTACT = false;
  const es = Array.from({ length: N }, (_, i) => new Entity(seed * 100 + i));
  const R = new ORng(seed); let pres = 0, focus = 0, prevC = es.map(() => null), prevW = es.map(() => null);
  const avgLook = es.map(() => [0.5, 0.5, 0.5, 0.5]);
  const own = [], heard = [], asks = [], lastSaid = es.map(() => -99), reachedTimes = es.map(() => []);
  for (let t = 0; t < T; t++) {
    const ph = t % 600, active = ph < 420; pres = active ? Math.min(.8, pres + .05) : pres * .985;
    es.forEach((e, i) => { const L = bodyLook(e.h); avgLook[i] = avgLook[i].map((v, k) => v + 0.01 * (L[k] - v)); });
    let word = null, col = null;
    if (active && R.next() < 0.03) { const tg = Math.floor(R.next() * N), L = bodyLook(es[tg].h), A = avgLook[tg];
      if (L[3] > 0.45) word = 'busy'; else if (L[1] > A[1] + 0.12) word = 'restless'; else if (L[1] < A[1] - 0.06) word = 'calm'; else if (L[3] < 0.15) word = 'still'; if (word) focus = tg; }
    if (active && R.next() < 0.01) col = Math.floor(R.next() * 6);
    const signers = []; for (let j = 0; j < N; j++) if (prevW[j] || prevC[j] !== null) signers.push(j);
    if (signers.length) focus = signers[Math.floor(R.next() * signers.length)];
    const looks = es.map(e => bodyLook(e.h));
    const lookAt = es.map((_, i) => focus !== i ? focus : (i + 1) % N);
    const cs = [], ws = [];
    es.forEach((e, i) => {
      if (R.next() < 0.004) { const h = Math.floor(R.next() * 6); for (let k = 0; k < 3; k++) e.addColour(OL.HUES[h], 'you'); e.h[0] = Math.min(1, e.h[0] + 0.2); e.h[1] = Math.max(0, e.h[1] - 0.25); }
      const ic = [], iw = []; for (let j = 0; j < N; j++) if (j !== i) { if (prevC[j] !== null) ic.push(prevC[j]); if (prevW[j]) iw.push(prevW[j]); }
      const w = lookAt[i];
      // dim: the body is harder to see; its trembling shows only partly (seen moves toward the middle)
      const seen = looks[w].map(v => dim ? 0.5 + (1 - dim) * (v - 0.5) : v);
      const held = (e.companyT || 0) > 0 || (es[w].companyT || 0) > 0;
      const watchedSpoke = !!prevW[w];
      e.updateGate(1); const r = e.tick({ typing: word ? .4 : 0, vowels: .4, speed: .1, px: .5, py: .5, presence: pres, seen }, col, word, ic, iw);
      const reach = r.act === 11;
      if (reach) reachedTimes[w].push(t);
      if (reach && !sham) es[w].company();
      if (r.said) lastSaid[i] = t;
      if (t > T / 2 && !held) {
        own.push([looks[i][1], r.said ? 1 : 0, r.act > 0 ? 1 : 0]);                                 // does it speak more when it trembles itself?
        heard.push([looks[w][1], watchedSpoke ? 1 : 0, reach ? 1 : 0, r.act > 0 ? 1 : 0, watchedSpoke ? prevW[w] : null]); // does hearing the watched one speak make it reach?
        if (looks[i][1] > 0.6) asks.push({ t, i, spoke: !!r.said });                                // a trembling moment: spoken or silent; is it reached soon after?
      }
      cs.push(r.act > 0 && r.act < 7 ? OL.HUES[r.act - 1] : null); ws.push(r.said);
    });
    prevC = cs; prevW = ws;
  }
  const thirds = (L) => { L = L.slice().sort((a, b) => a[0] - b[0]); const k = Math.floor(L.length / 3); return [L.slice(-k), L.slice(0, k)]; };
  const [oTop, oBot] = thirds(own);
  // reach after hearing the watched one speak, among moments when the watched one trembles (top third of seen trembling)
  const [hTop] = thirds(heard);
  const reachSpoke = mean(hTop.filter(p => p[1]).map(p => p[2])), reachSilent = mean(hTop.filter(p => !p[1]).map(p => p[2]));
  const byWord = {}; hTop.filter(p => p[1]).forEach(p => { (byWord[p[4]] = byWord[p[4]] || []).push(p[2]); });
  // answered: reached within 10 steps after a trembling moment, spoken vs silent (pairs only make this clean)
  const got = (a) => reachedTimes[a.i].some(x => x > a.t && x <= a.t + 10) ? 1 : 0;
  const answeredSpoken = mean(asks.filter(a => a.spoke).map(got)), answeredSilent = mean(asks.filter(a => !a.spoke).map(got));
  return { speakWhenTrembling: mean(oTop.map(p => p[1])), speakWhenSteady: mean(oBot.map(p => p[1])),
    answeredSpoken, answeredSilent, reachAfterWord: reachSpoke, reachNoWord: reachSilent, nWord: hTop.filter(p => p[1]).length,
    byWord: Object.fromEntries(Object.entries(byWord).filter(([, v]) => v.length > 30).map(([k, v]) => [k, mean(v)])) };
}
module.exports = { run, mean };
if (require.main === module) {
  const [name, o] = JSON.parse(process.argv[2]); const S0 = +(process.env.S0 || 1), S1 = +(process.env.S1 || 12); const R = [];
  for (let seed = S0; seed <= S1; seed++) R.push(run({ seed, ...o }));
  const out = { name, runs: R.length };
  ['speakWhenTrembling', 'speakWhenSteady', 'answeredSpoken', 'answeredSilent', 'reachAfterWord', 'reachNoWord', 'nWord'].forEach(k => out[k] = mean(R.map(r => r[k]).filter(v => !isNaN(v))));
  out.speakLeanRuns = R.filter(r => r.speakWhenTrembling > r.speakWhenSteady).length; out.answeredRuns = R.filter(r => r.answeredSpoken > r.answeredSilent).length; out.wordRuns = R.filter(r => r.reachAfterWord > r.reachNoWord).length;
  const words = {}; R.forEach(r => Object.entries(r.byWord).forEach(([k, v]) => (words[k] = words[k] || []).push(v))); out.byWord = Object.fromEntries(Object.entries(words).map(([k, v]) => [k, mean(v)]));
  console.log(JSON.stringify(out, (q, v) => typeof v === 'number' ? Math.round(v * 10000) / 10000 : v));
  require('fs').writeFileSync('t14_' + name.replace(/\W+/g, '_') + '.json', JSON.stringify({ summary: out, runs: R }));
}
