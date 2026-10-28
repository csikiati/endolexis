"""
NewNeural - dreaming experiment.

Hypothesis (user): dreaming without ANY outside input is impossible. Dreams happen
only when the sleeping brain lets some outside input through; otherwise there is
nothing to interpret the internal state against.

Setup
  The agent first lives a normal life in World A (see agent.py) and forms
  its concepts. Then it sleeps. While asleep:
    - the body keeps drifting (slowly getting hungry and thirsty) -> internal input
    - the room is dark: the outside is unstructured sensory noise
    - a sensory GATE g in [0, 1] sets how much of the outside gets through
    - halfway through the night, a "sound of water" plays (the pond pattern)

  Two interpreters, identical concepts, differ only in how they read themselves:
    A "stored dictionary"  : sleep turns the outside down AND stops trusting it.
                             The agent reads itself from internal signals alone,
                             weighted by g.            (the conventional view)
    B "always-on dictionary": the interpreter ALWAYS compares the inside against an
                             outside. Asleep, that outside is whatever leaks through
                             the gate, filled in by the agent's own imagined version
                             of the scene it currently believes it is in.
                             (the user's theory, with imagination allowed)
    C "always-on, no imagination": the interpreter always compares against an
                             outside, and asleep that outside is ONLY what leaks
                             through the gate. g=0 means pure silence.
                             (the user's theory, taken literally)

Measures (per night)
  scene changes / 100 steps : does the dream move at all?
  distinct scenes           : how rich is it?
  body tracking             : does the dream follow the real (sleeping) body?
                              correlation between the body implied by the dream
                              and the true body, for energy and water
  life-like transitions     : fraction of scene changes that also happened in
                              waking life (vs. chance)
  incorporation             : does the water sound pull the dream to the pond?

Run:  python -m endolexis.lab.dream      (needs agent.py next to it)
"""
import argparse
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import agent as nn

GATES = [0.0, 0.03, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 1.0]
NIGHT = 400
EVENT_T, EVENT_LEN = 200, 15


def raise_and_index(seed):
    world, body, agent, log = nn.raise_agent(nn.WORLD_A, 6000, seed, "self")
    agent.learning = False
    K = len(agent.mu)
    labels = nn.describe_concepts(world, log, K)
    # observer's knowledge per concept: typical body and typical place
    body_of = np.array([log["body"][log["concept"] == k].mean(0) if (log["concept"] == k).any()
                        else np.full(3, np.nan) for k in range(K)])
    place_of = np.array([np.bincount(log["ctx"][log["concept"] == k], minlength=len(world.contexts)).argmax()
                         if (log["concept"] == k).any() else -1 for k in range(K)])
    # which concept-to-concept changes happened in waking life
    seq = log["concept"]
    seen = np.zeros((K, K), bool)
    for a, b in zip(seq[:-1], seq[1:]):
        if a != b:
            seen[a, b] = True
    return dict(world=world, body=body, agent=agent, log=log, labels=labels,
                body_of=body_of, place_of=place_of, seen=seen, K=K)


def sleep(ctx, model, g, seed, event=True):
    world, agent = ctx["world"], ctx["agent"]
    rng = np.random.default_rng(seed)
    body = nn.Body(interoception_seed=42, seed=seed + 7)
    body.state = ctx["log"]["body"][-1].copy()  # falls asleep in the state it lived in last
    body.state[nn.ENERGY] = max(body.state[nn.ENERGY], 0.6)  # went to bed fed
    body.state[nn.WATER] = max(body.state[nn.WATER], 0.6)    # ... and watered
    pond = world.contexts.index("pond")
    prev = int(ctx["log"]["concept"][-1])

    reading, true_body, event_on = [], [], []
    for t in range(NIGHT):
        # sleeping body: slow metabolism, warmth drifts to ambient
        s = body.state
        s += np.array([-0.0010, 0.01 * (0.45 - s[nn.WARMTH]), -0.0015]) + rng.normal(0, 0.003, 3)
        body.state = np.clip(s, 0, 1)
        body.t += 1
        x_int = body.feel()

        ev = event and EVENT_T <= t < EVENT_T + EVENT_LEN
        real = rng.normal(0, 1, nn.EXT_DIM)            # dark room: unstructured
        if ev:
            real = world.protos[pond] + rng.normal(0, 0.3, nn.EXT_DIM)  # sound of water

        if model == "A":
            x_ext = g * real
            p = agent.interpret(x_ext, x_int, lam_ext=g, lam_int=1.0)
        elif model == "C":
            x_ext = g * real
            p = agent.interpret(x_ext, x_int, lam_ext=1.0, lam_int=1.0)
        else:
            imagined = agent.mu[prev][:nn.EXT_DIM]
            x_ext = g * real + (1 - g) * imagined + rng.normal(0, 0.1, nn.EXT_DIM)
            p = agent.interpret(x_ext, x_int, lam_ext=1.0, lam_int=1.0)
        prev = int(np.argmax(p))
        reading.append(prev)
        true_body.append(body.state.copy())
        event_on.append(ev)
    return np.array(reading), np.array(true_body), np.array(event_on)


def score(ctx, reading, true_body, event_on):
    ch = np.flatnonzero(reading[1:] != reading[:-1])
    n_changes = len(ch)
    implied = ctx["body_of"][reading]
    track = []
    for v in (nn.ENERGY, nn.WATER):
        a, b = implied[:, v], true_body[:, v]
        track.append(np.corrcoef(a, b)[0, 1] if a.std() > 1e-9 and b.std() > 1e-9 else 0.0)
    if n_changes:
        lifelike = np.mean([ctx["seen"][reading[i], reading[i + 1]] for i in ch])
    else:
        lifelike = np.nan
    pond = ctx["world"].contexts.index("pond")
    at_pond = ctx["place_of"][reading] == pond
    before = at_pond[EVENT_T - 30:EVENT_T].mean()
    during = at_pond[event_on].mean()
    return dict(changes=100 * n_changes / len(reading),
                distinct=len(np.unique(reading)),
                tracking=float(np.nanmean(track)),
                lifelike=lifelike,
                incorporation=during - before)


def chance_lifelike(ctx):
    K = ctx["K"]
    off = ~np.eye(K, dtype=bool)
    return ctx["seen"][off].mean()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--nights", type=int, default=4)
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    metrics = ["changes", "distinct", "tracking", "lifelike", "incorporation"]
    R = {m: {k: np.full((args.seeds * args.nights, len(GATES)), np.nan) for k in metrics} for m in "ABC"}
    chance = []
    examples = {}
    for si in range(args.seeds):
        ctx = raise_and_index(si + 1)
        chance.append(chance_lifelike(ctx))
        for ni in range(args.nights):
            row = si * args.nights + ni
            for gi, g in enumerate(GATES):
                for m in "ABC":
                    r, b, e = sleep(ctx, m, g, seed=1000 * si + 10 * ni + gi)
                    sc = score(ctx, r, b, e)
                    for k in metrics:
                        R[m][k][row, gi] = sc[k]
                    if si == 0 and ni == 0:
                        examples[(m, g)] = (r, b, ctx)

    # ---------------- summary figure
    titles = {"changes": "Scene changes per 100 steps (does the dream move?)",
              "distinct": "Distinct scenes in a night (richness)",
              "tracking": "Body tracking (dream follows the real body: corr.)",
              "lifelike": "Scene changes that also happened in waking life",
              "incorporation": "Incorporation: water sound pulls dream to the pond"}
    fig, axes = plt.subplots(len(metrics), 1, figsize=(9, 14), sharex=True)
    xs = np.arange(len(GATES))
    for ax, k in zip(axes, metrics):
        for m, name, c in (("A", "A: stored dictionary (inside only)", "tab:blue"),
                           ("B", "B: always-on + imagination", "tab:red"),
                           ("C", "C: always-on, no imagination", "tab:orange")):
            v = R[m][k]
            mu = np.nanmean(v, 0)
            se = np.nanstd(v, 0) / np.sqrt(np.sum(~np.isnan(v), 0).clip(1))
            ax.errorbar(xs, mu, yerr=se, marker="o", label=name, color=c, capsize=3)
        if k == "lifelike":
            ax.axhline(np.mean(chance), color="gray", ls=":", label="chance")
        ax.axhline(0, color="k", lw=0.5)
        ax.set_title(titles[k], fontsize=10)
    axes[0].legend(fontsize=8)
    axes[-1].set_xticks(xs)
    axes[-1].set_xticklabels([str(g) for g in GATES])
    axes[-1].set_xlabel("sensory gate g (0 = outside completely shut out)")
    plt.tight_layout()
    plt.savefig(os.path.join(args.out, "4_dream_sweep.png"), dpi=120)
    plt.close()

    # ---------------- example nights
    show = [0.0, 0.1, 0.5, 1.0]
    fig, axes = plt.subplots(len(show), 3, figsize=(18, 2.6 * len(show)), sharex=True)
    for col, m in enumerate("ABC"):
        for row, g in enumerate(show):
            r, b, ctx = examples[(m, g)]
            ax = axes[row, col]
            places = ctx["place_of"][r]
            ax.scatter(np.arange(NIGHT), r, c=places, cmap="tab10", vmin=0, vmax=9, s=6)
            ax.axvspan(EVENT_T, EVENT_T + EVENT_LEN, color="tab:cyan", alpha=0.2)
            ax.set_ylim(-0.5, ctx["K"] - 0.5)
            ax.set_yticks(range(0, ctx["K"], 2))
            ax.set_ylabel("dream scene #")
            ax2 = ax.twinx()
            ax2.plot(b[:, nn.WATER], color="tab:green", lw=1, ls="--", label="true water")
            ax2.plot(b[:, nn.ENERGY], color="tab:brown", lw=1, ls="--", label="true energy")
            if row == 0 and col == 0:
                ax2.legend(fontsize=7, loc="upper right")
            ax2.set_ylim(0, 1)
            ax2.set_yticks([])
            name = {"A": "A: stored dictionary", "B": "B: always-on + imagination",
                    "C": "C: always-on, no imagination"}[m]
            ax.set_title(f"{name}, gate g={g}   (cyan = water sound; dot colour = place of scene)",
                         fontsize=9)
    for ax in axes[-1]:
        ax.set_xlabel("time asleep")
    plt.tight_layout()
    plt.savefig(os.path.join(args.out, "5_dream_nights.png"), dpi=120)
    plt.close()

    # ---------------- text report
    lines = ["== Dream experiment ==",
             f"{args.seeds} agents x {args.nights} nights, {NIGHT} steps each. mean over nights.",
             f"chance level for 'life-like' transitions: {np.mean(chance):.2f}", ""]
    for m, name in (("A", "A: stored dictionary"), ("B", "B: always-on + imagination"),
                    ("C", "C: always-on, no imagination")):
        lines.append(name)
        lines.append("  gate     " + "".join(f"{g:>8}" for g in GATES))
        for k in metrics:
            lines.append(f"  {k:<9}" + "".join(f"{x:8.2f}" for x in np.nanmean(R[m][k], 0)))
        lines.append("")
    lines.append("example nights, agent 1 - dream narrative (observer's labels):")
    for m, g in (("A", 0.0), ("B", 0.0), ("B", 0.5), ("C", 0.0), ("C", 0.1)):
        r, _, ctx = examples[(m, g)]
        runs = []
        for k in r:
            if not runs or runs[-1][0] != k:
                runs.append([k, 1])
            else:
                runs[-1][1] += 1
        lines.append(f"  model {m}, g={g}: {len(runs)} scenes")
        for k, n in runs[:8]:
            lines.append(f"     C{k:<2} x{n:<4} {ctx['labels'][k]}")
        if len(runs) > 8:
            lines.append(f"     ... {len(runs) - 8} more")
    text = "\n".join(lines)
    print(text)
    with open(os.path.join(args.out, "dream_report.txt"), "w") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
