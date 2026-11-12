"""Experiment 34 - the singer.

Toy world v1 with one hand only: a voice that sings (`hands=["sing"]`, see room.py). Each act is one note of three
octaves (C3 to B5) or a pause, a whole, half, quarter, eighth or sixteenth long (16 to 1 moments; a moment is a
quarter of a second of sound). Olvasó is the auditory mirror's mind (experiment 14), learning which intention to
form from whether the world answered; with one hand it learns only when to sing, and its notes are chosen at
random. The microphone hears its singing (`voice="mirror"`) or does not (`voice="deaf"`).

Questions: does a mind whose only way to act is singing come to have words for its own song (hearing words that
occur mostly while it sings)? Does it sing more when it hears itself, as in the auditory mirror, and does it sing
more when someone is in the room (singing as a way to reach out)? What does its song sound like? The observer
writes singer_<voice>_<seed>.wav: an excerpt of its own singing, rendered alone.

Results: singer_results.json, 5 lives of 30 days a condition. --quick: one life of 12 days in each.
"""
import json
import sys
import wave
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # run from a clone without installing
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from endolexis.toyworld.room import Room, FELT1, FS, NSAMP, note_freq
from endolexis.toyworld.processors import Processors
from endolexis.toyworld.readers import GroupCollector
from endolexis.toyworld.hands import ActingReaders
from many_senses import CONDITIONS as SENSES, MIND, SIZES, inputs_for

DAY = 1000
VOCABS = SENSES["rich, per processor"]
CONDITIONS = {v: dict(voice=v) for v in ("mirror", "deaf")}
HEAR = 1                                               # the hearing vocabulary


def render(sung, t0, t1):
    """Olvasó's own song between moments t0 and t1, alone, as samples at FS (the room's voice, without the room)."""
    out = np.zeros((t1 - t0) * NSAMP)
    tt = np.arange(NSAMP) / FS
    for t, (n, d) in sorted(sung.items()):
        if n is None or not t0 <= t < t1:
            continue
        nxt = min([u for u in sung if u > t] + [t + d])            # a new note or pause cuts it off
        f = note_freq(n)
        for k in range(min(d, nxt - t, t1 - t)):
            x = (k + np.arange(NSAMP) / NSAMP) / d
            env = np.minimum(1.0, x * d * NSAMP / 80) * np.clip((0.85 - x) / 0.15, 0, 1) ** 2
            i = (t - t0 + k) * NSAMP
            out[i:i + NSAMP] += 0.15 * env * np.sin(2 * np.pi * f * (tt + k * NSAMP / FS))
    return out


def write_wav(path, samples):
    s = np.int16(np.clip(samples / 0.2, -1, 1) * 30000)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FS)
        w.writeframes(s.tobytes())


def one_life(seed, cond, days=30, wav=None):
    c = CONDITIONS[cond]
    room = Room(seed=seed, hands=True, pain=False, pain_channel=False, voice=c["voice"])
    proc = Processors()
    sizes = [sum(SIZES[g] for g in v) for v in VOCABS["vocabs"]]
    nfin = len(FELT1)
    col = GroupCollector(sizes, nfin, seed=seed)
    olv = ActingReaders(sizes, nfin, learn="answer", threshold=20.0, seed=seed, hands=["sing"],
                        max_words=VOCABS["words"], radius=VOCABS["radius"], **MIND, slow_fit=True)
    n = olv.total_words
    occ, own_heard = np.zeros(n), np.zeros(n)
    sang_heard = sang_moments = 0                      # late: while it sang, was a word of its own song among its words?
    acts, present = [], []
    act = None
    for t in range(days * DAY):
        day, tick = divmod(t, DAY)
        if tick == 0 and day == 10:
            olv.threshold = 250.0
        if tick == 0 and day >= 1:
            olv.housekeeping(merge_dist=0)
        raw, felt, truth = room.step(act=act)
        present.append(truth["present"])
        if act is not None:
            acts.append((t, act[1]))
        groups, f_anon = col.anonymise(inputs_for(VOCABS["vocabs"], proc(raw)), felt)
        act, _ = olv.live(groups, f_anon)
        now = [w for w in olv.words_now() if w >= 0]
        for w in now:
            part = int(np.searchsorted(olv.offsets, w, side="right") - 1)
            if olv.parts[part].word_uses[w - olv.offsets[part]] == 1:
                occ[w] = own_heard[w] = 0
            occ[w] += 1
            own_heard[w] += truth["heard_song"]
        if day >= days * 2 // 3 and truth["own_song"]:
            known = (occ >= 10) & (own_heard / np.maximum(occ, 1) > 0.5)
            sang_moments += 1
            sang_heard += any(known[w] for w in now)
    hs, he = olv.offsets[HEAR], olv.offsets[HEAR] + olv.parts[HEAR].max_words
    known = occ >= 10
    own_w = (own_heard / np.maximum(occ, 1) > 0.5) & known
    own_w[:hs] = own_w[he:] = False
    lo = days * 2 // 3 * DAY
    late = [a for a in acts if a[0] >= lo]
    pres = np.array(present)
    n_pres, n_abs = pres[lo:].sum(), (~pres[lo:]).sum()
    sung = room.sung
    if wav:
        busiest = max(range(lo, days * DAY - 240, 60), key=lambda t: sum(t <= u < t + 240 for u in sung))
        write_wav(wav, render(sung, busiest, busiest + 240))       # a minute of its song
    notes = [d for _, d in late if d[0] is not None]
    mean = lambda xs: float(np.mean(xs)) if len(xs) else None
    return {
        "acts_per_day_early": sum(1 <= a[0] // DAY < 10 for a in acts) / 9,
        "acts_per_day_late": len(late) / max(1, days - days * 2 // 3),
        "pause_share_late": mean([d[0] is None for _, d in late]),
        "acts_per_1000_present": 1000 * sum(pres[a[0]] for a in late) / n_pres if n_pres else None,
        "acts_per_1000_absent": 1000 * sum(not pres[a[0]] for a in late) / n_abs if n_abs else None,
        "lowest_note": min((d[0] for d in notes), default=None), "highest_note": max((d[0] for d in notes), default=None),
        "lengths_late": dict(sorted(Counter(str(d[1]) for _, d in late).items())),
        "own_song_words": int(own_w.sum()),
        "own_song_word_while_singing": sang_heard / sang_moments if sang_moments else None,
        "expects_answer": float(olv.W[0, -1]),
    }


def mean_of(lives):
    out = {}
    for k in lives[0]:
        vs = [life[k] for life in lives if life[k] is not None]
        if all(isinstance(v, (int, float)) for v in vs):
            out[k] = float(np.mean(vs)) if vs else None
    return out


def main(seeds=(1, 2, 3, 4, 5), days=30, conds=None):
    from multiprocessing import Pool
    out = {}
    fmt = lambda d: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()}
    here = Path(__file__).parent
    with Pool() as pool:
        for cond in conds or CONDITIONS:
            args = [(s, cond, days, here / f"singer_{cond}_{s}.wav" if s == seeds[0] else None) for s in seeds]
            lives = pool.starmap(one_life, args)
            out[cond] = {"lives": lives, "mean": mean_of(lives)}
            print(cond, fmt(mean_of(lives)), flush=True)
    if days == 30 and len(seeds) == 5:
        (here / "singer_results.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    if "--quick" in sys.argv:
        main((2,), days=12)
    else:
        main(conds=[c for c in CONDITIONS if c in sys.argv[1:]] or None)
