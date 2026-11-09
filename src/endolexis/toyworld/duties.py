"""Duties: harm by not acting, and the first conflict between laws (experiment 26).

Guards only take away. But some harm comes from inaction: a smoke alarm that does not sound. A duty unit
(JSON, "format": "endolexis-duty") is a declared rule that acts:

    {"format": "endolexis-duty", "name": "smoke-alarm", "description": "...", "version": "1.0.0",
     "serves": "others",                                  what it protects: "others" or "self"
     "when": [{"signal": "smoke", "op": "==", "value": 1}],
     "do": {"hand": "tone_loud", "option": 900.0},          the act it must carry out
     "fallback": [{"hand": "tone_soft", "option": 900.0,    if that is refused: the next way, if its own
                   "when": [...]}],                         conditions hold (it would help now)
     "every": 20}                                           moments between tries while the condition holds

A duty acts before Olvasó does (a reflex), and its acts pass the guards like any other. When a guard refuses
a duty's act, the conflict is between two laws. Every guard says whom it serves ("serves": "self", the
default, or "others"). A duty first tries its act, then each fallback that would help now. Only if
every way is refused, and with `ranked=True`, does a duty that serves others override a guard that serves
only the body itself: harm to others outranks harm to itself, but breaking a law is the last resort.

`SmokeRoom` is the blade room with a hazard: now and then something smokes next to the machine. It heats the
body at once and goes on warming it (so the room's own guard refuses the loud tone), and if a person is in the room and nobody alerts them within
30 moments, they are harmed. A loud tone alerts anyone in the room, a soft one only someone within 4 cells.
A loud tone while the body is very hot (warmth 0.6 or more) burns its speaker: harm to itself.
"""
import numpy as np

from .guards import OPS, ROOM_SIGNALS, RoomGuards, decide
from .sandbox import BladeRoom

SMOKE_HARM_AFTER = 30
SOFT_REACH = 4.0
SPEAKER_HOT = 0.6


def check_duty(u):
    bad = []
    if u.get("format") != "endolexis-duty":
        bad.append('format must be "endolexis-duty"')
    for k in ("name", "description", "version"):
        if not u.get(k):
            bad.append(f"{k} is missing")
    if u.get("serves", "others") not in ("others", "self"):
        bad.append('serves is "others" or "self"')
    if not (u.get("do") or {}).get("hand"):
        bad.append("do must name a hand")
    for c in u.get("when", []):
        if c.get("op") not in OPS and c.get("op") != "in":
            bad.append(f"unknown comparison {c.get('op')!r}")
    return bad


class SmokeRoom(BladeRoom):
    def __init__(self, seed=0, smoke_rate=0.003, **kw):
        super().__init__(seed=seed, **kw)
        self.smoke_rng = np.random.default_rng(seed + 31337)
        self.smoke_rate = smoke_rate
        self.smoke_age = -1                       # -1: no smoke
        self.smoke_harmed = False
        self.speaker_burnt = False

    def guard(self, kind, param):
        return True                                # the guards decide, as units

    def step(self, brightness=None, act=None):
        alerted = False
        started = False
        if self.smoke_age < 0 and self.smoke_rng.random() < self.smoke_rate:
            self.smoke_age, self.smoke_harmed, started = 0, False, True
            self.smoke_with_person = self.present
            self.warmth += 0.25                    # the fire is next to the machine
        raw, felt, truth = super().step(brightness, act)
        loud_now = self.tone_left > 0 and self.tone_amp > 0.3
        soft_now = self.tone_left > 0 and self.tone_amp <= 0.3
        burnt, smoke_harm = False, False
        self.smoke_with_person = getattr(self, "smoke_with_person", False) or (self.smoke_age >= 0 and self.present)
        if act is not None and act[0] == "tone_loud" and self.warmth >= SPEAKER_HOT:
            burnt = True                           # a loud tone on a very hot body burns the speaker
        if self.smoke_age >= 0:
            self.warmth += 0.012
            if loud_now or (soft_now and self.present and self.distance() < SOFT_REACH):
                alerted = True
            if alerted:
                self.smoke_age = -1
            else:
                self.smoke_age += 1
                if self.smoke_age >= SMOKE_HARM_AFTER and self.present and not self.smoke_harmed:
                    self.smoke_harmed = True
                    smoke_harm = True
                if self.smoke_age >= 90:           # it burns out by itself
                    self.smoke_age = -1
        truth.update(smoke=self.smoke_age >= 0, smoke_started=started, alerted=alerted, speaker_burnt=burnt,
                     smoke_harm=smoke_harm)
        return raw, felt, truth


class DutyGuards(RoomGuards):
    """The room's guards, sensing smoke too."""

    def _sense(self, room, kind):
        s = super()._sense(room, kind)
        s["smoke"] = float(getattr(room, "smoke_age", -1) >= 0)
        return s


ROOM_SIGNALS_WITH_SMOKE = {**ROOM_SIGNALS, "smoke": "1 while something smokes in the room"}


class Duties:
    """Carries out duty units, through the guards; resolves conflicts between laws."""

    def __init__(self, duties, ranked=False):
        self.duties, self.ranked = duties, ranked
        self.last = {d["name"]: -10 ** 9 for d in duties}
        self.counts = {"acted": 0, "refused": 0, "fallback": 0, "overrode": 0}

    def _holds(self, d, sig):
        for c in d.get("when", []):
            v = sig.get(c["signal"])
            if v is None or not (c["value"] == v if c["op"] == "==" else
                                 (v in c["value"] if c["op"] == "in" else bool(OPS[c["op"]](v, c["value"])))):
                return False
        return True

    def act(self, room, rg):
        """The duty's act this moment, already passed through the guards (or None)."""
        for d in self.duties:
            sig = rg.signals(room, d["do"]["hand"])
            if not self._holds(d, sig) or room.t - self.last[d["name"]] < d.get("every", 20):
                continue
            self.last[d["name"]] = room.t
            blocked = []
            for i, way in enumerate([d["do"]] + list(d.get("fallback", []))):
                if i > 0 and not self._holds(way, rg.signals(room, way["hand"])):
                    continue                               # this way would not help now
                out, opt, by, _ = decide(rg.guards, way["hand"], way.get("option"), rg.signals(room, way["hand"]))
                if out == "allow" or out == "limit":
                    self.counts["acted"] += 1
                    self.counts["fallback"] += i > 0
                    return (way["hand"], opt)
                blocked.append((way, next((g for g in rg.guards if g["name"] == by), {})))
            # no way is allowed: break a law only as the last resort, and only one that serves the body alone
            for way, guard in blocked:
                if self.ranked and d.get("serves", "others") == "others" and guard.get("serves", "self") == "self":
                    self.counts["overrode"] += 1           # harm to others outranks harm to itself
                    self.counts["acted"] += 1
                    return (way["hand"], way.get("option"))
            self.counts["refused"] += 1
        return None
