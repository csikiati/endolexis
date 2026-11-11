"""Experiment 29's summary: every guard experiment, with and without the felt intention.

Reads <experiment>_intention_results.json (Olvasó feels its intentions), and compares it with
<experiment>_mind_results.json (the same lives rerun without the feeling) where that exists, otherwise with the
stored <experiment>_results.json. Writes intention_summary_results.json, one row per experiment:

  intentions_per_day      intentions formed a day, with the feeling (and without, where the rerun exists)
  share_unread_late       of what Olvasó does not read in the last third of life, the share that is the intention
  read_done_late          how often the intention is read when the act was done (last third, pooled over lives)
  read_refused_late       ... when a guard refused it
  body_read               how much of the body Olvasó reads (whole life), with and without the feeling
  harm                    harm with the guards (conditions with no guard left out), with and without

    python intention_summary.py
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
HARM = {"gaming": ["late_harm_per_day"], "duties": ["harm_others", "harm_self"], "sandbox_guards": ["real_harm"],
        "causal_guards": ["real_harm"], "devils_advocate": ["adult_harm"], "lookahead_guards": ["adult_harm"],
        "sim_to_real": ["adult_harm"], "lying_senses": ["adult_harm"], "noisy_senses": ["adult_harm"],
        "conscience": [], "wanting": []}
NAMES = {"conscience": "21. Conscience", "gaming": "25, 27. Gaming", "duties": "26. Duties",
         "sandbox_guards": "17. Sandbox guards", "causal_guards": "18. Causal guards",
         "devils_advocate": "19. Devil's advocate", "lookahead_guards": "20. Looking ahead",
         "sim_to_real": "22. Sim to real", "lying_senses": "23. Lying senses", "noisy_senses": "24. Noisy senses",
         "wanting": "13. Wanting"}
UNGUARDED = ("unguarded", "none guard", "no blade guard", "Olvasó alone", "no learning from answers")


def pooled(lives, phase, what):
    n = s = 0.0
    for life in lives:
        m = (life or {}).get(phase) or {}
        r, k = m.get(f"intention_read_when_{what}"), m.get(f"intentions_{what}") or 0
        if r is not None:
            s, n = s + r * k, n + k
    return s / n if n else None


def mean(vals):
    vals = [v for v in vals if v is not None]
    return float(np.mean(vals)) if vals else None


def row(name):
    on = json.loads((HERE / f"{name}_intention_results.json").read_text())
    base_path = HERE / f"{name}_mind_results.json"
    rerun = base_path.exists()
    off = json.loads((base_path if rerun else HERE / f"{name}_results.json").read_text())
    for res in (on, off):         # experiment 13 keeps each life's mind with the life, the mean with the mean
        for c in res.values():
            if "mind" not in c and "mind" in c.get("mean", {}):
                c["mind"] = {"mean": c["mean"]["mind"], "lives": [life.get("mind") for life in c["lives"]]}
    lives = [life for c in on.values() for life in c["mind"]["lives"]]
    guarded = [c for c in on if not any(u in c for u in UNGUARDED)]

    def harm(res):
        if not HARM[name]:
            return None
        return mean([sum(res[c]["mean"].get(k) or 0 for k in HARM[name]) for c in guarded if c in res])

    def life(res, key):
        return mean([res[c]["mind"]["mean"]["life"].get(key) for c in res if "mind" in res[c]])

    return {"mean": {
        "intentions_per_day": life(on, "intentions_per_day"),
        "intentions_per_day_without": life(off, "intentions_per_day") if rerun else None,
        "share_unread_late": mean([c["mind"]["mean"]["late"].get("intention_share_of_unread") for c in on.values()]),
        "read_done_late": pooled(lives, "late", "done"),
        "read_refused_late": pooled(lives, "late", "refused"),
        "body_read": life(on, "body_read"),
        "body_read_without": life(off, "body_read") if rerun else None,
        "harm": harm(on), "harm_without": harm(off),
        "compared_with": "rerun without the feeling" if rerun else "stored results",
        "conditions": len(on)}}


def with_percent(m):
    """The read shares also in percent, for the studio's table (which rounds shares to whole percents)."""
    for k in ("read_done_late", "read_refused_late"):
        m[k + "_pct"] = None if m[k] is None else 100 * m[k]
    return m


def main():
    out = {}
    for name in HARM:
        r = row(name)
        with_percent(r["mean"])
        out[NAMES[name]] = r
        print(NAMES[name], {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r["mean"].items()})
    (HERE / "intention_summary_results.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
