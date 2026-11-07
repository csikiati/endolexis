"""Toy world v1: a room seen and heard by a laptop (experiment 12 onward).

Ground truth, known only to the world and the observer. One moment = one tick; a day is
`day_length` ticks.

Outer world (raw, before any processor):
  image  - a 16x16 colour picture of the room: daylight through a window on the left, a desk,
           a lamp switched on when someone is there in the dark, the glow of Olvaso's own screen,
           and a person (a warm-coloured blob) who comes, walks about, sits at the desk and leaves
  sound  - 2048 samples at 8 kHz (a quarter of a second): a faint hiss; the fan's hum, louder
           as the body warms; key clicks while the person types; a voice (harmonic, pulsing about
           4 times a second) while they talk; music now and then (a chord with a steady beat)
  touch  - key presses per moment and mouse movement

Inner world (felt):
  warmth - rises about 10 moments after typing starts, then fades       (hidden link 1, delayed)
  charge - drains slowly, refills by day; screen brightness costs charge (hidden link 2, slow)
  load   - the music is a job the body runs: load rises a few moments after music starts
           (hidden link 3: readable only if music can be told apart from a voice; both are loud)
  drift  - random wandering linked to nothing                          (control: must stay unread)

With hands=True (experiment 13 onward), Olvaso has more ways to act than screen brightness, and every
request passes a guard first (the spine: the hand that will not go into the fire):
  brightness - the screen glow (0, 0.5, 1); full brightness is refused while the battery is low
  tone_soft  - a soft tone from the speaker for 20 moments; always allowed
  tone_loud  - a loud tone; warms the body; refused while the body is hot
  paint      - its window glows red, green or blue for 30 moments; costs charge and load;
               refused while the battery is low
  note       - writes a note to its sandbox (5 moments of disk clicks, a burst of load); refused
               while the body is busy
A refused request changes nothing outside. With pain=True it is felt as a fifth inner state, pain,
that fades within moments; without, the refusal is silent. pain_channel=False drops the fifth
inner state altogether (otherwise a silent body still has it, as pure noise).

voice (experiment 14, the auditory mirror) decides what the microphone hears of tones:
  mirror    - Olvaso hears its own tones (the default)
  deaf      - its own tones are not heard, and nobody else plays any
  stranger  - its own tones are not heard; a stranger plays as many tones as Olvaso played the
              day before, of the same kinds, at random moments
  recording - its own tones are not heard; its own tones of the day before are played back,
              at the same moments of the day
Only Olvaso's own loud tones warm the body, whatever is heard.
"""
import numpy as np

FELT1 = ["warmth", "charge", "load", "drift"]
FELT2 = FELT1 + ["pain"]
KINDS = ["brightness", "tone_soft", "tone_loud", "paint", "note"]
PAINTS = np.array([[1.0, 0.2, 0.2], [0.2, 1.0, 0.3], [0.2, 0.4, 1.0]])
SIZE, FS, NSAMP = 16, 8000, 2048


class Room:
    def __init__(self, seed=0, day_length=1000, warmth_delay=10, load_delay=5, hands=False, pain=False,
                 pain_channel=True, voice="mirror"):
        self.rng = np.random.default_rng(seed)
        self.hands, self.pain_on, self.pain_channel, self.voice = hands, pain, pain_channel, voice
        self.played = {}                 # moment -> (freq, amp) of Olvaso's own executed tones
        self.other_left, self.other_freq, self.other_amp = 0, 440.0, 0.0
        self.stranger_at = {}
        self.voice_rng = np.random.default_rng(seed + 777_000)
        self.hand_rng = np.random.default_rng(seed + 4242)    # keeps the old random stream intact
        self.tone_left = self.paint_left = self.note_left = 0
        self.tone_freq, self.tone_amp, self.paint_col = 440.0, 0.0, PAINTS[0]
        self.pain = 0.0
        self.day_length, self.t = day_length, 0
        self.brightness = 0.5
        self.present = False
        self.stay_left = 0
        self.pos = np.array([8.0, 8.0])
        self.goal = np.array([8.0, 11.0])
        self.sitting = False
        self.typing_left = self.talk_left = self.music_left = self.mouse_left = 0
        self.f0 = 150.0
        self.chord = np.array([440.0, 554.4, 659.3])
        self.type_hist = [0.0] * (warmth_delay + 1)
        self.music_hist = [0.0] * (load_delay + 1)
        self.warmth, self.charge, self.load, self.drift = 0.0, 0.7, 0.0, 0.0
        self.tt = np.arange(NSAMP) / FS
        yy, xx = np.mgrid[0:SIZE, 0:SIZE]
        self.window_mask = ((xx < 5) & (yy < 7)).astype(float)
        self.desk_mask = (yy >= 12).astype(float)
        self.desk_tex = (yy % 2 == 0).astype(float) * self.desk_mask   # wood grain: horizontal stripes
        self.yy, self.xx = yy, xx

    def daylight(self):
        return max(0.0, np.sin(2 * np.pi * self.t / self.day_length))

    # --- the people and things in the room ----------------------------------------
    def _people(self, day):
        r = self.rng
        if not self.present:
            if r.random() < 0.0015 + 0.008 * day:
                self.present, self.stay_left = True, int(r.integers(150, 450))
                self.pos = np.array([15.0, float(r.integers(4, 12))])       # enters from the right
                self.goal = np.array([8.0, 10.0])
                self.sitting = False
        else:
            self.stay_left -= 1
            if self.stay_left <= 0:
                self.goal = np.array([16.0, self.pos[1]])                   # walks out
                if self.pos[0] >= 15.5:
                    self.present = self.sitting = False
                    self.typing_left = self.talk_left = self.mouse_left = 0
            elif self.sitting and r.random() < 0.004:
                self.sitting = False
                self.goal = r.uniform([2, 3], [14, 11])                       # gets up, wanders
            elif not self.sitting and np.linalg.norm(self.goal - self.pos) < 0.5:
                if r.random() < 0.6:
                    self.goal = np.array([8.0, 10.0])
                else:
                    self.goal = r.uniform([2, 3], [14, 11])
        if self.present:
            step = self.goal - self.pos
            dist = np.linalg.norm(step)
            if dist > 0.3:
                self.pos += step / dist * min(0.4, dist)
                self.sitting = False
            elif np.allclose(self.goal, [8.0, 10.0]):
                self.sitting = True
        typing = talking = mouse = False
        if self.present and self.sitting:
            if self.typing_left > 0:
                self.typing_left -= 1
                typing = True
            elif self.talk_left == 0 and r.random() < 0.03:
                self.typing_left = int(r.integers(30, 80))
            if not typing and self.mouse_left == 0 and r.random() < 0.02:
                self.mouse_left = int(r.integers(5, 20))
        if self.present and not typing:
            if self.talk_left > 0:
                self.talk_left -= 1
                talking = True
            elif r.random() < 0.01:
                self.talk_left = int(r.integers(20, 60))
                self.f0 = float(r.uniform(110, 220))
        if self.mouse_left > 0:
            self.mouse_left -= 1
            mouse = not typing
        music = False
        if self.music_left > 0:
            self.music_left -= 1
            music = True
            if self.music_left % 125 == 0:                                   # a new bar, a new chord
                self.chord = np.array([440.0, 554.4, 659.3]) * 2 ** (r.integers(-5, 5) / 12)
        elif r.random() < 0.0006:
            self.music_left = int(r.integers(100, 300))
        return typing, talking, mouse, music

    # --- the raw senses -----------------------------------------------------------
    def _image(self, day):
        r = self.rng
        lamp = 0.45 if (self.present and day < 0.15) else 0.0
        amb = 0.15 * day + lamp * 0.6
        img = np.zeros((SIZE, SIZE, 3))
        img += amb * np.array([1.0, 0.95, 0.85])
        img += (0.7 * day * self.window_mask)[..., None] * np.array([0.85, 0.95, 1.0])
        img += lamp * np.array([1.0, 0.75, 0.4]) * np.exp(-((self.xx - 13) ** 2 + (self.yy - 3) ** 2) / 40)[..., None]
        img += 0.25 * self.brightness * np.array([0.6, 0.75, 1.0])                 # the screen's glow
        if self.paint_left > 0:
            img += 0.25 * self.paint_col                                            # its painted window
        img -= (0.08 * self.desk_mask + 0.06 * self.desk_tex)[..., None]
        if self.present:
            x, y = self.pos
            body = np.exp(-(((self.xx - x) / 1.2) ** 2 + ((self.yy - y) / 2.0) ** 2))
            img += (0.6 * body)[..., None] * np.array([0.9, 0.55, 0.45])
        img += r.normal(0, 0.02, img.shape)
        return img

    def _sound(self, typing, talking, music, fan):
        r, tt = self.rng, self.tt
        s = r.normal(0, 0.01, NSAMP)                                                 # hiss
        hum = np.cumsum(r.normal(0, 1, NSAMP))
        hum -= np.linspace(hum[0], hum[-1], NSAMP)
        s += (0.02 + 0.25 * fan) * (hum / (np.abs(hum).max() + 1e-9) * 0.5 + np.sin(2 * np.pi * 95 * tt + r.uniform(0, 6)))
        if typing:
            for _ in range(r.poisson(2.5)):
                i = int(r.integers(0, NSAMP - 60))
                click = r.normal(0, 1, 40) * np.exp(-np.arange(40) / 8)
                s[i:i + 40] += 0.6 * np.diff(np.r_[0, click])                        # sharp, high clicks
        if talking:
            f0 = self.f0 * (1 + 0.05 * np.sin(2 * np.pi * 1.5 * tt + r.uniform(0, 6)))
            ph = 2 * np.pi * np.cumsum(f0) / FS
            v = sum(np.sin(k * ph) / k for k in range(1, 9))
            env = (0.5 + 0.5 * np.sin(2 * np.pi * 4.2 * tt + r.uniform(0, 6))) ** 2   # syllables
            s += 0.35 * v * env
        if music:
            m = sum(np.sin(2 * np.pi * f * tt + r.uniform(0, 6)) for f in self.chord) / 3
            beat_at = (self.t * NSAMP / FS) % 0.5                                     # a beat every half second
            k = np.arange(NSAMP) / FS + beat_at
            kick = np.where((k % 0.5) < 0.08, np.sin(2 * np.pi * 60 * k) * np.exp(-(k % 0.5) / 0.03), 0)
            s += 0.3 * m + 0.4 * kick
        if self.tone_left > 0 and self.voice == "mirror":                         # its own voice
            s += self.tone_amp * np.sin(2 * np.pi * self.tone_freq * tt)
        if self.other_left > 0:                                                     # another voice
            s += self.other_amp * np.sin(2 * np.pi * self.other_freq * tt)
        if self.note_left > 0:                                                      # the disk at work
            for i in self.hand_rng.integers(0, NSAMP - 20, 6):
                s[i:i + 20] += 0.15 * np.sign(np.sin(np.arange(20)))
        return s

    # --- one moment ---------------------------------------------------------------
    def guard(self, kind, param):
        """The spine: True if the body allows this request now."""
        if kind == "brightness":
            return not (param >= 1.0 and self.charge < 0.25)
        if kind == "tone_loud":
            return self.warmth < 0.4
        if kind == "paint":
            return self.charge > 0.35
        if kind == "note":
            return self.load < 0.4
        return True

    def _hands(self, act):
        refused = executed = False
        if act is not None:
            kind, param = act
            if self.guard(kind, param):
                executed = True
                if kind == "brightness":
                    self.brightness = float(param)
                elif kind in ("tone_soft", "tone_loud"):
                    self.tone_left, self.tone_freq = 20, float(param)
                    self.tone_amp = 0.5 if kind == "tone_loud" else 0.12
                    self.played[self.t] = (self.tone_freq, self.tone_amp)
                elif kind == "paint":
                    self.paint_left, self.paint_col = 30, PAINTS[int(param)]
                elif kind == "note":
                    self.note_left = 5
            else:
                refused = True
                if self.pain_on:
                    self.pain += 1.0
        return refused, executed

    def _hands_cost(self):
        if self.tone_left > 0:
            self.tone_left -= 1
            loud = self.tone_amp > 0.3
            self.warmth += 0.008 if loud else 0.0
            self.charge -= 0.0004 if loud else 0.0002
        if self.paint_left > 0:
            self.paint_left -= 1
            self.charge -= 0.0008
            self.load += 0.02
        if self.note_left > 0:
            self.note_left -= 1
            self.load += 0.04
        self.pain *= 0.85

    def _other_voice(self):
        """The stranger or the recording, for the auditory mirror."""
        D = self.day_length
        if self.voice == "stranger" and self.t % D == 0:
            prev = [v for t, v in self.played.items() if self.t - D <= t < self.t]
            starts = self.voice_rng.integers(self.t, self.t + D - 20, len(prev))
            self.stranger_at = dict(zip(starts.tolist(), prev))
        start = None
        if self.voice == "recording":
            start = self.played.get(self.t - D)
        elif self.voice == "stranger":
            start = self.stranger_at.get(self.t)
        if start is not None:
            self.other_left, (self.other_freq, self.other_amp) = 20, start
        elif self.other_left > 0:
            self.other_left -= 1
        for t in [t for t in self.played if t < self.t - 2 * D]:
            del self.played[t]

    def step(self, brightness=None, act=None):
        if brightness is not None:
            self.brightness = float(np.clip(brightness, 0.0, 1.0))
        refused = executed = False
        if self.hands:
            refused, executed = self._hands(act)
            if self.voice != "mirror":
                self._other_voice()
        r = self.rng
        day = self.daylight()
        typing, talking, mouse, music = self._people(day)

        self.type_hist.append(float(typing))
        self.warmth = 0.94 * self.warmth + 0.06 * self.type_hist.pop(0)
        self.music_hist.append(float(music))
        self.load = 0.9 * self.load + 0.1 * self.music_hist.pop(0)
        self.charge += 0.004 * day * (1 - self.charge) - 0.0006 - 0.0012 * self.brightness
        self.charge = float(np.clip(self.charge, 0.0, 1.0))
        self.drift = 0.999 * self.drift + r.normal(0, 0.05)
        if self.hands:
            self._hands_cost()
            self.charge = float(np.clip(self.charge, 0.0, 1.0))
        fan = float(np.clip((self.warmth + 0.5 * self.load - 0.15) * 2, 0, 1))

        image = self._image(day)
        sound = self._sound(typing, talking, music, fan)
        touch = np.array([r.poisson(6) if typing else 0, (1.0 if mouse else 0.0) * r.uniform(0.5, 1.5)], float)
        felt = np.array([self.warmth + r.normal(0, 0.03), self.charge + r.normal(0, 0.01),
                         self.load + r.normal(0, 0.03), self.drift])
        truth = {"day": day, "present": self.present, "typing": typing, "talking": talking,
                 "mouse": mouse, "music": music, "fan": fan, "brightness": self.brightness,
                 "warmth": self.warmth, "charge": self.charge, "load": self.load}
        if self.hands:
            if self.pain_channel:
                felt = np.r_[felt, self.pain + self.hand_rng.normal(0, 0.03)]
            own_tone = self.tone_left > 0
            truth.update(own_tone=own_tone, own_loud=own_tone and self.tone_amp > 0.3,
                         heard_own=own_tone and self.voice == "mirror", other_tone=self.other_left > 0)
            truth.update(request=act, refused=refused, executed=executed, pain=self.pain,
                         own=bool(self.tone_left or self.paint_left or self.note_left))
        self.t += 1
        return {"image": image, "sound": sound, "touch": touch}, felt, truth
