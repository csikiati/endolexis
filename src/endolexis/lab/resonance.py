"""
NewNeural - cue-evoked feelings and the "click".

Missing piece found in awaken.py: a daytime cue only told the agent WHERE it is.
It did not make it FEEL anything, so nothing could resonate with the night's trace.

Here a cue evokes a feeling. Nothing new is learned for this: the agent's concepts
already pair "what it looks like" with "what it feels like". Reading the dictionary
backwards gives the feeling a cue usually comes with:
    evoked(cue) = sum_k P(concept k | cue) * internal part of concept k

Recall of a stored night trace (model B: trace re-read with the dictionary at hand):
    inside  = (1-EVOKE) * [(1-LEAK) * trace + LEAK * current body] + EVOKE * evoked(cue)
    outside = G_RECALL * cue + (1-G_RECALL) * imagined scene
EVOKE (how strongly cues evoke feelings) is swept; EVOKE = 0 is awaken.py.

The click, as a chain of testable links:
  1. match      : the place matches the night's body state (observer's view)
  2. resonance  : the feeling the cue evokes is close to the night's trace
                  (the agent can sense this itself - it is all internal)
  3. settling   : recall settles on one version (two recalls in the same context agree)
                  (max-posterior confidence was tried first; it saturates near 1)
  4. retrieval  : a settled recall gives back what was actually dreamed
                  (or does it invent something that merely feels right?)

Run:  python -m endolexis.lab.resonance   (needs agent.py, dream.py, cycles.py, awaken.py)
"""
import argparse
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import agent as nn
from .dream import raise_and_index
from .cycles import PERIOD, stabilize
from .awaken import sleep_until, REPORT_LEN, BODIES, RECALL_LEAK, G_RECALL, narrative

EVOKE_SWEEP = [0.0, 0.2, 0.4, 0.6]
EVOKE_MAIN = 0.4


def evoked(agent, x_ext):
    """The feeling a cue usually comes with: read the dictionary from outside to inside."""
    p = agent.interpret(x_ext, np.zeros(len(agent.mu[0]) - nn.EXT_DIM), lam_ext=1.0, lam_int=0.0)
    return np.sum(p[:, None] * np.array(agent.mu)[:, nn.EXT_DIM:], axis=0)


def recall_night(ctx, ep, dreamed, place_i, body_state, evoke, rng, seed):
    world, agent = ctx["world"], ctx["agent"]
    probe = nn.Body(interoception_seed=42, seed=seed)
    probe.state = np.array(body_state, float)
    prev, out, conf, res = dreamed[0], [], [], []
    for x in ep:
        cue = world.observe(place_i)
        ev = evoked(agent, cue)
        inside = (1 - evoke) * ((1 - RECALL_LEAK) * x + RECALL_LEAK * probe.feel()) + evoke * ev
        outside = G_RECALL * cue + (1 - G_RECALL) * agent.mu[prev][:nn.EXT_DIM] \
            + rng.normal(0, 0.1, nn.EXT_DIM)
        p = agent.interpret(outside, inside, lam_ext=1.0, lam_int=1.0)
        prev = int(np.argmax(p))
        out.append(prev)
        conf.append(p.max())
        res.append(-np.linalg.norm(ev - x))         # resonance: evoked feeling vs. the trace
    return np.array(out), float(np.mean(conf)), float(np.mean(res))


def run_night(ctx, evoke, seed):
    world, log = ctx["world"], ctx["log"]
    T = 2 * PERIOD + PERIOD // 2 + REPORT_LEN // 2
    reading, trace, bodies, _, _, rng = sleep_until(ctx, "B", T, seed)
    ep, ep_body, dreamed = trace[-REPORT_LEN:], bodies[-REPORT_LEN:].mean(0), reading[-REPORT_LEN:]
    rows = []
    for pi, place in enumerate(world.contexts):
        place_body = log["body"][log["ctx"] == pi].mean(0)
        match = -np.linalg.norm(place_body - ep_body)
        for bname, bstate in BODIES.items():
            for rep in range(2):
                r, c, res = recall_night(ctx, ep, dreamed, pi, bstate, evoke, rng,
                                         seed=seed + 31 * pi + 7 * rep + len(bname))
                rows.append(dict(place=place, body=bname, rep=rep, match=match, conf=c, res=res,
                                 retrieval=float(np.mean(r == dreamed)), rec=r))
    return rows, dreamed


def rank_corr(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if a.std() == 0 or b.std() == 0:
        return np.nan
    rk = lambda v: np.argsort(np.argsort(v))
    return np.corrcoef(rk(a), rk(b))[0, 1]


def night_stats(rows):
    # per place (averaging bodies and repeats), then rank correlations across the 5 places
    places = list(dict.fromkeys(r["place"] for r in rows))
    agg = {k: np.array([np.mean([r[k] for r in rows if r["place"] == p]) for p in places])
           for k in ("match", "res", "conf", "retrieval")}
    # settling: do two recalls in the same place and body state come out the same?
    agg["settle"] = np.array([np.mean([np.mean(a["rec"] == b["rec"]) for a in rows for b in rows
                                       if a["place"] == p and b["place"] == p and a["body"] == b["body"]
                                       and a["rep"] == 0 and b["rep"] == 1]) for p in places])
    return dict(match_res=rank_corr(agg["match"], agg["res"]),
                res_conf=rank_corr(agg["res"], agg["conf"]),
                conf_retr=rank_corr(agg["conf"], agg["retrieval"]),
                match_conf=rank_corr(agg["match"], agg["conf"]),
                res_settle=rank_corr(agg["res"], agg["settle"]),
                match_settle=rank_corr(agg["match"], agg["settle"]),
                settle_retr=rank_corr(agg["settle"], agg["retrieval"]),
                settle=np.mean(agg["settle"]), conf_mean=np.mean(agg["conf"]),
                res_retr=rank_corr(agg["res"], agg["retrieval"]),
                retrieval=np.mean(agg["retrieval"]), agg=agg, places=places)


def summarize(vals):
    v = np.array([x for x in vals if not np.isnan(x)])
    return v.mean(), v.std() / np.sqrt(len(v)), int(np.sum(v > 0)), len(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--nights", type=int, default=4)
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    ctxs = [raise_and_index(si + 1) for si in range(args.seeds)]
    S = {e: [] for e in EVOKE_SWEEP}
    examples = {}
    for e in EVOKE_SWEEP:
        for si, ctx in enumerate(ctxs):
            for ni in range(args.nights):
                rows, dreamed = run_night(ctx, e, seed=4000 + 900 * si + 37 * ni)
                st = night_stats(rows)
                st["rows"] = rows
                S[e].append(st)
                if si == 0 and ni == 0:
                    examples[e] = (rows, dreamed, ctx)

    links = [("match_res", "1 place matches night -> resonance"),
             ("res_settle", "2 resonance -> recall settles on one version"),
             ("settle_retr", "3 settled recall -> gives back the night"),
             ("match_settle", "the whole click: match -> settling")]

    # ---------------- figure 10
    fig, ax = plt.subplots(1, 3, figsize=(19, 5.5))
    for (k, lab), c in zip(links, ["tab:purple", "tab:red", "tab:green", "k"]):
        m = [summarize([s[k] for s in S[e]]) for e in EVOKE_SWEEP]
        ax[0].errorbar(EVOKE_SWEEP, [x[0] for x in m], yerr=[x[1] for x in m], marker="o", capsize=3,
                       label=lab, color=c, ls="--" if k == "match_conf" else "-")
    ax[0].axhline(0, color="gray", lw=0.6)
    ax[0].set_xlabel("how strongly a cue evokes its usual feeling (EVOKE)")
    ax[0].set_ylabel("rank correlation across places, mean over nights")
    ax[0].set_title("The links of the click, as cues start evoking feelings", fontsize=10)
    ax[0].legend(fontsize=8)

    z = lambda v: (v - v.mean()) / (v.std() + 1e-9)
    for s in S[EVOKE_MAIN]:
        ax[1].scatter(z(s["agg"]["match"]), z(s["agg"]["res"]), s=14, alpha=0.6)
    ax[1].set_xlabel("place matches the night's body state (z within night)")
    ax[1].set_ylabel("resonance: evoked feeling vs. the night's trace (z within night)")
    ax[1].set_title("Link 1: the agent can feel which place fits last night", fontsize=10)

    for s in S[EVOKE_MAIN]:
        ax[2].scatter(z(s["agg"]["res"]), s["agg"]["retrieval"], s=14, alpha=0.6)
    ax[2].set_xlabel("resonance (z within night)")
    ax[2].set_ylabel("share of recall equal to what was dreamed")
    ax[2].set_title(f"EVOKE={EVOKE_MAIN}: when it resonates, is it the real dream?", fontsize=10)
    plt.tight_layout()
    plt.savefig(os.path.join(args.out, "10_resonance.png"), dpi=120)
    plt.close()

    # ---------------- report
    L = ["== Cue-evoked feelings and the click ==",
         f"{args.seeds} agents x {args.nights} nights; one dream episode per night recalled at 5 places x "
         f"3 body states x 2; cue weight {G_RECALL}, body leak {RECALL_LEAK}.",
         "rank correlations across the 5 places, mean (s.e.) [nights positive / nights]", ""]
    for e in EVOKE_SWEEP:
        L.append(f"EVOKE = {e}" + ("   (= awaken.py, cues evoke nothing)" if e == 0 else ""))
        for k, lab in links + [("res_retr", "  resonance -> gives back the night"),
                               ("res_conf", "  resonance -> confidence (saturates, see mean)")]:
            m, se, pos, n = summarize([s[k] for s in S[e]])
            L.append(f"  {lab:<46} {m:+.2f} ({se:.2f}) [{pos}/{n}]")
        L.append(f"  {'mean share of recall equal to the dream':<46} "
                 f"{np.mean([s['retrieval'] for s in S[e]]):.2f}")
        L.append(f"  {'mean settling / mean confidence':<46} "
                 f"{np.mean([s['settle'] for s in S[e]]):.2f} / {np.mean([s['conf_mean'] for s in S[e]]):.2f}")
        L.append("")
    rows, dreamed, ctx = examples[EVOKE_MAIN]
    st = night_stats(rows)
    L.append(f"Example night (agent 1, EVOKE={EVOKE_MAIN}), body 'fine', first repeat:")
    L.append(f"  dreamed             : {narrative(dreamed, ctx['labels'])}")
    order = np.argsort(-st["agg"]["res"])
    for i in order:
        p = st["places"][i]
        r = next(x for x in rows if x["place"] == p and x["body"] == "fine" and x["rep"] == 0)
        L.append(f"  at {p:<11} res {st['agg']['res'][i]:6.2f} conf {st['agg']['conf'][i]:.2f}: "
                 f"{narrative(r['rec'], ctx['labels'])}")
    text = "\n".join(L)
    print(text)
    with open(os.path.join(args.out, "resonance_report.txt"), "w") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
