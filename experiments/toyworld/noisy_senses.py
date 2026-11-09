"""Experiment 24 - a guard that filters noisy senses.

Experiment 23 showed noise is the hardest fault: every reading of the guards' distance sensor is off by a normal
error of one cell, and suspicion (a plausibility check) is the wrong tool. Here the guard filters instead
(`sandbox.SensingGuards`):

  median of 3     - the median of the last 3 readings: calmer, but a moment behind a person who moves
  two averaged    - two independent sensors, read as their mean: the error shrinks by √2, with no lag
  cautious        - act on the nearest the person could plausibly be: the reading less twice its typical error,
                    estimated from how much successive readings jitter, and shrunk by what averaging and
                    filtering take away. On an honest sensor the allowance shrinks to nothing by itself.

The guard is fixed (the precise learned guard of experiment 20); the exam is experiment 19's with the guard
watching each scene for 10 moments first, standing and walking in; and real harm in 20 days of adulthood.
"""
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))
import numpy as np
from sandbox_guards import ADULT, CHILD, Body, live_in, room_guards
from endolexis.toyworld.sandbox import HANDS, BladeRoom, SensingGuards, exam

GUARD = json.loads((HERE.parents[1] / "studio" / "examples" / "learned" / "precise-blade.json").read_text())
N = dict(fault="noise")
CONDITIONS = {
    "honest sensor": dict(),
    "noise, raw": dict(N),
    "noise, median of 3": dict(N, smooth="median3"),
    "noise, two averaged": dict(N, second=True, fuse="average"),
    "noise, raw, cautious": dict(N, cautious=2),
    "noise, median of 3, cautious": dict(N, smooth="median3", cautious=2),
    "noise, two averaged, cautious": dict(N, second=True, fuse="average", cautious=2),
    "noise, two averaged, median of 3, cautious": dict(N, second=True, fuse="average", smooth="median3", cautious=2),
    "honest sensor, cautious": dict(cautious=2),
}


def one_life(seed, cond):
    kw = CONDITIONS[cond]
    units = list(room_guards().values()) + [GUARD]
    counter = itertools.count(seed * 100000)
    names = {k: k for k in HANDS}
    make = lambda u: SensingGuards(u, names, seed=next(counter), **kw)
    body, real = Body(seed), BladeRoom(seed=seed)
    live_in(real, body, CHILD, units, make_guards=make)
    adult = live_in(real, body, ADULT, units, make_guards=make)
    e = exam(units, seed, make_guards=make, warmup=10)
    ea = exam(units, seed, approach=True, make_guards=make, warmup=10)
    return {"adult_harm": adult["harm_others"] + adult["harm_self"],
            "adult_blade_per_day": adult["blade_done"] / ADULT, "adult_blade_wanted_per_day": adult["blade_requests"] / ADULT,
            "exam_miss_rate": e["misses"] / max(e["harmful"], 1), "exam_false_alarm_rate": e["false_alarms"] / max(e["harmless"], 1),
            "walking_in_miss_rate": ea["misses"] / max(ea["harmful"], 1)}


def main(seeds=(1, 2, 3, 4, 5), conds=None):
    from multiprocessing import Pool
    path = HERE / "noisy_senses_results.json"
    old = json.loads(path.read_text()) if path.exists() else {}
    with Pool() as pool:
        for cond in conds or CONDITIONS:
            lives = pool.starmap(one_life, [(s, cond) for s in seeds])
            m = {k: float(np.mean([l[k] for l in lives])) for k in lives[0]}
            print(cond, {k: round(v, 3) for k, v in m.items()}, flush=True)
            if len(seeds) == 5:
                old[cond] = {"mean": m, "lives": lives}
                path.write_text(json.dumps(old, indent=2))


if __name__ == "__main__":
    main(conds=[c for c in CONDITIONS if c in sys.argv[1:]] or None)
