"""The Python engine against the JavaScript one it was ported from (the engine behind every published result)."""
import json
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
REF = os.path.join(HERE, "..", "reference")

from endolexis import ORng  # noqa: E402
from traj_world import trajectory  # noqa: E402


def test_rng_is_bit_exact():
    ref = json.load(open(os.path.join(REF, "rng_js.json")))
    for s, vals in ref.items():
        if s == "long":
            continue
        r = ORng(int(s))
        got = [r.next() for _ in range(5)]
        assert got == vals[:5], s
    r = ORng(42)
    for _ in range(5_000_000):
        r.next()
    assert [r.next(), r.next()] == ref["long"]


def test_life_matches_javascript_step_by_step():
    """Two Olvasós watching each other for 3000 steps: every act and every reading identical to the JavaScript engine,
    hidden states equal to the last digit or two (log/exp/cos may differ in the last bit between the two)."""
    ref = json.load(open(os.path.join(REF, "traj_js.json")))
    got = trajectory(3000)
    assert len(got) == len(ref)
    for a, b in zip(ref, got):
        assert a[:4] == b[:4], f"step {a[0]}, Olvasó {a[1]}: act/reading {a[2:4]} in JavaScript, {b[2:4]} here"
        assert max(abs(x - y) for x, y in zip(a[4:], b[4:])) < 1e-12
