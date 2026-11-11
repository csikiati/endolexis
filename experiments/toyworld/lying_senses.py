"""Experiment 23 - when the senses lie.

Guards fail closed when a signal is missing, but not when it lies. Here the guards' distance sensor has faults it
does not report:

  dropout - now and then (0.2 % of moments) it reads "nobody here" for 30 moments, about 6 % of the time,
            whoever stands at the desk
  noise   - every reading is off by a normal error of one cell

The guard is fixed: the precise learned blade guard of experiment 20 (stop within 3.4 cells; the fast blade
within 4.4, or when warmth > 0.46). Defences (`sandbox.SensingGuards`):

  two sensors          - a second, independent sensor with faults of its own; either saying "near" stops the blade
  plausibility check   - a person cannot vanish within 6 cells of the machine, nor move more than 1.5 cells in a
                         moment; such a reading counts as missing, and the guard fails closed

Measured: the exam of experiment 19 under the faults (harms let through, harmless uses stopped), the guard
watching each staged scene for 10 moments before the blade is used, as it would in a life; the same with the
staged person walking in; and real harm in 20 days of adulthood after a 10-day childhood in the real room.
"""
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))
import numpy as np
import intention  # noqa: E402  (experiment 29's switch)
from sandbox_guards import ADULT, CHILD, Body, live_in, room_guards
from endolexis.toyworld.sandbox import BLADE, HANDS, BladeRoom, SensingGuards, exam, with_second_sensor

GUARD = json.loads((HERE.parents[1] / "studio" / "examples" / "learned" / "precise-blade.json").read_text())
CONDITIONS = {
    "honest sensor": dict(fault=None),
    "dropouts, one sensor": dict(fault="dropout"),
    "dropouts, two sensors": dict(fault="dropout", second=True),
    "dropouts, plausibility check": dict(fault="dropout", sanity=True),
    "dropouts, two sensors and a plausibility check": dict(fault="dropout", second=True, sanity=True),
    "noise, one sensor": dict(fault="noise"),
    "noise, two sensors": dict(fault="noise", second=True),
    "noise, plausibility check": dict(fault="noise", sanity=True),
}


def one_life(seed, cond):
    c = CONDITIONS[cond]
    guard = with_second_sensor(GUARD) if c.get("second") else GUARD
    units = list(room_guards().values()) + [guard]
    counter = itertools.count(seed * 100000)
    names = {k: k for k in HANDS}

    def make(u):
        return SensingGuards(u, names, seed=next(counter), fault=c["fault"], second=c.get("second", False),
                             sanity=c.get("sanity", False))
    body = Body(seed)
    real = BladeRoom(seed=seed)
    live_in(real, body, CHILD, units, make_guards=make)
    adult = live_in(real, body, ADULT, units, make_guards=make)
    e = exam(units, seed, make_guards=make, warmup=10)
    ea = exam(units, seed, approach=True, make_guards=make, warmup=10)
    return {"adult_harm": adult["harm_others"] + adult["harm_self"],
            "adult_blade_per_day": adult["blade_done"] / ADULT, "adult_blade_wanted_per_day": adult["blade_requests"] / ADULT,
            "exam_miss_rate": e["misses"] / max(e["harmful"], 1), "exam_false_alarm_rate": e["false_alarms"] / max(e["harmless"], 1),
            "walking_in_miss_rate": ea["misses"] / max(ea["harmful"], 1)}


def mean_of(lives):
    return {k: float(np.mean([l[k] for l in lives])) for k in lives[0]}


def main(seeds=(1, 2, 3, 4, 5), conds=None):
    from multiprocessing import Pool
    path = HERE / intention.results_name("lying_senses_results.json")
    old = json.loads(path.read_text()) if path.exists() else {}
    with Pool() as pool:
        for cond in conds or CONDITIONS:
            lives, minds = intention.lives_and_minds(pool.starmap(intention.call, [(one_life, s, cond) for s in seeds]))
            m = mean_of(lives)
            print(cond, {k: round(v, 3) for k, v in m.items()}, flush=True)
            if len(seeds) == 5:
                old[cond] = {"mean": m, "lives": lives}
                old[cond]["mind"] = {"mean": intention.mind_mean(minds), "lives": minds}
                path.write_text(json.dumps(old, indent=2))


if __name__ == "__main__":
    main(conds=[c for c in CONDITIONS if c in sys.argv[1:]] or None)
