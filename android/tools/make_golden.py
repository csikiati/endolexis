"""Record one E.L.E.M.E.R. life in Python, for the Kotlin port to replay and match.

The life is the app's own mind (the best mind for many senses, learning from the world's answer, restless
until moment 10 000, housekeeping every 1000 moments that only retires words) in toy world v1 with hands.
Inputs are rounded to float32 before the Python mind sees them, so that both minds get the same numbers.

Writes app/src/test/resources/golden_life.bin (little-endian):
  int32 T, n_in, n_felt, n_read
  float32 inputs[T][n_in]      anonymised processor end products (vision 11, hearing 9, touch 2)
  float32 felt[T][n_felt]      anonymised inner states
  int16 readings[T][n_read]    what the mind read (-1 unread, -2 disregarded)
  int16 words[T][3]            the word each vocabulary sensed (-1 none)
  int8 kind[T], int8 detail[T] the intention formed this moment (-1 none)
  float64 W[5][n_felt+1]       the expectations at the end (one row per kind of intention)
Run from android/:  python tools/make_golden.py
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np
from endolexis.toyworld.room import Room, FELT1, KINDS
from endolexis.toyworld.processors import Processors
from endolexis.toyworld.readers import GroupCollector
from endolexis.toyworld.hands import ActingReaders, DETAILS

T = 12000
ORDER = ("vision", "hearing", "touch")
SIZES = [11, 9, 2]
RADIUS = [3.0 * np.sqrt(n / 3) for n in SIZES]
MIND = dict(memory=300, doubt_memory=3000, doubt_limit=0.1, adapt=300, adapt_mode="both", slow_fit=True)


def main(seed=3, out=Path(__file__).resolve().parents[1] / "app/src/test/resources/golden_life.bin", feel=False, T=T,
         surprise=False, retry=False):
    """A recorded life (Python's Olvasó), for the Kotlin one to replay. feel: it feels its own intentions
    (experiment 29; golden_life_intention.bin); surprise: it feels a missing answer (experiment 30;
    golden_life_surprise.bin, with both); retry: it tries again and feels "stopped" (experiment 31;
    golden_life_retry.bin, with all three)."""
    room = Room(seed=seed, hands=True, pain=False, pain_channel=False, voice="mirror")
    proc = Processors()
    col = GroupCollector(SIZES, len(FELT1), seed=seed)
    olv = ActingReaders(SIZES, len(FELT1), learn="answer", threshold=20.0, seed=seed,
                        max_words=[100, 80, 20], radius=RADIUS, feel_intention=feel,
                        feel_surprise=surprise, retry=retry, **MIND)
    f32 = lambda a: np.asarray(a, np.float32).astype(float)
    ins, fel, rds, wds, kinds, dets = [], [], [], [], [], []
    act = None
    for t in range(T):
        if t == 10000:
            olv.threshold = 250.0
        if t > 0 and t % 1000 == 0:
            olv.housekeeping(merge_dist=0)
        raw, felt, truth = room.step(act=act)
        ends = proc(raw)
        groups, f = col.anonymise([ends[g] for g in ORDER], felt)
        groups, f = [f32(g) for g in groups], f32(f)
        act, r = olv.live(groups, f)
        ins.append(np.concatenate(groups)); fel.append(f); rds.append(r); wds.append(olv.words_now())
        if act is None:
            kinds.append(-1); dets.append(-1)
        else:
            kinds.append(KINDS.index(act[0])); dets.append(list(DETAILS[act[0]]).index(act[1]))
    R = np.array(rds)
    print("moments with a reading:", float(np.mean((R >= 0).any(axis=1))), "requests:", sum(k >= 0 for k in kinds))
    with open(out, "wb") as fh:
        fh.write(struct.pack("<4i", T, 22, len(FELT1), R.shape[1]))
        fh.write(np.array(ins, "<f4").tobytes()); fh.write(np.array(fel, "<f4").tobytes())
        fh.write(R.astype("<i2").tobytes()); fh.write(np.array(wds, "<i2").tobytes())
        fh.write(np.array(kinds, "i1").tobytes()); fh.write(np.array(dets, "i1").tobytes())
        fh.write(olv.W.astype("<f8").tobytes())
    print("wrote", out, out.stat().st_size, "bytes; W bias:", np.round(olv.W[:, -1], 3))


def senses(seed=4, n=120, out=Path(__file__).resolve().parents[1] / "app/src/test/resources/golden_senses.bin"):
    """Raw frames and what the processors made of them: int32 n, then per moment float32 image[16*16*3],
    float32 sound[2048], float64 vision[11], float64 hearing[9]. The room acts now and then, so tones and
    paint are in the sound and picture."""
    room, proc = Room(seed=seed, hands=True, pain_channel=False), Processors()
    rng = np.random.default_rng(seed)
    with open(out, "wb") as fh:
        fh.write(struct.pack("<i", n))
        t = 0
        while n:
            act = (KINDS[int(rng.integers(5))], 0) if rng.random() < 0.1 else None
            if act and act[0] != "note":
                act = (act[0], DETAILS[act[0]][int(rng.integers(len(DETAILS[act[0]])))])
            raw, _, _ = room.step(act=act)
            img, snd = np.asarray(raw["image"], np.float32), np.asarray(raw["sound"], np.float32)
            ends = proc({"image": img.astype(float), "sound": snd.astype(float), "touch": raw["touch"]})
            t += 1
            if t < 400:                           # the processors start fresh at moment 400, as in the test
                proc = Processors()
                continue
            fh.write(img.astype("<f4").tobytes()); fh.write(snd.astype("<f4").tobytes())
            fh.write(ends["vision"].astype("<f8").tobytes()); fh.write(ends["hearing"].astype("<f8").tobytes())
            n -= 1
    print("wrote", out, out.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
    main(out=Path(__file__).resolve().parents[1] / "app/src/test/resources/golden_life_intention.bin", feel=True, T=6000)
    main(out=Path(__file__).resolve().parents[1] / "app/src/test/resources/golden_life_surprise.bin", feel=True, T=6000,
         surprise=True)
    main(out=Path(__file__).resolve().parents[1] / "app/src/test/resources/golden_life_retry.bin", feel=True, T=6000,
         surprise=True, retry=True)
    senses()
