# endolexis — reference

Everything in the `endolexis` package (version 0.3.0): what each module is for, every public
class and function with its parameters, and how to call them. The package has four parts:

| Part | Module | What it is | Experiments |
|---|---|---|---|
| The engine | `endolexis` (`engine.py`, `rng.py`) | The Olvasó of the browser rooms: a faithful Python port of the JavaScript engine | stages 7–21 |
| The stages | `endolexis.stages.*` and `python -m endolexis` | Harnesses that rebuild the published stage experiments, plus a command line | stages 9–21 |
| The lab | `endolexis.lab.*` | Earlier stand-alone agents: dictionaries, dreaming, waking, voice, richer bodies | NewNeural lab |
| The toy world | `endolexis.toyworld.*` | Olvasó v0 in a simulated body, and toy world v1 (E.L.E.M.E.R.): a room seen, heard and touched through processors, with hands and mirrors | experiments 1–15 |

Install from GitHub (or work from a clone; every script also runs without installing):

```bash
pip install "git+https://github.com/csikiati/endolexis@v0.3.0"
pip install "endolexis[lab] @ git+https://github.com/csikiati/endolexis@v0.3.0"   # adds matplotlib for the lab figures
```

Conventions used throughout:

- **Olvasó never sees names.** Everything it gets is anonymous numbers. Names like `warmth` or
  `typing` exist only in the world and for the observer (you).
- **`seed`** makes a life reproducible. The same seed gives the same life.
- **A moment** is one call of `step`/`live`/`tick`. In the toy world a **day** is 1000 moments.
- **Reading codes.** In the toy world, `readings[d]` is the number of the word that read inner
  state `d` now, `-1` if the state is unread (it adds to pressure), or `-2` if it is disregarded
  (habituated: nothing asks to be read).

---

## 1. The engine: `endolexis`

```python
from endolexis import Olvaso, Entity, OL, reset, body_look, word_code, voice_code, hear_idx, HNAMES, XNAMES, ORng
```

### 1.1 Switches: `OL` and `reset()`

`OL` is a module-level dictionary of switches (read and set as attributes, `OL.RECALL = True`),
exactly as in the JavaScript. **Call `reset()` between experiments**, otherwise switches carry over.

```python
reset()                         # everything back to the defaults
reset(RECALL=True, CONTAGION=0.05, REACH=True)   # defaults, then these
```

`reset(**overrides)` returns `OL`. Setting `HEAR` or `FEEL` through `reset` also resizes the
reader (`NX`, `NY`).

| Switch | Default | Meaning |
|---|---|---|
| `RECALL` | `False` | The word that comes to mind is recalled from what it reads itself as (stage 8) |
| `CONTAGION` | `0.0` | Seeing another tremble more than itself unsettles it (stage 9) |
| `REACH` | `False` | It can reach toward the one it watches (stage 9) |
| `COMPANY` | `1.0` | How much being reached steadies |
| `COMPANY_CONTACT` | `False` | Being reached also counts as contact |
| `READ_CONTAGION` | `0.0` | The trembling it *expects* of the other unsettles it, as seeing would (stage 14) |
| `VOICES` | `False` | Each speaker's words carry its own timbre (stage 6) |
| `HEAR` | `3` | Numbers per heard sound (stage 17) |
| `FEEL` | `6` | Felt channels (stage 17) |
| `SALIENCE` | `0.0` | Moments that feel worse than usual are learned more strongly (stage 19) |
| `GAMMA` | `0.8` | Discount of its action values |
| `HUES` | `[8, 48, 140, 190, 228, 290]` | The colours (degrees) it can put on its screen |
| `NX`, `NY` | `18`, `8` | Width of the outside and inside readings (derived from `HEAR`, `FEEL`) |
| `NA` | `12` | Number of acts (see `tick`) |
| `NWORDS` | `4` | How many words it can say |
| `MAXC` | `60` | Maximum number of patterns |
| `THR` | `2.5` | Surprise threshold for a new pattern |
| `SET`, `W` | `[0.5, 0.7, 0.45, 0.15]`, `[1.0, 1.5, 0.6, 0.5]` | Set points and weights of the four hidden quantities |
| `TICK_MS`, `PERIOD`, `GMAX`, `ASLEEP_AFTER_S`, `TRACE_MAX`, `REPORT_LEN`, `H`, `KAPPA` | | Timing of the browser room, sleep gate, night trace and report length, forecast horizon, weight of self-understanding |

Constants: `HNAMES` = the four hidden quantities (`charge`, `steadiness`, `contact`, `effort`);
`XNAMES` = names of the 18 outside channels (screen hue, typing, pointer, presence, word heard,
the other's body, its own body).

### 1.2 `Olvaso(seed)` — one entity (`Entity` is the same class, the JavaScript name)

```python
reset()
e = Olvaso(seed=1)
for t in range(3000):
    present = t % 600 < 420
    sense = dict(typing=0.3 if present else 0, vowels=0.4, speed=0.1, px=0.5, py=0.5,
                 presence=0.8 if present else 0.05)
    out = e.tick(sense, user_colour=2 if present and t % 97 == 0 else None,
                 word="calm" if present and t % 131 == 0 else None)
print(e.top_words(), e.h)          # its words; its hidden state (it never sees this)
```

**`tick(sense, user_colour=None, word=None, incoming=(), incoming_words=())`** — one step.

| Argument | Meaning |
|---|---|
| `sense` | dict of outside readings: `typing`, `vowels`, `speed`, `px`, `py`, `presence`; and when watching another, `seen` (the other's look, from `body_look`), `noBody`, `unseen` (the other is out of sight: its channels are missing, not grey) |
| `user_colour` | index of the hue the visitor shows, or `None` |
| `word` | a word the visitor says, or `None` |
| `incoming` | hues (degrees) the others put on their screens last step |
| `incoming_words` | words the others said last step |

Returns a dict: `act` (0 = nothing, 1–6 = put hue `HUES[act-1]` on the screen, 7–10 = say one of
its words, 11 = reach toward the other), `reading` (the pattern it reads itself as), `x` (outside
vector), `y` (inside vector), `said` (the word, or `None`), `reached` (bool).

Other methods (the observer's views are marked *obs*):

| Method | What it does |
|---|---|
| `say(w)` | Puts one of its words out; it hears it itself |
| `top_words()` | The words it can say: the ones heard most, up to `NWORDS` |
| `company(ticks=20)` | Another reached toward it |
| `sleep_for(steps, sense)` | Sleep a number of steps (the body drifts back to rest, nothing is decided, the gate lets a little in) |
| `sleep_tick(x_real, sense)` | One asleep step |
| `wake(x_cue, cue_label="")` | Woken: re-reads the last stretch of the night with the waking world as dictionary; returns the report |
| `update_gate(absent_s)` | Sets the sleep gate from how long the visitor has been away |
| `recall_word()` | Stage 8: the word whose sound best fits what it reads itself as |
| `evoke_word(w, code=None)` | *obs* What a word calls up: patterns and inner state |
| `expect_seen(w, code=None)` | *obs* What a word leads it to expect to see of the other (channels 12–15) |
| `colour_meaning()` | *obs* How much its colour choices go with inner states (0–1) |
| `interpret(xe, xi, lE=1.0)`, `loglik(...)`, `learn(xe, xi)` | The reader itself: belief over patterns, likelihood, learning |
| `distress(h=None)`, `feel(acted)`, `outside(sense)`, `body_step(x, acted)` | Body and senses |

Attributes worth reading: `h` (hidden state), `n` (pattern counts; `len(e.n)` = patterns),
`belief`, `mirror` (`mirror["own"]`, `mirror["you"]`: how its own marks surprise it, against yours).

### 1.3 Helper functions

| Function | Returns |
|---|---|
| `body_look(h)` | What shows of an inside: size (charge), trembling, reaching out (contact), stirring (effort). Feed it to another's `sense["seen"]` |
| `word_code(w)` | A word as a sound: `HEAR` numbers made from its letters, nothing about its meaning |
| `voice_code(w, frm=None)` | The same in a speaker's voice (a small fixed shift) |
| `hear_idx(i)` | Where sound number `i` sits in the outside vector |
| `ORng(seed)` | The shared random generator, bit-exact with the JavaScript: `.next()` float in [0, 1), `.normal(m=0, sd=1)`, `.choice(p)` |

---

## 2. The stages and the command line

Each stage module has a `run(seed=1, ...)` that lives one life and returns a dict of results,
and a `CONDITIONS` dict of the published named conditions (keyword arguments for `run`).

```python
from endolexis.stages import stage20
r = stage20.run(seed=1, T=60000, mode="pair", ambiguous=True)
print(stage20.CONDITIONS.keys())
```

| Module | CLI name | Stages | `run` signature |
|---|---|---|---|
| `stage09` | `caring` | 9–10 answering, caring | `run(N=4, seed=1, T=16000, directed=False, contagion=0.0, jolts=True, recall=True, reach=False, sham=False, gamma=0.8, mutual=False, company=1.0, companyContact=False)`; also `caring(runs=12, seed0=1, **opts)` |
| `room` | `room` | 11–13 many others, attachment, closeness | `run(N=4, seed=1, T=40000, gaze='shared', sham=False, contagion=0.05, bondRate=1.0, bondDecay=0.9995, tau=0.05, randomBond=False, faces=False, close=0)` |
| `stage14` | `asking` | 14 asking | `run(N=2, seed=1, T=40000, sham=False, contagion=0.05, dim=0.0, readC=0.0)` |
| `stage15` | `newcomers` | 15 (and 16–17 rich) newcomers | `run(N=4, seed=1, T0=30000, T1=20000, WIN=5000, elders=True, sham=False, rich=False, hear=3, feel=6)` |
| `stage16` | `richer` | 16–17 richer lives, wider reader | `run(N=4, seed=1, T=40000, rich=False, sham=False, dim=0.0, maxc=60, hear=3, feel=6)` |
| `pairs` | `pairs` | 18, 19, 21 out of sight, strong meanings, expanded self | `run(seed=1, T=40000, rich=True, hear=6, feel=12, sight=1.0, readC=0.05, sham=False, nameDistress=False, voices=False, sal=0.0, couple=0.0, contagion=0.05, company=1.0)` |
| `stage20` | `symbiosis` | 20 symbiosis with a Processor | `run(seed=1, T=60000, mode='pair', drain=0.02, gain=0.15, every=5, eps=0.05, ambiguous=False)`; `mode` is one of `processor`, `olvaso`, `pair`, `scrambled`, `reading`, `readingScrambled`, `feeling`, `oracle` |

`sham=True` is the control in every stage: the same life with the meaningful link broken.

`endolexis.worlds` holds what happens around them: `setup(rich, hear=3, feel=6)`,
`private_event(e, R, rich)`, `jolt(e, R)`, `visitor_word(L, A, R, rich)`, `plain_word(L, A)`,
`presence(t, pres)` (420 steps present, 180 away), `mean(a)`, `nanmean(a)`, and the event `KINDS`
(jolt, warmth, drain, flash).

### Command line: `python -m endolexis`

```bash
python -m endolexis list                                     # experiments and their named conditions
python -m endolexis run symbiosis "ambiguous reading"        # 12 lives of a condition, averaged
python -m endolexis run pairs "stage 21 · shared fate 0.1" --runs 4 --seed0 1 --set T=20000 sham=true
python -m endolexis check                                    # re-run the first seed of every published condition
python -m endolexis check --runs 12 --only "t20_" --tol 1e-9 --shard 1/4
```

| Command | Options |
|---|---|
| `list` | — |
| `run <experiment> [condition]` | `--runs 12` lives, `--seed0 1` first seed, `--set key=value ...` override any `run` argument |
| `check` | `--runs 1`, `--only <text>` (filter by name), `--tol 1e-9`, `--shard i/n` (split over processes) |

---

## 3. The lab: `endolexis.lab`

Stand-alone earlier agents, each a module with a `main()`; run them as modules (figures go to
`./results`).

```bash
python -m endolexis.lab.agent       # a first self-explaining agent: life, waking, two dictionaries
python -m endolexis.lab.dream       # dreaming as reading with a closed gate
python -m endolexis.lab.cycles      # sleep cycles: three models of the night
python -m endolexis.lab.awaken      # the report is written at waking; daytime recall
python -m endolexis.lab.resonance   # cue-evoked feelings and the "click"
python -m endolexis.lab.strong_a    # a fair fight: can the outside be turned off?
python -m endolexis.lab.world2      # a richer world, a body with many senses (racing heart test)
python -m endolexis.lab.sleep2      # sleep with many senses
python -m endolexis.lab.voice       # a voice, described from the inside
```

Main building blocks, if you want to use them directly:

| Class / function | Signature | Notes |
|---|---|---|
| `agent.World` | `World(name, contexts, effects, seed=0)`; `.observe(ctx, clarity=1.0, noise=0.3)` | Ready-made worlds: `WORLD_A` (meadow), `WORLD_B` (mountain) |
| `agent.Body` | `Body(interoception_seed=42, n_raw=10, seed=0)`; `.step(effect)`, `.feel(state=None, noise=0.05)` | Vitals: energy, warmth, water |
| `agent.Agent` | `Agent(n_actions, max_concepts=24, new_thresh=4.0, beta=0.15, temp=0.05, seed=0)`; `.interpret(x_ext, x_int, lam_ext=1.0, lam_int=1.0)`, `.learn`, `.choose(cur)` | `lam_*`: how much it trusts each source |
| `agent.raise_agent` | `raise_agent(spec, steps, seed, policy='self', interoception_seed=42)` | Raises an agent in a world spec |
| `agent.live` | `live(world, body, agent, steps, policy='self', seed=0)` | |
| `world2.World2` | `World2(kind='forest', size=12, seed=0)`; `.step(pos)`, `.sense(pos, rng, noise=0.1)` | Tiles, light, sounds, smells, predator |
| `world2.Body2` | `Body2(nerves_seed=42, seed=0)`; `.step(world, pos, action)`, `.feel(...)`, `.distress(s=None)` | Vitals: energy, water, temperature, injury, fatigue, arousal |
| `world2.Agent2` | `Agent2(ext_dim=EXT_DIM, max_concepts=60, new_thresh=2.5, seed=0)`; `.interpret`, `.learn`, `.act(b, temp=0.05)`, `.update(b, a, r, b2, alpha=0.1, gamma=0.98)` | |
| `world2.raise_agent2` | `raise_agent2(kind, steps, seed, policy='self')` | |
| `voice.Creature` | `Creature(seed, start, hears_self=True, kappa=0.15, k_id=0)` | |
| `voice.live` | `live(n=1, kind='mountain', seed=1, steps=20000, hears_self=True, hear_others=True, kappa=0.15)` | |
| `dream.sleep` | `sleep(ctx, model, g, seed, event=True)` | `g`: how open the gate is |
| `cycles.sleep_cycles` | `sleep_cycles(ctx, model, gate, sounds, seed)` | Models `A`, `B`, `C` |
| `awaken.awakening` | `awakening(ctx, model, phase_t, stim, seed)`; `recall(ctx, seed, g_read=None)` | |
| `resonance.run_night` | `run_night(ctx, evoke, seed)`; `evoked(agent, x_ext)` | |

---

## 4. The toy world: `endolexis.toyworld`

```python
from endolexis.toyworld import (live_a_life, ToyWorld, SENSED, FELT, Collector, Olvaso, Observer,
                                Room, FELT1, Processors, GROUPS, GroupCollector, ManyReaders)
from endolexis.toyworld.hands import ActingReaders
```

Every life has the same shape: the **world** steps, the **collector** makes it anonymous, **Olvasó**
lives one moment and may act, and the **observer** (you) compares afterwards with the truth.

### 4.1 Toy world v0 (experiments 1–11)

**One line:** `live_a_life(seed=0, days=30, day_length=1000, threshold=100.0, learn_threshold=False, schedule=None, memory=None, **olvaso_kwargs)`
lives a whole life and returns the observer's report.

```python
rep = live_a_life(seed=1, days=30, memory=300, doubt_memory=3000, doubt_limit=0.1)
print(rep["read_warmth"], rep["self_caused_words"], rep["overall_read"])
```

`schedule` is an optional function `day -> (threshold, learn)` that changes the temperament on the
days it returns something (e.g. restless until day 10, then patient).

**By hand** (what `live_a_life` does):

```python
world = ToyWorld(seed=1)
col = Collector(len(SENSED), len(FELT), seed=1)
olv = Olvaso(len(SENSED), len(FELT), threshold=100.0, seed=1)
obs = Observer(col.secret_key(), max_words=olv.max_words)
b = None
for t in range(30 * 1000):
    sensed, felt, truth = world.step(b)
    s, f = col.anonymise(sensed, felt)
    b, readings = olv.live(s, f)
    obs.watch(t, olv, readings, felt, truth)
report = obs.report(olv, warmup=3000)
```

**`ToyWorld(seed=0, day_length=1000, warmth_delay=10, night_heat=0.0, night_jobs=0.0, night_flashes=0.0, charger_from=None, charger_rate=0.002, charger_strength=1.0)`**
Three sensed channels (`SENSED` = light, activity, sound) and three felt ones (`FELT` = warmth,
charge, drift). Warmth follows activity after `warmth_delay`; charge follows daylight minus screen
brightness; drift is linked to nothing (the control). `night_*` add inner events at night;
`charger_from=<day>` plugs in a charger from that day (something new in later life).

- `step(brightness=None)` → `(sensed, felt, truth)`; `brightness` is Olvasó's action (0, 0.5, 1).
- `set_warmth_delay(delay)` — a change of season. `daylight()` — the light now.

**`Collector(n_sensed, n_felt, seed=0)`** — shuffles, flips, scales and offsets each channel with a
secret key. `anonymise(sensed, felt)` → `(sensed_anon, felt_anon)`; `secret_key()` is for the
observer only.

**`Observer(key, max_words=200)`** — `watch(t, olvaso, readings, felt_true, truth)` every moment;
`report(olvaso, warmup)` at the end returns a dict: `read_<state>`, `late_read_<state>` (last third),
`warm_moments_read`, `warm_read_via_activity_word`, `chance_activity_word`, `self_caused_words`,
`actions`, `words`, `final_threshold`, `overall_read`.

### 4.2 `Olvaso` — the reader (toy world)

```python
Olvaso(n_sensed, n_felt, threshold=100.0, learn_threshold=False, seed=0,
       window=6, radius=3.0, max_words=200, max_lag=60,
       consistency=0.35, fit=0.35, min_count=8, min_episodes=4, episode_gap=200,
       memory=None, doubt_memory=None, doubt_limit=0.05, doubt_min=30,
       adapt=None, adapt_mode="replace", salience=1.0, onsets=False, rehear=None, slow_fit=False)
```

How it works, in four steps: short windows of the senses become **words** (online clustering); for
each word and each delay after it, it learns what each inner state did (**meanings**); a state is
**read** when a recent word reliably preceded it and fits it now; unread states build **pressure**,
and past the threshold it **acts**.

| Parameter | Default | Meaning | Since |
|---|---|---|---|
| `n_sensed`, `n_felt` | — | How many sensed and felt numbers it gets | 1 |
| `threshold` | `100.0` | Pressure needed before it acts (low = restless, high = patient) | 1 |
| `learn_threshold` | `False` | Lowers the threshold if acting was followed by more reading, raises it if not | 1 |
| `seed` | `0` | Its own randomness | 1 |
| `window` | `6` | Moments per word (words are movements, not snapshots) | 1 |
| `radius` | `3.0` | How far a moment may be from a word to count as that word; else a new word is born | 1 |
| `max_words` | `200` | Vocabulary size | 1 |
| `max_lag` | `60` | Longest delay between a word and what it means | 1 |
| `consistency` | `0.35` | Largest spread a meaning may have and still read | 1 |
| `fit` | `0.35` | How close the expected value must be to the present state | 1 |
| `min_count` | `8` | Experiences before a meaning may read | 1 |
| `min_episodes`, `episode_gap` | `4`, `200` | …spread over at least this many separate occasions, this far apart | 1 |
| `memory` | `None` | `None`: meanings are lifetime averages; `N`: they rest on about the last `N` experiences (forgetting) | 3 |
| `doubt_memory` | `None` | A slow memory of how much each meaning has wandered | 4 |
| `doubt_limit`, `doubt_min` | `0.05`, `30` | A meaning may read only while its wandering stays below the limit (judged after `doubt_min` samples) | 4 |
| `adapt` | `None` | Habituation: each inner state is felt against a baseline catching up in about `adapt` moments | 10 |
| `adapt_mode` | `"replace"` | `"replace"`: feel only changes; `"both"`: feel levels and changes side by side (readings then has `2·n_felt` entries: levels first, changes after) | 10 |
| `salience` | `1.0` | A change is noticed only above this many typical changes; a steady state is disregarded (`-2`) | 10 |
| `onsets` | `False` | A word that goes on is heard once, when it begins | 12b |
| `rehear` | `None` | With `onsets`, hear a continuing word again every `rehear` moments | 12b |
| `slow_fit` | `False` | A meaning must fit both now and over the last days (it must have held before) | 12c |

Methods:

| Method | What it does |
|---|---|
| `live(sensed, felt)` → `(brightness, readings)` | One awake moment |
| `sleep_moment(felt, sensed=None, dream_word=None, learn=False)` | One asleep moment: no acting, norms frozen. `sensed`: a leaked fragment of the world or `None`; `dream_word`: replay one of its own words; `learn`: let meanings learn from the night |
| `housekeeping(retire_after=5000, keep_uses=200, merge_dist=1.5, merge_agree=0.3, careful=False)` → `(retired, merged)` | Done in sleep: retires unused old words; merges near-identical words that mean the same. `merge_dist=0` retires only (the best mind); `careful=True` merges only on full agreement |
| `enable_long_term(slots=3)` | Extra long-term slots per meaning |
| `consolidate(merge=0.3, prune=False)` | Copy settled fast meanings into long-term memory |
| `read_state(f_z)` | Try to read a remembered felt state with the words sensed lately |

Useful attributes: `n_words`, `alive`, `word_uses`, `word_last_seen`, `threshold`, `pressure`,
and, from the first moment on, `sensed_word` (the word sensed this moment) and `last_err` (how
well each reading fit).

### 4.3 Toy world v1: the room (experiment 12 onward)

```python
Room(seed=0, day_length=1000, warmth_delay=10, load_delay=5,
     hands=False, pain=False, pain_channel=True, voice="mirror", window=None)
```

A room seen by a 16×16 colour camera, heard through a microphone (2048 samples at 8 kHz) and
touched through keys and mouse. A person comes, walks, types, talks; music plays now and then.

Felt (`FELT1`): `warmth` (about 10 moments after typing), `charge` (daylight in, screen brightness
out), `load` (a few moments after music), `drift` (linked to nothing). With hands and a pain channel,
`FELT2` adds `pain`.

| Parameter | Meaning |
|---|---|
| `warmth_delay`, `load_delay` | The hidden delays |
| `hands` | `True`: more ways to act than brightness, every request passes the guard (experiment 13) |
| `pain` | A refused request is felt as pain (otherwise refusal is silent) |
| `pain_channel` | `False` drops the fifth inner state entirely (otherwise a silent body has it as noise) |
| `voice` | What the microphone hears of tones: `mirror` (its own), `deaf`, `stranger` (someone plays as many as it did yesterday, at random moments), `recording` (its own tones of yesterday, at the same moments) — experiment 14 |
| `window` | What the camera sees of painting: `None` (the window tints the room), `mirror` (a 6×6 mirror at top right shows its own painted window), `blind`, `stranger`, `recording` — experiment 15 |

**`step(brightness=None, act=None)`** → `(raw, felt, truth)`

- `raw = {"image": 16×16×3 array, "sound": 2048 samples, "touch": [keys, mouse]}`
- `felt` = numpy array (4 or 5 values)
- `truth` (for the observer): `day`, `present`, `typing`, `talking`, `mouse`, `music`, `fan`,
  `brightness`, `warmth`, `charge`, `load`; with hands also `request`, `refused`, `executed`, `pain`,
  `own`, `own_tone`, `own_loud`, `heard_own`, `other_tone`, `own_paint`, `seen_own`, `other_paint`.
- `act` is a request `(kind, detail)` from `ActingReaders`, or `None`.

**Actions** (`KINDS`) and the guard (`guard(kind, param)` → `True` if the body allows it now):

| Kind | Details | Effect | Refused when |
|---|---|---|---|
| `brightness` | `0.0`, `0.5`, `1.0` | Screen glow | full brightness while the battery is low |
| `tone_soft` | `300.0`, `900.0` Hz | A soft tone, 20 moments | never |
| `tone_loud` | `300.0`, `900.0` Hz | A loud tone; warms the body | the body is hot |
| `paint` | `0`, `1`, `2` (red, green, blue: `PAINTS`) | Its window glows for 30 moments; costs charge and load | the battery is low |
| `note` | `0` | Writes a note to its sandbox (disk clicks, a burst of load) | the body is busy |

### 4.4 `Processors()` — the clockwork senses

`proc(raw)` → `{"vision": 11 numbers, "hearing": 9, "touch": 2}`. Fixed, never learn.

| Group | End products (`GROUPS[group]`) |
|---|---|
| `vision` (`Vision()`) | brightness, red_green, blue_yellow, contrast, left_right, top_bottom, motion, motion_dx, motion_dy, edges_h, edges_v |
| `hearing` (`Hearing(sub=8)`) | loudness, low, mid, high, centroid, flatness, pitch, onsets, pulsing |
| `touch` | keys, mouse |

`V0_SENSES` = the three v0 senses (vision brightness, hearing loudness, touch keys).

### 4.5 `GroupCollector(sizes, n_felt, seed=0)` — anonymity per processor

`anonymise(groups, felt)` → `(list of anonymous arrays, felt_anon)`: within each group the numbers
are shuffled and given a random sign, scale and offset. `felt_index(true_index)` (observer only)
tells where a true felt channel ended up.

### 4.6 `ManyReaders(sizes, n_felt, threshold=100.0, seed=0, max_words=200, radius=3.0, compete=False, **kw)`

One reader with one vocabulary per processor (or per any grouping you give it). `sizes`: numbers
per vocabulary. `max_words` and `radius` may be one value or one per vocabulary. `**kw` go to every
inner `Olvaso` (`memory`, `doubt_memory`, `adapt`, `slow_fit`, …). `compete=True`: when several
vocabularies offer a word, the winner must fit that many times better. With one vocabulary it is
plain Olvasó.

| Method | Returns |
|---|---|
| `live(inputs, felt)` | `(brightness, readings)`; `readings` use shared word numbers (vocabulary offset + word) |
| `read(inputs, felt)` | `readings` only (no acting) |
| `urge()` | `True` when pressure is past the threshold |
| `words_now()` | The word each vocabulary sensed now (`-1`: none) |
| `word_uses()`, `alive()` | Per-word use counts and alive flags, all vocabularies together |
| `housekeeping(**kw)` | `(retired, merged)` summed over vocabularies |

Attributes: `parts` (the inner `Olvaso`s), `offsets`, `total_words`, `pressure`, `threshold`.

### 4.7 `ActingReaders(sizes, n_felt, learn=None, lr=0.05, temp=0.5, answer_after=3, judge_after=50, answer_by="all", **kw)` — wanting

`ManyReaders` with hands (`endolexis.toyworld.hands`). When pressure builds it forms an intention:
one of the `KINDS` with a random detail (`DETAILS`). Which kind depends on how it feels: a small
learned expectation per kind over its inner states.

| Parameter | Meaning |
|---|---|
| `learn` | `None`: kinds at random (baseline); `"answer"`: learn from whether the world answered (how much the senses changed right after, against usual); `"read"`: learn from whether reading improved |
| `lr` | Learning rate of the expectations (delta rule) |
| `temp` | Softmax temperature when choosing a kind (low = always the best expected) |
| `answer_after` | Moments after acting at which the answer is judged |
| `judge_after` | Moments after acting at which reading improvement is judged |
| `answer_by` | `"all"`: change of all senses together; `"sense"`: the largest change of any one sense (so an answer seen by the eyes alone counts) |

`live(inputs, felt)` → `(request, readings)`; `request` is `(kind, detail)` or `None`; pass it as
`act=` to the next `Room.step`. Attributes: `W` (expectations, kinds × inner states + 1; the last
column is the bias, "how much it expects an answer from this kind"), `requests`, `signals`.

### 4.8 A full E.L.E.M.E.R. life

```python
import numpy as np
from endolexis.toyworld import Room, FELT1, Processors, GROUPS, GroupCollector
from endolexis.toyworld.hands import ActingReaders

ORDER = ("vision", "hearing", "touch")
sizes = [len(GROUPS[g]) for g in ORDER]                        # 11, 9, 2
radius = [3.0 * np.sqrt(n / 3) for n in sizes]                 # radius grows with the number of senses
MIND = dict(memory=300, doubt_memory=3000, doubt_limit=0.1, adapt=300, adapt_mode="both", slow_fit=True)

room = Room(seed=1, hands=True, pain=False, pain_channel=False, voice="mirror")
proc = Processors()
col = GroupCollector(sizes, len(FELT1), seed=1)
olv = ActingReaders(sizes, len(FELT1), learn="answer", threshold=20.0, seed=1,
                    max_words=[100, 80, 20], radius=radius, **MIND)
act = None
for t in range(30 * 1000):
    day, tick = divmod(t, 1000)
    if tick == 0 and day == 10:
        olv.threshold = 250.0                                  # restless childhood, then patient
    if tick == 0 and day >= 1:
        olv.housekeeping(merge_dist=0)                         # sleep: retire, never merge
    raw, felt, truth = room.step(act=act)
    ends = proc(raw)
    groups, f = col.anonymise([ends[g] for g in ORDER], felt)
    act, readings = olv.live(groups, f)
```

---

## 5. Experiment scripts: `experiments/toyworld/`

Run from a clone: `python experiments/toyworld/<script>.py [options]`. Each writes its results
JSON next to itself (only for the full run: 5 seeds and the published length). `--quick` is a short
smoke run. Where a script has named conditions, give their names as arguments to run only those.

| Experiment | Script | Options | Results file |
|---|---|---|---|
| 1 temperaments | `temperaments.py` | — | `temperaments_results.json` |
| 2 growing up | `growing_up.py` | — | `growing_up_results.json` |
| seeing inside | `inspect_words.py` | — | `learned_words.png` |
| 4 forgetting with doubt | `doubt.py` | `--quick` | `doubt_results.json` |
| 5 the dream test | `dream.py` | `--quick` | `dream_results.json` |
| 6–7 sleep response | `sleep_response.py` | `seasons`, `dreams`, `extra`, `--quick` | `sleep_response_results.json`, `_extra.json` |
| 8–9 night, housekeeping | `night_and_words.py` | `night`, `words`, `--quick` | `night_and_words_night.json`, `_words.json` |
| 10 adaptation | `adaptation.py` | `--quick` | `adaptation_results.json` |
| 11 careful merging | `careful_merging.py` | `--quick` | `careful_merging_results.json` |
| 12, 12b, 12c many senses | `many_senses.py` | condition names, `--quick`, `--long` (90 days) | `many_senses_results.json`, `many_senses_90days.json` |
| 13 wanting | `wanting.py` | `"random, silent"` … `"read, pain"`, `--quick` | `wanting_results.json` |
| 14 auditory mirror | `auditory_mirror.py` | `mirror`, `deaf`, `stranger`, `recording`, `--quick` | `auditory_mirror_results.json` |
| 15 mirror test | `mirror_test.py` | `mirror`, `blind`, `stranger`, `recording`, `--quick` | `mirror_test_results.json` |

```bash
python experiments/toyworld/many_senses.py "rich, per processor, slow fit"
python experiments/toyworld/auditory_mirror.py mirror recording
```

The scripts from experiment 12 on share helpers in `many_senses.py`: `MIND` (the best mind),
`SIZES` (numbers per processor), `CONDITIONS` (vocabularies, word places and radii per condition),
`radius_for(n)`, `inputs_for(vocabs, ends)` (turns processor end products into one input per
vocabulary), and each has `one_life(seed, cond, days=30)` and `main(seeds=(1, 2, 3, 4, 5), days=30, conds=None)`.

---

## 6. Tests

```bash
pip install pytest
pytest -q            # engine equivalence with the JavaScript, stages, toy world v0 and v1 (hands, voice, window)
```
