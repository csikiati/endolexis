"""Experiments 8 and 9, framed for the laptop body.

Experiment 8 - a richer night.
  A laptop's night is not empty: scheduled jobs (updates, backups) spin the fan and warm the body in
  the dark, a hall light flicks on, and there are inner warmth surges with no outer cause. The best
  mind (forgets + doubt, restless childhood then patient) lives 20 days with its lid open at night,
  so it can learn the night's own words, then sleeps 10 nights. Nights: plain (only inner surges) or
  rich (+ night jobs and flashes); sleep: sealed, or a trickle of 5% or 20% of the outer world.
  Question: does a trickle in a rich night give dream-like readings, shifting and through the wrong
  world, where a trickle in a plain night stayed faithful (experiment 5)?

Experiment 9 - housekeeping in sleep, and something new in later life.
  The vocabulary fills in the first few hundred moments of life with infancy words that are rarely
  used again. From day 20, a charger appears: the light flickers in a pattern never sensed before,
  and charge rises fast. Olvaso sleeps sealed every night; with housekeeping, each waking retires
  words not met for 5 days that were used fewer than 200 times, and merges near-identical words that
  mean the same. Question: can it still learn something new late in life, and at what cost?
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # run from a clone without installing
import numpy as np
from endolexis.toyworld import ToyWorld, Collector, Olvaso, SENSED, FELT

DAY, LID_CLOSE, LID_OPEN, ASLEEP_AFTER = 1000, 550, 950, 60
BEST = dict(memory=300, doubt_memory=3000, doubt_limit=0.1)
NIGHT = {"plain": dict(night_heat=0.004), "rich": dict(night_heat=0.004, night_jobs=0.002, night_flashes=0.002)}


class Words:
    """The observer's notes on each word slot (reset when a slot is reborn)."""
    def __init__(self, n):
        self.occ, self.day, self.act, self.chg = (np.zeros(n) for _ in range(4))
        self.born = np.zeros(n, dtype=int)

    def note(self, olv, t, truth):
        if not olv.history or olv.history[0] < 0:
            return
        w = olv.history[0]
        if olv.word_uses[w] == 1:                     # just born (or reborn in a freed slot)
            self.occ[w] = self.day[w] = self.act[w] = self.chg[w] = 0
            self.born[w] = t
        self.occ[w] += 1
        self.day[w] += truth["day"]
        self.act[w] += truth["activity"]
        self.chg[w] += truth.get("charging", False)

    def share(self, a):
        return a / np.maximum(self.occ, 1)


def awake(world, col, olv, b, notes, t):
    s, f, truth = world.step(b)
    b, r = olv.live(*col.anonymise(s, f))
    notes.note(olv, t, truth)
    return b, r, truth


# --- experiment 8 ----------------------------------------------------------------
def night_life(seed, night, trickle):
    world = ToyWorld(seed=seed, **NIGHT[night])
    col = Collector(len(SENSED), len(FELT), seed=seed)
    olv = Olvaso(len(SENSED), len(FELT), threshold=20.0, seed=seed, **BEST)
    notes, leak = Words(olv.max_words), np.random.default_rng(seed + 777)
    aw = list(col.felt_perm).index(FELT.index("warmth"))
    b, t = None, 0
    for t in range(20 * DAY):
        if t == 10 * DAY:
            olv.threshold = 250.0
        b, _, _ = awake(world, col, olv, b, notes, t)
    day_w = notes.share(notes.day) > 0.3
    busy_w = notes.share(notes.act) > 0.2
    active_w = notes.share(notes.act) > 0.1
    known = notes.occ >= 10
    m = dict(ticks=0, reads=0, wrong=0, switch=0, base=0, job=0, job_read=0, job_right=0, surge=0, surge_read=0, surge_wrong=0)
    last_act = last_job = -10**9
    for t in range(20 * DAY, 30 * DAY):
        tick = t % DAY
        if not (LID_CLOSE <= tick < LID_OPEN):
            b, _, _ = awake(world, col, olv, b, notes, t)
            continue
        s, f, truth = world.step(None)
        sa, fa = col.anonymise(s, f)
        r, _ = olv.sleep_moment(fa, sa if (trickle and leak.random() < trickle) else None)
        if truth["activity"]:
            last_act = t
        if truth["night_job"]:
            last_job = t
        k = tick - LID_CLOSE
        if k == 0:
            prev = np.full(olv.nf, -1)
        if k >= ASLEEP_AFTER:
            m["ticks"] += 1
            quiet = t - last_act > 30
            for d in range(olv.nf):
                w = r[d]
                if w >= 0:
                    m["reads"] += 1
                    m["wrong"] += int(known[w] and ((day_w[w] and truth["day"] < 0.05) or (busy_w[w] and quiet)))
                    if prev[d] >= 0:
                        m["base"] += 1
                        m["switch"] += int(prev[d] != w)
            warm = truth["warmth"] > 0.3
            if warm and t - last_job < 80:            # warm because of a real night job
                m["job"] += 1
                m["job_read"] += int(r[aw] >= 0)
                m["job_right"] += int(r[aw] >= 0 and active_w[r[aw]])
            elif warm and t - last_act > 80:          # warm with no outer cause
                m["surge"] += 1
                m["surge_read"] += int(r[aw] >= 0)
                m["surge_wrong"] += int(r[aw] >= 0 and known[r[aw]] and busy_w[r[aw]])
        prev = r
    q = lambda a, b: m[a] / m[b] if m[b] else None
    return {"read": m["reads"] / (3 * max(m["ticks"], 1)), "wrong_world": q("wrong", "reads"),
            "switch_rate": q("switch", "base"), "job_warmth_read": q("job_read", "job"),
            "job_warmth_read_via_activity": q("job_right", "job_read"),
            "surge_read": q("surge_read", "surge"), "surge_read_busy_word": q("surge_wrong", "surge_read")}


# --- experiment 9 ----------------------------------------------------------------
def words_life(seed, housekeeping, days=40, charger_from=20, mind=None, charger_strength=1.0):
    world = ToyWorld(seed=seed, charger_from=charger_from, charger_strength=charger_strength)
    col = Collector(len(SENSED), len(FELT), seed=seed)
    olv = Olvaso(len(SENSED), len(FELT), threshold=20.0, seed=seed, **(mind or BEST))
    notes = Words(olv.max_words)
    ac = list(col.felt_perm).index(FELT.index("charge"))
    ad = list(col.felt_perm).index(FELT.index("drift"))
    aw = list(col.felt_perm).index(FELT.index("warmth"))
    b = None
    retired = merged = 0
    alive_at = {}
    rows = []   # (day, charging, charge reading, drift read, warm, warmth reading, active recently)
    last_act = -10**9
    for t in range(days * DAY):
        day, tick = divmod(t, DAY)
        if tick == 0:
            if day == 10:
                olv.threshold = 250.0
            alive_at[day] = int(olv.alive.sum())
        if tick == LID_OPEN and housekeeping and day >= 1:
            a, m = olv.housekeeping()
            retired += a
            merged += m
        if day >= 1 and LID_CLOSE <= tick < LID_OPEN:
            s, f, _ = world.step(None)
            olv.sleep_moment(col.anonymise(s, f)[1])
            continue
        b, r, truth = awake(world, col, olv, b, notes, t)
        if truth["activity"]:
            last_act = t
        rd = lambda a: r[a] if r[a] >= 0 or len(r) == 3 else r[a + 3]   # level, else its felt change
        rows.append((day, truth["charging"], rd(ac), rd(ad) >= 0, truth["warmth"] > 0.3, rd(aw), t - last_act < 80))
    charger_word = (notes.share(notes.chg) > 0.5) & (notes.occ >= 10)
    new_charger_words = int((charger_word & (notes.born >= charger_from * DAY)).sum())
    active = notes.share(notes.act) > 0.1
    late = [x for x in rows if x[0] >= charger_from + 5]
    chg = [x for x in late if x[1]]
    warm = [x for x in late if x[4] and not x[1]]
    chg_warm = [x for x in chg if x[4] and not x[6]]     # warm only because the battery charges
    pick = lambda xs, f: float(np.mean([f(x) for x in xs])) if xs else None
    return {
        "words_alive_day20": alive_at.get(20), "words_alive_day39": alive_at.get(days - 1),
        "retired": retired, "merged": merged, "charger_words": int(charger_word.sum()),
        "new_charger_words": new_charger_words,
        "charging_charge_read": float(np.mean([x[2] >= 0 for x in chg])) if chg else None,
        "charging_read_via_charger_word": float(np.mean([x[2] >= 0 and charger_word[x[2]] for x in chg])) if chg else None,
        "charging_warmth_read": pick(chg_warm, lambda x: x[5] >= 0),
        "charging_warmth_via_charger_word": pick(chg_warm, lambda x: x[5] >= 0 and charger_word[x[5]]),
        "charging_warmth_via_activity_word": pick(chg_warm, lambda x: x[5] >= 0 and active[x[5]] and not charger_word[x[5]]),
        "warm_via_activity_late": pick(warm, lambda x: x[5] >= 0 and active[x[5]]),
        "drift_read": float(np.mean([x[3] for x in rows if x[0] >= 3])),
    }


def mean_of(lives):
    return {k: (float(np.mean([l[k] for l in lives if l[k] is not None])) if any(l[k] is not None for l in lives) else None)
            for k in lives[0]}


def main(seeds=(1, 2, 3, 4, 5), which=("night", "words")):
    out = {}
    fmt = lambda d: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()}
    if "night" in which:
        out["night"] = {}
        for night in ("plain", "rich"):
            for trickle in (0.0, 0.05, 0.2):
                name = f"{night} night, " + ("sealed" if not trickle else f"trickle {int(trickle * 100)}%")
                lives = [night_life(s, night, trickle) for s in seeds]
                out["night"][name] = {"lives": lives, "mean": mean_of(lives)}
                print(name, fmt(mean_of(lives)), flush=True)
    if "words" in which:
        out["words"] = {}
        for hk in (False, True):
            name = "housekeeping" if hk else "no housekeeping"
            lives = [words_life(s, hk) for s in seeds]
            out["words"][name] = {"lives": lives, "mean": mean_of(lives)}
            print(name, fmt(mean_of(lives)), flush=True)
            for s, l in zip(seeds, lives):
                print("   seed", s, fmt(l), flush=True)
    tag = "_".join(which)
    Path(__file__).with_name(f"night_and_words_{tag}.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    which = [w for w in ("night", "words") if w in sys.argv] or ["night", "words"]
    main((2,) if quick else (1, 2, 3, 4, 5), which)
