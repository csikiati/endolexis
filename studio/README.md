# Olvasó Studio

A web page for drawing **architectures**: which processor outputs feed which Olvasó (one, two or three), which
hands each Olvasó may use, and when each one sleeps. The architecture is saved as JSON and lived by the Python
package in the toy world's room (`endolexis.studio`). A second page makes new **processor units** from
use-case templates.

Open `studio/index.html` in a browser (no server, no install). It is one self-contained file.

## The page

**Wiring and sleep** splits the screen in three: processors, Olvasós, hands.

- **Cords.** Drag from a processor output's socket to an Olvasó, or from an Olvasó's socket to a hand. On a
  touch screen, tap the socket and then the card. Tap a cord to select it, then press × (or Delete) to
  remove it. The lettered pips beside each output wire it to Olvasó A, B or C, or unwire it. The pips in a
  processor's header wire or unwire all of its outputs at once.
- **Processors.** *Add processor* offers the built-in units, a unit JSON file, or pasted JSON. Remove one with
  its ×; its cords go with it.
- **Olvasós.** Up to three. Each has three sliders, all fractions of a day (0-100 %):
  - *Sleeps*: how much of the day it is asleep (lid closed, nothing sensed, no acting).
  - *Waking*: how long it takes, after sleep, to come round (it senses, learns and reads, but does not
    act yet).
  - *Later by*: how much later its sleep begins each day, so that over the days it sees every hour of the
    room. A day picker then shows any day of its life.
  - *Falls asleep*: when its sleep begins (on the first day).
- **A day of the body** draws each Olvasó's day, the room's night, and how many are awake at each moment,
  with warnings when nobody is awake or when two sleep at once.
  - *Take turns* chains the sleeps: each one falls asleep as the one before wakes.
  - *One asleep, one waking, one awake* sets three Olvasós to a third each, staggered.
- **Save JSON** / **Open JSON…** / **Open an example…** The examples are the architectures of experiment 16.

**Processor maker.** Pick a use case, then adjust the unit's fields:

- name, version and description;
- the outside source of its information, what arrives from it, and how many numbers come in;
- the outputs, each with a name and how it is computed.

It shows the unit's JSON and a Python skeleton. You can save either one, or add the unit to the architecture
being drawn.

**Experiment 16** shows the results of living the example architectures.

## Files

| File | Format | What |
|---|---|---|
| processor unit | `"format": "endolexis-processor"` | `name`, `title`, `description`, `version`, `source` (`kind`, `detail`, `raw`: the key in the world's raw senses), `inputs`, `outputs`, `output_names`, and `implementation`: `{"builtin": "vision", "outputs": [6, 7, 8]}` or `{"python": "module:function"}` |
| architecture | `"format": "endolexis-architecture"` | `processors` (`id`, `unit`), `olvasos` (`id`, `name`, `sleep`, `waking`, `phase`, optionally `shift`), `outputs` (`id`, `kind`: one of the body's hands), `links` (`{"from": {"node", "port"}, "to": {"node"}}` for a processor output; `{"from": {"node"}, "to": {"node"}}` for a hand) |

Built-in units are in `src/endolexis/studio/processors/`: the whole eye, ear and touch, and their stages
(retina, motion, form; cochlea, timbre, rhythm). The use-case templates are in
`src/endolexis/studio/templates.json`.

## The command line

```bash
python -m endolexis.studio check studio/examples/three-take-turns.json
python -m endolexis.studio run   studio/examples/three-take-turns.json --seeds 1 2 3 --days 30 --out results.json
python -m endolexis.studio stagger my-architecture.json
python -m endolexis.studio units
python -m endolexis.studio templates
python -m endolexis.studio new-processor accelerometer --name my-accel -o my-accel.json --stub my_accel.py
```

A unit with a Python implementation is called with the room's raw senses (`raw["image"]`, `raw["sound"]`,
`raw["touch"]`) and returns its `outputs` numbers. Templates for other sources (accelerometer, weather,
calendar…) describe processors for other bodies. The room cannot feed them, so their skeletons need a world or
a body that provides that source.

## How an architecture lives

`endolexis.toyworld.ensemble`:

- **Its own mind for each Olvasó.** Each one is the best mind of experiments 13-15 (`ActingReaders`, learning
  from whether the world answered, judged sense by sense).
- **Vocabularies.** Each Olvasó has one vocabulary per processor it is wired to, made only of the outputs
  actually wired.
- **Anonymity.** Each Olvasó has its own secret key: its own shuffle of the numbers.
- **Housekeeping.** It tidies its words (retire only, never merge) each time it wakes. If it never sleeps, it
  tidies once a day.
- **One body.** All the Olvasós feel the same body, and the body has one pair of hands.
  - The body reads an inner state when any Olvasó that is not asleep reads it. If several read it, the best
    fit counts.
  - If two awake Olvasós ask in the same moment, the first one is carried out and the other is let go.

To rebuild `index.html` after changing the page (`studio.html`), the units, the templates or the examples:
`python studio/build.py`.
