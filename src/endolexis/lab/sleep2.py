"""
NewNeural - step 1 in the new world: sleep with many senses.

Agents grown up in the forest (world2.py) sleep in the cave through one night.
  - inside: the body drifts while asleep (hunger and thirst creep up, fatigue drains,
    injuries heal, the heart slows)
  - outside: the dark cave, the odd spell of rain, and now and then the predator
    prowls past the cave mouth (a growl and its smell)
  - a sensory gate rises and falls through 4 sleep cycles

Both interpreters have identical expectations (learned from waking life) and generative
replay; the only difference is the theory's claim:
  A_strong : evidence = inside + gate * outside
  B_fair   : evidence = inside + outside, always (gate * real + (1 - gate) * imagined)

Measures: dreaming across the cycle (stable scene changes), dreaming in shut vs open
phases (paired, per night), and whether a passing predator turns the dream into a
"danger" dream - by gate.

Run:  python -m endolexis.lab.sleep2     (needs world2.py, cycles.py)
"""
import argparse
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import world2 as w2
from .cycles import gate_schedule, stabilize, PERIOD, NIGHT, GMAX, N_PHASE

PROWL_LEN = 10
N_PROWLS = 8
GROWL = w2.EXT_NAMES.index("hear:growl")
MODELS = {"A": ("A strong: outside can be turned off", "tab:gray"),
          "B": ("B fair: outside always needed", "tab:blue")}


def prepare(seed, steps):
    world, body, agent, log = w2.raise_agent2("forest", steps, seed)
    agent.learning = False
    K = len(agent.mu)
    seq = log["concept"]
    T = np.ones((K, K)) * 0.01
    for a, b in zip(seq[:-1], seq[1:]):
        T[a, b] += 1
    T /= T.sum(1, keepdims=True)
    mu_ext = np.array(agent.mu)[:, :w2.EXT_DIM]
    danger = mu_ext[:, GROWL] > 0.25                 # observer's label: "danger" readings
    return dict(world=world, agent=agent, log=log, T=T, mu_ext=mu_ext, danger=danger, K=K)


def prowl_times(rng):
    out = []
    while len(out) < N_PROWLS:
        s = int(rng.integers(40, NIGHT - PROWL_LEN))
        if all(abs(s - o) > 50 for o in out):
            out.append(s)
    return sorted(out)


def sleep(ctx, model, gate, prowls, seed):
    rng = np.random.default_rng(seed)
    world = w2.World2("forest", seed=seed + 50)
    world.pred = None                                # the prowls are scripted below
    world.t = w2.DAY // 2                            # night
    cave = np.array([10, 1])
    body = w2.Body2(nerves_seed=42, seed=seed + 7)
    body.s = np.array([0.6, 0.6, 0.55, 0.15, 0.7, 0.3])   # tired, a little hurt, going to sleep
    agent, T, mu_ext = ctx["agent"], ctx["T"], ctx["mu_ext"]
    prev = int(np.argmax(agent.interpret(world.sense(cave, rng), body.feel())))
    on = np.zeros(NIGHT, bool)
    for s in prowls:
        on[s:s + PROWL_LEN] = True
    reading = []
    for t in range(NIGHT):
        world.t = w2.DAY // 2                        # stays night
        world.rain = world.rain if rng.random() > 0.01 else not world.rain
        e, w, tp, d, f, ar = body.s
        body.s = np.clip([e - 0.0004, w - 0.0005, tp + 0.05 * (0.55 - tp), d - 0.004,
                          f - 0.002, ar + 0.1 * (0.15 + (0.6 if on[t] else 0) - ar)]
                         + rng.normal(0, 0.003, 6), 0, 1)
        real = world.sense(cave, rng)
        if on[t]:                                    # the predator passes the cave mouth
            real[GROWL] = 0.8 + rng.normal(0, 0.1)
            real[w2.EXT_NAMES.index("smell:predator")] = 0.6 + rng.normal(0, 0.1)
        x_int = body.feel()
        g = gate[t]
        prior = T[prev]
        if model == "A":
            ll = agent.loglik(g * real, x_int, lam_ext=g)
        else:
            imagined = prior @ mu_ext
            ll = agent.loglik(g * real + (1 - g) * imagined + rng.normal(0, 0.1, w2.EXT_DIM), x_int,
                              lam_ext=1.0)
        logp = np.log(prior) + ll
        p = np.exp(logp - logp.max())
        prev = int(rng.choice(len(p), p=p / p.sum()))
        reading.append(prev)
    return np.array(reading), on


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--nights", type=int, default=6)
    ap.add_argument("--steps", type=int, default=20000)
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    gate = gate_schedule()
    phase_bin = (np.arange(NIGHT) % PERIOD) * N_PHASE // PERIOD
    gate_by_phase = np.array([gate[phase_bin == b].mean() for b in range(N_PHASE)])
    rate = {m: [] for m in MODELS}
    diff = {m: [] for m in MODELS}
    co = {m: [] for m in MODELS}
    inc = {m: [] for m in MODELS}
    nd = []
    for si in range(args.seeds):
        ctx = prepare(si + 1, args.steps)
        nd.append(int(ctx["danger"].sum()))
        for ni in range(args.nights):
            prowls = prowl_times(np.random.default_rng(9000 + 100 * si + ni))
            for m in MODELS:
                r, on = sleep(ctx, m, gate, prowls, seed=555 * si + 17 * ni)
                st = stabilize(r)
                ch = np.zeros(NIGHT, bool)
                ch[1:] = st[1:] != st[:-1]
                rate[m].append([100 * ch[phase_bin == b].mean() for b in range(N_PHASE)])
                shut, opn = 100 * ch[gate < 0.02].mean(), 100 * ch[gate > 0.25].mean()
                co[m].append((shut, opn))
                diff[m].append(opn - shut)
                dz = ctx["danger"][r]
                for s in prowls:
                    inc[m].append((gate[s:s + PROWL_LEN].mean(),
                                   dz[s:s + PROWL_LEN].mean() - dz[max(0, s - 30):s].mean()))

    fig, ax = plt.subplots(1, 2, figsize=(14, 5))
    ph = (np.arange(N_PHASE) + 0.5) / N_PHASE
    a2 = ax[0].twinx()
    a2.fill_between(ph, gate_by_phase, color="gray", alpha=0.15, step="mid")
    a2.set_ylim(0, 1)
    a2.set_yticks([])
    for m, (name, c) in MODELS.items():
        v = np.array(rate[m])
        ax[0].errorbar(ph, v.mean(0), yerr=v.std(0) / np.sqrt(len(v)), color=c, marker="o", ms=3,
                       capsize=2, label=name)
    ax[0].set_xlabel("phase within a sleep cycle (0 = gate shut, 0.5 = most open)")
    ax[0].set_ylabel("stable scene changes per 100 steps")
    ax[0].set_title("Many senses, same machinery: does dreaming follow the gate?")
    ax[0].legend(fontsize=8)
    bins = np.array([0, 0.02, 0.1, 0.2, 0.3, 0.4, 0.51])
    for m, (name, c) in MODELS.items():
        gi = np.array(inc[m])
        idx = np.digitize(gi[:, 0], bins) - 1
        mu = [gi[idx == k, 1].mean() if (idx == k).any() else np.nan for k in range(len(bins) - 1)]
        ax[1].plot((bins[:-1] + bins[1:]) / 2, mu, marker="o", color=c, label=name)
    ax[1].axhline(0, color="k", lw=0.5)
    ax[1].set_xlabel("gate while the predator prowls past")
    ax[1].set_ylabel("shift of the dream toward 'danger' readings")
    ax[1].set_title("Does a passing predator turn the dream into a danger dream?")
    plt.tight_layout()
    plt.savefig(os.path.join(args.out, "13_sleep2.png"), dpi=120)
    plt.close()

    L = ["== Sleep in the new world: strong A vs fair B (identical expectations + replay) ==",
         f"{args.seeds} forest agents x {args.nights} nights; 'danger' readings per agent: {nd}", ""]
    for m, (name, _) in MODELS.items():
        c, d, gi = np.array(co[m]), np.array(diff[m]), np.array(inc[m])
        L += [name,
              f"  scene changes /100 steps: shut {c[:, 0].mean():.2f}  open {c[:, 1].mean():.2f}",
              f"  open minus shut per night: {d.mean():+.2f} (s.e. {d.std() / np.sqrt(len(d)):.2f}), "
              f"positive on {np.sum(d > 0)}/{len(d)} nights",
              f"  predator woven in: shut {gi[gi[:, 0] < 0.02, 1].mean():+.2f}  "
              f"open {gi[gi[:, 0] > 0.25, 1].mean():+.2f}", ""]
    pd = np.array(diff["B"]) - np.array(diff["A"])
    L.append(f"B minus A, paired: {pd.mean():+.2f} (s.e. {pd.std() / np.sqrt(len(pd)):.2f}), "
             f"B larger on {np.sum(pd > 0)}/{len(pd)} nights")
    text = "\n".join(L)
    print(text)
    with open(os.path.join(args.out, "sleep2_report.txt"), "w") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
