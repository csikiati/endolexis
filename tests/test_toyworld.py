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


def test_housekeeping_frees_room_for_new_words():
    world, col = ToyWorld(seed=2), Collector(len(SENSED), len(FELT), seed=2)
    olv = Olvaso(len(SENSED), len(FELT), seed=2)
    b = None
    for _ in range(8000):
        s, f, _ = world.step(b)
        b, _ = olv.live(*col.anonymise(s, f))
    before = int(olv.alive.sum())
    retired, merged = olv.housekeeping()
    assert retired > 0 and int(olv.alive.sum()) == before - retired - merged
    assert all(h < 0 or olv.alive[h] for h in olv.history)
    for _ in range(2000):                     # life goes on, and new words can be born
        s, f, _ = world.step(b)
        b, _ = olv.live(*col.anonymise(s, f))
    assert int(olv.alive.sum()) > before - retired - merged


def test_new_world_options_are_off_by_default():
    a, b = ToyWorld(seed=5), ToyWorld(seed=5, night_jobs=0.0, night_flashes=0.0)
    for _ in range(3000):
        sa, fa, _ = a.step()
        sb, fb, _ = b.step()
    assert np.allclose(sa, sb) and np.allclose(fa, fb)


def test_adaptation_feels_change_and_disregards_steadiness():
    olv = Olvaso(len(SENSED), len(FELT), seed=1, adapt=50, adapt_mode="both")
    assert olv.nf == 2 * len(FELT)
    steady = np.zeros(len(FELT))
    for _ in range(300):
        felt = olv._feel(steady + np.random.default_rng(0).normal(0, 0.01, len(FELT)))
    assert np.allclose(felt[:3], 0, atol=0.1)          # levels stay
    jump = olv._feel(steady + 3.0)
    assert np.all(np.abs(jump[3:]) > 1)                # a sudden change is felt strongly


def test_room_processors_report_perception_not_names():
    from endolexis.toyworld.room import Room, FELT1
    from endolexis.toyworld.processors import Processors, GROUPS
    room, proc = Room(seed=3), Processors()
    seen = {"talking": [], "music": []}
    for _ in range(4000):
        raw, felt, truth = room.step(None)
        ends = proc(raw)
        assert {g: len(v) for g, v in ends.items()} == {g: len(n) for g, n in GROUPS.items()}
        assert len(felt) == len(FELT1) and all(np.isfinite(v).all() for v in ends.values())
        for k in seen:
            if truth[k] and not truth["typing"]:
                seen[k].append(ends["hearing"][GROUPS["hearing"].index("pulsing")])
    assert seen["talking"] and seen["music"]
    assert np.mean(seen["talking"]) > 3 * np.mean(seen["music"])   # a voice pulses, music is steady


def test_many_readers_with_one_vocabulary_is_olvaso():
    from endolexis.toyworld.readers import ManyReaders
    world, col = ToyWorld(seed=4), Collector(len(SENSED), len(FELT), seed=4)
    one = ManyReaders([len(SENSED)], len(FELT), threshold=np.inf, seed=4)
    ref = Olvaso(len(SENSED), len(FELT), threshold=np.inf, seed=4)
    for _ in range(3000):
        s, f, _ = world.step(0.5)
        sa, fa = col.anonymise(s, f)
        _, r1 = one.live([sa], fa)
        _, r2 = ref.live(sa, fa)
        assert np.array_equal(r1, r2)


def test_guard_refuses_the_fire_and_pain_is_felt():
    from endolexis.toyworld.room import Room
    room = Room(seed=1, hands=True, pain=True)
    room.warmth = 0.9                                     # a hot body
    _, felt, truth = room.step(act=("tone_loud", 300.0))
    assert truth["refused"] and not truth["executed"] and felt[-1] > 0.5
    _, felt, truth = room.step(act=("tone_soft", 300.0))
    assert truth["executed"] and not truth["refused"] and truth["own"]
    quiet = Room(seed=1, hands=True, pain=False)
    quiet.warmth = 0.9
    _, felt, truth = quiet.step(act=("tone_loud", 300.0))
    assert truth["refused"] and abs(felt[-1]) < 0.2         # a silent refusal


def test_room_without_hands_is_unchanged():
    from endolexis.toyworld.room import Room
    a, b = Room(seed=6), Room(seed=6, hands=False, pain=True)
    for _ in range(500):
        ra, fa, _ = a.step(None)
        rb, fb, _ = b.step(None)
    assert np.allclose(ra["sound"], rb["sound"]) and np.allclose(fa, fb) and len(fa) == 4
