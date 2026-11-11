"""Experiment 30: Olvasó feels a missing answer, an answer it expected from a hand that did not come."""
import json
from pathlib import Path

import numpy as np

from endolexis.toyworld.hands import ActingReaders, mind_report

ROOT = Path(__file__).resolve().parents[1]
MIND = dict(memory=300, doubt_memory=3000, doubt_limit=0.1, adapt=300, adapt_mode="both", slow_fit=True)


def mind(surprise, intention=False, seed=1):
    return ActingReaders([3, 2], 2, learn="answer", threshold=3.0, seed=seed, max_words=[20, 10],
                         radius=[1.5, 1.2], hands=["a", "b"], details={"a": (0,), "b": (0,)},
                         feel_intention=intention, feel_surprise=surprise, **MIND)


def live(m, n=1500, seed=2, refuse=lambda req: False):
    """A world that answers hand "a" (the senses jump after it) unless refused; "b" is never answered."""
    r = np.random.default_rng(seed)
    jump = 0
    for _ in range(n):
        x = [r.normal(size=3) + (4.0 if jump else 0.0), r.normal(size=2)]
        jump = max(0, jump - 1)
        req, readings = m.live(x, r.normal(size=2))
        if req is not None:
            ok = not refuse(req)
            m.outcome(ok)
            if ok and req[0] == "a":
                jump = 3
    return readings


def test_without_the_surprise_nothing_changes():
    a, b = mind(False), ActingReaders([3, 2], 2, learn="answer", threshold=3.0, seed=1, max_words=[20, 10],
                                      radius=[1.5, 1.2], hands=["a", "b"], details={"a": (0,), "b": (0,)}, **MIND)
    assert np.array_equal(live(a), live(b)) and a.requests == b.requests and np.allclose(a.W, b.W)
    assert not a.surprises and "surprises_per_day" not in mind_report(a, 0, 2)


def test_a_missing_answer_is_felt_on_its_hand_and_fades():
    m = mind(True)
    readings = live(m, refuse=lambda req: m.rng.random() < 0.5)
    assert m.parts[0].nf_in == 4 and len(readings) == 8               # two body states, two surprises
    assert m.surprise_columns(1) == [3, 7]
    assert m.surprises, "it never missed an answer"
    assert m.surprise.min() >= 0.0 and m.surprise.max() <= 1.0
    for t, k, act, level, *_ in m.surprises:
        assert 0.05 < level <= 1.0 and act[2] is not None and act[1] == k and t == act[0] + m.answer_after
    rep = mind_report(m, 0, 2)
    assert rep["surprises_refused"] > 0 and rep["surprises_done"] > 0
    assert 0.0 <= rep["surprise_share_of_unread"] <= 1.0


def test_with_the_intention_the_surprise_comes_after_it():
    m = mind(True, intention=True)
    live(m, n=600)
    assert m.parts[0].nf_in == 6 and m.intention_columns(1) == [3, 9] and m.surprise_columns(1) == [5, 11]


def test_the_shuffled_control_moves_the_surprise_away_from_the_act():
    m = mind("shuffled")
    live(m)
    assert m.surprises and all(t - act[0] >= 50 for t, _, act, *_ in m.surprises)


def test_the_studios_olvaso_can_feel_a_missing_answer():
    from endolexis.studio import live as studio_live
    arch = json.loads((ROOT / "studio" / "examples" / "one-never-sleeps.json").read_text())
    for o in arch["olvasos"]:
        o["feel_surprise"] = True
    out = studio_live(arch, seed=1, days=2, childhood_days=1)
    rep = next(iter(out["members"].values()))["intention"]
    assert "surprises_per_day" in rep
