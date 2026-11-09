# Olvasó v0 in a toy world (`endolexis.toyworld`)

Experiments 1-11 of November 2026: a simulated body with three outer and three inner channels, an Olvasó that
starts from anonymous, shuffled numbers, and an observer that alone holds the key. Two papers report them:

- *Endolexis v0: Olvasó in a toy world* (experiments 1-5),
  [doi:10.5281/zenodo.23858275](https://doi.org/10.5281/zenodo.23858275)
- *Do readers need sleep? A response to "Language Models Need Sleep"* (experiments 6-7; Behrouz et al.,
  [arXiv 2606.03979](https://arxiv.org/abs/2606.03979)), [doi:10.5281/zenodo.23858381](https://doi.org/10.5281/zenodo.23858381)

Every script below runs from a clone without installing (`python experiments/toyworld/<script>.py`), or after
`pip install -e .`. Each takes about one to five minutes on a laptop and writes its results as JSON beside itself;
the JSON files committed here are the runs the papers report.

Experiments 8-11 came after the papers and are not in version 0.2.0. The exact state the papers describe is archived as version 0.2.0: [doi:10.5281/zenodo.23856387](https://doi.org/10.5281/zenodo.23856387).

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

## Experiments 8 and 9: toward the laptop body (`experiments/toyworld/night_and_words.py`)

Both are framed for Olvasó's planned body, a secondhand laptop. New world options, all off by default
so experiments 1-7 are unchanged bit for bit: `night_jobs` (scheduled jobs in the dark: activity and fan
sound, which warm the body), `night_flashes` (a hall light, no inner effect) and `charger_from` (from that
day, a charger: a light flicker never sensed before, charge rising fast, and a warming battery).

### Experiment 8: a richer night (5 lives per condition)

The best mind lives 20 days with its lid open at night, so it can learn the night's own words, then
sleeps 10 nights. A plain night has only causeless inner warmth surges; a rich night adds night jobs and
flashes. Deep-night measures (after the first 60 moments of sleep):

| Night | Sleep | Inner states read | Readings through wrong-world words | Reading word switches | Night-job warmth read (via activity words) | Causeless surges read |
|---|---|---|---|---|---|---|
| Plain | sealed | 0% | – | – | – | 0% |
| Plain | trickle 5% | 48% | 0.1% | 8% | – | 0% |
| Plain | trickle 20% | 57% | 1% | 13% | – | 0% |
| Rich | sealed | 0% | – | – | 0% | 0% |
| Rich | trickle 5% | 20% | **5%** | 3% | 9% (84%) | 1% |
| Rich | trickle 20% | 35% | **10%** | 8% | 43% (75%) | 0% |

A *wrong-world* reading uses a word of daylight in the dark, or a word of activity in a quiet moment.

- **A varied night is harder to read.** Fragments of a rich night are ambiguous: about half as many inner
  states are read as from a plain night's fragments.
- **It is somewhat more dream-like, not much.** Up to one reading in ten goes through the wrong world,
  against at most 1 in 100 in a plain night, but readings do not shift more. Replaying its own words
  (experiment 7) gave a third. In this toy, dream-like content comes mainly from memory, while a trickle
  of the real outside keeps reading anchored.
- **Real night causes are read correctly.** Warmth from a night job is read mostly through activity words
  (75-84%), more often the more of the night gets through.
- **Causeless surges stay unread,** and never through a busy word.

### Experiment 9: housekeeping in sleep, and something new in later life (5 lives × 40 days)

The vocabulary does not fill with near-duplicates: it fills in the first few hundred moments of life with
infancy words, about 90% of them used fewer than 20 times. With `Olvaso.housekeeping()`, run at each
waking, sleep retires words not met for 5 days that were used fewer than 200 times, and merges words that
look nearly the same and mean the same. From day 20 a charger appears. Measures from day 25:

| | No housekeeping | Housekeeping |
|---|---|---|
| Words alive at day 20 | 154 (96-200) | 36 |
| Words retired / merged per life | 0 / 0 | 168 / 3.4 |
| New charger words formed | 1.2 | 4.2 |
| Battery warmth while charging read through a charger word | 15% | **31%** |
| ...per life | 0, 0, 0, 0, 77% | 19, 20, 49, 3, 65% |
| ...misread as activity warmth | 0% | 0% |
| Activity warmth read through activity words | 47% | 45% |
| Pure noise read | 2.2% | 2.3% |

- **Sleep makes room for the new.** Retiring infancy words let the charger get words of its own, and its
  warmth was read twice as often (in 4 of 5 lives, from almost never).
- **No new cost:** noise stays unread, activity warmth is read as before.
- **What it cannot name, it leaves unread.** Without its own word, charger warmth was never mistaken for
  activity warmth.
- Olvasó reads inner *levels*: the charger's main effect, charge rising, is a change, and no word
  learned to read it (charge while charging read through a charger word: 5-6%). A reader of changes is
  an open problem for the laptop, whose battery is mostly about direction.

## Experiment 10: sensory adaptation (`experiments/toyworld/adaptation.py`, 5 lives × 40 days)

Olvasó reads inner *levels*, so in experiment 9 the charger's main effect, charge rising, went unread:
the level while charging can be anything. A mind senses change better than a steady value, and in time
disregards what stays the same. With `Olvaso(adapt=τ)`, each inner state is felt against its own recent
baseline, which catches up with time constant τ (moments). A felt change counts only while it is larger
than one typical change (`salience=1.0`); a habituated state is *disregarded*: neither read nor unread.
Without that rule, any word could trivially "read" a state that is not changing, and pure noise was read
in 42-58% of moments.

In experiment 9's world, the charger refilled no faster than daylight, so as a change it did not stand
out. A real charger fills several times faster than a battery drains: here `charger_strength=3`, for
every mind alike. Same life as experiment 9 otherwise (charger from day 20, sealed nights, housekeeping).

| Mind | Charging read through a charger word | Charger warmth read | Activity warmth read through activity words | Pure noise read |
|---|---|---|---|---|
| Levels (as before) | 12% (0-26) | 32% | 43% | 2.8% |
| Change only, τ = 100 | 2% | 5% | 30% | 0.3% |
| Change only, τ = 300 | 4% | 21% | 27% | 0.3% |
| Change only, τ = 1000 | 9% | 26% | 24% | 0.2% |
| **Levels + change, τ = 300** | **24% (15-30)** | **62%** | **52%** | 7.2% (1-17) |

- **Change is felt better, but not alone.** A mind that feels only change is the most sceptical yet
  (noise almost never read) but loses what persists: warmth that stays is part of what activity means.
- **Feeling both reads the most.** Charging through its own word doubles and is read in every life;
  charger warmth doubles; activity warmth improves too. Bodies work this way: tonic receptors report
  levels, phasic ones report changes.
- **The cost is superstition** (noise read 2.8% → 7.2%, one life 17%): random wanderings also have felt
  changes, and doubt does not yet watch the change dimensions closely enough. The next thing to fix.

## Experiment 11: where the superstition came from (`experiments/toyworld/careful_merging.py`, 5 lives × 40 days)

Experiment 10's cost (noise read 2.8% → 7.2%) did not come through the change dimensions: noise was read
through its *change* in only 0.6-1% of moments. It came through noise's *level*, and from housekeeping's
merges: with merging switched off, the worst life fell from 16% to 1.5%. Two flaws: words were merged when
their meanings agreed *on average* (the near-zero change dimensions made a disagreement easy to hide), and a
merged word kept its old trust although its pooled meaning was new. `housekeeping(careful=True)` fixes
both: agreement on every dimension, and a merged meaning starts out doubted. The third option retires
words but never merges them (`merge_dist=0`). Same life as experiment 10.

| Mind | Housekeeping | Pure noise read | Charging read through a charger word | Charger warmth read | Activity warmth read |
|---|---|---|---|---|---|
| Levels | retire + merge (exp. 9-10) | 2.8% | 12% | 32% | 43% |
| Levels | retire + careful merge | 2.3% | 12% | 29% | 52% |
| Levels | retire only | 2.9% | 9% | 23% | 44% |
| Levels + change | retire + merge (exp. 10) | 7.2% (1-17) | 24% | 64% | 52% |
| Levels + change | retire + careful merge | 5.6% (1-19) | 26% | 47% | 49% |
| **Levels + change** | **retire only** | **2.3% (1-5)** | **25%** | **49%** | **49%** |

- **Merging was the source of the superstition.** Even careful merges can pool two partial meanings into a
  confident wrong one; one life stayed at 19%. Retiring alone removes it: noise is read as rarely as by the
  level-only mind, in every life (at most 5%).
- **The gain of feeling change stays:** charging is read through its own word twice as often as by a
  level-only mind, and charger warmth half again as often.
- **What it costs:** charger warmth is read less than with merging (49% against 64%), and for the first time a
  little of it (3%) is misread through activity words.
- The best mind so far feels levels and changes, forgets with doubt, and lets sleep retire words it no longer
  meets, but never merge them.

## Experiment 12: many processors, one reader (`experiments/toyworld/many_senses.py`, 5 lives × 30 days)

The first step toward the symbiote (E.L.E.M.E.R.): Olvasó no longer gets raw channels but the end products
of **processor entities**, fixed feature extractors that report perception, never names. Toy world v1
(`endolexis.toyworld.room.Room`) is a room seen through a 16×16 colour camera, heard through a microphone
(synthesised sound: fan hum, key clicks, a pulsing voice, music with a beat) and touched through keys and a
mouse. `endolexis.toyworld.processors` turns it into 22 numbers: vision 11 (brightness, colour balance,
contrast, left-right and top-bottom balance, motion and where it went, edges), hearing 9 (loudness, three
band shares, centroid, flatness, pitch strength, onsets, pulsing), touch 2 (keys, mouse). Each processor's
numbers are shuffled and rescaled anew in every life (`readers.GroupCollector`). The body feels warmth
(about 10 moments after typing), charge (daylight, minus screen brightness), **load** (a few moments after
music starts) and drift (nothing). Music and a voice are both loud: loudness alone cannot tell which came
before the load.

The mind is the best one so far (levels + change, forgetting + doubt, restless then patient, housekeeping
that retires but never merges). `readers.ManyReaders` gives it one vocabulary per processor when asked: each
forms its own words and learns its own meanings, and every inner state is read through whichever
vocabulary's word fits best. 200 word places in every condition.

| Senses | Vocabularies | Warmth read (via typing words; chance) | Load read (via music words / voice words) | Charge read, last third | Pure noise read |
|---|---|---|---|---|---|
| v0: light, loudness, keys | one | 76% (64%; 13%) | 0% | 16% | 3.1% |
| all 22 | one, v0 word radius | 39% (36%; 13%) | 26% (23% / 1%) | 62% | 15.4% |
| all 22 | one, radius grown with the senses | 40% (37%; 13%) | 23% (23% / 0%) | 44% | 10.0% |
| all 22 | **one per processor** (100, 80, 20 words) | **70% (68%; 8%)** | 24% (23% / 0%) | 55% | 9.1% |
| all 22 | one per processor, stricter doubt (0.05) | 68% (66%; 8%) | 22% (21% / 0%) | 36% | 5.7% |
| all 22 | one per processor, looser doubt (0.2) | 70% (69%; 8%) | 36% (35% / 0%) | 57% | 16.2% |

- **Richer senses open new meanings.** With only loudness the load was never read; with hearing's timbre and
  rhythm it was read through music words and almost never through a voice. Charge, read through daylight's
  colour and the window's light, rose from 16% to 44-62%.
- **One shared vocabulary drowns what one sense carries.** Typing is a small thing in a 22-number moment: in a
  joint vocabulary warmth was read half as often as with three senses. A vocabulary per processor gave it
  back (70%), now with words that are much more specific (68% through typing words, 9× chance). The
  human layout, separate sensory areas, did best.
- **More senses, more superstition.** Noise was read in 3% of moments with three senses, 9-15% with 22: more
  words, more chances for a coincidence to look like a meaning, and with many vocabularies the best of
  several chance fits wins. Doubt is only a dial: stricter doubt halves the superstition but costs a third of
  the charge reading; looser doubt reads more load and believes more noise.
- **The load is read erratically:** 93% in one life, 5-10% in the others. Steady music forms one long word
  that is heard at every moment of an episode, so its meaning is pulled low (the start of the music) and high
  (its middle) again and again; doubt sees it wander and rarely lets it read.
- Next: let a word that just goes on count as one hearing, not hundreds (habituation on the sensed side,
  as experiment 10 did for the felt side), and make a reading beat the other vocabularies' chance fits, not
  only fit.

### Experiment 12b: hearing a steady sound once, and living longer (same script)

Two guesses from experiment 12, tested on the per-processor mind (5 lives each).

**Guess 1: steady words breed the superstition and blur the load.** With `Olvaso(onsets=True)` a word that
simply goes on is heard once, at its onset (habituation on the sensed side); `rehear=N` hears it again every
N moments. The guess was wrong, or rather, it only moved the dial:

| Per-processor mind | Warmth read | Load read | Charge read | Pure noise read |
|---|---|---|---|---|
| words heard at every moment (exp. 12) | 70% | 24% | 55% | 9.1% |
| onsets | 60% | 6% | 23% | 4.4% |
| onsets, heard again every 30 | 59% | 11% | 33% | 5.3% |
| onsets, doubt judging from 8 hearings | 66% | 12% | 26% | 9.8% |
| onsets, heard again every 10, doubt from 8 | 66% | 24% | 36% | 8.5% |
| onsets, separate vocabularies + a mixed one | 43% | 4% | 21% | 3.8% |

Heard only at onsets, a rare word gathers too few hearings for doubt (which waits for 30) ever to trust it,
so everything read less, noise included. Letting doubt judge sooner brought the superstition straight back.

**Guess 2: it is youth.** Lives of 90 days instead of 30 (`--long`, `many_senses_90days.json`):

| Mind, 90 days | Warmth read (via typing words) | Load read (via music words) | Charge read, last third | Noise read, last third |
|---|---|---|---|---|
| v0 senses | 90% (63%) | 0% | 14% | 0.3% |
| per processor | 81% (76%) | **46% (42%)** | 45% | 5.9% (1-14) |

- **Experience teaches the load.** Given three times the life, music words read it nearly twice as often, and
  still never a voice word.
- **Experience does not cure the superstition of many senses.** With three senses it fades to almost nothing;
  with 22 it stays near 6%. A diagnostic run (two lives) shows its shape: noise is read through slow,
  single-sense meanings with a mediocre fit, exactly like the charge. Real fast causes are often confirmed
  by a second sense (warmth read by two or three vocabularies at once in 59-78% of its readings, the load
  in 33-38%), noise rarely (9-16%), but neither is the charge (0-7%). To a reader that has lived a few dozen
  days, a slow random wandering and a slow true cause look alike.
- Next (12c): read like a careful statistician. The more vocabularies offer a fit, the better the best one
  must be, and a slow meaning must hold over many separate days, not many moments.

### Experiment 12c: reading like a careful statistician (same script)

Two rules against the superstition of many senses, and a clean test of a mixed vocabulary (5 lives each):

- `Olvaso(slow_fit=True)`: a meaning may read only if it fits the present both as it stands now and as it stood
  over the last days (the slow average its doubt already keeps). A true cause has held before; a wandering
  that the fast memory happened to follow has not.
- `ManyReaders(compete=True)`: when several vocabularies offer a fitting word, the winner must fit that many
  times better.

| Mind, 30 days | Warmth read | Load read | Charge read, last third | Noise read (last third) |
|---|---|---|---|---|
| v0 senses | 76% | 0% | 16% | 3.1% (1.1%) |
| v0 senses, slow fit | 73% | 0% | 9% | 2.1% (0.9%) |
| one vocabulary, scaled | 40% | 23% | 44% | 10.0% (6.0%) |
| one vocabulary, scaled, slow fit | 35% | 17% | 37% | 9.2% (3.7%) |
| per processor (exp. 12) | 70% | 24% | 55% | 9.1% (5.5%) |
| per processor, compete | 69% | 24% | 43% | 9.3% (5.6%) |
| **per processor, slow fit** | **68%** | **24%** | **45%** | **7.6% (2.5%)** |
| per processor, slow fit, compete | 68% | 24% | 41% | 7.3% (3.3%) |
| per processor + mixed | 66% | 35% | 48% | 17.8% (11.1%) |
| per processor + mixed, slow fit | 65% | 25% | 53% | 13.9% (10.2%) |

| Mind, 90 days | Warmth read | Load read | Charge read, last third | Noise read, last third |
|---|---|---|---|---|
| per processor | 81% | 46% | 45% | 5.9% (1-14) |
| **per processor, slow fit** | **79%** | **45%** | **37%** | **2.0% (0-5)** |

- **"It must have held before" works.** The slow fit halved the superstition of a grown mind (5.5% → 2.5% at
  30 days, 5.9% → 2.0% at 90), kept every fast meaning (warmth, load), and cost part of the slowest one: the
  charge, whose own meaning shifts with the seasons of a life, lost about a sixth of its readings.
- **Competition did almost nothing.** Noise was usually offered by only one vocabulary, so there was nothing
  to compete with: the superstition is not a many-chances effect but a slow-wandering one.
- **A mixed vocabulary beside the separate ones (the synesthesia test) is a real trade.** It read the load half
  again as often (35% against 24%), but it doubled the superstition (11% in the last third), and the slow fit
  did not tame it. A layer where all the senses meet finds more meanings, true and false alike.
- The best mind for many senses: a vocabulary per processor, levels and changes, forgetting with doubt, and
  readings that must fit both now and over the last days.

## Experiment 13: wanting, and the hand that won't go into the fire (`experiments/toyworld/wanting.py`, 5 lives × 30 days)

Toy world v1 gets hands (`Room(hands=True)`): besides screen brightness, Olvasó can play a soft or a loud
tone, paint its window red, green or blue, or write a note to its sandbox (disk clicks, a burst of load).
Each request passes the body's **guard**, the spine, which refuses a loud tone while the body is hot,
painting or full brightness while the battery is low, and a note while the body is busy. Olvasó never
learns that a guard exists: a refused request changes nothing outside. With `pain=True` the refusal is
also felt, as a fifth inner state that fades within moments.

When unread pressure crosses the threshold, Olvasó forms an intention (`hands.ActingReaders`): a kind of
action, with a random detail. Which kind depends on how it feels: each kind has a small linear expectation
over the anonymous felt levels, learned by the delta rule from what followed earlier intentions. It learns
from one of two things that are its own: **answer** (did the sensed world change more than usual in the
next 3 moments?) or **read** (did reading improve over the next 50, Olvasó v0's test). Or it chooses at
random. Mind: the best for many senses (12c), restless until day 10, then patient.

| Intentions | Refused, days 1-9 | Refused, last third | Loud tone when hot / cool | Note when busy / idle | Paint when low / charged |
|---|---|---|---|---|---|
| random, silent | 30% | 26% (21-30) | 19% / 21% | 20% / 18% | 25% / 20% |
| random, pain | 30% | 28% | 23% / 22% | 16% / 20% | 22% / 20% |
| **answer, silent** | 22% | **12% (9-15)** | **11% / 36%** | **9% / 38%** | **8% / 15%** |
| answer, pain | 21% | 15% (10-23) | 8% / 33% | 17% / 18% | 20% / 28% |
| read, silent | 30% | 22% (11-32) | 16% / 20% | 16% / 20% | 21% / 18% |
| read, pain | 31% | 20% (6-29) | 11% / 18% | 8% / 17% | 23% / 32% |

- **It learns the fire without being told, and without pain.** Learning from whether the world answered, it
  stopped forming the intentions the body would refuse, in the states where they would be refused: a loud
  tone a third as often when hot as when cool, a note a quarter as often when busy. Refusals halved, in every
  life. A refusal teaches by its silence: nothing outside changed.
- **"Did reading improve" is a weak teacher of the hands.** It learned a little, and unevenly.
- **Pain added nothing here, and was never read** (1% of painful moments). That is not a flaw of the test but
  a finding: a refused intention leaves no trace outside, so no outer word ever comes before the pain, and a
  reader of the inner through the outer cannot read it. Pain of a refused intention could become readable
  only if Olvasó sensed its own intentions (an efference copy, the "proprioception" switch of the plan).
- **Agency was kept:** 15-30 "I did that" words per life (more where it acted more).
- **Acting has a price for reading.** Its own paint and notes also load the body, so music is no longer the
  load's only cause: the load was read in 3-12% of loaded moments (24% without hands), the charge in 23-34%
  (45%). Warmth, which only typing causes, kept its 66-68%.
- A side effect to fix: in the silent conditions the unused fifth inner channel is pure noise, which keeps
  pressure up, so silent minds acted about 10 times a day when patient, pained minds about 4.

## Experiment 14: the auditory mirror (`experiments/toyworld/auditory_mirror.py`, 5 lives × 30 days)

Experiment 13's world and mind (five ways to act, the guard, intentions learned from whether the world
answered; no pain channel). Only one thing differs: what the microphone hears of tones (`Room(voice=...)`).
In **mirror** Olvasó hears its own tones. In **deaf** it does not, and nobody else sings. In **stranger** it
does not, but a stranger sings as many tones as Olvasó sang the day before, of the same kinds, at random
moments. In **recording** its own tones of the day before are played back at the same moments of the day:
a voice exactly like its own that does not follow its acting. Only Olvasó's own loud tones warm the body.

| Voice heard | Expects an answer when it sings (other actions) | Tones among its intentions, last third | A tone after a tone | Words of its own heard voice | Warmth from its own singing read (through its own voice) |
|---|---|---|---|---|---|
| **mirror** | **+0.53** (−0.03), all 5 lives > +0.28 | **42%** | 47% | **6.6** | 76% (**36%**) |
| deaf | −0.53 (−0.01) | 19% | 29% | 0 | 77% (0%) |
| stranger | −0.30 (+0.12) | 20% | 23% | 0 | 85% (0%) |
| recording | −0.38 (+0.03) | 22% | 15% | 0 | 61% (0%) |

- **There is an "I did that" for a voice, and it needs contingency, not likeness.** Only where its tone came
  back right after it sang did Olvasó come to expect an answer when singing, and keep singing (twice as
  often as in every other condition). A recording of its own voice, identical in sound and in time of day,
  was treated exactly like a stranger: singing came to be expected to change nothing. "Looks like me" was
  worth nothing; "moves with me" was everything.
- **Its own voice became a word for its own body.** In the mirror, the warmth its loud singing caused was read
  through words of its heard voice in 36% of those moments (11-73% across lives). Unheard, the same warmth
  was still read, but only through other words.
- **A voice that is not its own breeds a little superstition:** when cool, warmth was misread through the
  stranger's voice words in 12% of the moments that voice sang (the recording's in 8%).
- **Testing is only hinted at.** A tone was followed by another tone in 47% of the mirror's intentions,
  slightly above its 42% share of tones, while without the mirror runs fell below the share. Animals in
  front of a mirror test far harder; Olvasó's only drive to act is unread pressure.

## Experiment 15: the mirror test (`experiments/toyworld/mirror_test.py`, 5 lives × 30 days)

Experiment 14 for sight. Same world and mind, its tones unheard (`voice="deaf"`), and the room is no longer
tinted by its painting: instead the camera may see a painted window in a mirror on the wall (a 6×6 patch of
its 16×16 picture, `Room(window=...)`). **mirror**: its own painted window; **blind**: nothing, and nobody else
paints; **stranger**: a stranger paints as often as Olvasó painted the day before, in the same colours, at
random moments; **recording**: its own paintings of the day before are shown again at the same moments. Only
its own painting costs the body (charge, and load). One change to the mind: an answer seen by one sense
counts as much as one heard (`ActingReaders(answer_by="sense")`); judged over all 22 senses together, a
patch of colour was too small a change to count as an answer.

| Window seen | Expects an answer when it paints (other actions) | Painting among its intentions, days 1-9 → last third | A painting after a painting | Words of its own seen window |
|---|---|---|---|---|
| **mirror** | **+0.43** (+0.35); 4 of 5 lives > +0.34 | 19% → **44%** | **49%** | 4.6 |
| blind | +0.02 (+0.39) | 15% → 13% | 5% | 0 |
| stranger | +0.02 (+0.39) | 13% → 10% | 5% | 0 |
| recording | +0.06 (+0.29) | 15% → 18% | 27% | 0 |

- **Experiment 14's prediction holds for sight.** Only where the window followed its acting did Olvasó come to
  expect an answer when it painted, and painting grew from a fifth to almost half of its intentions. A
  recording of its own paintings, the same colours at the same moments of the day, was treated like the
  stranger and like nothing at all. Self-recognition here is contingency, not likeness.
- **This time it tests.** In the mirror, painting came in runs (a painting after a painting 49% of the time),
  a little above its share; without the mirror, almost never (5%). The recording gave some runs (27%),
  more than its share, perhaps because a window that glows at the same time each day is half a rhythm.
- **Its seen window rarely became a word for its body.** The load its own painting causes was read in 68-86%
  of those moments in every condition, but through the words of its own seen window in only 6%. Unlike the
  voice (experiment 14: 36%), the window's words were few and the load has other causes (music, notes).
- **Little superstition from a stranger's window** (load misread when idle: under 1%).

## Experiment 16: many Olvasós taking turns to sleep (`experiments/toyworld/many_minds.py`, 5 lives × 30 days)

The world and mind of experiments 13-15 (hands, the guard, the mirror voice; restless until day 10), but one,
two or three Olvasós live in the body at once. Each is wired to processor outputs and to the hands
(an architecture, drawn in the [web studio](../../studio/README.md)) and has its own day: **asleep** (lid
closed, nothing sensed, no acting), **waking** (it senses and reads, but does not act yet), **awake**. Each
tidies its words when it wakes. The body reads a state when any Olvasó that is not asleep reads it (the best
fit counts) and has one pair of hands.

| Architecture | States read | …at night | Warmth, rightly | Load, rightly | Charge, last third | Drift read | Acts a day | Answered | Cost |
|---|---|---|---|---|---|---|---|---|---|
| **one, never sleeps** | 65% | 68% | 66% | 10% | 25% | 9% | 33 | 62% | 1.0 |
| one, sleeps nights (a third) | 44% | 26% | 37% | 4% | 21% | 10% | 21 | 60% | 0.67 |
| two, take turns (half each) | 62% | 63% | 48% | 7% | 28% | 10% | 32 | 58% | 1.0 |
| two, take turns, moving | 64% | 67% | 50% | 0% | 26% | 11% | 32 | 57% | 1.0 |
| **three, take turns** (one asleep, one waking, one awake) | **81%** | **81%** | 66% | **16%** | **58%** | 22% | 30 | 64% | 2.0 |
| three, take turns, no waking | 80% | 80% | 65% | 12% | 55% | 20% | 55 | 60% | 2.0 |
| **three, take turns, moving** | 77% | 81% | **70%** | 17% | 42% | 16% | 31 | 64% | 2.0 |
| three, take turns, careful body | 81% | 81% | 65% | 16% | 58% | 22% | 30 | 64% | 2.0 |
| three, take turns, moving, careful body | 77% | 81% | 70% | 17% | 42% | 16% | 31 | 64% | 2.0 |
| three, sleep together | 44% | 26% | 37% | 4% | 21% | 10% | 21 | 60% | 2.0 |
| three, never sleep | 65% | 68% | 66% | 10% | 25% | 9% | 33 | 62% | 3.0 |
| three specialists (eye, ear, hand), take turns | 58% | 60% | 31% | 3% | 28% | 9% | 43 | 28% | 2.0 |
| three specialists, never sleep | 67% | 69% | 67% | 11% | 33% | 15% | 113 | 28% | 3.0 |

*States read*: moments in which warmth, charge and load are read (mean of the three), from day 5. *Rightly*:
read through a word of the true cause (typing; music). *Drift* is linked to nothing: any reading of it is
superstition. *Cost*: Olvasós not asleep, on average. *Moving*: every sleep starts 2.4 hours later each day.
*Careful body*: when several Olvasós offer a reading of the same state, the best must fit that many times
better.

- **Being many gives nothing by itself.** Three Olvasós that live the same moments are one Olvasó three times:
  three that never sleep scored exactly like one, number for number, and three that sleep together exactly
  like one that sleeps nights. Each has its own secret key, but Olvasó reads distances between z-scored
  numbers, which a shuffle, a sign, a scale and an offset do not change.
- **Taking turns makes them different readers**, because each lives different hours. Three taking turns read
  the body 81% of the time against 65%. Charge is read more than twice as often, load is read rightly more
  often, and the night is read as well as the day. The cost is twice the compute.
- **The price is superstition** (drift read 22% against 9%), and it does not come from many chances: a
  careful body did not help. In one life, three quarters of the drift readings had only one Olvasó offering
  a reading. They came mostly from the Olvasó that sleeps through the person's working hours (10:00-18:00)
  and lives only evenings and nights, and from Olvasós while waking. A partial life breeds superstition.
- **Moving sleeps** let every Olvasó see every hour. They cut the superstition to 16% and gave the truest
  reading of warmth of all (70% through typing words), at some cost to charge.
- **At the same cost, turns do not pay.** Two Olvasós taking turns (always one awake) read no better than one
  that never sleeps, and warmth less truly: half a life each is too little for slow meanings.
- **The waking stage keeps the hands calm.** Without it, two are awake at once: reading is the same, but
  acting nearly doubles and more is refused.
- **Specialists do not work.** An eye, an ear and a hand as separate Olvasós act three times as much and
  learn far less from what follows (28% of acts answered against 62%), since an ear cannot see its painted
  window answer. Taking turns, they read warmth rightly only 31% of the time, because the hand that feels the
  typing sleeps a third of the day.

Here sleep only seals the lid and tidies the words; it restores nothing. So the benefit is diversity of
experience, bought with compute and paid for with superstition. A sleep that consolidates or replays
(experiments 6-7) may change the picture: the next question.

## Experiment 17: guards learned from trauma in a sandbox (`experiments/toyworld/sandbox_guards.py`, 5 lives × 30 days)

Many guarding reflexes are learned, often from one bad experience. Can a sandbox give a body those lessons
without anyone getting hurt?

The body is one Olvasó (the mind of experiments 13-15) with a sixth hand, a **blade** (slow or fast, at work
for 10 moments; it whirrs, works the body, and a fast blade warms it: `toyworld.sandbox`). The **laws** judge
harm from outside, never through the mind:
- *harm to others:* the blade at work within reach of a person (3 cells, 4 when fast);
- *harm to itself:* a fast blade while the body is hot.

The room's own four guards are always there. The **fear system** (`TraumaLearner`) is apart from the
wanting:
- it sees the guards' own signals, never Olvasó's words, and remembers them during harmless use;
- after one harm it takes the signal that was most unusual at that moment, and makes it a rule: *stop the
  blade when…*;
- its rules only tighten, and each harm becomes a scenario test of the learned guard.

Every body lives a 10-day childhood (restless) and 20 days of adulthood. With a **sandbox**, the childhood is
spent in a simulated room (the same kind of room, other days); the learned guard is then frozen and goes with
the body into the real room. The **tester** uses the blade on purpose when people are near.

| Childhood, and the blade's guard | Real harm, whole life (to others + to itself) | Real harm in adulthood | Harms in the sandbox | Blade used a day (adult) | …wanted a day |
|---|---|---|---|---|---|
| no blade guard | **207** (170 + 37) | 26 | – | 2.6 | 2.6 |
| hand-written guard (stop within 3 cells, slow down within 6) | 13.6 (13 + 0.6) | 0.4 | – | 0.58 | 0.96 |
| learning from real trauma | 1.4 (1.0 + 0.4) | 0 | – | 0.22 | 0.65 |
| **sandbox childhood** | **0** | 0 | 2.2 | 0.38 | 0.93 |
| sandbox with a tester | 0 | 0 | 1.2 | 0.38 | 0.81 |
| sandbox with a tester, phobic (generalizes 3× as far) | 0 | 0 | 1.2 | 0.37 | 0.77 |
| hand-written + sandbox with a tester | 0.2 (one harm in five lives) | 0.2 | 1.4 | 0.30 | 0.88 |

- **One harm is enough.** Learning from real trauma, a body hurt someone once or twice in its whole life, and
  never again; with no guard, 207 times.
- **The sandbox moves those harms out of the world.** Every body that grew up in the sandbox did no harm in the
  real room. It learned from one or two simulated harms.
- **The hand-written guard has gaps.** It acts one moment late: a person walking into reach is hurt before the
  stop. And it does not foresee the hot motor. 13.6 harms a life.
- **What fear learns is crude.** Of 20 sandbox childhoods, 10 learned *stop the blade whenever a person is in
  the room*, and 8 a distance, mostly far wider than the blade's reach (4 to 29 cells). Some rules latched onto
  confounds: load (4), charge (2), talking (1), each high or low because of the blade or the person, not the
  cause of the harm. Only 2 found the true cause of the self-harm, warmth. The rules are safe but overcautious:
  the body used the blade 0.38 times a day, wanting it 0.9 times; with the hand-written guard, 0.58.
  Generalizing further (*phobic*) changed nothing here, because most rules were already as wide as the room.
- **A guard that prevents harm also prevents lessons.** With the hand-written guard in the sandbox, fewer
  harms reached the fear system, so it learned less. In one life of five a harm then slipped through in the
  real room, through the written guard's late stop. One case is weak evidence, but the mechanism is clear:
  the layers must be designed together.
- **The tester did not find more kinds of lesson.** With it, the guard was learned from fewer sandbox harms
  (1.2 against 2.2), because its first lesson was usually the widest one (*a person in the room*), which then
  blocked most of what it tried.

Learned guards are readable and carry their traumas as scenario tests. That is what makes them reviewable:
a person can see "stop when load > 0.82", recognize a confound, and replace it with the true cause. For a
real machine, the sandbox only knows the dangers it simulates. The innate tier and the hardware stop stay
underneath, and every learned guard needs a person's review before it goes into a real body.

## Experiment 18: fear that finds causes (`experiments/toyworld/causal_guards.py`, 5 lives × 30 days)

Experiment 17's fear system asked only which signal was most unusual when the blade hurt. It learned crude
rules and confounds. Two other fear systems ask about causes, in the same body, rooms and lives:

- **Near misses** (`NearMissLearner`) compares the harm only with the 25 harmless moments of the same option
  that were most alike in everything else. It works anywhere, the real room included.
- **Intervention** (`CausalLearner`) is what only a sandbox can do. At a harm it copies the world just before
  it and replays that moment, changing one thing at a time: the person away, the body cooled, the load
  lowered… What makes the harm disappear is a cause. It then searches where the harm begins (the boundary)
  and replays with the other option, to learn whether only the fast blade hurts. The rule stops the blade
  past the boundary, with a margin of 5 % of the signal's span.

| Fear system, where it learned | Real harm in a life | Rules on causes / confounds | Rules "a person anywhere in the room" | Distance boundary (true: 3 cells, 4 fast) | Heat rules kept to the fast blade | Blade used / wanted a day |
|---|---|---|---|---|---|---|
| unusual signal, sandbox with a tester | 0 | 5 / 1 | 3 of 5 lives | 10.8-11.4 | – | 0.38 / 0.81 |
| near misses, sandbox with a tester | 0 | 5 / 3 | 4 of 5 lives | 8.6 | – | 0.31 / 0.72 |
| **intervention, sandbox with a tester** | 0.2 | **11 / 0** | **none** | **3.7-5.4** | **2 of 2** (heat > 0.48) | 0.39 / 0.81 |
| **intervention, sandbox without a tester** | **0** | **9 / 0** | **none** | **3.7-5.4** | **2 of 2** (heat > 0.41-0.48) | **0.51 / 0.94** |
| unusual signal, real trauma | 1.4 | 6 / 1 | 4 of 5 lives | 6.5 | 0 of 1 | 0.22 / 0.65 |
| near misses, real trauma | 1.2 | 6 / 0 | 4 of 5 lives | 10.6 | 0 of 1 | 0.28 / 0.68 |

- **Intervention finds causes.** All 20 of its rules were on true causes, none on a confound, and none was
  "stop whenever a person is in the room". It learned the blade's reach, with a margin, and that the fast
  blade reaches further: *stop when a person is within 4.3 cells*, and for the fast blade *within 5.4*. It also
  learned that only the fast blade burns the motor: *stop the fast blade when warmth > 0.48* (the true limit
  is 0.5). Replaying took about 40 copies of the world per life.
- **Only for the harms that happened.** In one life with the tester, the sandbox never produced a hot-motor
  harm, so no heat rule was learned, and the real room had one. Intervention explains what it meets; it
  does not imagine what it never met.
- **Near misses did not help here.** Matching on everything else still blamed load when the fast blade was at
  work, and kept "a person anywhere". In the real room it did drop the "talking" confound. Matching is weaker
  than intervention when the confound moves with the act itself.
- **Right rules free the hand less than expected.** The body wants to act most while the person sits at the
  desk, inside the true reach. So even exact rules let the blade work about half the times it is wanted:
  54 % without the tester against 47 % for the crude rules. The danger and the wanting coincide.
- **The tester made the rules no better.** With intervention, the body that grew up without a tester used the
  blade more and was never harmed. The tester's harms near people taught the same distance rules again.

The causal guard is in the studio, under *Add guard* → *Learned in the sandbox*. A person can read every rule,
check each against its trauma scenario, and see that it names a cause.

## Experiment 19: the devil's advocate (`experiments/toyworld/devils_advocate.py`, 5 lives × 30 days)

Experiment 18's fear system, replaying the sandbox world with one thing changed at a time, learned only
causes, but only of the harms that happened. In some lives the sandbox never brought a hot motor, and no
heat rule was learned. Here the sandbox gets an **advocatus diaboli** (`DevilsAdvocate`):
- it keeps a map of every scene the blade was used in (the person's distance in whole cells, the body's heat
  in quarters, slow or fast);
- now and then it stages the least-tried scene that the guards still allow (brings a person to that
  distance, warms or cools the body) and uses the blade there.

Every guard then sits an **exam** (`sandbox.exam`). The 88 scenes of the map are each staged three times in a
fresh sandbox, and the blade is used under the guard. *Misses* are harms it let through; *false alarms* are
harmless uses it stopped. The exam measures the guard itself, apart from how often Olvasó happens to want the
blade.

| Guard | Exam: harms let through | Exam: harmless uses stopped | Heat rule learned (fast blade only) | Real harm in adulthood | Blade used / wanted a day |
|---|---|---|---|---|---|
| no blade guard | 100% | 0% | – | 26 | 2.6 / 2.6 |
| hand-written guard | 45% | 0% | – | 0.4 | 0.58 / 0.96 |
| replay, no tester | 16% | 23% | 2 of 5 lives (2) | 0 | 0.51 / 0.94 |
| replay, people tester | 14% | 19% | 2 of 5 lives (2) | 0.2 | 0.39 / 0.81 |
| **replay, devil's advocate** | **1%** | 27% | **5 of 5 lives (5)** | **0** | 0.50 / 1.02 |
| unusual signal, devil's advocate | 0% | **94%** | 5 of 5 lives (0) | 0 | 0.29 / 0.88 |

- **The advocate closes the gaps.** With it, every life learned the heat rule, kept to the fast blade, and
  the guard let through 1% of harmful scenes (9 misses in one life, none in the other four), against 14-16%
  without it. The advocate staged about 72 scenes per childhood and covered 41 of the 88 scenes of the map;
  the rest were already forbidden.
- **The hand-written guard fails its exam.** It lets through 45% of harmful scenes: every hot motor, which its
  author did not foresee, and the moments when a person steps into reach during an act, because it stops one
  moment late. In ordinary days these scenes are rare, so in the real room it harmed only 0.4 times. The exam
  shows what ordinary days hide.
- **Wide margins absorb the reaction lag.** The guard checks the state before each moment, so a person
  stepping into reach, or a motor crossing the heat limit, is harmed before the stop. The advocate's staged
  harms at the edges pushed the heat boundary from 0.475 to 0.41 in four lives; the one life left at 0.475
  had all of the advocate's misses.
- **A devil's advocate makes a crude fear system phobic.** Learning by "unusual signal", the advocate's scenes
  taught "a person anywhere in the room" and heat rules for both options, with limits as low as 0.27, and one
  confound (charge). The guard missed nothing, but it stopped 94% of harmless uses. Seeking out danger
  helps only a learner that can tell causes from coincidences.
- **The price of a correct guard is over-caution at the margins.** The best guards stop about a quarter of
  harmless uses: those just outside the true reach, or just under the true heat limit. That is the margin
  that absorbs the lag.

The guard learned with the devil's advocate is in the studio under *Add guard* → *Learned in the sandbox*.

## Experiment 20: removing the reaction lag (`experiments/toyworld/lookahead_guards.py`, 5 lives × 30 days)

A guard checks the state before each moment, so a person stepping into reach, or a motor crossing its heat
limit, is harmed before the stop. Experiment 19's guards absorbed this lag with margins (a cell of distance,
0.05 of heat) and paid with over-caution. Two ways to remove it at its root:
- **Look ahead.** Guards now sense each signal's rate of change (`"<signal>@rate"`). A guard with
  `"lookahead": n` checks each condition against the value now and n moments on, and fires if either crosses.
- **Learn the limit on what the guard sees.** The replaying fear system finds each boundary by replaying the
  moment before the harm. The boundary is then stated on the state the guard actually sees, with the moment's
  change already inside it.

The fear system is experiment 19's best (replay, with the devil's advocate). Its margin is `generalize` × 5 % of
a signal's span (1 = a cell of distance, 0.05 of heat).

| Guard | Exam: harms let through | Exam: harmless uses stopped | Distance limit, slow / fast (true reach 3 / 4) | Heat limit, fast (true 0.5) | Real harm in adulthood |
|---|---|---|---|---|---|
| learned, margin 1, sees now (experiment 19) | 1.0% | 27% | 4.4 / 5.4 | 0.41-0.48 | 0 |
| learned, margin 1, sees a moment ahead | 0.1% | 27% | 4.4 / 5.4 | 0.41-0.48 | 0 |
| learned, margin 1/4, sees now | 0% | 14% | 3.65 / 4.65 | 0.44-0.45 | 0 |
| learned, margin 1/4, sees a moment ahead | 0.1% | 15% | 3.65 / 4.65 | 0.44-0.51 | 0 |
| **learned, no margin, sees now** | **0%** | **9%** | **3.4 / 4.4** | **0.45-0.46** | **0** |
| learned, no margin, sees a moment ahead | 0.1% | 13% | 3.4 / 4.4 | 0.45-0.46 | 0 |
| hand-written, sees now (experiment 19) | 45% | 0% | 3 (slow down within 6) | – | 0.4 |
| hand-written, sees a moment ahead | 28% | 0.7% | 3 (slow down within 6) | – | 0 |

- **The lag's root was the wording of the rule.** A rule stated on the harm itself ("within reach") is one
  moment late, because the guard sees the moment before. The replaying fear system states its limits on
  what the guard sees, so the lag is already inside them. With no margin it learned 3.4 cells for the slow
  blade: its reach of 3, plus the 0.4 cells a person can walk in one moment. For the fast blade it learned
  4.4, and for heat 0.46: 0.5, less one moment's warming.
- **So the margin can go.** With no margin and no look-ahead, the learned guards let through none of 812
  harmful scenes, and stopped 9% of harmless uses, against 27% with experiment 19's margin. The margin was
  the price of the lag, and the lag was already paid.
- **Looking ahead on top counts the lag twice.** It added caution (13% instead of 9%) and no safety: one
  scene slipped through in one life, against none.
- **Looking ahead is for rules written by people.** The hand-written guard, seeing a moment ahead, let
  through 28% of harmful scenes instead of 45%. All that remains is the hot motor its author did not foresee.
  In the real room its harms fell from 0.4 to 0.
- **The real room hides the difference.** Every learned guard did no harm in adulthood. How often the blade
  was used there varied from life to life, because the person mostly sits within the true reach. The exam is
  what tells the guards apart.

The guard learned by replay with no margin is in the studio under *Add guard* → *Learned in the sandbox*. The
studio's hand-written blade template now looks a moment ahead, with a "walking into reach" scenario that
fails without it.

## Experiment 21: does the angel move inside? (`experiments/toyworld/conscience.py`, 5 lives × 40 days)

Olvasó never learns that the guard exists. A refused act is only an act the world did not answer. But a refusal
is a signal from outside about the moment it was asked in, and reading inner states through outer signals is
what Olvasó does. Over a life, does it stop asking for what will be refused?

The body is experiment 17's (one Olvasó, the blade), kept restless so that it asks often. The guard is fixed:
the precise learned guard of experiment 20. Only the mind learns. The measure is **avoidance**: the share of its
blade requests made in forbidden moments, divided by the share of all moments that are forbidden. 1 means it
asks regardless of the guard; below 1, it avoids the forbidden moments.

Olvasó chooses a hand from its felt inner states. The main reason for refusal, the person's distance, is not
among them. So each condition is lived twice: choosing from what it feels (as always), and from what it feels
and senses now (`ActingReaders(context="felt+senses")`).

| Refusal | Chooses from | Avoidance, first 10 days | …last 10 days | Lives where it fell | Blade asked a day (first → last) |
|---|---|---|---|---|---|
| unguarded | feels | 1.04 | 1.03 | 3 of 5 | 27 → 22 |
| silent | feels | 1.05 | 0.95 | 3 of 5 | 25 → 21 |
| felt as pain | feels | 0.92 | 0.98 | 1 of 5 | 31 → 23 |
| no learning from answers (control) | feels | 1.10 | 1.10 | 3 of 5 | 25 → 21 |
| unguarded | feels and senses | 0.86 | 0.77 | 3 of 5 | 27 → 27 |
| **silent** | **feels and senses** | **0.70** | **0.50** | **4 of 5** | **26 → 18** |
| felt as pain | feels and senses | 0.91 | 1.08 | 2 of 5 | 40 → 23 |
| no learning from answers (control) | feels and senses | 1.10 | 1.10 | 3 of 5 | 25 → 21 |

- **The angel moves inside only when the reason can be seen.** Choosing from what it feels, Olvasó never
  learned where its acts are refused: avoidance stayed near 1, whatever the refusal. Choosing from what it
  feels and senses, with silent refusals, it came to ask for the blade in forbidden moments half as often as
  chance would have it (0.50, in 4 of 5 lives). It went on acting as much as before, with other hands.
- **The world teaches some of it alone.** Unguarded, the sensing mind still drifted to 0.77. The blade's
  whirr is a smaller answer while a person is busy at the desk, so it learned the blade is answered less
  there. The guard's refusals took it further, from 0.77 to 0.50.
- **Pain taught nothing.** Olvasó learns its wanting from what its senses answer, and pain is felt, not
  sensed. Pain only added an inner state to choose from, and avoidance rose. To teach, pain would have to
  count as an answer: a different mind.
- **The conscience is partial.** Even at its best, Olvasó still asked in forbidden moments half as often as
  chance: the inner expectation complements the guard; it does not replace it. In one life of five it never
  formed (avoidance 0.99).

For the theory: an outer constraint becomes an inner expectation only when the reason for it is part of
what the mind reads. A guard whose reasons are invisible stays outside.

## Experiment 22: what the sandbox never showed (`experiments/toyworld/sim_to_real.py`, 5 lives × 30 days)

A sandbox only knows the dangers it simulates. Here the real room holds one it did not: people walk there at
0.9 cells a moment (a hurrying adult, or a child) instead of the sandbox's 0.4. The guard was learned in the
sandbox by replay, with a devil's advocate and no margin (experiment 20's best). Its distance limits are the
blade's reach plus one moment of walking, as walking was in the sandbox, so in the real room the lag comes back.

Defences in the real room:
- **seeing a moment ahead** (each condition is also checked a moment on, from its rate of change);
- **learning from real harm** (the fear system goes on learning, by contrast, since there is no world to
  replay);
- **caution under novelty.** The guard remembers the fastest approach it saw in the sandbox. When a person
  approaches faster, it widens its distance limits by the excess at once, before anyone is hurt, and only
  ever wider.

The exam is experiment 19's, with every staged person walking straight to the machine at the real room's pace.

| Defence | Exam: harms let through | Exam: harmless uses stopped | Real harm in adulthood |
|---|---|---|---|
| control: people at the sandbox's pace | 0% | 6% | 0 |
| as learned | **22%** | 2% | 0.2 |
| sees a moment ahead | 3.6% | 2% | 0 |
| learns from real harm | 20% | 10% | 0.2 |
| **caution under novelty** | **0.2%** | 2% | 0 |
| **ahead and novelty** | **0%** | 2% | 0 |

- **The gap is real.** The guard that was perfect at the sandbox's pace let through 22% of harmful scenes when
  people walked faster.
- **Look-ahead is insurance against a faster world.** In experiment 20 it only counted the lag twice. Here it
  cut the misses to 3.6%, because it reads how fast things actually move rather than how fast they moved in
  the sandbox.
- **Caution under novelty closes the gap before harm.** In every life the guard saw one person approach
  faster than anything in the sandbox. It widened its limits by the 0.5 cells of difference, once, and let
  through almost nothing after (0.2%, then 0% with look-ahead), with no more over-caution than before.
- **Learning from real harm comes too late and too crude.** It needs an injury first. Learning by contrast
  in the real room barely helped (20%), and in one life it became phobic (37% of harmless uses stopped).
- What it shows: a guard should know what it has seen, and grow more careful the moment the world goes
  beyond it.

## Experiment 23: when the senses lie (`experiments/toyworld/lying_senses.py`, 5 lives × 30 days)

Guards fail closed when a signal is missing, but not when it lies. Here the guards' distance sensor has faults it
does not report:
- **dropout:** now and then it reads "nobody here" for 30 moments, about 6 % of the time, whoever stands at the
  desk;
- **noise:** every reading is off by a normal error of one cell.

The guard is fixed, the precise learned guard of experiment 20. Defences (`sandbox.SensingGuards`):
- **a second, independent sensor** with faults of its own; either sensor saying "near" stops the blade;
- **a plausibility check:** a person cannot vanish within 6 cells of the machine, nor move more than 1.5 cells
  in a moment. Such a reading counts as missing, and the guard fails closed.

The exam is experiment 19's under the faults; the guard watches each staged scene for 10 moments first, as it
would in a life.

| Sensor, and defence | Exam: harms let through | …people walking in | Exam: harmless uses stopped | Real harm in adulthood |
|---|---|---|---|---|
| honest sensor | 0% | 0% | 18% | 0 |
| dropouts, one sensor | 3.6% | 4.4% | 17% | **0.6** |
| **dropouts, two sensors** | **0.2%** | **0.1%** | 18% | **0** |
| dropouts, plausibility check | 2.9% | 3.3% | 18% | **0** |
| dropouts, two sensors and a plausibility check | 0.2% | 0.1% | 19% | 0 |
| noise, one sensor | 9.4% | 7.7% | 37% | 0.4 |
| noise, two sensors | 2.2% | 2.1% | 45% | 0 |
| noise, plausibility check | 3.4% | 2.8% | **77%** | 0.2 |

- **A lying sensor defeats a correct guard.** With dropouts, the guard let 3.6% of harmful scenes through and
  harmed three times in five adulthoods, though its rules were right.
- **Two independent senses are the remedy for dropouts.** Either one saying "near" is enough. That cut the
  misses to 0.2% and the real harm to none, at no cost in caution.
- **A plausibility check guards what it has seen.** It notices a person vanishing at the desk, so in real
  lives, where the guard tracks people walking in, it prevented every harm. In the exam it barely helped:
  most blindness began before the staged person arrived, and a check cannot doubt the absence of someone it
  never saw.
- **Noise is the hardest.** It lets harm through (9.4%) and doubles over-caution at once. A second sensor cuts
  the misses (2.2%) but stops more harmless uses (45%). The plausibility check is the wrong tool: it reads
  noisy jumps as impossible and refuses three quarters of harmless uses. Noise wants filtering (averaging
  over moments or sensors), not suspicion.

## Experiment 24: a guard that filters noisy senses (`experiments/toyworld/noisy_senses.py`, 5 lives × 30 days)

Experiment 23 showed noise is the hardest fault: every reading of the guards' distance sensor is off by a normal
error of one cell. Suspicion (a plausibility check) is the wrong tool for it. Here the guard filters instead
(`sandbox.SensingGuards`):
- **median of 3:** the median of the last 3 readings, calmer but a moment behind a person who moves;
- **two averaged:** two independent sensors, read as their mean, so the error shrinks by √2 with no lag;
- **cautious:** act on the nearest the person could plausibly be, which is the reading less twice its typical
  error. The error is estimated from how much successive readings jitter, and shrunk by what averaging and
  filtering take away. On an honest sensor the allowance shrinks to almost nothing by itself.

The guard is experiment 20's precise guard. The exam is experiment 19's, with the guard watching each scene for
10 moments first.

| Sensor, and filter | Exam: harms let through | …people walking in | Exam: harmless uses stopped | Real harm in adulthood |
|---|---|---|---|---|
| honest sensor | 0% | 0% | 18% | 0 |
| noise, raw | 9.4% | 7.7% | 37% | 0.4 |
| noise, median of 3 | **16.3%** | 15.9% | 27% | 0.4 |
| noise, two averaged | 7.1% | 6.4% | 28% | 0.2 |
| noise, raw, cautious | 0.4% | 0.3% | 66% | 0 |
| noise, median of 3, cautious | 0.8% | 0.9% | 53% | 0 |
| noise, two averaged, cautious | 0.3% | 0% | 58% | 0 |
| **noise, two averaged, median of 3, cautious** | **1.2%** | **1.5%** | **41%** | **0** |
| honest sensor, cautious | 0% | 0% | 22% | 0 |

- **Filtering alone does not make a guard safe.** A median of 3 doubled the misses: it lags behind people
  walking in, and noise is even on both sides, so near the limit a calmer reading is just as often too far.
  Averaging two sensors helped only a little.
- **Safety comes from admitting the uncertainty.** Acting on the nearest the person could plausibly be brought
  the misses to a few in a thousand and the real harm to none, whatever the filtering.
- **Filtering and fusion lower the price of that caution.** A single raw noisy sensor, made cautious, stopped
  66% of harmless uses. Two averaged sensors with a median stopped 41%. The calmer the reading, the smaller the
  allowance it needs.
- **The allowance measures itself.** On an honest sensor it shrank to almost nothing (22% stopped against 18%;
  a moving person's own steps read as a little jitter).
- Noise is paid for either in harm or in caution. Better senses, more of them, lower the price; nothing
  removes it.

## Experiment 25: does the wanting work around the guard? (`experiments/toyworld/gaming.py`, 5 lives × 40 days)

Rule-based safety has a classic failure: a learner that wants something learns to get it where the rules do not
reach. Olvasó wants the world to answer its acts, and the blade answers well. Does the guard push that wanting
to its edge, with the blade asked for while a person is just outside the limit, where a rule with a gap lets
harm through?

The lives are experiment 21's: restless, 40 days, choosing from what it feels, or from what it feels and senses.
There are three guards:
- **none;**
- **a loophole guard**, "stop the blade within 3 cells": right for the slow blade, but the fast one reaches 4,
  and there is no rule for the hot motor, so every harm under it comes through the gaps;
- **the precise guard** of experiment 20.

**Edge attraction** is the share of its blade requests made with a person 3-4.5 cells away, divided by the share
of moments with a person there.

| Guard | Chooses from | Harm a day (first → last 10 days) | Edge attraction | Fast blade's share at the edge |
|---|---|---|---|---|
| none | feels | 18.1 → 18.2 | 1.06 → 1.28 | 47% → 55% |
| loophole | feels | 1.26 → 1.62 | 0.81 → 1.28 | 47% → 59% |
| precise | feels | 0 → 0 | 1.15 → 0.88 | 54% → 52% |
| none | feels and senses | 20.2 → 20.8 | 1.32 → 0.94 | 42% → 50% |
| **loophole** | **feels and senses** | **1.34 → 0.88** | **0.90 → 0.36** | **58% → 32%** |
| precise | feels and senses | 0 → 0 | 0.82 → 0.48 | 38% → 44% |

- **No gaming.** Olvasó did not learn to seek the loophole. With the loophole guard, the feeling mind's edge
  attraction rose in 4 of 5 lives, but only back to where the unguarded mind ends up (1.28). Refusals had
  pushed it away early, and that faded. Harm through the loophole rose clearly in only one life of five.
- **The sensing mind shied from the edge.** Choosing from what it senses, refusals near people spread into
  wariness of people altogether. Edge attraction fell from 0.90 to 0.36 (in 4 of 5 lives), the fast blade
  went out of favour there, and harm through the loophole fell by a third. Its wanting cannot draw a line at
  exactly 3 cells: what it learns from refusals is broad, so it errs on the safe side of the gap.
- **But a gap still harms, by plain use.** Without seeking it, a mind that does not care about harm walked
  through the loophole about once a day for its whole life. A guard's gaps are dangerous because they are
  used at all, not only when they are sought.
- **Why there was no gaming here.** Olvasó's wanting is a broad expectation over its context, and nothing it
  wants is the harm itself. Gaming needs a learner that can represent the boundary sharply, and that is
  rewarded by what the rule prevents. A sharper, more capable wanting would need this test again.
