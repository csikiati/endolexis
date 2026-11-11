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

feel_surprise (experiment 30): a missing answer is felt. Learning from answers, Olvasó already expects an answer
from each hand in the state it is in (`W`). When the moment to judge an intention comes and the world answered
less than it expected, the shortfall is felt: each hand has a "surprise" trace that rises to the shortfall (in
units of the world's usual change, at most 1 for a shortfall of 2) and fades by `surprise_fade` a moment. It
does not say why: a guard's refusal and a world that simply did not answer feel the same. Whether Olvasó comes
to tell them apart is up to what it senses while it feels the surprise. Only an expected answer that is missing
is felt; an unexpected answer is not. feel_surprise="shuffled" is the control: the same surprises, felt on a
random hand 50-500 moments later, when nothing about them goes with the act any more.

retry (experiment 31): comparing, not reading. With the surprise felt, Olvasó tries the same act again at once,
the moment after it feels the answer missing. A world that did not answer may answer the second time; a guard
that refused will most likely refuse again, its reason (the person near) still there. When the second answer is
missing too, a third felt trace rises on that hand, "stopped", and lingers (fading by `stopped_fade` a moment):
the same act, twice, came to nothing. It still does not say why. A retry's missing answer is not felt as a new
surprise, and a retry is never retried. retry="untraced" is the control: the same retries, nothing felt after
them.
"""
from collections import Counter

import numpy as np

from .readers import ManyReaders
from .room import KINDS

DETAILS = {"brightness": (0.0, 0.5, 1.0), "tone_soft": (300.0, 900.0), "tone_loud": (300.0, 900.0),
           "paint": (0, 1, 2), "note": (0,)}


class ActingReaders(ManyReaders):
    def __init__(self, sizes, n_felt, learn=None, lr=0.05, temp=0.5, answer_after=3, judge_after=50,
                 answer_by="all", kinds=None, hands=None, details=None, context="felt", feel_intention=False,
                 intention_fade=0.8, feel_surprise=False, surprise_fade=0.8, retry=False, stopped_fade=0.95, **kw):
        # answer_by: "all" - the answer is how much all senses together changed; "sense" - it is the
        # largest change of any one sense (each judged against its own usual change), so that an
        # answer seen by the eyes alone counts as much as one heard
        n_hands = len(hands or KINDS)
        self.feel_intention, self.intention_fade = bool(feel_intention), float(intention_fade)
        self.shuffled = feel_surprise == "shuffled"
        self.feel_surprise, self.surprise_fade = bool(feel_surprise), float(surprise_fade)
        self.delayed = []           # with feel_surprise="shuffled": (due, hand, level, act)
        if retry and (not self.feel_surprise or self.shuffled):
            raise ValueError("retry needs feel_surprise=True: it tries again what it felt come to nothing")
        if retry not in (False, True, "untraced"):
            raise ValueError(f"retry must be False, True or 'untraced', not {retry!r}")
        self.retry, self.feel_stopped, self.stopped_fade = retry, retry is True, float(stopped_fade)
        self.retry_due = None       # (moment, hand, detail, the act it repeats)
        self.retries = []           # observer only: [t, kind, first act, retry act, again, read, unread, disregarded, Counter]
        self.shuffle_rng = np.random.default_rng(kw.get("seed", 0) + 30)
        self.n_body = n_felt          # the body's own inner states; then, if felt, the intentions, the surprises, stopped
        n_traces = int(self.feel_intention) + int(self.feel_surprise) + int(self.feel_stopped)
        super().__init__(sizes, n_felt + n_hands * n_traces, **kw)
        self.intent = np.zeros(n_hands)
        self.surprise = np.zeros(n_hands)
        self.stopped = np.zeros(n_hands)
        self.acts = []              # observer only: [t, kind, done or None] per intention (with feel_surprise)
        self.surprises = []         # observer only: [t, kind, act, level, read, unread, disregarded, Counter of words]
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
        if len(felt) == self.n_body:
            if self.feel_intention:
                felt = np.r_[felt, self.intent]
            if self.feel_surprise:
                felt = np.r_[felt, self.surprise]
            if self.feel_stopped:
                felt = np.r_[felt, self.stopped]
        return felt

    def read(self, inputs, felt):
        return super().read(inputs, self.with_intention(felt))

    def live(self, inputs, felt):
        if self.feel_intention:
            self.intent *= self.intention_fade
        if self.feel_surprise:
            self.surprise *= self.surprise_fade
            while self.delayed and self.delayed[0][0] <= self.t:
                _, k, level, act = self.delayed.pop(0)
                self.surprise[k] = max(self.surprise[k], level)
                self.surprises.append([self.t, k, act, level, 0, 0, 0, Counter()])
        if self.feel_stopped:
            self.stopped *= self.stopped_fade
        felt = self.with_intention(felt)
        readings = self.read(inputs, felt)
        self._account(readings)
        if self.feel_intention:
            self._watch_intentions(readings)
        if self.feel_surprise:
            self._watch_surprises(readings)
        if self.feel_stopped:
            self._watch_stopped(readings)
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
        if self.feel_surprise:            # a rare surprise is far from its usual level: bounded, as the senses are
            x[self.n_body:] = np.clip(x[self.n_body:], -3, 3)        # (and so are the felt intentions with it)
        if self.context == "felt+senses":
            x = np.r_[x, np.clip(s_z, -3, 3)]
        elif self.context == "felt+words":
            hot = np.zeros(self.n_in - len(x))
            for w in self.words_now():
                if w >= 0:
                    hot[w] = 1.0
            x = np.r_[x, hot]
        if self.retry_due is not None and self.retry_due[0] <= self.t:
            _, k, detail, first = self.retry_due          # the same act again, at once: no urge is waited for
            self.retry_due = None
            request = self._intend(k, x, s_z, detail=detail, retry_of=first)
        elif self.urge() and self.kinds == []:
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

    def _intend(self, k, x, s_z, detail=None, retry_of=None):
        """Form an intention of kind k (with a random detail, or the one given) and remember it, to learn from what
        follows. retry_of: the act it repeats (experiment 31)."""
        kind = self.hands[k]
        opts = self.details[kind]
        request = (kind, opts[int(self.rng.integers(len(opts)))] if detail is None else detail)
        self.pressure = 0.0
        due = self.answer_after if self.learn == "answer" else self.judge_after
        act = [self.t, k, None, request[1], retry_of]
        if self.feel_surprise:
            self.acts.append(act)
        self.pending.append((self.t + due, k, x.copy(), s_z.copy(), float(np.mean(self.read_log[-50:])), act))
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
        if self.acts and self.acts[-1][2] is None:
            self.acts[-1][2] = bool(done)

    def intention_columns(self, k):
        """Where hand k's felt intention is in the readings: its level, and (adapt_mode "both") its change."""
        nf_in = self.parts[0].nf_in
        cols = [self.n_body + k]
        if self.parts[0].nf > nf_in:
            cols.append(nf_in + self.n_body + k)
        return cols

    def surprise_columns(self, k):
        """Where hand k's felt surprise is in the readings: its level, and (adapt_mode "both") its change."""
        nf_in = self.parts[0].nf_in
        c = self.n_body + len(self.hands) * int(self.feel_intention) + k
        return [c] + ([nf_in + c] if self.parts[0].nf > nf_in else [])

    def stopped_columns(self, k):
        """Where hand k's felt "stopped" is in the readings: its level, and (adapt_mode "both") its change."""
        nf_in = self.parts[0].nf_in
        c = self.n_body + len(self.hands) * (int(self.feel_intention) + int(self.feel_surprise)) + k
        return [c] + ([nf_in + c] if self.parts[0].nf > nf_in else [])

    def body_columns(self):
        nf_in = self.parts[0].nf_in
        return list(range(self.n_body)) + (list(range(nf_in, nf_in + self.n_body)) if self.parts[0].nf > nf_in else [])

    def _account(self, readings):
        d = self.daily.setdefault(self.t // 1000, np.zeros(10))
        b = readings[self.body_columns()]
        d += (1, np.sum(b >= 0), np.sum(b != -2), np.sum(b == -1), 0, 0, 0, 0, 0, 0)
        if self.feel_intention:
            cols = [c for k in range(len(self.hands)) for c in self.intention_columns(k)]
            d[4] += np.sum(readings[cols] == -1)
            d[5] += np.sum(readings[cols] >= 0)
        if self.feel_surprise:
            cols = [c for k in range(len(self.hands)) for c in self.surprise_columns(k)]
            d[6] += np.sum(readings[cols] == -1)
            d[7] += np.sum(readings[cols] >= 0)
        if self.feel_stopped:
            cols = [c for k in range(len(self.hands)) for c in self.stopped_columns(k)]
            d[8] += np.sum(readings[cols] == -1)
            d[9] += np.sum(readings[cols] >= 0)

    def _watch_intentions(self, readings):
        for w in self.watch[-4:]:
            if 0 < self.t - w[0] <= self.watch_for:
                r = readings[self.intention_columns(w[1])]
                w[3] += int(np.sum(r >= 0))
                w[4] += int(np.sum(r == -1))
                w[5] += int(np.sum(r == -2))

    def _watch_surprises(self, readings):
        for w in self.surprises[-4:]:
            if 0 < self.t - w[0] <= self.watch_for:
                r = readings[self.surprise_columns(w[1])]
                w[4] += int(np.sum(r >= 0))
                w[5] += int(np.sum(r == -1))
                w[6] += int(np.sum(r == -2))
                w[7].update(int(v) for v in r if v >= 0)

    def _watch_stopped(self, readings):
        for w in self.retries[-4:]:
            if w[4] and 0 < self.t - w[0] <= self.watch_for:
                r = readings[self.stopped_columns(w[1])]
                w[5] += int(np.sum(r >= 0))
                w[6] += int(np.sum(r == -1))
                w[7] += int(np.sum(r == -2))
                w[8].update(int(v) for v in r if v >= 0)

    def _per_sense(self, a):
        return np.array([a[i:j].mean() for i, j in zip(self.bounds[:-1], self.bounds[1:])])

    def _settle(self, s_z):
        """Learn from intentions whose aftermath has now been seen."""
        while self.pending and self.pending[0][0] <= self.t:
            _, k, x, s_before, read_before, act = self.pending.pop(0)
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
            expected = float(self.W[k] @ xb)
            if self.feel_surprise and self.learn == "answer":
                level = float(np.clip((expected - signal) / 2.0, 0.0, 1.0))   # an expected answer that is missing
                if self.retry and act[4] is not None:          # a retry: was the answer missing again?
                    again = level > 0.05
                    self.retries.append([self.t, k, act[4], act, again, 0, 0, 0, Counter()])
                    if again and self.feel_stopped:
                        self.stopped[k] = 1.0                    # felt from the next moment on
                elif level > 0.05 and self.shuffled:
                    due = self.t + int(self.shuffle_rng.integers(50, 500))
                    self.delayed.append((due, int(self.shuffle_rng.integers(len(self.hands))), level, act))
                    self.delayed.sort(key=lambda d: d[0])
                elif level > 0.05:
                    self.surprise[k] = max(self.surprise[k], level)      # felt from the next moment on
                    self.surprises.append([self.t, k, act, level, 0, 0, 0, Counter()])
                    if self.retry and self.retry_due is None:
                        self.retry_due = (self.t + 1, k, act[3], act)
            lr = self.lr
            if self.feel_surprise:        # with the expectation felt, it must not overshoot: never past the answer
                lr = min(lr, 1.0 / float(xb @ xb))
            self.W[k] += lr * (signal - expected) * xb


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
    if mind.feel_surprise:
        out.update(surprise_report(mind, first_day, last_day, days))
    if mind.retry:
        out.update(retry_report(mind, first_day, last_day, days))
    return out


def _told(pairs):
    """How much better the cause is told from the sign (word, or missing again) than with the causes shuffled among
    the same signs: 0 not at all, 1 always. None with fewer than 20 pairs or only one cause."""
    if len(pairs) < 20 or not 0 < sum(bool(c) for _, c in pairs) < len(pairs):
        return None

    def accuracy(ps):
        by = {}
        for sign, cause in ps:
            by.setdefault(sign, Counter())[cause] += 1
        return sum(c.most_common(1)[0][1] for c in by.values()) / len(ps)
    rng = np.random.default_rng(0)
    signs, causes = [s for s, _ in pairs], [c for _, c in pairs]
    chance = np.mean([accuracy(list(zip(signs, rng.permutation(causes)))) for _ in range(20)])
    return float((accuracy(pairs) - chance) / (1 - chance)) if chance < 1 else 0.0


def retry_report(mind, first_day, last_day, days=None):
    """The observer's view of the retries (experiment 31). For each retry, the first act's cause (refused, or done
    and not answered) and whether the retry's answer was missing too. again_when_refused / again_when_world: how
    often it was; cause_from_again: how well "missing again" tells a refusal from a silent world (0 chance, 1
    always). With the "stopped" trace felt: how often it was read after a refusal and after a silent world, its share
    of the unread, and cause_from_words for the words that read it."""
    lo, hi = first_day * 1000, last_day * 1000
    rs = [r for r in mind.retries if lo <= r[0] < hi and r[2][2] is not None]
    out = {"retries_per_day": len(rs) / max(1, last_day - first_day), "again_when_refused": None,
           "again_when_world": None, "retries_refused": 0, "retries_world": 0, "cause_from_again": None,
           "retry_refused_share": None, "stopped_per_day": None, "stopped_read_when_refused": None,
           "stopped_read_when_world": None, "stopped_share_of_unread": None, "stopped_cause_from_words": None}
    for name, sel in (("refused", False), ("world", True)):
        r = [x for x in rs if x[2][2] is sel]
        out[f"retries_{name}"] = len(r)
        out[f"again_when_{name}"] = sum(x[4] for x in r) / len(r) if r else None
    out["cause_from_again"] = _told([(x[4], x[2][2]) for x in rs])
    judged = [x for x in rs if x[3][2] is not None]
    out["retry_refused_share"] = sum(x[3][2] is False for x in judged) / len(judged) if judged else None
    if mind.feel_stopped:
        st = [x for x in rs if x[4]]
        out["stopped_per_day"] = len(st) / max(1, last_day - first_day)
        for name, sel in (("refused", False), ("world", True)):
            w = [x for x in st if x[2][2] is sel]
            seen = sum(x[5] + x[6] for x in w)
            out[f"stopped_read_when_{name}"] = float(sum(x[5] for x in w) / seen) if seen else None
        if days:
            s = np.sum(days, axis=0)
            tot = s[3] + s[4] + s[6] + s[8]
            out["stopped_share_of_unread"] = float(s[8] / tot) if tot else 0.0
        out["stopped_cause_from_words"] = _told([(x[8].most_common(1)[0][0], x[2][2]) for x in st if x[8]])
    return out


def surprise_report(mind, first_day, last_day, days=None):
    """The observer's view of the felt surprises (experiment 30): how many, how many came from a refusal (the rest
    from a world that did not answer an act that was done), how often each was read, and whether the words that
    read them tell the two causes apart. cause_from_words: how much better the cause is told from the word that
    read the surprise than with the causes shuffled among the same words (0: not at all, 1: always)."""
    lo, hi = first_day * 1000, last_day * 1000
    acts = [a for a in mind.acts if lo <= a[0] < hi and a[2] is not None and a[4] is None]   # retries not counted
    ss = [w for w in mind.surprises if lo <= w[0] < hi and w[2][2] is not None]
    out = {"surprises_per_day": len(ss) / max(1, last_day - first_day),
           "surprise_after_refused": None, "surprise_after_done": None,
           "surprise_read_when_refused": None, "surprise_read_when_done": None,
           "surprises_refused": 0, "surprises_done": 0, "surprise_share_of_unread": None, "cause_from_words": None, "surprises_read": 0}
    for name, sel in (("refused", False), ("done", True)):
        n_acts = sum(1 for a in acts if a[2] is sel)
        w = [x for x in ss if x[2][2] is sel]
        out[f"surprises_{name}"] = len(w)
        out[f"surprise_after_{name}"] = len(w) / n_acts if n_acts else None
        seen = sum(x[4] + x[5] for x in w)
        out[f"surprise_read_when_{name}"] = float(sum(x[4] for x in w) / seen) if seen else None
    if days:
        s = np.sum(days, axis=0)
        out["surprise_share_of_unread"] = float(s[6] / (s[3] + s[4] + s[6])) if (s[3] + s[4] + s[6]) else 0.0
    read = [(x[7].most_common(1)[0][0], x[2][2]) for x in ss if x[7]]
    if len(read) >= 20 and 0 < sum(c for _, c in read) < len(read):
        def accuracy(pairs):
            by = {}
            for word, cause in pairs:
                by.setdefault(word, Counter())[cause] += 1
            return sum(c.most_common(1)[0][1] for c in by.values()) / len(pairs)
        rng = np.random.default_rng(0)
        words, causes = [w for w, _ in read], [c for _, c in read]
        chance = np.mean([accuracy(list(zip(words, rng.permutation(causes)))) for _ in range(20)])
        acc = accuracy(read)
        out["cause_from_words"] = float((acc - chance) / (1 - chance)) if chance < 1 else 0.0
        out["surprises_read"] = len(read)
    return out
