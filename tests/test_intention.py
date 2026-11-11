"""Experiment 29: Olvasó feels its own intentions as inner states, whether or not the act is done."""
import json
from pathlib import Path

import numpy as np

from endolexis.toyworld.hands import ActingReaders, mind_report

ROOT = Path(__file__).resolve().parents[1]
MIND = dict(memory=300, doubt_memory=3000, doubt_limit=0.1, adapt=300, adapt_mode="both", slow_fit=True)


def mind(feel, seed=1):
    return ActingReaders([3, 2], 2, learn="answer", threshold=3.0, seed=seed, max_words=[20, 10],
                         radius=[1.5, 1.2], hands=["a", "b"], details={"a": (0,), "b": (0,)},
                         feel_intention=feel, **MIND)


def live(m, n=600, seed=2, refuse=lambda req: False):
    r = np.random.default_rng(seed)
    for _ in range(n):
        req, readings = m.live([r.normal(size=3), r.normal(size=2)], r.normal(size=2))
        if req is not None:
            m.outcome(not refuse(req))
    return readings


def test_without_the_feeling_nothing_changes():
    m = mind(False)
    readings = live(m)
    assert m.parts[0].nf_in == 2 and len(readings) == 4 and m.n_body == 2
    assert not m.watch and mind_report(m, 0, 1)["intention_share_of_unread"] == 0.0


def test_an_intention_is_felt_and_fades_whatever_became_of_it():
    m = mind(True)
    readings = live(m, refuse=lambda req: req[0] == "b")
    assert m.parts[0].nf_in == 4 and len(readings) == 8               # two body states, two felt intentions
    assert m.intention_columns(1) == [3, 7] and m.body_columns() == [0, 1, 4, 5]
    assert m.requests, "it never wanted anything"
    t, kind = m.requests[-1]
    assert m.intent.max() <= 1.0 and m.intent.min() >= 0.0
    k = m.hands.index(kind)
    assert np.isclose(m.intent[k], 0.8 ** (m.t - t - 1), atol=1e-12)               # 1 when formed, then fading
    done = {w[1]: w[2] for w in m.watch if w[2] is not None}
    assert done.get(0) is True and done.get(1) is False               # what the observer was told, per hand
    rep = mind_report(m, 0, 1)
    assert rep["intentions_done"] > 0 and rep["intentions_refused"] > 0
    assert 0.0 <= rep["intention_share_of_unread"] <= 1.0


def test_the_same_seed_lives_the_same_life():
    a, b = mind(True, seed=5), mind(True, seed=5)
    assert np.array_equal(live(a), live(b)) and a.requests == b.requests


def test_the_studios_olvaso_can_feel_its_intentions():
    from endolexis.studio import live as studio_live
    arch = json.loads((ROOT / "studio" / "examples" / "one-never-sleeps.json").read_text())
    for o in arch["olvasos"]:
        o["feel_intention"] = True
    out = studio_live(arch, seed=1, days=2, childhood_days=1)
    rep = next(iter(out["members"].values()))["intention"]
    assert rep["intentions_per_day"] > 0 and "intention_read_when_refused" in rep
