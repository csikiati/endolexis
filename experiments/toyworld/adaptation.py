"""Experiment 10: sensory adaptation (habituation).

Olvaso reads inner *levels*, so the charger's main effect, charge rising, could not be read: the
level while charging can be anything. Following the observation that a mind senses change better
than a steady value, and in time disregards what stays the same, each inner state is felt against
its own recent baseline, which slowly catches up (time constant `adapt`, in moments).

Same life as experiment 9 (charger from day 20, sealed nights, housekeeping on), but with a realistic
charger that refills three times faster than daylight (in experiment 9 it matched daylight, so its
change did not stand out). Five minds:
levels (as before) | adapted, fast / medium / slow | levels and adapted side by side.
A reading counts for an inner state if it reads its level or its adapted (change) dimension.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # run from a clone without installing
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import night_and_words as nw

BEST = nw.BEST
MINDS = {
    "levels": dict(BEST),
    "adapted, fast (100)": dict(BEST, adapt=100),
    "adapted, medium (300)": dict(BEST, adapt=300),
    "adapted, slow (1000)": dict(BEST, adapt=1000),
    "levels + adapted (300)": dict(BEST, adapt=300, adapt_mode="both"),
}


def main(seeds=(1, 2, 3, 4, 5)):
    out = {}
    fmt = lambda d: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()}
    for name, mind in MINDS.items():
        lives = [nw.words_life(s, True, mind=mind, charger_strength=3.0) for s in seeds]
        out[name] = {"lives": lives, "mean": nw.mean_of(lives)}
        print(name, fmt(nw.mean_of(lives)), flush=True)
    Path(__file__).with_name("adaptation_results.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main((2,) if "--quick" in sys.argv else (1, 2, 3, 4, 5))
