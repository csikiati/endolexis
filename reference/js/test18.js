// stage 18: out of sight. Pairs that hear each other but see each other only part of the time (sight = share of time in view, in stretches).
// While the other is out of sight its four body channels are missing to the watcher (engine: sense.unseen), seeing it tremble cannot
// unsettle, and the only way its state can reach in is through what the watcher expects of it: from its words, its colours, the moment.
const { Entity, OL, ORng, bodyLook, voiceCode } = require('./engine.js');
const { setup, privateEvent, visitorWord } = require('./rich16.js');
const mean = (a) => a.length ? a.reduce((p, q) => p + q, 0) / a.length : NaN;
const cor = (a, b) => { if (a.length < 30) return NaN; const ma = mean(a), mb = mean(b); let s = 0, x = 0, y = 0; for (let i = 0; i < a.length; i++) { s += (a[i] - ma) * (b[i] - mb); x += (a[i] - ma) ** 2; y += (b[i] - mb) ** 2; } return s / Math.sqrt(x * y + 1e-12); };
function eta(rows) {
  const by = {}; rows.forEach(([w, h]) => (by[w] = by[w] || []).push(h)); const groups = Object.values(by).filter(g => g.length >= 5); if (groups.length < 2) return NaN;
  const all = groups.flat(); let s = 0;
  for (let i = 0; i < 4; i++) { const m = mean(all.map(h => h[i])); const tot = mean(all.map(h => (h[i] - m) ** 2)); const bet = groups.reduce((a, g) => a + g.length * (mean(g.map(h => h[i])) - m) ** 2, 0) / all.length; s += tot > 1e-9 ? bet / tot : 0; }
  return s / 4;
}
function run({ seed = 1, T = 40000, rich = true, hear = 6, feel = 12, sight = 1, readC = 0.05, sham = false, nameDistress = false, voices = false, sal = 0 } = {}) {
  const N = 2; setup(rich, hear, feel); OL.MAXC = 60; OL.RECALL = true; OL.CONTAGION = 0.05; OL.REACH = true; OL.GAMMA = 0.8; OL.COMPANY = 1; OL.COMPANY_CONTACT = false; OL.READ_CONTAGION = readC; OL.VOICES = voices; OL.SALIENCE = sal;
  const es = Array.from({ length: N }, (_, i) => new Entity(seed * 100 + i)); es.forEach((e, i) => { e.speechLog = []; e.voice = i; }); // voices: each speaker's words carry its own timbre (stage 6)
  const R = new ORng(seed); let pres = 0, prevC = [null, null], prevW = [null, null];
  const avgLook = es.map(() => [0.5, 0.5, 0.5, 0.5]), sees = [R.next() < sight, R.next() < sight], lastSpoke = [-99, -99];
  const said = es.map(() => []), rows = [], asks = [], reachedTimes = es.map(() => []), imag = [];
  for (let t = 0; t < T; t++) {
    const ph = t % 600, active = ph < 420; pres = active ? Math.min(.8, pres + .05) : pres * .985;
    es.forEach((e, i) => { const L = bodyLook(e.h); avgLook[i] = avgLook[i].map((v, k) => v + 0.01 * (L[k] - v)); });
    for (let i = 0; i < N; i++) if (R.next() < 0.01) sees[i] = R.next() < sight; // stretches in and out of view, about 100 steps each
    let word = null, col = null;
    if (active && R.next() < 0.03) { const tg = Math.floor(R.next() * N); const L = bodyLook(es[tg].h); word = nameDistress && L[1] > avgLook[tg][1] + 0.12 ? 'uneasy' : visitorWord(L, avgLook[tg], R, rich); } // nameDistress: like a caregiver, the visitor always names trembling when it sees it
    if (active && R.next() < 0.01) col = Math.floor(R.next() * 6);
    const looks = es.map(e => bodyLook(e.h)), late = t > T / 2;
    const cs = [], ws = [];
    es.forEach((e, i) => {
      privateEvent(e, R, rich);
      const w = 1 - i, ic = prevC[w] !== null ? [prevC[w]] : [], iw = prevW[w] ? [{ w: prevW[w], from: w }] : [];
      const unseen = !sees[i];
      const held = (e.companyT || 0) > 0 || (es[w].companyT || 0) > 0;
      e.updateGate(1);
      const r = e.tick({ typing: word ? .4 : 0, vowels: .4, speed: .1, px: .5, py: .5, presence: pres, seen: unseen ? null : looks[w], unseen }, col, word, ic, iw);
      const reach = r.act === 11;
      if (reach) reachedTimes[w].push(t);
      if (reach && !sham) es[w].company();
      if (r.said) lastSpoke[i] = t;
      if (late) {
        if (r.said) said[i].push([r.said, e.h.slice()]);
        // what it imagines of the other's trembling: the patterns it reads itself as, and the trembling they expect to see (observer's view)
        if (unseen && e.belief && e.belief.length) { let ex = 0; e.belief.forEach((p, j) => (ex += p * e.mu[j][13])); imag.push([ex, looks[w][1], t - lastSpoke[w] <= 5 ? 1 : 0]); }
        if (!held) {
          rows.push({ unseen, tr: looks[w][1], reach: reach ? 1 : 0, acted: r.act > 0 ? 1 : 0, spoke: t - lastSpoke[w] <= 3 ? 1 : 0, saidTr: looks[w][1] });
          if (looks[i][1] > 0.6) asks.push({ t, i, spoke: !!r.said, unseenByOther: !sees[w] });
        }
      }
      cs.push(r.act > 0 && r.act < 7 ? OL.HUES[r.act - 1] : null); ws.push(r.said);
    });
    prevC = cs; prevW = ws;
  }
  const thirds = (L, key) => { L = L.slice().sort((a, b) => a[key] - b[key]); const k = Math.floor(L.length / 3); return [L.slice(-k), L.slice(0, k)]; };
  const share = (L) => mean(L.map(p => p.reach)) / mean(L.map(p => p.acted));
  const lean = (L) => { if (L.length < 300) return NaN; const [top, bot] = thirds(L, 'tr'); return share(top) - share(bot); };
  const S = rows.filter(r => !r.unseen), U = rows.filter(r => r.unseen);
  const rate = (L) => mean(L.map(p => p.reach));
  // asking in the dark: among moments the watcher cannot see, does the other's having just spoken bring a reach, and more so when the speaker trembles?
  const [uTop, uBot] = U.length > 300 ? thirds(U, 'tr') : [[], []];
  const got = (a) => reachedTimes[a.i].some(x => x > a.t && x <= a.t + 10) ? 1 : 0;
  const aU = asks.filter(a => a.unseenByOther), aS = asks.filter(a => !a.unseenByOther);
  const fit = mean(es.map(e => { const L = e.speechLog.filter(x => x.t > T / 2 && x.mine !== null && x.others !== null); return L.length ? (mean(L.map(x => x.others)) - mean(L.map(x => x.mine))) / mean(L.map(x => x.others)) : NaN; }).filter(v => !isNaN(v)));
  const imW = imag.filter(x => x[2]), imN = imag.filter(x => !x[2]);
  run.lastEs = es;
  return {
    wordState: mean(said.map(eta).filter(v => !isNaN(v))), fit,
    leanSeen: lean(S), leanUnseen: lean(U), unseenShare: U.length / Math.max(1, rows.length),
    // reach toward an unseen trembling one: after it spoke, and after silence
    reachUnseenTrSpoke: mean(uTop.filter(p => p.spoke).map(p => p.reach)), reachUnseenTrSilent: mean(uTop.filter(p => !p.spoke).map(p => p.reach)),
    reachUnseenCalmSpoke: mean(uBot.filter(p => p.spoke).map(p => p.reach)), reachUnseenCalmSilent: mean(uBot.filter(p => !p.spoke).map(p => p.reach)),
    answeredSpokenUnseen: mean(aU.filter(a => a.spoke).map(got)), answeredSilentUnseen: mean(aU.filter(a => !a.spoke).map(got)),
    answeredSpokenSeen: mean(aS.filter(a => a.spoke).map(got)), answeredSilentSeen: mean(aS.filter(a => !a.spoke).map(got)),
    // reading in the dark: does what it imagines of the other's trembling follow the real trembling, right after a word and otherwise?
    imagCorAfterWord: cor(imW.map(x => x[0]), imW.map(x => x[1])), imagCorNoWord: cor(imN.map(x => x[0]), imN.map(x => x[1])),
    uneasyShare: (() => { let n = 0, u = 0; es.forEach(e => e.speechLog.filter(x => x.t > T / 2).forEach(x => { n++; if (x.w === 'uneasy') u++; })); return n ? u / n : NaN; })(),
    // what 'uneasy' (against 'easy'), heard in the other's voice, leads it to expect of the other's trembling, and of its own steadiness (observer's view)
    uneasyOther: mean(es.map((e, i) => { const a = e.expectSeen('uneasy', voiceCode('uneasy', OL.VOICES ? 1 - i : null)), b = e.expectSeen('easy', voiceCode('easy', OL.VOICES ? 1 - i : null)); return a && b ? a[1] - b[1] : NaN; }).filter(v => !isNaN(v))),
    uneasyOwn: mean(es.map((e, i) => { const a = e.evokeWord('uneasy', voiceCode('uneasy', OL.VOICES ? 1 - i : null)), b = e.evokeWord('easy', voiceCode('easy', OL.VOICES ? 1 - i : null)); return a && b ? b.ev[1] - a.ev[1] : NaN; }).filter(v => !isNaN(v))),
    speaks: mean(es.map(e => e.speechLog.filter(x => x.t > T / 2).length)) / (T / 2),
  };
}
module.exports = { run, mean };
if (require.main === module) {
  const [name, o] = JSON.parse(process.argv[2]); const S0 = +(process.env.S0 || 1), S1 = +(process.env.S1 || 12); const R = [];
  for (let seed = S0; seed <= S1; seed++) R.push(run({ seed, ...o }));
  const out = { name, runs: R.length };
  Object.keys(R[0]).forEach(k => (out[k] = mean(R.map(r => r[k]).filter(v => !isNaN(v)))));
  out.leanUnseenRuns = R.filter(r => r.leanUnseen > 0).length; out.askRuns = R.filter(r => r.reachUnseenTrSpoke - r.reachUnseenTrSilent > r.reachUnseenCalmSpoke - r.reachUnseenCalmSilent).length;
  out.answeredUnseenRuns = R.filter(r => r.answeredSpokenUnseen > r.answeredSilentUnseen).length; out.imagRuns = R.filter(r => r.imagCorAfterWord > r.imagCorNoWord).length;
  console.log(JSON.stringify(out, (q, v) => typeof v === 'number' ? Math.round(v * 10000) / 10000 : v));
  require('fs').writeFileSync((process.env.TAG || 't18_') + name.replace(/\W+/g, '_') + '.json', JSON.stringify({ summary: out, runs: R }));
}
