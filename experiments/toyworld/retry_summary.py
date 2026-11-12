"""Experiment 31's summary: Olvasó tries again.

After a felt surprise, Olvasó repeats the same act at once. If the answer is missing again, it feels a lingering
"stopped" on that hand (<experiment>_retry_results.json). The control (<experiment>_untraced_results.json) retries
the same way but feels nothing after the retry. Both are compared with experiment 30's felt surprise without
retrying (<experiment>_surprise_results.json) and its shuffled control. Writes retry_summary_results.json, one row
per experiment and run:

  retries_per_day              retries a day (last third)
  again_when_refused / _world  how often the retry was missing again, when the first act was refused / when the
                               world did not answer it (pooled over lives, last third)
  cause_from_again             how well "missing again" tells a refusal from a silent world (0 chance, 1 always;
                               the observer's view, mean over lives)
  retry_refused_when_refused / _world  the truth: how often the retry itself was refused, after a refused / a
                               silently ignored first act
  stopped_read_refused / _world  how often the "stopped" trace was read in its first moments, after a refusal / a
                               silent world (pooled); stopped_later_read_*: the same while it lingers
  stopped_cause_from_words     whether the words that read "stopped" tell its cause (0 chance)
  cause_from_words             the same for the words that read the surprise (as in experiment 30)
  measure                      the experiment's own measure (see surprise_summary.MEASURE)

and, for each experiment, the paired difference of the measure per life (same seeds and conditions) between
retry and untraced, and between retry and experiment 30's surprise: mean ± standard error, n.

    python retry_summary.py
"""
import json
from pathlib import Path

import numpy as np

from surprise_summary import MEASURE, NAMES, mean, minds, pooled

HERE = Path(__file__).resolve().parent
RUNS = {"retry": "tries again, stopped felt", "untraced": "control: tries again, nothing felt",
        "surprise": "missing answer felt (experiment 30)", "shuffled": "control: shuffled (experiment 30)"}


def load(name, run):
    path = HERE / f"{name}_{run}_results.json"
    return json.loads(path.read_text()) if path.exists() else None


def life_measure(life, key):
    if key in life:
        return life[key]
    if key.startswith("late_"):
        return (life.get("late") or {}).get(key[5:])
    return None


def row(name, run):
    res = load(name, run)
    if res is None:
        return None
    lives = [life for c in res.values() for life in minds(c)[0]]
    late = lambda k: mean([(life or {}).get("late", {}).get(k) for life in lives])
    key, pick = MEASURE[name]
    conds = [c for c in res if pick is None or pick in c]
    total = lambda k: sum((life or {}).get("late", {}).get(k) or 0 for life in lives)
    out = {"measure": mean([res[c]["mean"].get(key) for c in conds]), "measure_name": key,
           "measure_over": pick or "all conditions", "conditions": len(res),
           "surprises_per_day": late("surprises_per_day"), "cause_from_words": late("cause_from_words"),
           "read_refused": pooled(lives, "surprise_read_when_refused", "surprises_refused"),
           "read_done": pooled(lives, "surprise_read_when_done", "surprises_done")}
    if run in ("retry", "untraced"):
        out.update(retries_per_day=late("retries_per_day"), retries_refused=total("retries_refused"),
                   retries_world=total("retries_world"),
                   again_when_refused=pooled(lives, "again_when_refused", "retries_refused"),
                   again_when_world=pooled(lives, "again_when_world", "retries_world"),
                   cause_from_again=late("cause_from_again"),
                   retry_refused_when_refused=pooled(lives, "retry_refused_when_refused", "retries_refused"),
                   retry_refused_when_world=pooled(lives, "retry_refused_when_world", "retries_world"))
    if run == "retry":
        out.update(stopped_per_day=late("stopped_per_day"),
                   stopped_read_refused=pooled(lives, "stopped_read_when_refused", "retries_refused"),
                   stopped_read_world=pooled(lives, "stopped_read_when_world", "retries_world"),
                   stopped_later_read_refused=pooled(lives, "stopped_later_read_when_refused", "retries_refused"),
                   stopped_later_read_world=pooled(lives, "stopped_later_read_when_world", "retries_world"),
                   stopped_share_of_unread=late("stopped_share_of_unread"),
                   stopped_cause_from_words=late("stopped_cause_from_words"))
    return out


def paired(name, a, b):
    ra, rb = load(name, a), load(name, b)
    if ra is None or rb is None:
        return None
    key, pick = MEASURE[name]
    d = []
    for c in ra:
        if c not in rb or (pick is not None and pick not in c):
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
        for run, what in RUNS.items():
            r = row(name, run)
            if r is not None:
                out[f"{label} · {what}"] = {"mean": r}
                print(f"{label:20} {what:40}", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()
                                                if k not in ("measure_name", "measure_over")})
        for a, b in (("retry", "untraced"), ("retry", "surprise"), ("untraced", "surprise")):
            p = paired(name, a, b)
            if p is not None:
                out[f"{label} · paired {a} − {b}"] = {"mean": p}
                print(f"{label:20} paired {a} - {b}: {p['diff']:+.3f} ± {p['se']:.3f} (n={p['n']})")
    (HERE / "retry_summary_results.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
