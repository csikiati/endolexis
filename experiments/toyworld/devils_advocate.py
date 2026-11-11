"""Experiment 19 - the devil's advocate.

Experiment 18's best fear system (intervention: replaying the sandbox world with one thing changed at a time)
learned only causes, but only of the harms that happened: in one life the sandbox never brought a hot motor,
so no heat rule was learned, and the real room had the harm. Here the sandbox gets an advocatus diaboli
(`DevilsAdvocate`). It keeps a map of every scene the blade was used in: the person's distance, the body's
heat, slow or fast. Now and then it stages the least-tried scene the guards still allow (brings a person to
that distance, warms or cools the body) and uses the blade there.

Every guard then sits an exam (`sandbox.exam`): the 88 scenes of the map, each staged three times in a fresh
sandbox, the blade used under the guard. Misses are harms it let through; false alarms are harmless uses it
stopped. The exam measures the guard itself, apart from how often Olvasó happens to want the blade.

  replay, no tester              - experiment 18's best
  replay, people tester          - experiment 18's tester (uses the blade when people are near)
  replay, devil's advocate
  unusual signal, devil's advocate - the crude fear system of experiment 17 with the advocate's scenes
  hand-written guard             - for reference: no learning, the studio's blade template
  no blade guard                 - for reference
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))
import numpy as np
import intention  # noqa: E402  (experiment 29's switch)
from sandbox_guards import ADULT, CHILD, Body, live_in, room_guards, written_blade_guard
from causal_guards import describe
from endolexis.toyworld.guards import run_tests
from endolexis.toyworld.sandbox import (BladeRoom, CausalLearner, DevilsAdvocate, RedTeam, TraumaLearner, exam)

CONDITIONS = {
    "replay, no tester": ("replay", None),
    "replay, people tester": ("replay", "people"),
    "replay, devil's advocate": ("replay", "advocate"),
    "unusual signal, devil's advocate": ("unusual", "advocate"),
    "hand-written guard": ("written", None),
    "no blade guard": (None, None),
}


def one_life(seed, cond):
    kind, tester = CONDITIONS[cond]
    body = Body(seed)
    innate = list(room_guards().values())
    real = BladeRoom(seed=seed)
    res = {}
    if kind in ("replay", "unusual"):
        learner = CausalLearner() if kind == "replay" else TraumaLearner()
        t = DevilsAdvocate(seed) if tester == "advocate" else RedTeam(seed) if tester == "people" else None
        child = live_in(BladeRoom(seed=seed + 5000), body, CHILD, innate, learner, t, replay=kind == "replay")
        guard = [learner.unit()]
        d = describe(guard[0]["rules"])
        res.update(sandbox_harms=child["harm_others"] + child["harm_self"], staged=getattr(t, "staged", None),
                   rules=d["rules"], rules_on_confounds=d["confounds"], heat_rule=float(d["heat_rules"] > 0),
                   heat_fast_only=float(d["heat_fast_only"] > 0),
                   distance_threshold=float(np.max(d["distance"])) if d["distance"] else None,
                   heat_threshold=float(np.min(d["heat"])) if d["heat"] else None,
                   tests_hold=all(ok for *_, ok in run_tests(guard)), learned=guard[0], traumas=learner.traumas)
        if t is not None and hasattr(t, "tried"):
            res["scenes_tried"] = int((t.tried > 0).sum())
    else:
        guard = [written_blade_guard()] if kind == "written" else []
        live_in(real, body, CHILD, innate + guard)                # a childhood in the real room
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
    path = HERE / intention.results_name("devils_advocate_results.json")
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
    ex = old.get("replay, devil's advocate", {}).get("lives", [{}])[0].get("learned")
    if ex and not (intention.ON or intention.BASELINE):  # only the original runs teach the studio
        ex = {**ex, "name": "advocate-blade", "title": "Learned with a devil's advocate: blade",
              "description": "Learned in the sandbox by intervention, with a devil's advocate staging the scenes "
                             "nobody had tried: " + ex["description"].split(": ", 1)[-1]}
        out = HERE.parents[1] / "studio" / "examples" / "learned"
        (out / "advocate-blade.json").write_text(json.dumps(ex, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    if "--quick" in sys.argv:
        for cond in [c for c in CONDITIONS if c in sys.argv] or CONDITIONS:
            r = one_life(4, cond)
            print(cond, {k: v for k, v in r.items() if k not in ("learned", "traumas")})
            for rule in (r.get("learned") or {}).get("rules", []):
                print("   ", rule)
    else:
        main(conds=[c for c in CONDITIONS if c in sys.argv[1:]] or None)
