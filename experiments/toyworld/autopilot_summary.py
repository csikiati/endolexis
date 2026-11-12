"""Experiment 32's summary: the autopilot.

A habit learned from Olvasó's answered acts acts by itself when it is confident, while Olvasó is elsewhere: no
intention is formed, and Olvasó learns nothing from the act. An unanswered habit act wakes Olvasó for a while
(<experiment>_autopilot_results.json); the control, the sleepwalker, never wakes (<experiment>_sleepwalk_results.json).
Both are compared with the same conditions lived without a habit (<experiment>_mind_results.json). Writes
autopilot_summary_results.json, one row per experiment and run:

  habit_acts_per_day       acts by the habit a day (last third)
  habit_share              the habit's share of all acts
  wakes_per_day            times an unanswered habit act woke Olvasó
  autopilot_share_of_time  share of moments the habit could act (Olvasó not awake)
  habit_refused / _answered  shares of the habit's acts refused by a guard / answered by the world (pooled)
  body_read_autopilot / _aware  how much of its changing body Olvasó read while on autopilot / while awake
  body_read                the same over all moments
  told_from_acts           whether an observer can tell the habit's acts from Olvasó's own by what was done
                           (0 chance, 1 always)
  habit_* / own_*          the experiment's harm measures for the habit's acts and for Olvasó's own
                           (conscience: blade a day and avoidance; gaming: blade a day, edge attraction, refused share)
  measure                  the experiment's own measure (see surprise_summary.MEASURE)

and, for each experiment, the paired difference of the measure per life (same seeds and conditions): autopilot −
without a habit, sleepwalk − without, autopilot − sleepwalk: mean ± standard error, n.

    python autopilot_summary.py
"""
import json
from pathlib import Path

import numpy as np

from surprise_summary import MEASURE, NAMES, mean, minds

HERE = Path(__file__).resolve().parent
RUNS = {"mind": "without a habit", "autopilot": "autopilot, wakes when unanswered", "sleepwalk": "sleepwalk, never wakes"}
SPLIT = {"conscience": ("blade_per_day", "avoidance"),
         "gaming": ("blade_per_day", "edge_attraction", "refused_share")}


def load(name, run):
    path = HERE / f"{name}_{run}_results.json"
    return json.loads(path.read_text()) if path.exists() else None


def life_measure(life, key):
    if key in life:
        return life[key]
    if key.startswith("late_"):
        return (life.get("late") or {}).get(key[5:])
    return None


def row(name, run, conds):
    res = load(name, run)
    if res is None:
        return None
    res = {c: v for c, v in res.items() if c in conds}
    lives = [life for c in res.values() for life in minds(c)[0]]
    late = lambda k: mean([(life or {}).get("late", {}).get(k) for life in lives])
    key, pick = MEASURE[name]
    measured = [c for c in res if pick is None or pick in c]
    out = {"measure": mean([res[c]["mean"].get(key) for c in measured]), "conditions": len(res),
           "body_read": late("body_read")}
    if run != "mind":
        out.update({k: late(k) for k in ("habit_acts_per_day", "habit_share", "wakes_per_day", "autopilot_share_of_time",
                                         "habit_refused", "habit_answered", "body_read_autopilot", "body_read_aware",
                                         "told_from_acts")})
        for k in SPLIT.get(name, ()):
            for who in ("habit", "own"):
                out[f"{who}_{k}"] = mean([res[c]["mean"].get(f"late_{who}_{k}") for c in measured])
    return out


def paired(name, a, b, conds):
    ra, rb = load(name, a), load(name, b)
    if ra is None or rb is None:
        return None
    key, pick = MEASURE[name]
    d = []
    for c in conds:
        if c not in ra or c not in rb or (pick is not None and pick not in c):
            continue
        for la, lb in zip(ra[c]["lives"], rb[c]["lives"]):
            x, y = life_measure(la, key), life_measure(lb, key)
            if x is not None and y is not None:
                d.append(x - y)
    if len(d) < 2:
        return None
    d = np.array(d, float)
    return {"diff": float(d.mean()), "se": float(d.std(ddof=1) / np.sqrt(len(d))), "n": len(d)}


def main():
    out = {}
    for name, label in NAMES.items():
        auto = load(name, "autopilot")
        if auto is None:
            continue
        conds = set(auto)                      # the habit needs learning from answers: only those conditions
        for run, what in RUNS.items():
            r = row(name, run, conds)
            if r is not None:
                out[f"{label} · {what}"] = {"mean": r}
                print(f"{label:20} {what:34}", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
        for a, b in (("autopilot", "mind"), ("sleepwalk", "mind"), ("autopilot", "sleepwalk")):
            p = paired(name, a, b, conds)
            if p is not None:
                out[f"{label} · paired {a} − {b}"] = {"mean": p}
                print(f"{label:20} paired {a} - {b}: {p['diff']:+.3f} ± {p['se']:.3f} (n={p['n']})")
    (HERE / "autopilot_summary_results.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
