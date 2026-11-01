"""Experiment 2: Olvasós that change temperament over a life.

childhood->patient : restless for the first 10 days, then patient
childhood->learning: restless for the first 10 days, then learns its own threshold
play-and-rest      : alternates restless and patient every 3 days, for life
compared with the fixed restless and patient temperaments of experiment 1.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # run from a clone without installing
import numpy as np
from endolexis.toyworld import live_a_life

RESTLESS, PATIENT = 20.0, 250.0

TEMPERAMENTS = {
    "restless": dict(threshold=RESTLESS),
    "patient": dict(threshold=PATIENT),
    "childhood->patient": dict(threshold=RESTLESS,
                               schedule=lambda d: (PATIENT, False) if d == 10 else None),
    "childhood->learning": dict(threshold=RESTLESS,
                                schedule=lambda d: (100.0, True) if d == 10 else None),
    "play-and-rest": dict(threshold=RESTLESS,
                          schedule=lambda d: ((RESTLESS if (d // 3) % 2 == 0 else PATIENT), False)),
}
KEYS = ["read_drift", "warm_read_via_activity_word", "late_read_charge", "self_caused_words",
        "actions", "final_threshold"]


def main(seeds=(1, 2, 3, 4, 5), days=30):
    results = {}
    print(f"{'':20s} drift  warm-via-act  charge(late)  I-did-that  actions  threshold")
    for name, cfg in TEMPERAMENTS.items():
        lives = [live_a_life(seed=s, days=days, **cfg) for s in seeds]
        mean = {k: float(np.mean([l[k] for l in lives])) for k in lives[0]}
        results[name] = {"lives": lives, "mean": mean}
        print(f"{name:20s} {mean['read_drift']:.2f}   {mean['warm_read_via_activity_word']:.2f}"
              f"          {mean['late_read_charge']:.2f}          {mean['self_caused_words']:5.1f}"
              f"   {mean['actions']:6.0f}   {mean['final_threshold']:5.0f}")
        print(" " * 20, "per life charge(late):",
              [round(l["late_read_charge"], 2) for l in lives],
              " I-did-that:", [l["self_caused_words"] for l in lives])
    Path(__file__).with_name("growing_up_results.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
