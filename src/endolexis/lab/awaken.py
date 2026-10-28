"""
NewNeural - awakening reports and daytime recall.

User's theory (going beyond Dennett's "composed at waking"):
  During sleep, internal states really happen and leave a TRACE, but they have no
  meaning yet. Meaning is assigned whenever a dictionary is available:
    - at awakening (waking up = the outside flooding in: an alarm, a touch, a word)
    - later, during the day, when some outside circumstance resonates with the trace.
  So a dream is not composed once; it can be re-composed, which is why recalled
  dreams drift and contradict themselves.

Two models of memory, built on the interpreters of dream.py / cycles.py:
  A "stored dictionary": the agent reads itself during sleep and remembers its
    readings. The report IS what it dreamed.
  B "always-on dictionary" (user's theory): the agent keeps the raw internal trace.
    A report or a recall is a fresh reading of that trace, made with whatever
    outside input (and body) is present at the moment of reading.

Part 1 - awakening
  The agent is woken either from a SHUT phase (deep sleep) or an OPEN phase (REM-like),
  by one of three awakenings: spontaneous (just the room), a water sound, a breakfast
  smell. Waking = the gate ramps open to 1 while that stimulus is present.
  Report = the last REPORT_LEN steps of the night, as remembered (A) or re-read (B).
  Measures: richness of the report vs. of what was dreamed at the time; how much the
  awakening stimulus shows up in the report; agreement with what was dreamed.

Part 2 - daytime recall (model B)
  One dream episode's trace is recalled 30 times: at each of the 5 places, in 3 body
  states (fine / thirsty / hungry), twice each. The current body leaks into the
  replayed trace (RECALL_LEAK), and the current place is the outside cue.
  The weight of the daytime cue is swept to find the regime between "the cue changes
  nothing" and "the cue takes over"; the detailed analysis uses G_RECALL.
  Measures: how much recalls agree with each other (same context vs. different);
  pull of the current place and the current body on the content; and the "click":
  is recall more confident in contexts that match the body state of that night?

Not built in vs. built in: re-reading a raw trace makes SOME instability inevitable.
What is measured is its size and structure, and whether the click appears.

Run:  python -m endolexis.lab.awaken    (needs agent.py, dream.py, cycles.py)
"""
import argparse
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import agent as nn
from .dream import raise_and_index
from .cycles import gate_schedule, stabilize, PERIOD

RAMP = 15            # steps it takes to wake up
REPORT_LEN = 60      # how much of the night the report covers
G_WAKE = 0.5         # weight of the outside when reading the trace at awakening (half awake)
G_RECALL = 0.4       # weight of a daytime cue when recalling (near the tipping point, see sweep)
RECALL_SWEEP = [0.2, 0.3, 0.35, 0.4, 0.45, 0.5]
RECALL_LEAK = 0.3    # how much of the current body leaks into a replayed trace
STIMULI = {"spontaneous": None, "water sound": "pond", "breakfast smell": "berry bush"}
PHASES = {"shut (deep)": 2 * PERIOD + 10, "open (REM-like)": 2 * PERIOD + PERIOD // 2}
BODIES = {"fine": [0.6, 0.6, 0.6], "thirsty": [0.6, 0.5, 0.2], "hungry": [0.2, 0.5, 0.6]}


# ----------------------------------------------------------------------------- sleeping
def sleep_until(ctx, model, T, seed):
    """Sleep with cycling gate until step T. Returns readings, raw internal trace, body, body obj."""
    world, agent = ctx["world"], ctx["agent"]
    gate = gate_schedule()
    rng = np.random.default_rng(seed)
    body = nn.Body(interoception_seed=42, seed=seed + 7)
    body.state = ctx["log"]["body"][-1].copy()
    body.state[nn.ENERGY] = max(body.state[nn.ENERGY], 0.6)
    body.state[nn.WATER] = max(body.state[nn.WATER], 0.6)
    prev = int(ctx["log"]["concept"][-1])
    reading, trace, bodies = [], [], []
    for t in range(T):
        s = body.state
        s += np.array([-0.0004, 0.01 * (0.45 - s[nn.WARMTH]), -0.0005]) + rng.normal(0, 0.003, 3)
        body.state = np.clip(s, 0, 1)
        body.t += 1
        x_int = body.feel()
        g = gate[t]
        real = rng.normal(0, 1, nn.EXT_DIM)
        if model == "A":
            p = agent.interpret(g * real, x_int, lam_ext=g, lam_int=1.0)
        else:
            x_ext = g * real + (1 - g) * agent.mu[prev][:nn.EXT_DIM] + rng.normal(0, 0.1, nn.EXT_DIM)
            p = agent.interpret(x_ext, x_int, lam_ext=1.0, lam_int=1.0)
        prev = int(np.argmax(p))
        reading.append(prev)
        trace.append(x_int)
        bodies.append(body.state.copy())
    return np.array(reading), np.array(trace), np.array(bodies), body, gate[T - 1], rng


def stim_sample(ctx, stim, rng):
    world = ctx["world"]
    if stim is None:
        return rng.normal(0, 1, nn.EXT_DIM)
    return world.protos[world.contexts.index(stim)] + rng.normal(0, 0.3, nn.EXT_DIM)


def reread(ctx, trace, cue_fn, start, rng, body_feel=None, g_read=G_WAKE):
    """Read a stored internal trace with the dictionary available NOW (model B)."""
    agent = ctx["agent"]
    prev, out, conf = start, [], []
    for x in trace:
        x_int = x if body_feel is None else (1 - RECALL_LEAK) * x + RECALL_LEAK * body_feel()
        x_ext = g_read * cue_fn() + (1 - g_read) * agent.mu[prev][:nn.EXT_DIM] \
            + rng.normal(0, 0.1, nn.EXT_DIM)
        p = agent.interpret(x_ext, x_int, lam_ext=1.0, lam_int=1.0)
        prev = int(np.argmax(p))
        out.append(prev)
        conf.append(p.max())
    return np.array(out), float(np.mean(conf))


def n_scenes(r):
    st = stabilize(r)
    return 1 + int(np.sum(st[1:] != st[:-1]))


# ----------------------------------------------------------------------------- part 1
def awakening(ctx, model, phase_t, stim, seed):
    agent = ctx["agent"]
    reading, trace, _, body, g0, rng = sleep_until(ctx, model, phase_t, seed)
    # waking up: the gate ramps open while the stimulus is present
    prev = reading[-1]
    for i in range(RAMP):
        g = g0 + (1 - g0) * (i + 1) / RAMP
        body.t += 1
        x_ext = g * stim_sample(ctx, stim, rng) + (1 - g) * agent.mu[prev][:nn.EXT_DIM]
        prev = int(np.argmax(agent.interpret(x_ext, body.feel(), lam_ext=1.0, lam_int=1.0)))
    dreamed = reading[-REPORT_LEN:]
    if model == "A":
        report = dreamed.copy()                                   # it remembers what it read
    else:
        report, _ = reread(ctx, trace[-REPORT_LEN:], lambda: stim_sample(ctx, stim, rng), prev, rng)
    target = None if stim is None else ctx["world"].contexts.index(stim)
    pull = np.nan if target is None else float(np.mean(ctx["place_of"][report] == target))
    base = None if target is None else float(np.mean(ctx["place_of"][dreamed] == target))
    return dict(dreamed=n_scenes(dreamed), report=n_scenes(report),
                agree=float(np.mean(report == dreamed)), pull=pull, base=base,
                report_seq=report, dreamed_seq=dreamed)


# ----------------------------------------------------------------------------- part 2
def recall(ctx, seed, g_read=None):
    g_read = G_RECALL if g_read is None else g_read
    world = ctx["world"]
    # one dream episode: the open phase of the 3rd cycle, read as model B
    T = 2 * PERIOD + PERIOD // 2 + REPORT_LEN // 2
    reading, trace, bodies, _, _, rng = sleep_until(ctx, "B", T, seed)
    ep, ep_body = trace[-REPORT_LEN:], bodies[-REPORT_LEN:].mean(0)
    dreamed = reading[-REPORT_LEN:]

    ctxs, recs, confs = [], [], []
    for pi, place in enumerate(world.contexts):
        for bname, bstate in BODIES.items():
            for rep in range(2):
                probe = nn.Body(interoception_seed=42, seed=seed + 31 * pi + 7 * rep + len(bname))
                probe.state = np.array(bstate, float)
                r, c = reread(ctx, ep, lambda: world.observe(pi), dreamed[0], rng,
                              body_feel=probe.feel, g_read=g_read)
                ctxs.append((place, bname, rep))
                recs.append(r)
                confs.append(c)
    recs = np.array(recs)
    n = len(recs)
    agree = np.array([[np.mean(recs[i] == recs[j]) for j in range(n)] for i in range(n)])
    same = [agree[i, j] for i in range(n) for j in range(n)
            if i < j and ctxs[i][:2] == ctxs[j][:2]]
    diff = [agree[i, j] for i in range(n) for j in range(n)
            if i < j and ctxs[i][:2] != ctxs[j][:2]]
    vs_dreamed = np.mean([np.mean(r == dreamed) for r in recs])

    # place pull: share of recalled steps at the current place, vs that place's share overall
    pp = []
    for (place, _, _), r in zip(ctxs, recs):
        k = world.contexts.index(place)
        pp.append(np.mean(ctx["place_of"][r] == k) - np.mean(ctx["place_of"][recs] == k))
    # body pull: implied water / energy of recalled scenes, by current body
    implied = {b: ctx["body_of"][recs[[c[1] == b for c in ctxs]]].reshape(-1, 3).mean(0) for b in BODIES}
    # click: confidence per place (body 'fine') vs how well the place's waking body matches the night
    log = ctx["log"]
    match, conf_p = [], []
    for pi, place in enumerate(world.contexts):
        place_body = log["body"][log["ctx"] == pi].mean(0)
        match.append(-np.linalg.norm(place_body - ep_body))
        conf_p.append(np.mean([c for (pl, b, _), c in zip(ctxs, confs) if pl == place]))
    rank = lambda v: np.argsort(np.argsort(v))
    rho = np.corrcoef(rank(match), rank(conf_p))[0, 1]
    return dict(ctxs=ctxs, recs=recs, agree=agree, same=np.mean(same), diff=np.mean(diff),
                vs_dreamed=vs_dreamed, place_pull=np.mean(pp), implied=implied,
                match=np.array(match), conf=np.array(conf_p), rho=rho, dreamed=dreamed,
                ep_body=ep_body)


# ----------------------------------------------------------------------------- main
def narrative(r, labels, maxn=6):
    st = stabilize(r)
    runs = []
    for k in st:
        if runs and runs[-1][0] == k:
            runs[-1][1] += 1
        else:
            runs.append([k, 1])
    return " -> ".join(labels[k].split("|")[0].strip() + f"({n})" for k, n in runs[:maxn]) + \
        (" ..." if len(runs) > maxn else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--nights", type=int, default=4)
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    A = {}  # (model, phase, stim) -> list of results
    R = []
    ctxs = []
    for si in range(args.seeds):
        ctx = raise_and_index(si + 1)
        ctxs.append(ctx)
        for ni in range(args.nights):
            for ph, T in PHASES.items():
                for sname, stim in STIMULI.items():
                    for m in "AB":
                        A.setdefault((m, ph, sname), []).append(
                            awakening(ctx, m, T, stim, seed=900 * si + 37 * ni))
            R.append(recall(ctx, seed=4000 + 900 * si + 37 * ni))
    SW = {g: [recall(c, seed=4000 + 900 * si + 37 * ni, g_read=g)
              for si, c in enumerate(ctxs) for ni in range(2)] for g in RECALL_SWEEP}

    # ---------------- figure 8: awakening
    fig, ax = plt.subplots(1, 3, figsize=(17, 5))
    phs = list(PHASES)
    w = 0.2
    for i, ph in enumerate(phs):
        res = sum((A[("B", ph, s)] for s in STIMULI), [])
        resA = sum((A[("A", ph, s)] for s in STIMULI), [])
        vals = [np.mean([r["dreamed"] for r in res]), np.mean([r["report"] for r in res]),
                np.mean([r["report"] for r in resA])]
        for j, (v, lab, c) in enumerate(zip(vals, ["B: dreamed at the time", "B: reported on waking",
                                                    "A: reported (= dreamed)"],
                                             ["tab:pink", "tab:red", "tab:blue"])):
            ax[0].bar(i + (j - 1) * w, v, w, color=c, label=lab if i == 0 else None)
    ax[0].set_xticks(range(len(phs)))
    ax[0].set_xticklabels(phs)
    ax[0].set_ylabel(f"scenes in the last {REPORT_LEN} steps")
    ax[0].set_title("Is there a dream to report?")
    ax[0].legend(fontsize=8)

    stims = [s for s in STIMULI if STIMULI[s]]
    for i, ph in enumerate(phs):
        for j, s in enumerate(stims):
            res = A[("B", ph, s)]
            pull = np.mean([r["pull"] - r["base"] for r in res])
            se = np.std([r["pull"] - r["base"] for r in res]) / np.sqrt(len(res))
            ax[1].bar(i + (j - 0.5) * 0.35, pull, 0.35, yerr=se, capsize=3,
                      color=["tab:cyan", "tab:olive"][j], label=s if i == 0 else None)
    ax[1].axhline(0, color="k", lw=0.5)
    ax[1].set_xticks(range(len(phs)))
    ax[1].set_xticklabels(phs)
    ax[1].set_ylabel("share of report at the stimulus place\n(minus share in what was dreamed)")
    ax[1].set_title("B: does the awakening become the dream?")
    ax[1].legend(fontsize=8)

    for i, ph in enumerate(phs):
        for j, s in enumerate(STIMULI):
            res = A[("B", ph, s)]
            ax[2].bar(i + (j - 1) * 0.25, np.mean([r["agree"] for r in res]), 0.25,
                      color=["gray", "tab:cyan", "tab:olive"][j], label=s if i == 0 else None)
    ax[2].set_xticks(range(len(phs)))
    ax[2].set_xticklabels(phs)
    ax[2].set_ylim(0, 1)
    ax[2].set_ylabel("report agrees with what was dreamed (share of steps)")
    ax[2].set_title("B: does the report match the night?")
    ax[2].legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(args.out, "8_awakening.png"), dpi=120)
    plt.close()

    # ---------------- figure 9: recall
    ex = R[0]
    fig, ax = plt.subplots(1, 4, figsize=(24, 6), gridspec_kw=dict(width_ratios=[1, 1.3, 1, 1]))
    sw = RECALL_SWEEP
    for key, lab, c in (("same", "two recalls, same context", "tab:green"),
                        ("diff", "two recalls, different contexts", "tab:purple"),
                        ("vs_dreamed", "recall vs. what was dreamed", "tab:gray"),
                        ("place_pull", "pull of the current place", "tab:orange")):
        ax[0].plot(sw, [np.mean([r[key] for r in SW[g]]) for g in sw], marker="o", label=lab, color=c)
    ax[0].axvline(G_RECALL, color="k", ls=":", lw=0.8)
    ax[0].set_xlabel("weight of the daytime cue when recalling")
    ax[0].set_title("Recall has a tipping point", fontsize=10)
    ax[0].legend(fontsize=8)
    ax = ax[1:]
    im = ax[0].imshow(ex["agree"], vmin=0, vmax=1, cmap="viridis")
    labs = [f"{p[:6]} {b[:4]} {r}" for p, b, r in ex["ctxs"]]
    ax[0].set_xticks(range(len(labs)))
    ax[0].set_xticklabels(labs, rotation=90, fontsize=6)
    ax[0].set_yticks(range(len(labs)))
    ax[0].set_yticklabels(labs, fontsize=6)
    ax[0].set_title(f"One night's dream, recalled 30 times (cue weight {G_RECALL}):\n"
                    "how much two recalls agree", fontsize=10)
    plt.colorbar(im, ax=ax[0], fraction=0.046)

    bn = list(BODIES)
    water = [np.mean([r["implied"][b][nn.WATER] for r in R]) for b in bn]
    energy = [np.mean([r["implied"][b][nn.ENERGY] for r in R]) for b in bn]
    x = np.arange(len(bn))
    ax[1].bar(x - 0.18, water, 0.36, label="water implied by recalled scenes", color="tab:green")
    ax[1].bar(x + 0.18, energy, 0.36, label="energy implied by recalled scenes", color="tab:brown")
    ax[1].set_xticks(x)
    ax[1].set_xticklabels([f"recalled while {b}" for b in bn])
    ax[1].set_ylim(0, 0.8)
    ax[1].set_title("Does the current body colour the recalled dream?", fontsize=10)
    ax[1].legend(fontsize=8)

    for r in R:
        z = lambda v: (v - v.mean()) / (v.std() + 1e-9)
        ax[2].scatter(z(r["match"]), z(r["conf"]), s=12, alpha=0.6)
    ax[2].set_xlabel("how well the place matches the night's body state (z within night)")
    ax[2].set_ylabel("confidence of recall at that place (z within night)")
    ax[2].set_title(f"The click: mean rank correlation {np.nanmean([r['rho'] for r in R]):.2f}",
                    fontsize=10)
    plt.tight_layout()
    plt.savefig(os.path.join(args.out, "9_recall.png"), dpi=120)
    plt.close()

    # ---------------- report
    L = ["== Awakening ==", f"{args.seeds} agents x {args.nights} nights; report covers the last "
         f"{REPORT_LEN} steps of sleep.", ""]
    for ph in phs:
        L.append(ph)
        for s in STIMULI:
            b, a = A[("B", ph, s)], A[("A", ph, s)]
            line = (f"  {s:<16} B dreamed {np.mean([r['dreamed'] for r in b]):4.1f} scenes, "
                    f"reported {np.mean([r['report'] for r in b]):4.1f}, agreement "
                    f"{np.mean([r['agree'] for r in b]):.2f}")
            if STIMULI[s]:
                line += (f", stimulus in report {np.mean([r['pull'] for r in b]):.2f} "
                         f"(in dream {np.mean([r['base'] for r in b]):.2f})")
            line += f" | A reported {np.mean([r['report'] for r in a]):4.1f}"
            L.append(line)
        L.append("")
    L += ["== Daytime recall (model B), cue weight sweep ==",
          "  cue   same  diff  vsDream  placePull  click"]
    for g in RECALL_SWEEP:
        f = lambda k: np.mean([r[k] for r in SW[g]])
        L.append(f"  {g:<5} {f('same'):.2f}  {f('diff'):.2f}  {f('vs_dreamed'):.2f}     {f('place_pull'):+.2f}     "
                 f"{np.nanmean([r['rho'] for r in SW[g]]):+.2f}")
    L += ["", f"== Daytime recall (model B), cue weight {G_RECALL} ==",
          f"agreement between two recalls in the SAME context      : {np.mean([r['same'] for r in R]):.2f}",
          f"agreement between two recalls in DIFFERENT contexts    : {np.mean([r['diff'] for r in R]):.2f}",
          f"agreement of a recall with what was dreamed that night : {np.mean([r['vs_dreamed'] for r in R]):.2f}",
          f"pull of the current place on the recalled content      : {np.mean([r['place_pull'] for r in R]):+.2f}",
          "water / energy implied by recalled scenes, by current body:"]
    for b in bn:
        L.append(f"  {b:<8} water {np.mean([r['implied'][b][nn.WATER] for r in R]):.2f}   "
                 f"energy {np.mean([r['implied'][b][nn.ENERGY] for r in R]):.2f}")
    rhos = np.array([r["rho"] for r in R])
    L += [f"click (rank corr. place-matches-night vs recall confidence): mean {np.nanmean(rhos):.2f}, "
          f"positive in {np.sum(rhos > 0)} of {len(rhos)} nights", "",
          "Example: one dream episode, as dreamed and as recalled in different contexts"]
    ex, lab = R[0], ctxs[0]["labels"]
    L.append(f"  dreamed        : {narrative(ex['dreamed'], lab)}")
    for i, (p, b, rep) in enumerate(ex["ctxs"]):
        if rep == 0 and (b == "fine" or p in ("pond", "berry bush")) and (p in ("pond", "berry bush", "sun rock")):
            L.append(f"  at {p:<10} {b:<7}: {narrative(ex['recs'][i], lab)}")
    text = "\n".join(L)
    print(text)
    with open(os.path.join(args.out, "awaken_report.txt"), "w") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
