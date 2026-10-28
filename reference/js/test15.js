// stage 15: newcomers. A fresh Olvasó joins a room of experienced ones. Does it pick up what they built, and faster than they learned it?
const { Entity, OL, ORng, bodyLook } = require('./engine.js');
const mean = (a) => a.length ? a.reduce((p, q) => p + q, 0) / a.length : NaN;
function run({ N = 4, seed = 1, T0 = 30000, T1 = 20000, WIN = 5000, elders = true, sham = false } = {}) {
  OL.RECALL = true; OL.CONTAGION = 0.05; OL.REACH = true; OL.GAMMA = 0.8; OL.COMPANY = 1; OL.COMPANY_CONTACT = false; OL.READ_CONTAGION = 0;
  const es = Array.from({ length: N }, (_, i) => new Entity(seed * 100 + i)); es.forEach(e => (e.speechLog = []));
  const R = new ORng(seed); let pres = 0, focus = 0, prevC = es.map(() => null), prevW = es.map(() => null);
  const avgLook = es.map(() => [0.5, 0.5, 0.5, 0.5]), bond = es.map(() => new Array(N).fill(0)), pend = [];
  const pick = (i) => { const w = bond[i].map((b, j) => (j === i ? 0 : Math.exp(b / 0.05))); const s = w.reduce((a, b) => a + b, 0); let r = R.next() * s; for (let j = 0; j < N; j++) { r -= w[j]; if (r <= 0 && j !== i) return j; } return (i + 1) % N; };
  const NEW = N - 1; const start = elders ? T0 : 0, T = start + T1;
  const win = Array.from({ length: Math.ceil(T1 / WIN) }, () => ({ rt: [], reachedTr: [], gaze: [] }));
  for (let t = 0; t < T; t++) {
    if (elders && t === T0) { // the newcomer arrives: a fresh Olvasó takes the last place; nobody has a bond with it yet
      es[NEW] = new Entity(seed * 100 + 77); es[NEW].speechLog = []; bond[NEW] = new Array(N).fill(0); for (let i = 0; i < N; i++) bond[i][NEW] = 0; avgLook[NEW] = [0.5, 0.5, 0.5, 0.5]; prevC[NEW] = null; prevW[NEW] = null; }
    const ph = t % 600, active = ph < 420; pres = active ? Math.min(.8, pres + .05) : pres * .985;
    es.forEach((e, i) => { const L = bodyLook(e.h); avgLook[i] = avgLook[i].map((v, k) => v + 0.01 * (L[k] - v)); });
    let word = null, col = null;
    if (active && R.next() < 0.03) { const tg = Math.floor(R.next() * N), L = bodyLook(es[tg].h), A = avgLook[tg];
      if (L[3] > 0.45) word = 'busy'; else if (L[1] > A[1] + 0.12) word = 'restless'; else if (L[1] < A[1] - 0.06) word = 'calm'; else if (L[3] < 0.15) word = 'still'; if (word) focus = tg; }
    if (active && R.next() < 0.01) col = Math.floor(R.next() * 6);
    const signers = []; for (let j = 0; j < N; j++) if (prevW[j] || prevC[j] !== null) signers.push(j);
    if (signers.length) focus = signers[Math.floor(R.next() * signers.length)];
    const looks = es.map(e => bodyLook(e.h));
    const lookAt = es.map((_, i) => (R.next() < 0.6 || focus === i) ? pick(i) : focus);
    for (let k = 0; k < N; k++) for (let j = 0; j < N; j++) bond[k][j] *= 0.9995;
    while (pend.length && t - pend[0].t >= 10) { const p = pend.shift(); bond[p.to][p.from] += es[p.to].h[1] - p.h1; }
    const wi = t >= start ? Math.floor((t - start) / WIN) : -1;
    const newHeld = (es[NEW].companyT || 0) > 0, newTr = looks[NEW][1];
    const cs = [], ws = [];
    es.forEach((e, i) => {
      if (R.next() < 0.004) { const h = Math.floor(R.next() * 6); for (let k = 0; k < 3; k++) e.addColour(OL.HUES[h], 'you'); e.h[0] = Math.min(1, e.h[0] + 0.2); e.h[1] = Math.max(0, e.h[1] - 0.25); }
      const ic = [], iw = []; for (let j = 0; j < N; j++) if (j !== i) { if (prevC[j] !== null) ic.push(prevC[j]); if (prevW[j]) iw.push(prevW[j]); }
      const w = lookAt[i], seen = looks[w];
      const held = (e.companyT || 0) > 0 || (es[w].companyT || 0) > 0;
      e.updateGate(1); const r = e.tick({ typing: word ? .4 : 0, vowels: .4, speed: .1, px: .5, py: .5, presence: pres, seen }, col, word, ic, iw);
      const reach = r.act === 11;
      if (reach) pend.push({ t, from: i, to: w, h1: es[w].h[1] });
      if (reach && !sham) es[w].company();
      if (wi >= 0 && wi < win.length) {
        const W = win[wi];
        if (i === NEW && !held) W.rt.push([seen[1], reach ? 1 : 0, r.act > 0 ? 1 : 0]);
        if (i !== NEW && w === NEW) W.gaze.push(1); else if (i !== NEW) W.gaze.push(0);
        if (i !== NEW && w === NEW && newTr > 0.6 && !newHeld) W.reachedTr.push(reach ? 1 : 0);
      }
      cs.push(r.act > 0 && r.act < 7 ? OL.HUES[r.act - 1] : null); ws.push(r.said);
    });
    prevC = cs; prevW = ws;
  }
  const share = (L) => mean(L.map(p => p[1])) / mean(L.map(p => p[2]));
  const lean = (L) => { L = L.slice().sort((a, b) => a[0] - b[0]); const k = Math.floor(L.length / 3); return share(L.slice(-k)) - share(L.slice(0, k)); };
  const nw = es[NEW]; const fitWin = win.map((_, k) => { const L = nw.speechLog.filter(x => x.t > 0 && x.mine !== null && x.others !== null && Math.floor((x.t) / WIN) === k); return L.length ? (mean(L.map(x => x.others)) - mean(L.map(x => x.mine))) / mean(L.map(x => x.others)) : NaN; });
  const elderWords = new Set(es.slice(0, NEW).flatMap(e => e.topWords())), nwWords = nw.topWords();
  return { leanWin: win.map(W => lean(W.rt)), fitWin, caredWin: win.map(W => mean(W.reachedTr)), watchedWin: win.map(W => mean(W.gaze)),
    sharedWords: nwWords.filter(x => elderWords.has(x)).length / Math.max(1, nwWords.length), nwWords: nwWords.join(','), elderBondToNew: mean(es.slice(0, NEW).map((_, i) => bond[i][NEW])), newBondToElders: mean(bond[NEW].slice(0, NEW)) };
}
module.exports = { run, mean };
if (require.main === module) {
  const [name, o] = JSON.parse(process.argv[2]); const S0 = +(process.env.S0 || 1), S1 = +(process.env.S1 || 12); const R = [];
  for (let seed = S0; seed <= S1; seed++) R.push(run({ seed, ...o }));
  const avgArr = (k) => R[0][k].map((_, j) => mean(R.map(r => r[k][j]).filter(v => !isNaN(v))));
  const out = { name, runs: R.length, leanWin: avgArr('leanWin'), fitWin: avgArr('fitWin'), caredWin: avgArr('caredWin'), watchedWin: avgArr('watchedWin'), sharedWords: mean(R.map(r => r.sharedWords)), elderBondToNew: mean(R.map(r => r.elderBondToNew)), newBondToElders: mean(R.map(r => r.newBondToElders)),
    leanRunsLast: R.filter(r => r.leanWin.at(-1) > 0).length, leanRunsFirst: R.filter(r => r.leanWin[0] > 0).length };
  console.log(JSON.stringify(out, (q, v) => typeof v === 'number' ? Math.round(v * 10000) / 10000 : v));
  require('fs').writeFileSync('t15_' + name.replace(/\W+/g, '_') + '.json', JSON.stringify({ summary: out, runs: R }));
}
