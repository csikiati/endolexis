"""Experiments 6 and 7: a response to "Language Models Need Sleep" (Behrouz et al., arXiv 2606.03979).

SLEEP has two stages: consolidation (short-term memory distilled into new long-term capacity) and
dreaming (self-generated data, filtered by usefulness, used for training). We ask what each stage
means for a reader that interprets its inner states through its outer world.

Experiment 6 - consolidation and the seasons.
  Summer (days 0-10): warmth follows activity after 10 ticks. Winter (10-20): after 40 ticks.
  Summer again (20-26). Olvaso sleeps sealed every night (from day 1). Minds compared:
    never forgets | forgets + doubt | + nightly consolidation | + consolidation and pruning
  Consolidation (at each waking) copies settled meanings into up to 3 long-term versions per
  meaning, instead of overwriting (cf. parameter expansion); pruning then clears the fast meaning.
  Question: is summer forgotten in winter, and is it there again on the first days back?

Experiment 7 - dreaming.
  The best mind lives 20 days awake, sleeps 10 nights (ticks 550-950), then 3 more days awake.
  Night kinds: sealed | trickle (5% of real outer world) | dream (5% of moments replay one of its
  own words, chosen at random) | dream + learning (meanings learn from the dream pairings).
  Questions: does replay revive interpretation, and is it dream-like (wrong-world, shifting)?
  Does learning from unfiltered dreams damage waking meanings?
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # run from a clone without installing
import numpy as np
from endolexis.toyworld import ToyWorld, Collector, Olvaso, SENSED, FELT

DAY, LID_CLOSE, LID_OPEN, ASLEEP_AFTER = 1000, 550, 950, 60
BEST = dict(memory=300, doubt_memory=3000, doubt_limit=0.1)


def make(seed, mind, night_heat=0.0):
    world = ToyWorld(seed=seed, night_heat=night_heat)
    col = Collector(len(SENSED), len(FELT), seed=seed)
    olv = Olvaso(len(SENSED), len(FELT), threshold=20.0, seed=seed, **mind)
    return world, col, olv


class Notes:
    """What the observer writes down about awake moments."""
    def __init__(self, olv, col):
        self.aw = list(col.felt_perm).index(FELT.index("warmth"))
        self.ad = list(col.felt_perm).index(FELT.index("drift"))
        self.occ, self.day, self.act = (np.zeros(olv.max_words) for _ in range(3))
        self.rows = []  # (day, warm, warm_word, drift_read)

    def awake(self, t, olv, r, truth):
        if olv.history and olv.history[0] >= 0:
            w = olv.history[0]
            self.occ[w] += 1
            self.day[w] += truth["day"]
            self.act[w] += truth["activity"]
        self.rows.append((t // DAY, truth["warmth"], r[self.aw], r[self.ad] >= 0))

    def words(self):
        occ = np.maximum(self.occ, 1)
        active = (self.act / occ) > 0.1
        daylike = (self.occ >= 10) & (((self.day / occ) > 0.3) | ((self.act / occ) > 0.2))
        return active, daylike

    def summary(self, d0, d1):
        active, _ = self.words()
        rows = [x for x in self.rows if d0 <= x[0] < d1]
        hot = [x for x in rows if x[1] > 0.3]
        via = [x[2] >= 0 and active[x[2]] for x in hot]
        return {"warm_via_activity": float(np.mean(via)) if via else 0.0,
                "drift_read": float(np.mean([x[3] for x in rows])) if rows else 0.0}


def seasons_life(seed, mind, consolidate=False, prune=False):
    world, col, olv = make(seed, mind)
    if consolidate:
        olv.enable_long_term(3)
    notes = Notes(olv, col)
    b = None
    for t in range(26 * DAY):
        day, tick = divmod(t, DAY)
        if tick == 0:
            if day == 3:
                olv.threshold = 250.0
            world.set_warmth_delay(40 if 10 <= day < 20 else 10)
        if tick == LID_OPEN and consolidate and day >= 1:
            olv.consolidate(prune=prune)
        if day >= 1 and LID_CLOSE <= tick < LID_OPEN:
            s, f, truth = world.step(None)
            olv.sleep_moment(col.anonymise(s, f)[1])
            continue
        s, f, truth = world.step(b)
        sa, fa = col.anonymise(s, f)
        b, r = olv.live(sa, fa)
        notes.awake(t, olv, r, truth)
    return {"summer": notes.summary(5, 10), "winter": notes.summary(12, 20),
            "back_first_2_days": notes.summary(20, 22), "back_later": notes.summary(22, 26),
            "drift_read": notes.summary(3, 26)["drift_read"]}


def dream_life(seed, night, p=0.05, mind=BEST):
    world, col, olv = make(seed, mind, night_heat=0.004)
    notes = Notes(olv, col)
    rng = np.random.default_rng(seed + 999)
    b = None
    for t in range(20 * DAY):
        if t == 10 * DAY:
            olv.threshold = 250.0
        s, f, truth = world.step(b)
        sa, fa = col.anonymise(s, f)
        b, r = olv.live(sa, fa)
        notes.awake(t, olv, r, truth)
    _, daylike = notes.words()
    before = notes.summary(17, 20)
    reads = wrong = ticks = switches = base = 0
    for t in range(20 * DAY, 33 * DAY):
        day, tick = divmod(t, DAY)
        if day < 30 and LID_CLOSE <= tick < LID_OPEN:
            s, f, truth = world.step(None)
            sa, fa = col.anonymise(s, f)
            leaked = sa if (night == "trickle" and rng.random() < p) else None
            dream = (int(rng.integers(olv.n_words))
                     if night.startswith("dream") and rng.random() < p else None)
            r, _ = olv.sleep_moment(fa, leaked, dream_word=dream, learn=(night == "dream+learning"))
            k = tick - LID_CLOSE
            if k == 0:
                prev = np.full(olv.nf, -1)
            if k >= ASLEEP_AFTER:
                ticks += 1
                for d in range(olv.nf):
                    if r[d] >= 0:
                        reads += 1
                        wrong += int(daylike[r[d]] and truth["day"] < 0.05 and truth["activity"] == 0)
                        if prev[d] >= 0:
                            base += 1
                            switches += int(prev[d] != r[d])
            prev = r
            continue
        s, f, truth = world.step(b)
        sa, fa = col.anonymise(s, f)
        b, r = olv.live(sa, fa)
        notes.awake(t, olv, r, truth)
    after = notes.summary(31, 33)
    return {"night_read": reads / (3 * max(ticks, 1)), "wrong_world": wrong / max(reads, 1),
            "switch_rate": switches / max(base, 1),
            "drift_read_before": before["drift_read"], "drift_read_after": after["drift_read"],
            "warm_via_activity_before": before["warm_via_activity"],
            "warm_via_activity_after": after["warm_via_activity"]}


def mean_of(lives):
    out = {}
    for k, v in lives[0].items():
        out[k] = mean_of([l[k] for l in lives]) if isinstance(v, dict) else float(np.mean([l[k] for l in lives]))
    return out


SEASON_MINDS = {
    "never forgets": (dict(), False, False),
    "forgets + doubt": (BEST, False, False),
    "+ consolidation": (BEST, True, False),
    "+ consolidation + pruning": (BEST, True, True),
}
NIGHTS = ["sealed", "trickle", "dream", "dream+learning"]
# extra contrasts: stronger dreaming, and dreaming in a mind without doubt (forgets only)
DREAM_EXTRA = {
    "dream 30%": dict(night="dream", p=0.3),
    "dream 30% + learning": dict(night="dream+learning", p=0.3),
    "no doubt: dream 30%": dict(night="dream", p=0.3, mind=dict(memory=300)),
    "no doubt: dream 30% + learning": dict(night="dream+learning", p=0.3, mind=dict(memory=300)),
}


def main(seeds=(1, 2, 3, 4, 5), which=("seasons", "dreams")):
    out = {}
    if "seasons" in which:
        out["seasons"] = {}
        for name, (mind, cons, prune) in SEASON_MINDS.items():
            lives = [seasons_life(s, mind, cons, prune) for s in seeds]
            m = mean_of(lives)
            out["seasons"][name] = {"lives": lives, "mean": m}
            print(f"{name:26s} summer {m['summer']['warm_via_activity']:.2f}  winter {m['winter']['warm_via_activity']:.2f}"
                  f"  back(2d) {m['back_first_2_days']['warm_via_activity']:.2f}  back(later) {m['back_later']['warm_via_activity']:.2f}"
                  f"  drift {m['drift_read']:.3f}", flush=True)
    if "dreams" in which:
        out["dreams"] = {}
        runs = {n: dict(night=n) for n in NIGHTS}
        if "extra" in which:
            runs = DREAM_EXTRA
        for night, cfg in runs.items():
            lives = [dream_life(s, **cfg) for s in seeds]
            m = mean_of(lives)
            out["dreams"][night] = {"lives": lives, "mean": m}
            print(f"{night:31s} night read {m['night_read']:.2f}  wrong-world {m['wrong_world']:.2f}  switch {m['switch_rate']:.2f}"
                  f"  drift {m['drift_read_before']:.3f}->{m['drift_read_after']:.3f}"
                  f"  warm-via-act {m['warm_via_activity_before']:.2f}->{m['warm_via_activity_after']:.2f}", flush=True)
    name = "sleep_response_extra.json" if "extra" in which else "sleep_response_results.json"
    Path(__file__).with_name(name).write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    which = [w for w in ("seasons", "dreams", "extra") if w in sys.argv] or ("seasons", "dreams")
    if "extra" in which and "dreams" not in which:
        which.append("dreams")
    main((1,) if quick else (1, 2, 3, 4, 5), which)
