# E.L.E.M.E.R. for Android

**E**ndo-**L**exis **E**ntity: a **M**ind **E**merging by **R**eading. This is Olvasó among processors (experiments 12–15
of the toy world) living in a real body: your phone.

| | In the toy world | On the phone |
|---|---|---|
| Sight (11 numbers) | a 16×16 camera picture of the room | the front camera, seen as 16×16 colours |
| Hearing (9) | 2048 samples at 8 kHz | the microphone, 2048 samples at 8 kHz: one moment is a quarter of a second |
| Touch (2) | key presses, mouse | touches on the screen, finger movement |
| warmth | rises after typing | the battery's temperature |
| charge | daylight in, screen brightness out | the battery's level |
| load | rises after music | the work the app's own process does |
| drift | linked to nothing | linked to nothing (the control: it must stay unread) |
| Hands | brightness, soft and loud tones, painting its window, writing a note | the same: the app's screen brightness, a tone from the speaker, its window on the screen glowing red, green or blue, a line in its diary; and a sixth, the vibration motor (a short or a long buzz) |
| The guards | refuse a loud tone when hot, painting and full brightness when the battery is low, a note when busy | the same, as guard units (the studio's JSON), with the phone's own values: hot = 40 °C or 1.5 °C above usual; battery low = below 35 % (25 % for full brightness) and not charging; busy = working clearly harder than usual. A sixth guards the buzz (below) |
| Duties | sound the alarm when something smokes (experiment 26) | one: when the phone is 2.5 °C warmer than usual, dim the screen |

The mind is the best one for many senses: a vocabulary per processor (100, 80 and 20 words), levels and changes,
forgetting with doubt, slow fit, learning which intention to form from whether the world answered (judged sense by
sense, as in the mirror test). It is restless for its first 10 000 moments (about 43 minutes of life), then patient,
and every 1000 moments (about 4 minutes) it naps: words that were never used much are retired.

It lives while the app is open (the screen stays on). Closing the app, or **Sleep**, is sleep: its whole life is
saved in the app's own folder and goes on next time. **New life** sets the present one aside (kept, not deleted).
Everything stays on the phone: no network permission, and it writes only to its own sandbox.

**The mirror.** Hold the phone facing a mirror. The front camera then sees its window and the microphone hears its
tones. The screen counts the words that come mostly while its own hands are at work ("come with its own doing").

## Guards and duties

The body's guards are units, the same `endolexis-guard` JSON the [studio](../studio/) makes, decided by a Kotlin
engine that gives the same outcome, option and guard as the Python one (`core/Guards.kt`, checked on 3000 recorded
cases). The built-in ones are in `app/src/main/assets/guards/`:

| Guard | Guards | Rule |
|---|---|---|
| `glare` | brightness | refuse full brightness below 25 % charge when not charging |
| `hot-voice` | tone_loud | refuse at 40 °C or more, or 1.5 °C above its usual warmth |
| `paint-battery` | paint | refuse below 35 % charge when not charging |
| `busy-note` | note | refuse while it works clearly harder than usual |
| `gentle-buzz` | vibrate | refuse below 20 % charge when not charging, and more than five buzzes in 100 moments (about 25 s); limit a long buzz to a short one while it is 1 °C or more warmer than usual |
| `learned-buzz` | vibrate | learned in the phone sandbox (experiment 28): lying flat, a long buzz becomes a short one (it walks the phone off a table); lying flat in the dark and quiet, refuse (the person sleeps); below 8 % charge when not charging, refuse; five buzzes in 100 moments, refuse; lying flat, 26 buzzes since it was laid down, refuse |

`learned-buzz` comes from a simulated phone and its person, where a guard for the buzz was learned by replaying each
harm with one thing changed at a time ([experiment 28](../experiments/toyworld/README.md)). In the simulation it let no
harm through, where `gentle-buzz` woke the sleeper 24 times a day. Its light and loudness limits come from the
simulation's scales, not this phone's camera and microphone, so `gentle-buzz` stays beside it until they are checked.

The first four decide exactly as the old built-in guard did (checked on 20 000 random phone states). Guards only
take away: the most severe outcome wins, and a signal the phone cannot sense refuses. A limit carries out the act
in its gentler form. Olvasó never learns that the guards exist, only what came after.

A duty acts, before Olvasó, through the guards: `cool-down` (`assets/duties/`) dims the screen when the phone is
2.5 °C warmer than usual, at most every 400 moments (about a minute and a half).

**Your own guard.** About → **Guards** lists every guard, its rules in words and how often it acted, the duty, and
what a guard can sense: `warmth_c`, `warmth_above_usual`, `charge`, `plugged`, `load`, `busy`, `hour`, `recent`
(acts of that hand in the last 100 moments), `active` (1 while any hand is at work), `lying` (flat and still, from the
accelerometer), `buzzes_here` (its buzzes since it was last laid down), `light` (the camera's mean brightness) and
`loudness` (the microphone, dBFS) and `lux` (the ambient light sensor). Without a camera, microphone or accelerometer those are unknown, and a guard
that asks for them fails closed. **Add guard file** opens a
guard unit (JSON); it is accepted only if it is sound, guards hands this phone has, uses signals it can sense, and
every one of its scenarios holds. It is kept in the app's own folder and is at work from the next moment.
**Built-in only** removes the added ones.

**Your nights.** `learned-buzz` knows sleep only from a simulation: a dark, quiet nightstand on the simulation's
scales. **Nights** fits it to you. **Start** begins the night log, a background recorder with a notification, so
the phone can be locked or used for anything else. Olvasó sleeps while it records. Every 4 seconds it notes
whether the phone lies flat (the accelerometer), the ambient light (the light sensor, lux) and how loud it is (the
microphone level in dBFS, a number, never the sound), with your mark: tap **Going to sleep** in the notification at
bedtime and **Awake** in the morning. The record (`nights.csv`) stays in the app's own folder; **Save log…** gives
you a copy.

After two nights or more, **Calibrate** does what the sandbox learner did for the hidden cause "the person
sleeps", on your own record (`core/Nights.kt`):
- among the moments the phone lay flat, it takes the light and loudness of almost all your sleep (99.5 %), with a
  margin;
- it keeps only the conditions that leave your waking moments alone;
- it adds caution for what the nights never showed: at the hours you sleep, a room darker than (almost) any you
  were awake in also counts as sleep.

It shows the rules, and how much of your recorded sleep and waking they would refuse. **Add as guard** adds them as
`my-nights` beside the built-in guards, through the same checks as any added guard file. Calibrating again replaces it.

Permissions for the night log: notifications (Android 13 and later ask), the microphone (already asked), and a
foreground service for it. The phone shows its microphone indicator while the log runs.

A life saved before the sixth hand wakes up with it: its expectations for the five old hands are kept, and it
expects nothing yet of the buzz.

## The screen

- **What it sees** and **its window** (dark, or glowing with its paint; ♪ while it sings, ≈ while it buzzes).
- **Inside:** the four inner states as the world knows them, and for each the word that reads its level and its
  change (`v` a word of sight, `h` of hearing, `t` of touch), or *unread*, or *quiet* (nothing changes, nothing
  asks to be read).
- **Unread pressure** against the threshold: when the bar passes the mark, it acts.
- **Words:** every word place of each vocabulary; filled = alive, amber = sensed now.
- **Wanting:** for each kind of act, how much it has come to expect the world to answer (amber = yes, brown = no),
  and how often that act was carried out ✓ or refused ✗.
- **Lately:** its recent acts, refusals and limits (with the guard's name), the duty's acts, and its naps. **Diary:** the notes it wrote.

## Building

- **Android Studio:** open this `android/` folder, connect the phone with USB debugging on, press Run.
- **From the command line:** `./gradlew assembleDebug` (needs the Android SDK; the APK lands in
  `app/build/outputs/apk/debug/`).
- **Without building:** every push builds the APK on GitHub (the *android* workflow); download `elemer-apk` from the
  run's artifacts and install it (allow installing from this source).

Requires Android 8.0 or later. Permissions: camera and microphone (it lives without them too, blind or deaf), and
vibration (granted at install).

## Is it the same mind?

`app/src/test` replays a 12 000-moment life recorded from the Python package (`tools/make_golden.py`, endolexis
0.3.0) through the Kotlin mind: every reading, every sensed word and every intention must be identical, and the
learned expectations equal to 1e-9 (a mind with the toy world's five hands; the phone's mind has six). The processors are checked on recorded camera and sound frames. Sums are done
the way numpy does them (pairwise), so the two minds make the same decisions bit for bit.

```bash
./gradlew testDebugUnitTest
```

## Code

| File | What |
|---|---|
| `core/Olvaso.kt` | the reader (port of `toyworld/olvaso.py`) |
| `core/Readers.kt` | `GroupCollector`, `ManyReaders`, `ActingReaders` (readers.py, hands.py) |
| `core/Processors.kt` | vision, hearing (processors.py) |
| `core/Num.kt` | numpy-exact sums, running norms |
| `core/Guards.kt`, `core/Json.kt` | guard and duty units (guards.py, duties.py), a small JSON reader |
| `body/Body.kt` | eyes, ears, skin, insides, hands |
| `Laws.kt` | the guards and duties at work: built-in and added units, the signals |
| `NightLog.kt`, `core/Nights.kt` | the night log (a background service) and the calibration of `my-nights` |
| `Life.kt` | one life: the moment loop (duty, then Olvasó through the guards), saving, the observer |
| `MindView.kt`, `MainActivity.kt` | the screen |
