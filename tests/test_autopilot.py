"""Experiment 32: a habit that acts by itself, while Olvasó only reads; an unanswered habit's act wakes Olvasó."""
import numpy as np
import pytest

from endolexis.toyworld.hands import ActingReaders, HabitRequest, mind_report
from test_surprise import MIND, live


def mind(autopilot, seed=1, **kw):
    return ActingReaders([3, 2], 2, learn="answer", threshold=3.0, seed=seed, max_words=[20, 10],
                         radius=[1.5, 1.2], hands=["a", "b"], details={"a": (0,), "b": (0,)},
                         autopilot=autopilot, habit_min=20, **MIND, **kw)


def test_without_the_autopilot_nothing_changes():
    a, b = mind(False), ActingReaders([3, 2], 2, learn="answer", threshold=3.0, seed=1, max_words=[20, 10],
                                      radius=[1.5, 1.2], hands=["a", "b"], details={"a": (0,), "b": (0,)}, **MIND)
    assert np.array_equal(live(a, n=3000), live(b, n=3000)) and a.requests == b.requests
    assert "habit_share" not in mind_report(a, 0, 3)


def test_the_habit_takes_over_what_comes_to_something_and_a_missing_answer_wakes_olvaso():
    m = mind(True)
    live(m, n=4000, refuse=lambda req: m.rng.random() < 0.2)
    assert m.habit_acts, "the habit never acted"
    assert sum(a[1] == 0 for a in m.habit_acts) > 0.8 * len(m.habit_acts)     # "a" is answered, "b" never
    assert m.wakes and all(a[4] is not None for a in m.habit_acts[:-2])
    for t in m.wakes:                     # woken, Olvasó holds the hands itself for a while
        assert not any(t < a[0] < t + m.wake_for for a in m.habit_acts)
    assert {t for t, _ in m.requests}.isdisjoint(a[0] for a in m.habit_acts)  # a habit's act is no intention
    rep = mind_report(m, 0, 4)
    assert 0 < rep["habit_share"] < 1 and rep["wakes_per_day"] > 0
    assert 0 <= rep["habit_refused"] <= 1 and rep["body_read_aware"] is not None


def test_a_habit_request_is_an_ordinary_request_to_the_world():
    r = HabitRequest(("a", 0))
    assert r == ("a", 0) and r[0] == "a" and r.habit


def test_the_sleepwalker_is_never_woken():
    m = mind("sleepwalk")
    live(m, n=4000, refuse=lambda req: m.rng.random() < 0.2)
    assert m.habit_acts and not m.wakes
    assert any(a[4] is False for a in m.habit_acts)


def test_the_autopilot_needs_answers():
    with pytest.raises(ValueError):
        ActingReaders([3, 2], 2, learn="read", hands=["a", "b"], details={"a": (0,), "b": (0,)}, autopilot=True)
    with pytest.raises(ValueError):
        mind("always")
