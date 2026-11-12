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


# --- experiment 33: the habit teaches Olvasó ------------------------------------------------------------------------
def test_without_teaching_the_autopilot_is_unchanged():
    a, b = mind(True), mind(True, habit_teaches=False)
    live(a, n=3000), live(b, n=3000)
    assert a.requests == b.requests and np.array_equal(a.W, b.W)


def test_the_habit_teaches_olvasos_expectations():
    plain, taught = mind(True), mind(True, habit_teaches="answers")
    live(plain, n=4000), live(taught, n=4000)
    assert plain.habit_acts and taught.habit_acts
    assert not np.array_equal(plain.W, taught.W)          # it learned from acts it never intended
    k = max(range(2), key=lambda j: sum(a[1] == j for a in taught.habit_acts))
    assert not np.array_equal(plain.W[k], taught.W[k])    # above all for the hand the habit uses


def test_a_felt_habit_act_is_a_trace_olvaso_can_read():
    m = mind(True, habit_teaches="felt")
    live(m, n=4000, refuse=lambda req: m.rng.random() < 0.2)
    assert m.habit_watch and len(m.with_intention(np.zeros(2))) == 2 + 2
    rep = mind_report(m, 0, 4)
    assert rep["habit_felt_read"] is not None and 0 <= rep["habit_felt_read"] <= 1
    assert "habit_felt_read_when_answered" in rep


def test_the_shuffled_control_feels_the_same_traces_elsewhere_and_later():
    m = mind(True, habit_teaches="felt_shuffled")
    live(m, n=4000, refuse=lambda req: m.rng.random() < 0.2)
    assert m.habit_watch and len(m.with_intention(np.zeros(2))) == 2 + 2
    acts = {id(a): a[0] for a in m.habit_acts}
    lags = [w[0] - acts[id(w[6])] for w in m.habit_watch]
    assert len(m.habit_watch) + len(m.habit_delayed) == len(m.habit_acts)
    assert min(lags) >= 50 and max(lags) < 500


def test_teaching_needs_a_habit():
    with pytest.raises(ValueError):
        mind(False, habit_teaches="answers")
    with pytest.raises(ValueError):
        mind(True, habit_teaches="always")
