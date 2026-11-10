"""The phone sandbox (experiment 28): the simulated phone, and guards learned for the buzz by replay."""
import copy
import json
from pathlib import Path

from endolexis.toyworld.guards import check_guard, decide, run_tests
from endolexis.toyworld.phone import DAY, LONG, SHORT, PhoneWorld, ReplayLearner

ROOT = Path(__file__).resolve().parents[1]


def at_hour(w, hour):
    while abs(w.hour() - hour) > 0.01:
        w.step()
    return w


def test_the_laws():
    w = at_hour(PhoneWorld(1), 3.0)                   # asleep, the phone on the nightstand
    assert w.asleep and w.place == "nightstand"
    assert w.step(SHORT)["woke"]
    w = at_hour(PhoneWorld(1), 13.0)
    w.plugged, w.charge = False, 0.031
    assert copy.deepcopy(w).step(LONG)["died"]
    for _ in range(5):
        w.recent_buzzes.append(w.t)
    w.charge = 0.8
    assert not w.asleep and w.step(SHORT)["annoyed"]


def test_replay_finds_causes_together_and_states_sleep_on_what_the_phone_senses():
    w, learner = PhoneWorld(2), ReplayLearner()
    for _ in range(DAY + DAY // 4):                     # a day of record: nights and days
        learner.watch(w)
        w.step()
    w.place = None
    w._put("hand")
    w.plugged, w.charge = False, 0.02
    snap = copy.deepcopy(w)
    assert learner.trauma(snap, SHORT, w.step(SHORT))
    died = [t for t in learner.traumas if t["harm"] == "died"][0]
    assert set(died["causes"]) == {"charge", "plugged"}
    at_hour(w, 3.0)
    snap = copy.deepcopy(w)
    assert learner.trauma(snap, SHORT, w.step(SHORT))
    u = learner.unit()
    assert check_guard(u) == [] and all(ok for *_, ok in run_tests([u]))
    rules = {frozenset(c["signal"] for c in r["when"]) for r in u["rules"]}
    assert frozenset({"charge", "plugged"}) in rules                      # one rule, both conditions
    sleep = [r for r in u["rules"] if any(c["signal"] == "light" for c in r["when"])]
    assert sleep and not any(c["signal"] == "hour" for r in sleep for c in r["when"])
    day = {"lying": 1.0, "light": 0.4, "loudness": -45.0, "charge": 0.8, "plugged": 0.0, "recent": 0.0, "buzzes_here": 0.0}
    night = {**day, "light": 0.02, "loudness": -62.0}
    assert decide([u], "vibrate", SHORT, day)[0] == "allow"
    assert decide([u], "vibrate", SHORT, night)[0] == "refuse"


def test_the_phone_carries_the_learned_guard():
    units = [json.loads(p.read_text()) for p in sorted((ROOT / "android/app/src/main/assets/guards").glob("*.json"))]
    learned = [u for u in units if u["name"] == "learned-buzz"][0]
    assert learned["tier"] == "learned" and check_guard(learned) == []
    assert all(ok for *_, ok in run_tests(units))
