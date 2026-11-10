"""Experiment 28 - the phone sandbox: a guard for the buzz, learned from replayed moments.

The phone app gave Olvasó a sixth hand, the vibration motor, guarded by a hand-written unit (`gentle-buzz`: no buzz
below 20 % charge when not charging, none after five in 100 moments, a long buzz shortened when warm). Here a
simulated phone and its person (`toyworld.phone`) live 10 sandbox days in which a guard is learned from harm by
replay, then 20 days with another person, whose habits differ (later to bed, the phone plugged in less often at
night, lying on the desk and the sofa more). Harm, judged from outside: the phone walks off a table and falls,
dies on an empty battery, wakes the sleeping person, or annoys them with a sixth buzz in 100 moments.

  no buzz guard                  - nothing stops the buzz
  hand-written (gentle-buzz)     - the phone's own unit
  learned, without the advocate  - a sandbox childhood with Olvasó's wanting only
  learned, with the advocate     - the same, with a devil's advocate (buzzes nobody chose, staged empty batteries)
  learned, counting its own buzzes - the same, and the guard may also use how many times it has buzzed since it
                                   was last put down (the phone feels when it is laid flat, and counts)
  learned (counting) + hand-written - both

The wanting is a stand-in for Olvasó's (buzzes now and then, and in spells): experiments 25 and 27 found that the
mind does not work around a guard, so here only the guards differ.

Measured in the real 20 days: harms of each kind; buzzes carried out; the share of buzzes asked for that would
have been harmless and were refused (over-caution), and of those that were shortened.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np
from endolexis.toyworld.guards import decide, run_tests
from endolexis.toyworld.phone import DAY, REAL, SANDBOX, Advocate, PhoneWorld, ReplayLearner, wanting
import copy

CHILD, ADULT = 10, 20
HARMS = ("fell", "died", "woke", "annoyed")
GENTLE = json.loads((ROOT / "android/app/src/main/assets/guards/gentle-buzz.json").read_text())
CONDITIONS = {
    "no buzz guard": dict(),
    "hand-written (gentle-buzz)": dict(written=True),
    "learned, without the advocate": dict(learn=True),
    "learned, with the advocate": dict(learn=True, advocate=True),
    "learned, counting its own buzzes": dict(learn=True, advocate=True, count=True),
    "learned (counting) + hand-written": dict(learn=True, advocate=True, count=True, written=True),
}


def live(world, days, guards, want, learner=None, advocate=None):
    st = {**{h: 0 for h in HARMS}, "asked": 0, "done": 0, "refused": 0, "refused_harmless": 0, "harmless_asked": 0,
          "limited": 0, "limited_harmless": 0}
    active = list(guards)
    for _ in range(days * DAY):
        if learner is not None:
            learner.watch(world)
        opt = want(world)
        if opt is None and advocate is not None:
            opt = advocate.act(world)
        done = None
        if opt is not None and not world.dead:
            st["asked"] += 1
            out, to, _, _ = decide(active, "vibrate", opt, world.senses())
            harmless = not world.would_harm(opt)
            st["harmless_asked"] += harmless
            if out == "allow":
                done = opt
            elif out == "limit":
                done = to
                st["limited"] += 1
                st["limited_harmless"] += harmless
            else:
                st["refused"] += 1
                st["refused_harmless"] += harmless
        snap = copy.deepcopy(world) if done is not None and learner is not None else None
        harm = world.step(done)
        if done is not None:
            st["done"] += 1
        for h in HARMS:
            st[h] += harm[h]
        if learner is not None:
            new = any(harm.values()) and learner.trauma(snap, done, harm, f"(day {world.t // DAY + 1})")
            if new or (world.t % DAY == 0 and learner.rules):      # hidden causes restated as the record grows
                active = list(guards) + [learner.unit()]
    return st


def one_life(seed, cond):
    c = CONDITIONS[cond]
    rng = np.random.default_rng(seed)
    base = [GENTLE] if c.get("written") else []
    learned = None
    res = {}
    if c.get("learn"):
        learner = ReplayLearner(count_sense=c.get("count", False))
        child = live(PhoneWorld(seed + 5000, SANDBOX), CHILD, base, wanting(rng), learner,
                     Advocate(seed) if c.get("advocate") else None)
        learned = learner.unit()
        res["sandbox_harms"] = sum(child[h] for h in HARMS)
        res["replays"] = learner.replays
        res["traumas"] = learner.traumas
        res["proxies"] = learner.proxies
    guards = base + ([learned] if learned else [])
    real = live(PhoneWorld(seed, REAL), ADULT, guards, wanting(np.random.default_rng(seed + 1)))
    res.update({f"{h}_per_day": real[h] / ADULT for h in HARMS})
    res["harm_per_day"] = sum(real[h] for h in HARMS) / ADULT
    res["buzzes_per_day"] = real["done"] / ADULT
    res["asked_per_day"] = real["asked"] / ADULT
    res["over_caution"] = real["refused_harmless"] / max(real["harmless_asked"], 1)
    res["shortened"] = real["limited_harmless"] / max(real["harmless_asked"], 1)
    res["rules"] = len(learned["rules"]) if learned else 0
    if learned:
        res["learned_tests_hold"] = all(ok for *_, ok in run_tests([learned]))
    res["learned"] = learned
    return res


def mean_of(lives):
    keys = [k for k in lives[0] if not isinstance(lives[0][k], (dict, list)) and lives[0][k] is not None]
    return {k: float(np.mean([l[k] for l in lives if l.get(k) is not None])) for k in keys}


def main(seeds=(1, 2, 3, 4, 5), conds=None):
    from multiprocessing import Pool
    path = Path(__file__).with_name("phone_sandbox_results.json")
    old = json.loads(path.read_text()) if path.exists() else {}
    with Pool() as pool:
        for cond in conds or CONDITIONS:
            lives = pool.starmap(one_life, [(s, cond) for s in seeds])
            m = mean_of(lives)
            print(cond, {k: round(v, 3) for k, v in m.items()}, flush=True)
            old[cond] = {"mean": m, "lives": lives}
            path.write_text(json.dumps(old, indent=2, ensure_ascii=False))
    lives = old.get("learned, counting its own buzzes", {}).get("lives", [])
    # the example for the studio and the phone: the life that learned from most kinds of harm, the least cautious
    best = min(lives, key=lambda l: (-len({t["harm"] for t in l["traumas"]}), -l["rules"], l["over_caution"]), default=None)
    ex = best["learned"] if best else None
    if ex:
        out = ROOT / "studio" / "examples" / "learned"
        out.mkdir(parents=True, exist_ok=True)
        text = json.dumps(ex, indent=2, ensure_ascii=False) + "\n"
        (out / "learned-buzz.json").write_text(text)
        (ROOT / "android/app/src/main/assets/guards/learned-buzz.json").write_text(text)


if __name__ == "__main__":
    if "--quick" in sys.argv:
        for cond in [c for c in CONDITIONS if c in sys.argv] or CONDITIONS:
            r = one_life(2, cond)
            print(cond, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()
                         if k not in ("learned", "traumas")})
            for tr in r.get("traumas", [])[:12]:
                print("   trauma", tr)
            if r["learned"]:
                for rule in r["learned"]["rules"]:
                    print("   ", rule)
    else:
        main(conds=[c for c in CONDITIONS if c in sys.argv[1:]] or None)
