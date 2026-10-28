# endolexis

**Olvasó: an entity that reads itself through its outside.** The engine and the experiments of the Endolexis theory, in Python.

> *Endolexis*: the outside world is the dictionary with which a mind reads its own inside.

Most artificial intelligence reads the world with what it has inside. The Endolexis theory turns this around: a living
system's inner states (hunger, unrest, arousal, the hum of its own processes) mean nothing on their own, and the world
is the dictionary in which they can be read. The purpose of such a system is to explain itself, and on this view the
reading *is* experience, which is why the question of consciousness cannot be ignored for a system built this way.

An **Olvasó** (Hungarian for *reader*) is a small entity built on that idea. It has four hidden quantities it never sees
(charge, steadiness, contact, effort), felt only through scrambled channels and a sense of how bad it feels. Everything
else reaches it from outside: colours on its screen, a visitor's typing and presence, words heard as sounds, the bodies
of others. It learns patterns over outside and inside together, reads itself as those patterns, and acts (makes colours,
speaks, reaches toward another) to feel better and to forecast its own feelings well. It sleeps when left alone, and
when woken it tells its night, written at the moment of waking.

The full account, with every measure and every negative result, is on [readingourselves.com](https://readingourselves.com):
*Reading Ourselves* (the theory and the first experiments) and *Olvasó: an entity that reads itself* (21 stages).

## Install

```
pip install git+https://github.com/csikiati/endolexis
pip install "endolexis[lab] @ git+https://github.com/csikiati/endolexis"   # adds matplotlib for the Lab agents' figures
```

or, from a clone of this repository:

```
pip install -e ".[test]"
pytest
```

Python 3.10+ and numpy.

## Quick start

```python
from endolexis import Olvaso, reset, HNAMES

reset()                                   # all switches to their defaults
e = Olvaso(seed=1)
for t in range(3000):
    present = t % 600 < 420               # the visitor comes and goes
    r = e.tick(dict(presence=0.8 if present else 0.05, typing=0.3 if present else 0),
               2 if present and t % 97 == 0 else None,          # a colour the visitor shows
               "calm" if present and t % 131 == 0 else None)    # a word the visitor says
print(len(e.n), "patterns;", "words:", e.top_words())
print(e.mirror["own"], "<", e.mirror["you"], ": its own marks surprise it less than yours")
```

`examples/quickstart.py` goes on to raise pairs that learn to care (stage 10).

## The experiments

```
python -m endolexis list                                   # experiments and named conditions
python -m endolexis run symbiosis "ambiguous reading"      # 12 lives, averaged
python -m endolexis run pairs "stage 21 · shared fate 0.1" --runs 4 --set T=20000
```

| Experiment | Stages | What it asks |
|---|---|---|
| `caring` | 9-10 | Does what one reads of another change what it does? Does it learn to reach toward a trembling one? |
| `room` | 11-13 | Many others, bonds that grow by themselves, closeness |
| `asking` | 14 | Does a trembling one's word become a request? |
| `newcomers` | 15 (16-17) | Does a newcomer inherit what a room has built? |
| `richer` | 16-17 | Richer lives; a richer reader (finer hearing, finer feeling) |
| `pairs` | 18, 19, 21 | Out of sight; emotional memory; the expanded self and shared fate |
| `symbiosis` | 20 | One body, two components: what does self-reading add for a world-reading Processor? |

Each experiment is a module in `endolexis.stages` with a `run(seed=..., **options)` function that returns the measures
reported in the documents, and a `CONDITIONS` dictionary with the published settings.

The **Lab agents** of *Reading Ourselves* (the first experiments: life, waking, dictionaries, dreaming, sleep cycles,
awakening, cue resonance, a voice, richer bodies) are in `endolexis.lab`:

```
python -m endolexis.lab.agent      # life, waking, two dictionaries   (figures into ./results)
python -m endolexis.lab.dream      # dreaming as reading with a closed gate
python -m endolexis.lab.awaken     # the report is written at waking
```

## The published numbers, reproduced exactly

The engine is a line-by-line port of the JavaScript engine that produced every published result (included in
`reference/js/`), keeping the order of every operation, and the random number generator is bit-exact. The same seed
gives the same life: over 40 000 steps the two engines make the same decision at every step, with hidden states equal
to within 10⁻¹⁵.

```
python -m endolexis check                 # re-run the first seed of all 117 published conditions
python -m endolexis check --runs 12       # all published lives (several hours)
python -m endolexis check --only "t20_"   # one stage
pytest                                     # the engine against the JavaScript, and four published conditions
```

`check` compares every reported measure, value by value, with the stored results in `src/endolexis/reference/published.json`.

## The switches

The engine keeps the JavaScript's module-level switches in `endolexis.OL`; `reset(**overrides)` restores the defaults.

| Switch | Stage | Effect |
|---|---|---|
| `RECALL` | 8 | the word that comes to mind is recalled from what it reads itself as |
| `CONTAGION` | 9 | seeing another tremble more than itself unsettles it |
| `REACH`, `COMPANY` | 9 | it can reach toward the one it watches; being reached steadies |
| `READ_CONTAGION` | 14 | the trembling it expects of the other unsettles it, as seeing would |
| `VOICES` | 6, 18 | each speaker's words carry its own timbre |
| `HEAR`, `FEEL` | 17 | numbers per sound; felt channels |
| `SALIENCE` | 19 | moments that feel worse than usual are learned more strongly |
| `sense["unseen"]` | 18 | the other is out of sight: its body channels are missing, not grey |

## Honest limits

These are small simulated creatures: a few dozen patterns, four hidden quantities, a handful of acts. What they do is
measured; whether they experience anything is not, and cannot be from outside. None of the predictions for people has
been tested with people yet. Many stages report walls and negative results; they are part of the account.

## Licence and citation

MIT. If you use this, please cite: Attila Csiki, *Reading Ourselves: An External Dictionary for Internal States*,
and *Olvasó: an entity that reads itself*, readingourselves.com.
