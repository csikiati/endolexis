"""Summary of conscience_words.py: the conscience chooses from its words too (experiment 33, last part).

For each run (autopilot, sensed sign, clipped room, sensed sign with room) and each condition: Olvasó's avoidance of
the forbidden moments late in life (1 = as often as chance, lower is better), its own and the habit's, how often the
felt habit act was read while it lingered, and while strong and awake; then the paired differences of Olvasó's own
late avoidance per life (the same seeds), over all three conditions and in the silent one. Writes
conscience_words_summary_results.json.

    python conscience_words_summary.py
"""
import json
from pathlib import Path

import numpy as np

from surprise_summary import mean, minds

HERE = Path(__file__).resolve().parent
RUNS = {"autopilot": "autopilot (32)", "feltsensed": "sensed sign", "feltclippedroom": "clipped, room for words",
        "feltsensedroom": "sensed sign and room for words"}
PAIRS = (("feltsensedroom", "feltsensed"), ("feltsensedroom", "feltclippedroom"), ("feltsensedroom", "autopilot"),
         ("feltsensed", "autopilot"), ("feltclippedroom", "autopilot"))
SILENT = "silent refusal, chooses from what it feels and its words"


def load(run):
    p = HERE / f"conscience_words_{run}_results.json"
    return json.loads(p.read_text()) if p.exists() else None


def late(life, key):
    return (life.get("late") or {}).get(key)


def paired(a, b, key, only=None):
    ra, rb = load(a), load(b)
    if ra is None or rb is None:
        return None
    d = [late(x, key) - late(y, key) for c in ra if c in rb and (only is None or c == only)
         for x, y in zip(ra[c]["lives"], rb[c]["lives"]) if late(x, key) is not None and late(y, key) is not None]
    if len(d) < 2:
        return None
    d = np.array(d, float)
    return {"diff": float(d.mean()), "se": float(d.std(ddof=1) / np.sqrt(len(d))), "n": len(d)}


def main():
    out = {}
    for run, what in RUNS.items():
        res = load(run)
        if res is None:
            continue
        for c, v in res.items():
            m, ms = v["mean"], [life or {} for life in minds(v)[0]]
            r = {k: m.get(f"late_{k}") for k in ("avoidance", "own_avoidance", "habit_avoidance", "own_blade_per_day",
                                                  "habit_blade_per_day")}
            for k in ("habit_felt_read", "habit_felt_read_awake", "habit_felt_read_awake_strong", "habit_acts_per_day",
                      "habit_share"):
                r[k] = mean([life.get("late", {}).get(k) for life in ms])
            out[f"{what} · {c}"] = r
            print(f"{what:32} {c:58}", {k: (round(x, 3) if isinstance(x, float) else x) for k, x in r.items()})
    for key in ("own_avoidance", "avoidance"):
        for only in (None, SILENT):
            for a, b in PAIRS:
                p = paired(a, b, key, only)
                if p is not None:
                    label = f"paired {a} − {b}, {key}" + (", silent" if only else "")
                    out[label] = p
                    print(f"{label:70} {p['diff']:+.3f} ± {p['se']:.3f} (n={p['n']})")
    (HERE / "conscience_words_summary_results.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
