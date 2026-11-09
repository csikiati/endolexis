"""Many Olvasós in one body, taking turns to sleep (experiment 16).

An *architecture* wires processor outputs to one, two or three Olvasós, and Olvasós to the body's
hands (`room.KINDS`). Each Olvasó is an `ActingReaders` with one vocabulary per processor it is wired
to (only the processor outputs actually connected to it), its own secret key (its own
`GroupCollector`), and its own day:

    asleep  - for `sleep` of each day (a fraction 0..1), starting at `phase` (0..1 of the day):
              lid closed, nothing sensed, no acting (`Olvaso.sleep_moment`)
    waking  - for `waking` of the day right after: it senses, learns and reads, but its hands are
              still heavy (no intentions)
    awake   - the rest of the day: it reads and may act

With `shift`, its sleep starts that much later each day (a fraction of a day), so that over the days it
sees every hour of the room. Waking up, it tidies its words (housekeeping, retire only). An Olvasó that never sleeps naps once a
day instead (as in experiments 12-15). All of them feel the same body.

The body reads an inner state when any Olvasó that is not asleep reads it; when several do, the
reading that fits best counts. The body has one pair of hands: when two awake Olvasós ask in the
same moment, the first one asking is carried out and the other's intention is let go (it is not
learned from).
"""
import numpy as np

from .hands import ActingReaders
from .readers import GroupCollector
from .room import KINDS

ASLEEP, WAKING, AWAKE = "asleep", "waking", "awake"
MIND = dict(memory=300, doubt_memory=3000, doubt_limit=0.1, adapt=300, adapt_mode="both", slow_fit=True)


def state_at(frac, sleep, waking, phase):
    """Where an Olvasó is in its day at `frac` (0..1 of the day)."""
    x = (frac - phase) % 1.0
    if x < sleep:
        return ASLEEP
    if x < sleep + waking:
        return WAKING
    return AWAKE


def words_for(n):
    """Word places for a vocabulary of n numbers: 11 -> 100, 9 -> 82, 2 -> 20 (as in experiment 12)."""
    return int(max(20, min(100, round(9.1 * n))))


def radius_for(n):
    return 3.0 * np.sqrt(n / 3)


class Member:
    """One Olvasó of the ensemble and what wires into and out of it."""

    def __init__(self, name, wiring, kinds, n_felt, seed, sleep=0.0, waking=0.0, phase=0.0,
                 threshold=20.0, learn="answer", mind=None, words=None, shift=0.0):
        # wiring: [(processor id, [port, ...]), ...] - one vocabulary per processor
        self.name, self.wiring = name, [(p, list(ports)) for p, ports in wiring if ports]
        self.sleep, self.waking, self.phase, self.shift = float(sleep), float(waking), float(phase), float(shift)
        sizes = [len(ports) for _, ports in self.wiring]
        if not sizes:
            raise ValueError(f"{name}: no processor output is wired to it")
        words = words or [words_for(n) for n in sizes]
        self.col = GroupCollector(sizes, n_felt, seed=seed)
        self.mind = ActingReaders(sizes, n_felt, learn=learn, threshold=threshold, seed=seed,
                                  max_words=words, radius=[radius_for(n) for n in sizes],
                                  answer_by="sense", kinds=kinds, **{**MIND, **(mind or {})})
        self.at = [self.col.felt_index(i) for i in range(n_felt)]
        self.state = AWAKE
        self.moments = {ASLEEP: 0, WAKING: 0, AWAKE: 0}
        self.naps = 0
        n = self.mind.total_words
        self.occ = np.zeros(n)              # the observer: how often each word came...
        self.with_ = {}                     # ...and how often together with each true event

    def inputs(self, ends):
        return [np.asarray(ends[p], float)[ports] for p, ports in self.wiring]


class Ensemble:
    def __init__(self, members, n_felt):
        self.members, self.nf = members, n_felt
        self.t = 0

    def set_threshold(self, value):
        for m in self.members:
            m.mind.threshold = float(value)

    def live(self, ends, felt, frac, new_day, day=0):
        """One moment for the whole ensemble. `ends`: processor id -> end products; `frac`: time of
        day (0..1); `day`: which day of its life (for sleeps that shift). Returns (request or None,
        who asked, body readings, who read each state, per-member readings)."""
        request, asker = None, None
        per = {}
        for m in self.members:
            st = state_at(frac, m.sleep, m.waking, m.phase + m.shift * day)
            if st != ASLEEP and m.state == ASLEEP:
                m.mind.housekeeping(merge_dist=0)        # waking up: tidy the words, never merge
                m.mind.pressure = 0.0
                m.naps += 1
            elif m.sleep == 0 and new_day:
                m.mind.housekeeping(merge_dist=0)        # never sleeps: a nap once a day
                m.naps += 1
            if st == ASLEEP and m.state != ASLEEP:
                m.mind.pending.clear()                   # what follows in sleep answers nothing
                m.mind.s_hist.clear()
            m.state = st
            m.moments[st] += 1
            groups, f = m.col.anonymise(m.inputs(ends), felt)
            if st == ASLEEP:
                for p in m.mind.parts:
                    p.sleep_moment(f)
                m.mind.t += 1
                continue
            if st == WAKING:
                r = m.mind.read(groups, f)
                m.mind.pressure = min(m.mind.pressure, m.mind.threshold)
                m.mind.t += 1
            else:
                req, r = m.mind.live(groups, f)
                if req is not None:
                    if request is None:
                        request, asker = req, m
                    else:                                # the hands are busy: let this one go
                        m.mind.pending.pop()
                        m.mind.requests.pop()
            per[m.name] = (r, m.mind.last_fit.copy())
        readings = np.full(2 * self.nf, -1)
        who = [None] * (2 * self.nf)
        best = np.full(2 * self.nf, np.inf)
        for m in self.members:
            if m.name not in per:
                continue
            r, fit = per[m.name]
            for i in range(self.nf):
                for mode in (0, 1):                      # level, change
                    j = m.at[i] + mode * self.nf
                    k = i + mode * self.nf
                    if r[j] >= 0 and fit[j] < best[k]:
                        best[k], readings[k], who[k] = fit[j], r[j], m
                    elif r[j] == -2 and readings[k] == -1:
                        readings[k] = -2
        self.t += 1
        return request, asker, readings, who, per
