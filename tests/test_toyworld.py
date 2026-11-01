"""Quick checks of endolexis.toyworld (Olvaso v0 in a toy world)."""
import numpy as np

from endolexis.toyworld import ToyWorld, Collector, Olvaso, SENSED, FELT, live_a_life


def test_same_seed_same_life():
    a = live_a_life(seed=3, days=4)
    b = live_a_life(seed=3, days=4)
    assert a == b


def test_doubt_keeps_noise_unread():
    kw = dict(seed=2, days=12, memory=300)
    with_doubt = live_a_life(doubt_memory=3000, doubt_limit=0.1, **kw)
    without = live_a_life(**kw)
    assert with_doubt["read_warmth"] > 0.5                      # warmth gets read
    assert with_doubt["read_drift"] < without["read_drift"] / 2  # doubt keeps noise far more unread


def test_sealed_sleep_reads_nothing():
    world, col = ToyWorld(seed=2), Collector(len(SENSED), len(FELT), seed=2)
    olv = Olvaso(len(SENSED), len(FELT), seed=2)
    b = None
    for _ in range(5000):
        s, f, _ = world.step(b)
        b, _ = olv.live(*col.anonymise(s, f))
    deep = []
    for k in range(300):
        s, f, _ = world.step(None)
        r, _ = olv.sleep_moment(col.anonymise(s, f)[1])
        if k > olv.max_lag:                 # after the day's last words have left the delay line
            deep.append(r)
    assert np.all(np.array(deep) < 0)


def test_consolidation_keeps_versions():
    olv = Olvaso(len(SENSED), len(FELT), seed=1, memory=300, doubt_memory=3000)
    olv.enable_long_term(3)
    world, col = ToyWorld(seed=1), Collector(len(SENSED), len(FELT), seed=1)
    b = None
    for _ in range(6000):
        s, f, _ = world.step(b)
        b, _ = olv.live(*col.anonymise(s, f))
    assert olv.consolidate() > 0
    assert olv.lt_used.any()
