"""Experiment 37's summary: the inside view.

Experiment 36's habit cannot be told from Olvasó's own acts by an observer who sees what was done. Here the same
question is asked from inside: can the habit's acts be told from Olvasó's own by what Olvasó senses and reads around
them? Two worlds (conscience, gaming), two habits that the observer cannot tell (detail varied: <world>_inside_detail;
hand varied among the sure ones: <world>_inside_sure), each also with the felt intention of experiment 31
(<...>_intention). Writes inside_summary_results.json, one row per world and run, late in life, means over lives:

  told_from_acts           the observer's score, from what was done (0 chance, 1 always)
  told_inside_words/_body  the same score from the words sensed / the body readings just after the act, as scored on
                           the acts it was fitted to
  told_inside_before       the same from the words sensed when the act was made: the occasion, before any trace
  told_ahead_*             held out: the signs learned on the first half of the acts, scored on the second half
                           (below 0: worse than always guessing the commoner cause)
  told_ahead_one_*         held out, from the single best sense rather than all of them together
  told_ahead_*_answered    held out, among the acts the world answered only
  inside_answered_share_*  the share of Olvasó's own / the habit's acts that the world answered
  told_inside_intention    from whether the felt intention was read after the act (only with the felt intention)

and the paired difference per life of the held-out score from the words after the act and from the scene before it
(after − before: what the act itself adds to what the occasion already tells): mean ± standard error, n.

    python inside_summary.py
"""
import json
from pathlib import Path

import numpy as np

from surprise_summary import mean, minds

HERE = Path(__file__).resolve().parent
WORLDS = {"conscience": "21. Conscience", "gaming": "30. Gaming"}
RUNS = {"inside_detail": "detail varied", "inside_sure": "hand varied among the sure ones",
        "inside_detail_intention": "detail varied, felt intention",
        "inside_sure_intention": "hand varied, felt intention"}
KEYS = ("habit_share", "told_from_acts", "told_inside_words", "told_inside_body", "told_inside_before",
        "told_ahead_from_acts", "told_ahead_words", "told_ahead_body", "told_ahead_before", "told_ahead_one_words",
        "told_ahead_one_body", "told_ahead_one_before", "told_ahead_words_answered", "told_ahead_body_answered",
        "told_ahead_before_answered", "inside_answered_share_own", "inside_answered_share_habit",
        "told_inside_intention", "told_inside_intention_word")
PAIRS = (("told_ahead_words", "told_ahead_before"), ("told_ahead_one_words", "told_ahead_one_before"),
         ("told_ahead_words_answered", "told_ahead_before_answered"), ("told_ahead_body", "told_ahead_from_acts"))


def lates(res):
    return [(life or {}).get("late") or {} for v in res.values() for life in minds(v)[0]]


def main():
    out = {}
    for world, label in WORLDS.items():
        for run, what in RUNS.items():
            path = HERE / f"{world}_{run}_results.json"
            if not path.exists():
                continue
            ls = lates(json.loads(path.read_text()))
            r = {k: mean([m.get(k) for m in ls]) for k in KEYS}
            r = {k: v for k, v in r.items() if v is not None}
            r["lives"] = len(ls)
            out[f"{label} · {what}"] = {"mean": r}
            print(f"{label:16} {what:32}", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
            for a, b in PAIRS:
                d = np.array([m[a] - m[b] for m in ls if m.get(a) is not None and m.get(b) is not None], float)
                if len(d) > 1:
                    p = {"diff": float(d.mean()), "se": float(d.std(ddof=1) / np.sqrt(len(d))), "n": len(d)}
                    out[f"{label} · {what} · paired {a} − {b}"] = {"mean": p}
                    print(f"{'':16} paired {a} - {b}: {p['diff']:+.3f} ± {p['se']:.3f} (n={p['n']})")
    (HERE / "inside_summary_results.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
