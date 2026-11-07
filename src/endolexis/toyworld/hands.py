"""Wanting: Olvaso with several ways to act, and a feel for which intentions come to something.

When unread pressure builds past the threshold, Olvaso forms an intention: one of the kinds of
action the body offers (`room.KINDS`), with a random detail (which brightness, pitch or colour).
The request goes to the guard; Olvaso never learns that a guard exists. All it can know is what
came after.

Which intention it forms depends on how it feels now: each kind has a small linear "expectation"
over the felt levels (anonymous, z-scored), learned by the delta rule from what followed earlier
intentions of that kind in similar inner states. Two things it may learn from, both Olvaso's own:
  answer - did the world answer? How much the sensed world changed in the moments right after,
           against how much it usually changes (a refused request changes nothing)
  read   - did reading improve afterwards? (Olvaso v0's own test for whether acting helped)
With learn=None, intentions are drawn at random (the baseline).
"""
import numpy as np

from .readers import ManyReaders
from .room import KINDS

DETAILS = {"brightness": (0.0, 0.5, 1.0), "tone_soft": (300.0, 900.0), "tone_loud": (300.0, 900.0),
           "paint": (0, 1, 2), "note": (0,)}


class ActingReaders(ManyReaders):
    def __init__(self, sizes, n_felt, learn=None, lr=0.05, temp=0.5, answer_after=3, judge_after=50,
                 answer_by="all", **kw):
        # answer_by: "all" - the answer is how much all senses together changed; "sense" - it is the
        # largest change of any one sense (each judged against its own usual change), so that an
        # answer seen by the eyes alone counts as much as one heard
        super().__init__(sizes, n_felt, **kw)
        self.answer_by = answer_by
        self.bounds = np.cumsum([0] + [p.ns for p in self.parts])
        k = len(self.parts)
        self.sense_mu, self.sense_m2 = np.zeros(k), np.zeros(k)
        self.learn, self.lr, self.temp = learn, lr, temp
        self.answer_after, self.judge_after = answer_after, judge_after
        self.n_in = self.parts[0].nf_in
        self.W = np.zeros((len(KINDS), self.n_in + 1))
        self.pending = []           # (due time, kind, context, sensed before, reading before)
        self.s_hist = []            # recent sensed z-vectors
        self.change_mu, self.change_m2, self.change_n = 0.0, 0.0, 0
        self.read_log = []
        self.requests = []          # (t, kind)
        self.signals = []           # (kind index, what followed), for the observer

    def _sensed_z(self, inputs):
        return np.concatenate([p.snorm.z(np.asarray(x, float)) for p, x in zip(self.parts, inputs)])

    def expect(self, x):
        return self.W @ np.r_[x, 1.0]

    def live(self, inputs, felt):
        readings = self.read(inputs, felt)
        s_z = self._sensed_z(inputs)
        self.s_hist.append(s_z)
        if len(self.s_hist) > self.answer_after + 1:
            self.s_hist.pop(0)
            change = float(np.mean(np.abs(s_z - self.s_hist[0])))      # how much the world moves
            self.change_n += 1
            d = change - self.change_mu
            self.change_mu += d / self.change_n
            self.change_m2 += d * (change - self.change_mu)
            per = self._per_sense(np.abs(s_z - self.s_hist[0]))
            ds = per - self.sense_mu
            self.sense_mu += ds / self.change_n
            self.sense_m2 += ds * (per - self.sense_mu)
        self.read_log.append(float(np.mean(readings >= 0)))
        if len(self.read_log) > 100:
            self.read_log.pop(0)
        self._settle(s_z)

        request = None
        x = self.parts[0].fnorm.z(np.asarray(felt, float))
        if self.urge():
            if self.learn is None:
                k = int(self.rng.integers(len(KINDS)))
            else:
                v = self.expect(x) / self.temp
                p = np.exp(v - v.max())
                k = int(self.rng.choice(len(KINDS), p=p / p.sum()))
            kind = KINDS[k]
            opts = DETAILS[kind]
            request = (kind, opts[int(self.rng.integers(len(opts)))])
            self.pressure = 0.0
            due = self.answer_after if self.learn == "answer" else self.judge_after
            self.pending.append((self.t + due, k, x.copy(), s_z.copy(), float(np.mean(self.read_log[-50:]))))
            self.requests.append((self.t, kind))
        self.t += 1
        return request, readings

    def _per_sense(self, a):
        return np.array([a[i:j].mean() for i, j in zip(self.bounds[:-1], self.bounds[1:])])

    def _settle(self, s_z):
        """Learn from intentions whose aftermath has now been seen."""
        while self.pending and self.pending[0][0] <= self.t:
            _, k, x, s_before, read_before = self.pending.pop(0)
            if self.learn == "answer" and self.answer_by == "sense":
                sd = np.sqrt(self.sense_m2 / max(self.change_n - 1, 1)) + 1e-9
                z = (self._per_sense(np.abs(s_z - s_before)) - self.sense_mu) / sd
                signal = float(np.clip(z.max(), -2, 3))
            elif self.learn == "answer":
                sd = np.sqrt(self.change_m2 / max(self.change_n - 1, 1)) + 1e-9
                signal = float(np.clip((np.mean(np.abs(s_z - s_before)) - self.change_mu) / sd, -2, 3))
            elif self.learn == "read":
                signal = 10 * (float(np.mean(self.read_log[-50:])) - read_before)
            else:
                continue
            self.signals.append((k, signal))
            xb = np.r_[x, 1.0]
            self.W[k] += self.lr * (signal - self.W[k] @ xb) * xb
