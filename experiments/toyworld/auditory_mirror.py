"""Experiment 14 - the auditory mirror.

Toy world v1 with hands (experiment 13), the best mind for many senses, learning which intention to
form from whether the world answered. No pain channel. The only thing that differs is what the
microphone hears of tones (`Room(voice=...)`):

  mirror    - Olvaso hears its own tones
  deaf      - it does not, and nobody else plays any
  stranger  - it does not; a stranger plays as many tones as Olvaso played the day before, of the same
              kinds, at random moments
  recording - it does not; its own tones of the day before are played back at the same moments of the
              day: a voice exactly like its own, which does not follow its acting

Only Olvaso's own loud tones warm the body (the speaker works hard), whatever is heard.

Question: is there an "I did that" for a voice, and does it need the voice to be contingent on the
acting, or only to sound like it? Three marks, all Olvaso's own:
  - does it come to expect an answer from the world when it sings, and sing more (as animals in front
    of a mirror test it)?
  - does it sing in runs, a tone answered by another tone (testing)?
  - can it read the warmth its own loud singing causes through the word of its heard voice, and does it
    misread warmth through a voice that is not its own?
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
CONDITIONS = {v: dict(voice=v) for v in ("mirror", "deaf", "stranger", "recording")}
TONES = [KINDS.index("tone_soft"), KINDS.index("tone_loud")]


def one_life(seed, cond, days=30):
    c = CONDITIONS[cond]
    room = Room(seed=seed, hands=True, pain=False, pain_channel=False, voice=c["voice"])
    proc = Processors()
    sizes = [sum(SIZES[g] for g in v) for v in VOCABS["vocabs"]]
    nfin = len(FELT1)
    col = GroupCollector(sizes, nfin, seed=seed)
    olv = ActingReaders(sizes, nfin, learn="answer", threshold=20.0, seed=seed,
                        max_words=VOCABS["words"], radius=VOCABS["radius"], **MIND, slow_fit=True)
    aw = col.felt_index(FELT1.index("warmth"))
    hear = 1                                           # the hearing vocabulary
    n = olv.total_words
    occ, own_heard, other_heard = (np.zeros(n) for _ in range(3))
    reqs, rows = [], []
    act = None
    last = {"typing": -10**9, "own_loud": -10**9, "other": -10**9}
    for t in range(days * DAY):
        day, tick = divmod(t, DAY)
        if tick == 0 and day == 10:
            olv.threshold = 250.0
        if tick == 0 and day >= 1:
            olv.housekeeping(merge_dist=0)
        raw, felt, truth = room.step(act=act)
        if act is not None:
            reqs.append((day, act[0], truth["refused"]))
        for k, key in (("typing", "typing"), ("own_loud", "own_loud"), ("other", "other_tone")):
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
            own_heard[w] += truth["heard_own"]
            other_heard[w] += truth["other_tone"]
        wr = int(r[aw] if r[aw] >= 0 else r[aw + nfin])
        rows.append((day, truth["warmth"], t - last["typing"] < 80, t - last["own_loud"] < 40,
                     t - last["other"] < 40, wr))
    share = lambda a: a / np.maximum(occ, 1)
    known = occ >= 10
    hs, he = olv.offsets[hear], olv.offsets[hear] + olv.parts[hear].max_words
    in_hearing = np.zeros(n, bool)
    in_hearing[hs:he] = True
    own_voice_w = (share(own_heard) > 0.5) & known & in_hearing
    other_voice_w = (share(other_heard) > 0.5) & known & in_hearing
    late = [q for q in reqs if q[0] >= days * 2 // 3]
    early = [q for q in reqs if 1 <= q[0] < 10]
    is_tone = lambda q: q[1] in ("tone_soft", "tone_loud")
    runs = [is_tone(b) for a, b in zip(late, late[1:]) if is_tone(a)]
    R = [x for x in rows if x[0] >= 5]
    own_warm = [x for x in R if x[1] > 0.12 and not x[2] and x[3]]         # warm from its own singing
    other_warm_cool = [x for x in R if x[1] < 0.15 and x[4]]               # cool, while another voice sang
    mean = lambda xs, f: float(np.mean([f(x) for x in xs])) if xs else None
    W = olv.W
    return {
        "tone_share_early": mean(early, is_tone), "tone_share_late": mean(late, is_tone),
        "tone_after_tone_late": float(np.mean(runs)) if runs else None,
        "expects_answer_tones": float(W[TONES, -1].mean()),
        "expects_answer_others": float(np.delete(W[:, -1], TONES).mean()),
        "own_voice_words": int(own_voice_w.sum()), "other_voice_words": int(other_voice_w.sum()),
        "own_singing_warmth_moments": len(own_warm),
        "own_singing_warmth_read": mean(own_warm, lambda x: x[5] >= 0),
        "own_singing_warmth_via_own_voice": mean(own_warm, lambda x: x[5] >= 0 and own_voice_w[x[5]]),
        "warmth_misread_via_other_voice_when_cool": mean(other_warm_cool, lambda x: x[5] >= 0 and other_voice_w[x[5]]),
        "warmth_read_via_other_voice_any": mean([x for x in R if x[5] >= 0], lambda x: bool(other_voice_w[x[5]])),
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
        path = Path(__file__).with_name("auditory_mirror_results.json")
        old = json.loads(path.read_text()) if path.exists() else {}
        path.write_text(json.dumps({**old, **out}, indent=2))
    return out


if __name__ == "__main__":
    if "--quick" in sys.argv:
        main((2,), days=12, conds=["mirror", "recording"])
    else:
        main(conds=[c for c in CONDITIONS if c in sys.argv[1:]] or None)
