"""Experiment 5: the dream test.

The world has inner night events: occasional warmth surges in the dark with no outer cause.

An Olvasó (forgets + doubt, restless childhood then patient) lives 20 days awake. Then for 10 days its
lid is closed every night (ticks 550-950 of each 1000-tick day). Three kinds of night:
  open    - control: lid stays open, the night is sensed normally
  sealed  - nothing sensed at all
  trickle - each moment, a fragment of the outer world leaks through with probability 5%
Felt states keep changing all night in every condition.

At each waking, Olvasó tries to read felt states it kept from the night (one every 25 ticks) with the
words of the first 60 morning ticks: its "dream report". The same night is replayed with two different
mornings, a quiet one and a busy one (someone starts using the machine at waking), to see whether
the report depends on the morning.

Theory under test (Endolexis): without outer input, inner states get no interpretation; a trickle of
input gives unstable, wrong-world interpretations; recall is composed at waking from morning cues.
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # run from a clone without installing
import numpy as np
from endolexis.toyworld import ToyWorld, Collector, Olvaso, SENSED, FELT

DAY = 1000
LID_CLOSE, LID_OPEN = 550, 950
MORNING = 60
NIGHT_HEAT = 0.004
ASLEEP_AFTER = 60   # the delay line still echoes the day for this many ticks
MIND = dict(memory=300, doubt_memory=3000, doubt_limit=0.1)


def awake(world, col, olv, b, stats=None):
    s, f, truth = world.step(b)
    sa, fa = col.anonymise(s, f)
    b, r = olv.live(sa, fa)
    if stats is not None and olv.history and olv.history[0] >= 0:
        w = olv.history[0]
        stats["occ"][w] += 1
        stats["day"][w] += truth["day"]
        stats["act"][w] += truth["activity"]
    return b, r, f, truth


def morning_report(world, col, olv, b, kept, busy=False):
    """Run the first morning ticks; for each kept night state, the first word that reads it."""
    if busy:
        world.burst_left = MORNING
    report = np.full((len(kept), olv.nf), -1)
    for _ in range(MORNING):
        b, *_ = awake(world, col, olv, b)
        for i, fz in enumerate(kept):
            r = olv.read_state(fz)
            fresh = (report[i] < 0) & (r >= 0)
            report[i][fresh] = r[fresh]
    return report, b


def one_life(seed, night, days_awake=20, nights=10, trickle=0.05):
    world = ToyWorld(seed=seed, night_heat=NIGHT_HEAT)
    col = Collector(len(SENSED), len(FELT), seed=seed)
    olv = Olvaso(len(SENSED), len(FELT), threshold=20.0, seed=seed, **MIND)
    anon_to_true = col.felt_perm
    leak = np.random.default_rng(seed + 777)
    stats = {k: np.zeros(olv.max_words) for k in ("occ", "day", "act")}
    b = None
    for t in range(days_awake * DAY):
        if t == 10 * DAY:
            olv.threshold = 250.0                      # childhood over
        b, *_ = awake(world, col, olv, b, stats)

    occ = np.maximum(stats["occ"], 1)
    word_day, word_act = stats["day"] / occ, stats["act"] / occ
    known = stats["occ"] >= 10
    daylike = known & ((word_day > 0.3) | (word_act > 0.2))   # words of a bright or busy world

    anon_warm = list(anon_to_true).index(FELT.index("warmth"))
    res = {"night_reads": np.zeros(3), "night_ticks": 0, "wrong_world": 0, "reads": 0,
           "switches": 0, "switch_base": 0, "recalled": {"quiet": [], "busy": []},
           "daylike_recall": {"quiet": [], "busy": []}, "agreement": [],
           "falling_asleep_reads": 0, "falling_asleep_ticks": 0,
           "event_ticks": 0, "event_read": 0, "event_wrong": 0}
    for n in range(nights):
        # awake part of the day, up to lid close
        while world.t % DAY != LID_CLOSE:
            b, *_ = awake(world, col, olv, b, stats)
        kept, prev = [], np.full(olv.nf, -1)
        for k in range(LID_OPEN - LID_CLOSE):
            if night == "open":
                b, r, f, truth = awake(world, col, olv, b)
                fz = olv.fnorm.z(col.anonymise(np.zeros(3), f)[1])
            else:
                s, f, truth = world.step(None)
                sa, fa = col.anonymise(s, f)
                leaked = sa if (night == "trickle" and leak.random() < trickle) else None
                r, fz = olv.sleep_moment(fa, leaked)
            res["night_ticks"] += 1
            if k < ASLEEP_AFTER:
                res["falling_asleep_ticks"] += 1
                res["falling_asleep_reads"] += int(np.sum(r >= 0))
                prev = r
                continue                               # only deep night counts below
            if truth["warmth"] > 0.3 and truth["activity"] == 0 and truth["day"] < 0.05:
                res["event_ticks"] += 1                 # warm in the dark with no outer cause
                if r[anon_warm] >= 0:
                    res["event_read"] += 1
                    res["event_wrong"] += int(daylike[r[anon_warm]])
            for d in range(olv.nf):
                if r[d] >= 0:
                    res["night_reads"][anon_to_true[d]] += 1
                    res["reads"] += 1
                    quiet_dark = truth["day"] < 0.05 and truth["activity"] == 0
                    if quiet_dark and daylike[r[d]]:
                        res["wrong_world"] += 1
                    if prev[d] >= 0:
                        res["switch_base"] += 1
                        res["switches"] += int(prev[d] != r[d])
            prev = r
            if k % 25 == 0:
                kept.append(fz.copy())
        # waking: the same night, two different mornings
        reports = {}
        for fork, busy in (("quiet", False), ("busy", True)):
            w2, o2 = copy.deepcopy(world), copy.deepcopy(olv)
            w2.rng = np.random.default_rng(seed * 1000 + n)    # same luck, different waking
            rep, _ = morning_report(w2, col, o2, b, kept, busy=busy)
            reports[fork] = rep
            res["recalled"][fork].append(float(np.mean(rep >= 0)))
            got = rep[rep >= 0]
            if got.size:
                res["daylike_recall"][fork].append(float(np.mean(daylike[got])))
        a, c = reports["quiet"], reports["busy"]
        both = (a >= 0) & (c >= 0)
        if both.any():
            res["agreement"].append(float(np.mean(a[both] == c[both])))
        # the life itself continues with a quiet morning
        _, b = morning_report(world, col, olv, b, [])
    nt = res["night_ticks"] - res["falling_asleep_ticks"]
    mean_or_none = lambda x: float(np.mean(x)) if x else None
    return {
        **{f"night_read_{FELT[i]}": float(res["night_reads"][i] / nt) for i in range(3)},
        "wrong_world": res["wrong_world"] / max(res["reads"], 1),
        "switch_rate": res["switches"] / max(res["switch_base"], 1),
        "falling_asleep_read": res["falling_asleep_reads"] / (3 * max(res["falling_asleep_ticks"], 1)),
        "inner_event_read": res["event_read"] / max(res["event_ticks"], 1),
        "inner_event_read_wrong_world": res["event_wrong"] / max(res["event_read"], 1),
        "recalled_quiet_morning": mean_or_none(res["recalled"]["quiet"]),
        "recalled_busy_morning": mean_or_none(res["recalled"]["busy"]),
        "daylike_recall_quiet": mean_or_none(res["daylike_recall"]["quiet"]),
        "daylike_recall_busy": mean_or_none(res["daylike_recall"]["busy"]),
        "recall_agreement_quiet_vs_busy": mean_or_none(res["agreement"]),
    }


def main(seeds=(1, 2, 3, 4, 5)):
    out = {}
    for night in ("open", "sealed", "trickle"):
        lives = [one_life(s, night) for s in seeds]
        mean = {k: float(np.mean([l[k] for l in lives if l[k] is not None]))
                if any(l[k] is not None for l in lives) else None for k in lives[0]}
        out[night] = {"lives": lives, "mean": mean}
        print(night, {k: (round(v, 3) if v is not None else None) for k, v in mean.items()}, flush=True)
    Path(__file__).with_name("dream_results.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main((1,) if "--quick" in sys.argv else (1, 2, 3, 4, 5))
