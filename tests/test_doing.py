"""Experiment 38: a trace that comes with the doing. An answer Olvasó expected of its own act, and got, is felt on
that hand; the habit's acts, sent without an expectation, leave no such trace."""
import numpy as np
import pytest

from endolexis.toyworld.hands import ActingReaders, mind_report
from test_autopilot import mind
from test_surprise import MIND, live


def test_without_the_trace_nothing_changes():
    a, b = mind(True), mind(True, feel_doing=False)
    assert np.array_equal(live(a, n=3000), live(b, n=3000)) and a.requests == b.requests
    assert not a.doing_watch and "doing_felt_after_own" not in mind_report(a, 0, 3)


def test_only_olvasos_own_answered_acts_are_felt_as_done():
    m = mind(True, feel_doing=True)
    live(m, n=6000)
    own, hab = [w for w in m.doing_watch if not w[2]], [w for w in m.doing_watch if w[2]]
    assert own and hab, "both Olvasó and the habit must have acted"
    assert all(w[4] == 0 for w in hab)                              # the habit sent no expectation
    assert np.mean([w[4] for w in own if w[3]][20:]) > np.mean([w[4] for w in own if not w[3]] or [0])
    assert 0 <= m.doing.max() <= 1
    rep = mind_report(m, 0, 6)
    assert rep["doing_felt_after_habit"] == 0 and rep["doing_felt_after_own_answered"] > 0


def test_with_both_the_habits_acts_are_felt_too():
    m = mind(True, feel_doing="both")
    live(m, n=6000)
    assert any(w[4] > 0.05 for w in m.doing_watch if w[2])


def test_the_shuffled_trace_is_felt_later_and_not_after_the_act():
    m = mind(True, feel_doing="shuffled")
    live(m, n=6000)
    assert all(w[4] <= 0.05 for w in m.doing_watch)                 # nothing is felt when the answer is due
    assert m.doing_delayed or m.doing.max() > 0                     # it comes later, on some hand


def test_the_trace_is_felt_as_one_more_inner_state_for_each_hand():
    a, b = mind(True), mind(True, feel_doing=True)
    assert b.parts[0].nf_in == a.parts[0].nf_in + len(b.hands)
    assert b.doing_columns(1)[0] == b.n_body + 1


def test_feel_doing_needs_answers_and_is_not_combined_with_a_felt_habit():
    with pytest.raises(ValueError):
        ActingReaders([3, 2], 2, seed=1, max_words=[20, 10], radius=[1.5, 1.2], feel_doing=True, **MIND)
    with pytest.raises(ValueError):
        mind(True, feel_doing=True, habit_teaches="felt")
    with pytest.raises(ValueError):
        mind(True, feel_doing="loud")
