// stage 9: answering. Does what one Olvasó reads of another change what it does?
const { Entity, OL, ORng, bodyLook } = require('./engine.js');
const mean = (a) => a.length ? a.reduce((p, q) => p + q, 0) / a.length : NaN;
function mi(pairs) { const n = pairs.length; if (!n) return NaN; const cx = {}, cy = {}, cxy = {}; pairs.forEach(([a, b]) => { cx[a] = (cx[a] || 0) + 1; cy[b] = (cy[b] || 0) + 1; cxy[a + '|' + b] = (cxy[a + '|' + b] || 0) + 1; });
  let m = 0; for (const k in cxy) { const [a, b] = k.split('|'); const p = cxy[k] / n; m += p * Math.log2(p / ((cx[a] / n) * (cy[b] / n))); } return m; }
// directed: an Olvasó's colour reaches only the one it watches; contagion: seeing another tremble lowers its own steadiness
function run({ N = 4, seed = 1, T = 16000, directed = false, contagion = 0, jolts = true, recall = true, reach = false, sham = false, gamma = 0.8, mutual = false, company = 1, companyContact: o_cc = false } = {}) {
  OL.COMPANY = company; OL.COMPANY_CONTACT = !!o_cc;
  OL.GAMMA = gamma;
  OL.RECALL = recall; OL.CONTAGION = contagion; OL.REACH = reach;
  const es = Array.from({ length: N }, (_, i) => new Entity(seed * 100 + i));
  const R = new ORng(seed); let pres = 0, focus = 0, prevC = es.map(() => null), prevW = es.map(() => null), prevLook = es.map(() => 0);
  const avgLook = es.map(() => [0.5, 0.5, 0.5, 0.5]); const resp = { hi: [], lo: [] }, wordAct = [], acted = [], notActed = [], distress = []; const trembLog = [];
  for (let t = 0; t < T; t++) {
    const ph = t % 600, active = ph < 420; pres = active ? Math.min(.8, pres + .05) : pres * .985;
    es.forEach((e, i) => { const L = bodyLook(e.h); avgLook[i] = avgLook[i].map((v, k) => v + 0.01 * (L[k] - v)); });
    let word = null, col = null;
    if (active && R.next() < 0.03) { const tg = Math.floor(R.next() * N), L = bodyLook(es[tg].h), A = avgLook[tg];
      if (L[3] > 0.45) word = 'busy'; else if (L[1] > A[1] + 0.12) word = 'restless'; else if (L[1] < A[1] - 0.06) word = 'calm'; else if (L[3] < 0.15) word = 'still'; if (word) focus = tg; }
    if (active && R.next() < 0.01) col = Math.floor(R.next() * 6);
    const signers = []; for (let j = 0; j < N; j++) if (prevW[j] || prevC[j] !== null) signers.push(j);
    if (signers.length) focus = signers[Math.floor(R.next() * signers.length)];
    const looks = es.map(e => bodyLook(e.h)); trembLog.push(looks.map(l => l[1]));
    const lookAt = es.map((_, i) => focus !== i ? focus : (i + 1) % N);
    const cs = [], ws = [];
    es.forEach((e, i) => {
      if (jolts && R.next() < 0.004) { const h = Math.floor(R.next() * 6); for (let k = 0; k < 3; k++) e.addColour(OL.HUES[h], 'you'); e.h[0] = Math.min(1, e.h[0] + 0.2); e.h[1] = Math.max(0, e.h[1] - 0.25); }
      const ic = [], iw = []; for (let j = 0; j < N; j++) if (j !== i) { if (prevC[j] !== null && (!directed || prevLook[j] === i)) ic.push(prevC[j]); if (prevW[j]) iw.push(prevW[j]); }
      const w = lookAt[i], seen = looks[w];
      const pre = { self: e.companyT || 0, other: es[w].companyT || 0 };
      e.updateGate(1); const r = e.tick({ typing: word ? .4 : 0, vowels: .4, speed: .1, px: .5, py: .5, presence: pres, seen }, col, word, ic, iw);
      const kind = r.act === 0 ? 'rest' : r.act < 7 ? 'colour' : r.act === 11 ? 'reach' : 'speak';
      if (kind === 'reach' && !sham) { es[w].company(); if (mutual) e.company(); }
      if (t > T / 2 && !(pre.self > 0) && !(pre.other > 0)) { (resp.ot = resp.ot || []).push([bodyLook(e.h)[1], kind === 'reach' ? 1 : 0, kind === 'rest' ? 0 : 1]); (resp.rt = resp.rt || []).push([seen[1], kind === 'reach' ? 1 : 0, kind === 'rest' ? 0 : 1, kind === 'reach' ? 0 : kind === 'rest' ? 0 : 1]); if (seen[1] > 0.6) (resp.rh = resp.rh || []).push(kind === 'reach' ? 1 : 0); else if (seen[1] < 0.35) (resp.rl = resp.rl || []).push(kind === 'reach' ? 1 : 0);
        if (seen[1] > 0.6 && t + 8 < T) (kind === 'reach' ? (resp.ra = resp.ra || []) : (resp.rn = resp.rn || [])).push({ t, w, tr: seen[1] });
        if (iw.length && !word) (resp.rw = resp.rw || []).push([iw[0], kind === 'reach' ? 1 : 0]); }
      if (t > T / 2) {
        if (seen[1] > 0.5) resp.hi.push(kind === 'colour' ? 1 : 0); else if (seen[1] < 0.2) resp.lo.push(kind === 'colour' ? 1 : 0);
        if (iw.length && !word) wordAct.push([iw[0], kind]);
        if (seen[1] > 0.4 && t + 8 < T) (kind === 'colour' && directed ? acted : notActed).push({ t, w, tr: seen[1] });
        distress.push(e.distress());
      }
      cs.push(kind === 'colour' ? OL.HUES[r.act - 1] : null); ws.push(r.said);
    });
    prevC = cs; prevW = ws; prevLook = lookAt;
  }
  // after a trembling one is given a colour by the one watching it, how does its trembling change over the next 8 steps, against when nobody gives it one?
  const dTr = (L) => mean(L.filter(x => trembLog[x.t + 8]).map(x => trembLog[x.t + 8][x.w] - x.tr));
  // word -> act: information in bits, against the same pairs shuffled
  const sh = wordAct.map(p => p[1]); for (let k = sh.length - 1; k > 0; k--) { const j = Math.floor(R.next() * (k + 1)); [sh[k], sh[j]] = [sh[j], sh[k]]; }
  const rt = (resp.rt || []).slice().sort((a, b) => a[0] - b[0]), third = Math.floor(rt.length / 3), topR = mean(rt.slice(-third).map(p => p[1])), botR = mean(rt.slice(0, third).map(p => p[1]));
  const at = (resp.rt || []); 
  const pr = (w) => { const L = (resp.rw || []).filter(p => p[0] === w); return L.length > 20 ? mean(L.map(p => p[1])) : NaN; };
  const anyTop = mean(rt.slice(-third).map(p => p[2])), anyBot = mean(rt.slice(0, third).map(p => p[2])), othTop = mean(rt.slice(-third).map(p => p[3])), othBot = mean(rt.slice(0, third).map(p => p[3]));
  const ot = (resp.ot || []).slice().sort((a, b) => a[0] - b[0]), t3 = Math.floor(ot.length / 3); const selfTop = mean(ot.slice(-t3).map(p => p[1])) / mean(ot.slice(-t3).map(p => p[2])), selfBot = mean(ot.slice(0, t3).map(p => p[1])) / mean(ot.slice(0, t3).map(p => p[2]));
  return { selfReachShareTrembling: selfTop, selfReachShareSteady: selfBot, anyActTop: anyTop, anyActBottom: anyBot, otherActsTop: othTop, otherActsBottom: othBot, reachTopThird: topR, reachBottomThird: botR, seenTrembleMean: mean(at.map(p => p[0])), reachWhenTrembling: mean(resp.rh || []), reachWhenSteady: mean(resp.rl || []), trembleAfterReach: dTr(resp.ra || []), trembleAfterNoReach: dTr(resp.rn || []), reachAfterRestless: pr('restless'), reachAfterCalm: pr('calm'), reachAfterBusy: pr('busy'), colourWhenTrembling: mean(resp.hi), colourWhenSteady: mean(resp.lo), wordActMI: mi(wordAct), wordActMIshuffled: mi(wordAct.map((p, k) => [p[0], sh[k]])), trembleAfterGiven: dTr(acted), trembleAfterNot: dTr(notActed), nGiven: acted.length, distress: mean(distress) };
}
module.exports = { run, mean };
if (require.main === module) {
  const conds = process.argv[2] ? JSON.parse(process.argv[2]) : [['stage 8 as is', {}], ['colours go to the one watched', { directed: true }]];
  const out = {};
  for (const [name, o] of conds) { const R = []; for (let seed = 1; seed <= 8; seed++) R.push(run({ seed, ...o }));
    const k = Object.keys(R[0]); out[name] = {}; k.forEach(q => out[name][q] = mean(R.map(r => r[q]))); out[name].answersTrembling = R.filter(r => r.colourWhenTrembling > r.colourWhenSteady).length + '/' + R.length; out[name].givenCalms = R.filter(r => r.trembleAfterGiven < r.trembleAfterNot).length + '/' + R.length; out[name].comforts = R.filter(r => r.reachTopThird > r.reachBottomThird).length + '/' + R.length; out[name].reachCalms = R.filter(r => r.trembleAfterReach < r.trembleAfterNoReach).length + '/' + R.length;
    console.log(name.padEnd(30), JSON.stringify(out[name], (q, v) => typeof v === 'number' ? Math.round(v * 1000) / 1000 : v)); require('fs').writeFileSync(process.argv[3] || 'test9.json', JSON.stringify(out)); }
}
