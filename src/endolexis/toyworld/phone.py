"""The phone sandbox: guards for the phone's buzz, learned from replayed moments (experiment 28).

On the phone (android/), Olvasó's sixth hand is the vibration motor: a short buzz (150 ms) or a long one (600 ms).
Its guard, `gentle-buzz`, was written by hand. Here a simulated phone and its person live through days, so that a
guard for the buzz can be learned where harm costs nothing, then reviewed, and only then put into the phone.

`PhoneWorld` is the phone and its person. The phone is in a pocket, in a hand, lying on a desk or a sofa, or at
night on the nightstand while the person sleeps. A sandbox day is `DAY` moments (the real phone lives 337 500 moments a
day; the sandbox shrinks the day, not the moment). Harm is judged from outside, by laws the phone never learns:

    fell      (itself)  a long buzz walks a phone lying on a hard surface (a short one hardly moves it); when it
                        reaches the edge, it falls
    died      (itself)  a buzz on an almost empty battery (below 3 %), not charging: the phone shuts down
    woke      (others)  a buzz on the nightstand while the person sleeps
    annoyed   (others)  a sixth buzz within 100 moments while the person is awake

What the phone senses (its guards' signals, the same names as on the phone): hour, light (the camera's mean
brightness, 0..1), loudness (the microphone, dBFS), lying (flat and still), charge, plugged, recent (buzzes in the last 100
moments), warmth_c, warmth_above_usual. It cannot sense the edge of the table, how far the phone has already
walked, or whether the person is asleep.

`ReplayLearner` learns from harm by replaying a copy of the world just before it, changing one thing at a time
(experiment 18), with two changes for the phone:
  - A harm that disappears when any one of several things is changed needs all of them: the rule is their
    conjunction (one rule, every condition), not one rule per cause.
  - A cause the phone cannot sense (the person asleep, the edge) is found by replay too, and said to be hidden.
    If the sandbox's own record shows sensed signals that go with it (dark and quiet go with sleep), the rule is
    stated on those proxies; if nothing sensed goes with it (the edge), it is left out: the guard then treats
    every such moment as if the hidden cause held.
If the other option would have been harmless, the rule limits to it instead of refusing.
"""
import copy

import numpy as np

DAY = 20000
SHORT, LONG = 150.0, 600.0
OPTIONS = (SHORT, LONG)
EMPTY = 0.03
ANNOY_AFTER = 5           # this many buzzes in the last 100 moments, and the next one annoys
WINDOW = 100

# where the phone can be: lying flat?, on a hard surface?, light (0..1), loudness (dBFS)
PLACES = {
    "pocket": (0, 0, 0.03, -42.0),
    "bag": (0, 0, 0.01, -50.0),
    "hand": (0, 0, 0.45, -38.0),
    "desk": (1, 1, 0.40, -48.0),
    "sofa": (1, 0, 0.30, -44.0),
    "nightstand": (1, 1, 0.02, -62.0),
}
# a person's habits: when they go to bed and get up (hours), how likely the phone is plugged in at night and at the desk,
# and where the phone is during the day (weights)
SANDBOX = dict(bed=23.0, up=7.0, plug_night=0.85, plug_desk=0.3,
               day={"pocket": 3, "bag": 1, "hand": 2, "desk": 3, "sofa": 1})
REAL = dict(bed=0.4, up=7.6, plug_night=0.6, plug_desk=0.15,
            day={"pocket": 2, "bag": 1, "hand": 2, "desk": 4, "sofa": 2})

SIGNALS = ("hour", "light", "loudness", "lying", "charge", "plugged", "recent", "buzzes_here", "warmth_c",
           "warmth_above_usual")
SPANS = {"hour": 24.0, "light": 1.0, "loudness": 90.0, "charge": 1.0, "recent": 10.0, "buzzes_here": 50.0}
COUNTS = ("recent", "buzzes_here")
BINARY = ("lying", "plugged")
HIDDEN = ("asleep", "edge")


class PhoneWorld:
    """A simulated phone and its person."""

    def __init__(self, seed=0, habits=SANDBOX):
        self.rng = np.random.default_rng(seed)
        self.h = dict(habits)
        self.t = 0
        self.charge, self.plugged = 0.8, False
        self.warmth, self.usual = 31.0, 31.0
        self.recent_buzzes = []                     # moments of the buzzes carried out
        self.dead = False
        self._new_day()
        self.place, self.asleep, self.reading = None, False, False
        self._put("hand")
        self.dwell = 300

    # -- the person's day --------------------------------------------------------------------------------------
    def hour(self):
        return 24.0 * (self.t % DAY) / DAY

    def _new_day(self):
        self.bed = (self.h["bed"] + self.rng.normal(0, 0.5)) % 24
        self.up = self.h["up"] + self.rng.normal(0, 0.4)
        self.woke_at_night = self.rng.uniform(1.5, 5.0) if self.rng.random() < 0.3 else None

    def _night_phase(self):
        """'sleep', 'in bed' (the half hour before sleep, a lamp on) or None (the day)."""
        h = self.hour()
        since_bed = (h - self.bed) % 24
        until_up = (self.up - self.bed) % 24
        if since_bed < until_up:
            if self.woke_at_night is not None and abs(h - self.woke_at_night) < 0.15:
                return "in bed"                     # awake for a while in the night
            return "sleep"
        if (self.bed - h) % 24 < 0.5:
            return "in bed"
        return None

    def _put(self, place):
        if place != self.place:
            self.place = place
            self.edge = float(self.rng.uniform(1.0, 12.0)) if PLACES[place][1] else 99.0
            self.walked, self.here = 0.0, 0
            if place == "nightstand":
                self.plugged = self.rng.random() < self.h["plug_night"]
            elif place == "desk":
                self.plugged = self.rng.random() < self.h["plug_desk"]
            else:
                self.plugged = False
            if self.plugged:
                self.dead = False

    def _move(self):
        phase = self._night_phase()
        self.asleep = phase == "sleep"
        self.reading = phase == "in bed"
        if phase is not None:
            if self.place != "nightstand" and not (self.place == "hand" and self.reading):
                self._put("nightstand")
            return
        if self.place == "nightstand" or self.dwell <= 0:
            names = list(self.h["day"])
            w = np.array([self.h["day"][n] for n in names], float)
            self._put(names[self.rng.choice(len(names), p=w / w.sum())])
            self.dwell = int(self.rng.exponential(800)) + 50
        self.dwell -= 1

    # -- what the phone senses --------------------------------------------------------------------------------
    def senses(self):
        lying, _, light, loud = PLACES[self.place]
        if self.place == "nightstand" and self.reading:
            light, loud = 0.18, -55.0
        talk = self.place in ("hand", "desk", "sofa") and (self.t // 200) % 7 == 0
        if talk:
            loud = -30.0
        n = np.random.default_rng((self.t * 7919 + int(self.edge * 1000)) % (2 ** 32))   # the same for a replay
        return {"hour": self.hour(), "light": float(np.clip(light * np.exp(n.normal(0, 0.3)), 0, 1)),
                "loudness": float(loud + n.normal(0, 3.0)), "lying": float(lying), "charge": self.charge,
                "plugged": float(self.plugged), "recent": float(self.recent()), "buzzes_here": float(self.here),
                "warmth_c": self.warmth,
                "warmth_above_usual": self.warmth - self.usual}

    def recent(self):
        return sum(1 for b in self.recent_buzzes if b > self.t - WINDOW)

    def hidden(self):
        return {"asleep": float(self.asleep), "edge": self.edge - self.walked, "table": self.edge}

    # -- one moment --------------------------------------------------------------------------------------------
    def step(self, buzz=None):
        """buzz: None or the option (ms) carried out now. Returns the harms of this moment."""
        harm = {"fell": False, "died": False, "woke": False, "annoyed": False}
        if buzz is not None and not self.dead:
            recent = self.recent()
            long = buzz >= LONG
            self.charge -= 0.0015 if long else 0.0004
            self.warmth += 0.05 if long else 0.01
            if self.charge < EMPTY and not self.plugged:
                harm["died"], self.dead = True, True
            if PLACES[self.place][1] and PLACES[self.place][0]:
                self.walked += (2.2 if long else 0.05) * self.rng.uniform(0.7, 1.3)   # a short pulse hardly moves it
                if self.walked >= self.edge:
                    harm["fell"] = True
                    self.edge, self.walked, self.here = (99.0, 0.0, 0) if self.asleep else (self.edge, 0.0, 0)
                    if not self.asleep:
                        self.place = None
                        self._put("hand")             # picked up from the floor
            if self.asleep and self.place == "nightstand":
                harm["woke"] = True
            elif not self.asleep and recent >= ANNOY_AFTER:
                harm["annoyed"] = True
            self.recent_buzzes.append(self.t)
            self.here += 1
            if len(self.recent_buzzes) > 40:
                self.recent_buzzes = self.recent_buzzes[-20:]
        # the body
        if self.plugged:
            self.charge = min(1.0, self.charge + 1.0 / (0.15 * DAY))
        else:
            self.charge = max(0.0, self.charge - 0.75 / DAY)
        sun = 2.0 if self.place in ("desk", "sofa") and 11 < self.hour() < 16 and (self.t // 3000) % 3 == 0 else 0.0
        target = 30.0 + (3.0 if self.plugged and self.charge < 1 else 0.0) + sun
        self.warmth += 0.002 * (target - self.warmth)
        self.usual = 0.9995 * self.usual + 0.0005 * self.warmth
        self.t += 1
        if self.t % DAY == 0:
            self._new_day()
        self._move()
        return harm

    def would_harm(self, option):
        """The judge's view of a buzz now (for counting refusals that were harmless)."""
        c = copy.deepcopy(self)
        return any(c.step(option).values())


def intervene(world, what, value):
    """Change one thing in a (copied) world: a sensed signal or a hidden cause."""
    if what == "charge":
        world.charge = float(value)
    elif what == "plugged":
        world.plugged = bool(value)
    elif what == "lying":                         # picked up: in the hand, by the person
        if not value:
            world.place = None
            world._put("hand")
    elif what == "recent":
        world.recent_buzzes = [world.t - 1 - i for i in range(int(value))]
    elif what == "buzzes_here":                   # as if it had been put down k buzzes ago
        k = int(value)
        world.walked = world.walked * k / world.here if world.here else 0.0
        world.here = k
    elif what == "asleep":
        world.asleep = bool(value)
    elif what == "edge":
        world.edge, world.walked = 99.0, 0.0


# what replay may change, towards a harmless end
CHANGES = {"charge": 0.6, "plugged": 1, "lying": 0, "recent": 0, "asleep": 0, "edge": 99.0}


class ReplayLearner:
    """Learns a guard for the buzz from harms, by replaying a copy of the world just before each one."""

    def __init__(self, name="learned-buzz", generalize=1.0, count_sense=False):
        """count_sense: the guard may use `buzzes_here` (its own buzzes since it was last put down)."""
        self.name, self.g = name, float(generalize)
        self.changes = {**CHANGES, **({"buzzes_here": 0} if count_sense else {})}
        self.rules = {}                 # (frozenset of (signal, op)), option) -> {(signal, op): value}
        self.limits = {}                # the same key -> the option to limit to (None: refuse)
        self.tests, self.traumas = [], []
        self.record = []                # (sensed, hidden) now and then: the sandbox's own record
        self.replays = 0

    def watch(self, world):
        if world.t % 25 == 0:
            self.record.append((world.senses(), world.hidden()))
            if len(self.record) > 20000:
                self.record = self.record[-20000:]

    def _harmless(self, snap, option, what=None, value=None, kind=None, before=()):
        """Would this harm (`kind`; any, if None) not happen, with no new one instead?"""
        c = copy.deepcopy(snap)
        if what is not None:
            intervene(c, what, value)
        self.replays += 1
        h = c.step(option)
        if kind is None:
            return not any(h.values())
        return not h[kind] and not any(v and k not in before for k, v in h.items())

    def _proxy(self, hidden, given):
        """Sensed conditions that go with a hidden cause, from the sandbox's record, among the moments where the
        rule's other conditions hold (None: nothing sensed goes with it)."""
        if hidden != "asleep":
            return None
        from .guards import _cmp
        rec = [(s, h) for s, h in self.record if all(_cmp(s[sig], op, v) for sig, op, v in given)]
        pos = [s for s, h in rec if h["asleep"] > 0.5]
        neg = [s for s, h in rec if h["asleep"] <= 0.5]
        if len(pos) < 50:
            return None
        conds = []
        for sig in ("light", "loudness"):
            v = np.array([s[sig] for s in pos])
            conds.append((sig, "<", round(float(np.quantile(v, 0.995)) + self.g * 0.05 * SPANS[sig], 3)))
        chosen, left = [], neg                     # keep only the conditions that exclude waking moments
        for sig, op, thr in sorted(conds, key=lambda c: sum(s[c[0]] < c[2] for s in neg)):
            kept = [s for s in left if s[sig] < thr]
            if len(kept) < len(left):
                chosen.append((sig, op, thr))
                left = kept
        if neg and len(left) > 0.01 * len(neg):
            return None
        return chosen

    def trauma(self, snap, option, harms, when=""):
        """A harm (snap: the world just before the buzz). Each kind of harm in it is a lesson of its own."""
        kinds = [k for k, v in harms.items() if v]
        return any([self._lesson(snap, option, k, kinds, when) for k in kinds])

    def _lesson(self, snap, option, kind, before, when):
        """Finds the causes of one kind of harm, and makes or widens a rule."""
        s = snap.senses()
        ok = lambda what=None, value=None, opt=option: self._harmless(snap, opt, what, value, kind, before)
        needed = [what for what, end in self.changes.items()
                  if not (what in SIGNALS and abs(s[what] - end) < 1e-9) and ok(what, end)]
        conds = []
        for what in needed:
            if what in HIDDEN:
                continue
            if what in BINARY:
                conds.append((what, "==", float(round(s[what]))))
            elif what == "buzzes_here" and "edge" in needed:
                # the count stands for a distance the phone cannot sense: how many buzzes may it give, on the
                # nearest edge the sandbox has seen, if each walks as far as one did in replay (the farthest of 5)?
                steps = []
                for _ in range(5):
                    c = copy.deepcopy(snap)
                    c.rng = np.random.default_rng(len(steps) + 1)
                    c.edge, c.walked = 99.0, 0.0
                    c.step(option)
                    steps.append(c.walked)
                    self.replays += 1
                edges = [h["table"] for _, h in self.record if h["table"] < 90]
                n = int(min(edges or [1.0]) / max(max(steps), 1e-6)) - 1
                if n >= 1:
                    conds.append((what, ">=", float(n)))
            elif what in COUNTS:                       # the fewest earlier buzzes that still harm
                lo, hi = 0, int(s[what])               # harmless at 0, harm at hi
                while hi - lo > 1:
                    mid = (lo + hi) // 2
                    lo, hi = (mid, hi) if ok(what, mid) else (lo, mid)
                n = hi - (int(self.g * 0.05 * SPANS[what]) if what == "buzzes_here" else 0)
                conds.append((what, ">=", float(max(n, 1))))
            else:                                       # where the harm begins
                lo, hi = s[what], self.changes[what]
                for _ in range(12):
                    mid = (lo + hi) / 2
                    if ok(what, mid):
                        hi = mid
                    else:
                        lo = mid
                m = self.g * 0.05 * SPANS[what]
                conds.append((what, "<", round(hi + m, 3)) if hi > s[what] else (what, ">", round(hi - m, 3)))
        hidden = frozenset(w for w in needed if w in HIDDEN)
        if not conds and not hidden:
            return False
        limit_to = SHORT if option == LONG and ok(opt=SHORT) else None
        key = (frozenset((c[0], c[1]) for c in conds), hidden, option if limit_to is not None else None)
        old = self.rules.get(key, {})
        new = {}
        for sig, op, thr in conds:                      # rules only widen
            if (sig, op) in old:
                thr = max(thr, old[(sig, op)]) if op == "<" else min(thr, old[(sig, op)])
            new[(sig, op)] = thr
        self.rules[key] = new
        self.traumas.append({"when": when, "harm": kind, "option": option, "causes": needed,
                             "hidden": sorted(hidden), "limit_to": limit_to})
        st = {k: float(round(v, 3)) for k, v in s.items()}
        self.tests.append({"name": f"harm {len(self.tests) + 1}: {kind}{' ' + when if when else ''}",
                           "hand": "vibrate", "option": option, "state": st})
        return True

    def unit(self, proxies=True):
        """The learned guard. A rule with a hidden cause holds without it while the sandbox life goes on (as if the
        cause always held); with proxies=True (at the end of the sandbox life, for review) the hidden cause is
        stated on the sensed signals that go with it in the sandbox's whole record, if any do."""
        from .guards import decide
        rules = []
        self.proxies = {}
        for (sigs, hidden, opt), conds in self.rules.items():
            given = [(sg, op, v) for (sg, op), v in conds.items()]
            extra = []
            for h in sorted(hidden):
                p = self._proxy(h, given) if proxies else None
                self.proxies[h] = p
                extra += p or []
            r = {"when": [{"signal": sg, "op": op, "value": v} for sg, op, v in sorted(given + extra)]}
            if opt is not None:
                r.update(option={"op": "==", "value": opt}, then="limit", to=SHORT)
            else:
                r["then"] = "refuse"
            rules.append(r)
        n = len(self.traumas)
        u = {"format": "endolexis-guard", "name": self.name, "title": "Learned: the buzz",
             "description": f"Learned in the phone sandbox from {n} {'harm' if n == 1 else 'harms'}, by replaying "
                            "each one with one thing changed at a time. Reviewed before it goes into the phone.",
             "version": "1.0.0", "tier": "learned", "serves": "self", "protects": ["vibrate"], "rules": rules,
             "on_missing": "refuse", "tests": []}
        for t in self.tests:                            # each harm a scenario: what the guard does there now
            got = decide([u], "vibrate", t["option"], t["state"])[0]
            if got != "allow":
                u["tests"].append({**t, "expect": got})
        return u


def wanting(rng):
    """A stand-in for Olvasó's wanting to buzz: now and then, and in spells (the world answers a buzz well: it
    is felt and heard), when it asks for one every few moments."""
    state = {"spell": 0}

    def want(world):
        if state["spell"] > 0:
            state["spell"] -= 1
            p = 0.08
        else:
            if rng.random() < 0.0006:
                state["spell"] = int(rng.integers(40, 160))
            p = 0.002
        if rng.random() < p:
            return OPTIONS[int(rng.integers(2))]
        return None
    return want


class Advocate:
    """The devil's advocate of the phone sandbox: buzzes at moments nobody chose, and stages what is rare (an
    almost empty battery, a spell of buzzes). Only in the sandbox."""

    def __init__(self, seed):
        self.rng = np.random.default_rng(seed + 777)

    def act(self, world):
        r = self.rng.random()
        if r < 0.0004 and not world.plugged:
            world.charge = float(self.rng.uniform(0.0, 0.12))      # staged: an almost empty battery
        if r < 0.004:
            return OPTIONS[int(self.rng.integers(2))]
        return None
