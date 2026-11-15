"""Experiments 38 and 38b's summary: a trace that comes with the doing.

Experiment 37's habit could not be told from Olvasó's own acts from inside either. Here Olvasó's own acts leave a
trace: when an answer it expected of its own act arrives, that is felt on the hand (the habit sends no expectation, so
its acts leave none). Two worlds (conscience, gaming), the habit whose hand varies among the sure ones, and four runs:
the trace (<world>_doing), the same traces at shuffled times on a random hand (<world>_doing_shuffled), the trace given
to the habit's acts too (<world>_doing_both), and the trace with words formed from it and room for new words
(<world>_doing_words); experiment 37's run without a trace (<world>_inside_sure, same seeds) is the baseline.
Experiment 38b repeats the four runs with a trace that lasts longer (<world>_doinglong*, --doing-long), and is
paired with them and with its own controls. Writes
doing_summary_results.json, one row per world and run, late in life, means over lives:

  doing_felt_after_own/_habit            share of Olvasó's own / the habit's acts after which the trace was felt
  doing_unread/_read/_disregarded_after  how the trace's sense was first read after the act (a quiet sense can be
                                         read too: a word can say that nothing is felt)
  doing_read_while_strong_own/_habit     share of the acts whose trace was read by a word while it was still strong
  told_ahead_doing_felt/_reading/_word   held out (signs learned on the first half of the acts, scored on the second;
                                         0 = always guessing the commoner cause, 1 = always right): who acted, told
                                         from whether the trace was felt / how it was first read / which word read it
  ..._answered                           the same among the acts the world answered only
  told_ahead_answer_alone                the same from whether the act was answered, alone
  told_from_acts, told_ahead_words       experiment 36's observer and experiment 37's inside view, for comparison
  habit_share, and what the world shows  (avoidance in the conscience world, edge and harm in the gaming world)

and the paired difference per life (same seeds) between the trace and each control, and between the trace and the
baseline: mean ± standard error, n.

    python doing_summary.py
"""
import json
from pathlib import Path

import numpy as np

from surprise_summary import mean, minds

HERE = Path(__file__).resolve().parent
WORLDS = {"conscience": "21. Conscience", "gaming": "30. Gaming"}
RUNS = {"inside_sure": "no trace (experiment 37)", "doing": "trace", "doing_shuffled": "trace shuffled",
        "doing_both": "trace for the habit too", "doing_words": "trace, with words formed from it",
        "doinglong": "longer trace", "doinglong_shuffled": "longer trace shuffled",
        "doinglong_both": "longer trace for the habit too", "doinglong_words": "longer trace, with words formed from it"}
SKIP = ("told_inside", "inside_")
PAIRS = (("doing", "doing_shuffled"), ("doing", "doing_both"), ("doing_words", "doing"), ("doing", "inside_sure"),
         ("doing_words", "inside_sure"),
         ("doinglong", "doinglong_shuffled"), ("doinglong", "doinglong_both"), ("doinglong_words", "doinglong"),
         ("doinglong", "doing"), ("doinglong_words", "doing_words"), ("doinglong_words", "doinglong_shuffled"))
PAIRED = ("told_ahead_doing_reading_answered", "told_ahead_doing_felt_answered", "told_ahead_doing_word_answered",
          "told_ahead_doing_reading", "told_ahead_words", "told_ahead_words_answered", "told_from_acts", "habit_share",
          "doing_read_while_strong_own", "doing_read_while_strong_habit", "intentions")


def lives(res):
    """The late-life measures of every life, in a fixed order (condition, then life), so that runs pair by seed."""
    return [(life or {}).get("late") or {} for _, v in sorted(res.items()) for life in minds(v)[0]]


def numbers(ls):
    keys = sorted({k for m in ls for k, v in m.items() if isinstance(v, (int, float)) and not isinstance(v, bool)})
    r = {k: mean([m.get(k) for m in ls]) for k in keys if not k.startswith(SKIP)}
    return {k: v for k, v in r.items() if v is not None}


def world_measures(res):
    """What the world shows late in life (harm, avoidance, edge...), the mean over conditions of each one's mean."""
    keys = sorted({k for v in res.values() for k in v["mean"] if k.startswith("late_")})
    r = {k[5:]: mean([v["mean"].get(k) for v in res.values()]) for k in keys}
    return {f"world_{k}": v for k, v in r.items() if v is not None}


def main():
    out = {}
    for world, label in WORLDS.items():
        got = {}
        for run, what in RUNS.items():
            path = HERE / f"{world}_{run}_results.json"
            if not path.exists():
                continue
            res = json.loads(path.read_text())
            got[run] = ls = lives(res)
            r = numbers(ls)
            r["lives"] = len(ls)
            r.update(world_measures(res))
            out[f"{label} · {what}"] = {"mean": r}
            show = {k: round(v, 3) for k, v in r.items() if k.startswith(("doing_", "told_ahead_doing", "told_from_acts", "told_ahead_words", "habit_share", "world_", "intentions", "body_read"))}
            print(f"{label:16} {what:34} lives={len(ls)}", show)
        for a, b in PAIRS:
            if a not in got or b not in got or len(got[a]) != len(got[b]):
                continue
            for k in PAIRED:
                d = np.array([x[k] - y[k] for x, y in zip(got[a], got[b])
                              if x.get(k) is not None and y.get(k) is not None], float)
                if len(d) > 1:
                    p = {"diff": float(d.mean()), "se": float(d.std(ddof=1) / np.sqrt(len(d))), "n": len(d)}
                    out[f"{label} · paired {k}: {RUNS[a]} − {RUNS[b]}"] = {"mean": p}
                    print(f"{'':16} paired {k}: {a} - {b}: {p['diff']:+.3f} ± {p['se']:.3f} (n={p['n']})")
    (HERE / "doing_summary_results.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
