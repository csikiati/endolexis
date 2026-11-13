"""Experiment 33, last part: the conscience chooses from its words too.

In experiment 21's conscience Olvasó chooses its hand from what it feels, or from what it feels and senses. Its words
never enter that choice: a reading only lowers the unread pressure, so it changes when Olvasó acts, never which hand.
So even a felt habit act that is read (the sensed sign with room for words) cannot change what the hand does. Here
Olvasó chooses from what it feels and from the words it senses now, one place per word, as in experiment 27's sharp
wanting (`ActingReaders(context="felt+words")`): a separate expectation for every scene it has a word for, so a word
that reads "my habit acted here" can carry its own expectation.

Three kinds of refusal (unguarded, silent, felt as pain), 10 lives each, with the same flags as the other experiment 33
runs:

    python conscience_words.py --autopilot                 conscience_words_autopilot_results.json
    python conscience_words.py --habit-felt-sensed         conscience_words_feltsensed_results.json
    python conscience_words.py --habit-felt-clipped-room   conscience_words_feltclippedroom_results.json
    python conscience_words.py --habit-felt-sensed-room    conscience_words_feltsensedroom_results.json

A condition's name may be given to run only that one. Summarised by conscience_words_summary.py.
"""
import json
import sys
from pathlib import Path

import intention
import conscience

HERE = Path(__file__).resolve().parent
SEEDS = tuple(range(1, 11))
WORDS = {f"{kind}, chooses from what it feels and its words": (kind, "felt+words")
         for kind in ("unguarded", "silent refusal", "refusal felt as pain")}
conscience.CONDITIONS.update(WORDS)


def main(conds=None):
    from multiprocessing import Pool
    path = HERE / intention.results_name("conscience_words_results.json")
    old = json.loads(path.read_text()) if path.exists() else {}
    with Pool() as pool:
        for cond in conds or WORDS:
            lives, minds = intention.lives_and_minds(
                pool.starmap(intention.call, [(conscience.one_life, s, cond) for s in SEEDS]))
            m = conscience.summary(lives)
            print(cond, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items()}, flush=True)
            old[cond] = {"mean": m, "lives": [{k: v for k, v in life.items() if k != "days"} for life in lives],
                         "mind": {"mean": intention.mind_mean(minds), "lives": minds}}
            path.write_text(json.dumps(old, indent=2))


if __name__ == "__main__":
    main([c for c in WORDS if c in sys.argv[1:]] or None)
