# Olvasó Studio

A web page for drawing **architectures**: which processor outputs feed which Olvasó (one, two or three), which
hands each Olvasó may use, and when each one sleeps. The architecture is saved as JSON and lived by the Python
package in the toy world's room (`endolexis.studio`). A second page makes new **processor units** and **hand
units** from use-case templates, and **guards**: declared rules between Olvasó's wanting and the world.

Open `studio/index.html` in a browser (no server, no install). It is one self-contained file.

## The page

**Wiring and sleep** splits the screen in three: processors, Olvasós, hands.

- **Cords.** Drag from a processor output's socket to an Olvasó, or from an Olvasó's socket to a hand. On a
  touch screen, tap the socket and then the card. Tap a cord to select it, then press × (or Delete) to
  remove it. The lettered pips beside each output wire it to Olvasó A, B or C, or unwire it. The pips in a
  processor's header wire or unwire all of its outputs at once.
- **Processors.** *Add processor* offers the built-in units, a unit JSON file, or pasted JSON. Remove one with
  its ×; its cords go with it.
- **Hands.** *Add hand* offers the room's five built-in hands, a hand unit JSON file, or pasted JSON. Each
  hand card shows its options. Its A/B/C pips let each Olvasó use it, or not. A new hand is wired to every
  Olvasó. A hand the room's body does not have (a vibration motor, a smart bulb…) is kept in the
  architecture, marked, and left out when the room lives it.
- **Guards.** The band above the hands. By default the room's own guard holds, four fixed rules. *Make them
  editable units* turns them into guard units, and *Add guard* adds more: built in, from a template, a file or
  pasted JSON. Each guard card shows its rules and whether its scenario tests hold. Each hand shows the guards
  protecting it, and a hand of a new kind without any guard is flagged as unguarded.
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

**Maker.** Choose *Processor*, *Hand* or *Guard*, pick a use case, then adjust the unit's fields:

- **Processor:** name, version and description; the outside source of its information, what arrives from
  it, and how many numbers come in; the outputs, each with a name and how it is computed.
- **Hand:** name, version and description; what it acts on and what it does there; the options it may
  choose among (a value and a label each); its guard (when the body refuses it); its effects.
- **Guard:** name, version, tier and description; the hands it protects; its rules (conditions on signals,
  an optional condition on the option, and what then happens); what to do with a signal the body cannot
  sense; its scenario tests, each checked as you type. A guard with a failing scenario cannot be added.
  The templates are: blade near a person, hot body, moving near people, privacy, not too often, quiet
  hours, ask first, battery reserve.

The maker shows the unit's JSON and a Python skeleton. You can save either one, or add the unit to the
architecture being drawn.

**Experiment 16** shows the results of living the example architectures.

## Files

| File | Format | What |
|---|---|---|
| processor unit | `"format": "endolexis-processor"` | `name`, `title`, `description`, `version`, `source` (`kind`, `detail`, `raw`: the key in the world's raw senses), `inputs`, `outputs`, `output_names`, and `implementation`: `{"builtin": "vision", "outputs": [6, 7, 8]}` or `{"python": "module:function"}` |
| hand unit | `"format": "endolexis-hand"` | `name`, `title`, `description`, `version`, `target` (`kind`, `detail`: what it acts on), `options` (`[{"value", "label"}]`: what Olvasó may choose among), `guard` (when the body refuses it), `effects`, and `implementation`: `{"builtin": "paint"}` (one of the room's hands) or `{"python": "module:act"}` |
| guard unit | `"format": "endolexis-guard"` | `name`, `title`, `description`, `version`, `tier` (`innate`; `learned` for guards a sandbox will produce), `protects` (hand names, or `"*"`), `rules` (`{"when": [{"signal", "op", "value"}], "option": {"op", "value"}, "then": "refuse" \| "limit" \| "stop" \| "ask", "to"}`), `on_missing` (`refuse`, the default, or `ignore`), `tests` (`{"name", "hand", "option", "state": {signal: value}, "expect", "ongoing"}`) |
| architecture | `"format": "endolexis-architecture"` | `processors` (`id`, `unit`), `olvasos` (`id`, `name`, `sleep`, `waking`, `phase`, optionally `shift`), `outputs` (`id`, and `kind`: one of the room's hands, and/or `unit`: a hand unit), optionally `guards` (`id`, `unit`; when present, these replace the room's own guard), `links` (`{"from": {"node", "port"}, "to": {"node"}}` for a processor output; `{"from": {"node"}, "to": {"node"}}` for a hand) |

Built-in units are in `src/endolexis/studio/processors/`: the whole eye, ear and touch, and their stages
(retina, motion, form; cochlea, timbre, rhythm). The room's hands are in `src/endolexis/studio/hands/`. The
use-case templates are in `src/endolexis/studio/templates.json` and `hand_templates.json`: vibrate, speak,
light colour, move, notify, thermostat, smart plug, sound clip, post a message.

## The command line

```bash
python -m endolexis.studio check studio/examples/three-take-turns.json
python -m endolexis.studio run   studio/examples/three-take-turns.json --seeds 1 2 3 --days 30 --out results.json
python -m endolexis.studio stagger my-architecture.json
python -m endolexis.studio units
python -m endolexis.studio templates
python -m endolexis.studio new-processor accelerometer --name my-accel -o my-accel.json --stub my_accel.py
python -m endolexis.studio hands
python -m endolexis.studio hand-templates
python -m endolexis.studio new-hand vibrate --name buzz -o buzz.json --stub buzz.py
python -m endolexis.studio guards
python -m endolexis.studio guard-templates
python -m endolexis.studio new-guard blade -o blade.json
python -m endolexis.studio test-guards blade.json my-other-guard.json
```

## Guards

A guard stands between Olvasó's wanting and the world. Olvasó never learns that it exists, only what follows.
Guards are built so that they hold even when everything else is wrong:

- **They only take away.** A rule can refuse, limit (carry the act out with a gentler option), stop (refuse,
  and cut short a hand already at work when the rule comes true) or ask (a person must agree; in the room
  there is nobody to ask, so it is refused). There is no rule that allows, so adding guards can only make
  the body more careful.
- **They read their own signals, never Olvasó's words.** In the room: `warmth`, `charge`, `load`, `hour`,
  `person`, `person_distance`, `talking`, `recent` (how often this hand was used lately), `active` (the hand
  is still at work).
- **They can look ahead.** With `"lookahead": n`, every condition is checked now and n moments on, from
  each signal's rate of change (`person_distance@rate`, `warmth@rate`, …). A rule written on the harm itself
  ("within reach") needs this, or it is one moment late (experiment 20).
- **They fail closed.** A signal the body cannot sense counts as danger, unless the guard says `ignore`.
- **They are rules, not code**, so they can be read, checked and tested. Every guard carries scenario tests.
  `check` runs all of them, together, before a life is lived, and a failing scenario stops it.

The room's own guard, as the four built-in units, lives exactly the same life as the room's fixed guard (a
test checks this).

The *learned* tier is for guards a sandbox produces. A body lives a childhood in a simulated room, harm is
judged from outside, and each harm becomes a rule with its scenario (experiment 17). *Add guard* lists the
learned blade guard from that experiment under *Learned in the sandbox*: read it before you use it. For a real machine
with a real blade, these guards model the idea. The reflex layer and an emergency stop belong in the hardware.

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
