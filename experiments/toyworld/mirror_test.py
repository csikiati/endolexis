"""Experiment 15 - the mirror test.

Toy world v1 with hands (experiment 13), the best mind for many senses, learning which intention to
form from whether the world answered (any one sense: an answer seen counts as much as one heard,
`answer_by="sense"`). No pain channel, and its own tones are not heard (voice "deaf"),
so the only thing that differs is what the camera sees of its painted window (`Room(window=...)`), in a
mirror on the wall:

  mirror    - it sees its own painted window
  blind     - it does not, and nobody else paints
  stranger  - it does not; a stranger paints as often as Olvaso painted the day before, in the same
              colours, at random moments
  recording - it does not; its own paintings of the day before are shown again at the same moments of
              the day: a window exactly like its own, which does not follow its acting

Only Olvaso's own painting costs the body (charge, and load: the work of drawing).

Question, as in experiment 14 but for sight: is there an "I did that" for its image in the mirror, and
does it need the image to be contingent on the acting, or only to look like it? Experiment 14 predicts
the recording fails. Marks: does it expect an answer when it paints, and paint more; does it paint in
runs (testing); can it read the load its own painting causes through the words of its seen window, and
does it misread its load through a window that is not its own?
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # run from a clone without installing
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from endolexis.toyworld.room import Room, FELT1, KINDS
from endolexis.toyworld.processors import Processors
from endolexis.toyworld.readers import GroupCollector
from endolexis.toyworld.hands import ActingReaders
from many_senses import CONDITIONS as SENSES, MIND, SIZES, inputs_for

DAY = 1000
VOCABS = SENSES["rich, per processor"]
CONDITIONS = {v: dict(window=v) for v in ("mirror", "blind", "stranger", "recording")}
PAINT = [KINDS.index("paint")]


def one_life(seed, cond, days=30):
    c = CONDITIONS[cond]
    room = Room(seed=seed, hands=True, pain=False, pain_channel=False, voice="deaf", window=c["window"])
    proc = Processors()
    sizes = [sum(SIZES[g] for g in v) for v in VOCABS["vocabs"]]
    nfin = len(FELT1)
    col = GroupCollector(sizes, nfin, seed=seed)
    olv = ActingReaders(sizes, nfin, learn="answer", answer_by="sense", threshold=20.0, seed=seed,
                        max_words=VOCABS["words"], radius=VOCABS["radius"], **MIND, slow_fit=True)
    al = col.felt_index(FELT1.index("load"))
    see = 0                                            # the vision vocabulary
    n = olv.total_words
    occ, own_heard, other_heard = (np.zeros(n) for _ in range(3))
    reqs, rows = [], []
    act = None
    last = {"music": -10**9, "own": -10**9, "other": -10**9}
    for t in range(days * DAY):
        day, tick = divmod(t, DAY)
        if tick == 0 and day == 10:
            olv.threshold = 250.0
        if tick == 0 and day >= 1:
            olv.housekeeping(merge_dist=0)
        raw, felt, truth = room.step(act=act)
        if act is not None:
            reqs.append((day, act[0], truth["refused"]))
        for k, key in (("music", "music"), ("own", "own_paint"), ("other", "other_paint")):
            if truth[key]:
                last[k] = t
        groups, f_anon = col.anonymise(inputs_for(VOCABS["vocabs"], proc(raw)), felt)
        act, r = olv.live(groups, f_anon)
        for w in olv.words_now():
            if w < 0:
                continue
            part = int(np.searchsorted(olv.offsets, w, side="right") - 1)
            if olv.parts[part].word_uses[w - olv.offsets[part]] == 1:
                occ[w] = own_heard[w] = other_heard[w] = 0
            occ[w] += 1
            own_heard[w] += truth["seen_own"]
            other_heard[w] += truth["other_paint"]
        lr = int(r[al] if r[al] >= 0 else r[al + nfin])
        rows.append((day, truth["load"], t - last["music"] < 80, t - last["own"] < 40,
                     t - last["other"] < 40, lr))
    share = lambda a: a / np.maximum(occ, 1)
    known = occ >= 10
    vs, ve = olv.offsets[see], olv.offsets[see] + olv.parts[see].max_words
    in_vision = np.zeros(n, bool)
    in_vision[vs:ve] = True
    own_w = (share(own_heard) > 0.5) & known & in_vision
    other_w = (share(other_heard) > 0.5) & known & in_vision
    late = [q for q in reqs if q[0] >= days * 2 // 3]
    early = [q for q in reqs if 1 <= q[0] < 10]
    is_paint = lambda q: q[1] == "paint"
    runs = [is_paint(b) for a, b in zip(late, late[1:]) if is_paint(a)]
    R = [x for x in rows if x[0] >= 5]
    own_load = [x for x in R if x[1] > 0.12 and not x[2] and x[3]]          # loaded by its own painting
    other_idle = [x for x in R if x[1] < 0.05 and x[4]]                     # idle, while another window glowed
    mean = lambda xs, f: float(np.mean([f(x) for x in xs])) if xs else None
    W = olv.W
    return {
        "paint_share_early": mean(early, is_paint), "paint_share_late": mean(late, is_paint),
        "paint_after_paint_late": float(np.mean(runs)) if runs else None,
        "expects_answer_paint": float(W[PAINT, -1].mean()),
        "expects_answer_others": float(np.delete(W[:, -1], PAINT).mean()),
        "own_window_words": int(own_w.sum()), "other_window_words": int(other_w.sum()),
        "own_painting_load_moments": len(own_load),
        "own_painting_load_read": mean(own_load, lambda x: x[5] >= 0),
        "own_painting_load_via_own_window": mean(own_load, lambda x: x[5] >= 0 and own_w[x[5]]),
        "load_misread_via_other_window_when_idle": mean(other_idle, lambda x: x[5] >= 0 and other_w[x[5]]),
        "load_read_via_other_window_any": mean([x for x in R if x[5] >= 0], lambda x: bool(other_w[x[5]])),
        "refused_late": mean(late, lambda q: q[2]),
    }


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
        path = Path(__file__).with_name("mirror_test_results.json")
        old = json.loads(path.read_text()) if path.exists() else {}
        path.write_text(json.dumps({**old, **out}, indent=2))
    return out


if __name__ == "__main__":
    if "--quick" in sys.argv:
        main((2,), days=12, conds=["mirror", "recording"])
    else:
        main(conds=[c for c in CONDITIONS if c in sys.argv[1:]] or None)
