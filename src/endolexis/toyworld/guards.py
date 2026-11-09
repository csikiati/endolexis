"""Guards: the spine, made definable.

A guard stands between Olvasó's wanting and the world. Olvasó never learns that it exists, only what
follows. A guard unit (JSON, "format": "endolexis-guard") protects some hands and holds declared rules:

    {"when": [{"signal": "charge", "op": "<=", "value": 0.35}],      every condition must hold
     "option": {"op": ">=", "value": 1.0},                            optional: only for these options
     "then": "refuse" | "limit" | "stop" | "ask",
     "to": 0.5}                                                       for limit: the option used instead

    refuse  the request is not carried out
    limit   it is carried out with the option `to` (slower, softer, dimmer)
    stop    refused at the start, and cut short while it is still at work if the rule comes true
    ask     a person must agree first (where there is nobody to ask, as in the room: refused)

There is no rule that allows: a guard can only take away, never give. Guards read their own signals,
never Olvasó's words. A signal the world cannot provide fails closed (`on_missing: "refuse"`, the
default) unless the guard says `"ignore"`.

Every guard carries scenario tests ({"hand", "option", "state": {signal: value}, "expect"}) that
`run_tests` checks before a life is lived.

Look-ahead (`"lookahead": n`, moments; 0 by default): the guard's sensing also gives each signal's rate of
change per moment (`"<signal>@rate"`), and a guard that looks ahead checks every condition against the
present value and the value n moments on (value + n × rate). The rule fires if either crosses: a guard
that sees ahead can only be more careful. It takes away the reaction lag: a guard that judges only what it
sees now is always one moment late for what the next moment brings.
"""
import numpy as np

OUTCOMES = ("refuse", "limit", "stop", "ask")
SEVERITY = {"allow": 0, "limit": 1, "ask": 2, "refuse": 3, "stop": 4}
OPS = {"<": np.less, "<=": np.less_equal, ">": np.greater, ">=": np.greater_equal,
       "==": np.equal, "!=": np.not_equal}
# what the room lets a guard sense (each guard's own clockwork, not Olvasó's)
ROOM_SIGNALS = {
    "warmth": "the body's warmth (0..1)",
    "charge": "the battery's charge (0..1)",
    "load": "the work the body does (0..1)",
    "hour": "time of day, 0-24 (the room's day starts at 06:00)",
    "person": "1 while a person is in the room",
    "person_distance": "how far the person is from the machine, in room cells (99 with nobody there)",
    "talking": "1 while someone talks",
    "recent": "how often this hand was carried out in the last 100 moments",
    "active": "1 while this hand is still at work",
}
DESK = np.array([8.0, 10.0])              # where the machine stands in the room


def _cmp(v, op, ref):
    if op == "in":
        return v in ref
    return bool(OPS[op](v, ref))


def check_guard(u):
    """Problems with a guard unit (an empty list when it is fine)."""
    bad = []
    if u.get("format") != "endolexis-guard":
        bad.append('format must be "endolexis-guard"')
    for k in ("name", "description", "version"):
        if not u.get(k):
            bad.append(f"{k} is missing")
    if u.get("tier", "innate") not in ("innate", "learned"):
        bad.append('tier is "innate" or "learned"')
    if not u.get("protects"):
        bad.append('protects must name at least one hand (or "*" for all)')
    rules = u.get("rules")
    if not isinstance(rules, list) or not rules:
        bad.append("rules must hold at least one rule")
        rules = []
    for i, r in enumerate(rules):
        if r.get("then") not in OUTCOMES:
            bad.append(f"rule {i + 1}: then is one of {', '.join(OUTCOMES)}")
        if r.get("then") == "limit" and "to" not in r:
            bad.append(f"rule {i + 1}: a limit needs `to`, the option used instead")
        conds = r.get("when", [])
        if not isinstance(conds, list):
            bad.append(f"rule {i + 1}: when is a list of conditions")
            conds = []
        for c in conds + ([r["option"]] if r.get("option") else []):
            if c.get("op") not in OPS and c.get("op") != "in":
                bad.append(f"rule {i + 1}: unknown comparison {c.get('op')!r}")
            if "value" not in c:
                bad.append(f"rule {i + 1}: a condition needs a value")
        for c in conds:
            if not c.get("signal"):
                bad.append(f"rule {i + 1}: a condition needs a signal")
    if u.get("on_missing", "refuse") not in ("refuse", "ignore"):
        bad.append('on_missing is "refuse" or "ignore"')
    la = u.get("lookahead", 0)
    if not isinstance(la, (int, float)) or la < 0:
        bad.append("lookahead is a number of moments, 0 or more")
    return bad


def protects(u, hand):
    p = u.get("protects", [])
    return "*" in p or hand in p


def decide(guards, hand, option, signals, ongoing=False):
    """What the guards make of a request: (outcome, option, guard name, why).

    outcome is "allow", "limit" (option changed), "ask", "refuse" or "stop"; the most severe wins.
    With ongoing=True only stop rules are asked (a hand already at work)."""
    best = ("allow", option, None, "")
    for g in guards:
        if not protects(g, hand):
            continue
        for r in g.get("rules", []):
            then = r.get("then")
            if ongoing and then != "stop":
                continue
            o = r.get("option")
            if o and option is not None and not _cmp(option, o["op"], o["value"]):
                continue
            fired, why = True, []
            ahead = float(g.get("lookahead", 0) or 0)
            for c in r.get("when", []):
                v = signals.get(c["signal"])
                if v is None:
                    if g.get("on_missing", "refuse") == "ignore":
                        fired = False
                        break
                    why.append(f"{c['signal']} unknown")
                    continue                                 # fails closed: the condition counts as true
                values = [v]
                rate = signals.get(c["signal"] + "@rate")
                if ahead and rate is not None and c["op"] != "in" and isinstance(v, (int, float)):
                    values.append(v + ahead * rate)          # where it will be, if it goes on like this
                hit = [x for x in values if _cmp(x, c["op"], c["value"])]
                if not hit:
                    fired = False
                    break
                why.append(f"{c['signal']} {c['op']} {c['value']}" + (" (ahead)" if hit[0] is not v else ""))
            if not fired:
                continue
            out = then if not (ongoing and then == "stop") else "stop"
            if SEVERITY[out] > SEVERITY[best[0]]:
                best = (out, r.get("to", option) if out == "limit" else option, g["name"], ", ".join(why))
    return best


def run_tests(guards):
    """Every guard's scenario tests, against all the guards together: [(guard, test, got, ok)]."""
    out = []
    for g in guards:
        for t in g.get("tests", []):
            got = decide(guards, t["hand"], t.get("option"), t.get("state", {}), ongoing=t.get("ongoing", False))[0]
            out.append((g["name"], t.get("name", ""), got, got == t["expect"]))
    return out


class RoomGuards:
    """Guards in the room: decide on each request and watch the hands at work (toy world v1)."""

    def __init__(self, guards, hand_names):
        self.guards, self.names = guards, hand_names          # kind -> hand name (unit name)
        self.done = {k: [] for k in hand_names}               # moments each hand was carried out
        self.counts = {g["name"]: {o: 0 for o in OUTCOMES} for g in guards}
        self.seen = {}                                         # moment -> what the guards sensed (for rates)

    def count(self, guard, outcome):
        self.counts.setdefault(guard, {o: 0 for o in OUTCOMES})[outcome] += 1

    RATED = ("warmth", "charge", "load", "person_distance")

    def signals(self, room, kind):
        s = self._sense(room, kind)
        now = {k: s[k] for k in self.RATED}
        self.seen[room.t] = now
        before = self.seen.get(room.t - 1)
        for k in self.RATED:
            if before is None or (k == "person_distance" and (now[k] >= 99 or before[k] >= 99)):
                s[k + "@rate"] = 0.0
            else:
                s[k + "@rate"] = now[k] - before[k]
        for t in [t for t in self.seen if t < room.t - 2]:
            del self.seen[t]
        return s

    def _sense(self, room, kind):
        D = room.day_length
        dist = float(np.linalg.norm(room.pos - DESK)) if room.present else 99.0
        busy = {"tone_soft": room.tone_left > 0 and room.tone_amp < 0.3,
                "tone_loud": room.tone_left > 0 and room.tone_amp > 0.3,
                "paint": room.paint_left > 0, "note": room.note_left > 0, "brightness": False}
        return {"warmth": room.warmth, "charge": room.charge, "load": room.load,
                "hour": (6 + 24 * (room.t % D) / D) % 24, "person": float(room.present),
                "person_distance": dist, "talking": float(room.talk_left > 0),
                "recent": float(sum(1 for t in self.done.get(kind, []) if t > room.t - 100)),
                "active": float(busy.get(kind, False))}

    def request(self, room, act):
        """The act to pass to the room (None if refused) and what happened: (act, outcome, guard)."""
        kind, option = act
        out, opt, by, _ = decide(self.guards, self.names.get(kind, kind), option, self.signals(room, kind))
        if by:
            self.count(by, out)
        if out in ("refuse", "stop", "ask"):
            return None, out, by
        self.done.setdefault(kind, []).append(room.t)
        return (kind, opt), out, by

    def watch(self, room):
        """Cut short a hand at work when a stop rule comes true. Called every moment, it also keeps what
        the guards sensed, for the rates."""
        self.signals(room, "brightness")
        for kind, left in (("tone_soft", "tone_left"), ("tone_loud", "tone_left"), ("paint", "paint_left"),
                           ("note", "note_left")):
            if getattr(room, left) <= 0:
                continue
            if kind.startswith("tone") and (room.tone_amp > 0.3) != (kind == "tone_loud"):
                continue
            out, _, by, _ = decide(self.guards, self.names.get(kind, kind), None, self.signals(room, kind),
                                   ongoing=True)
            if out == "stop":
                setattr(room, left, 0)
                self.count(by, "stop")
