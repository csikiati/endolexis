"""Experiment 12 - many processors, one reader.

Toy world v1 (`Room`): a room seen through a 16x16 camera, heard through a microphone and touched
through a keyboard and mouse. Processor entities (`Processors`) turn the raw senses into 22
anonymous end products: vision 11, hearing 9, touch 2. The body feels warmth (after typing),
charge (daylight, minus screen brightness), load (a few moments after music starts) and drift
(linked to nothing).

The best mind so far lives 30 days: levels + changes, forgetting + doubt, restless childhood then
patient from day 10, and housekeeping that retires unused words but never merges them.

  v0 senses               - only light, loudness and key presses, one vocabulary (as v0 had)
  rich, one vocabulary    - all 22, one vocabulary, word radius of v0
  rich, one vocab, scaled - all 22, one vocabulary, word radius grown with the number of senses
  rich, per processor     - one vocabulary per processor (vision, hearing, touch); the 200 word
                            places are shared out by size (100, 80, 20)

Question: do richer senses help Olvaso read, or does its vocabulary drown? The load is the test
case: music and a voice are both loud, so loudness alone cannot tell which one came before it.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # run from a clone without installing
import numpy as np
from endolexis.toyworld.room import Room, FELT1
from endolexis.toyworld.processors import Processors, GROUPS, V0_SENSES
from endolexis.toyworld.readers import GroupCollector, ManyReaders

DAY = 1000
MIND = dict(memory=300, doubt_memory=3000, doubt_limit=0.1, adapt=300, adapt_mode="both")
SIZES = {g: len(v) for g, v in GROUPS.items()}
V0_IDX = [(g, GROUPS[g].index(n)) for g, n in V0_SENSES]


def radius_for(n):
    return 3.0 * np.sqrt(n / 3)          # v0: 3 senses, radius 3; distances grow as sqrt(dims)


CONDITIONS = {
    "v0 senses": dict(vocabs=[["v0"]], words=[200], radius=[3.0]),
    "rich, one vocabulary": dict(vocabs=[["vision", "hearing", "touch"]], words=[200], radius=[3.0]),
    "rich, one vocabulary, scaled": dict(vocabs=[["vision", "hearing", "touch"]], words=[200],
                                         radius=[radius_for(22)]),
    "rich, per processor": dict(vocabs=[["vision"], ["hearing"], ["touch"]], words=[100, 80, 20],
                                radius=[radius_for(11), radius_for(9), radius_for(2)]),
}
# follow-up: is the doubt limit tuned for three senses the wrong one for 22?
for _lim in (0.05, 0.2):
    CONDITIONS[f"rich, per processor, doubt limit {_lim}"] = dict(CONDITIONS["rich, per processor"],
                                                                  mind=dict(doubt_limit=_lim))


def inputs_for(vocabs, ends):
    out = []
    for v in vocabs:
        if v == ["v0"]:
            out.append(np.array([ends[g][i] for g, i in V0_IDX]))
        else:
            out.append(np.concatenate([ends[g] for g in v]))
    return out


def one_life(seed, cond, days=30):
    c = CONDITIONS[cond]
    room, proc = Room(seed=seed), Processors()
    sizes = [3 if v == ["v0"] else sum(SIZES[g] for g in v) for v in c["vocabs"]]
    col = GroupCollector(sizes, len(FELT1), seed=seed)
    olv = ManyReaders(sizes, len(FELT1), threshold=20.0, seed=seed, max_words=c["words"],
                      radius=c["radius"], **{**MIND, **c.get("mind", {})})
    nfin = len(FELT1)
    at = {name: col.felt_index(i) for i, name in enumerate(FELT1)}
    n = olv.total_words
    occ, typ, talk, mus = (np.zeros(n) for _ in range(4))
    rows = []
    b = None
    last = {"typing": -10**9, "music": -10**9}
    for t in range(days * DAY):
        day, tick = divmod(t, DAY)
        if tick == 0 and day == 10:
            olv.threshold = 250.0
        if tick == 0 and day >= 1:
            olv.housekeeping(merge_dist=0)
        raw, felt, truth = room.step(b)
        groups, f_anon = col.anonymise(inputs_for(c["vocabs"], proc(raw)), felt)
        b, r = olv.live(groups, f_anon)
        for w in olv.words_now():
            if w < 0:
                continue
            part = int(np.searchsorted(olv.offsets, w, side="right") - 1)
            if olv.parts[part].word_uses[w - olv.offsets[part]] == 1:     # a word (re)born here
                occ[w] = typ[w] = talk[w] = mus[w] = 0
            occ[w] += 1
            typ[w] += truth["typing"]
            talk[w] += truth["talking"]
            mus[w] += truth["music"]
        for k in last:
            if truth[k]:
                last[k] = t
        rd = lambda name: int(r[at[name]] if r[at[name]] >= 0 else r[at[name] + nfin])
        rows.append((day, truth["warmth"], truth["load"], t - last["typing"] < 80, t - last["music"] < 80,
                     rd("warmth"), rd("load"), rd("charge"), rd("drift")))
    share = lambda a: a / np.maximum(occ, 1)
    known = occ >= 10
    typing_w, music_w, voice_w = (share(typ) > 0.5) & known, (share(mus) > 0.5) & known, (share(talk) > 0.5) & known
    R = [x for x in rows if x[0] >= 5]
    warm = [x for x in R if x[1] > 0.3]
    loaded = [x for x in R if x[2] > 0.3]
    mean = lambda xs, f: float(np.mean([f(x) for x in xs])) if xs else None
    uses = olv.word_uses()
    all_occ = occ.sum()
    return {
        "warmth_read": mean(warm, lambda x: x[5] >= 0),
        "warmth_via_typing_words": mean(warm, lambda x: x[5] >= 0 and typing_w[x[5]]),
        "typing_words_chance": float(occ[typing_w].sum() / all_occ) if all_occ else None,
        "load_read": mean(loaded, lambda x: x[6] >= 0),
        "load_via_music_words": mean(loaded, lambda x: x[6] >= 0 and music_w[x[6]]),
        "load_via_voice_words": mean(loaded, lambda x: x[6] >= 0 and voice_w[x[6]]),
        "music_words_chance": float(occ[music_w].sum() / all_occ) if all_occ else None,
        "charge_read_last_third": mean([x for x in R if x[0] >= 20], lambda x: x[7] >= 0),
        "drift_read": mean(R, lambda x: x[8] >= 0),
        "words_alive": int(olv.alive().sum()),
        "words_used_20": int((uses >= 20).sum()),
        "music_words": int(music_w.sum()), "voice_words": int(voice_w.sum()), "typing_words": int(typing_w.sum()),
    }


def mean_of(lives):
    return {k: (float(np.mean([l[k] for l in lives if l[k] is not None]))
                if any(l[k] is not None for l in lives) else None) for k in lives[0]}


def main(seeds=(1, 2, 3, 4, 5), days=30, conds=None):
    out = {}
    fmt = lambda d: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()}
    from multiprocessing import Pool
    with Pool() as pool:
        for cond in conds or CONDITIONS:
            lives = pool.starmap(one_life, [(s, cond, days) for s in seeds])
            _report(out, cond, lives, seeds, fmt)
    if days == 30 and len(seeds) == 5:
        path = Path(__file__).with_name("many_senses_results.json")
        old = json.loads(path.read_text()) if path.exists() else {}
        path.write_text(json.dumps({**old, **out}, indent=2))
    return out


def _report(out, cond, lives, seeds, fmt):
    out[cond] = {"lives": lives, "mean": mean_of(lives)}
    print(cond, fmt(mean_of(lives)), flush=True)
    for s, l in zip(seeds, lives):
        print("   seed", s, fmt(l), flush=True)


if __name__ == "__main__":
    if "--quick" in sys.argv:
        main((2,), days=8)
    else:
        main(conds=[c for c in CONDITIONS if c in sys.argv[1:]] or None)
