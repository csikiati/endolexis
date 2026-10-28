// ============================================================================
// NewNeural simulation engine (JavaScript port of the Python experiments)
// ============================================================================

// ---------- random numbers (seeded, reproducible)
class RNG {
  constructor(seed) { this.a = (seed * 2654435761) >>> 0 || 1; this.spare = null; }
  next() {
    let a = (this.a = (this.a + 0x6d2b79f5) | 0);
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }
  normal(m = 0, s = 1) {
    if (this.spare !== null) { const v = this.spare; this.spare = null; return m + s * v; }
    let u, v, r;
    do { u = this.next() * 2 - 1; v = this.next() * 2 - 1; r = u * u + v * v; } while (r === 0 || r >= 1);
    const f = Math.sqrt((-2 * Math.log(r)) / r);
    this.spare = v * f;
    return m + s * u * f;
  }
  normals(n, m = 0, s = 1) { const a = new Array(n); for (let i = 0; i < n; i++) a[i] = this.normal(m, s); return a; }
  int(n) { return Math.floor(this.next() * n); }
  choice(p) { let r = this.next(), c = 0; for (let i = 0; i < p.length; i++) { c += p[i]; if (r < c) return i; } return p.length - 1; }
}

const clip = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
const argmax = (a) => { let b = 0; for (let i = 1; i < a.length; i++) if (a[i] > a[b]) b = i; return b; };
const mean = (a) => (a.length ? a.reduce((s, x) => s + x, 0) / a.length : NaN);
const softmax = (ll) => { const m = Math.max(...ll); const e = ll.map((v) => Math.exp(v - m)); const s = e.reduce((x, y) => x + y, 0); return e.map((v) => v / s); };
const corr = (a, b) => {
  const ma = mean(a), mb = mean(b); let sab = 0, saa = 0, sbb = 0;
  for (let i = 0; i < a.length; i++) { sab += (a[i] - ma) * (b[i] - mb); saa += (a[i] - ma) ** 2; sbb += (b[i] - mb) ** 2; }
  return saa < 1e-12 || sbb < 1e-12 ? 0 : sab / Math.sqrt(saa * sbb);
};
const rankCorr = (a, b) => {
  const rk = (v) => { const idx = v.map((x, i) => [x, i]).sort((p, q) => p[0] - q[0]); const r = new Array(v.length); idx.forEach((p, i) => (r[p[1]] = i)); return r; };
  return corr(rk(a), rk(b));
};
const tick = () => new Promise((r) => setTimeout(r, 0));

// ---------- the concept-forming interpreter (shared by both worlds)
class Agent {
  constructor(ed, { maxC = 24, thr = 4.0, seed = 0 } = {}) {
    this.ed = ed; this.maxC = maxC; this.thr = thr;
    this.mu = []; this.vr = []; this.n = [];
    this.trans = new Map(); this.rng = new RNG(seed + 777); this.learning = true;
  }
  parts(x, k) {
    const mu = this.mu[k], v = this.vr[k]; let a = 0, b = 0;
    for (let i = 0; i < x.length; i++) {
      const d = x[i] - mu[i];
      const t = -0.5 * ((d * d) / v[i] + Math.log(2 * Math.PI * v[i]));
      if (i < this.ed) a += t; else b += t;
    }
    return [a, b];
  }
  loglik(xe, xi, lE = 1, lI = 1) {
    const x = xe.concat(xi); let N = 0; for (const c of this.n) N += c;
    return this.mu.map((_, k) => { const [a, b] = this.parts(x, k); return Math.log(this.n[k] / N) + lE * a + lI * b; });
  }
  interpret(xe, xi, lE = 1, lI = 1) { return softmax(this.loglik(xe, xi, lE, lI)); }
  learn(xe, xi) {
    const x = xe.concat(xi);
    if (this.mu.length) {
      if (!this.learning) return argmax(this.interpret(xe, xi));
      let k = 0, best = -Infinity;
      for (let j = 0; j < this.mu.length; j++) { const [a, b] = this.parts(x, j); if (a + b > best) { best = a + b; k = j; } }
      let ze = 0, zi = 0; const mu = this.mu[k], v = this.vr[k];
      for (let i = 0; i < x.length; i++) { const z = (x[i] - mu[i]) ** 2 / v[i]; if (i < this.ed) ze += z; else zi += z; }
      const novel = Math.max(ze / this.ed, zi / (x.length - this.ed));
      if (novel < this.thr || this.mu.length >= this.maxC) {
        this.n[k] += 1;
        const lr = Math.max(1 / this.n[k], 0.02), lv = Math.min(lr, 0.05);
        for (let i = 0; i < x.length; i++) {
          const d = x[i] - mu[i]; mu[i] += lr * d;
          v[i] = clip((1 - lv) * v[i] + lv * d * d, 0.01, 0.5);
        }
        return k;
      }
    }
    this.mu.push(x.slice()); this.vr.push(x.map(() => 0.3)); this.n.push(1);
    return this.mu.length - 1;
  }
  // simple world: learn how felt badness changed after each move, from each self-reading
  record(cur, a, delta) {
    if (cur === null || delta === null) return;
    const key = cur + "|" + a; const [n, m] = this.trans.get(key) || [0, 0];
    this.trans.set(key, [n + 1, m + (delta - m) / (n + 1)]);
  }
  choose(cur, nA, beta = 0.15, temp = 0.05) {
    const v = [];
    for (let a = 0; a < nA; a++) { const [n, m] = this.trans.get(cur + "|" + a) || [0, 0]; v.push((-m + beta / Math.sqrt(1 + n)) / temp); }
    return this.rng.choice(softmax(v));
  }
  muExt() { return this.mu.map((m) => m.slice(0, this.ed)); }
}

// ============================================================================
// SIMPLE WORLD (newneural_agent.py)
// ============================================================================
const S = { ENERGY: 0, WARMTH: 1, WATER: 2, EXT: 6, SET: [0.6, 0.6, 0.6], DWELL: 4 };
const WORLDS = {
  meadow: { name: "Meadow", places: ["sun rock", "shade", "pond", "berry bush", "open field"],
    effects: [[0, 0.04, -0.03], [0, -0.02, 0], [0, -0.03, 0.05], [0.05, 0, -0.01], [-0.01, 0.01, -0.01]] },
  mountain: { name: "Mountain", places: ["hot spring", "cold wind", "warm cave", "snow field", "berry bush"],
    effects: [[0, 0.06, 0.03], [0, -0.05, -0.01], [0, 0.03, 0], [-0.01, -0.03, 0.02], [0.05, 0, -0.01]] },
};

class World {
  constructor(kind, seed) {
    const spec = WORLDS[kind]; this.kind = kind; this.places = spec.places; this.effects = spec.effects;
    const r = new RNG(seed); this.protos = spec.places.map(() => r.normals(S.EXT));
    this.rng = new RNG(seed + 100);
  }
  observe(ctx, clarity = 1, noise = 0.3) {
    const p = this.protos[ctx];
    return p.map((v) => clarity * v + (1 - clarity) * this.rng.normal() + this.rng.normal(0, noise));
  }
}

class Body {
  constructor(nervesSeed = 42, seed = 0) {
    const r = new RNG(nervesSeed);
    this.A = Array.from({ length: 10 }, () => r.normals(3, 0, 1.8));
    this.c = r.normals(10, 0, 0.5);
    this.rng = new RNG(seed + 31); this.s = S.SET.slice(); this.t = 0;
  }
  static distress(s) { return Math.sqrt(s.reduce((a, v, i) => a + (v - S.SET[i]) ** 2, 0)); }
  step(eff) {
    const s = this.s;
    const amb = [0, 0.02 * (0.45 - s[1]), 0];
    const met = [-0.008, 0, -0.008];
    this.s = s.map((v, i) => clip(v + eff[i] + met[i] + amb[i] + this.rng.normal(0, 0.005), 0, 1));
    this.t += 1;
  }
  feel(state = null, noise = 0.05) {
    const s = state || this.s;
    const raw = this.A.map((row, j) => Math.tanh(row[0] * (s[0] - 0.5) + row[1] * (s[1] - 0.5) + row[2] * (s[2] - 0.5) + this.c[j]));
    raw[0] += 0.3 * Math.sin(this.t / 3); raw[1] += 0.3 * Math.sin(this.t / 3);
    for (let i = 0; i < raw.length; i++) raw[i] += this.rng.normal(0, noise);
    raw.push(3 * Body.distress(s));
    return raw;
  }
}

const cache = new Map();
async function raiseSimple(kind, steps, seed, policy = "self", onProgress = null) {
  const key = [kind, steps, seed, policy].join("|");
  if (cache.has(key)) return cache.get(key);
  const world = new World(kind, seed), body = new Body(42, seed), agent = new Agent(S.EXT, { maxC: 24, thr: 4.0, seed });
  const rng = new RNG(seed + 5);
  let ctx = rng.int(5), cur = null, prevCur = null, prevA = null, felt = null, feltBefore = null;
  const log = { ctx: [], concept: [], body: [], distress: [] };
  for (let t = 0; t < steps; t++) {
    if (t % S.DWELL === 0) {
      if (feltBefore !== null) agent.record(prevCur, prevA, felt - feltBefore);
      feltBefore = felt;
      const a = policy === "self" && cur !== null ? agent.choose(cur, 5) : rng.int(5);
      prevCur = cur; prevA = a; ctx = a;
    }
    body.step(world.effects[ctx]);
    const xi = body.feel(); felt = xi[xi.length - 1];
    cur = agent.learn(world.observe(ctx), xi);
    log.ctx.push(ctx); log.concept.push(cur); log.body.push(body.s.slice()); log.distress.push(Body.distress(body.s));
    if (t % 1500 === 0) { if (onProgress) onProgress(t / steps); await tick(); }
  }
  const out = indexSimple({ world, body, agent, log });
  cache.set(key, out);
  return out;
}

function indexSimple(ctx) {
  const { agent, log, world } = ctx; const K = agent.mu.length;
  const bodyOf = [], placeOf = [], labels = [];
  for (let k = 0; k < K; k++) {
    const idx = []; log.concept.forEach((c, i) => { if (c === k) idx.push(i); });
    if (!idx.length) { bodyOf.push([NaN, NaN, NaN]); placeOf.push(-1); labels.push("unused"); continue; }
    const b = [0, 0, 0], cnt = new Array(world.places.length).fill(0);
    idx.forEach((i) => { for (let j = 0; j < 3; j++) b[j] += log.body[i][j] / idx.length; cnt[log.ctx[i]]++; });
    bodyOf.push(b); const pl = argmax(cnt); placeOf.push(pl);
    const lvl = (v) => (v < 0.4 ? "low" : v > 0.78 ? "high" : null);
    const flags = ["energy", "warmth", "water"].map((n, j) => (lvl(b[j]) ? `${n} ${lvl(b[j])}` : null)).filter(Boolean);
    labels.push(`${world.places[pl]}${flags.length ? ", " + flags.join(", ") : ""}`);
  }
  const seen = new Set(); for (let i = 1; i < log.concept.length; i++) if (log.concept[i] !== log.concept[i - 1]) seen.add(log.concept[i - 1] + "|" + log.concept[i]);
  const T = Array.from({ length: K }, () => new Array(K).fill(0.01));
  for (let i = 1; i < log.concept.length; i++) T[log.concept[i - 1]][log.concept[i]] += 1;
  T.forEach((row) => { const s = row.reduce((a, b) => a + b, 0); for (let j = 0; j < K; j++) row[j] /= s; });
  return Object.assign(ctx, { K, bodyOf, placeOf, labels, seen, T });
}

// ---------- experiment 2: same body, two dictionaries
function dictionaryMap(ctx, n = 30) {
  const probe = new Body(42, 999), agent = ctx.agent; agent.learning = false;
  const M = [];
  for (let i = 0; i < n; i++) {
    const water = 0.05 + (0.9 * i) / (n - 1); const row = [];
    for (let j = 0; j < n; j++) {
      const warmth = 0.05 + (0.9 * j) / (n - 1); probe.t = 0;
      row.push(argmax(agent.interpret(new Array(S.EXT).fill(0), probe.feel([0.6, warmth, water], 0), 0)));
    }
    M.push(row);
  }
  probe.t = 0;
  const probeK = argmax(agent.interpret(new Array(S.EXT).fill(0), probe.feel([0.6, 0.3, 0.75], 0), 0));
  return { M, probeK };
}

// ---------- experiment 3: waking up
function waking(ctx, placeIdx, steps = 40) {
  const { agent, log, world } = ctx; agent.learning = false;
  const body = new Body(42, 4242);
  const st = [0, 0, 0]; let c = 0; log.ctx.forEach((p, i) => { if (p === placeIdx) { c++; for (let j = 0; j < 3; j++) st[j] += log.body[i][j]; } });
  body.s = c ? st.map((v) => v / c) : S.SET.slice();
  const clarity = [], posts = [];
  for (let t = 0; t < steps; t++) {
    const cl = 1 / (1 + Math.exp(-(t - steps * 0.55) / (steps / 13)));
    body.t += 1;
    posts.push(agent.interpret(world.observe(placeIdx, cl), body.feel(), cl * cl, 1));
    clarity.push(cl);
  }
  return { clarity, posts, truth: body.s.slice() };
}

// ---------- shared sleep helpers
const stabilize = (r, minHold = 3) => {
  const runs = []; for (const k of r) { if (runs.length && runs[runs.length - 1][0] === k) runs[runs.length - 1][1]++; else runs.push([k, 1]); }
  const out = []; let cur = runs[0][0];
  for (const [k, n] of runs) { if (n >= minHold) cur = k; for (let i = 0; i < n; i++) out.push(cur); }
  return out;
};
const sceneCount = (r) => { const s = stabilize(r); let n = 1; for (let i = 1; i < s.length; i++) if (s[i] !== s[i - 1]) n++; return n; };
const gateAt = (t, gmax, period) => gmax * (0.5 - 0.5 * Math.cos((2 * Math.PI * t) / period)) ** 2;

function sleepBody(ctx, seed) {
  const body = new Body(42, seed + 7);
  const last = ctx.log.body[ctx.log.body.length - 1].slice();
  last[0] = Math.max(last[0], 0.6); last[2] = Math.max(last[2], 0.6);
  body.s = last; return body;
}

// ---------- experiment 4: dreaming at a fixed gate (dream.py)
const NIGHT4 = 400, EV_T = 200, EV_LEN = 15;
function dreamNight(ctx, model, g, seed) {
  const { agent, world } = ctx; agent.learning = false;
  const rng = new RNG(seed); const body = sleepBody(ctx, seed);
  const pond = world.places.indexOf("pond");
  let prev = ctx.log.concept[ctx.log.concept.length - 1];
  const reading = [], trueBody = [], ev = [];
  for (let t = 0; t < NIGHT4; t++) {
    const s = body.s;
    body.s = [clip(s[0] - 0.001 + rng.normal(0, 0.003), 0, 1), clip(s[1] + 0.01 * (0.45 - s[1]) + rng.normal(0, 0.003), 0, 1), clip(s[2] - 0.0015 + rng.normal(0, 0.003), 0, 1)];
    body.t += 1; const xi = body.feel();
    const on = t >= EV_T && t < EV_T + EV_LEN;
    let real = rng.normals(S.EXT);
    if (on) real = world.protos[pond].map((v) => v + rng.normal(0, 0.3));
    let p;
    if (model === "A") p = agent.interpret(real.map((v) => g * v), xi, g, 1);
    else if (model === "C") p = agent.interpret(real.map((v) => g * v), xi, 1, 1);
    else { const im = agent.mu[prev]; p = agent.interpret(real.map((v, i) => g * v + (1 - g) * im[i] + rng.normal(0, 0.1)), xi, 1, 1); }
    prev = argmax(p); reading.push(prev); trueBody.push(body.s.slice()); ev.push(on);
  }
  return { reading, trueBody, ev };
}
function scoreNight(ctx, n) {
  const { reading, trueBody, ev } = n;
  const st = stabilize(reading); let changes = 0, lifelike = 0;
  for (let i = 1; i < st.length; i++) if (st[i] !== st[i - 1]) { changes++; if (ctx.seen.has(st[i - 1] + "|" + st[i])) lifelike++; }
  const track = [0, 2].map((v) => corr(reading.map((k) => ctx.bodyOf[k][v]), trueBody.map((b) => b[v])));
  const pond = ctx.world.places.indexOf("pond");
  const at = reading.map((k) => (ctx.placeOf[k] === pond ? 1 : 0));
  const during = mean(at.filter((_, i) => ev[i])), before = mean(at.slice(EV_T - 30, EV_T));
  return { changes: (100 * changes) / reading.length, distinct: new Set(st).size, tracking: mean(track),
    lifelike: changes ? lifelike / changes : NaN, incorporation: during - before };
}

// ---------- experiment 5: sleep cycles, fair fight (strong_a.py)
function replayNight(ctx, model, { gmax, period, cycles = 4, sounds, seed }) {
  const { agent, world, T } = ctx; agent.learning = false;
  const NIGHT = period * cycles; const rng = new RNG(seed); const body = sleepBody(ctx, seed);
  const pond = world.places.indexOf("pond"); const muE = agent.muExt();
  let prev = ctx.log.concept[ctx.log.concept.length - 1];
  const on = new Array(NIGHT).fill(false); sounds.forEach((s) => { for (let i = s; i < s + 8 && i < NIGHT; i++) on[i] = true; });
  const reading = [], gate = [];
  for (let t = 0; t < NIGHT; t++) {
    const s = body.s;
    body.s = [clip(s[0] - 0.0004 + rng.normal(0, 0.003), 0, 1), clip(s[1] + 0.01 * (0.45 - s[1]) + rng.normal(0, 0.003), 0, 1), clip(s[2] - 0.0005 + rng.normal(0, 0.003), 0, 1)];
    body.t += 1; const xi = body.feel(); const g = gateAt(t, gmax, period);
    let real = rng.normals(S.EXT); if (on[t]) real = world.protos[pond].map((v) => v + rng.normal(0, 0.3));
    const prior = T[prev]; let ll;
    if (model === "A") ll = agent.loglik(real.map((v) => g * v), xi, g, 1);
    else {
      const im = new Array(S.EXT).fill(0); prior.forEach((p, k) => { for (let i = 0; i < S.EXT; i++) im[i] += p * muE[k][i]; });
      ll = agent.loglik(real.map((v, i) => g * v + (1 - g) * im[i] + rng.normal(0, 0.1)), xi, 1, 1);
    }
    const p = softmax(ll.map((v, k) => v + Math.log(prior[k])));
    prev = rng.choice(p); reading.push(prev); gate.push(g);
  }
  return { reading, gate, on };
}
function soundTimes(rng, NIGHT) {
  const out = []; let guard = 0;
  while (out.length < 8 && guard++ < 1000) { const s = 40 + rng.int(NIGHT - 48); if (out.every((o) => Math.abs(s - o) > 40)) out.push(s); }
  return out.sort((a, b) => a - b);
}

// ---------- experiment 6 & 7: awakening and recall (awaken.py)
function sleepUntil(ctx, T, seed, gmax = 0.5, period = 300) {
  const { agent } = ctx; agent.learning = false;
  const rng = new RNG(seed); const body = sleepBody(ctx, seed);
  let prev = ctx.log.concept[ctx.log.concept.length - 1];
  const reading = [], trace = [], bodies = [];
  for (let t = 0; t < T; t++) {
    const s = body.s;
    body.s = [clip(s[0] - 0.0004 + rng.normal(0, 0.003), 0, 1), clip(s[1] + 0.01 * (0.45 - s[1]) + rng.normal(0, 0.003), 0, 1), clip(s[2] - 0.0005 + rng.normal(0, 0.003), 0, 1)];
    body.t += 1; const xi = body.feel(); const g = gateAt(t, gmax, period);
    const im = agent.mu[prev]; const real = rng.normals(S.EXT);
    const p = agent.interpret(real.map((v, i) => g * v + (1 - g) * im[i] + rng.normal(0, 0.1)), xi, 1, 1);
    prev = argmax(p); reading.push(prev); trace.push(xi); bodies.push(body.s.slice());
  }
  return { reading, trace, bodies, body, rng, g0: gateAt(T - 1, gmax, period) };
}
function stimSample(ctx, stim, rng) {
  if (stim === null) return rng.normals(S.EXT);
  return ctx.world.protos[ctx.world.places.indexOf(stim)].map((v) => v + rng.normal(0, 0.3));
}
function reread(ctx, trace, cueFn, start, rng, gRead, bodyFeel = null, leak = 0.3) {
  const { agent } = ctx; let prev = start; const out = [];
  for (const x of trace) {
    const xi = bodyFeel ? (() => { const f = bodyFeel(); return x.map((v, i) => (1 - leak) * v + leak * f[i]); })() : x;
    const cue = cueFn(); const im = agent.mu[prev];
    const p = agent.interpret(cue.map((v, i) => gRead * v + (1 - gRead) * im[i] + rng.normal(0, 0.1)), xi, 1, 1);
    prev = argmax(p); out.push(prev);
  }
  return out;
}
function awakening(ctx, phase, stim, seed, LEN = 60) {
  const T = phase === "deep" ? 610 : 750;
  const sl = sleepUntil(ctx, T, seed); const { agent } = ctx;
  let prev = sl.reading[sl.reading.length - 1];
  for (let i = 0; i < 15; i++) {
    const g = sl.g0 + ((1 - sl.g0) * (i + 1)) / 15; sl.body.t += 1;
    const im = agent.mu[prev]; const s = stimSample(ctx, stim, sl.rng);
    prev = argmax(agent.interpret(s.map((v, j) => g * v + (1 - g) * im[j]), sl.body.feel(), 1, 1));
  }
  const dreamed = sl.reading.slice(-LEN);
  const report = reread(ctx, sl.trace.slice(-LEN), () => stimSample(ctx, stim, sl.rng), prev, sl.rng, 0.5);
  const target = stim === null ? -1 : ctx.world.places.indexOf(stim);
  const share = (r) => (target < 0 ? NaN : mean(r.map((k) => (ctx.placeOf[k] === target ? 1 : 0))));
  return { dreamed, report, dreamedScenes: sceneCount(dreamed), reportScenes: sceneCount(report),
    agree: mean(dreamed.map((k, i) => (k === report[i] ? 1 : 0))), stimShare: share(report), stimShareDream: share(dreamed) };
}
const BODIES = { fine: [0.6, 0.6, 0.6], thirsty: [0.6, 0.5, 0.2], hungry: [0.2, 0.5, 0.6] };
function recall(ctx, gRead, seed) {
  const sl = sleepUntil(ctx, 780, seed); const ep = sl.trace.slice(-60), dreamed = sl.reading.slice(-60);
  const recs = [], ctxs = [];
  ctx.world.places.forEach((pl, pi) => {
    Object.entries(BODIES).forEach(([bn, bs], bi) => {
      for (let rep = 0; rep < 2; rep++) {
        const probe = new Body(42, seed + 31 * pi + 7 * rep + bi * 3); probe.s = bs.slice();
        recs.push(reread(ctx, ep, () => ctx.world.observe(pi), dreamed[0], sl.rng, gRead, () => probe.feel()));
        ctxs.push({ place: pl, pi, body: bn, rep });
      }
    });
  });
  const n = recs.length; const agree = Array.from({ length: n }, (_, i) => recs.map((r, j) => mean(r.map((k, t) => (k === recs[i][t] ? 1 : 0)))));
  const same = [], diff = [];
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) (ctxs[i].pi === ctxs[j].pi && ctxs[i].body === ctxs[j].body ? same : diff).push(agree[i][j]);
  const placeShare = (r, pi) => mean(r.map((k) => (ctx.placeOf[k] === pi ? 1 : 0)));
  const pull = mean(recs.map((r, i) => placeShare(r, ctxs[i].pi) - mean(recs.map((q) => placeShare(q, ctxs[i].pi)))));
  return { agree, ctxs, same: mean(same), diff: mean(diff), vsDream: mean(recs.map((r) => mean(r.map((k, t) => (k === dreamed[t] ? 1 : 0))))), pull };
}

// ============================================================================
// MANY-SENSES WORLD (world2.py)
// ============================================================================
const W2 = {
  TILES: ["grass", "water", "bush", "rock", "cave", "thorns", "hill"],
  GRASS: 0, WATER: 1, BUSH: 2, ROCK: 3, CAVE: 4, THORNS: 5, HILL: 6,
  MOVES: [[-1, 0], [1, 0], [0, -1], [0, 1], [0, 0]],
  SET: [0.7, 0.7, 0.6, 0.0, 0.2, 0.25], WEIGHT: [1, 1, 2, 2, 0.5, 0.5], DAY: 240, EXT: 16,
};
W2.EXT_NAMES = W2.TILES.map((t) => "see:" + t).concat(["see:light", "hear:water", "hear:growl", "hear:rain", "smell:berries", "smell:predator", "touch:wet", "touch:skin-temp", "touch:sharp"]);

class World2 {
  constructor(kind, seed, n = 12) {
    this.kind = kind; this.n = n; const r = new RNG(seed);
    const g = Array.from({ length: n }, () => new Array(n).fill(W2.GRASS));
    for (let i = 2; i < 4; i++) for (let j = 2; j < 4; j++) g[i][j] = W2.WATER;
    for (let i = 9; i < 11; i++) for (let j = 1; j < 3; j++) g[i][j] = W2.CAVE;
    [[1, 8], [6, 1], [5, 9], [10, 6]].forEach(([a, b]) => (g[a][b] = W2.ROCK));
    [[7, 7], [7, 9], [8, 8], [9, 7], [9, 9], [8, 10]].forEach(([a, b]) => (g[a][b] = W2.BUSH));
    const free = []; for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (g[i][j] === W2.GRASS) free.push([i, j]);
    for (let k = 0; k < 8; k++) { const idx = r.int(free.length); const [a, b] = free.splice(idx, 1)[0]; g[a][b] = W2.THORNS; }
    if (kind === "mountain") for (let i = 6; i < 12; i++) for (let j = 5; j < 12; j++) if (g[i][j] === W2.GRASS) g[i][j] = W2.HILL;
    this.grid = g; this.stock = g.map((row) => row.map((v) => (v === W2.BUSH ? 1 : 0)));
    this.rng = new RNG(seed + 1); this.t = 0; this.rain = false; this.den = [11, 11];
    this.pred = kind === "forest" ? this.den.slice() : null;
    this.cells = {}; for (let t = 0; t < 7; t++) this.cells[t] = [];
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) this.cells[g[i][j]].push([i, j]);
  }
  light() { return clip(0.5 + 0.6 * Math.cos((2 * Math.PI * this.t) / W2.DAY), 0.03, 1); }
  tile(p) { return this.grid[p[0]][p[1]]; }
  ambient(p) {
    if (this.tile(p) === W2.CAVE) return 0.55;
    let a = 0.3 + 0.35 * this.light(); if (this.tile(p) === W2.ROCK) a += 0.25 * this.light();
    return a - (this.rain ? 0.12 : 0);
  }
  dist(p, kind) { let m = 99; for (const c of this.cells[kind]) m = Math.min(m, Math.abs(c[0] - p[0]) + Math.abs(c[1] - p[1])); return m; }
  predDist(p) { return this.pred ? Math.abs(this.pred[0] - p[0]) + Math.abs(this.pred[1] - p[1]) : 99; }
  step(p) {
    this.t += 1;
    this.rain = this.rain ? this.rng.next() > 0.03 : this.rng.next() < 0.004;
    for (const [i, j] of this.cells[W2.BUSH]) this.stock[i][j] = clip(this.stock[i][j] + 0.004, 0, 1);
    if (this.pred && this.light() >= 0.35) this.pred = this.den.slice();
    else if (this.pred) {
      const d = this.predDist(p); let mv;
      if (d <= 3 && this.rng.next() < 0.25) {
        const st = [Math.sign(p[0] - this.pred[0]), Math.sign(p[1] - this.pred[1])]; const k = this.rng.int(2);
        mv = [0, 0]; mv[k] = st[k] !== 0 ? st[k] : st[1 - k];
      } else {
        mv = W2.MOVES[this.rng.int(4)].slice();
        if (Math.abs(this.pred[0] + mv[0] - this.den[0]) + Math.abs(this.pred[1] + mv[1] - this.den[1]) > 4)
          mv = [Math.sign(this.den[0] - this.pred[0]), Math.sign(this.den[1] - this.pred[1])];
      }
      this.pred = [clip(this.pred[0] + mv[0], 0, this.n - 1), clip(this.pred[1] + mv[1], 0, this.n - 1)];
    }
  }
  sense(p, rng, noise = 0.1) {
    const L = this.light(); const cnt = new Array(7).fill(0); let tot = 0;
    for (let i = Math.max(p[0] - 1, 0); i <= Math.min(p[0] + 1, this.n - 1); i++) for (let j = Math.max(p[1] - 1, 0); j <= Math.min(p[1] + 1, this.n - 1); j++) { cnt[this.grid[i][j]]++; tot++; }
    const vision = cnt.map((c) => L * (c / tot)).concat([L]).map((v) => v + rng.normal(0, noise + 0.15 * (1 - L)));
    const dp = this.predDist(p);
    let sm = 0; for (const [i, j] of this.cells[W2.BUSH]) sm += this.stock[i][j] * Math.exp(-(Math.abs(i - p[0]) + Math.abs(j - p[1])) / 2);
    const tile = this.tile(p);
    const other = [Math.max(0, 1 - this.dist(p, W2.WATER) / 4), Math.max(0, 1 - dp / 6), this.rain ? 1 : 0,
      Math.min(1, sm), Math.exp(-dp / 3), this.rain || tile === W2.WATER ? 1 : 0, this.ambient(p), tile === W2.THORNS ? 1 : 0].map((v) => v + rng.normal(0, noise));
    return vision.concat(other);
  }
}

class Body2 {
  constructor(nervesSeed = 42, seed = 0) {
    const r = new RNG(nervesSeed);
    const mk = (rows, cols) => ({ A: Array.from({ length: rows }, () => r.normals(cols, 0, 2)), c: r.normals(rows, 0, 0.4) });
    this.maps = { gut: mk(3, 3), thermo: mk(2, 1), pain: mk(2, 1), fatigue: mk(2, 1) };
    this.rng = new RNG(seed + 3); this.s = W2.SET.slice(); this.beat = 0;
  }
  static distress(s) { return Math.sqrt(s.reduce((a, v, i) => a + W2.WEIGHT[i] * (v - W2.SET[i]) ** 2, 0)); }
  step(world, p, action) {
    let [e, w, tp, dmg, fat, ar] = this.s; const tile = world.tile(p);
    const moving = action !== 4 ? 1 : 0, climbing = moving && tile === W2.HILL ? 1 : 0;
    e -= 0.0015 + 0.001 * moving + 0.005 * climbing; w -= 0.002 + 0.0005 * moving;
    if (tile === W2.BUSH && world.stock[p[0]][p[1]] > 0.2) { e += 0.08; world.stock[p[0]][p[1]] -= 0.2; }
    if (tile === W2.WATER) w += 0.1;
    tp += 0.06 * (world.ambient(p) - tp) + 0.004 * moving;
    if (tile === W2.THORNS) dmg += 0.06;
    if (world.predDist(p) <= 1) { dmg += 0.2; world.pred = world.den.slice(); }
    dmg -= 0.01;
    fat += 0.001 + 0.0015 * moving + 0.005 * climbing; if (!moving) fat -= tile === W2.CAVE ? 0.03 : 0.015;
    const threat = Math.max(0, 1 - world.predDist(p) / 5);
    ar += 0.2 * (0.15 + 0.8 * threat + 0.6 * dmg + 0.7 * climbing + 0.1 * moving - ar);
    this.s = [e, w, tp, dmg, fat, ar].map((v) => clip(v, 0, 1));
  }
  feel(state = null, noise = 0.05) {
    const s = state || this.s; const [e, w, tp, dmg, fat, ar] = s;
    const f = (m, x) => m.A.map((row, j) => Math.tanh(row.reduce((a, v, i) => a + v * x[i], 0) + m.c[j]));
    this.beat += 0.4 + 1.6 * ar;
    const out = f(this.maps.gut, [e - 0.5, w - 0.5, dmg]).concat(f(this.maps.thermo, [tp - 0.5]), f(this.maps.pain, [dmg]), f(this.maps.fatigue, [fat - 0.3]),
      [Math.sin(this.beat) * (0.3 + 0.7 * ar), 2 * ar - 1]).map((v) => v + this.rng.normal(0, noise));
    out.push(3 * Body2.distress(s)); return out;
  }
}

class QAgent extends Agent {
  constructor(seed) { super(W2.EXT, { maxC: 60, thr: 2.5, seed }); this.Q = Array.from({ length: 60 }, () => new Array(5).fill(0)); }
  qv(b, a) { let s = 0; for (let k = 0; k < b.length; k++) s += b[k] * this.Q[k][a]; return s; }
  act(b, temp = 0.05) { return this.rng.choice(softmax([0, 1, 2, 3, 4].map((a) => this.qv(b, a) / temp))); }
  update(b, a, r, b2, alpha = 0.1, gamma = 0.98) {
    const target = r + gamma * Math.max(...[0, 1, 2, 3, 4].map((x) => this.qv(b2, x)));
    const cur = this.qv(b, a); for (let k = 0; k < b.length; k++) this.Q[k][a] += alpha * b[k] * (target - cur);
  }
}

async function raiseWorld2(kind, steps, seed, onProgress = null) {
  const key = ["w2", kind, steps, seed].join("|"); if (cache.has(key)) return cache.get(key);
  const world = new World2(kind, seed), body = new Body2(42, seed), agent = new QAgent(seed); const rng = new RNG(seed + 9);
  let pos = [5, 5]; let xi = body.feel(), xe = world.sense(pos, rng);
  agent.learn(xe, xi); let b = agent.interpret(xe, xi); let prevFelt = xi[xi.length - 1] / 3;
  const visits = Array.from({ length: world.n }, () => new Array(world.n).fill(0)); const vit = [], dist = [];
  for (let t = 0; t < steps; t++) {
    const a = agent.act(b); const mv = W2.MOVES[a];
    pos = [clip(pos[0] + mv[0], 0, world.n - 1), clip(pos[1] + mv[1], 0, world.n - 1)];
    world.step(pos); body.step(world, pos, a);
    xe = world.sense(pos, rng); xi = body.feel(); agent.learn(xe, xi); const b2 = agent.interpret(xe, xi);
    const felt = xi[xi.length - 1] / 3; agent.update(b, a, 10 * (prevFelt - felt) - 0.1 * felt, b2); prevFelt = felt; b = b2;
    visits[pos[0]][pos[1]]++; vit.push(body.s.slice()); dist.push(Body2.distress(body.s));
    if (t % 500 === 0) { if (onProgress) onProgress(t / steps); await tick(); }
  }
  const out = { world, agent, visits, vit, dist }; cache.set(key, out); return out;
}
function racingHeartProbe(r) {
  const probe = new Body2(42, 999); r.agent.learning = false; const muE = r.agent.muExt(); const res = {};
  for (const [label, ar] of [["calm", 0.2], ["racing", 0.9]]) {
    const exp = new Array(W2.EXT).fill(0);
    for (let rep = 0; rep < 40; rep++) {
      const st = W2.SET.slice(); st[5] = ar;
      const p = r.agent.interpret(new Array(W2.EXT).fill(0), probe.feel(st), 0, 1);
      p.forEach((pk, k) => { for (let i = 0; i < W2.EXT; i++) exp[i] += (pk * muE[k][i]) / 40; });
    }
    res[label] = exp;
  }
  return res;
}

// ============================================================================
// VOICE (voice.py): expression described from the inside
// ============================================================================
const V = { EXT: W2.EXT + 3, VO: W2.EXT, NA: 10, KAPPA: 0.15, TRACK: [0, 1, 4, 5] };
const voiceQuality = (s) => [0.3 + 0.7 * s[0] * (1 - 0.5 * s[4]), 0.2 + 0.8 * s[5], clip(1 - s[1] + 0.3 * s[4], 0, 1)];
class VAgent extends Agent {
  constructor(seed, ed = V.EXT) { super(ed, { maxC: 60, thr: 2.5, seed }); this.Q = Array.from({ length: 60 }, () => new Array(V.NA).fill(0)); }
  qv(b, a) { let s = 0; for (let k = 0; k < b.length; k++) s += b[k] * this.Q[k][a]; return s; }
  act(b, temp = 0.05) { const v = []; for (let a = 0; a < V.NA; a++) v.push(this.qv(b, a) / temp); return this.rng.choice(softmax(v)); }
  update(b, a, r, b2, alpha = 0.1, gamma = 0.98) {
    let mx = -Infinity; for (let x = 0; x < V.NA; x++) mx = Math.max(mx, this.qv(b2, x));
    const cur = this.qv(b, a), target = r + gamma * mx; for (let k = 0; k < b.length; k++) this.Q[k][a] += alpha * b[k] * (target - cur);
  }
  bodySurprise(xe, xi) {
    const k = argmax(this.loglik(xe, xi)); const mu = this.mu[k], v = this.vr[k]; let z = 0;
    for (let i = 0; i < 11; i++) z += (xi[i] - mu[this.ed + i]) ** 2 / v[this.ed + i];
    return z / 11;
  }
  // how badly the voice it hears fits what it expects from everything else it senses
  voiceSurprise(xe, xi) {
    const x = xe.concat(xi); let best = -Infinity, kb = 0;
    for (let k = 0; k < this.mu.length; k++) {
      const mu = this.mu[k], v = this.vr[k]; let ll = Math.log(this.n[k]);
      for (let i = 0; i < x.length; i++) { if (i >= V.VO && i < V.VO + 3) continue; const d = x[i] - mu[i]; ll -= 0.5 * (d * d / v[i] + Math.log(v[i])); }
      if (ll > best) { best = ll; kb = k; }
    }
    let z = 0; for (let i = V.VO; i < V.VO + 3; i++) z += (x[i] - this.mu[kb][i]) ** 2 / this.vr[kb][i];
    return z / 3;
  }
}
async function liveVoice({ n = 1, kind = "mountain", seed = 1, steps = 10000, hearsSelf = true, hearOthers = true, kappa = V.KAPPA, innerNoise = 0.05, forceVoice = null, seeSelf = false, strong = false, H = 5 }, onProgress = null) {
  const key = ["v", n, kind, seed, steps, hearsSelf, hearOthers, kappa, innerNoise, forceVoice, seeSelf, strong, H].join("|");
  const ED = V.EXT + (seeSelf ? 3 : 0);
  // seeing its own body (thin when hungry, dry when thirsty, hurt): fades with the light like all vision
  const seen = (cr) => { if (!seeSelf) return []; const L = world.light(), s = cr.body.s; return [1 - s[0], 1 - s[1], s[3]].map((v) => L * v + rng.normal(0, 0.1 + 0.15 * (1 - L))); }; if (cache.has(key)) return cache.get(key);
  const world = new World2(kind, seed), rng = new RNG(seed + 5), starts = [[5, 5], [6, 3]];
  const crs = []; for (let i = 0; i < n; i++) crs.push({ body: new Body2(42, seed + 31 * i), agent: new VAgent(seed + 7 * i, ED), pos: starts[i].slice(), voiced: false, rng: new RNG(seed + 101 * i) });
  const heard = (cr) => {
    const snd = [0, 0, 0]; let own = 0;
    if (cr.voiced && hearsSelf) { const q = voiceQuality(cr.body.s); own = q[0]; q.forEach((v, i) => (snd[i] += v)); }
    if (hearOthers) for (const o of crs) if (o !== cr && o.voiced) { const att = Math.exp(-(Math.abs(o.pos[0] - cr.pos[0]) + Math.abs(o.pos[1] - cr.pos[1])) / 3); voiceQuality(o.body.s).forEach((v, i) => (snd[i] += att * v)); }
    return { snd: snd.map((v) => clip(v, 0, 1.5) + rng.normal(0, 0.05 + (world.rain ? 0.15 : 0))), own };
  };
  const inner = (cr) => { const xi = cr.body.feel(null, innerNoise); const last = xi.pop(); xi.push((cr.voiced ? 1 : 0) + cr.rng.normal(0, 0.1), last); return xi; };
  if (strong) crs.forEach((cr) => { cr.Qm = Array.from({ length: 60 }, () => new Array(5).fill(0)); cr.Qv = Array.from({ length: 60 }, () => [0, 0]); cr.F = new Array(60).fill(0.3); cr.hist = []; });
  const qv = (Q, b, a) => { let x = 0; for (let k = 0; k < b.length; k++) x += b[k] * Q[k][a]; return x; };
  const pick = (cr, Q, b, nA, temp) => { const v = []; for (let a = 0; a < nA; a++) v.push(qv(Q, b, a) / temp); return cr.agent.rng.choice(softmax(v)); };
  const learnQ = (Q, b, a, r, b2, nA, alpha, gamma) => { let mx = -Infinity; for (let x = 0; x < nA; x++) mx = Math.max(mx, qv(Q, b2, x)); const cur = qv(Q, b, a), tg = r + gamma * mx; for (let k = 0; k < b.length; k++) Q[k][a] += alpha * b[k] * (tg - cur); };
  const state = crs.map((cr) => { const xe = world.sense(cr.pos, rng).concat(heard(cr).snd, seen(cr)), xi = inner(cr); cr.agent.learn(xe, xi); return { b: cr.agent.interpret(xe, xi), felt: xi[xi.length - 1] / 3 }; });
  const logs = crs.map(() => ({ concept: [], vitals: [], voiced: [], light: [], pos: [], ownHeard: [], otherHeard: [], surprise: [], vsur: [], loud: [], ent: [], perr: [], fit: [], dpe: [] }));
  const L_clar = crs.map(() => []);
  for (let t = 0; t < steps; t++) {
    const acts = crs.map((cr, i) => { const a = strong ? pick(cr, cr.Qm, state[i].b, 5, 0.03) + 5 * pick(cr, cr.Qv, state[i].b, 2, 0.02) : cr.agent.act(state[i].b); const mv = W2.MOVES[a % 5]; cr.pos = [clip(cr.pos[0] + mv[0], 0, world.n - 1), clip(cr.pos[1] + mv[1], 0, world.n - 1)]; cr.voiced = forceVoice === null ? a >= 5 : forceVoice(t, world); return a; });
    world.step(crs[0].pos);
    crs.forEach((cr, i) => { cr.body.step(world, cr.pos, acts[i] % 5); if (cr.voiced) { cr.body.s[0] = Math.max(0, cr.body.s[0] - 0.0008); cr.body.s[1] = Math.max(0, cr.body.s[1] - 0.0006); } });
    crs.forEach((cr, i) => {
      const h = heard(cr), xe = world.sense(cr.pos, rng).concat(h.snd, seen(cr)), xi = inner(cr);
      const c = cr.agent.learn(xe, xi), b2 = cr.agent.interpret(xe, xi), sur = cr.agent.bodySurprise(xe, xi), felt = xi[xi.length - 1] / 3;
      if (strong) {
        cr.hist.push(state[i].b); let clar = 0;
        if (cr.hist.length > H) { const bo = cr.hist.shift(); let pr = 0; bo.forEach((p, k) => (pr += p * cr.F[k])); const e = felt - pr; bo.forEach((p, k) => (cr.F[k] += 0.05 * p * e)); clar = Math.abs(e); }
        L_clar[i].push(clar);
        const rc = 10 * (state[i].felt - felt) - 0.1 * felt, ry = -kappa * 10 * clar;
        learnQ(cr.Qm, state[i].b, acts[i] % 5, rc + ry, b2, 5, 0.1, 0.98);
        learnQ(cr.Qv, state[i].b, acts[i] >= 5 ? 1 : 0, rc + ry, b2, 2, 0.1, 0.8);
      } else cr.agent.update(state[i].b, acts[i], 10 * (state[i].felt - felt) - 0.1 * felt - kappa * Math.min(sur, 4), b2);
      { let e = 0; b2.forEach((p) => { if (p > 1e-12) e -= p * Math.log(p); }); logs[i].ent.push(e); }
      { const prevB = state[i].b; let pe = 0; for (let j = 0; j < 11; j++) { let m = 0; prevB.forEach((p, k) => { if (k < cr.agent.mu.length) m += p * cr.agent.mu[k][ED + j]; }); pe += (xi[j] - m) ** 2; } logs[i].perr.push(pe / 11); }
      { const ll = cr.agent.loglik(xe, xi); logs[i].fit.push(Math.max(...ll)); }
      { const prevB = state[i].b; let m = 0; prevB.forEach((p, k) => { if (k < cr.agent.mu.length) m += p * cr.agent.mu[k][ED + 12]; }); logs[i].dpe.push((xi[12] - m) ** 2); }
      state[i] = { b: b2, felt };
      const L = logs[i]; L.concept.push(c); L.vitals.push(cr.body.s.slice()); L.voiced.push(cr.voiced); L.light.push(world.light()); L.pos.push(cr.pos.slice());
      L.ownHeard.push(h.own); L.otherHeard.push(Math.max(0, h.snd[0] - h.own)); L.surprise.push(sur); L.loud.push(h.snd[0]); L.vsur.push(n > 1 && h.snd[0] > 0.45 ? cr.agent.voiceSurprise(xe, xi) : NaN);
    });
    if (t % 500 === 0) { if (onProgress) onProgress(t / steps); await tick(); }
  }
  logs.forEach((L, i) => (L.clar = L_clar[i])); const out = { world, crs, logs, steps }; cache.set(key, out); return out;
}
function voiceStats(L, steps) {
  const h0 = Math.floor(steps / 2), K = Math.max(...L.concept) + 1;
  const cm = Array.from({ length: K }, () => ({ s: [0, 0, 0, 0, 0, 0], n: 0 }));
  for (let t = h0; t < steps; t++) { const c = cm[L.concept[t]]; c.n++; L.vitals[t].forEach((v, i) => (c.s[i] += v)); }
  const cmap = cm.map((c) => (c.n ? c.s.map((v) => v / c.n) : W2.SET));
  const byHour = Array.from({ length: 24 }, () => [0, 0]); const err = {}; const vd = [0, 0], vb = [0, 0];
  for (let t = h0; t < steps; t++) {
    const hr = Math.floor(((t + 1) % W2.DAY) * 24 / W2.DAY); byHour[hr][0] += L.voiced[t]; byHour[hr][1]++;
    const ea = V.TRACK.reduce((a, i) => a + Math.abs(L.vitals[t][i] - cmap[L.concept[t]][i]), 0) / 4, ka = L.voiced[t] ? "voice" : "quiet";
    (err[ka] = err[ka] || [0, 0])[0] += ea; err[ka][1]++;
    const lt = L.light[t] < 0.3 ? "dark" : L.light[t] > 0.7 ? "bright" : null; if (!lt) continue;
    if (lt === "dark") { vd[0] += L.voiced[t]; vd[1]++; } else { vb[0] += L.voiced[t]; vb[1]++; }
    const k = lt + "/" + (L.voiced[t] ? "voice" : "quiet"); const e = V.TRACK.reduce((a, i) => a + Math.abs(L.vitals[t][i] - cmap[L.concept[t]][i]), 0) / 4;
    (err[k] = err[k] || [0, 0])[0] += e; err[k][1]++;
  }
  const E = {}; for (const k in err) E[k] = err[k][1] > 30 ? err[k][0] / err[k][1] : NaN;
  return { byHour: byHour.map(([a, b]) => (b ? a / b : NaN)), dark: vd[0] / vd[1], bright: vb[0] / vb[1], err: E, K };
}
function pairStats(r) {
  const h0 = Math.floor(r.steps / 2), [A, B] = r.logs; let near = 0, d = 0; const n = r.steps - h0;
  const va = A.voiced.slice(h0), vb = B.voiced.slice(h0);
  for (let t = h0; t < r.steps; t++) { const dd = Math.abs(A.pos[t][0] - B.pos[t][0]) + Math.abs(A.pos[t][1] - B.pos[t][1]); d += dd; near += dd <= 3; }
  const follow = (x, y) => { const nx = y.map((_, t) => y[t + 1] || y[t + 2] || y[t + 3] || false); let hit = 0, cnt = 0; x.forEach((v, t) => { if (v) { cnt++; hit += nx[t]; } }); return (hit / Math.max(cnt, 1)) / Math.max(mean(nx.map(Number)), 1e-9); };
  const own = [], oth = [];
  for (const L of r.logs) for (let t = h0; t < r.steps; t++) {
    if (!Number.isFinite(L.vsur[t]) || L.loud[t] > 1.1) continue;
    if (L.ownHeard[t] > 0.4 && L.otherHeard[t] < 0.1) own.push(L.vsur[t]); else if (L.ownHeard[t] === 0 && L.otherHeard[t] > 0.4) oth.push(L.vsur[t]);
  }
  return { surOwn: mean(own), surOther: mean(oth), nOwn: own.length, nOther: oth.length, sync: 0.5 * (follow(va, vb) + follow(vb, va)), dist: d / n, near: near / n, voice: 0.5 * (mean(va.map(Number)) + mean(vb.map(Number))) };
}

if (typeof module !== "undefined") module.exports = { RNG, Agent, World, Body, raiseSimple, dictionaryMap, waking, dreamNight, scoreNight, replayNight, soundTimes, gateAt, stabilize, sceneCount, awakening, recall, raiseWorld2, racingHeartProbe, liveVoice, voiceStats, pairStats, voiceQuality, V, W2, WORLDS, mean, rankCorr };
