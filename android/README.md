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
| Hands | brightness, soft and loud tones, painting its window, writing a note | the same: the app's screen brightness, a tone from the speaker, its window on the screen glowing red, green or blue, a line in its diary |
| The guard | refuses a loud tone when hot, painting and full brightness when the battery is low, a note when busy | the same, with the phone's own values: hot = 40 °C or 1.5 °C above usual; battery low = below 35 % (25 % for full brightness) and not charging; busy = working clearly harder than usual |

The mind is the best one for many senses: a vocabulary per processor (100, 80 and 20 words), levels and changes,
forgetting with doubt, slow fit, learning which intention to form from whether the world answered (judged sense by
sense, as in the mirror test). It is restless for its first 10 000 moments (about 43 minutes of life), then patient,
and every 1000 moments (about 4 minutes) it naps: words that were never used much are retired.

It lives while the app is open (the screen stays on). Closing the app, or **Sleep**, is sleep: its whole life is
saved in the app's own folder and goes on next time. **New life** sets the present one aside (kept, not deleted).
Everything stays on the phone: no network permission, and it writes only to its own sandbox.

**The mirror.** Hold the phone facing a mirror. The front camera then sees its window and the microphone hears its
tones. The screen counts the words that come mostly while its own hands are at work ("come with its own doing").

## The screen

- **What it sees** and **its window** (dark, or glowing with its paint; ♪ while it sings).
- **Inside:** the four inner states as the world knows them, and for each the word that reads its level and its
  change (`v` a word of sight, `h` of hearing, `t` of touch), or *unread*, or *quiet* (nothing changes, nothing
  asks to be read).
- **Unread pressure** against the threshold: when the bar passes the mark, it acts.
- **Words:** every word place of each vocabulary; filled = alive, amber = sensed now.
- **Wanting:** for each kind of act, how much it has come to expect the world to answer (amber = yes, brown = no),
  and how often that act was carried out ✓ or refused ✗.
- **Lately:** its recent acts and refusals, and its naps. **Diary:** the notes it wrote.

## Building

- **Android Studio:** open this `android/` folder, connect the phone with USB debugging on, press Run.
- **From the command line:** `./gradlew assembleDebug` (needs the Android SDK; the APK lands in
  `app/build/outputs/apk/debug/`).
- **Without building:** every push builds the APK on GitHub (the *android* workflow); download `elemer-apk` from the
  run's artifacts and install it (allow installing from this source).

Requires Android 8.0 or later. Permissions: camera and microphone (it lives without them too, blind or deaf).

## Is it the same mind?

`app/src/test` replays a 12 000-moment life recorded from the Python package (`tools/make_golden.py`, endolexis
0.3.0) through the Kotlin mind: every reading, every sensed word and every intention must be identical, and the
learned expectations equal to 1e-9. The processors are checked on recorded camera and sound frames. Sums are done
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
| `body/Body.kt` | eyes, ears, skin, insides and the guard, hands |
| `Life.kt` | one life: the moment loop, saving, the observer |
| `MindView.kt`, `MainActivity.kt` | the screen |
