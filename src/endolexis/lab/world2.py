"""
NewNeural - grown-up agents: a richer world and a body with many senses.

WORLD (12 x 12 grid)
  places: grass, pond (water), berry bushes, sun rocks, a cave, thorns, hills
  day and night (light, temperature), spells of rain
  "forest" version: a predator sleeps in its den by day and roams near the berry bushes at night
  "mountain" version: no predator; the berry bushes grow on steep hills

BODY (hidden, never read directly)
  energy, water, body temperature, injury, fatigue, arousal

EXTERNAL SENSES (16 channels)
  vision  : what is around (share of each kind of place in view) + brightness; fades at night
  hearing : water babbling, growling, rain
  smell   : berries, predator
  touch   : wet, skin temperature, something sharp

INTERNAL SENSES (12 channels, raw and unlabelled: fixed random mixtures + noise)
  gut (3), temperature (2), pain (2), fatigue (2), heartbeat (2, with a real rhythm that
  speeds up with arousal), and one innate channel: how bad it feels overall

AGENT
  forms concepts = joint patterns of outside + inside, reads itself by asking which concept
  explains how it feels now (the outside as dictionary), and learns which moves, from each
  self-reading, make it feel better (Q-learning on its own self-readings; the reward is
  the change in the innate "how bad" feeling).

Run:  python -m endolexis.lab.world2      (life test + "racing heart" test; writes results/12_*.png)
"""
import argparse
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TILES = ["grass", "water", "bush", "rock", "cave", "thorns", "hill"]
GRASS, WATER, BUSH, ROCK, CAVE, THORNS, HILL = range(7)
MOVES = [(-1, 0), (1, 0), (0, -1), (0, 1), (0, 0)]          # N S W E rest
EXT_NAMES = [f"see:{t}" for t in TILES] + ["see:light", "hear:water", "hear:growl", "hear:rain",
                                           "smell:berries", "smell:predator", "touch:wet",
                                           "touch:skin-temp", "touch:sharp"]
EXT_DIM = len(EXT_NAMES)                                     # 16
INT_DIM = 12
VITALS = ["energy", "water", "temperature", "injury", "fatigue", "arousal"]
SETPOINT = np.array([0.7, 0.7, 0.6, 0.0, 0.2, 0.25])
WEIGHT = np.array([1.0, 1.0, 2.0, 2.0, 0.5, 0.5])
DAY = 240


# ----------------------------------------------------------------------------- world
class World2:
    def __init__(self, kind="forest", size=12, seed=0):
        self.kind, self.n = kind, size
        rng = np.random.default_rng(seed)
        g = np.zeros((size, size), int)
        g[2:4, 2:4] = WATER                                    # the pond
        g[9:11, 1:3] = CAVE
        for (r, c) in [(1, 8), (6, 1), (5, 9), (10, 6)]:
            g[r, c] = ROCK
        bushes = [(7, 7), (7, 9), (8, 8), (9, 7), (9, 9), (8, 10)]
        for (r, c) in bushes:
            g[r, c] = BUSH
        free = list(zip(*np.where(g == GRASS)))
        for i in rng.choice(len(free), 8, replace=False):
            g[free[i]] = THORNS
        if kind == "mountain":                                 # bushes sit on steep slopes
            for r in range(6, 12):
                for c in range(5, 12):
                    if g[r, c] == GRASS:
                        g[r, c] = HILL
        self.grid = g
        self.stock = np.where(g == BUSH, 1.0, 0.0)
        self.rng = np.random.default_rng(seed + 1)
        self.t = 0
        self.rain = False
        self.den = np.array([11, 11])
        self.pred = self.den.copy() if kind == "forest" else None

    def light(self):
        return float(np.clip(0.5 + 0.6 * np.cos(2 * np.pi * self.t / DAY), 0.03, 1))

    def ambient(self, pos):
        if self.grid[tuple(pos)] == CAVE:
            return 0.55
        a = 0.3 + 0.35 * self.light()
        if self.grid[tuple(pos)] == ROCK:
            a += 0.25 * self.light()
        return a - (0.12 if self.rain else 0)

    def dist(self, pos, kind):
        cells = np.argwhere(self.grid == kind)
        return np.abs(cells - pos).sum(1).min() if len(cells) else 99

    def pred_dist(self, pos):
        return 99 if self.pred is None else int(np.abs(self.pred - pos).sum())

    def step(self, pos):
        self.t += 1
        if self.rain:
            self.rain = self.rng.random() > 0.03
        else:
            self.rain = self.rng.random() < 0.004
        self.stock = np.clip(self.stock + 0.004 * (self.grid == BUSH), 0, 1)
        if self.pred is not None and self.light() >= 0.35:      # by day it sleeps in its den
            self.pred = self.den.copy()
        elif self.pred is not None:                             # at night it roams near the bushes
            d = self.pred_dist(pos)
            if d <= 3 and self.rng.random() < 0.25:
                step = np.sign(pos - self.pred)
                k = self.rng.integers(2)
                mv = np.zeros(2, int)
                mv[k] = step[k] if step[k] != 0 else step[1 - k]
            else:
                mv = np.array(MOVES[self.rng.integers(4)])
                if np.abs(self.pred + mv - self.den).sum() > 4:
                    mv = np.sign(self.den - self.pred)
            self.pred = np.clip(self.pred + mv, 0, self.n - 1)

    def sense(self, pos, rng, noise=0.1):
        L = self.light()
        r0, c0 = max(pos[0] - 1, 0), max(pos[1] - 1, 0)
        view = self.grid[r0:pos[0] + 2, c0:pos[1] + 2].ravel()
        frac = np.bincount(view, minlength=len(TILES)) / len(view)
        vision = np.concatenate([L * frac, [L]]) + rng.normal(0, noise + 0.15 * (1 - L), len(TILES) + 1)
        dp = self.pred_dist(pos)
        hearing = [max(0, 1 - self.dist(pos, WATER) / 4), max(0, 1 - dp / 6), float(self.rain)]
        bushes = np.argwhere(self.grid == BUSH)
        db = np.abs(bushes - pos).sum(1)
        smell = [min(1, (self.stock[tuple(bushes.T)] * np.exp(-db / 2)).sum()), np.exp(-dp / 3)]
        tile = self.grid[tuple(pos)]
        touch = [float(self.rain or tile == WATER), self.ambient(pos), float(tile == THORNS)]
        other = np.array(hearing + smell + touch) + rng.normal(0, noise, 8)
        return np.concatenate([vision, other])


# ----------------------------------------------------------------------------- body
class Body2:
    def __init__(self, nerves_seed=42, seed=0):
        r = np.random.default_rng(nerves_seed)                  # same seed = same nervous system
        self.maps = {"gut": (r.normal(0, 2, (3, 3)), r.normal(0, .4, 3)),
                     "thermo": (r.normal(0, 2, (2, 1)), r.normal(0, .4, 2)),
                     "pain": (r.normal(0, 2, (2, 1)), r.normal(0, .4, 2)),
                     "fatigue": (r.normal(0, 2, (2, 1)), r.normal(0, .4, 2))}
        self.rng = np.random.default_rng(seed)
        self.s = SETPOINT.copy()
        self.s[3] = 0.0
        self.beat = 0.0

    def distress(self, s=None):
        s = self.s if s is None else s
        return float(np.sqrt((WEIGHT * (s - SETPOINT) ** 2).sum()))

    def step(self, world, pos, action):
        e, w, tp, dmg, fat, ar = self.s
        tile = world.grid[tuple(pos)]
        moving = action != 4
        climbing = moving and tile == HILL
        e -= 0.0015 + 0.001 * moving + 0.005 * climbing
        w -= 0.002 + 0.0005 * moving
        if tile == BUSH and world.stock[tuple(pos)] > 0.2:
            e += 0.08
            world.stock[tuple(pos)] -= 0.2
        if tile == WATER:
            w += 0.1
        tp += 0.06 * (world.ambient(pos) - tp) + 0.004 * moving
        if tile == THORNS:
            dmg += 0.06
        if world.pred_dist(pos) <= 1:
            dmg += 0.2
            world.pred = world.den.copy()                         # strikes, then slinks back
        dmg -= 0.01
        fat += 0.001 + 0.0015 * moving + 0.005 * climbing
        if not moving:
            fat -= 0.03 if tile == CAVE else 0.015
        threat = max(0, 1 - world.pred_dist(pos) / 5)
        ar += 0.2 * (0.15 + 0.8 * threat + 0.6 * dmg + 0.7 * climbing + 0.1 * moving - ar)
        self.s = np.clip([e, w, tp, dmg, fat, ar], 0, 1)

    def feel(self, s=None, noise=0.05, rng=None):
        """Raw internal senses, unlabelled. Last channel = how bad it feels (innate)."""
        s = self.s if s is None else s
        rng = self.rng if rng is None else rng
        e, w, tp, dmg, fat, ar = s
        f = lambda k, x: np.tanh(self.maps[k][0] @ np.atleast_1d(x) + self.maps[k][1])
        self.beat += 0.4 + 1.6 * ar                               # the heart beats faster when aroused
        heart = [np.sin(self.beat) * (0.3 + 0.7 * ar), 2 * ar - 1]
        out = np.concatenate([f("gut", [e - .5, w - .5, dmg]), f("thermo", tp - .5),
                              f("pain", dmg), f("fatigue", fat - .3), heart])
        return np.concatenate([out + rng.normal(0, noise, len(out)), [3 * self.distress(s)]])


# ----------------------------------------------------------------------------- agent
class Agent2:
    def __init__(self, ext_dim=EXT_DIM, max_concepts=60, new_thresh=2.5, seed=0):
        self.ed, self.max, self.thr = ext_dim, max_concepts, new_thresh
        self.mu, self.var, self.n = [], [], []
        self.rng = np.random.default_rng(seed)
        self.learning = True

    def _parts(self, x, k):
        t = -0.5 * ((x - self.mu[k]) ** 2 / self.var[k] + np.log(2 * np.pi * self.var[k]))
        return t[:self.ed].sum(), t[self.ed:].sum()

    def loglik(self, x_ext, x_int, lam_ext=1.0, lam_int=1.0):
        x = np.concatenate([x_ext, x_int])
        N = sum(self.n)
        return np.array([np.log(self.n[k] / N) + lam_ext * a + lam_int * b
                         for k, (a, b) in enumerate(self._parts(x, k) for k in range(len(self.mu)))])

    def interpret(self, x_ext, x_int, lam_ext=1.0, lam_int=1.0):
        ll = self.loglik(x_ext, x_int, lam_ext, lam_int)
        p = np.exp(ll - ll.max())
        return p / p.sum()

    def learn(self, x_ext, x_int):
        x = np.concatenate([x_ext, x_int])
        if self.mu:
            if not self.learning:
                return int(np.argmax(self.interpret(x_ext, x_int)))
            k = int(np.argmax([sum(self._parts(x, j)) for j in range(len(self.mu))]))
            z = (x - self.mu[k]) ** 2 / self.var[k]
            if max(z[:self.ed].mean(), z[self.ed:].mean()) < self.thr or len(self.mu) >= self.max:
                self.n[k] += 1
                lr = max(1 / self.n[k], 0.02)
                lv = min(lr, 0.05)
                d = x - self.mu[k]
                self.mu[k] += lr * d
                self.var[k] = np.clip((1 - lv) * self.var[k] + lv * d ** 2, 0.01, 0.5)
                return k
        self.mu.append(x.copy())
        self.var.append(np.full_like(x, 0.3))
        self.n.append(1)
        return len(self.mu) - 1

    # acting: Q-learning on its own (soft) self-reading; reward = change in felt badness
    def qtab(self):
        K = len(self.mu)
        if not hasattr(self, "_Q") or self._Q.shape[0] < K:
            Q = np.zeros((self.max, len(MOVES)))
            if hasattr(self, "_Q"):
                Q[:self._Q.shape[0]] = self._Q
            self._Q = Q
        return self._Q

    def act(self, b, temp=0.05):
        v = b @ self.qtab()[:len(b)] / temp
        p = np.exp(v - v.max())
        return int(self.rng.choice(len(MOVES), p=p / p.sum()))

    def update(self, b, a, r, b2, alpha=0.1, gamma=0.98):
        Q = self.qtab()
        target = r + gamma * (b2 @ Q[:len(b2)]).max()
        Q[:len(b), a] += alpha * b * (target - b @ Q[:len(b), a])


def live(world, body, agent, steps, policy="self", seed=0):
    rng = np.random.default_rng(seed)
    pos = np.array([5, 5])
    xi0, xe0 = body.feel(), world.sense(pos, rng)
    c = agent.learn(xe0, xi0)
    b = agent.interpret(xe0, xi0)
    prev_felt = xi0[-1] / 3
    log = {k: [] for k in ("pos", "concept", "vitals", "distress", "ext", "int", "light", "rain", "pred")}
    for t in range(steps):
        a = agent.act(b) if policy == "self" else int(rng.integers(len(MOVES)))
        pos = np.clip(pos + MOVES[a], 0, world.n - 1)
        world.step(pos)
        body.step(world, pos, a)
        xe, xi = world.sense(pos, rng), body.feel()
        c = agent.learn(xe, xi)
        b2 = agent.interpret(xe, xi)
        felt = xi[-1] / 3                                        # the innate "how bad" channel
        if policy == "self":
            agent.update(b, a, 10 * (prev_felt - felt) - 0.1 * felt, b2)
        prev_felt, b = felt, b2
        log["pos"].append(pos.copy())
        log["concept"].append(c)
        log["vitals"].append(body.s.copy())
        log["distress"].append(body.distress())
        log["ext"].append(xe)
        log["int"].append(xi)
        log["light"].append(world.light())
        log["rain"].append(world.rain)
        log["pred"].append(world.pred_dist(pos))
    return {k: np.array(v) for k, v in log.items()}


def raise_agent2(kind, steps, seed, policy="self"):
    world = World2(kind, seed=seed)
    body = Body2(nerves_seed=42, seed=seed)
    agent = Agent2(seed=seed)
    log = live(world, body, agent, steps, policy, seed)
    return world, body, agent, log


def describe(log, K):
    """Observer's labels for each concept: typical place, time, and the body state it goes with."""
    out = {}
    for k in range(K):
        m = log["concept"] == k
        if not m.any():
            out[k] = "(unused)"
            continue
        # typical place = most common tile under the agent
        v = log["vitals"][m].mean(0)
        flags = [n for n, val, sp in zip(VITALS, v, SETPOINT) if abs(val - sp) > 0.2]
        day = "day" if log["light"][m].mean() > 0.5 else "night"
        out[k] = f"{day}, " + (", ".join(flags) if flags else "body fine")
    return out


# ----------------------------------------------------------------------------- tests
def test_life(steps, seeds, out):
    res = {"self": [], "random": []}
    crit = {"self": [], "random": []}
    for s in range(seeds):
        for pol in res:
            w, b, a, log = raise_agent2("forest", steps, s + 1, pol)
            h = log["distress"][steps // 2:]
            v = log["vitals"][steps // 2:]
            res[pol].append(h.mean())
            crit[pol].append(np.mean((v[:, 0] < .15) | (v[:, 1] < .15) | (v[:, 3] > .5)))
            if s == 0:
                if pol == "self":
                    keep = (w, b, a, log)
                else:
                    rand_log = log
    w, b, a, log = keep
    fig, ax = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    for i, n in enumerate(VITALS):
        ax[0].plot(log["vitals"][:, i], lw=0.6, label=n)
    ax[0].fill_between(range(steps), 0, 1, where=log["light"] < 0.3, color="k", alpha=0.06, label="night")
    ax[0].legend(fontsize=7, ncol=7, loc="upper right")
    ax[0].set_title("Hidden body (never read directly); shaded = night")
    ax[1].scatter(range(steps), log["concept"], s=1, c=log["light"], cmap="cividis")
    ax[1].set_title(f"Self-readings: {len(a.mu)} concepts (colour = daylight)")
    win = 300
    sm = lambda x: np.convolve(x, np.ones(win) / win, mode="valid")
    ax[2].plot(sm(log["distress"]), label="self-interpreting agent")
    ax[2].plot(sm(rand_log["distress"]), label="random mover (same learning)", alpha=0.8)
    ax[2].legend(fontsize=8)
    ax[2].set_title("How bad it feels, 300-step average")
    plt.tight_layout()
    plt.savefig(os.path.join(out, "12_life2.png"), dpi=110)
    plt.close()
    m = lambda d: np.mean(d)
    lines = ["== Life in the new world (forest, with predator) ==",
             f"{seeds} agents, {steps} steps; second half of life",
             f"  how bad it feels : self {m(res['self']):.3f} | random {m(res['random']):.3f} "
             f"(self better in {sum(x < y for x, y in zip(res['self'], res['random']))}/{seeds})",
             f"  time in danger   : self {m(crit['self']):.3f} | random {m(crit['random']):.3f}",
             f"  concepts formed (agent 1): {len(a.mu)}"]
    return lines, keep


def test_racing_heart(steps, seeds, out):
    """Schachter & Singer in silico: same racing heart, two worlds. What does each expect to find?"""
    rows = []
    for s in range(seeds):
        for kind in ("forest", "mountain"):
            w, b, a, log = raise_agent2(kind, steps, s + 1)
            a.learning = False
            probe = Body2(nerves_seed=42, seed=999)
            mu_ext = np.array(a.mu)[:, :EXT_DIM]
            for label, ar in (("calm", 0.2), ("racing heart", 0.9)):
                exp = np.zeros(EXT_DIM)
                for rep in range(40):
                    st = SETPOINT.copy()
                    st[5] = ar
                    p = a.interpret(np.zeros(EXT_DIM), probe.feel(st), lam_ext=0.0)   # eyes closed
                    exp += p @ mu_ext / 40
                rows.append((s, kind, label, exp))
    keys = ["hear:growl", "smell:predator", f"see:hill", "see:bush"]
    idx = [EXT_NAMES.index(k) for k in keys]
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.5), sharey=True)
    summary = {}
    for j, kind in enumerate(("forest", "mountain")):
        for lab, off, col in (("calm", -0.2, "lightgray"), ("racing heart", 0.2, "tab:red")):
            vals = np.array([r[3][idx] for r in rows if r[1] == kind and r[2] == lab])
            summary[(kind, lab)] = vals.mean(0)
            ax[j].bar(np.arange(len(keys)) + off, vals.mean(0), 0.4, yerr=vals.std(0) / np.sqrt(len(vals)),
                      color=col, label=lab, capsize=3)
        ax[j].set_xticks(range(len(keys)))
        ax[j].set_xticklabels(keys)
        ax[j].set_title(f"Raised in the {kind}: with eyes closed, what does it expect around it?")
        ax[j].legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(out, "12_racing_heart.png"), dpi=110)
    plt.close()
    lines = ["", "== Racing heart: same body, same feeling, two worlds (eyes closed) ==",
             "expected outside, calm -> racing heart:"]
    for kind in ("forest", "mountain"):
        c, r = summary[(kind, "calm")], summary[(kind, "racing heart")]
        lines.append(f"  {kind:<9}" + "  ".join(f"{k} {c[i]:.2f}->{r[i]:.2f}" for i, k in enumerate(keys)))
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=20000)
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    L, _ = test_life(args.steps, args.seeds, args.out)
    L += test_racing_heart(args.steps, args.seeds, args.out)
    text = "\n".join(L)
    print(text)
    with open(os.path.join(args.out, "world2_report.txt"), "w") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
