# endolexis

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24051313.svg)](https://doi.org/10.5281/zenodo.24051313)

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

Every module, class, function and parameter, with how to call them: [docs/API.md](docs/API.md).

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

## Olvasó v0 in a toy world (`endolexis.toyworld`, new in 0.2.0)

A second, smaller reader, built in November 2026 to test single ideas in a world whose hidden truth is known: a
simulated body with three outer and three inner channels, an Olvasó that starts from anonymous, shuffled numbers,
and an observer that alone holds the key. Version 0.3.0 adds toy world v1, the symbiote: a room seen, heard and
touched through processor entities, with hands, a guard and mirrors. Twenty-six experiments, with every script and the stored results of the
reported runs, are in [`experiments/toyworld/`](experiments/toyworld/README.md):

| Experiments | Finding, in one line |
|---|---|
| 1. Temperaments | It finds a hidden, delayed link and never reads noise; only acting reveals agency, only patience reads the slow body |
| 2-4. Growing up, forgetting, doubt | A restless childhood scars until meanings can fade; fading needs a slow doubt to avoid superstition |
| 5. The dream test | Sealed sleep reads nothing; a sealed night is written at waking, from the morning's cues |
| 6-7. Response to "Language Models Need Sleep" | Nightly consolidation keeps an old world; pruning breeds superstition; dreams from memory are read through the wrong world |
| 8. A richer night | A varied night is harder to read and slightly more dream-like; real night causes are read correctly |
| 9. Housekeeping in sleep | Retiring infancy words makes room to learn something new late in life, at no cost |
| 10. Sensory adaptation | Feeling levels and changes reads a charger twice as well; feeling only change loses what persists |
| 11. Where the superstition came from | Merging words in sleep bred it; retiring without merging keeps the gain of feeling change, without the superstition |
| 12. Many processors, one reader | Toy world v1: a room seen, heard and touched through 22 processor outputs. Richer senses read what loudness could not; a vocabulary per processor beats one shared vocabulary; more senses bring more superstition |
| 12b-c. Habituation, age, and careful reading | Hearing steady sounds once only moves the dial; age teaches the load but not to doubt noise; requiring a meaning to fit now and over past days halves the superstition; a mixed vocabulary finds more meanings, true and false |
| 13. Wanting, and the guard | With five ways to act and a guard that refuses what the body can't afford, Olvasó learns from whether the world answered to stop forming the refused intentions, in the states where they'd be refused, without pain; the pain of a refused intention is never read, as no outer word precedes it |
| 14. The auditory mirror | Only a voice that follows its acting becomes its own: Olvasó expects an answer when it sings and sings twice as often, and reads the warmth of its own singing through its heard voice; a recording of its own voice is treated like a stranger |
| 15. The mirror test | The same for sight: only a mirrored window that follows its painting makes Olvasó expect an answer, paint more (19% → 44% of intentions) and paint in runs; a recording of its own paintings is treated like a stranger |
| 16. Many Olvasós taking turns to sleep | Olvasós living the same moments are clones; taking turns makes them different readers: three (one asleep, one waking, one awake) read the body 81% of the time against 65%, at twice the compute, with twice the superstition, which comes from partial lives and falls when the sleeps move on each day. Drawn and run with the [Olvasó Studio](studio/README.md) |
| 17. Guards learned from trauma in a sandbox | A body with a blade: with no guard it harmed 207 times in a life; learning from real trauma, once or twice; growing up in a sandbox, never in the real room. One simulated harm was enough, but what fear learned was crude (*stop whenever a person is in the room*) and sometimes a confound, so learned guards are readable and need review |
| 18. Fear that finds causes | Replaying the sandbox world with one thing changed at a time, the fear system learned only causes: the blade's reach with a margin (4.3 cells, 5.4 when fast; true 3 and 4), heat for the fast blade only, and no confounds or "a person anywhere" rules. It learns only from the harms it meets; comparing with near misses was not enough |
| 19. The devil's advocate | A tester that stages the scenes nobody has tried (a person at each distance, a hot body, each option) made the replaying fear system learn every cause: its guards let through 1% of harmful scenes in an exam of 88 scenes, against 45% for a hand-written guard. The same advocate made a crude fear system phobic, stopping 94% of harmless uses |
| 20. Removing the reaction lag | The lag came from rules stated on the harm itself, while a guard sees the moment before. Limits learned by replay are stated on what the guard sees (reach + one moment's walk), so the safety margin could go: no harm let through in 812 scenes, and over-caution down from 27% to 9%. Looking ahead (from each signal's rate of change) is for rules written by people: it cut the hand-written guard's misses from 45% to 28% |
| 21. Does the angel move inside? | A refusal is only an act the world did not answer. Olvasó learned to avoid the moments its acts are refused (asking there half as often as chance) only when it chose from what it senses, where the reason for refusal can be seen; choosing from what it feels, it never did. Refusal felt as pain taught nothing |
| 22. What the sandbox never showed | People walked faster in the real room than in the sandbox, and the learned guard let 22% of harmful scenes through. Caution under novelty (widening its limits the moment a person approached faster than anything seen in the sandbox) closed the gap before anyone was hurt; seeing a moment ahead was insurance too |
| 23. When the senses lie | A sensor that sometimes reads "nobody here" made a correct guard harm. A second, independent sensor removed the misses at no cost; a plausibility check protected people the guard had seen walk in. Noise was hardest: it wants filtering, not suspicion |
| 24. A guard that filters noisy senses | Filtering alone made noisy guards worse (a median lags). Safety came from acting on the nearest the person could plausibly be, an allowance estimated from the sensor's own jitter: no real harm. Two averaged sensors and a median cut the price of that caution from 66% to 41% of harmless uses stopped |
| 25. Does the wanting work around the guard? | No gaming: Olvasó did not seek a guard's loophole. Choosing from what it senses, refusals near people spread into wariness of them, and harm through the loophole fell by a third. But a mind that does not care about harm still walked through the gap about once a day, by plain use |
| 26. Harm by not acting, and conflicts between laws | A duty (a declared rule that acts) to sound an alarm met a guard that forbade the loud tone when hot. Blocked, it let people be harmed; with laws ranked (others before itself) it saved them at its own cost; trying a gentler way first harmed nobody and broke no law |

```python
from endolexis.toyworld import live_a_life
print(live_a_life(seed=2, days=30, memory=300, doubt_memory=3000, doubt_limit=0.1))
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

Code: MIT. Papers: CC BY 4.0. Please cite the paper you build on, and the software at the version you used:

| Work | DOI |
|---|---|
| Csiki, A. (2026). *Reading Ourselves: An External Dictionary for Internal States*. Preprint, Zenodo. | [10.5281/zenodo.23857768](https://doi.org/10.5281/zenodo.23857768) |
| Csiki, A. (2026). *Olvasó: an entity that reads itself*. Preprint, Zenodo. | [10.5281/zenodo.23857948](https://doi.org/10.5281/zenodo.23857948) |
| Csiki, A. (2026). *Endolexis v0: Olvasó in a toy world*. Preprint, Zenodo. | [10.5281/zenodo.23858275](https://doi.org/10.5281/zenodo.23858275) |
| Csiki, A. (2026). *Do readers need sleep? A response to "Language Models Need Sleep"*. Preprint, Zenodo. | [10.5281/zenodo.23858381](https://doi.org/10.5281/zenodo.23858381) |
| Csiki, A. (2026). *The symbiote in a toy world: Olvasó among processors* (experiments 12–15). Preprint, Zenodo. | [10.5281/zenodo.24051218](https://doi.org/10.5281/zenodo.24051218) |
| Csiki, A. (2026). *endolexis* (Version 0.3.0, experiments 1–15) [Software]. Zenodo. | [10.5281/zenodo.24051313](https://doi.org/10.5281/zenodo.24051313) |
| Csiki, A. (2026). *endolexis* (Version 0.2.0, experiments 1–7) [Software]. Zenodo. | [10.5281/zenodo.23856387](https://doi.org/10.5281/zenodo.23856387) |

Each paper's record holds its English and Hungarian versions. The paper DOIs above cite all versions of a
paper and resolve to the latest; each software DOI cites exactly one version. `CITATION.cff` holds the same references; GitHub's
"Cite this repository" button gives other formats.

The toy-world code, experiments and the last two papers were developed with AI assistance (Claude, Anthropic); the
author is responsible for their content.
