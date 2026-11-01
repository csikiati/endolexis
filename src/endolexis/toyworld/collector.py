"""Collector: turns the body's channels into anonymous numbers.

Within each bundle (felt, sensed) the channels are shuffled and given a random sign, scale
and offset, with a fresh secret key per life. The key goes to the observer only.
Olvasó receives two bundles of bare numbers: anatomy, not dictionary.
"""
import numpy as np


class Collector:
    def __init__(self, n_sensed, n_felt, seed=0):
        r = np.random.default_rng(seed + 10_000)
        self.sensed_perm = r.permutation(n_sensed)
        self.felt_perm = r.permutation(n_felt)
        self.sensed_gain = r.choice([-1, 1], n_sensed) * r.uniform(0.3, 5.0, n_sensed)
        self.felt_gain = r.choice([-1, 1], n_felt) * r.uniform(0.3, 5.0, n_felt)
        self.sensed_off = r.uniform(-10, 10, n_sensed)
        self.felt_off = r.uniform(-10, 10, n_felt)

    def anonymise(self, sensed, felt):
        s = sensed[self.sensed_perm] * self.sensed_gain + self.sensed_off
        f = felt[self.felt_perm] * self.felt_gain + self.felt_off
        return s, f

    def secret_key(self):
        """For the observer only. anon_index -> true_index, per bundle."""
        return {"sensed": self.sensed_perm.tolist(), "felt": self.felt_perm.tolist()}
