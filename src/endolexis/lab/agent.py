"""
Endolexis Lab - a first self-explaining agent.

The agent's job is NOT to solve the world. Its job is to make sense of its own
internal state, using the outside world as the dictionary.

  Body      : hidden variables (energy, warmth, water) that drift and react to
              where the agent is. The agent can never read them directly.
  Feeling   : a raw, unlabeled interoceptive vector - a fixed random nonlinear
              mix of the hidden body state, plus an irrelevant internal rhythm
              ("heartbeat") and noise. On its own, this is chaos.
              One channel is innate: distress (distance from a setpoint).
  World     : places that look a certain way (external features) and that
              change the body.
  Agent     : forms "concepts" on the fly. A concept is a joint pattern:
              "when the world looks like THIS, I feel like THAT".
              To interpret itself, it asks which concept best explains the
              current feeling, given what it sees outside. How much it trusts
              the outside vs. the inside is a precision weight.
  Acting    : from each self-reading it learns which move made it feel better
              (felt distress going down), plus curiosity about moves it
              hasn't tried from that self-reading yet.

Experiments
  1. life       : does self-interpretation help it stay alive vs. acting randomly?
  2. waking     : outside input fades in from noise (eyes opening). Watch the
                  interpretation jump between readings and then settle.
  3. dictionary : two agents with IDENTICAL bodies, raised in different worlds.
                  Present the same internal feeling with no outside input.
                  Do they read it differently?

Run:  python -m endolexis.lab.agent            (needs numpy, matplotlib)
"""
import argparse
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ENERGY, WARMTH, WATER = 0, 1, 2
VAR_NAMES = ["energy", "warmth", "water"]
SETPOINT = np.array([0.6, 0.6, 0.6])
EXT_DIM = 6
DWELL = 4  # steps spent in a place before deciding again


# ----------------------------------------------------------------------------- world
class World:
    def __init__(self, name, contexts, effects, seed=0):
        rng = np.random.default_rng(seed)
        self.name = name
        self.contexts = contexts
        self.effects = np.array(effects, float)
        self.protos = rng.normal(0, 1, (len(contexts), EXT_DIM))
        self.rng = np.random.default_rng(seed + 100)

    def observe(self, ctx, clarity=1.0, noise=0.3):
        """External sensation. clarity<1 mixes in junk (eyes half-open)."""
        p = self.protos[ctx]
        junk = self.rng.normal(0, 1, EXT_DIM)
        return clarity * p + (1 - clarity) * junk + self.rng.normal(0, noise, EXT_DIM)


WORLD_A = dict(  # rich in water distinctions
    name="World A (meadow)",
    contexts=["sun rock", "shade", "pond", "berry bush", "open field"],
    effects=[[0.00, +0.04, -0.03],
             [0.00, -0.02, 0.00],
             [0.00, -0.03, +0.05],
             [+0.05, 0.00, -0.01],
             [-0.01, +0.01, -0.01]],
)
WORLD_B = dict(  # rich in warmth distinctions
    name="World B (mountain)",
    contexts=["hot spring", "cold wind", "warm cave", "snow field", "berry bush"],
    effects=[[0.00, +0.06, +0.03],
             [0.00, -0.05, -0.01],
             [0.00, +0.03, 0.00],
             [-0.01, -0.03, +0.02],
             [+0.05, 0.00, -0.01]],
)


# ----------------------------------------------------------------------------- body
class Body:
    def __init__(self, interoception_seed=42, n_raw=10, seed=0):
        r = np.random.default_rng(interoception_seed)  # same seed = same "nervous system"
        self.A = r.normal(0, 1.8, (n_raw, 3))
        self.c = r.normal(0, 0.5, n_raw)
        self.rng = np.random.default_rng(seed)
        self.state = SETPOINT.copy()
        self.t = 0

    def step(self, effect):
        metabolism = np.array([-0.008, 0.0, -0.008])
        ambient = np.array([0.0, 0.02 * (0.45 - self.state[WARMTH]), 0.0])
        self.state = np.clip(self.state + effect + metabolism + ambient
                             + self.rng.normal(0, 0.005, 3), 0, 1)
        self.t += 1

    @staticmethod
    def distress_of(state):
        return float(np.linalg.norm(state - SETPOINT))

    def feel(self, state=None, noise=0.05):
        """Raw interoception: unlabeled, mixed, noisy. Last channel = innate distress."""
        s = self.state if state is None else state
        raw = np.tanh(self.A @ (s - 0.5) + self.c)
        raw[:2] += 0.3 * np.sin(self.t / 3.0)            # irrelevant internal rhythm
        raw += self.rng.normal(0, noise, raw.shape)
        return np.concatenate([raw, [3.0 * self.distress_of(s)]])


# ----------------------------------------------------------------------------- agent
class Agent:
    def __init__(self, n_actions, max_concepts=24, new_thresh=4.0, beta=0.15, temp=0.05, seed=0):
        self.mu, self.var, self.n = [], [], []
        self.n_actions = n_actions
        self.max_concepts = max_concepts
        self.new_thresh = new_thresh
        self.beta, self.temp = beta, temp
        self.trans = {}  # (concept, action) -> {next_concept: count}
        self.rng = np.random.default_rng(seed)
        self.learning = True

    # --- perception of self
    def _ll_parts(self, x, k):
        terms = -0.5 * ((x - self.mu[k]) ** 2 / self.var[k] + np.log(2 * np.pi * self.var[k]))
        return terms[:EXT_DIM].sum(), terms[EXT_DIM:].sum()

    def interpret(self, x_ext, x_int, lam_ext=1.0, lam_int=1.0):
        """Posterior over concepts. lam_* = how much the agent trusts each source."""
        if not self.mu:
            return None
        x = np.concatenate([x_ext, x_int])
        N = sum(self.n)
        logp = []
        for k in range(len(self.mu)):
            le, li = self._ll_parts(x, k)
            logp.append(np.log(self.n[k] / N) + lam_ext * le + lam_int * li)
        logp = np.array(logp)
        p = np.exp(logp - logp.max())
        return p / p.sum()

    def learn(self, x_ext, x_int):
        x = np.concatenate([x_ext, x_int])
        if self.mu:
            if not self.learning:
                return int(np.argmax(self.interpret(x_ext, x_int)))
            # judge novelty against the most SIMILAR concept, not the most common one
            k = int(np.argmax([sum(self._ll_parts(x, j)) for j in range(len(self.mu))]))
            z2 = (x - self.mu[k]) ** 2 / self.var[k]
            novel = max(z2[:EXT_DIM].mean(), z2[EXT_DIM:].mean())  # new outside OR new inside
            if novel < self.new_thresh or len(self.mu) >= self.max_concepts:
                self._update(k, x)
                return k
        if not self.learning:
            return None
        self.mu.append(x.copy())
        self.var.append(np.full_like(x, 0.3))
        self.n.append(1)
        return len(self.mu) - 1

    def _update(self, k, x):
        self.n[k] += 1
        lr = max(1.0 / self.n[k], 0.02)
        d = x - self.mu[k]
        self.mu[k] += lr * d
        lv = min(lr, 0.05)  # concepts broaden slowly, and only so far
        self.var[k] = np.clip((1 - lv) * self.var[k] + lv * d ** 2, 0.01, 0.5)

    # --- acting to stay well
    def expected_distress(self, k):
        return self.mu[k][-1] / 3.0

    def record(self, cur, a, delta):
        """Remember how FELT distress changed after doing a, starting from self-reading cur."""
        if cur is None or delta is None:
            return
        n, m = self.trans.get((cur, a), (0, 0.0))
        self.trans[(cur, a)] = (n + 1, m + (delta - m) / (n + 1))

    def choose(self, cur):
        vals = []
        for a in range(self.n_actions):
            n, m = self.trans.get((cur, a), (0, 0.0))
            vals.append(-m + self.beta / np.sqrt(1 + n))
        v = np.array(vals) / self.temp
        p = np.exp(v - v.max())
        p /= p.sum()
        return int(self.rng.choice(self.n_actions, p=p))


# ----------------------------------------------------------------------------- living
def live(world, body, agent, steps, policy="self", seed=0):
    rng = np.random.default_rng(seed)
    ctx = int(rng.integers(len(world.contexts)))
    cur = prev_cur = prev_a = None
    felt = felt_before = None
    log = dict(ctx=[], concept=[], body=[], distress=[])
    for t in range(steps):
        if t % DWELL == 0:
            if felt_before is not None:
                agent.record(prev_cur, prev_a, felt - felt_before)
            felt_before = felt
            if policy == "self" and cur is not None:
                a = agent.choose(cur)
            else:
                a = int(rng.integers(len(world.contexts)))
            prev_cur, prev_a, ctx = cur, a, a
        body.step(world.effects[ctx])
        xi = body.feel()
        felt = xi[-1]  # the one innate channel: how bad it feels
        cur = agent.learn(world.observe(ctx), xi)
        log["ctx"].append(ctx)
        log["concept"].append(cur)
        log["body"].append(body.state.copy())
        log["distress"].append(body.distress_of(body.state))
    for k in log:
        log[k] = np.array(log[k])
    return log


def describe_concepts(world, log, n_concepts):
    """OBSERVER's labels (the agent never sees these): where it usually was, how its body was."""
    out = {}
    for k in range(n_concepts):
        m = log["concept"] == k
        if m.sum() == 0:
            out[k] = "(never active)"
            continue
        place = world.contexts[np.bincount(log["ctx"][m]).argmax()]
        b = log["body"][m].mean(0)
        lvl = lambda v: "low" if v < 0.4 else ("high" if v > 0.78 else "ok")
        out[k] = f"@{place:<11}| " + ", ".join(f"{VAR_NAMES[i]} {lvl(b[i])}" for i in range(3))
    return out


def raise_agent(spec, steps, seed, policy="self", interoception_seed=42):
    world = World(spec["name"], spec["contexts"], spec["effects"], seed=seed)
    body = Body(interoception_seed=interoception_seed, seed=seed)
    agent = Agent(len(world.contexts), seed=seed)
    log = live(world, body, agent, steps, policy=policy, seed=seed)
    return world, body, agent, log


# ----------------------------------------------------------------------------- experiments
def exp_life(steps, seed, out):
    w, b, a, log_self = raise_agent(WORLD_A, steps, seed, "self")
    _, _, a_r, log_rand = raise_agent(WORLD_A, steps, seed, "random")
    labels = describe_concepts(w, log_self, len(a.mu))

    fig, ax = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    for i in range(3):
        ax[0].plot(log_self["body"][:, i], label=VAR_NAMES[i], lw=0.8)
    ax[0].axhline(0.6, color="k", ls=":", lw=0.8)
    ax[0].set_title("Hidden body state (the agent never sees this)")
    ax[0].legend(loc="upper right", fontsize=8)
    ax[1].scatter(range(steps), log_self["concept"], s=2, c=log_self["ctx"], cmap="tab10")
    ax[1].set_title("Which concept the agent uses to understand itself (color = true place)")
    ax[1].set_ylabel("concept #")
    win = 100
    sm = lambda x: np.convolve(x, np.ones(win) / win, mode="valid")
    ax[2].plot(sm(log_self["distress"]), label="self-interpreting agent")
    ax[2].plot(sm(log_rand["distress"]), label="random mover (same learning)", alpha=0.8)
    ax[2].set_title(f"Distress, {win}-step average (lower = better at staying alive)")
    ax[2].legend(fontsize=8)
    ax[2].set_xlabel("time step")
    plt.tight_layout()
    plt.savefig(os.path.join(out, "1_life.png"), dpi=120)
    plt.close()

    half = steps // 2
    report = [
        "== Experiment 1: life ==",
        f"concepts formed: {len(a.mu)}",
        f"mean distress, second half of life: self-interpreting {log_self['distress'][half:].mean():.3f}"
        f" | random {log_rand['distress'][half:].mean():.3f}",
        "concepts (observer's labels):",
    ] + [f"  C{k:<2} n={a.n[k]:<5} {labels[k]}" for k in range(len(a.mu))]
    return w, b, a, log_self, labels, report


def exp_waking(world, body, agent, labels, log, seed, out, place="berry bush", steps=40):
    agent.learning = False
    ctx = world.contexts.index(place)
    # wake up in a body state it has really lived at this place (its typical state there)
    body.state = log["body"][log["ctx"] == ctx].mean(0)
    truth = ", ".join(f"{VAR_NAMES[i]} {body.state[i]:.2f}" for i in range(3))
    clarity = 1 / (1 + np.exp(-(np.arange(steps) - steps * 0.55) / 3.0))
    posts, seq = [], []
    for t in range(steps):
        body.t += 1
        xe = world.observe(ctx, clarity=clarity[t])
        xi = body.feel()
        p = agent.interpret(xe, xi, lam_ext=clarity[t] ** 2, lam_int=1.0)
        posts.append(p)
        seq.append(int(np.argmax(p)))
    posts = np.array(posts)

    shown = sorted(set(seq) | set(np.argsort(posts.max(0))[-6:].tolist()))
    fig, ax = plt.subplots(2, 1, figsize=(11, 6), sharex=True,
                           gridspec_kw=dict(height_ratios=[1, 3]))
    ax[0].plot(clarity, color="k")
    ax[0].set_title("Waking: clarity of the outside world (eyes opening)")
    im = ax[1].imshow(posts[:, shown].T, aspect="auto", cmap="magma", vmin=0, vmax=1)
    ax[1].set_yticks(range(len(shown)))
    ax[1].set_yticklabels([f"C{k} {labels[k]}" for k in shown], fontsize=7)
    ax[1].set_title(f"How the agent reads itself, step by step (truly: at the {place}; {truth})")
    ax[1].set_xlabel("time step")
    plt.colorbar(im, ax=ax[1], label="belief")
    plt.tight_layout()
    plt.savefig(os.path.join(out, "2_waking.png"), dpi=120)
    plt.close()

    # compress the sequence of readings
    runs = []
    for k in seq:
        if not runs or runs[-1][0] != k:
            runs.append([k, 1])
        else:
            runs[-1][1] += 1
    report = ["", "== Experiment 2: waking ==",
              f"truth: at the {place}; {truth}. Sequence of self-readings (concept x steps):"]
    report += [f"  C{k:<2} x{n:<3} {labels[k]}" for k, n in runs]
    return report


def exp_dictionary(steps, seed, out):
    wa, ba, aa, la = raise_agent(WORLD_A, steps, seed, "self", interoception_seed=42)
    wb, bb, ab, lb = raise_agent(WORLD_B, steps, seed + 1, "self", interoception_seed=42)
    lab_a = describe_concepts(wa, la, len(aa.mu))
    lab_b = describe_concepts(wb, lb, len(ab.mu))

    g = np.linspace(0.05, 0.95, 40)
    probe = Body(interoception_seed=42, seed=999)
    maps = []
    for agent in (aa, ab):
        agent.learning = False
        M = np.zeros((len(g), len(g)), int)
        for i, water in enumerate(g):
            for j, warmth in enumerate(g):
                probe.t = 0
                xi = probe.feel(np.array([0.6, warmth, water]), noise=0.0)
                p = agent.interpret(np.zeros(EXT_DIM), xi, lam_ext=0.0)  # eyes closed
                M[i, j] = int(np.argmax(p))
        maps.append(M)

    fig, ax = plt.subplots(1, 2, figsize=(12, 5))
    for a_, M, title, n in ((ax[0], maps[0], WORLD_A["name"], len(aa.mu)),
                            (ax[1], maps[1], WORLD_B["name"], len(ab.mu))):
        a_.imshow(M, origin="lower", extent=[g[0], g[-1], g[0], g[-1]], cmap="tab20",
                  interpolation="nearest")
        for k in np.unique(M):
            ys, xs = np.where(M == k)
            a_.text(g[int(xs.mean())], g[int(ys.mean())], f"C{k}", ha="center", va="center",
                    fontsize=8, color="k", weight="bold")
        a_.set_title(f"Raised in {title}: {len(np.unique(M))} readings used ({n} concepts total)")
        a_.set_xlabel("true warmth")
        a_.set_ylabel("true water")
    fig.suptitle("Same body, same feelings, eyes closed: how each agent reads them (energy fixed)")
    plt.tight_layout()
    plt.savefig(os.path.join(out, "3_dictionary.png"), dpi=120)
    plt.close()

    probe_state = np.array([0.6, 0.3, 0.75])  # cool and well watered
    probe.t = 0
    xi = probe.feel(probe_state, noise=0.0)
    ka = int(np.argmax(aa.interpret(np.zeros(EXT_DIM), xi, lam_ext=0)))
    kb = int(np.argmax(ab.interpret(np.zeros(EXT_DIM), xi, lam_ext=0)))
    return ["", "== Experiment 3: different dictionaries ==",
            "identical body and nervous system; one probe feeling (cool, well watered), eyes closed:",
            f"  agent from A reads it as C{ka}: {lab_a[ka]}",
            f"  agent from B reads it as C{kb}: {lab_b[kb]}",
            f"distinct readings over the warmth x water grid: A {len(np.unique(maps[0]))}, "
            f"B {len(np.unique(maps[1]))}"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=6000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    w, b, a, log, labels, rep = exp_life(args.steps, args.seed, args.out)
    rep += exp_waking(w, b, a, labels, log, args.seed, args.out)
    rep += exp_dictionary(args.steps, args.seed, args.out)
    text = "\n".join(rep)
    print(text)
    with open(os.path.join(args.out, "report.txt"), "w") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
