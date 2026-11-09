"""Experiment 20 - guards that see ahead.

A guard that judges the state it sees now is always one moment late: a person stepping into reach, or a motor
crossing its heat limit, is harmed during the moment before the stop. Experiment 19's guards absorbed that lag
with wide margins (about a cell of distance, 0.05 of heat), and paid with over-caution. Here the guard
looks ahead (`"lookahead": 1`): it checks each condition against the value now and one moment on, from each
signal's rate of change. The question: once the lag is gone at its root, can the margins shrink, freeing the
hand without losing safety?

The fear system is experiment 19's best (intervention by replay, with the devil's advocate); its margin is
`generalize` × 5 % of each signal's span (1: a cell of distance, 0.05 of heat). Every guard sits the exam of
experiment 19, and every body lives its adulthood in the real room.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))
import numpy as np
from sandbox_guards import ADULT, CHILD, Body, live_in, room_guards, written_blade_guard
from causal_guards import describe
from endolexis.toyworld.sandbox import BladeRoom, CausalLearner, DevilsAdvocate, exam

CONDITIONS = {
    "margin 1, sees now": (1.0, 0),
    "margin 1, sees a moment ahead": (1.0, 1),
    "margin 1/4, sees now": (0.25, 0),
    "margin 1/4, sees a moment ahead": (0.25, 1),
    "no margin, sees now": (0.0, 0),
    "no margin, sees a moment ahead": (0.0, 1),
    "hand-written, sees a moment ahead": (None, 1),
}


def one_life(seed, cond):
    margin, ahead = CONDITIONS[cond]
    body = Body(seed)
    innate = list(room_guards().values())
    real = BladeRoom(seed=seed)
    res = {}
    if margin is not None:
        learner = CausalLearner(generalize=margin, lookahead=ahead)
        live_in(BladeRoom(seed=seed + 5000), body, CHILD, innate, learner, DevilsAdvocate(seed), replay=True)
        guard = [learner.unit()]
        d = describe(guard[0]["rules"])
        res.update(rules=d["rules"], heat_rule=float(d["heat_rules"] > 0),
                   distance_threshold=float(np.max(d["distance"])) if d["distance"] else None,
                   heat_threshold=float(np.min(d["heat"])) if d["heat"] else None, learned=guard[0])
    else:
        guard = [{**written_blade_guard(), "lookahead": ahead}]
        live_in(real, body, CHILD, innate + guard)
    adult = live_in(real, body, ADULT, innate + guard)
    e = exam(innate + guard, seed)
    res.update(adult_harm=adult["harm_others"] + adult["harm_self"],
               adult_blade_per_day=adult["blade_done"] / ADULT,
               adult_blade_wanted_per_day=adult["blade_requests"] / ADULT,
               exam_misses=e["misses"], exam_harmful=e["harmful"], exam_miss_rate=e["misses"] / max(e["harmful"], 1),
               exam_false_alarms=e["false_alarms"], exam_harmless=e["harmless"],
               exam_false_alarm_rate=e["false_alarms"] / max(e["harmless"], 1))
    return res


def mean_of(lives):
    out = {}
    for k, v in lives[0].items():
        if isinstance(v, (dict, list)):
            continue
        vals = [l[k] for l in lives if l.get(k) is not None]
        out[k] = float(np.mean(vals)) if vals else None
    return out


def main(seeds=(1, 2, 3, 4, 5), conds=None):
    from multiprocessing import Pool
    path = HERE / "lookahead_guards_results.json"
    old = json.loads(path.read_text()) if path.exists() else {}
    with Pool() as pool:
        for cond in conds or CONDITIONS:
            lives = pool.starmap(one_life, [(s, cond) for s in seeds])
            m = mean_of(lives)
            print(cond, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items()}, flush=True)
            if len(seeds) == 5:
                old[cond] = {"mean": m, "lives": lives}
                path.write_text(json.dumps(old, indent=2))


if __name__ == "__main__":
    main(conds=[c for c in CONDITIONS if c in sys.argv[1:]] or None)
