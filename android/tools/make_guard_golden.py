"""Record the Python guard engine's decisions on random cases, for the Kotlin guards to replay (GuardsTest).

python android/tools/make_guard_golden.py  ->  app/src/test/resources/guards_golden.json
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np
from endolexis.studio import from_guard_template, guard_templates
from endolexis.toyworld.guards import decide

units = [json.loads(p.read_text()) for p in sorted((HERE.parent / "app/src/main/assets/guards").glob("*.json"))]
units += [from_guard_template(t) for t in guard_templates() if t["name"] != "blank"]
units += [json.loads(p.read_text()) for p in sorted((ROOT / "studio/examples/learned").glob("*.json"))]
units = list({u["name"]: u for u in units}.values())
hands = sorted({h for u in units for h in u["protects"] if h != "*"}) + ["paint"]
options = {"brightness": [0.0, 0.5, 1.0], "tone_loud": [300.0, 900.0], "tone_soft": [300.0, 900.0], "vibrate": [150.0, 600.0],
           "blade": ["slow", "fast"], "move": [-2.0, -1.0, 0.0, 1.0, 2.0], "speak": ["ba", "mo"], "post": [0.0, 1.0]}
rng = np.random.default_rng(7)
signals = ["warmth_c", "warmth_above_usual", "charge", "plugged", "busy", "recent", "active", "load", "warmth", "person",
           "person_distance", "hour", "talking", "lying", "buzzes_here", "light", "loudness"]
cases = []
for _ in range(3000):
    k = int(rng.integers(1, 5))
    sel = [units[int(i)] for i in rng.choice(len(units), k, replace=False)]
    hand = hands[int(rng.integers(len(hands)))]
    opts = options.get(hand, [0.0])
    opt = opts[int(rng.integers(len(opts)))]
    sig = {}
    for s in signals:
        if rng.random() < 0.08:
            continue                                  # missing: fails closed (or is ignored)
        sig[s] = {"warmth_c": rng.uniform(25, 45), "warmth_above_usual": rng.uniform(-1, 4), "charge": rng.uniform(0, 1),
                  "plugged": float(rng.integers(2)), "busy": rng.uniform(-1, 1), "recent": float(rng.integers(0, 8)),
                  "active": float(rng.integers(2)), "load": rng.uniform(0, 1), "warmth": rng.uniform(0, 1),
                  "person": float(rng.integers(2)), "person_distance": rng.choice([rng.uniform(0, 12), 99.0]),
                  "hour": rng.uniform(0, 24), "talking": float(rng.integers(2)), "lying": float(rng.integers(2)),
                  "buzzes_here": float(rng.integers(0, 40)), "light": rng.uniform(0, 0.5),
                  "loudness": rng.uniform(-70, -30)}[s]
        if s in ("person_distance", "warmth") and rng.random() < 0.5:
            sig[s + "@rate"] = rng.uniform(-1, 1) * (0.5 if s == "person_distance" else 0.05)
    ongoing = bool(rng.random() < 0.2)
    out, o, by, _ = decide(sel, hand, opt, sig, ongoing=ongoing)
    cases.append({"guards": [u["name"] for u in sel], "hand": hand, "option": opt, "signals": sig, "ongoing": ongoing,
                  "outcome": out, "to": o, "by": by})
out = HERE.parent / "app/src/test/resources/guards_golden.json"
out.write_text(json.dumps({"units": units, "cases": cases}))
print(out, len(cases), {o: sum(c["outcome"] == o for c in cases) for o in ("allow", "limit", "ask", "refuse", "stop")})
