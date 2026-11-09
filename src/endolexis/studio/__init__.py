"""The studio: architectures of processors, Olvasós and hands, as JSON, and lives lived by them.

Three kinds of file:

  processor unit  (format "endolexis-processor") - one processor entity: name, title, description,
                  version, source (the outside source of its information), inputs and outputs
                  (how many numbers come in and go out), output_names, and optionally an
                  implementation: {"builtin": "vision" | "hearing" | "touch" | "v0", "outputs": [...]}
                  or {"python": "module:function"} (called with the world's raw senses, returns
                  `outputs` numbers)
  architecture    (format "endolexis-architecture") - processors, 1-3 Olvasós (each with its sleep,
                  waking and phase as fractions of a day, and optionally shift: how much later its sleep
                  starts each day), the body's hands, the links between them (a processor output to an
                  Olvasó, an Olvasó to a hand), and optionally body: {"compete": true}, a careful body
                  (when several Olvasós read a state, the best must fit that many times better)
  template        (templates.json) - starting points for new processor units, by use case

`python -m endolexis.studio --help` for the command line. The web studio (studio/index.html in the
repository) draws and edits architectures and makes processor units.
"""
import importlib
import json
import keyword
from pathlib import Path

import numpy as np

from ..toyworld.ensemble import ASLEEP, AWAKE, WAKING, Ensemble, Member, state_at
from ..toyworld.processors import GROUPS, V0_SENSES, Processors
from ..toyworld.room import FELT1, KINDS, Room

HERE = Path(__file__).resolve().parent
DAY = 1000
HANDS = {"brightness": "dims or lights the screen", "tone_soft": "sings a soft tone",
         "tone_loud": "sings a loud tone", "paint": "paints its window red, green or blue",
         "note": "writes a note to its sandbox"}
RAW = ("image", "sound", "touch")           # what the room gives a processor


def library():
    """The built-in processor units, by name."""
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((HERE / "processors").glob("*.json"))}


def templates():
    return json.loads((HERE / "templates.json").read_text(encoding="utf-8"))


def check_unit(u):
    """Problems with a processor unit (an empty list when it is fine)."""
    bad = []
    if u.get("format") != "endolexis-processor":
        bad.append('format must be "endolexis-processor"')
    for k in ("name", "description", "version", "source"):
        if not u.get(k):
            bad.append(f"{k} is missing")
    if not isinstance(u.get("inputs"), int) or u["inputs"] < 0:
        bad.append("inputs must be a whole number (0: any number)")
    if not isinstance(u.get("outputs"), int) or u["outputs"] < 1:
        bad.append("outputs must be a whole number, at least 1")
    names = u.get("output_names")
    if names is not None and len(names) != u.get("outputs"):
        bad.append(f"output_names has {len(names)} names for {u.get('outputs')} outputs")
    return bad


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check(arch):
    """Problems with an architecture, and warnings about its sleep schedule."""
    bad, warn = [], []
    if arch.get("format") != "endolexis-architecture":
        bad.append('format must be "endolexis-architecture"')
    procs = {p["id"]: p for p in arch.get("processors", [])}
    olvs = {o["id"]: o for o in arch.get("olvasos", [])}
    outs = {o["id"]: o for o in arch.get("outputs", [])}
    if not 1 <= len(olvs) <= 3:
        bad.append(f"{len(olvs)} Olvasós: an architecture has 1, 2 or 3")
    for p in procs.values():
        bad += [f"processor {p['id']}: {b}" for b in check_unit(p["unit"])]
    for o in outs.values():
        if o.get("kind") not in KINDS:
            bad.append(f"output {o['id']}: the body has no hand {o.get('kind')!r} (it has {', '.join(KINDS)})")
    for o in olvs.values():
        s, w = float(o.get("sleep", 0)), float(o.get("waking", 0))
        if not 0 <= float(o.get("shift", 0)) < 1:
            bad.append(f"{o.get('name', o['id'])}: shift is a fraction of a day, 0 up to 1")
        if not (0 <= s <= 1 and 0 <= w <= 1 and s + w <= 1 + 1e-9):
            bad.append(f"{o.get('name', o['id'])}: sleep and waking are fractions of a day, together at most 1")
    for ln in arch.get("links", []):
        a, b = ln["from"], ln["to"]
        if a["node"] in procs:
            n = procs[a["node"]]["unit"].get("outputs", 0)
            if b["node"] not in olvs:
                bad.append(f"a processor output must go to an Olvasó, not {b['node']}")
            if not 0 <= int(a.get("port", -1)) < n:
                bad.append(f"{a['node']} has no output {a.get('port')}")
        elif a["node"] in olvs:
            if b["node"] not in outs:
                bad.append(f"an Olvasó must go to an output, not {b['node']}")
        else:
            bad.append(f"a link starts at {a['node']}, which is not there")
    for o in olvs.values():
        if not any(ln["to"]["node"] == o["id"] for ln in arch.get("links", [])):
            bad.append(f"{o.get('name', o['id'])}: no processor output is wired to it")
    sch = schedule(arch)
    if sch["never_awake"]:
        warn.append(f"for {sch['never_awake']:.0%} of the day no Olvasó is awake: the body cannot act")
    if sch["none_reading"]:
        warn.append(f"for {sch['none_reading']:.0%} of the day every Olvasó sleeps: nothing is read")
    if sch["two_asleep"]:
        warn.append(f"for {sch['two_asleep']:.0%} of the day more than one Olvasó sleeps")
    return bad, warn


def schedule(arch, steps=DAY, day=0):
    """Who is asleep, waking and awake through a day (the first, or `day`); the shares of the day with gaps or overlaps."""
    olvs = arch.get("olvasos", [])
    states = [[state_at(i / steps, float(o.get("sleep", 0)), float(o.get("waking", 0)),
                        float(o.get("phase", 0)) + float(o.get("shift", 0)) * day)
               for o in olvs] for i in range(steps)]
    share = lambda f: sum(1 for s in states if f(s)) / steps
    return {
        "never_awake": share(lambda s: AWAKE not in s),
        "none_reading": share(lambda s: all(x == ASLEEP for x in s)),
        "two_asleep": share(lambda s: s.count(ASLEEP) > 1),
        "ideal": share(lambda s: s.count(AWAKE) >= 1 and s.count(ASLEEP) <= 1),
        "minds_on": float(np.mean([sum(x != ASLEEP for x in s) for s in states])),
    }


def stagger(arch):
    """Set the phases so that each Olvasó falls asleep as the one before it wakes up (in place)."""
    ph = 0.5                                        # the first one sleeps when the room's night begins
    for o in arch.get("olvasos", []):
        if float(o.get("sleep", 0)) > 0:
            o["phase"] = round(ph % 1.0, 4)
            ph += float(o["sleep"])
    return arch


class _Senses:
    """Runs the architecture's processors on the room's raw senses."""

    def __init__(self, procs):
        self.builtin = Processors()
        self.units = procs
        self.custom = {}
        for pid, p in procs.items():
            imp = p["unit"].get("implementation") or {}
            if "python" in imp:
                mod, fn = imp["python"].split(":")
                self.custom[pid] = getattr(importlib.import_module(mod), fn)
            elif imp.get("builtin") not in ("vision", "hearing", "touch", "v0"):
                raise ValueError(f"processor {pid} ({p['unit'].get('name')}): no implementation this world can run "
                                 f"(give it {{\"python\": \"module:function\"}})")

    def __call__(self, raw):
        ends = self.builtin(raw)
        ends["v0"] = np.array([ends[g][GROUPS[g].index(n)] for g, n in V0_SENSES])
        out = {}
        for pid, p in self.units.items():
            u = p["unit"]
            if pid in self.custom:
                out[pid] = np.asarray(self.custom[pid](raw), float)
            else:
                imp = u["implementation"]
                e = np.asarray(ends[imp["builtin"]], float)
                out[pid] = e[imp["outputs"]] if "outputs" in imp else e
            if len(out[pid]) != u["outputs"]:
                raise ValueError(f"processor {pid} gave {len(out[pid])} numbers, its unit says {u['outputs']}")
        return out


def build(arch, seed=1):
    """The ensemble an architecture describes, and the processors feeding it."""
    bad, _ = check(arch)
    if bad:
        raise ValueError("; ".join(bad))
    procs = {p["id"]: p for p in arch["processors"]}
    outs = {o["id"]: o for o in arch["outputs"]}
    members = []
    for i, o in enumerate(arch["olvasos"]):
        wiring = []
        for pid in procs:
            ports = sorted({int(ln["from"]["port"]) for ln in arch["links"]
                            if ln["from"]["node"] == pid and ln["to"]["node"] == o["id"]})
            if ports:
                wiring.append((pid, ports))
        kinds = sorted({KINDS.index(outs[ln["to"]["node"]]["kind"]) for ln in arch["links"]
                        if ln["from"]["node"] == o["id"]})
        members.append(Member(o.get("name", o["id"]), wiring, kinds, len(FELT1), seed=seed + 1000 * i,
                              sleep=o.get("sleep", 0), waking=o.get("waking", 0), phase=o.get("phase", 0),
                              threshold=o.get("threshold", 20.0), learn=o.get("learn", "answer"),
                              mind=o.get("mind"), shift=o.get("shift", 0.0)))
    used = {ln["from"]["node"] for ln in arch["links"]}
    return Ensemble(members, len(FELT1), compete=bool((arch.get("body") or {}).get("compete"))), _Senses({k: v for k, v in procs.items() if k in used})


def live(arch, seed=1, days=30, childhood_days=10, progress=None):
    """A whole life in the room (toy world v1, with hands). Returns what the observer saw."""
    ens, senses = build(arch, seed)
    room = Room(seed=seed, hands=True, pain=False, pain_channel=False, voice="mirror")
    nf = len(FELT1)
    I = {n: i for i, n in enumerate(FELT1)}
    events = ("typing", "music", "talking")
    for m in ens.members:
        m.with_ = {e: np.zeros(m.mind.total_words) for e in events}
    rows, acts = [], []
    act = None
    last = {"typing": -10**9, "music": -10**9}
    for t in range(days * DAY):
        day, tick = divmod(t, DAY)
        if tick == 0 and day == childhood_days:
            ens.set_threshold(250.0)                 # restless childhood, then patient
        raw, felt, truth = room.step(act=act)
        if act is not None:
            acts.append((day, act[0], bool(truth["refused"]), asker.name))
        act, asker, r, who, per = ens.live(senses(raw), felt, tick / DAY, tick == 0 and day >= 1, day)
        for m in ens.members:
            if m.state == ASLEEP:
                continue
            for w in m.mind.words_now():
                if w < 0:
                    continue
                part = int(np.searchsorted(m.mind.offsets, w, side="right") - 1)
                if m.mind.parts[part].word_uses[w - m.mind.offsets[part]] == 1:
                    m.occ[w] = 0
                    for e in events:
                        m.with_[e][w] = 0
                m.occ[w] += 1
                for e in events:
                    m.with_[e][w] += truth[e]
        for k in last:
            if truth[k]:
                last[k] = t

        def rd(name):
            i = I[name]
            j = i if r[i] >= 0 else i + nf
            return (int(r[j]), ens.members.index(who[j]) if who[j] is not None else -1)
        states = tuple(m.state for m in ens.members)
        rows.append((day, tick, truth["warmth"], truth["load"], rd("warmth"), rd("load"), rd("charge"), rd("drift"), states))
        if progress and tick == 0:
            progress(day)
    return _report(ens, rows, acts, days)


def _report(ens, rows, acts, days):
    known = [m.occ >= 10 for m in ens.members]
    share = lambda m, e: m.with_[e] / np.maximum(m.occ, 1)
    typing_w = [(share(m, "typing") > 0.5) & k for m, k in zip(ens.members, known)]
    music_w = [(share(m, "music") > 0.5) & k for m, k in zip(ens.members, known)]
    R = [x for x in rows if x[0] >= min(5, days // 2)]          # after the first days (or half a short life)
    late = [x for x in R if x[0] >= days * 2 // 3]
    warm = [x for x in R if x[2] > 0.3]
    loaded = [x for x in R if x[3] > 0.3]
    mean = lambda xs, f: float(np.mean([f(x) for x in xs])) if xs else None
    is_read = lambda rw: rw[0] >= 0
    via = lambda rw, sets: rw[0] >= 0 and rw[1] >= 0 and bool(sets[rw[1]][rw[0]])
    signals = [s for m in ens.members for _, s in m.mind.signals]
    A = [a for a in acts if a[0] >= min(5, days // 2)]
    out = {
        "warmth_read": mean(warm, lambda x: is_read(x[4])),
        "warmth_via_typing_words": mean(warm, lambda x: via(x[4], typing_w)),
        "load_read": mean(loaded, lambda x: is_read(x[5])),
        "load_via_music_words": mean(loaded, lambda x: via(x[5], music_w)),
        "charge_read_last_third": mean(late, lambda x: is_read(x[6])),
        "drift_read": mean(R, lambda x: is_read(x[7])),
        "linked_read": mean(R, lambda x: (is_read(x[4]) + is_read(x[5]) + is_read(x[6])) / 3),
        "linked_read_night": mean([x for x in R if x[1] >= DAY // 2], lambda x: (is_read(x[4]) + is_read(x[5]) + is_read(x[6])) / 3),
        "someone_awake": mean(R, lambda x: AWAKE in x[8]),
        "minds_on": mean(R, lambda x: sum(s != ASLEEP for s in x[8])),
        "acts_per_day": len(A) / max(days - min(5, days // 2), 1),
        "refused": float(np.mean([a[2] for a in A])) if A else None,
        "answered": float(np.mean([s > 0 for s in signals])) if signals else None,
        "words_alive": int(sum(m.mind.alive().sum() for m in ens.members)),
    }
    out["members"] = {m.name: {"words_alive": int(m.mind.alive().sum()), "naps": m.naps,
                               "acts": sum(1 for a in A if a[3] == m.name),
                               "reads": mean(R, lambda x, i=ens.members.index(m): sum(
                                   rw[1] == i for rw in (x[4], x[5], x[6])) / 3)}
                      for m in ens.members}
    return out


def stub(unit):
    """A Python skeleton implementing a processor unit, for {"python": "module:function"}."""
    given = unit.get("output_names") or [f"output_{i + 1}" for i in range(unit["outputs"])]
    names = [n if n.isidentifier() and not keyword.iskeyword(n) else f"output_{i + 1}" for i, n in enumerate(given)]
    hows = {o["name"]: o.get("how", "") for o in unit.get("outputs_how", [])}
    raw = (unit.get("source") or {}).get("raw") or "your_source"
    lines = [f'"""{unit.get("title") or unit["name"]} {unit.get("version", "")}: {unit.get("description", "")}',
             f'Source: {(unit.get("source") or {}).get("kind", "")} - {(unit.get("source") or {}).get("detail", "")}',
             '', 'Clockwork only: it reports perception, never names, and never learns."""', 'import numpy as np', '', '',
             'def process(raw):', f'    x = np.asarray(raw["{raw}"], float)   # {unit.get("inputs", 0)} numbers in (0: any number)']
    for n in names:
        lines.append(f"    {n} = 0.0   # {hows.get(given[names.index(n)]) or 'TODO'}")
    lines.append(f"    return [{', '.join(names)}]")
    return "\n".join(lines) + "\n"


def from_template(tpl, name=None, version="1.0.0"):
    """A new processor unit from a template (see templates())."""
    return {"format": "endolexis-processor", "name": name or tpl["name"], "title": tpl["title"],
            "description": tpl["description"], "version": version, "source": tpl["source"],
            "inputs": tpl["inputs"], "outputs": len(tpl["outputs"]),
            "output_names": [o["name"] for o in tpl["outputs"]],
            "outputs_how": tpl["outputs"]}
