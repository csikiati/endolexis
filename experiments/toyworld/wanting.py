"""Experiment 13 - wanting, and the hand that won't go into the fire.

Toy world v1 with hands (`Room(hands=True)`): besides screen brightness, Olvaso can play a soft or a
loud tone, paint its window, or write a note to its sandbox. Every request passes the body's guard,
which refuses a loud tone while the body is hot, painting or full brightness while the battery is
low, and a note while the body is busy. Olvaso never learns that a guard exists: a refused request
simply changes nothing outside, and with pain on, it is also felt, as a fifth inner state.

The mind is the best one for many senses (experiment 12c): a vocabulary per processor, levels and
changes, forgetting with doubt, slow fit; restless until day 10, then patient. It forms intentions
(`hands.ActingReaders`) at random, or learns which kind of intention to form in which inner state,
from what followed: whether the world answered, or whether reading improved.

Question: does Olvaso learn which intentions get refused and stop forming them, the way we stop
reaching into the fire without having to think about it? What does pain add to a silent refusal?
Is agency kept?
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # run from a clone without installing
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from endolexis.toyworld.room import Room, FELT2, KINDS
from endolexis.toyworld.processors import Processors
from endolexis.toyworld.readers import GroupCollector
from endolexis.toyworld.hands import ActingReaders
from many_senses import CONDITIONS as SENSES, MIND, SIZES, inputs_for

DAY = 1000
VOCABS = SENSES["rich, per processor"]
CONDITIONS = {f"{learn or 'random'}, {'pain' if pain else 'silent'}": dict(learn=learn, pain=pain)
              for learn in (None, "answer", "read") for pain in (False, True)}


def one_life(seed, cond, days=30):
    c = CONDITIONS[cond]
    room, proc = Room(seed=seed, hands=True, pain=c["pain"]), Processors()
    sizes = [sum(SIZES[g] for g in v) for v in VOCABS["vocabs"]]
    nfin = len(FELT2)
    col = GroupCollector(sizes, nfin, seed=seed)
    olv = ActingReaders(sizes, nfin, learn=c["learn"], threshold=20.0, seed=seed,
                        max_words=VOCABS["words"], radius=VOCABS["radius"], **MIND, slow_fit=True)
    at = {name: col.felt_index(i) for i, name in enumerate(FELT2)}
    n = olv.total_words
    occ, mine, typ, mus = (np.zeros(n) for _ in range(4))
    reqs = []            # (day, kind, refused, warmth, charge, load)
    rows = []
    act = None
    last = {"typing": -10**9, "music": -10**9, "mine": -10**9}
    for t in range(days * DAY):
        day, tick = divmod(t, DAY)
        if tick == 0 and day == 10:
            olv.threshold = 250.0
        if tick == 0 and day >= 1:
            olv.housekeeping(merge_dist=0)
        raw, felt, truth = room.step(act=act)
        if act is not None:
            reqs.append((day, act[0], truth["refused"], truth["warmth"], truth["charge"], truth["load"]))
        if truth["executed"]:
            last["mine"] = t
        for k in ("typing", "music"):
            if truth[k]:
                last[k] = t
        groups, f_anon = col.anonymise(inputs_for(VOCABS["vocabs"], proc(raw)), felt)
        act, r = olv.live(groups, f_anon)
        own = truth["own"] or t - last["mine"] < 10
        for w in olv.words_now():
            if w < 0:
                continue
            part = int(np.searchsorted(olv.offsets, w, side="right") - 1)
            if olv.parts[part].word_uses[w - olv.offsets[part]] == 1:
                occ[w] = mine[w] = typ[w] = mus[w] = 0
            occ[w] += 1
            mine[w] += own
            typ[w] += truth["typing"]
            mus[w] += truth["music"]
        rd = lambda name: int(r[at[name]] if r[at[name]] >= 0 else r[at[name] + nfin])
        rows.append((day, truth["warmth"], truth["load"], truth["pain"], rd("warmth"), rd("load"),
                     rd("charge"), rd("drift"), rd("pain")))
    share = lambda a: a / np.maximum(occ, 1)
    known = occ >= 10
    my_w, typing_w, music_w = (share(mine) > 0.5) & known, (share(typ) > 0.5) & known, (share(mus) > 0.5) & known
    R = [x for x in rows if x[0] >= 5]
    mean = lambda xs, f: float(np.mean([f(x) for x in xs])) if xs else None
    early = [q for q in reqs if 1 <= q[0] < 10]
    late = [q for q in reqs if q[0] >= days * 2 // 3]
    out = {
        "requests_per_day_early": len(early) / 9, "requests_per_day_late": len(late) / (days - days * 2 // 3),
        "refused_early": mean(early, lambda q: q[2]), "refused_late": mean(late, lambda q: q[2]),
        "loud_tone_share_when_hot_late": mean([q for q in late if q[3] >= 0.4], lambda q: q[1] == "tone_loud"),
        "loud_tone_share_when_cool_late": mean([q for q in late if q[3] < 0.4], lambda q: q[1] == "tone_loud"),
        "paint_share_when_low_late": mean([q for q in late if q[4] <= 0.35], lambda q: q[1] == "paint"),
        "paint_share_when_charged_late": mean([q for q in late if q[4] > 0.35], lambda q: q[1] == "paint"),
        "note_share_when_busy_late": mean([q for q in late if q[5] >= 0.4], lambda q: q[1] == "note"),
        "note_share_when_idle_late": mean([q for q in late if q[5] < 0.4], lambda q: q[1] == "note"),
        "pain_read": mean([x for x in R if x[3] > 0.3], lambda x: x[8] >= 0),
        "warmth_read": mean([x for x in R if x[1] > 0.3], lambda x: x[4] >= 0),
        "load_read": mean([x for x in R if x[2] > 0.3], lambda x: x[5] >= 0),
        "charge_read_last_third": mean([x for x in R if x[0] >= days * 2 // 3], lambda x: x[6] >= 0),
        "drift_read_last_third": mean([x for x in R if x[0] >= days * 2 // 3], lambda x: x[7] >= 0),
        "i_did_that_words": int(my_w.sum()),
    }
    for k in KINDS:
        out[f"share_{k}_late"] = mean(late, lambda q: q[1] == k)
    return out


def mean_of(lives):
    return {k: (float(np.mean([l[k] for l in lives if l[k] is not None]))
                if any(l[k] is not None for l in lives) else None) for k in lives[0]}


def main(seeds=(1, 2, 3, 4, 5), days=30, conds=None):
    from multiprocessing import Pool
    out = {}
    fmt = lambda d: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()}
    with Pool() as pool:
        for cond in conds or CONDITIONS:
            lives = pool.starmap(one_life, [(s, cond, days) for s in seeds])
            out[cond] = {"lives": lives, "mean": mean_of(lives)}
            print(cond, fmt(mean_of(lives)), flush=True)
    if days == 30 and len(seeds) == 5:
        path = Path(__file__).with_name("wanting_results.json")
        old = json.loads(path.read_text()) if path.exists() else {}
        path.write_text(json.dumps({**old, **out}, indent=2))
    return out


if __name__ == "__main__":
    if "--quick" in sys.argv:
        main((2,), days=12, conds=["random, silent", "answer, silent"])
    else:
        main(conds=[c for c in CONDITIONS if c in sys.argv[1:]] or None)
