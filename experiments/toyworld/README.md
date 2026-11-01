# Olvasó v0 in a toy world (`endolexis.toyworld`)

Experiments 1-7 of November 2026: a simulated body with three outer and three inner channels, an Olvasó that
starts from anonymous, shuffled numbers, and an observer that alone holds the key. Two papers report them:

- *Endolexis v0: Olvasó in a toy world* (experiments 1-5)
- *Do readers need sleep? A response to "Language Models Need Sleep"* (experiments 6-7; Behrouz et al.,
  [arXiv 2606.03979](https://arxiv.org/abs/2606.03979))

Every script below runs from a clone without installing (`python experiments/toyworld/<script>.py`), or after
`pip install -e .`. Each takes about one to five minutes on a laptop and writes its results as JSON beside itself;
the JSON files committed here are the runs the papers report.

This toy is separate from the stage engine in `endolexis` (the 21 stages of *Olvasó: an entity that reads itself*):
it is a smaller, independent reader, built to test single ideas in a world whose hidden truth is known.

Olvasó reads its inner (felt) states through the outer (sensed) world. It starts "the long way
around": anonymous, shuffled, randomly scaled numbers, with no names and no dictionary.

## Parts

| File | Role |
|---|---|
| `src/endolexis/toyworld/world.py` | Toy body: sensed light, activity, sound; felt warmth, charge, drift |
| `src/endolexis/toyworld/collector.py` | Shuffles and disguises channels; keeps the secret key for the observer |
| `src/endolexis/toyworld/olvaso.py` | Words from sensed movements, felt profiles, reading, pressure and action |
| `src/endolexis/toyworld/observer.py` | Read-only; matches what formed inside Olvasó to the truth afterwards |
| `experiments/toyworld/temperaments.py` | Four temperaments, three lives each, 30 simulated days |

Run: `python experiments/toyworld/temperaments.py` (about a minute).

## Hidden links in the world

- **Warmth** rises about 10 ticks after activity starts, then fades (delayed link).
- **Charge** drains slowly, refills by day, and brightness costs charge (slow, partly self-caused link).
- **Drift** wanders randomly and is linked to nothing. It is the control, and must stay unread.

## How Olvasó reads

1. Short windows of sensed numbers (movements, not snapshots) become **words** by online clustering.
2. For each word and each delay after it, Olvasó keeps the mean and spread of every felt dimension.
3. A word may **read** a felt state only if it has reliably preceded it, across at least 4 separate
   occasions, and its expected value fits the present. Otherwise the state is **unread**.
4. Unread states build **pressure**. Past a threshold Olvasó changes screen brightness.
   The learning Olvasó lowers its threshold when acting is followed by more reading, and raises it otherwise.

## First results (3 lives × 30 days each)

| Temperament | Drift read | Warm moments read via activity words (chance 13%) | Charge read | Actions | "I did that" words | Final threshold |
|---|---|---|---|---|---|---|
| Restless | 2% | 50% | 15% | 2701 | 18.7 | 20 |
| Middle | 1% | 60% | 13% | 429 | 0 | 100 |
| Patient | 1% | 48% | 45% | 20 | 0 | 250 |
| Learning | 1% | 60% | 14% | 40 | 0 | 247 (started at 100) |

What this shows, honestly:

- **No superstition.** Pure noise (drift) is almost never "read" (0–4% in every life).
  The rule that meaning must hold across separate occasions does the work.
- **The delayed link is found.** When truly warm, Olvasó usually reads it through activity words,
  about 4–5 times chance, in 11 of 12 lives. One world (seed 1) stays weak for most temperaments.
- **Only the restless one discovers its own agency.** Words that appear almost only right after its own
  actions formed only in the restless Olvasó. You have to act a lot to find out that you act.
- **Patience reads the slow body.** Charge was best read by patient lives (in 2 of 3), probably because
  constant acting keeps disturbing charge, so its profiles never settle. The result is noisy.
- **The learning Olvasó became patient.** In every life its threshold climbed from 100 to about 250:
  in this world, acting rarely brings a missing word, so it learned to wait.

Together this supports the idea that acting and understanding each give something the other cannot:
the restless mind learns that it is an agent, and the patient mind reads its slow inner life.
Neither temperament alone gets both.

## Open problems

- The vocabulary fills its 200-word limit; the light cycle gets tiled into many near-duplicate words.
- Charge, the slowest link, is read only weakly: word profiles look back at most 60 ticks.
- Alternating temperaments: see experiment 2.
- The dream test: see experiment 5.

## Experiment 2: growing up (`experiments/toyworld/growing_up.py`, 5 lives × 30 days)

Temperaments that change over a life: restless for 10 days then patient ("childhood→patient"),
restless then learning, and "play-and-rest" (alternating every 3 days).

| Temperament | Drift read | Warm via activity | Charge read, last third of life | "I did that" words |
|---|---|---|---|---|
| Restless | 2% | 57% | 14% | 18.8 |
| Patient | 1% | 54% | 50% | 0 |
| Childhood→patient | 1% | 57% | 13% | 5.0 |
| Childhood→learning | 2% | 57% | 25% | 4.0 |
| Play-and-rest | 1% | 56% | 14% | 5.2 |

A restless childhood leaves lasting "I did that" words, but the grown-up reads its slow body no better
than a lifelong restless Olvasó. Patience in adulthood does not repair it. Reason: meanings are lifetime
averages, so the disturbed childhood stays mixed into every charge meaning. Olvasó never forgets.

## Experiment 3: forgetting (`memory` parameter of Olvaso)

With `memory=N`, each meaning rests on roughly its last N experiences.

| Memory | Temperament | Drift read | Charge read, last third | "I did that" words |
|---|---|---|---|---|
| never forgets | Patient | 1% | 50% | 0 |
| never forgets | Childhood→patient | 1% | 13% | 5.0 |
| 1000 | Patient | 6% | 42% | 0 |
| 1000 | Childhood→patient | 6% | 46% | 5.4 |
| 300 | Patient | 29% | 69% | 0 |
| 300 | Childhood→patient | 24% | **86% (all 5 lives 83–89%)** | 5.0 |
| 300 | Restless | 17% | 30% | 10.4 |

- **Forgetting heals.** With short memory, the Olvasó that had a restless childhood and then became
  patient reads its slow body best of all, and keeps its sense of agency: the first one to get both.
- **Forgetting breeds superstition.** The same short memory makes pure noise (drift) look meaningful
  in a fifth to a third of moments. A meaning resting on few recent experiences can be a coincidence.
- **The open problem for v1:** an Olvasó that can revise meanings without believing coincidences.
  Candidates: requiring a fading meaning to still hold across several separate recent occasions,
  or keeping a slow "doubt" memory that a fast meaning must not contradict too often.

## Seeing inside (`experiments/toyworld/inspect_words.py`)

Draws one Olvasó's most-used words after a life: the sensed movement each word is, and the felt change
it expects over the next 60 ticks. See `experiments/toyworld/learned_words.png`.

## Experiment 4: forgetting with doubt (`experiments/toyworld/doubt.py`, 5 lives × 30 days)

Each meaning now has two memories. A **fast** one (about the last 300 experiences) says what the word
means now. A slow **doubt** memory (about 3000 experiences) tracks how much that fast meaning has
*wandered*. A real link settles, so its meaning stops wandering; a coincidence keeps drifting with the
noise it latched onto. A word may read only when its present meaning fits *and* its doubt is low
(`memory=300, doubt_memory=3000, doubt_limit=0.1`).

| Mind | Temperament | Drift read | Warm via activity | Charge read, last third | "I did that" words |
|---|---|---|---|---|---|
| Never forgets | Patient | 1% | 54% | 50% | 0 |
| Never forgets | Childhood→patient | 1% | 57% | 13% | 5.0 |
| Forgets | Patient | 29% | 66% | 69% | 0 |
| Forgets | Childhood→patient | 24% | 67% | 86% | 5.0 |
| **Forgets + doubt** | Restless | 1% | 72% | 21% | 18.8 |
| **Forgets + doubt** | Patient | 1% | 72% | 56% | 0 |
| **Forgets + doubt** | Childhood→patient | **1%** | **75%** | **66%** | **5.0** |

- **Doubt removes the superstition** that forgetting created (24% → 1%), back to the never-forgetting level.
- **It keeps most of the healing.** The Olvasó with a restless childhood now reads its slow body better than
  a lifelong patient one (66% vs 56%) and keeps its agency words. In 3 of 5 lives it reads charge at 82–85%;
  in the other 2 some charge meanings never settle enough to be trusted (36–42%).
- **It also sharpens the delayed link:** warm moments are read through activity words 72–75% of the time
  (chance 13%), up from about 57%.
- **Too much doubt reads only the obvious.** With `doubt_limit` 0.01–0.03, charge is almost never read.
  Less strict settings (0.2, or doubt_memory 1500) give similar results to 0.1.

So the best mind so far revises quickly, doubts slowly, was restless as a child and became patient.

## Experiment 5: the dream test (`experiments/toyworld/dream.py`, 5 lives)

An Olvasó (forgets + doubt, restless childhood then patient) lives 20 days awake, then sleeps with its lid
closed every night for 10 nights. The world now also has **inner night events**: warmth surges in the dark
with no outer cause, present from the start of life. Three kinds of night:

- **open:** control, the lid stays open and the dark night is sensed normally
- **sealed:** nothing sensed at all
- **trickle:** each moment, a fragment of the outer world leaks through with probability 5%

While sleeping Olvasó does not learn or act; time passes and empty moments enter the delay line.
At each waking it tries to read felt states kept from the night (one every 25 ticks) with the words of its
first 60 morning ticks: its **dream report**. Each night is replayed with two mornings: a quiet waking, and a
busy one (someone starts using the machine right away). A **wrong-world** reading is one made through a word
of a bright or busy world, while the moment actually was dark and quiet.

| | Open | Sealed | Trickle |
|---|---|---|---|
| Read while falling asleep (first 60 ticks) | 54% | 52% | 54% |
| Read in deep night: warmth / charge | 83% / 85% | **0% / 0%** | 76% / 69% |
| Drift read at night | 0% | 0% | 0% |
| Inner night surges read | 23%, of which 64% wrong-world | 0% | 1% |
| Night states recalled, quiet / busy morning | 58% / 64% | 57% / 34% | 59% / 58% |
| Recalled through wrong-world words, busy morning | 13% | **87%** | 17% |
| Same reading after quiet and after busy morning | 94% | **20%** | 91% |

What it shows:

- **Without outer input, inner states get no interpretation.** In the sealed deep night, not a single felt
  state was read. Only while falling asleep, while the day's last words still echo in the delay line, does
  reading continue. This is exactly the prediction of the theory.
- **A trickle is enough.** 5% of the outer world restores most reading, and it stays faithful (almost no
  wrong-world readings). Our toy night is dark and quiet, and its fragments say so; the trickle alone did
  not produce dream-like readings.
- **A sealed night is composed at waking, from the morning.** Nights that had some input are recalled
  stably, whatever the morning brings (91–94% the same). A sealed night left nothing to read it by, so the
  morning does it: after a busy waking, 87% of the recalled night is read through busy-day words, and the
  quiet and busy mornings agree on only 20% of the night (in 4 of 5 lives, 0–11%). The same night, two
  different reports, both made at waking. This is the theory's account of dream recall (and Dennett's
  "composed at waking") showing up in a 77,000-number toy.
- **Inner events with no outer cause stay mostly unread,** like drift. The exception is unsettling:
  awake in the dark (open), the few surges that were read were mostly read through busy-day words.
  With no right word available, Olvasó reached for a wrong one: a small misattribution, or hallucination.

Limits: the night world is simple; trickle fragments are mixed into 6-sample windows that span long
stretches of night; recall after open and trickle nights is helped by night words still in the delay line
at waking, which a sealed night cannot have. That last point is not a flaw but the mechanism itself.

## Experiments 6 and 7: a response to "Language Models Need Sleep" (`experiments/toyworld/sleep_response.py`)

Behrouz, Hashemi, Javanmard and Mirrokni (arXiv 2606.03979) give LLMs a sleep with two stages:
consolidation (short-term memory distilled into new long-term capacity, then pruned) and dreaming
(self-generated practice data, used for training). We ask what each stage does for a reader of itself.

### Experiment 6: consolidation and the seasons (5 lives)

Summer (days 0–10): warmth follows activity after 10 ticks. Winter (10–20): after 40 ticks. Summer again
(20–26). Olvasó sleeps sealed every night. Consolidation, at each waking, copies every settled meaning into
up to 3 long-term versions (a new version rather than overwriting: cf. parameter expansion); pruning then
clears the fast meaning. Measure: warm moments read through activity words.

| Mind | Summer | Winter | Summer again, first 2 days | Summer again, later | Drift read |
|---|---|---|---|---|---|
| Never forgets | 51% | 13% | 6% | 6% | 1.9% |
| Forgets + doubt | 46% | 10% | 2% | 3% | 1.1% |
| + nightly consolidation | 47% | 32% | **47%** | 44% | 3.7% |
| + consolidation + pruning | 48% | 34% | 48% | 47% | **10.3%** |

- **Without consolidation, a change of world is devastating twice over.** Winter is barely learned, and
  summer never comes back. The never-forgetting mind mixes the seasons into meanings too spread to trust.
  The doubting mind fails differently: the season change made its meanings wander, so doubt shuts them
  out for days. Burned by change, it stops trusting what it knows.
- **Consolidation into new long-term versions solves it** (in line with the paper): summer is read again on
  the first day back as well as in the first summer, and winter is read three times better.
- **Pruning has a price.** Clearing the fast meaning after consolidation tripled superstition (1 life: 39%).
  Long-term meanings are not doubted at reading time, so a consolidated coincidence stays believed.

### Experiment 7: dreaming (5 lives, night inner events on)

The best mind lives 20 days, sleeps 10 sealed nights, then lives 3 more days. Night kinds: sealed; trickle
(5% of the real outer world); dream (a share of moments replays one of Olvasó's own words, chosen at random:
cf. random expert activation); dream + learning (meanings learn from the dream pairings, unfiltered).

| Night | Inner states read in deep night | Readings through wrong-world words | Warm via activity, after the nights |
|---|---|---|---|
| Sealed | 0% | – | 39% |
| Trickle, 5% real | 48% | 1% | 39% |
| Dream, 5% replay | 3% | 33% | 39% |
| Dream, 30% replay | 16% | 33% | 39% |
| Dream 30% + learning | 16% | 35% | 36% |
| No doubt: dream 30% | 23% | 42% | 53% (drift read 9% → 24%) |
| No doubt: dream 30% + learning | 25% | 40% | 53% (drift read 9% → 24%) |

(Before the nights, warm via activity was 33%; it rises to 39% in every condition with 3 more days of life.)

- **Replaying its own words revives interpretation, and it is dream-like.** A third of dream readings are
  made through words of a bright or busy world in a dark, quiet night, against 1% for a real trickle. Dreams
  are the inside read through a remembered outside, untethered from the present one.
- **Learning from unfiltered dreams did little harm here** (39% → 36%), with or without doubt. The paper's
  filtering of dreams by usefulness may matter more for a model trained on its dreams at scale.
- **The larger risk is forgetting without doubt:** in that mind superstition rose from 9% to 24% across the
  nights whether or not it learned from its dreams.
