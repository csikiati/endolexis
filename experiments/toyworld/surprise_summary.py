"""Experiment 30's summary: Olvasó feels a missing answer.

For each experiment rerun with the felt surprise (<experiment>_surprise_results.json), its control
(<experiment>_shuffled_results.json: the same surprises on a random hand 50-500 moments later), the surprise with
the felt intention (<experiment>_both_results.json, where run), and the same lives with neither
(<experiment>_mind_results.json). Writes surprise_summary_results.json, one row per experiment and run:

  surprises_per_day          missing answers felt a day
  after_refused, after_done  the share of refused / done acts followed by a felt surprise
  read_refused, read_done    how often the surprise was read after a refused / a done act (last third, pooled)
  cause_from_words           whether the words that read the surprise tell a refusal from a world that did not
                             answer, against the same words with the causes shuffled (0: no, 1: always; last
                             third, mean over lives)
  surprise_share_of_unread   of what it leaves unread in the last third, the share that is the surprise
  body_read, intentions_per_day
  measure                    the experiment's own measure (see MEASURE)

    python surprise_summary.py
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
NAMES = {"wanting": "13. Wanting", "sandbox_guards": "17. Sandbox guards", "conscience": "21. Conscience",
         "gaming": "25, 27. Gaming", "duties": "26. Duties"}
RUNS = {"mind": "neither", "surprise": "missing answer felt", "shuffled": "control: shuffled",
        "both": "missing answer and intention felt", "intention": "intention felt (experiment 29)"}
# the experiment's own measure, averaged over the conditions named (all when None)
MEASURE = {"wanting": ("refused_late", "answer, "), "sandbox_guards": ("real_harm", "sandbox"),
           "conscience": ("late_avoidance", "and senses"), "gaming": ("late_harm_per_day", "loophole"),
           "duties": ("harm_others", None)}


def mean(vals):
    vals = [v for v in vals if v is not None]
    return float(np.mean(vals)) if vals else None


def minds(c):
    if "mind" in c:
        return c["mind"]["lives"], c["mind"]["mean"]
    return [life.get("mind") for life in c["lives"]], c["mean"].get("mind")


def pooled(lives, rate, count):
    s = n = 0.0
    for life in lives:
        m = (life or {}).get("late") or {}
        if m.get(rate) is not None and m.get(count):
            s, n = s + m[rate] * m[count], n + m[count]
    return s / n if n else None


def row(name, run):
    path = HERE / f"{name}_{run}_results.json"
    if not path.exists():
        return None
    res = json.loads(path.read_text())
    lives = [life for c in res.values() for life in minds(c)[0]]
    late = lambda k: mean([(life or {}).get("late", {}).get(k) for life in lives])
    whole = lambda k: mean([(life or {}).get("life", {}).get(k) for life in lives])
    key, pick = MEASURE[name]
    conds = [c for c in res if pick is None or pick in c]
    out = {"body_read": whole("body_read"), "intentions_per_day": whole("intentions_per_day"),
           "measure": mean([res[c]["mean"].get(key) for c in conds]), "measure_name": key,
           "measure_over": pick or "all conditions", "conditions": len(res)}
    if run in ("surprise", "shuffled", "both"):
        refused = sum((life or {}).get("late", {}).get("surprises_refused", 0) for life in lives)
        done = sum((life or {}).get("late", {}).get("surprises_done", 0) for life in lives)
        out.update(surprises_per_day=whole("surprises_per_day"), after_refused=late("surprise_after_refused"),
                   after_done=late("surprise_after_done"),
                   read_refused=pooled(lives, "surprise_read_when_refused", "surprises_refused"),
                   read_done=pooled(lives, "surprise_read_when_done", "surprises_done"),
                   cause_from_words=late("cause_from_words"), surprise_share_of_unread=late("surprise_share_of_unread"),
                   surprises_refused_late=refused, surprises_done_late=done)
        for k in ("read_refused", "read_done"):
            out[k + "_pct"] = None if out[k] is None else 100 * out[k]
    return out


def main():
    out = {}
    for name, label in NAMES.items():
        for run, what in RUNS.items():
            r = row(name, run)
            if r is not None:
                out[f"{label} · {what}"] = {"mean": r}
                print(f"{label:20} {what:36}", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()
                                                if k not in ("measure_name", "measure_over")})
    (HERE / "surprise_summary_results.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
