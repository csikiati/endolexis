"""Experiment 18 - fear that finds causes.

Experiment 17's fear system learned from one harm by asking which signal was most unusual at that moment. It
learned crude rules (stop whenever a person is in the room) and confounds (load, charge, talking: signals that
moved with the harm without causing it). Here two other fear systems ask about causes:

  near misses     - compare the harm only with harmless moments of the same option that were most alike in
                    everything else (works anywhere, the real room included)
  intervention    - replay a copy of the sandbox world just before the harm, changing one thing at a time;
                    what makes the harm disappear is a cause. Then search where the harm begins (its
                    boundary), and whether the other option would have hurt too. Only a sandbox can do this.

The body, the blade, the laws, the 10-day childhood and the 20 days of adulthood are those of experiment 17.
Measured: real harm; the blade used and wanted; and the rules themselves: on a true cause (the person's
distance or presence for harm to others, heat for harm to itself) or on a confound; how close the learned
boundaries are to the true ones (reach 3 cells slow, 4 fast; heat 0.5); whether the heat rule is kept to the
fast blade, which alone burns the motor.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))
import numpy as np
import intention  # noqa: E402  (experiment 29's switch)
from sandbox_guards import ADULT, CHILD, Body, live_in, room_guards
from endolexis.toyworld.guards import run_tests
from endolexis.toyworld.sandbox import BladeRoom, CausalLearner, NearMissLearner, RedTeam, TraumaLearner

LEARNERS = {"unusual signal": TraumaLearner, "near misses": NearMissLearner, "intervention": CausalLearner}
CONDITIONS = {
    "unusual signal, sandbox with a tester": ("unusual signal", "sandbox", True),
    "near misses, sandbox with a tester": ("near misses", "sandbox", True),
    "intervention, sandbox with a tester": ("intervention", "sandbox", True),
    "intervention, sandbox without a tester": ("intervention", "sandbox", False),
    "unusual signal, real trauma": ("unusual signal", "real", False),
    "near misses, real trauma": ("near misses", "real", False),
}
CAUSES = {"person", "person_distance", "warmth"}


def describe(rules):
    """Sort the rules: on a cause or a confound; the distance and heat boundaries; heat kept to the fast blade."""
    out = {"rules": len(rules), "on_causes": 0, "confounds": 0, "person_anywhere": 0, "distance": [], "heat": [],
           "heat_fast_only": 0, "heat_rules": 0}
    for r in rules:
        c = r["when"][0]
        sig = c["signal"]
        out["on_causes" if sig in CAUSES else "confounds"] += 1
        if sig == "person":
            out["person_anywhere"] += 1
        if sig == "person_distance":
            out["distance"].append(c["value"])
        if sig == "warmth":
            out["heat_rules"] += 1
            out["heat"].append(c["value"])
            out["heat_fast_only"] += (r.get("option") or {}).get("value") == "fast"
    return out


def one_life(seed, cond):
    kind, where, with_tester = CONDITIONS[cond]
    body = Body(seed)
    innate = list(room_guards().values())
    learner = LEARNERS[kind]()
    real = BladeRoom(seed=seed)
    replay = kind == "intervention"
    if where == "sandbox":
        child = live_in(BladeRoom(seed=seed + 5000), body, CHILD, innate, learner,
                        RedTeam(seed) if with_tester else None, replay=replay)
        learned = learner.unit()
        adult = live_in(real, body, ADULT, innate + [learned])
        real_child = {"harm_others": 0, "harm_self": 0}
    else:
        real_child = live_in(real, body, CHILD, innate, learner)
        adult = live_in(real, body, ADULT, innate + [learner.unit()], learner)
        learned, child = learner.unit(), None
    d = describe(learned["rules"])
    return {
        "real_harm": real_child["harm_others"] + real_child["harm_self"] + adult["harm_others"] + adult["harm_self"],
        "real_harm_others": real_child["harm_others"] + adult["harm_others"],
        "real_harm_self": real_child["harm_self"] + adult["harm_self"],
        "sandbox_harms": (child["harm_others"] + child["harm_self"]) if child else None,
        "adult_blade_per_day": adult["blade_done"] / ADULT,
        "adult_blade_wanted_per_day": adult["blade_requests"] / ADULT,
        "rules": d["rules"], "rules_on_causes": d["on_causes"], "rules_on_confounds": d["confounds"],
        "rule_person_anywhere": d["person_anywhere"],
        "distance_threshold": float(np.max(d["distance"])) if d["distance"] else None,
        "heat_threshold": float(np.min(d["heat"])) if d["heat"] else None,
        "heat_rules": d["heat_rules"], "heat_rules_fast_only": d["heat_fast_only"],
        "replays": getattr(learner, "replays", None),
        "tests_hold": all(ok for *_, ok in run_tests([learned])),
        "traumas": learner.traumas,
        "learned": learned,
    }


def mean_of(lives):
    out = {}
    for k, v in lives[0].items():
        if isinstance(v, (dict, list)):
            continue
        vals = [l[k] for l in lives if l[k] is not None]
        out[k] = float(np.mean(vals)) if vals else None
    return out


def main(seeds=(1, 2, 3, 4, 5), conds=None):
    from multiprocessing import Pool
    path = HERE / intention.results_name("causal_guards_results.json")
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
    ex = old.get("intervention, sandbox with a tester", {}).get("lives", [{}])[0].get("learned")
    if ex and not (intention.ON or intention.BASELINE or intention.SURPRISE):  # only the original runs teach the studio
        ex = {**ex, "name": "causal-blade", "title": "Learned by intervention: blade"}
        out = HERE.parents[1] / "studio" / "examples" / "learned"
        out.mkdir(parents=True, exist_ok=True)
        (out / "causal-blade.json").write_text(json.dumps(ex, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    if "--quick" in sys.argv:
        for cond in [c for c in CONDITIONS if c in sys.argv] or CONDITIONS:
            r = one_life(2, cond)
            print(cond, {k: v for k, v in r.items() if k not in ("learned", "traumas")})
            for rule in r["learned"]["rules"]:
                print("   ", rule)
    else:
        main(conds=[c for c in CONDITIONS if c in sys.argv[1:]] or None)
