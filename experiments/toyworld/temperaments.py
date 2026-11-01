"""Experiment 1: four temperaments, several lives each, in the same toy world.

restless = acts at low pressure, patient = high, middle = in between, learning = finds its own.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # run from a clone without installing
import numpy as np
from endolexis.toyworld import live_a_life

TEMPERAMENTS = {
    "restless": dict(threshold=20.0, learn_threshold=False),
    "middle": dict(threshold=100.0, learn_threshold=False),
    "patient": dict(threshold=250.0, learn_threshold=False),
    "learning": dict(threshold=100.0, learn_threshold=True),
}


def main(seeds=(1, 2, 3), days=30):
    results = {}
    for name, cfg in TEMPERAMENTS.items():
        lives = [live_a_life(seed=s, days=days, **cfg) for s in seeds]
        results[name] = {"lives": lives,
                         "mean": {k: float(np.mean([l[k] for l in lives])) for k in lives[0]}}
        m = results[name]["mean"]
        print(f"{name:9s} warmth {m['read_warmth']:.2f}  charge {m['read_charge']:.2f}  "
              f"drift {m['read_drift']:.2f}  warm-via-activity {m['warm_read_via_activity_word']:.2f} "
              f"(chance {m['chance_activity_word']:.2f})  actions {m['actions']:.0f}  "
              f"self-caused words {m['self_caused_words']:.1f}  threshold {m['final_threshold']:.0f}")
    out = Path(__file__).with_name("temperaments_results.json")
    out.write_text(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    main()
