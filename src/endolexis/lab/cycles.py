"""
NewNeural - sleep cycles.

The sensory gate is no longer fixed: it rises and falls through the night like
sleep cycles. Each cycle starts shut (g = 0, roughly deep sleep) and opens
part way (up to g = GMAX, roughly REM), then shuts again.
Short "water sounds" are played at random moments through the night.

Question: if dreaming needs the outside (the user's theory), dream activity and
incorporation of sounds should be locked to the OPEN phases. If meanings can be
read from the inside alone (model A), dreaming should go on regardless of the gate.

Same three interpreters as dream.py:
  A stored dictionary, B always-on + imagination, C always-on, no imagination.

Measures
  stable scene changes : changes into a scene that is held for >= MIN_HOLD steps
                         (one-step flicker is removed)
  phase-locking        : stable scene-change rate across the cycle, vs the gate
  incorporation        : for each sound, how much more the dream is "at the pond"
                         during the sound than just before it, vs the gate at that moment
  onset lag            : how long after the gate starts opening the dream starts moving

Run:  python -m endolexis.lab.cycles     (needs agent.py and dream.py next to it)
"""
import argparse
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import agent as nn
from .dream import raise_and_index

PERIOD = 300
CYCLES = 4
NIGHT = PERIOD * CYCLES
GMAX = 0.5
N_SOUNDS = 8
SOUND_LEN = 8
MIN_HOLD = 3
N_PHASE = 20
MODELS = {"A": ("A: stored dictionary", "tab:blue"),
          "B": ("B: always-on + imagination", "tab:red"),
          "C": ("C: always-on, no imagination", "tab:orange")}


def gate_schedule():
    t = np.arange(NIGHT)
    return GMAX * (0.5 - 0.5 * np.cos(2 * np.pi * t / PERIOD)) ** 2


def sound_times(rng):
    starts = []
    while len(starts) < N_SOUNDS:
        s = int(rng.integers(40, NIGHT - SOUND_LEN))
        if all(abs(s - o) > 40 for o in starts):
            starts.append(s)
    return sorted(starts)


def sleep_cycles(ctx, model, gate, sounds, seed):
    world, agent = ctx["world"], ctx["agent"]
    rng = np.random.default_rng(seed)
    body = nn.Body(interoception_seed=42, seed=seed + 7)
    body.state = ctx["log"]["body"][-1].copy()
    body.state[nn.ENERGY] = max(body.state[nn.ENERGY], 0.6)
    body.state[nn.WATER] = max(body.state[nn.WATER], 0.6)
    pond = world.contexts.index("pond")
    prev = int(ctx["log"]["concept"][-1])
    sound_on = np.zeros(NIGHT, bool)
    for s in sounds:
        sound_on[s:s + SOUND_LEN] = True

    reading, true_body = [], []
    for t in range(NIGHT):
        s = body.state
        # slower metabolism than dream.py: the night is 3x longer
        s += np.array([-0.0004, 0.01 * (0.45 - s[nn.WARMTH]), -0.0005]) + rng.normal(0, 0.003, 3)
        body.state = np.clip(s, 0, 1)
        body.t += 1
        x_int = body.feel()
        g = gate[t]
        real = rng.normal(0, 1, nn.EXT_DIM)
        if sound_on[t]:
            real = world.protos[pond] + rng.normal(0, 0.3, nn.EXT_DIM)
        if model == "A":
            p = agent.interpret(g * real, x_int, lam_ext=g, lam_int=1.0)
        elif model == "C":
            p = agent.interpret(g * real, x_int, lam_ext=1.0, lam_int=1.0)
        else:
            imagined = agent.mu[prev][:nn.EXT_DIM]
            x_ext = g * real + (1 - g) * imagined + rng.normal(0, 0.1, nn.EXT_DIM)
            p = agent.interpret(x_ext, x_int, lam_ext=1.0, lam_int=1.0)
        prev = int(np.argmax(p))
        reading.append(prev)
        true_body.append(body.state.copy())
    return np.array(reading), np.array(true_body), sound_on


def stabilize(reading):
    """Remove flicker: a run shorter than MIN_HOLD is absorbed by the scene before it."""
    r = reading.copy()
    runs = []
    for k in r:
        if runs and runs[-1][0] == k:
            runs[-1][1] += 1
        else:
            runs.append([k, 1])
    out, cur = [], runs[0][0]
    for k, n in runs:
        if n >= MIN_HOLD:
            cur = k
        out += [cur] * n
    return np.array(out)


def analyse(ctx, reading, gate, sounds):
    st = stabilize(reading)
    change = np.zeros(NIGHT, bool)
    change[1:] = st[1:] != st[:-1]
    pond = ctx["world"].contexts.index("pond")
    at_pond = ctx["place_of"][reading] == pond
    inc = []
    for s in sounds:
        before = at_pond[max(0, s - 20):s].mean()
        during = at_pond[s:s + SOUND_LEN].mean()
        inc.append((gate[s:s + SOUND_LEN].mean(), during - before))
    return change, st, inc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--nights", type=int, default=4)
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    gate = gate_schedule()
    phase_bin = ((np.arange(NIGHT) % PERIOD) * N_PHASE // PERIOD)
    gate_by_phase = np.array([gate[phase_bin == b].mean() for b in range(N_PHASE)])

    phase_rate = {m: [] for m in MODELS}         # per night: change rate per phase bin
    incs = {m: [] for m in MODELS}               # (gate, incorporation) per sound
    closed_open = {m: [] for m in MODELS}        # per night: (rate when g<0.02, rate when g>0.25)
    nights = []                                  # every night, all models, for picking an example
    for si in range(args.seeds):
        ctx = raise_and_index(si + 1)
        for ni in range(args.nights):
            rng = np.random.default_rng(5000 + 100 * si + ni)
            sounds = sound_times(rng)
            night = {}
            for m in MODELS:
                r, b, son = sleep_cycles(ctx, m, gate, sounds, seed=777 * si + 31 * ni)
                ch, st, inc = analyse(ctx, r, gate, sounds)
                phase_rate[m].append([100 * ch[phase_bin == k].mean() for k in range(N_PHASE)])
                incs[m] += inc
                closed_open[m].append((100 * ch[gate < 0.02].mean(), 100 * ch[gate > 0.25].mean()))
                night[m] = (r, st, son, ctx, ch.sum())
            nights.append(night)

    # example: the night whose B activity is closest to the median (not hand-picked)
    acts = np.array([n["B"][4] for n in nights])
    example = nights[int(np.argmin(np.abs(acts - np.median(acts))))]

    # ---------- figure 6: phase locking + incorporation
    fig, ax = plt.subplots(1, 2, figsize=(14, 5))
    ph = (np.arange(N_PHASE) + 0.5) / N_PHASE
    a2 = ax[0].twinx()
    a2.fill_between(ph, gate_by_phase, color="gray", alpha=0.2, step="mid")
    a2.set_ylim(0, 1)
    a2.set_ylabel("gate (gray)")
    for m, (name, c) in MODELS.items():
        v = np.array(phase_rate[m])
        ax[0].errorbar(ph, v.mean(0), yerr=v.std(0) / np.sqrt(len(v)), color=c, marker="o",
                       ms=3, capsize=2, label=name)
    ax[0].set_xlabel("phase within a sleep cycle (0 = shut, 0.5 = most open)")
    ax[0].set_ylabel("stable scene changes per 100 steps")
    ax[0].set_title("Does dreaming follow the gate?")
    ax[0].legend(fontsize=8, loc="upper left")
    bins = np.array([0, 0.02, 0.1, 0.2, 0.3, 0.4, 0.51])
    for m, (name, c) in MODELS.items():
        gi = np.array(incs[m])
        idx = np.digitize(gi[:, 0], bins) - 1
        mu = [gi[idx == k, 1].mean() if (idx == k).any() else np.nan for k in range(len(bins) - 1)]
        se = [gi[idx == k, 1].std() / np.sqrt((idx == k).sum()) if (idx == k).sum() > 1 else np.nan
              for k in range(len(bins) - 1)]
        ax[1].errorbar((bins[:-1] + bins[1:]) / 2, mu, yerr=se, color=c, marker="o", capsize=3, label=name)
    ax[1].axhline(0, color="k", lw=0.5)
    ax[1].set_xlabel("gate at the moment of the water sound")
    ax[1].set_ylabel("pull of the dream toward the pond")
    ax[1].set_title("Is the sound woven into the dream?")
    plt.tight_layout()
    plt.savefig(os.path.join(args.out, "6_cycles_phase.png"), dpi=120)
    plt.close()

    # ---------- figure 7: one night per model
    fig, axes = plt.subplots(3, 1, figsize=(14, 9), sharex=True)
    for ax_, m in zip(axes, MODELS):
        r, st, son, ctx, _ = example[m]
        ax_.fill_between(np.arange(NIGHT), 0, gate / GMAX * (ctx["K"] - 1), color="gray", alpha=0.15,
                         label="gate (scaled)")
        for s in np.flatnonzero(np.diff(son.astype(int)) == 1) + 1:
            ax_.axvspan(s, s + SOUND_LEN, color="tab:cyan", alpha=0.5)
        ax_.scatter(np.arange(NIGHT), st, c=ctx["place_of"][st], cmap="tab10", vmin=0, vmax=9, s=4)
        ax_.set_ylim(-0.5, ctx["K"] - 0.5)
        ax_.set_ylabel("dream scene #")
        ax_.set_title(f"{MODELS[m][0]}   (gray = gate, cyan = water sounds, dot colour = place)", fontsize=10)
    axes[-1].set_xlabel("time asleep (4 sleep cycles) - the night with median activity for B")
    plt.tight_layout()
    plt.savefig(os.path.join(args.out, "7_cycles_night.png"), dpi=120)
    plt.close()

    # ---------- report
    rise = np.flatnonzero(gate_by_phase > 0.02 * GMAX)[0]
    lines = ["== Sleep cycles ==",
             f"{args.seeds} agents x {args.nights} nights, {CYCLES} cycles of {PERIOD} steps, gate 0..{GMAX}, "
             f"{N_SOUNDS} water sounds per night. Flicker shorter than {MIN_HOLD} steps removed.", ""]
    for m, (name, _) in MODELS.items():
        co = np.array(closed_open[m])
        v = np.array(phase_rate[m]).mean(0)
        gi = np.array(incs[m])
        shut_inc = gi[gi[:, 0] < 0.02, 1].mean()
        open_inc = gi[gi[:, 0] > 0.25, 1].mean()
        # onset: first phase bin after gate starts rising where rate exceeds half its max-min range
        thr = v.min() + 0.5 * (v.max() - v.min())
        onset = next((b for b in range(rise, N_PHASE) if v[b] >= thr), None)
        lines += [name,
                  f"  scene changes /100 steps : shut {co[:, 0].mean():5.2f}   open {co[:, 1].mean():5.2f}"
                  f"   ratio open/shut {co[:, 1].mean() / max(co[:, 0].mean(), 1e-9):5.1f}",
                  f"  sound incorporation      : shut {shut_inc:5.2f}   open {open_inc:5.2f}",
                  f"  dream onset after gate starts opening: "
                  + (f"{(onset - rise) * PERIOD / N_PHASE:.0f} steps" if onset is not None else "none"),
                  f"  rate by phase: " + " ".join(f"{x:4.1f}" for x in v), ""]
    lines.append("gate by phase:   " + " ".join(f"{x:4.2f}" for x in gate_by_phase))
    text = "\n".join(lines)
    print(text)
    with open(os.path.join(args.out, "cycles_report.txt"), "w") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
