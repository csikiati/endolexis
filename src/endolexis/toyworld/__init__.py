"""endolexis.toyworld: Olvasó v0 in a simulated toy body (experiments 1-7, November 2026)."""
from .world import ToyWorld, SENSED, FELT
from .collector import Collector
from .olvaso import Olvaso
from .observer import Observer


def live_a_life(seed=0, days=30, day_length=1000, threshold=100.0, learn_threshold=False,
                schedule=None, memory=None, **olvaso_kwargs):
    """schedule: optional function day -> (threshold, learn) that lets a temperament change over
    a life. It is applied at the start of each day it returns something for."""
    world = ToyWorld(seed=seed, day_length=day_length)
    collector = Collector(len(SENSED), len(FELT), seed=seed)
    olvaso = Olvaso(len(SENSED), len(FELT), threshold=threshold,
                    learn_threshold=learn_threshold, seed=seed, memory=memory, **olvaso_kwargs)
    observer = Observer(collector.secret_key(), max_words=olvaso.max_words)
    brightness = None
    for t in range(days * day_length):
        if schedule is not None and t % day_length == 0:
            change = schedule(t // day_length)
            if change is not None:
                olvaso.threshold, olvaso.learn_threshold = float(change[0]), bool(change[1])
        sensed, felt, truth = world.step(brightness)
        s_anon, f_anon = collector.anonymise(sensed, felt)
        brightness, readings = olvaso.live(s_anon, f_anon)
        observer.watch(t, olvaso, readings, felt, truth)
    return observer.report(olvaso, warmup=day_length * 3)
