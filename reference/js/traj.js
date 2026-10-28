// a fixed little world: two Olvasós watching each other, visitor words and colours, jolts. Dump every step.
const { Entity, OL, ORng, bodyLook } = require(process.argv[2]);
Object.assign(OL, { RECALL: true, CONTAGION: 0.05, REACH: true, GAMMA: 0.8, COMPANY: 1, READ_CONTAGION: 0.05 });
const es = [new Entity(101), new Entity(102)]; const R = new ORng(5); let pres = 0, prevC = [null, null], prevW = [null, null]; const out = [];
const T = +process.argv[3];
for (let t = 0; t < T; t++) {
  const active = t % 600 < 420; pres = active ? Math.min(.8, pres + .05) : pres * .985;
  let word = null, col = null;
  if (active && R.next() < 0.05) word = ['busy', 'restless', 'calm', 'still'][Math.floor(R.next() * 4)];
  if (active && R.next() < 0.02) col = Math.floor(R.next() * 6);
  const looks = es.map(e => bodyLook(e.h)); const cs = [], ws = [];
  es.forEach((e, i) => {
    if (R.next() < 0.004) { for (let k = 0; k < 3; k++) e.addColour(OL.HUES[2], 'you'); e.h[1] = Math.max(0, e.h[1] - 0.25); }
    const w = 1 - i; const r = e.tick({ typing: word ? .4 : 0, vowels: .4, speed: .1, px: .5, py: .5, presence: pres, seen: looks[w] }, col, word, prevC[w] !== null ? [prevC[w]] : [], prevW[w] ? [prevW[w]] : []);
    if (r.act === 11) es[w].company();
    out.push([t, i, r.act, r.reading, ...e.h]);
    cs.push(r.act > 0 && r.act < 7 ? OL.HUES[r.act - 1] : null); ws.push(r.said);
  });
  prevC = cs; prevW = ws;
}
console.log(JSON.stringify(out));
