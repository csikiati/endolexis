"""Many vocabularies, one reader (experiment 12 onward).

`GroupCollector` anonymises each processor's end products the way `Collector` does a bundle:
within each processor the numbers are shuffled and given a random sign, scale and offset, with a
fresh secret key per life. Which numbers come from the same processor is anatomy, not dictionary.

`ManyReaders` is Olvaso with one word layer per vocabulary: each vocabulary forms its own words
from its own processors and learns its own meanings, and every inner state is read through
whichever vocabulary's word fits it best. Pressure and action are shared: one reader, one body.
Given a single vocabulary it is plain Olvaso.
"""
import numpy as np

from .olvaso import Olvaso


class GroupCollector:
    def __init__(self, sizes, n_felt, seed=0):
        r = np.random.default_rng(seed + 10_000)
        self.groups = []
        for n in sizes:
            self.groups.append((r.permutation(n), r.choice([-1, 1], n) * r.uniform(0.3, 5.0, n),
                                r.uniform(-10, 10, n)))
        self.felt = (r.permutation(n_felt), r.choice([-1, 1], n_felt) * r.uniform(0.3, 5.0, n_felt),
                     r.uniform(-10, 10, n_felt))

    @staticmethod
    def _apply(x, key):
        perm, gain, off = key
        return x[perm] * gain + off

    def anonymise(self, groups, felt):
        return [self._apply(np.asarray(g, float), k) for g, k in zip(groups, self.groups)], \
            self._apply(np.asarray(felt, float), self.felt)

    def felt_index(self, true_index):
        """For the observer only: where a true felt channel ended up."""
        return int(list(self.felt[0]).index(true_index))


class ManyReaders:
    def __init__(self, sizes, n_felt, threshold=100.0, seed=0, max_words=200, radius=3.0, **kw):
        k = len(sizes)
        max_words = list(max_words) if np.ndim(max_words) else [max_words] * k
        radius = list(radius) if np.ndim(radius) else [radius] * k
        self.parts = [Olvaso(n, n_felt, threshold=np.inf, seed=seed + 101 * i, max_words=m,
                             radius=rad, **kw)
                      for i, (n, m, rad) in enumerate(zip(sizes, max_words, radius))]
        self.offsets = np.cumsum([0] + max_words[:-1])
        self.total_words = int(sum(max_words))
        self.nf = self.parts[0].nf
        self.threshold = float(threshold)
        self.pressure = 0.0
        self.brightness = 0.5
        self.rng = np.random.default_rng(seed + 20_000)
        self.t = 0

    def live(self, inputs, felt):
        R, E = [], []
        for p, x in zip(self.parts, inputs):
            _, r = p.live(x, felt)
            R.append(r)
            E.append(np.where(r >= 0, p.last_err, np.inf))
        R, E = np.array(R), np.array(E)
        best = E.argmin(axis=0)
        cols = np.arange(self.nf)
        hit = np.isfinite(E[best, cols])
        readings = np.where(hit, self.offsets[best] + R[best, cols], -1)
        readings[~hit & (R == -2).any(axis=0)] = -2
        unread = int(np.sum(readings == -1))
        self.pressure = 0.99 * self.pressure + unread
        if self.pressure > self.threshold and self.parts[0].fnorm.n > 200:
            self.brightness = float(self.rng.choice([b for b in (0.0, 0.5, 1.0) if b != self.brightness]))
            self.pressure = 0.0
        self.t += 1
        return self.brightness, readings

    def words_now(self):
        """The word each vocabulary sensed this moment, in shared numbering (-1: none). With onsets,
        a word that goes on is still sensed, though not heard anew."""
        return [int(o + p.sensed_word) if getattr(p, "sensed_word", -1) >= 0 else -1
                for o, p in zip(self.offsets, self.parts)]

    def word_uses(self):
        return np.concatenate([p.word_uses for p in self.parts])

    def alive(self):
        return np.concatenate([p.alive for p in self.parts])

    def housekeeping(self, **kw):
        out = [p.housekeeping(**kw) for p in self.parts]
        return sum(a for a, _ in out), sum(m for _, m in out)
