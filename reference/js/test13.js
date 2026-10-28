// stage 12: attachment. Bonds that grow by themselves: each comes to look most at the one whose company has steadied it.
// stage 11: many others. In rooms of several, does caring hold, does each care more for the one it watches most, and does it spread or crowd itself out?
const { Entity, OL, ORng, bodyLook } = require('./engine.js');
const mean = (a) => a.length ? a.reduce((p, q) => p + q, 0) / a.length : NaN;
// gaze: 'shared' = all watch whoever made a sign last; 'pairs' = each has a partner (0-1, 2-3, 4-5) it watches 60% of the time
function run({ N = 4, seed = 1, T = 40000, gaze = 'shared', sham = false, contagion = 0.05, bondRate = 1, bondDecay = 0.9995, tau = 0.05, randomBond = false, faces = false, close = 0 } = {}) {
  const face = Array.from({ length: N }, (_, j) => [0.15 + 0.7 * ((j * 0.618034) % 1), 0.15 + 0.7 * ((j * 0.381966 + 0.5) % 1)]); // a face: a fixed look of its own, seen on two channels
  OL.RECALL = true; OL.CONTAGION = contagion; OL.REACH = true; OL.GAMMA = 0.8; OL.COMPANY = 1; OL.COMPANY_CONTACT = false;
  const es = Array.from({ length: N }, (_, i) => new Entity(seed * 100 + i));
  const R = new ORng(seed); let pres = 0, focus = 0, prevC = es.map(() => null), prevW = es.map(() => null);
  const avgLook = es.map(() => [0.5, 0.5, 0.5, 0.5]); const partner = (i) => (i ^ 1) < N ? i ^ 1 : (i + 1) % N;
  const rt = [], perPair = { p: { tw: 0, tr: 0 }, o: { tw: 0, tr: 0 } }, episodes = []; let distress = [], tremble = []; const open = new Map();
  let lookAt = es.map((_, i) => (i + 1) % N);
  const bond = es.map(() => new Array(N).fill(0)), pendingB = [], watchCnt = es.map(() => new Array(N).fill(0)), careB = { b: { tw: 0, tr: 0 }, o: { tw: 0, tr: 0 } };
  const pickBond = (i) => { const w = bond[i].map((b, j) => (j === i ? 0 : Math.exp(b / tau))); const s = w.reduce((a, b) => a + b, 0); let r = R.next() * s; for (let j = 0; j < N; j++) { r -= w[j]; if (r <= 0 && j !== i) return j; } return (i + 1) % N; };
  const topBond = (i) => { let b = -1, v = -Infinity; for (let j = 0; j < N; j++) if (j !== i && bond[i][j] > v) { v = bond[i][j]; b = j; } return b; };
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
    lookAt = es.map((_, i) => { if (gaze === 'pairs' && (R.next() < 0.6 || focus === i)) return partner(i); if (gaze === 'attach' && (R.next() < 0.6 || focus === i)) return pickBond(i); return focus !== i ? focus : (i + 1) % N; });
    for (let k = 0; k < N; k++) for (let j = 0; j < N; j++) bond[k][j] *= bondDecay;
    // a bond grows by how much steadier one became in the ten steps after another reached toward it
    while (pendingB.length && t - pendingB[0].t >= 10) { const p = pendingB.shift(); const gain = es[p.to].h[1] - p.h1; const from = randomBond ? [...Array(N).keys()].filter(j => j !== p.to)[Math.floor(R.next() * (N - 1))] : p.from; bond[p.to][from] += bondRate * gain; }
    // trembling episodes: a not-held Olvasó starts trembling hard; does anyone reach it within 10 steps, and how many?
    if (t > T / 2) es.forEach((e, j) => { if (looks[j][1] > 0.6 && !(e.companyT > 0) && !open.has(j)) open.set(j, { t, reachers: new Set() }); });
    const cs = [], ws = [];
    es.forEach((e, i) => {
      if (R.next() < 0.004) { const h = Math.floor(R.next() * 6); for (let k = 0; k < 3; k++) e.addColour(OL.HUES[h], 'you'); e.h[0] = Math.min(1, e.h[0] + 0.2); e.h[1] = Math.max(0, e.h[1] - 0.25); }
      const ic = [], iw = []; for (let j = 0; j < N; j++) if (j !== i) { if (prevC[j] !== null) ic.push(prevC[j]); if (prevW[j]) iw.push(prevW[j]); }
      const w = lookAt[i], seen = looks[w];
      const held = (e.companyT || 0) > 0 || (es[w].companyT || 0) > 0;
      if (close) { const mx = Math.max(1e-6, ...bond[i].filter((_, j) => j !== i)); const c = bond[i][w] > 0 ? Math.min(1, bond[i][w] / mx) : 0; e.closeGain = close === 2 ? 0.8 + 0.6 * c : 0.5 + 1.5 * c; } else e.closeGain = 1;
      e.updateGate(1); const r = e.tick({ typing: word ? .4 : 0, vowels: .4, speed: .1, px: faces ? face[w][0] : .5, py: faces ? face[w][1] : .5, presence: pres, seen }, col, word, ic, iw);
      const reach = r.act === 11;
      if (reach && open.has(w)) open.get(w).reachers.add(i);
      if (reach) pendingB.push({ t, from: i, to: w, h1: es[w].h[1] });
      if (reach && !sham) es[w].company();
      if (t > T / 2) { watchCnt[i][w]++; if (!held && seen[1] > 0.6) { const k = w === topBond(i) ? 'b' : 'o'; careB[k].tw++; if (reach) careB[k].tr++; } }
      if (t > T / 2) {
        distress.push(e.distress()); tremble.push(looks[i][1]);
        if (!held) { rt.push([seen[1], reach ? 1 : 0, r.act > 0 ? 1 : 0, w === topBond(i) ? 1 : 0]); if (seen[1] > 0.6) { const k = w === partner(i) ? 'p' : 'o'; perPair[k].tw++; if (reach) perPair[k].tr++; } }
      }
      cs.push(r.act > 0 && r.act < 7 ? OL.HUES[r.act - 1] : null); ws.push(r.said);
    });
    for (const [j, ep] of open) if (t - ep.t >= 10) { episodes.push(ep.reachers.size); open.delete(j); }
    prevC = cs; prevW = ws;
  }
  rt.sort((a, b) => a[0] - b[0]); const th = Math.floor(rt.length / 3);
  const conc = mean(watchCnt.map((r, i) => { const tot = r.reduce((a, b) => a + b, 0); return tot ? Math.max(...r) / tot : NaN; }));
  const tops = es.map((_, i) => topBond(i)); const mutual = mean(tops.map((j, i) => (tops[j] === i ? 1 : 0)));
  const topWatched = watchCnt.map((r) => r.indexOf(Math.max(...r)));
  const share = (L) => mean(L.map(p => p[1])) / mean(L.map(p => p[2]));
  const leanOf = (L) => { L = L.slice().sort((a, b) => a[0] - b[0]); const k = Math.floor(L.length / 3); return share(L.slice(-k)) - share(L.slice(0, k)); };
  const leanBonded = leanOf(rt.filter(p => p[3] === 1)), leanOthers = leanOf(rt.filter(p => p[3] === 0));
  return { leanBonded, leanOthers, leanShare: share(rt.slice(-th)) - share(rt.slice(0, th)), reachShareTrembling: share(rt.slice(-th)), reachShareSteady: share(rt.slice(0, th)),
    rescued: mean(episodes.map(n => n > 0 ? 1 : 0)), reachersPerEpisode: mean(episodes), episodes: episodes.length,
    reachRateTremblingPartner: perPair.p.tw ? perPair.p.tr / perPair.p.tw : NaN, reachRateTremblingOther: perPair.o.tw ? perPair.o.tr / perPair.o.tw : NaN,
    distress: mean(distress), tremble: mean(tremble), gazeOnTop: conc, mutualBonds: mutual, topWatched: topWatched.join(''),
    reachRateBonded: careB.b.tw ? careB.b.tr / careB.b.tw : NaN, reachRateOthers: careB.o.tw ? careB.o.tr / careB.o.tw : NaN };
}
module.exports = { run, mean };
if (require.main === module) {
  const [name, o] = JSON.parse(process.argv[2]); const S0 = +(process.env.S0 || 1), S1 = +(process.env.S1 || 12); const R = [];
  for (let seed = S0; seed <= S1; seed++) R.push(run({ seed, ...o }));
  const out = { name, runs: R.length, leanRuns: R.filter(r => r.leanShare > 0).length };
  Object.keys(R[0]).forEach(k => out[k] = mean(R.map(r => r[k]).filter(v => !isNaN(v))));
  out.bondedLeanRuns = R.filter(r => r.leanBonded > r.leanOthers).length;
  out.bondedRuns = R.filter(r => r.reachRateBonded > r.reachRateOthers).length;
  if (o.gaze === 'pairs') out.partnerRuns = R.filter(r => r.reachRateTremblingPartner > r.reachRateTremblingOther).length;
  console.log(JSON.stringify(out, (q, v) => typeof v === 'number' ? Math.round(v * 10000) / 10000 : v));
  require('fs').writeFileSync('t13_' + name.replace(/\W+/g, '_') + '.json', JSON.stringify({ summary: out, runs: R }));
}
