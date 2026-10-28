"""The Olvasó engine: an entity that reads itself through its outside.

A faithful Python port of the JavaScript engine used in the browser rooms and in all the published experiments
(stages 7 to 21). The order of operations follows the JavaScript closely, so the same seeds give the same lives
for a long while; over very long runs the two drift apart through last-digit differences in log, exp and cos, and
results agree statistically (see tests/).

The outside: colours on its screen, typing, pointer, the visitor's presence, words heard as sounds, the body of the
one it watches, and its own body as it shows. The inside: four hidden quantities it never sees (charge, steadiness,
contact, effort), felt only through scrambled channels plus "how bad it feels". It learns patterns over outside and
inside together, reads itself as those patterns, and acts (colours, words, reaching out) to feel better and to
forecast its own feelings well.

Switches (module-level `OL`, as in the JavaScript):
  RECALL           the word that comes to mind is recalled from what it reads itself as (stage 8)
  CONTAGION        seeing another tremble more than itself unsettles it (stage 9)
  REACH, COMPANY   it can reach toward the one it watches; being reached steadies (stage 9)
  READ_CONTAGION   the trembling it expects of the other unsettles it, as seeing would (stage 14)
  VOICES           each speaker's words carry its own timbre (stage 6)
  HEAR, FEEL       width of the reader: numbers per sound, felt channels (stage 17)
  SALIENCE         moments that feel worse than usual are learned more strongly (stage 19)
  sense['unseen']  the other is out of sight: its body channels are missing, not grey (stage 18)
"""
import math
import numpy as np
from .rng import ORng


class _Config(dict):
    __getattr__ = dict.__getitem__

    def __setattr__(self, k, v):
        self[k] = v


DEFAULTS = dict(
    HUES=[8, 48, 140, 190, 228, 290],
    VOICES=False, RECALL=False, CONTAGION=0.0, REACH=False, GAMMA=0.8, COMPANY=1.0, COMPANY_CONTACT=False, READ_CONTAGION=0.0,
    NX=18, NY=8, NA=12, NWORDS=4, MAXC=60, HEAR=3, FEEL=6, SALIENCE=0.0, THR=2.5,
    SET=[0.5, 0.7, 0.45, 0.15], W=[1.0, 1.5, 0.6, 0.5],
    TICK_MS=250, PERIOD=240, GMAX=0.5, ASLEEP_AFTER_S=45, TRACE_MAX=320, REPORT_LEN=80, H=5, KAPPA=0.3,
)
OL = _Config(DEFAULTS)
HNAMES = ["charge", "steadiness", "contact", "effort"]
XNAMES = ["screen hue (x)", "screen hue (y)", "screen colour strength", "typing rate", "vowel share of typing", "pointer speed",
          "pointer x", "pointer y", "your presence", "word heard (a)", "word heard (b)", "word heard (c)", "the other: size",
          "the other: trembling", "the other: reaching out", "the other: stirring", "its own body: size", "its own body: trembling"]
UNSEEN = (12, 13, 14, 15)
TWO_PI = 2 * math.pi


def reset(**overrides):
    """Restore all switches to their defaults (then apply overrides). Call this between experiments."""
    OL.clear()
    OL.update({k: (list(v) if isinstance(v, list) else v) for k, v in DEFAULTS.items()})
    OL.update(overrides)
    if "HEAR" in overrides or "FEEL" in overrides:
        OL.NX = 18 + OL.HEAR - 3
        OL.NY = OL.FEEL + 2
    return OL


def oclip(x, a, b):
    return min(b, max(a, x))


def osoftmax(v):
    v = np.asarray(v, dtype=float)
    e = np.exp(v - v.max())
    return e / np.cumsum(e)[-1]  # sequential sum, as in JavaScript


def body_look(h):
    """What shows of its inside: size (charge), trembling (unsteadiness), reaching out (contact), stirring (effort)."""
    return [h[0], oclip((0.78 - h[1]) * 4, 0, 1), h[2], oclip(h[3] * 3, 0, 1)]


def hear_idx(i):
    """A sound is HEAR numbers; the first three sit at outside channels 9-11, the rest after the body (18+)."""
    return 9 + i if i < 3 else 18 + (i - 3)


def word_code(w):
    """A word reaches it as a sound: HEAR numbers made from its letters, nothing about its meaning."""
    h = 2166136261
    for ch in w:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    out = []
    for _ in range(OL.HEAR):
        h ^= h >> 13
        h = (h * 0x5BD1E995) & 0xFFFFFFFF
        out.append(0.1 + 0.8 * ((h >> 8) / 16777216))
    return out


def voice_code(w, frm=None):
    """A word in a speaker's voice: a small fixed shift of the sound (stage 6)."""
    c = word_code(w)
    if frm is None:
        return c
    r = ORng(9973 + 7919 * (frm + 1))
    return [oclip(v + 0.12 * (r.next() * 2 - 1), 0, 1) for v in c]


def stab(r, hold=3):
    s = list(r)
    i = 0
    while i < len(s):
        j = i
        while j < len(s) and r[j] == r[i]:
            j += 1
        if j - i < hold and i > 0:
            for q in range(i, j):
                s[q] = s[i - 1]
        i = j
    return s


def _seqsum_rows(M):
    """Row sums accumulated left to right (the JavaScript loop order)."""
    if M.shape[1] == 0:
        return np.zeros(M.shape[0])
    return np.cumsum(M, axis=1)[:, -1]


class Olvaso:
    """One Olvasó. Call tick() once per step with what reaches it from outside."""

    def __init__(self, seed):
        self.seed = seed
        self.rng = ORng(seed)
        r = ORng(seed ^ 0x5BD1E995)  # JavaScript: new ORng(seed ^ 0x5bd1e995), read as uint32
        self.A = [[r.normal(0, 1.8) for _ in range(4)] for _ in range(6)]
        self.c = [r.normal(0, 0.3) for _ in range(6)]
        for _ in range(6, OL.FEEL):  # stage 17: more felt channels from the same four hidden quantities
            self.A.append([r.normal(0, 1.8) for _ in range(4)])
            self.c.append(r.normal(0, 0.3))
        self.h = list(OL.SET)
        self.h[0] = 0.4
        D = OL.NX + OL.NY
        self.D = D
        self.mu = np.zeros((0, D))
        self.vr = np.zeros((0, D))
        self.L = np.zeros((0, D))  # log(2*pi*variance), cached per pattern
        self.n = []
        self.Q = np.zeros((0, OL.NA))
        self.F = []
        self.T = []
        self.age = 0
        self.awake_ticks = 0
        self.sleep_ticks = 0
        self.screen = dict(hue=0.0, str=0.0, by="none", vx=0.0, vy=0.0)
        self.xavg = [0.5] * OL.NX
        self.gate = 1.0
        self.mode = "awake"
        self.prev = 0
        self.belief = None
        self.felt = 0.0
        self.hist = []
        self.reading = -1
        self.trace = []
        self.reports = []
        self.mirror = dict(own=None, you=None, others=None, nOwn=0, nYou=0, nOthers=0)
        self.marks = 0
        self.you_colours = 0
        self.others_colours = 0
        self.word = dict(code=[0.5, 0.5, 0.5], str=0.0)
        self.lexicon = {}
        self.hm = []  # observer's record: the hidden state that goes with each pattern (the entity never uses it)
        self.hue_stats = [dict(n=0, s=[0.0] * 4, q=[0.0] * 4) for _ in OL.HUES]
        self.last_own_mark = -999
        self.last_own_hue = -1
        self.answers = 0
        self.echoes = 0
        self.miss = None
        self.company_t = 0
        self.close_gain = None
        self.mute = False
        self.deaf = False
        self.voice = None
        self.speech = None
        self.speech_log = None  # set to [] to record every utterance
        self.said = None
        self.f_avg = None

    # ---------- patterns (online Gaussian clusters over [outside, inside])
    def _terms(self, x, skip=None):
        d = x[None, :] - self.mu
        t = -0.5 * ((d * d) / self.vr + self.L)
        if skip is not None:
            t[:, list(skip)] = 0.0
        return t

    def _parts(self, x, skip=None):
        t = self._terms(x, skip)
        return _seqsum_rows(t[:, :OL.NX]), _seqsum_rows(t[:, OL.NX:])

    def loglik(self, xe, xi, lE=1.0):
        x = np.asarray(list(xe) + list(xi), dtype=float)
        N = float(sum(self.n))
        a, b = self._parts(x, UNSEEN if self.miss else None)
        return np.log(np.asarray(self.n, dtype=float) / N) + lE * a + b

    def interpret(self, xe, xi, lE=1.0):
        return osoftmax(self.loglik(xe, xi, lE)) if len(self.n) else np.zeros(0)

    def learn(self, xe, xi):
        x = np.asarray(list(xe) + list(xi), dtype=float)
        K = len(self.n)
        skip = UNSEEN if self.miss else None
        nm = len(UNSEEN) if self.miss else 0
        if K:
            a, b = self._parts(x, skip)
            k = int(np.argmax(a + b))
            mu, v = self.mu[k], self.vr[k]
            z = (x - mu) ** 2 / v
            if skip is not None:
                z[list(skip)] = 0.0
            ze = float(np.cumsum(z[:OL.NX])[-1])
            zi = float(np.cumsum(z[OL.NX:])[-1])
            novel = max(ze / (OL.NX - nm), zi / OL.NY)
            if novel < OL.THR or K >= OL.MAXC:
                self.n[k] += 1
                sw = self.salience_w(xi)
                lr = min(0.5, max(1 / self.n[k], 0.02) * sw)
                lv = min(lr, 0.05 * sw)
                d = x - mu
                newmu = mu + lr * d
                newv = np.clip((1 - lv) * v + lv * d * d, 0.01, 0.5)
                if skip is not None:
                    idx = list(skip)
                    newmu[idx] = mu[idx]
                    newv[idx] = v[idx]
                self.mu[k] = newmu
                self.vr[k] = newv
                self.L[k] = np.log(TWO_PI * newv)
                return k
        nx = x.copy()
        if self.miss and K:
            for i in UNSEEN:
                s = 0.0
                N = 0.0
                for j in range(K):
                    s += self.n[j] * self.mu[j, i]
                    N += self.n[j]
                nx[i] = s / N
        self.mu = np.vstack([self.mu, nx[None, :]])
        v0 = np.full(self.D, 0.3)
        self.vr = np.vstack([self.vr, v0[None, :]])
        self.L = np.vstack([self.L, np.log(TWO_PI * v0)[None, :]])
        self.n.append(1)
        self.Q = np.vstack([self.Q, np.zeros((1, OL.NA))])
        self.F.append(0.3)
        for row in self.T:
            row.append(0)
        self.T.append([0] * len(self.n))
        return len(self.n) - 1

    def salience_w(self, xi):
        """Stage 19: a moment that feels worse than usual is learned more strongly (1 when off)."""
        if not OL.SALIENCE:
            return 1
        f = xi[OL.NY - 1] / 3
        if self.f_avg is None:
            self.f_avg = f
        w = 1 + OL.SALIENCE * max(0, f - self.f_avg)
        self.f_avg += 0.01 * (f - self.f_avg)
        return w

    # ---------- the inside: hidden, felt only through scrambled channels
    def distress(self, h=None):
        h = self.h if h is None else h
        s = 0.0
        for i in range(4):
            s += OL.W[i] * (h[i] - OL.SET[i]) ** 2
        return math.sqrt(s)

    def feel(self, acted):
        y = []
        for j, row in enumerate(self.A):
            a = 0.0
            for i in range(4):
                a = a + row[i] * (self.h[i] - 0.5)
            y.append(math.tanh(a + self.c[j]) + self.rng.normal(0, 0.08))
        y.append(acted + self.rng.normal(0, 0.1))  # the felt act (like a throat)
        y.append(3 * self.distress())  # innate: how bad it feels
        return y

    # ---------- one step awake
    def outside(self, sense):
        s = self.screen["str"]
        a = (self.screen["hue"] * math.pi) / 180
        ws = self.word["str"]
        wc = self.word["code"]
        x = [0.5 + 0.5 * math.cos(a) * s, 0.5 + 0.5 * math.sin(a) * s, s, sense.get("typing", 0), sense.get("vowels", 0.4),
             sense.get("speed", 0.1), sense.get("px", 0.5), sense.get("py", 0.5), sense.get("presence", 0),
             0.5 + (wc[0] - 0.5) * ws, 0.5 + (wc[1] - 0.5) * ws, 0.5 + (wc[2] - 0.5) * ws]
        seen = sense.get("seen") or [0.5, 0.5, 0.5, 0.5]
        me = [0.5, 0.5] if sense.get("noBody") else body_look(self.h)
        x += [seen[0], seen[1], seen[2], seen[3], me[0], me[1]]
        for i in range(3, OL.HEAR):
            x.append(0.5 + ((wc[i] if i < len(wc) else 0.5) - 0.5) * ws)
        return [v + self.rng.normal(0, 0.04) for v in x]

    def body_step(self, x, acted):
        unseen = bool(self.miss)
        nov = 0.0
        for i in range(OL.NX):
            if i < 12:
                nov += abs(x[i] - self.xavg[i])
            self.xavg[i] += 0.05 * (x[i] - self.xavg[i])
        nov /= 12
        h = self.h
        pres = x[8]
        h[0] += 0.02 * (0.42 - h[0]) + 0.02 * min(nov, 0.4)
        h[1] += 0.02 * (0.7 - h[1]) - 0.08 * max(0, nov - 0.25)
        h[2] += 0.03 * (0.2 + 0.6 * pres - h[2])
        h[3] = 0.85 * h[3] + 0.15 * acted
        if OL.CONTAGION and not unseen:  # seeing another tremble more than itself unsettles it (stage 9)
            h[1] -= OL.CONTAGION * (1 if self.close_gain is None else self.close_gain) * max(0, x[13] - x[17] - 0.1)
        if self.company_t > 0:  # company: another reached toward it, and it steadies
            self.company_t -= 1
            if OL.COMPANY_CONTACT:
                h[2] += 0.03 * (0.8 - h[2])
            h[1] += min(0.9, 0.02 * OL.COMPANY) * (0.7 - h[1])
        self.h = [oclip(v + self.rng.normal(0, 0.003), 0, 1) for v in h]

    def screen_surprise(self, xe, xi):
        if not len(self.n):
            return None
        x = np.asarray(list(xe) + list(xi), dtype=float)
        a, b = self._parts(x, (0, 1, 2))
        ll = np.log(np.asarray(self.n, dtype=float)) + a + b
        kb = int(np.argmax(ll))
        z = (x[2] - self.mu[kb, 2]) ** 2 / self.vr[kb, 2]
        return min(z, 30)

    def add_colour(self, hue_deg, by):
        a = (hue_deg * math.pi) / 180
        sc = self.screen
        sc["vx"] = sc["vx"] + math.cos(a)
        sc["vy"] = sc["vy"] + math.sin(a)
        sc["str"] = min(1, sc["str"] + 1)
        sc["hue"] = ((math.atan2(sc["vy"], sc["vx"]) * 180) / math.pi + 360) % 360
        sc["by"] = by

    def fade_screen(self):
        sc = self.screen
        sc["str"] *= 0.93
        sc["vx"] *= 0.93
        sc["vy"] *= 0.93

    def _qvals(self, b):
        """Value of every act given a belief: sum over patterns, accumulated in order."""
        b = np.asarray(b, dtype=float)
        return np.cumsum(b[:, None] * self.Q[:len(b)], axis=0)[-1]

    def top_words(self):
        """The words it can say: the ones it has heard most, up to NWORDS."""
        return [w for w, _ in sorted(self.lexicon.items(), key=lambda kv: (-kv[1], kv[0]))][:OL.NWORDS]

    def tick(self, sense, user_colour=None, word=None, incoming=(), incoming_words=()):
        """One step. sense: dict of outside readings (typing, vowels, speed, px, py, presence, seen, noBody, unseen).
        user_colour: hue index the visitor shows, or None. word: a word the visitor says, or None.
        incoming: hues (degrees) the others put on their screens last step. incoming_words: words the others said
        (strings, or dicts {'w': word, 'from': speaker index} for voices). Returns what it did."""
        self.age += 1
        voice = None
        if not word and len(incoming_words):
            iw = incoming_words[0]
            if isinstance(iw, str):
                word = iw
            else:
                word = iw["w"]
                voice = iw["from"] if OL.VOICES else None
        if word:
            self.word = dict(code=voice_code(word, voice), str=1.0)
            self.heard_from = voice
            self.lexicon[word] = self.lexicon.get(word, 0) + 1
            if len(self.lexicon) > 60:
                ks = sorted(self.lexicon.keys(), key=lambda k: self.lexicon[k])
                del self.lexicon[ks[0]]
        came = set()
        if len(incoming):
            for hh in incoming:
                self.add_colour(hh, "others")
            came.add("others")
            self.others_colours += len(incoming)
        if user_colour is not None:
            self.add_colour(OL.HUES[user_colour], "you")
            came.add("you")
            self.you_colours += 1
            if self.age - self.last_own_mark <= 12:
                self.answers += 1
                if OL.HUES[user_colour] == self.last_own_hue:
                    self.echoes += 1
        act = 0
        if self.mode == "awake" and self.belief is not None and len(self.belief):
            act = self.rng.choice(osoftmax(self._qvals(self.belief) / 0.05))
            if act == 11:
                if not OL.REACH:
                    act = 0
            elif act >= 7:
                w = self.recall_word() if OL.RECALL else (self.top_words()[act - 7] if act - 7 < len(self.top_words()) else None)
                if not w or word or self.mute:
                    act = 0
                else:
                    self.say(w)
            elif act > 0 and user_colour is None:
                self.add_colour(OL.HUES[act - 1], "self")
                came.add("self")
                self.marks += 1
                self.last_own_mark = self.age
                self.last_own_hue = OL.HUES[act - 1]
                hs = self.hue_stats[act - 1]
                hs["n"] += 1
                for i in range(4):
                    hs["s"][i] += self.h[i]
                    hs["q"][i] += self.h[i] ** 2
            elif act > 0:
                act = 0
        acted = 1 if act > 0 else 0
        fresh = next(iter(came)) if len(came) == 1 else None
        self.miss = UNSEEN if sense.get("unseen") else None
        x_real = self.outside(sense)
        if self.mode != "awake":
            return self.sleep_tick(x_real, sense)
        self.body_step(x_real, acted)
        xi = self.feel(acted)
        if fresh:
            s = self.screen_surprise(x_real, xi)
            if s is not None:
                m = self.mirror
                key = "own" if fresh == "self" else ("you" if fresh == "you" else "others")
                wk = key + "W"
                m[wk] = (m.get(wk) or []) + [round(s * 100) / 100]
                m[wk] = m[wk][-60:]
                m[key] = sum(m[wk]) / len(m[wk])
                nk = {"own": "nOwn", "you": "nYou", "others": "nOthers"}[key]
                m[nk] = m.get(nk, 0) + 1
        k = self.learn(x_real, xi)
        b2 = self.interpret(x_real, xi)
        if OL.READ_CONTAGION and len(b2):  # stage 14: the trembling it expects of the watched one unsettles it
            ex = float(np.cumsum(b2 * self.mu[:len(b2), 13])[-1])
            self.h[1] = oclip(self.h[1] - OL.READ_CONTAGION * max(0, ex - x_real[17] - 0.1), 0, 1)
        if self.prev < len(self.T):
            self.T[self.prev][k] += 1
        felt = xi[OL.NY - 1] / 3
        # learning what to do: feel better, and forecast its own feelings well (its wish to understand itself)
        self.hist.append(self.belief if self.belief is not None else b2)
        clar = 0.0
        if len(self.hist) > OL.H:
            bo = self.hist.pop(0)
            pr = 0.0
            for j, p in enumerate(bo):
                pr += p * self.F[j]
            e = felt - pr
            for j, p in enumerate(bo):
                self.F[j] += 0.05 * p * e
            clar = abs(e)
            self.last_clar = clar
        if self.belief is not None and len(self.belief):
            r = 10 * (self.felt - felt) - 0.1 * felt - OL.KAPPA * 10 * clar
            self.last_r = dict(r=r, dfelt=self.felt - felt, clar=clar, act=act)
            mx = float(np.max(self._qvals(b2)))
            cur = float(self._qvals(self.belief)[act])
            tg = r + OL.GAMMA * mx
            nb = len(self.belief)
            self.Q[:nb, act] += 0.1 * np.asarray(self.belief) * (tg - cur)
        while len(self.hm) < len(self.n):
            self.hm.append(dict(n=0, h=list(self.h)))
        m = self.hm[k]
        m["n"] += 1
        lr = max(1 / m["n"], 0.02)
        for i in range(4):
            m["h"][i] += lr * (self.h[i] - m["h"][i])
        self.belief = b2
        self.felt = felt
        self.prev = k
        self.reading = k
        self.awake_ticks += 1
        self.fade_screen()
        self.word["str"] *= 0.95
        return dict(act=act, reading=k, x=x_real, y=xi, said=self.said if 7 <= act <= 10 else None, reached=act == 11)

    # ---------- the sensory gate and sleep
    def update_gate(self, absent_s):
        if self.mode == "awake" and absent_s > OL.ASLEEP_AFTER_S:
            self.mode = "falling"
        if self.mode == "asleep":
            ph = (self.sleep_ticks % OL.PERIOD) / OL.PERIOD
            self.gate = 0.03 + OL.GMAX * (0.5 - 0.5 * math.cos(2 * math.pi * ph)) ** 2
        if self.mode == "falling":
            self.gate = max(0.03, self.gate - 0.012)
            if self.gate <= 0.05:
                self.mode = "asleep"
                self.sleep_ticks = 0
            if absent_s < 2:
                self.mode = "awake"
                self.gate = 1.0
        if self.mode == "waking":
            self.gate = min(1, self.gate + 0.12)
            if self.gate >= 1:
                self.mode = "awake"

    def imagined(self, prev):
        row = self.T[prev] if prev < len(self.T) else []
        tot = sum(row) + 0.01 * len(self.n)
        out = np.zeros(OL.NX)
        for j in range(len(self.n)):
            p = ((row[j] if j < len(row) else 0) + 0.01) / tot
            out += p * self.mu[j, :OL.NX]
        return out

    def sleep_tick(self, x_real, sense):
        """Asleep: the body drifts back to rest with slow restless spells; nothing is decided; the gate lets a little in."""
        t = self.sleep_ticks
        self.sleep_ticks += 1
        wander = [0.2 * math.sin(t / 47), 0.18 * math.sin(t / 71 + 1), 0.15 * math.sin(t / 29 + 2), 0.05 * math.sin(t / 19)]
        self.h = [oclip(v + 0.05 * (OL.SET[i] + wander[i] - v) + self.rng.normal(0, 0.01), 0, 1) for i, v in enumerate(self.h)]
        xi = self.feel(0)
        g = self.gate
        im = self.imagined(self.prev)
        x = [g * v + (1 - g) * im[i] + self.rng.normal(0, 0.1) for i, v in enumerate(x_real)]
        k = self.prev
        if len(self.n):
            row = self.T[self.prev] if self.prev < len(self.T) else []
            ll = self.loglik(x, xi)
            tot = sum(row) + 0.01 * len(self.n)
            p = osoftmax([l + math.log(((row[j] if j < len(row) else 0) + 0.01) / tot) for j, l in enumerate(ll)])
            k = self.rng.choice(p)
        self.prev = k
        self.reading = k
        self.trace.append(dict(y=[round(v, 3) for v in xi], k=k, g=round(g, 3)))
        if len(self.trace) > OL.TRACE_MAX:
            self.trace.pop(0)
        self.fade_screen()
        self.word["str"] *= 0.95
        return dict(act=0, reading=k, x=x, y=xi)

    def sleep_for(self, steps, sense):
        """Sleep for a number of steps (compressed time away)."""
        if self.mode == "awake":
            self.mode = "asleep"
        for _ in range(steps):
            self.update_gate(1e9)
            self.sleep_tick(self.outside(sense), sense)

    def wake(self, x_cue, cue_label=""):
        """Woken: re-read the last stretch of the night with the waking world as dictionary. The report is written now."""
        seg = self.trace[-OL.REPORT_LEN:]
        self.mode = "waking"
        if not seg or not len(self.n):
            return None
        dreamt = [s["k"] for s in seg]
        report = []
        prev = dreamt[0]
        for s in seg:
            im = self.imagined(prev)
            x = [0.7 * v + 0.3 * im[i] for i, v in enumerate(x_cue)]
            ll = self.loglik(x, s["y"])
            b = int(np.argmax(ll))
            report.append(b)
            prev = b
        rep = dict(cue=cue_label, dreamt=stab(dreamt), report=stab(report))
        self.reports.insert(0, rep)
        self.reports = self.reports[:6]
        return rep

    # ---------- words
    def say(self, w):
        """Speaking: it puts one of its words out; it hears it itself, and so do the others."""
        sp = self.speech or dict(n=0, fit=0.0, base=0.0, nb=0, words={})
        self.speech = sp

        def err(r):
            return sum(abs(v - self.h[i]) for i, v in enumerate(r["ev"])) / 4 if r else None

        mine = err(self.evoke_word(w))
        others = [e for e in (err(self.evoke_word(x)) for x in self.top_words() if x != w) if e is not None]
        if mine is not None and others:
            sp["fit"] += mine
            sp["base"] += sum(others) / len(others)
            sp["nb"] += 1
        sp["n"] += 1
        sp["words"][w] = sp["words"].get(w, 0) + 1
        self.said = w
        self.said_at = self.age
        if self.speech_log is not None:
            self.speech_log.append(dict(t=self.age, w=w, mine=mine, others=(sum(others) / len(others)) if others else None))
        if not self.deaf:
            self.word = dict(code=voice_code(w, self.voice if OL.VOICES else None), str=1.0)

    def _sound_ll(self, code):
        N = float(sum(self.n))
        ll = []
        for k in range(len(self.n)):
            a = math.log(self.n[k] / N)
            for i in range(OL.HEAR):
                q = hear_idx(i)
                d = code[i] - self.mu[k, q]
                v = self.vr[k, q]
                a += -0.5 * ((d * d) / v + math.log(2 * math.pi * v))
            ll.append(a)
        return ll

    def evoke_word(self, w, code=None):
        """What a word calls up: the patterns its sound alone points to, and the inner state those go with (observer's view)."""
        if not len(self.n):
            return None
        code = word_code(w) if code is None else code
        p = osoftmax(self._sound_ll(code))
        top = int(np.argmax(p))
        ev = [0.0] * 4
        for k, q in enumerate(p):
            hm = self.hm[k]["h"] if k < len(self.hm) else OL.SET
            for i in range(4):
                ev[i] += q * hm[i]
        base = [0.0] * 4
        tot = 0
        for k, m in enumerate(self.hm):
            for i in range(4):
                base[i] += self.n[k] * m["h"][i]
            tot += self.n[k]
        if tot:
            base = [b / tot for b in base]
        return dict(word=w, heard=self.lexicon.get(w, 0), top=top, ev=ev, base=base, sharp=float(np.cumsum(p * p)[-1]))

    def company(self, ticks=20):
        """Another reached toward it."""
        self.company_t = max(self.company_t, ticks)

    def recall_word(self):
        """Stage 8: the word that comes to mind is the one whose sound goes best with the patterns it reads itself as."""
        ws = self.top_words()
        if not ws or self.belief is None or not len(self.belief):
            return None
        best, bs = None, -math.inf
        for w in ws:
            c = word_code(w)
            sc = 0.0
            for k, b in enumerate(self.belief):
                if b < 1e-4:
                    continue
                a = 0.0
                for i in range(OL.HEAR):
                    q = hear_idx(i)
                    dd = c[i] - self.mu[k, q]
                    v = self.vr[k, q]
                    a += -0.5 * ((dd * dd) / v + math.log(2 * math.pi * v))
                sc += b * a
            if sc > bs:
                bs, best = sc, w
        return best

    def expect_seen(self, w, code=None):
        """What a word leads it to expect to see of the one it watches (observer's view): channels 12-15."""
        if not len(self.n):
            return None
        code = word_code(w) if code is None else code
        p = osoftmax(self._sound_ll(code))
        return [float(np.cumsum(p * self.mu[:, 12 + i])[-1]) for i in range(4)]

    def colour_meaning(self):
        """How much its colour choices go with different inner states: 0 = not at all, 1 = completely (observer's view)."""
        used = [s for s in self.hue_stats if s["n"] >= 5]
        if len(used) < 2:
            return dict(tied=None, used=len(used))
        n = sum(s["n"] for s in used)
        between = total = 0.0
        for i in range(4):
            m = sum(s["s"][i] for s in used) / n
            total += sum(s["q"][i] for s in used) / n - m * m
            between += sum((s["n"] / n) * (s["s"][i] / s["n"] - m) ** 2 for s in used)
        return dict(tied=between / total if total > 1e-9 else 0, used=len(used))


Entity = Olvaso  # the JavaScript name
