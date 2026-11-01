"""Experiment 4: forgetting with doubt.

Each meaning has a fast memory (memory=300: what the word means now) and a slow doubt memory
(doubt_memory=3000: how much that meaning has wandered). A word reads only if its meaning is both
consistent now and has stopped wandering (doubt below doubt_limit).
Compares: never forgets / forgets / forgets with doubt, for three temperaments.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # run from a clone without installing
import numpy as np
from endolexis.toyworld import live_a_life

R, P = 20.0, 250.0
TEMPERAMENTS = {
    "restless": dict(threshold=R),
    "patient": dict(threshold=P),
    "childhood->patient": dict(threshold=R, schedule=lambda d: (P, False) if d == 10 else None),
}
MINDS = {
    "never forgets": dict(),
    "forgets": dict(memory=300),
    "forgets + doubt": dict(memory=300, doubt_memory=3000, doubt_limit=0.1),
}


def main(seeds=(1, 2, 3, 4, 5), days=30):
    results = {}
    for mind, mcfg in MINDS.items():
        for name, tcfg in TEMPERAMENTS.items():
            lives = [live_a_life(seed=s, days=days, **tcfg, **mcfg) for s in seeds]
            mean = {k: float(np.mean([l[k] for l in lives])) for k in lives[0]}
            results[f"{mind} | {name}"] = {"lives": lives, "mean": mean}
            print(f"{mind:16s} {name:20s} drift {mean['read_drift']:.2f}  "
                  f"warm-via-activity {mean['warm_read_via_activity_word']:.2f}  "
                  f"charge(late) {mean['late_read_charge']:.2f}  "
                  f"I-did-that {mean['self_caused_words']:.1f}", flush=True)
    Path(__file__).with_name("doubt_results.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main(*(((1,), 12) if "--quick" in sys.argv else ()))
