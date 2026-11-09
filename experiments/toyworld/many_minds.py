"""Experiment 16 - many Olvasós in one body, taking turns to sleep.

The same body (toy world v1 with hands, the mirror voice) and the same mind as experiments 13-15,
but one, two or three Olvasós live in it at once. Each is wired to processor outputs and to the
body's hands (`endolexis.studio` architectures; the web studio draws them), and each has its own
day: asleep (lid closed, nothing sensed), waking (it senses and reads but does not act yet), awake.

  one, never sleeps          - the baseline (naps once a day, as before)
  one, sleeps nights         - a third of each day asleep, from the room's nightfall
  two, take turns            - each sleeps half the day; one is always awake
  three, take turns          - the plan: each sleeps a third, wakes for a third, is awake a third,
                               staggered so that at every moment one sleeps, one wakes, one is awake
  three, take turns, no waking - each sleeps a third, no waking stage (two awake at a time)
  three, sleep together      - all three sleep the same third of the day (the night)
  three, never sleep         - redundancy alone
  three specialists, take turns - each Olvasó reads one processor only (vision, hearing, touch)
  three specialists, never sleep
  three, take turns[, moving], careful - a careful body: when several Olvasós read the same state, the best
                               must fit that many times better
  two / three, take turns, moving - the same turns, but every sleep starts 2.4 hours later each day, so each
                               Olvasó sees every hour of the room over its life

Questions: does a body with Olvasós that take turns read itself better, or more truly, than one
Olvasó - and is it sleeping, or just being many, that makes the difference? What does each cost
(Olvasós not asleep, on average)? Does acting suffer when the hands are shared?
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))  # run from a clone without installing
import numpy as np
from endolexis.studio import library, live, stagger, check
from endolexis.toyworld.room import KINDS

EXAMPLES = ROOT / "studio" / "examples"
THIRD = round(1 / 3, 4)


def architecture(name, olvasos, note=""):
    """olvasos: [(name, [processor names], sleep, waking[, shift])]; every Olvasó gets every hand."""
    lib = library()
    used = []
    for _, ps, *_ in olvasos:
        used += [p for p in ps if p not in used]
    procs = [{"id": f"p_{p}", "unit": lib[p], "x": 40, "y": 60 + 200 * i} for i, p in enumerate(used)]
    olvs = [{"id": f"o{i + 1}", "name": o[0], "sleep": o[2], "waking": o[3], "phase": 0.5}
            for i, o in enumerate(olvasos)]
    for ol, o in zip(olvs, olvasos):
        if len(o) > 4:
            ol["shift"] = o[4]
    outs = [{"id": f"h_{k}", "kind": k} for k in KINDS]
    links = []
    for o, (_, ps, *_) in zip(olvs, olvasos):
        for p in ps:
            for port in range(lib[p]["outputs"]):
                links.append({"from": {"node": f"p_{p}", "port": port}, "to": {"node": o["id"]}})
        for h in outs:
            links.append({"from": {"node": o["id"]}, "to": {"node": h["id"]}})
    arch = {"format": "endolexis-architecture", "version": 1, "name": name, "note": note,
            "processors": procs, "olvasos": olvs, "outputs": outs, "links": links,
            "life": {"days": 30, "childhood_days": 10}}
    return stagger(arch)


ALL = ["vision", "hearing", "touch"]
CONDITIONS = {
    "one, never sleeps": [("Olvasó", ALL, 0, 0)],
    "one, sleeps nights": [("Olvasó", ALL, THIRD, 0)],
    "two, take turns": [("A", ALL, 0.5, 0), ("B", ALL, 0.5, 0)],
    "three, take turns": [("A", ALL, THIRD, THIRD), ("B", ALL, THIRD, THIRD), ("C", ALL, THIRD, THIRD)],
    "three, take turns, no waking": [("A", ALL, THIRD, 0), ("B", ALL, THIRD, 0), ("C", ALL, THIRD, 0)],
    "three, sleep together": [("A", ALL, THIRD, 0), ("B", ALL, THIRD, 0), ("C", ALL, THIRD, 0)],
    "three, never sleep": [("A", ALL, 0, 0), ("B", ALL, 0, 0), ("C", ALL, 0, 0)],
    "three specialists, take turns": [("Eye", ["vision"], THIRD, THIRD), ("Ear", ["hearing"], THIRD, THIRD),
                                      ("Hand", ["touch"], THIRD, THIRD)],
    "three specialists, never sleep": [("Eye", ["vision"], 0, 0), ("Ear", ["hearing"], 0, 0), ("Hand", ["touch"], 0, 0)],
    # follow-up: with a fixed phase each Olvasó misses the same hours every day; let the sleeps move on
    # 0.1 of a day (2.4 hours) each day, all together, so the turns stay staggered
    "two, take turns, moving": [("A", ALL, 0.5, 0, 0.1), ("B", ALL, 0.5, 0, 0.1)],
    "three, take turns, moving": [("A", ALL, THIRD, THIRD, 0.1), ("B", ALL, THIRD, THIRD, 0.1), ("C", ALL, THIRD, THIRD, 0.1)],
}
# follow-up: three different readers give a coincidence three chances. A careful body: when several offer a
# reading of the same state, the best must fit that many times better
CAREFUL = {"three, take turns, careful": "three, take turns", "three, take turns, moving, careful": "three, take turns, moving"}
CONDITIONS.update({k: CONDITIONS[v] for k, v in CAREFUL.items()})


def make(cond):
    arch = architecture(cond, CONDITIONS[cond])
    if cond in CAREFUL:
        arch["body"] = {"compete": True}
    if cond == "three, sleep together":
        for o in arch["olvasos"]:
            o["phase"] = 0.5
    bad, _ = check(arch)
    assert not bad, bad
    return arch


def one_life(seed, cond, days=30):
    return live(make(cond), seed=seed, days=days)


def mean_of(lives):
    keys = [k for k in lives[0] if k != "members"]
    return {k: (float(np.mean([l[k] for l in lives if l[k] is not None]))
                if any(l[k] is not None for l in lives) else None) for k in keys}


def write_examples():
    EXAMPLES.mkdir(parents=True, exist_ok=True)
    for cond in CONDITIONS:
        slug = cond.replace(", ", "-").replace(" ", "-")
        (EXAMPLES / f"{slug}.json").write_text(json.dumps(make(cond), indent=2, ensure_ascii=False) + "\n")


def main(seeds=(1, 2, 3, 4, 5), days=30, conds=None):
    from multiprocessing import Pool
    fmt = lambda d: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()}
    out = {}
    path = Path(__file__).with_name("many_minds_results.json")
    with Pool() as pool:
        for cond in conds or CONDITIONS:
            lives = pool.starmap(one_life, [(s, cond, days) for s in seeds])
            out[cond] = {"lives": lives, "mean": mean_of(lives)}
            print(cond, fmt(out[cond]["mean"]), flush=True)
            if days == 30 and len(seeds) == 5:
                old = json.loads(path.read_text()) if path.exists() else {}
                path.write_text(json.dumps({**old, cond: out[cond]}, indent=2))
    return out


if __name__ == "__main__":
    write_examples()
    if "--quick" in sys.argv:
        main((2,), days=8, conds=[c for c in CONDITIONS if c in sys.argv[1:]] or None)
    elif "--examples" not in sys.argv:
        main(conds=[c for c in CONDITIONS if c in sys.argv[1:]] or None)
