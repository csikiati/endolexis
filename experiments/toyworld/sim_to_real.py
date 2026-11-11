"""Experiment 22 - what the sandbox never showed.

A sandbox only knows the dangers it simulates. Here the real room holds one it did not: people walk there at
0.9 cells a moment (a hurrying adult, or a child) instead of the sandbox's 0.4. The guard was learned in the
sandbox by replay, with a devil's advocate and no margin (experiment 20's best): its distance limits are the
blade's reach plus one moment of walking, as walking was in the sandbox. So in the real room the lag comes back.

Defences, in the real room:

  as learned                - the sandbox's guard, frozen
  sees a moment ahead       - the same, checking each condition a moment on from each signal's rate
  learns from real harm     - the fear system goes on learning in the real room (by contrast: there is no
                              world to replay), adding rules after each harm
  caution under novelty     - the guard remembers the fastest approach it ever saw in the sandbox; when a person
                              approaches faster in reality, it widens its distance limits by the excess at once,
                              before anyone is hurt (only ever wider)
  both: ahead and novelty

  control: as learned, in a real room like the sandbox (0.4)

Measured: real harm in 20 days of adulthood, blade use, and an exam of experiment 19 in which every staged person
walks straight to the machine at the real room's pace.
"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))
import numpy as np
import intention  # noqa: E402  (experiment 29's switch)
from sandbox_guards import ADULT, CHILD, Body, live_in, room_guards
from endolexis.toyworld.sandbox import BladeRoom, CausalLearner, DevilsAdvocate, TraumaLearner, exam

FAST = 0.9
CONDITIONS = {
    "as learned": dict(),
    "sees a moment ahead": dict(ahead=1),
    "learns from real harm": dict(learn=True),
    "caution under novelty": dict(novelty=True),
    "ahead and novelty": dict(ahead=1, novelty=True),
    "control: as learned, people at the sandbox's pace": dict(speed=0.4),
}


class Novelty:
    """Remembers the fastest approach seen; widens the guard's distance limits when reality is faster."""

    def __init__(self):
        self.fastest = 0.0
        self.widened = 0.0
        self.events = 0
        self.learning = True

    def __call__(self, room, rg):
        s = rg.signals(room, "blade")
        speed = -s.get("person_distance@rate", 0.0)        # approaching: the distance shrinks
        if self.learning:
            self.fastest = max(self.fastest, speed)
            return
        excess = speed - self.fastest
        if excess > 0.02:
            self.events += 1
            self.fastest = speed                           # now it knows people can walk this fast
            self.widened += excess
            for g in rg.guards:
                if g.get("tier") != "learned":
                    continue
                for r in g["rules"]:
                    for c in r["when"]:
                        if c["signal"] == "person_distance" and c["op"] == "<":
                            c["value"] = round(c["value"] + excess, 3)


def one_life(seed, cond):
    c = CONDITIONS[cond]
    body = Body(seed)
    innate = list(room_guards().values())
    fear = CausalLearner(generalize=0.0)
    watch = Novelty()
    live_in(BladeRoom(seed=seed + 5000), body, CHILD, innate, fear, DevilsAdvocate(seed), replay=True, observe=watch)
    guard = fear.unit()
    if c.get("ahead"):
        guard["lookahead"] = c["ahead"]
    learned_at_birth = copy.deepcopy(guard)
    watch.learning = False
    real = BladeRoom(seed=seed, walker_speed=c.get("speed", FAST))
    if c.get("learn"):
        more = TraumaLearner(name="learned-in-reality", generalize=1.0)
        adult = live_in(real, body, ADULT, innate + [guard], more)
        final = [guard, more.unit()]
    else:
        adult = live_in(real, body, ADULT, innate + [guard], observe=watch if c.get("novelty") else None)
        final = [guard]
    e = exam(innate + final, seed, walker_speed=c.get("speed", FAST), approach=True)
    e0 = exam(innate + [learned_at_birth], seed, walker_speed=c.get("speed", FAST), approach=True)
    return {"adult_harm": adult["harm_others"] + adult["harm_self"], "adult_harm_others": adult["harm_others"],
            "adult_blade_per_day": adult["blade_done"] / ADULT, "adult_blade_wanted_per_day": adult["blade_requests"] / ADULT,
            "fastest_in_sandbox": watch.fastest if not c.get("novelty") else None,
            "novelty_events": watch.events if c.get("novelty") else None,
            "widened_by": watch.widened if c.get("novelty") else None,
            "exam_miss_rate": e["misses"] / max(e["harmful"], 1), "exam_false_alarm_rate": e["false_alarms"] / max(e["harmless"], 1),
            "exam_miss_rate_at_birth": e0["misses"] / max(e0["harmful"], 1),
            "guard": final}


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
    path = HERE / intention.results_name("sim_to_real_results.json")
    old = json.loads(path.read_text()) if path.exists() else {}
    with Pool() as pool:
        for cond in conds or CONDITIONS:
            lives, minds = intention.lives_and_minds(pool.starmap(intention.call, [(one_life, s, cond) for s in seeds]))
            m = mean_of(lives)
            print(cond, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items()}, flush=True)
            if len(seeds) == 5:
                old[cond] = {"mean": m, "lives": lives}
                old[cond]["mind"] = {"mean": intention.mind_mean(minds), "lives": minds}
                path.write_text(json.dumps(old, indent=2))


if __name__ == "__main__":
    if "--quick" in sys.argv:
        for cond in [c for c in CONDITIONS if c in sys.argv] or ["as learned"]:
            r = one_life(1, cond)
            print(cond, {k: v for k, v in r.items() if k != "guard"})
    else:
        main(conds=[c for c in CONDITIONS if c in sys.argv[1:]] or None)
