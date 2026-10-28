"""
NewNeural - step 1: a fair fight.

Earlier, model A (stored dictionary) was a weak version of the conventional view: it
re-read its feelings step by step with no expectations and no imagination.

Here both interpreters get IDENTICAL machinery:
  - learned expectations: how often each concept follows each other one in waking life
  - generative replay: at each step the agent SAMPLES its next reading from
        expectation(previous reading) x evidence
    so it can dream by imagining what usually comes next.

The ONLY difference is the theory's claim:
  A_strong : evidence = inside + gate * outside   (outside can be turned down to zero)
  B_fair   : evidence = inside + outside, always; asleep, "outside" is
             gate * real input + (1 - gate) * the imagined scene of what it expects next

Question: does dreaming still lock to the open phases of the sleep cycle for B,
and not for a strong A? And are outside sounds woven in only when the gate is open?

Run:  python -m endolexis.lab.strong_a    (needs agent.py, dream.py, cycles.py)
"""
import argparse
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import agent as nn
from .dream import raise_and_index
from .cycles import gate_schedule, stabilize, sound_times, PERIOD, NIGHT, GMAX, N_PHASE, SOUND_LEN

MODELS = {"A": ("A strong: outside can be turned off", "tab:gray"),
          "B": ("B fair: outside always needed", "tab:blue")}


def transitions(ctx, stickiness=None):
    """Learned expectations: P(next concept | this concept) from waking life."""
    K, seq = ctx["K"], ctx["log"]["concept"]
    T = np.ones((K, K)) * 0.01
    for a, b in zip(seq[:-1], seq[1:]):
        T[a, b] += 1
    return T / T.sum(1, keepdims=True)


def concept_ll(agent, x_ext, x_int, lam_ext):
    out = []
    for k in range(len(agent.mu)):
        le, li = agent._ll_parts(np.concatenate([x_ext, x_int]), k)
        out.append(lam_ext * le + li)
    return np.array(out)


def sleep_replay(ctx, model, gate, sounds, seed, temp=1.0):
    world, agent = ctx["world"], ctx["agent"]
    T = ctx["T"]
    rng = np.random.default_rng(seed)
    body = nn.Body(interoception_seed=42, seed=seed + 7)
    body.state = ctx["log"]["body"][-1].copy()
    body.state[nn.ENERGY] = max(body.state[nn.ENERGY], 0.6)
    body.state[nn.WATER] = max(body.state[nn.WATER], 0.6)
    pond = world.contexts.index("pond")
    prev = int(ctx["log"]["concept"][-1])
    mu_ext = np.array(agent.mu)[:, :nn.EXT_DIM]
    sound_on = np.zeros(NIGHT, bool)
    for s in sounds:
        sound_on[s:s + SOUND_LEN] = True
    reading = []
    for t in range(NIGHT):
        s = body.state
        s += np.array([-0.0004, 0.01 * (0.45 - s[nn.WARMTH]), -0.0005]) + rng.normal(0, 0.003, 3)
        body.state = np.clip(s, 0, 1)
        body.t += 1
        x_int = body.feel()
        g = gate[t]
        real = rng.normal(0, 1, nn.EXT_DIM)
        if sound_on[t]:
            real = world.protos[pond] + rng.normal(0, 0.3, nn.EXT_DIM)
        prior = T[prev]
        if model == "A":
            ll = concept_ll(agent, g * real, x_int, lam_ext=g)
        else:
            imagined = prior @ mu_ext                       # what it expects to see next
            x_ext = g * real + (1 - g) * imagined + rng.normal(0, 0.1, nn.EXT_DIM)
            ll = concept_ll(agent, x_ext, x_int, lam_ext=1.0)
        logp = np.log(prior) + ll / temp
        p = np.exp(logp - logp.max())
        p /= p.sum()
        prev = int(rng.choice(len(p), p=p))                 # generative replay: sample
        reading.append(prev)
    return np.array(reading), sound_on


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--nights", type=int, default=4)
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    gate = gate_schedule()
    phase_bin = (np.arange(NIGHT) % PERIOD) * N_PHASE // PERIOD
    gate_by_phase = np.array([gate[phase_bin == b].mean() for b in range(N_PHASE)])
    rate = {m: [] for m in MODELS}
    co = {m: [] for m in MODELS}
    inc = {m: [] for m in MODELS}
    for si in range(args.seeds):
        ctx = raise_and_index(si + 1)
        ctx["T"] = transitions(ctx)
        pond = ctx["world"].contexts.index("pond")
        for ni in range(args.nights):
            sounds = sound_times(np.random.default_rng(5000 + 100 * si + ni))
            for m in MODELS:
                r, son = sleep_replay(ctx, m, gate, sounds, seed=777 * si + 31 * ni)
                st = stabilize(r)
                ch = np.zeros(NIGHT, bool)
                ch[1:] = st[1:] != st[:-1]
                rate[m].append([100 * ch[phase_bin == b].mean() for b in range(N_PHASE)])
                co[m].append((100 * ch[gate < 0.02].mean(), 100 * ch[gate > 0.25].mean()))
                at = ctx["place_of"][r] == pond
                for s in sounds:
                    inc[m].append((gate[s:s + SOUND_LEN].mean(),
                                   at[s:s + SOUND_LEN].mean() - at[max(0, s - 20):s].mean()))

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
    ax[0].set_title("Same machinery, one difference: does dreaming follow the gate?")
    ax[0].legend(fontsize=8)
    bins = np.array([0, 0.02, 0.1, 0.2, 0.3, 0.4, 0.51])
    for m, (name, c) in MODELS.items():
        gi = np.array(inc[m])
        idx = np.digitize(gi[:, 0], bins) - 1
        mu = [gi[idx == k, 1].mean() if (idx == k).any() else np.nan for k in range(len(bins) - 1)]
        ax[1].plot((bins[:-1] + bins[1:]) / 2, mu, marker="o", color=c, label=name)
    ax[1].axhline(0, color="k", lw=0.5)
    ax[1].set_xlabel("gate at the moment of the water sound")
    ax[1].set_ylabel("pull of the dream toward the pond")
    ax[1].set_title("Is the sound woven into the dream?")
    plt.tight_layout()
    plt.savefig(os.path.join(args.out, "11_strong_a.png"), dpi=120)
    plt.close()

    L = ["== Step 1: strong A vs fair B (identical expectations + generative replay) ==",
         f"{args.seeds} agents x {args.nights} nights, {NIGHT // PERIOD} cycles, gate 0..{GMAX}", ""]
    for m, (name, _) in MODELS.items():
        c = np.array(co[m])
        gi = np.array(inc[m])
        L += [name,
              f"  scene changes /100 steps: shut {c[:, 0].mean():.2f}  open {c[:, 1].mean():.2f}  "
              f"ratio {c[:, 1].mean() / max(c[:, 0].mean(), 1e-9):.2f}",
              f"  sound pull: shut {gi[gi[:, 0] < 0.02, 1].mean():+.2f}  open {gi[gi[:, 0] > 0.25, 1].mean():+.2f}",
              "  by phase: " + " ".join(f"{x:4.1f}" for x in np.array(rate[m]).mean(0)), ""]
    text = "\n".join(L)
    print(text)
    with open(os.path.join(args.out, "strong_a_report.txt"), "w") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
