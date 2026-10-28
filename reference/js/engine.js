// ============================================================================
// Olvasó in a body (NewNeural, stage 7): an entity that reads itself through its outside, and now has a body the others can see
// The outside is the visitor: colours shown on the screen, typing rhythm, pointer, presence.
// The inside: four hidden quantities it never sees, felt only as scrambled channels.
// Purpose: explain itself. It can make marks (colours) that come back to it as outside.
// When the visitor is away, the sensory gate closes: it sleeps, keeping an unread trace.
// When woken, it re-reads the trace with whatever woke it: the report is written at waking.
// ============================================================================
const OL = {
  HUES: [8, 48, 140, 190, 228, 290], // degrees: the six colours both it and the visitor can show
  VOICES: false, RECALL: false, CONTAGION: 0, REACH: false, GAMMA: 0.8, COMPANY: 1, READ_CONTAGION: 0, NX: 18, NY: 8, NA: 12, NWORDS: 4, MAXC: 60, HEAR: 3, FEEL: 6, SALIENCE: 0, THR: 2.5,
  SET: [0.5, 0.7, 0.45, 0.15], W: [1, 1.5, 0.6, 0.5],
  TICK_MS: 250, PERIOD: 240, GMAX: 0.5, ASLEEP_AFTER_S: 45, TRACE_MAX: 320, REPORT_LEN: 80, H: 5, KAPPA: 0.3,
};
OL.XNAMES = ["screen hue (x)", "screen hue (y)", "screen colour strength", "typing rate", "vowel share of typing", "pointer speed", "pointer x", "pointer y", "your presence", "word heard (a)", "word heard (b)", "word heard (c)", "the other: size", "the other: trembling", "the other: reaching out", "the other: stirring", "its own body: size", "its own body: trembling"];
// stage 7: a body others can see. What shows of its inside: size (charge), trembling (unsteadiness), reaching out (contact), stirring (effort)
function bodyLook(h) { return [h[0], oclip((0.78 - h[1]) * 4, 0, 1), h[2], oclip(h[3] * 3, 0, 1)]; }
// a word reaches it as a sound with a fixed signature: three numbers from the word's letters, nothing about its meaning
// a voice: in a room, each speaker's words carry its own timbre, a small fixed shift of the sound (stage 6, when OL.VOICES is on)
function voiceCode(w, from) { const c = wordCode(w); if (from === null || from === undefined) return c; const r = new ORng(9973 + 7919 * (from + 1)); return c.map((v) => oclip(v + 0.12 * (r.next() * 2 - 1), 0, 1)); }
// stage 17: hearing can be finer. A sound is HEAR numbers; the first three sit at channels 9-11 as before, the rest after the body (18+)
function hearIdx(i) { return i < 3 ? 9 + i : 18 + (i - 3); }
function wordCode(w) { let h = 2166136261; for (const ch of w) { h ^= ch.codePointAt(0); h = Math.imul(h, 16777619) >>> 0; } const out = []; for (let i = 0; i < OL.HEAR; i++) { h ^= h >>> 13; h = Math.imul(h, 0x5bd1e995) >>> 0; out.push(0.1 + 0.8 * ((h >>> 8) / 16777216)); } return out; }
OL.HNAMES = ["charge", "steadiness", "contact", "effort"];

class ORng {
  constructor(s) { this.s = (s >>> 0) || 1; }
  next() { let t = (this.s += 0x6d2b79f5); t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }
  normal(m = 0, sd = 1) { const u = Math.max(1e-9, this.next()), v = this.next(); return m + sd * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); }
  choice(p) { let r = this.next(), c = 0; for (let i = 0; i < p.length; i++) { c += p[i]; if (r < c) return i; } return p.length - 1; }
}
const UNSEEN = new Set([12, 13, 14, 15]);
const oclip = (x, a, b) => Math.min(b, Math.max(a, x));
const osoftmax = (v) => { let m = -Infinity; for (const x of v) m = Math.max(m, x); const e = v.map((x) => Math.exp(x - m)); const s = e.reduce((a, b) => a + b, 0); return e.map((x) => x / s); };
const r3 = (x) => Math.round(x * 1000) / 1000;

class Entity {
  constructor(seed = Math.floor(Math.random() * 1e9)) {
    this.seed = seed; this.rng = new ORng(seed);
    const r = new ORng(seed ^ 0x5bd1e995);
    this.A = Array.from({ length: 6 }, () => Array.from({ length: 4 }, () => r.normal(0, 1.8)));
    this.c = Array.from({ length: 6 }, () => r.normal(0, 0.3));
    // stage 17: finer inner feeling: more scrambled channels from the same four hidden quantities (the first six as before)
    for (let j = 6; j < OL.FEEL; j++) { this.A.push(Array.from({ length: 4 }, () => r.normal(0, 1.8))); this.c.push(r.normal(0, 0.3)); }
    this.h = OL.SET.slice(); this.h[0] = 0.4;
    this.mu = []; this.vr = []; this.n = []; this.Q = []; this.F = []; this.T = [];
    this.age = 0; this.awakeTicks = 0; this.sleepTicks = 0; this.born = Date.now(); this.lastSeen = Date.now();
    this.screen = { hue: 0, str: 0, by: "none", vx: 0, vy: 0 };
    this.xavg = new Array(OL.NX).fill(0.5);
    this.gate = 1; this.mode = "awake"; // awake | falling | asleep | waking
    this.prev = 0; this.belief = null; this.felt = 0; this.hist = []; this.reading = -1;
    this.trace = []; this.reports = [];
    this.mirror = { own: null, you: null, others: null, nOwn: 0, nYou: 0, nOthers: 0 };
    this.marks = 0; this.youColours = 0;
    this.lastAct = 0; this.acted = 0;
    this.word = { code: [0.5, 0.5, 0.5], str: 0 }; this.lexicon = {}; this.hm = []; this.hueStats = OL.HUES.map(() => ({ n: 0, s: [0, 0, 0, 0], q: [0, 0, 0, 0] })); this.lastOwnMark = -999; this.lastOwnHue = -1; this.answers = 0; this.echoes = 0;
  }
  // ---------- concepts (online Gaussian clusters over [outside, inside])
  parts(x, k, skip) {
    const mu = this.mu[k], v = this.vr[k]; let a = 0, b = 0;
    for (let i = 0; i < x.length; i++) {
      if (skip && skip(i)) continue;
      const d = x[i] - mu[i], t = -0.5 * ((d * d) / v[i] + Math.log(2 * Math.PI * v[i]));
      if (i < OL.NX) a += t; else b += t;
    }
    return [a, b];
  }
  loglik(xe, xi, lE = 1) {
    const x = xe.concat(xi); let N = 0; for (const c of this.n) N += c; const miss = this.miss;
    return this.mu.map((_, k) => { const [a, b] = this.parts(x, k, miss ? (i) => miss.has(i) : null); return Math.log(this.n[k] / N) + lE * a + b; });
  }
  interpret(xe, xi, lE = 1) { return this.mu.length ? osoftmax(this.loglik(xe, xi, lE)) : []; }
  learn(xe, xi) {
    const x = xe.concat(xi);
    if (this.mu.length) {
      let k = 0, best = -Infinity;
      const miss = this.miss, sk = miss ? (i) => miss.has(i) : null, nm = miss ? miss.size : 0;
      for (let j = 0; j < this.mu.length; j++) { const [a, b] = this.parts(x, j, sk); if (a + b > best) { best = a + b; k = j; } }
      let ze = 0, zi = 0; const mu = this.mu[k], v = this.vr[k];
      for (let i = 0; i < x.length; i++) { if (sk && sk(i)) continue; const z = (x[i] - mu[i]) ** 2 / v[i]; if (i < OL.NX) ze += z; else zi += z; }
      const novel = Math.max(ze / (OL.NX - nm), zi / OL.NY);
      if (novel < OL.THR || this.mu.length >= OL.MAXC) {
        this.n[k] += 1; const sw = this.salienceW(xi); const lr = Math.min(0.5, Math.max(1 / this.n[k], 0.02) * sw), lv = Math.min(lr, 0.05 * sw);
        for (let i = 0; i < x.length; i++) { if (sk && sk(i)) continue; const d = x[i] - mu[i]; mu[i] += lr * d; v[i] = oclip((1 - lv) * v[i] + lv * d * d, 0.01, 0.5); }
        return k;
      }
    }
    const nx = x.slice(); if (this.miss && this.mu.length) for (const i of this.miss) { let s = 0, N = 0; this.mu.forEach((m, j) => { s += this.n[j] * m[i]; N += this.n[j]; }); nx[i] = s / N; }
    this.mu.push(nx); this.vr.push(x.map(() => 0.3)); this.n.push(1);
    this.Q.push(new Array(OL.NA).fill(0)); this.F.push(0.3);
    this.T.forEach((row) => row.push(0)); this.T.push(new Array(this.mu.length).fill(0));
    return this.mu.length - 1;
  }
  // stage 19: strong meanings. A moment that feels worse than usual is learned more strongly (arousal-weighted memory); 1 when off
  salienceW(xi) { if (!OL.SALIENCE) return 1; const f = xi[OL.NY - 1] / 3; if (this.fAvg === undefined) this.fAvg = f; const w = 1 + OL.SALIENCE * Math.max(0, f - this.fAvg); this.fAvg += 0.01 * (f - this.fAvg); return w; }
  // ---------- the inside: hidden, felt only through scrambled channels
  distress(h = this.h) { let s = 0; for (let i = 0; i < 4; i++) s += OL.W[i] * (h[i] - OL.SET[i]) ** 2; return Math.sqrt(s); }
  feel(acted) {
    const y = this.A.map((row, j) => Math.tanh(row.reduce((a, w, i) => a + w * (this.h[i] - 0.5), 0) + this.c[j]) + this.rng.normal(0, 0.08));
    y.push(acted + this.rng.normal(0, 0.1));           // the felt act (like a throat)
    y.push(3 * this.distress());                        // innate: how bad it feels
    return y;
  }
  // ---------- one tick awake
  outside(sense) {
    const s = this.screen.str, a = (this.screen.hue * Math.PI) / 180; // the colour on its screen: the sum of what arrived, fading
    const ws = this.word.str, wc = this.word.code;
    const x = [0.5 + 0.5 * Math.cos(a) * s, 0.5 + 0.5 * Math.sin(a) * s, s, sense.typing, sense.vowels, sense.speed, sense.px, sense.py, sense.presence, 0.5 + (wc[0] - 0.5) * ws, 0.5 + (wc[1] - 0.5) * ws, 0.5 + (wc[2] - 0.5) * ws];
    const seen = sense.seen || [0.5, 0.5, 0.5, 0.5], me = sense.noBody ? [0.5, 0.5] : bodyLook(this.h); x.push(seen[0], seen[1], seen[2], seen[3], me[0], me[1]); for (let i = 3; i < OL.HEAR; i++) x.push(0.5 + ((wc[i] === undefined ? 0.5 : wc[i]) - 0.5) * ws);
    return x.map((v) => v + this.rng.normal(0, 0.04));
  }
  bodyStep(x, acted) {
    const unseen = !!this.miss;
    let nov = 0; for (let i = 0; i < OL.NX; i++) { if (i < 12) nov += Math.abs(x[i] - this.xavg[i]); this.xavg[i] += 0.05 * (x[i] - this.xavg[i]); } nov /= 12;
    const h = this.h, pres = x[8];
    h[0] += 0.02 * (0.42 - h[0]) + 0.02 * Math.min(nov, 0.4);
    h[1] += 0.02 * (0.7 - h[1]) - 0.08 * Math.max(0, nov - 0.25);
    h[2] += 0.03 * (0.2 + 0.6 * pres - h[2]);
    h[3] = 0.85 * h[3] + 0.15 * acted;
    if (OL.CONTAGION && !unseen) h[1] -= OL.CONTAGION * (this.closeGain === undefined ? 1 : this.closeGain) * Math.max(0, x[13] - x[17] - 0.1); // stage 13: closeness scales how strongly the watched one's trembling reaches in // seeing another tremble more than itself unsettles it
    if (this.companyT > 0) { this.companyT--; if (OL.COMPANY_CONTACT) h[2] += 0.03 * (0.8 - h[2]); h[1] += Math.min(0.9, 0.02 * OL.COMPANY) * (0.7 - h[1]); } // company: another reached toward it; contact rises and it steadies // seeing another tremble unsettles it (stage 9): another's state reaches its inside only through its own outside
    this.h = h.map((v) => oclip(v + this.rng.normal(0, 0.003), 0, 1));
  }
  // mirror measure: how badly the screen colour fits what it expects from everything else
  screenSurprise(xe, xi) {
    if (!this.mu.length) return null;
    const x = xe.concat(xi); let best = -Infinity, kb = 0;
    for (let k = 0; k < this.mu.length; k++) { const [a, b] = this.parts(x, k, (i) => i < 3); const ll = Math.log(this.n[k]) + a + b; if (ll > best) { best = ll; kb = k; } }
    const z = (x[2] - this.mu[kb][2]) ** 2 / this.vr[kb][2];
    return Math.min(z, 30);
  }
  addColour(hueDeg, by) {
    const a = (hueDeg * Math.PI) / 180, sc = this.screen;
    sc.vx = (sc.vx || 0) + Math.cos(a); sc.vy = (sc.vy || 0) + Math.sin(a);
    sc.str = Math.min(1, sc.str + 1); sc.hue = ((Math.atan2(sc.vy, sc.vx) * 180) / Math.PI + 360) % 360; sc.by = by;
  }
  fadeScreen() { const sc = this.screen; sc.str *= 0.93; sc.vx = (sc.vx || 0) * 0.93; sc.vy = (sc.vy || 0) * 0.93; }
  qv(b, a) { let s = 0; for (let k = 0; k < b.length; k++) s += b[k] * this.Q[k][a]; return s; }
  // sense = {typing, vowels, speed, px, py, presence}; userColour = hue index or null; returns what it did
  // incoming = hues (degrees) the other Olvasós put on their screens last tick: their output is its input
  // the words it can say: the ones it has heard most (from you or the others), up to four
  topWords() { return Object.keys(this.lexicon).sort((p, q) => this.lexicon[q] - this.lexicon[p] || (p < q ? -1 : 1)).slice(0, OL.NWORDS); }
  // incomingWords = words the others said last tick; they reach it as sounds, like yours
  tick(sense, userColour = null, word = null, incoming = [], incomingWords = []) {
    this.age++;
    let voice = null;
    if (!word && incomingWords.length) { const iw = incomingWords[0]; if (typeof iw === "string") word = iw; else { word = iw.w; voice = OL.VOICES ? iw.from : null; } }
    if (word) { this.word = { code: voiceCode(word, voice), str: 1 }; this.heardFrom = voice; this.lexicon[word] = (this.lexicon[word] || 0) + 1; const ks = Object.keys(this.lexicon); if (ks.length > 60) { ks.sort((p, q) => this.lexicon[p] - this.lexicon[q]); delete this.lexicon[ks[0]]; } }
    const came = new Set();
    if (incoming.length) { incoming.forEach((h) => this.addColour(h, "others")); came.add("others"); this.othersColours = (this.othersColours || 0) + incoming.length; }
    if (userColour !== null) { this.addColour(OL.HUES[userColour], "you"); came.add("you"); this.youColours++; if (this.age - this.lastOwnMark <= 12) { this.answers++; if (OL.HUES[userColour] === this.lastOwnHue) this.echoes++; } }
    let act = 0;
    const awake = this.mode === "awake";
    if (awake && this.belief && this.belief.length) {
      const v = []; for (let a = 0; a < OL.NA; a++) v.push(this.qv(this.belief, a) / 0.05);
      act = this.rng.choice(osoftmax(v));
      if (act === 11) { if (!OL.REACH) act = 0; } // stage 9: reaching toward the one it watches
      else if (act >= 7) { const w = OL.RECALL ? this.recallWord() : this.topWords()[act - 7]; if (!w || word || this.mute) act = 0; else this.say(w); }
      else if (act > 0 && userColour === null) { this.addColour(OL.HUES[act - 1], "self"); came.add("self"); this.marks++; this.lastOwnMark = this.age; this.lastOwnHue = OL.HUES[act - 1]; const hs = this.hueStats[act - 1]; hs.n++; for (let i = 0; i < 4; i++) { hs.s[i] += this.h[i]; hs.q[i] += this.h[i] ** 2; } }
      else if (act > 0) act = 0;
    }
    const acted = act > 0 ? 1 : 0;
    const fresh = came.size === 1 ? [...came][0] : null; // a colour from one source only: measure the surprise
    this.miss = sense.unseen ? UNSEEN : null; // stage 18: the other out of sight: its four seen channels are missing, not grey
    const xReal = this.outside(sense);
    if (this.mode !== "awake") return this.sleepTick(xReal, sense);
    this.bodyStep(xReal, acted);
    const xi = this.feel(acted);
    if (fresh) {
      const s = this.screenSurprise(xReal, xi);
      if (s !== null) { const m = this.mirror, key = fresh === "self" ? "own" : fresh === "you" ? "you" : "others", w = key + "W"; m[w] = (m[w] || []).concat([Math.round(s * 100) / 100]).slice(-60); m[key] = m[w].reduce((p, q) => p + q, 0) / m[w].length; const nk = key === "own" ? "nOwn" : key === "you" ? "nYou" : "nOthers"; m[nk] = (m[nk] || 0) + 1; }
    }
    const k = this.learn(xReal, xi); const b2 = this.interpret(xReal, xi);
    // stage 14: what it reads moves its body. If the patterns it reads itself as expect the watched one to tremble more than itself, that unsettles it, as seeing would
    if (OL.READ_CONTAGION && b2.length) { let ex = 0; b2.forEach((p, j) => (ex += p * this.mu[j][13])); this.h[1] = oclip(this.h[1] - OL.READ_CONTAGION * Math.max(0, ex - xReal[17] - 0.1), 0, 1); }
    if (this.T[this.prev]) this.T[this.prev][k] += 1;
    const felt = xi[OL.NY - 1] / 3;
    // learning what to do: feel better, and forecast its own feelings well (its wish to understand itself)
    this.hist.push(this.belief || b2); let clar = 0;
    if (this.hist.length > OL.H) { const bo = this.hist.shift(); let pr = 0; bo.forEach((p, j) => (pr += p * this.F[j])); const e = felt - pr; bo.forEach((p, j) => (this.F[j] += 0.05 * p * e)); clar = Math.abs(e); this.lastClar = clar; }
    if (this.belief && this.belief.length) {
      const r = 10 * (this.felt - felt) - 0.1 * felt - OL.KAPPA * 10 * clar; this.lastR = { r, dfelt: this.felt - felt, clar, act }; let mx = -Infinity;
      for (let a = 0; a < OL.NA; a++) mx = Math.max(mx, this.qv(b2, a));
      const cur = this.qv(this.belief, act), tg = r + OL.GAMMA * mx;
      for (let j = 0; j < this.belief.length; j++) this.Q[j][act] += 0.1 * this.belief[j] * (tg - cur);
    }
    // observer's record: the hidden state that goes with each pattern (the entity never uses this)
    while (this.hm.length < this.mu.length) this.hm.push({ n: 0, h: this.h.slice() });
    { const m = this.hm[k]; m.n++; const lr = Math.max(1 / m.n, 0.02); for (let i = 0; i < 4; i++) m.h[i] += lr * (this.h[i] - m.h[i]); }
    this.belief = b2; this.felt = felt; this.prev = k; this.reading = k; this.awakeTicks++;
    this.fadeScreen(); this.word.str *= 0.95;
    return { act, reading: k, x: xReal, y: xi, said: act >= 7 && act <= 10 ? this.said : null, reached: act === 11 };
  }
  // ---------- the sensory gate and sleep
  updateGate(absentS) {
    if (this.mode === "awake" && absentS > OL.ASLEEP_AFTER_S) this.mode = "falling";
    if (this.mode === "asleep") { const ph = (this.sleepTicks % OL.PERIOD) / OL.PERIOD; this.gate = 0.03 + OL.GMAX * (0.5 - 0.5 * Math.cos(2 * Math.PI * ph)) ** 2; }
    if (this.mode === "falling") { this.gate = Math.max(0.03, this.gate - 0.012); if (this.gate <= 0.05) { this.mode = "asleep"; this.sleepTicks = 0; } if (absentS < 2) this.mode = "awake", (this.gate = 1); }
    if (this.mode === "waking") { this.gate = Math.min(1, this.gate + 0.12); if (this.gate >= 1) this.mode = "awake"; }
  }
  imagined(prev) {
    const row = this.T[prev] || [], tot = row.reduce((a, b) => a + b, 0) + 0.01 * this.mu.length;
    const out = new Array(OL.NX).fill(0);
    this.mu.forEach((m, j) => { const p = ((row[j] || 0) + 0.01) / tot; for (let i = 0; i < OL.NX; i++) out[i] += p * m[i]; });
    return out;
  }
  sleepTick(xReal, sense) {
    // asleep: the body drifts back to rest, with slow restless spells; nothing is decided; the gate lets a little in
    const t = this.sleepTicks++;
    const wander = [0.2 * Math.sin(t / 47), 0.18 * Math.sin(t / 71 + 1), 0.15 * Math.sin(t / 29 + 2), 0.05 * Math.sin(t / 19)];
    this.h = this.h.map((v, i) => oclip(v + 0.05 * (OL.SET[i] + wander[i] - v) + this.rng.normal(0, 0.01), 0, 1));
    const xi = this.feel(0);
    const g = this.gate, im = this.imagined(this.prev);
    const x = xReal.map((v, i) => g * v + (1 - g) * im[i] + this.rng.normal(0, 0.1));
    let k = this.prev;
    if (this.mu.length) {
      const row = this.T[this.prev] || [], ll = this.loglik(x, xi);
      const tot = row.reduce((a, b) => a + b, 0) + 0.01 * this.mu.length;
      const p = osoftmax(ll.map((l, j) => l + Math.log(((row[j] || 0) + 0.01) / tot)));
      k = this.rng.choice(p);
    }
    this.prev = k; this.reading = k;
    this.trace.push({ y: xi.map(r3), k, g: r3(g) }); if (this.trace.length > OL.TRACE_MAX) this.trace.shift();
    this.fadeScreen(); this.word.str *= 0.95;
    return { act: 0, reading: k, x, y: xi };
  }
  // fast-forward the time it was away (page closed): sleep, compressed
  sleepFor(seconds, sense) {
    const n = Math.min(Math.round(seconds * 0.5), 900); if (n <= 0) return 0;
    if (this.mode === "awake") this.mode = "asleep";
    for (let i = 0; i < n; i++) { this.updateGate(1e9); this.sleepTick(this.outside(sense), sense); }
    return n;
  }
  // woken: re-read the last stretch of the trace with the waking world as dictionary
  wake(xCue, cueLabel) {
    const seg = this.trace.slice(-OL.REPORT_LEN);
    this.mode = "waking";
    if (!seg.length || !this.mu.length) return null;
    const dreamt = seg.map((s) => s.k); const report = []; let prev = dreamt[0];
    for (const s of seg) {
      const im = this.imagined(prev); const x = xCue.map((v, i) => 0.7 * v + 0.3 * im[i]);
      const ll = this.loglik(x, s.y); let b = 0; for (let j = 1; j < ll.length; j++) if (ll[j] > ll[b]) b = j;
      report.push(b); prev = b;
    }
    const rep = { at: Date.now(), cue: cueLabel, dreamt: stab(dreamt), report: stab(report) };
    this.reports.unshift(rep); this.reports = this.reports.slice(0, 6);
    return rep;
  }
  // a concept's look: the colour it expects on the screen (or grey when it expects none)
  conceptHue(k) { const m = this.mu[k]; const cx = m[0] - 0.5, cy = m[1] - 0.5; return { hue: ((Math.atan2(cy, cx) * 180) / Math.PI + 360) % 360, str: oclip(Math.hypot(cx, cy) * 2, 0, 1) }; }
  // speaking: it puts one of its words on its screen; it hears it itself (with the feel of acting), and so do the others
  say(w) {
    const sp = this.speech || (this.speech = { n: 0, fit: 0, base: 0, nb: 0, words: {} });
    const err = (r) => r ? r.ev.reduce((a, v, i) => a + Math.abs(v - this.h[i]), 0) / 4 : null;
    const mine = err(this.evokeWord(w)); const others = this.topWords().filter((x) => x !== w).map((x) => err(this.evokeWord(x))).filter((x) => x !== null);
    if (mine !== null && others.length) { sp.fit += mine; sp.base += others.reduce((a, b) => a + b, 0) / others.length; sp.nb++; }
    sp.n++; sp.words[w] = (sp.words[w] || 0) + 1; this.said = w; this.saidAt = this.age;
    if (this.speechLog) this.speechLog.push({ t: this.age, w, mine, others: others.length ? others.reduce((a, b) => a + b, 0) / others.length : null });
    if (!this.deaf) this.word = { code: voiceCode(w, OL.VOICES ? this.voice : null), str: 1 }; // deaf: it speaks but does not hear itself
  }
  // what a word calls up: the patterns its sound alone points to, and the inner state those go with (observer's view)
  evokeWord(w, code = wordCode(w)) {
    if (!this.mu.length) return null;
    const x = code.map((c) => 0.5 + (c - 0.5)); let N = 0; for (const c of this.n) N += c;
    const ll = this.mu.map((m, k) => { let a = Math.log(this.n[k] / N); for (let i = 0; i < OL.HEAR; i++) { const q = hearIdx(i), d = x[i] - m[q], v = this.vr[k][q]; a += -0.5 * ((d * d) / v + Math.log(2 * Math.PI * v)); } return a; });
    const p = osoftmax(ll); let top = 0; p.forEach((q, k) => { if (q > p[top]) top = k; });
    const ev = [0, 0, 0, 0]; p.forEach((q, k) => { const hm = this.hm[k] ? this.hm[k].h : OL.SET; for (let i = 0; i < 4; i++) ev[i] += q * hm[i]; });
    // the same, for an unfamiliar sound: what any word would call up
    const base = [0, 0, 0, 0]; let tot = 0; this.hm.forEach((m, k) => { for (let i = 0; i < 4; i++) base[i] += this.n[k] * m.h[i]; tot += this.n[k]; }); if (tot) for (let i = 0; i < 4; i++) base[i] /= tot;
    const heard = this.lexicon[w] || 0; let sharp = 0; p.forEach((q) => { sharp += q * q; });
    return { word: w, heard, top, ev, base, sharp };
  }
  company(ticks = 20) { this.companyT = Math.max(this.companyT || 0, ticks); }
  // stage 8: the word that comes to mind. Whether to speak is learned; which word comes is recall: the one of its words whose sound
  // goes best with the patterns it reads itself as right now
  recallWord() {
    const ws = this.topWords(); if (!ws.length || !this.belief || !this.belief.length) return null; let best = null, bs = -Infinity;
    for (const w of ws) { const c = wordCode(w); let sc = 0; this.belief.forEach((b, k) => { if (b < 1e-4) return; let a = 0; for (let i = 0; i < OL.HEAR; i++) { const q = hearIdx(i), dd = c[i] - this.mu[k][q], v = this.vr[k][q]; a += -0.5 * ((dd * dd) / v + Math.log(2 * Math.PI * v)); } sc += b * a; }); if (sc > bs) { bs = sc; best = w; } }
    return best;
  }
  // what a word leads it to expect to see of the one it is looking at (observer's view): channels 12-15
  expectSeen(w, code = wordCode(w)) {
    if (!this.mu.length) return null; let N = 0; for (const c of this.n) N += c;
    const ll = this.mu.map((m, k) => { let a = Math.log(this.n[k] / N); for (let i = 0; i < OL.HEAR; i++) { const q = hearIdx(i), d = code[i] - m[q], v = this.vr[k][q]; a += -0.5 * ((d * d) / v + Math.log(2 * Math.PI * v)); } return a; });
    const p = osoftmax(ll), out = [0, 0, 0, 0]; p.forEach((q, k) => { for (let i = 0; i < 4; i++) out[i] += q * this.mu[k][12 + i]; }); return out;
  }
  // how much its colour choices go with different inner states: 0 = not at all, 1 = completely (observer's view)
  colourMeaning() {
    const used = this.hueStats.filter((s) => s.n >= 5); if (used.length < 2) return { tied: null, used: used.length };
    let n = 0; const tot = [0, 0, 0, 0], tq = [0, 0, 0, 0]; used.forEach((s) => { n += s.n; for (let i = 0; i < 4; i++) { tot[i] += s.s[i]; tq[i] += s.q[i]; } });
    let between = 0, total = 0;
    for (let i = 0; i < 4; i++) { const m = tot[i] / n; total += tq[i] / n - m * m; used.forEach((s) => { between += (s.n / n) * (s.s[i] / s.n - m) ** 2; }); }
    return { tied: total > 1e-9 ? between / total : 0, used: used.length };
  }
  // ---------- saving
  toJSON() {
    return { v: 7, seed: this.seed, rng: this.rng.s, A: this.A, c: this.c, h: this.h.map(r3), mu: this.mu.map((m) => m.map(r3)), vr: this.vr.map((m) => m.map(r3)), n: this.n, Q: this.Q.map((q) => q.map(r3)), F: this.F.map(r3), T: this.T,
      age: this.age, awakeTicks: this.awakeTicks, sleepTicks: this.sleepTicks, born: this.born, lastSeen: Date.now(), xavg: this.xavg.map(r3), mode: this.mode === "awake" ? "awake" : "asleep", prev: this.prev,
      trace: this.trace, reports: this.reports, mirror: this.mirror, marks: this.marks, youColours: this.youColours, othersColours: this.othersColours || 0, savedAt: Date.now(),
      lexicon: this.lexicon, speech: this.speech || null, name: this.name || null, guest: !!this.guest, deaf: !!this.deaf, readStats: this.readStats || null, moved: this.moved || null, hm: this.hm.map((m) => ({ n: m.n, h: m.h.map(r3) })), hueStats: this.hueStats.map((s) => ({ n: s.n, s: s.s.map(r3), q: s.q.map(r3) })), answers: this.answers, echoes: this.echoes };
  }
  static fromJSON(o) {
    const e = new Entity(o.seed); Object.assign(e, { A: o.A, c: o.c, h: o.h, mu: o.mu, vr: o.vr, n: o.n, Q: o.Q, F: o.F, T: o.T, age: o.age, awakeTicks: o.awakeTicks, sleepTicks: o.sleepTicks, born: o.born, lastSeen: o.lastSeen, xavg: o.xavg, mode: o.mode, prev: o.prev, trace: o.trace || [], reports: o.reports || [], mirror: o.mirror, marks: o.marks || 0, youColours: o.youColours || 0, othersColours: o.othersColours || 0 });
    if ((o.v || 1) < 2) { // stage 2 entity: give it ears for words (three new outside channels, quiet so far)
      e.mu = e.mu.map((m) => m.slice(0, 9).concat([0.5, 0.5, 0.5], m.slice(9)));
      e.vr = e.vr.map((m) => m.slice(0, 9).concat([0.3, 0.3, 0.3], m.slice(9)));
      e.xavg = (e.xavg || []).slice(0, 9).concat([0.5, 0.5, 0.5]);
    } else Object.assign(e, { name: o.name || null, guest: !!o.guest, deaf: !!o.deaf, readStats: o.readStats || null, moved: o.moved || null, speech: o.speech || null, lexicon: o.lexicon || {}, hm: o.hm || [], hueStats: o.hueStats || e.hueStats, answers: o.answers || 0, echoes: o.echoes || 0 });
    e.Q = e.Q.map((q) => q.length < OL.NA ? q.concat(new Array(OL.NA - q.length).fill(0)) : q); // stage 5: room for speaking
    e.rng = new ORng(o.rng); e.gate = o.mode === "awake" ? 1 : 0.04; e.savedAt = o.savedAt; return e;
  }
}
function stab(r, hold = 3) { const s = r.slice(); let i = 0; while (i < s.length) { let j = i; while (j < s.length && r[j] === r[i]) j++; if (j - i < hold && i > 0) for (let q = i; q < j; q++) s[q] = s[i - 1]; i = j; } return s; }
function stageOK(o) { return o && o.v === 7; }
if (typeof module !== "undefined") module.exports = { Entity, OL, ORng, stab, wordCode, voiceCode, bodyLook, hearIdx };
