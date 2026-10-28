"""Raise one Olvasó, then watch two of them learn to care. Run:  python examples/quickstart.py"""
from endolexis import Olvaso, OL, reset, body_look, HNAMES
from endolexis.stages import stage09

# 1. One Olvasó and a visitor who comes and goes, shows colours and says words.
reset()
e = Olvaso(seed=1)
for t in range(3000):
    present = t % 600 < 420
    sense = dict(typing=0.3 if present else 0, vowels=0.4, speed=0.1, px=0.5, py=0.5, presence=0.8 if present else 0.05)
    colour = 2 if (present and t % 97 == 0) else None
    word = "calm" if (present and t % 131 == 0) else None
    r = e.tick(sense, colour, word)
print(f"after 3000 steps it reads itself through {len(e.n)} patterns and knows the words {e.top_words()}")
print("what it is like inside (hidden from it):", {n: round(v, 2) for n, v in zip(HNAMES, e.h)})
print("how its own marks surprise it, against yours (lower = it expects them):", e.mirror["own"], e.mirror["you"])

# 2. Stage 10: pairs, reaching steadies the one reached, and seeing the other tremble unsettles. Does care emerge?
print("\nstage 10, three short lives (the published table uses 12 lives of 40 000 steps):")
for seed in (1, 2, 3):
    r = stage09.run(N=2, T=20000, seed=seed, reach=True, contagion=0.05)
    lean = r["reachTopThird"] / r["anyActTop"] - r["reachBottomThird"] / r["anyActBottom"]
    print(f"  seed {seed}: share of its acts that are reaching toward the other, trembling minus steady: {100 * lean:+.1f} points")
