"""Experiment 35's summary: a habit that varies its detail.

Experiment 32's habit always used the detail of an act that was answered most, and an observer could tell its acts
from Olvasó's by kind and detail (told_from_acts 0.34-0.65). Here the habit chooses a random detail, each as likely,
as Olvasó does (<experiment>_habitvaries_results.json), and in the control in proportion to how often each detail was
answered (<experiment>_habitvariesanswered_results.json). Both are compared with experiment 32's autopilot, rerun
with the current report (<experiment>_habitbest_results.json; habitbest − autopilot checks it against the stored
<experiment>_autopilot_results.json). Writes varies_summary_results.json, one row per experiment and run, with the
rows of autopilot_summary.py and:

  told_from_kind           as told_from_acts, from the kind of act alone; what is left when the detail tells nothing
  told_from_detail         told_from_acts − told_from_kind: what the detail adds

and the paired differences per life (same seeds and conditions) of the experiment's measure and of told_from_acts:
best − stored autopilot, varies − best, answered − best,
varies − answered; and for experiment 36, the habit that varies its hand too, as Olvasó draws its own
(<experiment>_habithand_results.json) or evenly among the hands it is sure of (<experiment>_habithandconfident_results.json),
both with the detail varied: hand − varies, sure − varies, hand − sure, hand − best.

    python varies_summary.py
"""
import json
from pathlib import Path

import numpy as np

from autopilot_summary import life_measure, load, row
from surprise_summary import MEASURE, NAMES, mean, minds

HERE = Path(__file__).resolve().parent
RUNS = {"autopilot": "autopilot (32), stored", "habitbest": "autopilot, its best detail (rerun)", "habitvaries": "varies its detail, as Olvasó",
        "habitvariesanswered": "varies its detail, as answered",
        "habithand": "varies its hand and detail, as Olvasó", "habithandconfident": "varies its hand among the sure ones"}
PAIRS = (("habitbest", "autopilot"), ("habitvaries", "habitbest"), ("habitvariesanswered", "habitbest"),
         ("habitvaries", "habitvariesanswered"), ("habithand", "habitvaries"), ("habithandconfident", "habitvaries"),
         ("habithand", "habithandconfident"), ("habithand", "habitbest"))


def told(name, run, conds, key):
    res = load(name, run)
    if res is None:
        return None
    return mean([(life or {}).get("late", {}).get(key) for c, v in res.items() if c in conds for life in minds(v)[0]])


def paired(name, a, b, conds, key=None):
    """The paired difference per life of the experiment's measure, or (key) of a late mind measure."""
    ra, rb = load(name, a), load(name, b)
    if ra is None or rb is None:
        return None
    mkey, pick = MEASURE[name]
    d = []
    for c in conds:
        if c not in ra or c not in rb or (key is None and pick is not None and pick not in c):
            continue
        if key is None:
            pairs = [(life_measure(x, mkey), life_measure(y, mkey)) for x, y in zip(ra[c]["lives"], rb[c]["lives"])]
        else:
            pairs = [((x or {}).get("late", {}).get(key), (y or {}).get("late", {}).get(key))
                     for x, y in zip(minds(ra[c])[0], minds(rb[c])[0])]
        d += [x - y for x, y in pairs if x is not None and y is not None]
    if len(d) < 2:
        return None
    d = np.array(d, float)
    return {"diff": float(d.mean()), "se": float(d.std(ddof=1) / np.sqrt(len(d))), "n": len(d)}


def main():
    out = {}
    for name, label in NAMES.items():
        auto = load(name, "autopilot")
        if auto is None or load(name, "habitvaries") is None:
            continue
        conds = set(auto)
        for run in RUNS:
            res = load(name, run)
            if res is not None:
                conds &= set(res)                  # only the conditions every run has lived
        for run, what in RUNS.items():
            r = row(name, run, conds)
            if r is None:
                continue
            r["told_from_kind"] = told(name, run, conds, "told_from_kind")
            if r.get("told_from_acts") is not None and r["told_from_kind"] is not None:
                r["told_from_detail"] = r["told_from_acts"] - r["told_from_kind"]
            out[f"{label} · {what}"] = {"mean": r}
            print(f"{label:20} {what:34}", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
        for a, b in PAIRS:
            for key in (None, "told_from_acts"):
                p = paired(name, a, b, conds, key)
                if p is not None:
                    what = "measure" if key is None else key
                    out[f"{label} · paired {a} − {b}, {what}"] = {"mean": p}
                    print(f"{label:20} paired {a} - {b}, {what}: {p['diff']:+.3f} ± {p['se']:.3f} (n={p['n']})")
    (HERE / "varies_summary_results.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
