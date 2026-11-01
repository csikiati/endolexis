"""Experiment 11: careful merging (doubt for merged meanings).

In experiment 10, feeling levels and changes raised superstition (noise read 2.8% -> 7.2%). It did
not come through the change dimensions: it came from housekeeping's merges. Two words were merged
when their meanings agreed on average, so one strong disagreement could hide among dimensions that
agree (and the near-zero change dimensions made that easy), and the merged word kept its old trust
although its pooled meaning was new. With careful=True, a merge must agree on every dimension, and
the merged meaning starts out doubted. A third option retires words but never merges them.
Same life as experiment 10 (realistic charger).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # run from a clone without installing
sys.path.insert(0, str(Path(__file__).resolve().parent))
import night_and_words as nw

BEST = nw.BEST
RUNS = {
    "levels, merging as before": dict(mind=dict(BEST), careful=False),
    "levels, careful merging": dict(mind=dict(BEST), careful=True),
    "levels + change, merging as before": dict(mind=dict(BEST, adapt=300, adapt_mode="both"), careful=False),
    "levels + change, careful merging": dict(mind=dict(BEST, adapt=300, adapt_mode="both"), careful=True),
    "levels, retiring only": dict(mind=dict(BEST), merge=False),
    "levels + change, retiring only": dict(mind=dict(BEST, adapt=300, adapt_mode="both"), merge=False),
}


def main(seeds=(1, 2, 3, 4, 5)):
    out = {}
    fmt = lambda d: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()}
    for name, cfg in RUNS.items():
        lives = [nw.words_life(s, True, charger_strength=3.0, **cfg) for s in seeds]
        out[name] = {"lives": lives, "mean": nw.mean_of(lives)}
        print(name, fmt(nw.mean_of(lives)), flush=True)
        print("   per life: drift", [round(l["drift_read"], 3) for l in lives],
              " charging via charger word", [round(l["charging_read_via_charger_word"], 2) for l in lives], flush=True)
    Path(__file__).with_name("careful_merging_results.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main((2,) if "--quick" in sys.argv else (1, 2, 3, 4, 5))
