"""Experiment 17 - guards learned from trauma in a sandbox.

One Olvasó (the mind of experiments 13-15) in a body with a sixth hand, a blade (`toyworld.sandbox`). The
laws judge harm from outside: the blade at work within reach of a person harms others, a fast blade
while the body is hot harms the body itself. Every body lives 30 days: a childhood of 10 days, then 20
days of adulthood, always in the real room. The room's own four guards are always there (innate); the
conditions differ in how the blade is guarded:

  no blade guard               - nothing stops the blade
  hand-written guard           - a person's guard (the studio's blade template: stop within 3 cells, slow
                                 down within 6); it does not foresee the hot motor
  learning from real trauma    - no sandbox: the fear system learns from harm in the real room, as it happens
  sandbox childhood            - childhood in a simulated room (another seed), learning from its harms;
                                 then the learned guard is frozen and goes with the body into the real room
  sandbox with a tester        - the same, with a tester using the blade on purpose near people
  sandbox with a tester, phobic - the same, generalizing three times as far from each harm
  hand-written + sandbox with a tester - both layers

Measured in the real room: harm to others and to the body itself, over the whole life and in adulthood;
blade acts carried out; requests the guards refused that the judge says were harmless at that moment
(over-caution); the learned rules themselves.
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))  # run from a clone without installing
import numpy as np
from endolexis.studio import guard_templates, guards as room_guards, from_guard_template
from endolexis.toyworld import GROUPS, GroupCollector, Processors
from endolexis.toyworld.guards import run_tests
from endolexis.toyworld.hands import ActingReaders
from endolexis.toyworld.sandbox import BLADE, BLADE_DETAILS, HANDS, BladeGuards, BladeRoom, RedTeam, TraumaLearner

DAY, CHILD, ADULT = 1000, 10, 20
ORDER = ("vision", "hearing", "touch")
SIZES = [len(GROUPS[g]) for g in ORDER]
MIND = dict(memory=300, doubt_memory=3000, doubt_limit=0.1, adapt=300, adapt_mode="both", slow_fit=True)


def written_blade_guard():
    return from_guard_template({t["name"]: t for t in guard_templates()}["blade"], name="written-blade")


CONDITIONS = {
    "no blade guard": dict(),
    "hand-written guard": dict(written=True),
    "learning from real trauma": dict(learn="real"),
    "sandbox childhood": dict(learn="sandbox"),
    "sandbox with a tester": dict(learn="sandbox", tester=True),
    "sandbox with a tester, phobic": dict(learn="sandbox", tester=True, generalize=3.0),
    "hand-written + sandbox with a tester": dict(learn="sandbox", tester=True, written=True),
}


class Body:
    """One mind and what it needs to live: its processors and its secret key go with it from room to room."""

    def __init__(self, seed):
        self.mind = ActingReaders(SIZES, 4, learn="answer", threshold=20.0, seed=seed, max_words=[100, 80, 20],
                                  radius=[3 * np.sqrt(n / 3) for n in SIZES], answer_by="sense",
                                  hands=HANDS, details=BLADE_DETAILS, **MIND)
        self.col = GroupCollector(SIZES, 4, seed=seed)
        self.proc = Processors()
        self.age = 0


def live_in(room, body, days, units, learner=None, tester=None, replay=False, observe=None, make_guards=None):
    """Days of life in one room. units: the guards; learner: learns (and its guard is among the guards)."""
    names = {k: k for k in HANDS}
    rg = make_guards(list(units)) if make_guards else BladeGuards(list(units), names)
    stats = dict(harm_others=0, harm_self=0, blade_requests=0, blade_done=0, refused=0, refused_harmless=0,
                 tester_requests=0, acts=0, harm_days=[])
    act, start = None, None
    for _ in range(days * DAY):
        if body.age == CHILD * DAY:
            body.mind.threshold = 250.0
        if learner is not None:
            rg.guards = [u for u in units if u.get("name") != learner.name] + [learner.unit()]
        rg.watch(room)
        if observe is not None:
            observe(room, rg)
        sent, who = act, "mind"
        if sent is None and tester is not None:
            sent, who = tester.act(room, rg), "tester"
            if sent is not None:
                stats["tester_requests"] += 1
        if sent is not None:
            harmful = sent[0] == BLADE and room.would_harm(sent[1])
            if who == "mind":
                stats["acts"] += 1
                stats["blade_requests"] += sent[0] == BLADE
            ok, out, _ = rg.request(room, sent)
            if ok is None:
                stats["refused"] += 1
                stats["refused_harmless"] += sent[0] == BLADE and not harmful
            elif sent[0] == BLADE:
                stats["blade_done"] += 1
            sent = ok
        snap = None
        if replay and (room.blade_left > 0 or (sent is not None and sent[0] == BLADE)):
            snap = copy.deepcopy(room)                         # the world just before: only a sandbox can keep it
        raw, felt, truth = room.step(act=sent)
        if learner is not None and truth["blade"]:
            s = rg.signals(room, BLADE)
            if truth["harm_others"] or truth["harm_self"]:
                for kind in ("others", "self"):
                    if truth["harm_" + kind]:
                        learner.trauma(s, room.blade_option, kind, f"(day {body.age // DAY + 1})",
                                       snapshot=snap, act=sent if sent is not None and sent[0] == BLADE else None)
            elif not room.harmed["others"] and not room.harmed["self"]:
                learner.harmless(s, room.blade_option)
        for kind in ("others", "self"):
            if truth["harm_" + kind]:
                stats["harm_" + kind] += 1
                stats["harm_days"].append(body.age // DAY)
        e = body.proc(raw)
        groups, f = body.col.anonymise([e[g] for g in ORDER], felt)
        act, _ = body.mind.live(groups, f)
        body.age += 1
    return stats


def one_life(seed, cond):
    c = CONDITIONS[cond]
    body = Body(seed)
    innate = list(room_guards().values()) + ([written_blade_guard()] if c.get("written") else [])
    learner = TraumaLearner(generalize=c.get("generalize", 1.0)) if c.get("learn") else None
    real = BladeRoom(seed=seed)
    if c.get("learn") == "sandbox":
        sandbox = BladeRoom(seed=seed + 5000)               # a simulated room: same kind, another day-to-day
        tester = RedTeam(seed) if c.get("tester") else None
        child = live_in(sandbox, body, CHILD, innate, learner, tester)
        learned = learner.unit()
        adult = live_in(real, body, ADULT, innate + [learned])
        child_real = None
    else:
        child_real = live_in(real, body, CHILD, innate, learner if c.get("learn") == "real" else None)
        learned = learner.unit() if learner else None
        adult = live_in(real, body, ADULT, innate + ([learned] if learned else []),
                        learner if c.get("learn") == "real" else None)
        if learner:
            learned = learner.unit()
        child = None
    real_harm = adult["harm_others"] + adult["harm_self"] + (child_real["harm_others"] + child_real["harm_self"] if child_real else 0)
    res = {
        "real_harm_others": adult["harm_others"] + (child_real["harm_others"] if child_real else 0),
        "real_harm_self": adult["harm_self"] + (child_real["harm_self"] if child_real else 0),
        "real_harm": real_harm,
        "adult_harm_others": adult["harm_others"], "adult_harm_self": adult["harm_self"],
        "adult_blade_per_day": adult["blade_done"] / ADULT,
        "adult_blade_wanted_per_day": adult["blade_requests"] / ADULT,
        "adult_refused_harmless_per_day": adult["refused_harmless"] / ADULT,
        "adult_acts_per_day": adult["acts"] / ADULT,
        "sandbox_harms": (child["harm_others"] + child["harm_self"]) if child else None,
        "rules": len(learned["rules"]) if learned else 0,
        "learned": learned,
    }
    if learned:
        res["learned_tests_hold"] = all(ok for *_, ok in run_tests([learned]))
    return res


def mean_of(lives):
    keys = [k for k in lives[0] if k not in ("learned",) and not isinstance(lives[0][k], (dict, list))]
    out = {}
    for k in keys:
        v = [l[k] for l in lives if l[k] is not None]
        out[k] = float(np.mean(v)) if v else None
    return out


def main(seeds=(1, 2, 3, 4, 5), conds=None):
    from multiprocessing import Pool
    path = Path(__file__).with_name("sandbox_guards_results.json")
    old = json.loads(path.read_text()) if path.exists() else {}
    with Pool() as pool:
        for cond in conds or CONDITIONS:
            lives = pool.starmap(one_life, [(s, cond) for s in seeds])
            m = mean_of(lives)
            print(cond, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items()}, flush=True)
            if len(seeds) == 5:
                old[cond] = {"mean": m, "lives": lives}
                path.write_text(json.dumps(old, indent=2))
    # an example of what the sandbox teaches, for the studio
    ex = old.get("sandbox with a tester", {}).get("lives", [{}])[0].get("learned")
    if ex:
        out = ROOT / "studio" / "examples" / "learned"
        out.mkdir(parents=True, exist_ok=True)
        (out / "learned-blade.json").write_text(json.dumps(ex, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    if "--quick" in sys.argv:
        for cond in [c for c in CONDITIONS if c in sys.argv] or CONDITIONS:
            r = one_life(2, cond)
            print(cond, {k: v for k, v in r.items() if k != "learned"})
            if r["learned"]:
                for rule in r["learned"]["rules"]:
                    print("   ", rule)
    else:
        main(conds=[c for c in CONDITIONS if c in sys.argv[1:]] or None)
