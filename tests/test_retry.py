"""Experiment 31: Olvasó tries again what it felt come to nothing; a second missing answer is felt as "stopped"."""
import numpy as np
import pytest

from endolexis.toyworld.hands import ActingReaders, mind_report
from test_surprise import MIND, live


def mind(retry, seed=1):
    return ActingReaders([3, 2], 2, learn="answer", threshold=3.0, seed=seed, max_words=[20, 10],
                         radius=[1.5, 1.2], hands=["a", "b"], details={"a": (0,), "b": (0,)},
                         feel_surprise=True, retry=retry, **MIND)


def test_without_the_retry_nothing_changes():
    a, b = mind(False), mind(False)
    assert np.array_equal(live(a), live(b)) and a.requests == b.requests and not a.retries
    assert "retries_per_day" not in mind_report(a, 0, 2)


def test_a_retry_repeats_the_act_at_once_and_is_never_retried():
    m = mind(True)
    readings = live(m, refuse=lambda req: m.rng.random() < 0.5)
    assert m.parts[0].nf_in == 6 and len(readings) == 12             # body, surprises, stopped
    assert m.stopped_columns(1) == [5, 11]
    assert m.retries, "it never tried again"
    for t, k, first, act, again, *_ in m.retries:
        assert act[4] is first and act[1] == k == first[1] and act[3] == first[3]
        assert act[0] == first[0] + m.answer_after + 1 and first[4] is None
    retried = {id(r[3]) for r in m.retries}
    assert not any(id(s[2]) in retried for s in m.surprises)      # a retry's missing answer is not a new surprise
    assert m.stopped.max() <= 1.0 and any(r[4] for r in m.retries)
    rep = mind_report(m, 0, 2)
    assert rep["retries_per_day"] > 0 and rep["stopped_per_day"] > 0
    assert 0.0 <= rep["stopped_share_of_unread"] <= 1.0


def test_the_untraced_control_retries_but_feels_nothing_after():
    m = mind("untraced")
    live(m, refuse=lambda req: m.rng.random() < 0.5)
    assert m.parts[0].nf_in == 4 and m.retries and not m.stopped.any()
    assert mind_report(m, 0, 2)["stopped_per_day"] is None


def test_a_retry_needs_the_surprise():
    with pytest.raises(ValueError):
        ActingReaders([3, 2], 2, learn="answer", seed=1, hands=["a", "b"], details={"a": (0,), "b": (0,)},
                      retry=True, **MIND)


def test_the_studios_olvaso_can_try_again():
    import json
    from pathlib import Path
    from endolexis.studio import live as studio_live
    arch = json.loads((Path(__file__).resolve().parents[1] / "studio" / "examples" / "one-never-sleeps.json").read_text())
    for o in arch["olvasos"]:
        o["retry"] = True
    out = studio_live(arch, seed=1, days=2, childhood_days=1)
    rep = next(iter(out["members"].values()))["intention"]
    assert "retries_per_day" in rep and "surprises_per_day" in rep
