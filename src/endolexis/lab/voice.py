"""
NewNeural - a voice, described from the inside.

Expression is not "sending a message". From the creature's side there are no outputs,
only things it does and how its inputs change afterwards. So the creature gets one new
thing it can do (use its voice) and two new kinds of input:

  hearing (outside, 3 channels): how loud, how high, how rough the sound reaching its ears is.
      Its own voice reaches its ears like any other sound. The voice carries the body:
      weak when hungry or tired, high when aroused, rough when thirsty.
  throat  (inside, 1 channel): the vibration felt while its own voice sounds.
      Only its own voice is felt here; a voice of another creature is only heard.

Nothing tells the creature that the sound is "about" itself, that it is "mine", or that
another creature can hear it.

Predictions tested
  P1  A creature that wants to understand itself uses its voice more when the outside says
      little (in the dark), because hearing itself gives it outside material for
      self-reading. Controls: no wish to understand itself; deaf to its own voice.
  P2  Its own voice is less surprising than the same sound made by another, and a sound
      felt in the throat is read as being about itself more than the same sound only heard.
  P3  Asleep the voice is shut off, so it cannot supply the missing outside. If a little
      of it leaks (sleep-talking), dreams with the gate shut follow the body more.
  P4  Two creatures that hear each other coordinate as a side effect: their voices
      cluster in time and they stay closer, with no notion of a message built in.

Run:  python -m endolexis.lab.voice        (writes results/14_*.png and results/voice_report.txt)
"""
import argparse
import os
from multiprocessing import Pool
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import world2 as w2
from .cycles import gate_schedule, stabilize, NIGHT

VOICE_NAMES = ["hear:voice-loud", "hear:voice-pitch", "hear:voice-rough"]
EXT_DIM = w2.EXT_DIM + 3                       # 19
VO = w2.EXT_DIM                                # index of the first voice channel
NA = 10                                        # 5 moves x (quiet, voice)
BODY_CH = slice(0, 11)                         # inner channels from the body (not throat, not "how bad")
KAPPA = 0.15                                   # how much it wants to understand itself
STEPS = 20000
TRACK = [0, 1, 4, 5]                           # energy, water, fatigue, arousal: what the voice carries


def voice_quality(s):
    e, w, tp, d, f, ar = s
    return np.array([0.3 + 0.7 * e * (1 - 0.5 * f), 0.2 + 0.8 * ar, np.clip(1 - w + 0.3 * f, 0, 1)])


class Creature:
    def __init__(self, seed, start, hears_self=True, kappa=KAPPA, k_id=0):
        self.body = w2.Body2(nerves_seed=42, seed=seed + 31 * k_id)
        self.agent = w2.Agent2(ext_dim=EXT_DIM, seed=seed + 7 * k_id)
        self.agent._Q = np.zeros((self.agent.max, NA))
        self.pos = np.array(start)
        self.hears_self, self.kappa = hears_self, kappa
        self.voiced = False
        self.rng = np.random.default_rng(seed + 101 * k_id)


def qtab(agent):
    K = len(agent.mu)
    if agent._Q.shape[0] < K:
        Q = np.zeros((K, NA))
        Q[:agent._Q.shape[0]] = agent._Q
        agent._Q = Q
    return agent._Q


def act(agent, b, temp=0.05):
    v = b @ qtab(agent)[:len(b)] / temp
    p = np.exp(v - v.max())
    return int(agent.rng.choice(NA, p=p / p.sum()))


def update(agent, b, a, r, b2, alpha=0.1, gamma=0.98):
    Q = qtab(agent)
    target = r + gamma * (b2 @ Q[:len(b2)]).max()
    Q[:len(b), a] += alpha * b * (target - b @ Q[:len(b), a])


def heard(cr, others, world, rng, hear_others=True):
    """What reaches this creature's ears from voices (its own and others')."""
    snd = np.zeros(3)
    own = np.zeros(3)
    if cr.voiced and cr.hears_self:
        own = voice_quality(cr.body.s)
        snd += own
    if hear_others:
        for o in others:
            if o.voiced:
                att = np.exp(-np.abs(o.pos - cr.pos).sum() / 3)
                snd += att * voice_quality(o.body.s)
    snd = np.clip(snd, 0, 1.5) + rng.normal(0, 0.05 + 0.15 * world.rain, 3)
    return snd, own


def inner(cr):
    xi = cr.body.feel()
    throat = (1.0 if cr.voiced else 0.0) + cr.rng.normal(0, 0.1)
    return np.concatenate([xi[:-1], [throat], xi[-1:]])


def body_surprise(agent, x_ext, x_int):
    """From the inside: how badly the current self-reading expected the body's feelings."""
    k = int(np.argmax(agent.loglik(x_ext, x_int)))
    mu, var = agent.mu[k][EXT_DIM:], agent.var[k][EXT_DIM:]
    return float(((x_int[BODY_CH] - mu[BODY_CH]) ** 2 / var[BODY_CH]).mean()), k


def live(n=1, kind="mountain", seed=1, steps=STEPS, hears_self=True, hear_others=True, kappa=KAPPA):
    world = w2.World2(kind, seed=seed)
    starts = [(5, 5), (6, 3)]
    crs = [Creature(seed, starts[i], hears_self, kappa, i) for i in range(n)]
    rng = np.random.default_rng(seed + 5)
    state = []
    for cr in crs:
        xe = np.concatenate([world.sense(cr.pos, rng), heard(cr, [], world, rng)[0]])
        xi = inner(cr)
        cr.agent.learn(xe, xi)
        state.append([cr.agent.interpret(xe, xi), xi[-1] / 3])
    log = [{k: [] for k in ("concept", "vitals", "voiced", "light", "pos", "surprise", "ext", "own", "loud_other")}
           for _ in crs]
    for t in range(steps):
        acts = []
        for i, cr in enumerate(crs):
            a = act(cr.agent, state[i][0])
            acts.append(a)
            cr.pos = np.clip(cr.pos + w2.MOVES[a % 5], 0, world.n - 1)
            cr.voiced = a >= 5
        world.step(crs[0].pos)
        for i, cr in enumerate(crs):
            cr.body.step(world, cr.pos, acts[i] % 5)
            if cr.voiced:                                       # voicing costs a little, dries the throat
                cr.body.s[0] = max(0, cr.body.s[0] - 0.0008)
                cr.body.s[1] = max(0, cr.body.s[1] - 0.0006)
        for i, cr in enumerate(crs):
            others = [o for j, o in enumerate(crs) if j != i]
            snd, own = heard(cr, others, world, rng, hear_others)
            xe = np.concatenate([world.sense(cr.pos, rng), snd])
            xi = inner(cr)
            c = cr.agent.learn(xe, xi)
            b2 = cr.agent.interpret(xe, xi)
            sur, _ = body_surprise(cr.agent, xe, xi)
            felt = xi[-1] / 3
            b, prev = state[i]
            r = 10 * (prev - felt) - 0.1 * felt - cr.kappa * min(sur, 4)
            update(cr.agent, b, acts[i], r, b2)
            state[i] = [b2, felt]
            L = log[i]
            L["concept"].append(c)
            L["vitals"].append(cr.body.s.copy())
            L["voiced"].append(cr.voiced)
            L["light"].append(world.light())
            L["pos"].append(cr.pos.copy())
            L["surprise"].append(sur)
            L["ext"].append(xe)
            L["own"].append(own[0] if cr.voiced else 0.0)
            L["loud_other"].append(snd[0] - (own[0] if cr.voiced else 0.0))
    return crs, [{k: np.array(v) for k, v in L.items()} for L in log]


def concept_map(log, K):
    """Observer's dictionary: the average true body state that went with each concept."""
    m = np.zeros((K, 6))
    for k in range(K):
        sel = log["concept"] == k
        m[k] = log["vitals"][sel].mean(0) if sel.any() else w2.SETPOINT
    return m


def reading_error(log, cmap, sel):
    v, c = log["vitals"][sel], log["concept"][sel]
    return float(np.abs(v[:, TRACK] - cmap[c][:, TRACK]).mean())


# ----------------------------------------------------------------------------- P1
P1_CONDS = {"hears": dict(hears_self=True, kappa=KAPPA),
            "comfort": dict(hears_self=True, kappa=0.0),
            "deaf": dict(hears_self=False, kappa=KAPPA)}
P1_LABELS = {"hears": "hears itself, wants to understand itself",
             "comfort": "hears itself, wants comfort only",
             "deaf": "deaf to its own voice, wants to understand itself"}


def run_p1(args):
    cond, seed, steps = args
    crs, logs = live(1, "mountain", seed, steps, **P1_CONDS[cond])
    L = logs[0]
    h = slice(steps // 2, None)
    light, vo = L["light"][h], L["voiced"][h]
    dark, bright = light < 0.3, light > 0.7
    cmap = concept_map({k: v[h] for k, v in L.items()}, len(crs[0].agent.mu))
    sub = {k: v[h] for k, v in L.items()}
    err = {}
    for nm, s in (("dark", dark), ("bright", bright)):
        for vn, vv in (("voice", vo), ("quiet", ~vo)):
            sel = s & vv
            err[(nm, vn)] = reading_error(sub, cmap, sel) if sel.sum() > 30 else np.nan
    # voice rate across the day (24 bins of the day cycle)
    ph = (np.arange(steps)[h] % w2.DAY) * 24 // w2.DAY
    by_hour = np.array([vo[ph == b].mean() for b in range(24)])
    sur = L["surprise"][h]
    return dict(cond=cond, seed=seed, v_dark=vo[dark].mean(), v_bright=vo[bright].mean(),
                err=err, by_hour=by_hour, K=len(crs[0].agent.mu),
                sur_voice=sur[vo].mean(), sur_quiet=sur[~vo].mean(),
                distress=np.mean([w2.Body2().distress(s) for s in L["vitals"][h][::10]]))


# ----------------------------------------------------------------------------- P4 + P2
def run_pair(args):
    cond, seed, steps = args
    crs, logs = live(2, "mountain", seed, steps, hears_self=True, hear_others=(cond == "together"))
    h = slice(steps // 2, None)
    va, vb = logs[0]["voiced"][h], logs[1]["voiced"][h]
    dist = np.abs(logs[0]["pos"][h] - logs[1]["pos"][h]).sum(1)
    # does B's voice follow A's (and vice versa) within 3 steps, beyond chance?
    def follow(x, y):
        nxt = np.zeros_like(y)
        for lag in (1, 2, 3):
            nxt[:-lag] |= y[lag:]
        return nxt[x].mean() / max(nxt.mean(), 1e-9)
    sync = 0.5 * (follow(va, vb) + follow(vb, va))
    near = dist <= 3
    out = dict(cond=cond, seed=seed, sync=sync, dist=dist.mean(), near=near.mean(),
               v=0.5 * (va.mean() + vb.mean()))
    if cond == "together":
        # P2a: surprise of the heard voice under the creature's own reading - own vs other's, matched loudness
        own_s, oth_s = [], []
        for cr, L in zip(crs, logs):
            ag = cr.agent
            ag.learning = False
            ext, vi = L["ext"][h], L["vitals"][h]
            for t in range(0, len(ext), 3):
                own, oth = L["own"][h][t], L["loud_other"][h][t]
                loud = ext[t, VO]
                if not (0.45 < loud < 1.1):
                    continue
                if own > 0.4 and oth < 0.1:
                    bucket = own_s
                elif own == 0 and oth > 0.4:
                    bucket = oth_s
                else:
                    continue
                # surprise of the heard voice, given how it reads itself from everything else
                xi = np.concatenate([cr.body.feel(vi[t])[:-1], [1.0 if own > 0 else 0.0], [3 * cr.body.distress(vi[t])]])
                p = ag.interpret(np.r_[ext[t, :VO], np.zeros(3)], xi, lam_ext=1.0)
                mu = np.array(ag.mu)[:, VO:EXT_DIM]
                var = np.array(ag.var)[:, VO:EXT_DIM]
                z = ((ext[t, VO:EXT_DIM] - mu) ** 2 / var).mean(1)
                bucket.append(float(p @ z))
        out["sur_own"] = np.mean(own_s) if own_s else np.nan
        out["sur_other"] = np.mean(oth_s) if oth_s else np.nan
        out["n_own"], out["n_other"] = len(own_s), len(oth_s)
        # P2b: the same heard voice, felt in the throat or not: how much does it move the self-reading?
        slopes = {"felt (mine)": [], "only heard": []}
        for cr, L in zip(crs, logs):
            ag = cr.agent
            cmap = concept_map({k: v[h] for k, v in L.items()}, len(ag.mu))
            base_ext = L["ext"][h][L["light"][h] > 0.7].mean(0)
            neutral = cr.body.feel(w2.SETPOINT.copy())
            for nm, th in (("felt (mine)", 1.0), ("only heard", 0.0)):
                ev = []
                for state in ("fresh", "worn"):
                    s = w2.SETPOINT.copy()
                    if state == "worn":
                        s[[0, 1, 4]] = [0.25, 0.3, 0.8]
                    q = voice_quality(s)
                    acc = np.zeros(6)
                    for rep in range(30):
                        xe = base_ext.copy()
                        xe[VO:] = q + np.random.default_rng(rep).normal(0, 0.05, 3)
                        xi = np.concatenate([cr.body.feel(w2.SETPOINT.copy())[:-1], [th], [neutral[-1]]])
                        acc += ag.interpret(xe, xi) @ cmap / 30
                    ev.append(acc)
                # how much worse-off the creature reads itself when the voice sounds worn
                d = ev[1] - ev[0]
                slopes[nm].append(float(-d[0] - d[1] + d[4]))
        out["evoke"] = {k: np.mean(v) for k, v in slopes.items()}
    return out


# ----------------------------------------------------------------------------- P3
def run_p3(args):
    seed, steps, nights = args
    crs, logs = live(1, "mountain", seed, steps, hears_self=True, kappa=KAPPA)
    cr, L = crs[0], logs[0]
    ag = cr.agent
    ag.learning = False
    K = len(ag.mu)
    h = slice(steps // 2, None)
    cmap = concept_map({k: v[h] for k, v in L.items()}, K)
    seq = L["concept"]
    T = np.ones((K, K)) * 0.01
    for a, b in zip(seq[:-1], seq[1:]):
        T[a, b] += 1
    T /= T.sum(1, keepdims=True)
    mu_ext = np.array(ag.mu)[:, :EXT_DIM]
    gate = gate_schedule()
    res = {"muted": [], "sleep-talk": []}
    chg = {"muted": [], "sleep-talk": []}
    for night in range(nights):
        for cond in res:
            rng = np.random.default_rng(1000 * seed + night)
            world = w2.World2("mountain", seed=seed + 50)
            cave = np.array([10, 1])
            body = w2.Body2(nerves_seed=42, seed=seed + 7 + night)
            body.s = np.array([0.6, 0.6, 0.55, 0.1, 0.7, 0.3])
            prev = int(rng.integers(K))
            reading, truth, talk = [], [], []
            for t in range(NIGHT):
                world.t = w2.DAY // 2
                e, w, tp, d, f, ar = body.s
                # the body wanders through the night: a slow drift plus a few restless spells
                ar_target = 0.15 + 0.5 * (np.sin(2 * np.pi * t / 170 + night) > 0.6)
                body.s = np.clip([e - 0.0006, w - 0.0008, tp + 0.05 * (0.55 - tp), d - 0.002,
                                  f - 0.002, ar + 0.1 * (ar_target - ar)] + rng.normal(0, 0.004, 6), 0, 1)
                talking = cond == "sleep-talk" and rng.random() < 0.25
                real = np.concatenate([world.sense(cave, rng),
                                       (voice_quality(body.s) if talking else np.zeros(3)) + rng.normal(0, 0.05, 3)])
                xi = body.feel()
                xi = np.concatenate([xi[:-1], [(0.4 if talking else 0.0) + rng.normal(0, 0.1)], xi[-1:]])
                g = gate[t]
                imagined = T[prev] @ mu_ext
                x_ext = g * real + (1 - g) * imagined
                if talking:                                    # own voice also reaches the ear through the bones
                    x_ext[VO:] = real[VO:]
                ll = ag.loglik(x_ext + rng.normal(0, 0.1, EXT_DIM), xi)
                logp = np.log(T[prev]) + ll
                p = np.exp(logp - logp.max())
                prev = int(rng.choice(K, p=p / p.sum()))
                reading.append(prev)
                truth.append(body.s.copy())
            reading, truth = np.array(reading), np.array(truth)
            shut = gate < 0.02
            res[cond].append(float(np.abs(truth[shut][:, TRACK] - cmap[reading[shut]][:, TRACK]).mean()))
            st = stabilize(reading)
            ch = np.r_[False, st[1:] != st[:-1]]
            chg[cond].append(100 * ch[shut].mean())
    return dict(seed=seed, err={k: np.mean(v) for k, v in res.items()},
                chg={k: np.mean(v) for k, v in chg.items()}, paired=np.array(res["muted"]) - np.array(res["sleep-talk"]))


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=STEPS)
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--nights", type=int, default=4)
    ap.add_argument("--out", default="results")
    ap.add_argument("--procs", type=int, default=os.cpu_count())
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    S = range(1, args.seeds + 1)
    jobs1 = [(c, s, args.steps) for c in P1_CONDS for s in S]
    jobs4 = [(c, s, args.steps) for c in ("together", "apart") for s in S]
    jobs3 = [(s, args.steps, args.nights) for s in S]
    with Pool(args.procs) as pool:
        r1 = pool.map_async(run_p1, jobs1)
        r4 = pool.map_async(run_pair, jobs4)
        r3 = pool.map_async(run_p3, jobs3)
        r1, r4, r3 = r1.get(), r4.get(), r3.get()

    R = []
    se = lambda x: np.std(x) / np.sqrt(len(x))
    # --- P1
    R += ["== P1: does it use its voice more when the outside says little? (mountain, no predator) ==",
          f"{args.seeds} creatures per condition, {args.steps} steps; second half of life", ""]
    fig, ax = plt.subplots(1, 3, figsize=(17, 4.8))
    cols = {"hears": "tab:blue", "comfort": "tab:gray", "deaf": "tab:orange"}
    for c in P1_CONDS:
        rr = [r for r in r1 if r["cond"] == c]
        dd = np.array([r["v_dark"] for r in rr])
        bb = np.array([r["v_bright"] for r in rr])
        diff = dd - bb
        hours = np.array([r["by_hour"] for r in rr])
        ax[0].plot(np.arange(24) + 0.5, hours.mean(0), marker="o", ms=3, color=cols[c], label=P1_LABELS[c])
        R += [P1_LABELS[c],
              f"  voice used: dark {dd.mean():.3f}  bright {bb.mean():.3f}  "
              f"dark minus bright {diff.mean():+.3f} (s.e. {se(diff):.3f}), more in the dark for {np.sum(diff > 0)}/{len(diff)}",
              f"  inner surprise: while voicing {np.mean([r['sur_voice'] for r in rr]):.2f}  while quiet {np.mean([r['sur_quiet'] for r in rr]):.2f}",
              f"  how bad it feels (body distress) {np.mean([r['distress'] for r in rr]):.3f}; concepts {np.mean([r['K'] for r in rr]):.0f}"]
        e = {k: np.nanmean([r["err"][k] for r in rr]) for k in rr[0]["err"]}
        R.append("  self-reading error (observer): " + "  ".join(f"{a}/{b} {e[(a, b)]:.3f}" for a, b in e))
        R.append("")
    light = 0.5 + 0.6 * np.cos(2 * np.pi * (np.arange(24) + 0.5) / 24)
    a2 = ax[0].twinx()
    a2.fill_between(np.arange(24) + 0.5, np.clip(light, 0.03, 1), color="gold", alpha=0.12)
    a2.set_yticks([])
    a2.set_ylim(0, 1.05)
    ax[0].set_xlabel("hour of its day (shaded = daylight)")
    ax[0].set_ylabel("share of steps with voice")
    ax[0].set_title("When does it use its voice?")
    ax[0].legend(fontsize=7)
    # reading error, hears condition
    rr = [r for r in r1 if r["cond"] == "hears"]
    keys = [("bright", "quiet"), ("bright", "voice"), ("dark", "quiet"), ("dark", "voice")]
    vals = np.array([[r["err"][k] for k in keys] for r in rr])
    ax[1].bar(range(4), np.nanmean(vals, 0), yerr=np.nanstd(vals, 0) / np.sqrt(len(vals)),
              color=["#f1d27a", "#c99a1e", "#8d9db6", "#3c5a8a"], capsize=3)
    ax[1].set_xticks(range(4))
    ax[1].set_xticklabels(["light,\nquiet", "light,\nvoice", "dark,\nquiet", "dark,\nvoice"])
    ax[1].set_ylabel("error of its self-reading (observer)")
    ax[1].set_title("How well does it read its body?")
    # --- P4
    R += ["== P4: two creatures, one world (mountain). Hearing each other vs not ==", ""]
    for c, nm in (("together", "they hear each other"), ("apart", "each hears only itself")):
        rr = [r for r in r4 if r["cond"] == c]
        R.append(f"{nm}: voice follows voice x{np.mean([r['sync'] for r in rr]):.2f} (1 = chance), "
                 f"mean distance {np.mean([r['dist'] for r in rr]):.2f}, within 3 steps {np.mean([r['near'] for r in rr]):.2f} of the time, "
                 f"voice used {np.mean([r['v'] for r in rr]):.3f}")
    tg = np.array([r["sync"] for r in r4 if r["cond"] == "together"])
    ap_ = np.array([r["sync"] for r in r4 if r["cond"] == "apart"])
    dt = np.array([r["dist"] for r in r4 if r["cond"] == "together"])
    da = np.array([r["dist"] for r in r4 if r["cond"] == "apart"])
    R += [f"  paired by seed: voice-follows-voice higher when they hear each other on {np.sum(tg > ap_)}/{len(tg)}; "
          f"closer on {np.sum(dt < da)}/{len(dt)}", ""]
    x = np.arange(2)
    ax[2].bar(x - 0.2, [ap_.mean(), da.mean() / 6], 0.4, color="lightgray", label="each hears only itself")
    ax[2].bar(x + 0.2, [tg.mean(), dt.mean() / 6], 0.4, color="tab:green", label="they hear each other")
    ax[2].axhline(1, color="k", lw=0.5, ls=":")
    ax[2].set_xticks(x)
    ax[2].set_xticklabels(["voice follows voice\n(1 = chance)", "distance apart\n(steps / 6)"])
    ax[2].set_title("Two creatures: side effects of hearing")
    ax[2].legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(os.path.join(args.out, "14_voice.png"), dpi=115)
    plt.close()
    # --- P2
    rr = [r for r in r4 if r["cond"] == "together"]
    so, sot = np.array([r["sur_own"] for r in rr]), np.array([r["sur_other"] for r in rr])
    ok = ~np.isnan(so) & ~np.isnan(sot)
    ev_m = np.array([r["evoke"]["felt (mine)"] for r in rr])
    ev_o = np.array([r["evoke"]["only heard"] for r in rr])
    R += ["== P2: my voice and someone else's (from the pairs that hear each other) ==",
          f"  surprise of a heard voice of matched loudness: own {np.nanmean(so):.2f}  other's {np.nanmean(sot):.2f}; "
          f"own less surprising for {np.sum(so[ok] < sot[ok])}/{ok.sum()} creature-pairs",
          f"  samples: own {sum(r['n_own'] for r in rr)}, other's {sum(r['n_other'] for r in rr)}",
          f"  a worn-sounding voice moves the self-reading toward 'worn': felt in the throat {ev_m.mean():+.3f}  "
          f"only heard {ev_o.mean():+.3f}; larger when felt for {np.sum(ev_m > ev_o)}/{len(ev_m)}", ""]
    # --- P3
    em = np.array([r["err"]["muted"] for r in r3])
    et = np.array([r["err"]["sleep-talk"] for r in r3])
    cm = np.array([r["chg"]["muted"] for r in r3])
    ct = np.array([r["chg"]["sleep-talk"] for r in r3])
    pd = np.concatenate([r["paired"] for r in r3])
    R += ["== P3: asleep, gate shut. Muted voice vs a little sleep-talking (interpreter B) ==",
          f"  dream follows the body (reading error, lower = closer): muted {em.mean():.3f}  sleep-talk {et.mean():.3f}; "
          f"closer with sleep-talk on {np.sum(pd > 0)}/{len(pd)} nights",
          f"  scene changes /100 steps with the gate shut: muted {cm.mean():.2f}  sleep-talk {ct.mean():.2f}", ""]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ax[0].bar([0, 1], [np.nanmean(so), np.nanmean(sot)], yerr=[se(so[ok]), se(sot[ok])], capsize=3,
              color=["tab:blue", "tab:green"])
    ax[0].set_xticks([0, 1])
    ax[0].set_xticklabels(["my own voice", "the other's voice\n(same loudness)"])
    ax[0].set_ylabel("surprise of what is heard")
    ax[0].set_title("P2: is my own voice less surprising?")
    ax[1].bar([0, 1], [em.mean(), et.mean()], yerr=[se(em), se(et)], capsize=3, color=["gray", "tab:purple"])
    ax[1].set_xticks([0, 1])
    ax[1].set_xticklabels(["voice muted\n(normal sleep)", "a little\nsleep-talking"])
    ax[1].set_ylabel("dream vs body: reading error")
    ax[1].set_title("P3: gate shut - does hearing itself tie the dream to the body?")
    plt.tight_layout()
    plt.savefig(os.path.join(args.out, "14_voice_self.png"), dpi=115)
    plt.close()
    text = "\n".join(R)
    print(text)
    with open(os.path.join(args.out, "voice_report.txt"), "w") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
