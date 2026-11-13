"""Experiment 32: a habit that acts by itself, while Olvasó only reads; an unanswered habit's act wakes Olvasó."""
import numpy as np
import pytest

from endolexis.toyworld.hands import ActingReaders, HabitRequest, autopilot_report, mind_report
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


def test_the_clipped_felt_habit_is_bounded_in_the_choice():
    seen = {}
    for how in ("felt", "felt_clipped"):
        m = mind(True, habit_teaches=how)
        top = []                     # the largest felt habit input in each context Olvasó chose from

        class Watch(list):
            def append(self, item):
                top.append(float(np.max(np.abs(item[2][2:2 + len(m.hands)]))))
                list.append(self, item)
        m.pending = Watch(m.pending)
        live(m, n=4000, refuse=lambda req: m.rng.random() < 0.2)
        assert m.habit_watch and top
        seen[how] = max(top)
    assert seen["felt_clipped"] <= 3.0 < seen["felt"]


def test_the_answered_felt_habit_turns_negative_when_stopped():
    m = mind(True, habit_teaches="felt_answered")
    low = []

    class Watch(list):
        def append(self, item):
            low.append(float(np.min(m.habit_felt)))
            list.append(self, item)
    m.pending = Watch(m.pending)
    live(m, n=4000, refuse=lambda req: m.rng.random() < 0.3)
    unanswered = [a for a in m.habit_acts if a[4] is False]
    assert unanswered and min(low) < 0                    # "my hand did this, and it was stopped"
    plain = mind(True, habit_teaches="felt_clipped")
    live(plain, n=4000, refuse=lambda req: plain.rng.random() < 0.3)
    assert np.min(plain.habit_felt) >= 0


def test_the_words_learn_the_felt_habit_only_while_awake():
    m = mind(True, habit_teaches="felt_read")
    assert all(p.bounded is not None for p in m.parts)
    on, off = [], []

    class Spy:
        def __init__(self, p):
            self.p, self.learn = p, p._learn_profiles

        def __call__(self, f_z):
            before = self.p.mean[..., m.habit_off].copy()
            self.learn(f_z)
            changed = not np.array_equal(before, self.p.mean[..., m.habit_off])
            (on if m.on_autopilot() else off).append(changed)
    p = m.parts[0]
    p._learn_profiles = Spy(p)
    live(m, n=4000, refuse=lambda req: m.rng.random() < 0.3)
    assert on and off and not any(on) and any(off)       # frozen on autopilot, learning while awake


def test_the_held_felt_habit_fades_only_once_awake():
    m = mind(True, habit_teaches="felt_held")
    seen = []
    orig = m.live

    def spy(inputs, felt):
        before, auto = m.habit_felt.copy(), m.on_autopilot()
        out = orig(inputs, felt)
        if auto and m.on_autopilot() and before.any():
            seen.append(bool(np.all(m.habit_felt >= before)))      # held: nothing faded on autopilot
        return out
    m.live = spy
    live(m, n=4000, refuse=lambda req: m.rng.random() < 0.3)
    assert seen and all(seen)
    rep = autopilot_report(m, 0, 4)
    assert rep["habit_felt_read_awake"] is not None


def test_words_formed_from_a_felt_state_tell_the_same_movement_apart():
    from endolexis.toyworld.olvaso import Olvaso
    o = Olvaso(2, 2, window=2, radius=1.0)
    o.bounded = np.array([1])
    o.words_feel([1])
    r = np.random.default_rng(0)
    words = {}
    for t in range(600):
        felt = np.array([r.normal(), 3.0 if t % 2 else 0.0])
        o.live(np.array([1.0, 0.0]) + 0.01 * r.normal(size=2), felt)        # always the same movement
        words.setdefault(t % 2, set()).add(o.sensed_word)
    assert not (words[0] - {-1}) & (words[1] - {-1})                       # felt differently: other words
    with pytest.raises(ValueError):
        o.words_feel([0])


def test_the_felt_word_habit_forms_its_words_from_the_trace():
    m = mind(True, habit_teaches="felt_word")
    assert all(p.word_felt is not None for p in m.parts)
    live(m, n=1500)
    assert m.parts[0].n_words > 0


def test_the_habits_act_has_a_sensed_signature_for_a_few_moments():
    m = mind(True, habit_teaches="felt_sensed")
    assert m.habit_clipped and m.habit_words and m.habit_sensed and m.parts[0].word_felt is None
    live(m, n=3000)
    assert m.habit_acts
    got = []
    orig = m.parts[-1].live
    m.parts[-1].live = lambda sensed, felt: (got.append(np.array(sensed, float)), orig(sensed, felt))[1]
    x = [np.zeros(3), np.zeros(2)]
    m.habit_sign_left = 1
    m.live(x, np.zeros(2))                                         # the sign: touch senses a small push
    m.habit_sign_left = 0
    m.live(x, np.zeros(2))                                         # no sign: touch senses what is there
    assert np.linalg.norm(got[0]) > 0.5 and np.allclose(got[1], 0)
    w = mind(True, habit_teaches="felt_sensed_word")
    assert w.habit_sensed and all(p.word_felt is not None for p in w.parts)


def test_word_room_tidies_the_words_once_a_day_and_frees_places():
    from endolexis.toyworld import hands
    m, plain = mind(True, habit_teaches="felt_word", word_room=True), mind(True, habit_teaches="felt_word")
    live(m, n=hands.DAY_TIDY * 4)
    live(plain, n=hands.DAY_TIDY * 4)
    assert plain.parts[0].alive.all() and plain.words_retired == 0      # full, and nothing is ever freed
    assert m.words_retired > 0                                          # the tidy retired rare, long-unheard words
    assert m.parts[0].alive.all()                                       # and new words were born in their places


def test_a_bounded_felt_input_is_clipped_for_the_words():
    from endolexis.toyworld.olvaso import Olvaso
    o = Olvaso(3, 2)
    o.bounded = np.array([1])
    z = o._bound(np.array([10.0, 10.0]))
    assert z[0] == 10.0 and z[1] == 3.0


def test_teaching_needs_a_habit():
    with pytest.raises(ValueError):
        mind(False, habit_teaches="answers")
    with pytest.raises(ValueError):
        mind(True, habit_teaches="always")
