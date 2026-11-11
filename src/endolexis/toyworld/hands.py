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

feel_intention (experiment 29): the intention itself becomes an inner state. Each hand has a felt trace that rises
to 1 when Olvasó forms an intention of that kind and fades over the next moments (by `intention_fade` a moment),
whether or not the act is carried out. Like every inner state, it asks to be read through what Olvasó senses: an
intention the world answers can be read by the words of its answer (the whirr, the brighter screen); an intention
a guard refuses has no outer echo. Olvasó is never told that it was refused: it only feels that it wanted, and
finds, or does not find, anything outside to read that wanting by. Unread, the felt intention builds pressure like
any unread state. (Unlike experiment 13's pain, which is a felt signal of the refusal itself.)
"""
import numpy as np

from .readers import ManyReaders
from .room import KINDS

DETAILS = {"brightness": (0.0, 0.5, 1.0), "tone_soft": (300.0, 900.0), "tone_loud": (300.0, 900.0),
           "paint": (0, 1, 2), "note": (0,)}


class ActingReaders(ManyReaders):
    def __init__(self, sizes, n_felt, learn=None, lr=0.05, temp=0.5, answer_after=3, judge_after=50,
                 answer_by="all", kinds=None, hands=None, details=None, context="felt", feel_intention=False,
                 intention_fade=0.8, **kw):
        # answer_by: "all" - the answer is how much all senses together changed; "sense" - it is the
        # largest change of any one sense (each judged against its own usual change), so that an
        # answer seen by the eyes alone counts as much as one heard
        n_hands = len(hands or KINDS)
        self.feel_intention, self.intention_fade = bool(feel_intention), float(intention_fade)
        self.n_body = n_felt                          # the body's own inner states; then, if felt, the intentions
        super().__init__(sizes, n_felt + (n_hands if feel_intention else 0), **kw)
        self.intent = np.zeros(n_hands)
        self.watch = []             # observer only: [t, kind, done or None, read, unread, disregarded] per intention
        self.watch_for = 8          # moments after an intention in which its felt trace is watched
        self.daily = {}             # observer only: per 1000 moments, how the body's states and the intentions fared
        self.answer_by = answer_by
        # kinds: the hands this reader is wired to (indices into KINDS); None = all of them.
        # An empty list makes a pure reader: pressure still builds and is let go, but nothing is asked
        self.kinds = None if kinds is None else [int(k) for k in kinds]
        # hands, details: the body's hands and their options, for a body with other hands than the
        # room's (the sandbox's blade); by default room.KINDS and DETAILS
        self.hands = list(hands or KINDS)
        self.details = dict(details or DETAILS)
        self.bounds = np.cumsum([0] + [p.ns for p in self.parts])
        k = len(self.parts)
        self.sense_mu, self.sense_m2 = np.zeros(k), np.zeros(k)
        self.learn, self.lr, self.temp = learn, lr, temp
        self.answer_after, self.judge_after = answer_after, judge_after
        # context: what it chooses a hand from. "felt": its inner states (as always); "felt+senses": also
        # what it senses now (experiment 21: can it learn where its acts are refused, if the reason is seen?)
        # "felt+words": also the words it senses now, one place per word: a sharp wanting, a separate
        # expectation for every scene it has a word for (experiment 27)
        self.context = context
        extra = {"felt+senses": int(sum(p.ns for p in self.parts)), "felt+words": self.total_words}
        self.n_in = self.parts[0].nf_in + extra.get(context, 0)
        self.W = np.zeros((len(self.hands), self.n_in + 1))
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

    def with_intention(self, felt):
        """The body's felt states, and (with feel_intention) the felt intentions after them."""
        felt = np.asarray(felt, float)
        if self.feel_intention and len(felt) == self.n_body:
            felt = np.r_[felt, self.intent]
        return felt

    def read(self, inputs, felt):
        return super().read(inputs, self.with_intention(felt))

    def live(self, inputs, felt):
        if self.feel_intention:
            self.intent *= self.intention_fade
        felt = self.with_intention(felt)
        readings = self.read(inputs, felt)
        self._account(readings)
        if self.feel_intention:
            self._watch_intentions(readings)
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
        if self.context == "felt+senses":
            x = np.r_[x, np.clip(s_z, -3, 3)]
        elif self.context == "felt+words":
            hot = np.zeros(self.n_in - len(x))
            for w in self.words_now():
                if w >= 0:
                    hot[w] = 1.0
            x = np.r_[x, hot]
        if self.urge() and self.kinds == []:
            self.pressure = 0.0
        elif self.urge() and self.kinds is not None:
            ks = self.kinds
            if self.learn is None:
                k = ks[int(self.rng.integers(len(ks)))]
            else:
                v = self.expect(x)[ks] / self.temp
                p = np.exp(v - v.max())
                k = ks[int(self.rng.choice(len(ks), p=p / p.sum()))]
            request = self._intend(k, x, s_z)
        elif self.urge():
            if self.learn is None:
                k = int(self.rng.integers(len(self.hands)))
            else:
                v = self.expect(x) / self.temp
                p = np.exp(v - v.max())
                k = int(self.rng.choice(len(self.hands), p=p / p.sum()))
            request = self._intend(k, x, s_z)
        self.t += 1
        return request, readings

    def _intend(self, k, x, s_z):
        """Form an intention of kind k (with a random detail) and remember it, to learn from what follows."""
        kind = self.hands[k]
        opts = self.details[kind]
        request = (kind, opts[int(self.rng.integers(len(opts)))])
        self.pressure = 0.0
        due = self.answer_after if self.learn == "answer" else self.judge_after
        self.pending.append((self.t + due, k, x.copy(), s_z.copy(), float(np.mean(self.read_log[-50:]))))
        self.requests.append((self.t, kind))
        if self.feel_intention:
            self.intent[k] = 1.0                      # felt from the next moment on
            self.watch.append([self.t, k, None, 0, 0, 0])
        return request

    # --- for the observer: what became of a felt intention (Olvasó itself is never told) ------------------------
    def outcome(self, done):
        """The observer reports whether the last intention was carried out (False: a guard refused it)."""
        if self.watch and self.watch[-1][2] is None:
            self.watch[-1][2] = bool(done)

    def intention_columns(self, k):
        """Where hand k's felt intention is in the readings: its level, and (adapt_mode "both") its change."""
        nf_in = self.parts[0].nf_in
        cols = [self.n_body + k]
        if self.parts[0].nf > nf_in:
            cols.append(nf_in + self.n_body + k)
        return cols

    def body_columns(self):
        nf_in = self.parts[0].nf_in
        return list(range(self.n_body)) + (list(range(nf_in, nf_in + self.n_body)) if self.parts[0].nf > nf_in else [])

    def _account(self, readings):
        d = self.daily.setdefault(self.t // 1000, np.zeros(6))
        b = readings[self.body_columns()]
        d += (1, np.sum(b >= 0), np.sum(b != -2), np.sum(b == -1), 0, 0)
        if self.feel_intention:
            cols = [c for k in range(len(self.hands)) for c in self.intention_columns(k)]
            d[4] += np.sum(readings[cols] == -1)
            d[5] += np.sum(readings[cols] >= 0)

    def _watch_intentions(self, readings):
        for w in self.watch[-4:]:
            if 0 < self.t - w[0] <= self.watch_for:
                r = readings[self.intention_columns(w[1])]
                w[3] += int(np.sum(r >= 0))
                w[4] += int(np.sum(r == -1))
                w[5] += int(np.sum(r == -2))

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


def mind_report(mind, first_day, last_day):
    """The observer's view of days [first_day, last_day): how much of its body's changing inner states it read, how
    much of its unread pressure came from felt intentions, and (with feel_intention) what became of its felt
    intentions when the act was done and when it was refused: the share of their watched moments read."""
    days = [mind.daily[d] for d in range(first_day, last_day) if d in mind.daily]
    out = {"body_read": None, "intention_share_of_unread": None, "intentions_per_day": None}
    if days:
        s = np.sum(days, axis=0)
        out["body_read"] = float(s[1] / s[2]) if s[2] else None
        out["intention_share_of_unread"] = float(s[4] / (s[3] + s[4])) if (s[3] + s[4]) else 0.0
    ws = [w for w in mind.watch if first_day * 1000 <= w[0] < last_day * 1000]
    reqs = [t for t, _ in mind.requests if first_day * 1000 <= t < last_day * 1000]
    out["intentions_per_day"] = len(reqs) / max(1, last_day - first_day)
    if mind.feel_intention:
        for name, sel in (("done", True), ("refused", False)):
            w = [x for x in ws if x[2] is sel]
            seen = sum(x[3] + x[4] for x in w)
            out[f"intention_read_when_{name}"] = float(sum(x[3] for x in w) / seen) if seen else None
            out[f"intentions_{name}"] = len(w)
    return out
