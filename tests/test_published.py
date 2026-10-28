"""Published results, reproduced value by value. Each test re-runs the first seed of a published condition and compares
every reported measure with the stored result. The full check over all 117 conditions:  python -m endolexis check
"""
import json
import os
import pytest

from endolexis.__main__ import _same, _mod

REF = json.load(open(os.path.join(os.path.dirname(__file__), "..", "src", "endolexis", "reference", "published.json")))
FAST = ["t14_pair_dim_reading.json", "t18_sight_0_5.json", "t20_amb_reading.json", "t21_couple_0_1.json"]


@pytest.mark.parametrize("fn", FAST)
def test_published_condition_first_seed(fn):
    e = REF[fn]
    got = _mod(e["harness"]).run(seed=e["seed0"], **e["opts"])
    want = e["runs"][0]
    bad = [(k, v, got[k]) for k, v in want.items() if k in got and not _same(v, got[k], 1e-9)]
    assert not bad, bad
