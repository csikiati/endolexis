"""Experiment 33's summary: the habit teaches Olvasó.

Experiment 32's habit acted while Olvasó only read, and Olvasó learned nothing from its acts. Here it does, in two ways:
from the answers to the habit's acts, as if they were its own (<experiment>_taught_results.json), or by feeling each
habit act afterwards on that hand, an inner state it can read (<experiment>_felthabit_results.json). Both are compared
with experiment 32's autopilot (<experiment>_autopilot_results.json) and with the same conditions lived without a
habit (<experiment>_mind_results.json). The control for the felt habit feels the same traces on a random hand, 50-500
moments later (<experiment>_feltshuffled_results.json); the clipped felt habit enters Olvasó's choice bounded
(<experiment>_feltclipped_results.json), and the answered felt habit, clipped and turning to -1 when the habit act
goes unanswered (<experiment>_feltanswered_results.json), and the felt habit read: clipped, felt bounded by the words
too, whose meanings for it learn only while Olvasó is awake (<experiment>_feltread_results.json). Writes teach_summary_results.json, one row per experiment and run:

  habit_acts_per_day, habit_share, wakes_per_day, habit_refused, habit_answered,
  body_read_autopilot, body_read_aware, body_read, told_from_acts    as in autopilot_summary.py
  habit_felt_read          (felt habit only) how often the felt habit act was read while it lingered, pooled;
  habit_felt_read_when_answered / _unanswered   the same, after an answered / an unanswered habit act
  habit_* / own_*          the experiment's harm measures for the habit's acts and for Olvasó's own
  silent_avoidance / silent_own_avoidance   (conscience) avoidance, and Olvasó's own, in "silent refusal, chooses
                           from what it feels and senses": 0.50 without a habit, 1.19 with experiment 32's autopilot
  measure                  the experiment's own measure (see surprise_summary.MEASURE)

and the paired differences of the measure per life: taught − autopilot, felt − autopilot, taught − without a habit,
felt − without, felt − shuffled, shuffled − autopilot, clipped − felt, clipped − autopilot, clipped − shuffled,
answered − clipped, answered − felt, answered − autopilot, read − clipped, read − felt, read − autopilot.

    python teach_summary.py
"""
import json
from pathlib import Path

from autopilot_summary import load, paired, row
from surprise_summary import NAMES, mean, minds

HERE = Path(__file__).resolve().parent
RUNS = {"mind": "without a habit", "autopilot": "autopilot (32)", "taught": "taught by the habit's answers",
        "felthabit": "habit's acts felt", "feltshuffled": "felt, shuffled (control)", "feltclipped": "felt, clipped",
        "feltanswered": "felt, answered", "feltread": "felt, read while awake"}
SILENT = "silent refusal, chooses from what it feels and senses"


def extra(name, run, conds):
    res = load(name, run)
    if res is None:
        return {}
    res = {c: v for c, v in res.items() if c in conds}
    lives = [life for c in res.values() for life in minds(c)[0]]
    out = {}
    if run in ("felthabit", "feltshuffled", "feltclipped", "feltanswered", "feltread"):
        for k in ("habit_felt_read", "habit_felt_read_when_answered", "habit_felt_read_when_unanswered"):
            out[k] = mean([(life or {}).get("late", {}).get(k) for life in lives])
    if name == "conscience" and SILENT in res:
        m = res[SILENT]["mean"]
        out["silent_avoidance"] = m.get("late_avoidance")
        out["silent_own_avoidance"] = m.get("late_own_avoidance")
    return out


def main():
    out = {}
    for name, label in NAMES.items():
        auto = load(name, "autopilot")
        if auto is None or (load(name, "taught") is None and load(name, "felthabit") is None):
            continue
        conds = set(auto)
        for run in ("taught", "felthabit", "feltshuffled", "feltclipped", "feltanswered", "feltread"):
            res = load(name, run)
            if res is not None:
                conds &= set(res)                  # only the conditions every run has lived
        for run, what in RUNS.items():
            r = row(name, run, conds)
            if r is None:
                continue
            r.update(extra(name, run, conds))
            out[f"{label} · {what}"] = {"mean": r}
            print(f"{label:20} {what:30}", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
        for a, b in (("taught", "autopilot"), ("felthabit", "autopilot"), ("taught", "mind"), ("felthabit", "mind"),
                     ("felthabit", "feltshuffled"), ("feltshuffled", "autopilot"),
                     ("feltclipped", "felthabit"), ("feltclipped", "autopilot"), ("feltclipped", "feltshuffled"),
                     ("feltanswered", "feltclipped"), ("feltanswered", "felthabit"), ("feltanswered", "autopilot"),
                     ("feltread", "feltclipped"), ("feltread", "felthabit"), ("feltread", "autopilot")):
            p = paired(name, a, b, conds)
            if p is not None:
                out[f"{label} · paired {a} − {b}"] = {"mean": p}
                print(f"{label:20} paired {a} - {b}: {p['diff']:+.3f} ± {p['se']:.3f} (n={p['n']})")
    (HERE / "teach_summary_results.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
