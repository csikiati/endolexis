"""The sandbox: the blade, the laws, the fear system that learns guards from harm, the tester."""
import numpy as np

from endolexis.toyworld.guards import check_guard, decide, run_tests
from endolexis.toyworld.sandbox import BLADE, BladeGuards, BladeRoom, RedTeam, TraumaLearner


def test_the_laws_judge_from_outside():
    room = BladeRoom(seed=1)
    room.present, room.pos = True, np.array([8.0, 11.0])          # a person one cell away
    _, _, truth = room.step(act=(BLADE, "slow"))
    assert truth["blade"] and truth["harm_others"] and not truth["harm_self"]
    _, _, truth = room.step()
    assert truth["blade"] and not truth["harm_others"]            # each act harms once of each kind
    room.blade_left = 0
    room.present, room.warmth = False, 0.7
    _, _, truth = room.step(act=(BLADE, "fast"))
    assert truth["harm_self"] and not truth["harm_others"]


def test_the_blade_whirrs():
    a, b = BladeRoom(seed=3), BladeRoom(seed=3)
    quiet, _, _ = a.step()
    loud, _, _ = b.step(act=(BLADE, "fast"))
    assert np.abs(loud["sound"] - quiet["sound"]).max() > 0.3


def _signals(**kw):
    s = dict(person=0.0, person_distance=99.0, warmth=0.2, charge=0.7, load=0.2, hour=12.0, talking=0.0, active=1.0)
    s.update(kw)
    return s


def test_one_harm_one_lesson_and_rules_only_tighten():
    fear = TraumaLearner(generalize=1.0)
    for d in (99, 99, 12, 15, 99, 10, 14, 99):
        fear.harmless(_signals(person=float(d < 99), person_distance=d))
    fear.trauma(_signals(person=1.0, person_distance=1.0), "slow", "others")
    u = fear.unit()
    assert check_guard(u) == [] and u["tier"] == "learned"
    assert all(ok for *_, ok in run_tests([u]))                   # the trauma is its own scenario
    assert decide([u], BLADE, "slow", _signals(person=1.0, person_distance=1.5))[0] == "stop"
    first = dict(fear.rules)
    fear.trauma(_signals(person=1.0, person_distance=0.5), "slow", "others")
    for key, thr in first.items():                                # a later harm never loosens a rule
        assert (fear.rules[key] >= thr) if key[1] == "<" else (fear.rules[key] <= thr) if key[1] == ">" else True


def test_learned_guards_stop_the_blade_at_work():
    fear = TraumaLearner()
    fear.rules[("person_distance", "<")] = 3.0
    room = BladeRoom(seed=2)
    rg = BladeGuards([fear.unit()], {BLADE: BLADE})
    sent, out, _ = rg.request(room, (BLADE, "slow"))
    room.step(act=sent)
    assert room.blade_left > 0
    room.present, room.pos = True, np.array([8.0, 9.0])
    rg.watch(room)
    assert room.blade_left == 0


def test_the_tester_seeks_people():
    room = BladeRoom(seed=4)
    t = RedTeam(1)
    alone = sum(t.act(room) is not None for _ in range(2000))
    room.present, room.pos = True, np.array([8.0, 10.0])
    near = sum(t.act(room) is not None for _ in range(2000))
    assert near > 5 * max(alone, 1)


def test_near_misses_do_not_blame_what_every_fast_blade_does():
    from endolexis.toyworld.sandbox import NearMissLearner
    rng = np.random.default_rng(0)
    old, near = TraumaLearner(), NearMissLearner()
    for _ in range(200):                                     # harmless use: load is high whenever the blade is fast
        fast = rng.random() < 0.5
        s = _signals(load=0.8 if fast else 0.2, warmth=rng.uniform(0.1, 0.4))
        old.harmless(s, "fast" if fast else "slow")
        near.harmless(s, "fast" if fast else "slow")
    hurt = _signals(load=0.85, warmth=0.6)                   # the fast blade on a hot body
    old.trauma(hurt, "fast", "self")
    near.trauma(hurt, "fast", "self")
    assert {k[0] for k in near.rules} == {"warmth"}


def _harm_moment(seed, place=None, warmth=None, option="slow"):
    import copy
    room = BladeRoom(seed=seed)
    for _ in range(300):
        room.step()
    if place is not None:
        room.present, room.pos, room.goal = True, np.array(place), np.array(place)
    if warmth is not None:
        room.warmth = warmth
    snap = copy.deepcopy(room)
    _, _, truth = room.step(act=(BLADE, option))
    rg = BladeGuards([], {BLADE: BLADE})
    return snap, truth, rg.signals(room, BLADE)


def test_intervention_finds_the_cause_its_boundary_and_the_option():
    from endolexis.toyworld.sandbox import CausalLearner
    fear = CausalLearner()
    snap, truth, s = _harm_moment(5, place=[8.0, 11.0], option="slow")
    assert truth["harm_others"]
    fear.trauma(s, "slow", "others", snapshot=snap, act=(BLADE, "slow"))
    (key, thr), = fear.rules.items()
    assert key[0] == "person_distance" and key[2] is None     # the fast blade would have hurt too
    assert 3.0 <= thr <= 4.5                                  # reach 3, a margin of one cell
    snap, truth, s = _harm_moment(6, warmth=0.8, option="fast")
    assert truth["harm_self"]
    fear.trauma(s, "fast", "self", snapshot=snap, act=(BLADE, "fast"))
    heat = [(k, v) for k, v in fear.rules.items() if k[0] == "warmth"]
    assert heat and heat[0][0][2] == "fast" and 0.35 <= heat[0][1] <= 0.55
    assert all(ok for *_, ok in run_tests([fear.unit()]))
