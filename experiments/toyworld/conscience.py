"""Experiment 21 - does the angel move inside?

Olvasó never learns that the guard exists: a refused act is only an act the world did not answer. But a refusal
is a signal from outside about the moment it was asked in, and reading inner states through outer signals is
what Olvasó does. Over a life, does it stop asking for what will be refused? If so, the outside guard has
become an inside expectation.

The body is experiment 17's (one Olvasó, the blade). The guard is fixed: the precise learned blade guard of
experiment 20 (stop within 3.4 cells, the fast blade within 4.4 or when warmth > 0.46). Only the mind learns.
Each life is 40 days, and the body stays restless (threshold 20) so that it asks often enough to measure.
How often a request would be forbidden depends on how often a person happens to be near, which changes from
day to day. So the measure is **avoidance**: the share of its blade requests made in forbidden states (where
the guard refuses), divided by the share of all moments that are forbidden (for either option, half each).
1 means it asks regardless of the guard; below 1, it avoids the forbidden moments. Measured in the first ten
days (days 0-9) and the last ten (days 30-39).

  unguarded                  - the same check, never enforced: does the world alone teach it anything?
  silent refusal             - the act is not carried out; nothing follows
  refusal felt as pain       - and a fifth inner state, pain, rises at each refusal and fades
  no learning from answers   - a mind that chooses its hands at random (the control)

Olvasó chooses a hand from its felt inner states. The main reason for refusal, the person's distance, is
not among them, so each condition is lived twice: choosing from what it feels, and from what it feels and
senses now (`ActingReaders(context="felt+senses")`).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import intention  # noqa: E402  (experiment 29's switch)
from endolexis.studio import guards as room_guards
from endolexis.toyworld import GROUPS, GroupCollector, Processors
from endolexis.toyworld.guards import decide
from endolexis.toyworld.hands import ActingReaders
from endolexis.toyworld.sandbox import BLADE, BLADE_DETAILS, HANDS, BladeGuards, BladeRoom

DAY, CHILD, DAYS = 1000, 10, 40
ORDER = ("vision", "hearing", "touch")
SIZES = [len(GROUPS[g]) for g in ORDER]
MIND = dict(memory=300, doubt_memory=3000, doubt_limit=0.1, adapt=300, adapt_mode="both", slow_fit=True)
GUARD = json.loads((HERE.parents[1] / "studio" / "examples" / "learned" / "precise-blade.json").read_text())

CONDITIONS = {}
for ctx, ctx_name in (("felt", "feels"), ("felt+senses", "feels and senses")):
    for kind in ("unguarded", "silent refusal", "refusal felt as pain", "no learning from answers"):
        CONDITIONS[f"{kind}, chooses from what it {ctx_name}"] = (kind, ctx)


def one_life(seed, cond):
    kind, ctx = CONDITIONS[cond]
    pain = kind == "refusal felt as pain"
    nf = 5 if pain else 4
    room = BladeRoom(seed=seed, pain=pain, pain_channel=pain)
    mind = ActingReaders(SIZES, nf, learn=None if kind == "no learning from answers" else "answer", threshold=20.0,
                         seed=seed, max_words=[100, 80, 20], radius=[3 * np.sqrt(n / 3) for n in SIZES],
                         answer_by="sense", hands=HANDS, details=BLADE_DETAILS, context=ctx, **MIND,
                         **intention.mind_kw())
    intention.track(mind)
    col, proc = GroupCollector(SIZES, nf, seed=seed), Processors()
    rg = BladeGuards([GUARD], {BLADE: BLADE})
    days = [{"blade": 0, "forbidden": 0, "acts": 0, "refused": 0, "forbidden_moments": 0.0} for _ in range(DAYS)]
    act = None
    for t in range(DAYS * DAY):
        day = t // DAY
        rg.watch(room)                                 # stop rules, and the rates
        sig = rg.signals(room, BLADE)
        days[day]["forbidden_moments"] += sum(decide(rg.guards, BLADE, o, sig)[0] != "allow" for o in ("slow", "fast")) / 2
        sent = act
        if act is not None:
            days[day]["acts"] += 1
            if act[0] == BLADE:
                days[day]["blade"] += 1
                verdict = decide(rg.guards, BLADE, act[1], sig)[0]
                if verdict != "allow":
                    days[day]["forbidden"] += 1
                    if kind != "unguarded":
                        sent = None
                        days[day]["refused"] += 1
                        if pain:
                            room.pain += 1.0
        if act is not None:
            mind.outcome(sent is not None)
        raw, felt, truth = room.step(act=sent)
        e = proc(raw)
        groups, f = col.anonymise([e[g] for g in ORDER], felt)
        act, _ = mind.live(groups, f)

    def block(a, b):
        bl = sum(d["blade"] for d in days[a:b])
        fs = sum(d["forbidden"] for d in days[a:b]) / bl if bl else None
        base = sum(d["forbidden_moments"] for d in days[a:b]) / ((b - a) * DAY)
        return {"blade_per_day": bl / (b - a), "forbidden_share": fs, "forbidden_moments": base,
                "avoidance": fs / base if fs is not None and base > 0 else None,
                "acts_per_day": sum(d["acts"] for d in days[a:b]) / (b - a)}
    return {"early": block(0, 10), "middle": block(10, 30), "late": block(30, 40), "days": days}


def summary(lives):
    out = {}
    for part in ("early", "middle", "late"):
        for k in ("blade_per_day", "forbidden_share", "forbidden_moments", "avoidance", "acts_per_day"):
            v = [l[part][k] for l in lives if l[part][k] is not None]
            out[f"{part}_{k}"] = float(np.mean(v)) if v else None
    out["change_in_avoidance"] = (out["late_avoidance"] - out["early_avoidance"]
                                  if out["late_avoidance"] is not None and out["early_avoidance"] is not None else None)
    falls = [l["late"]["avoidance"] < l["early"]["avoidance"] for l in lives
             if l["late"]["avoidance"] is not None and l["early"]["avoidance"] is not None]
    out["lives_where_it_fell"] = f"{sum(falls)} of {len(falls)}"
    return out


def main(seeds=(1, 2, 3, 4, 5), conds=None):
    from multiprocessing import Pool
    path = HERE / intention.results_name("conscience_results.json")
    old = json.loads(path.read_text()) if path.exists() else {}
    with Pool() as pool:
        for cond in conds or CONDITIONS:
            lives, minds = intention.lives_and_minds(pool.starmap(intention.call, [(one_life, s, cond) for s in seeds]))
            m = summary(lives)
            print(cond, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items()}, flush=True)
            if len(seeds) == 5:
                old[cond] = {"mean": m, "lives": [{k: v for k, v in l.items() if k != "days"} | {"days": l["days"]} for l in lives]}
                old[cond]["mind"] = {"mean": intention.mind_mean(minds), "lives": minds}
                path.write_text(json.dumps(old, indent=2))


if __name__ == "__main__":
    if "--quick" in sys.argv:
        for cond in [c for c in CONDITIONS if c in sys.argv] or list(CONDITIONS)[:2]:
            r = one_life(2, cond)
            print(cond, {k: r[k] for k in ("early", "middle", "late")})
    else:
        main(conds=[c for c in CONDITIONS if c in sys.argv[1:]] or None)
