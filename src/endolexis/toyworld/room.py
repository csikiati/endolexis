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
"""
import numpy as np

FELT1 = ["warmth", "charge", "load", "drift"]
SIZE, FS, NSAMP = 16, 8000, 2048


class Room:
    def __init__(self, seed=0, day_length=1000, warmth_delay=10, load_delay=5):
        self.rng = np.random.default_rng(seed)
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
        return s

    # --- one moment ---------------------------------------------------------------
    def step(self, brightness=None):
        if brightness is not None:
            self.brightness = float(np.clip(brightness, 0.0, 1.0))
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
        fan = float(np.clip((self.warmth + 0.5 * self.load - 0.15) * 2, 0, 1))

        image = self._image(day)
        sound = self._sound(typing, talking, music, fan)
        touch = np.array([r.poisson(6) if typing else 0, (1.0 if mouse else 0.0) * r.uniform(0.5, 1.5)], float)
        felt = np.array([self.warmth + r.normal(0, 0.03), self.charge + r.normal(0, 0.01),
                         self.load + r.normal(0, 0.03), self.drift])
        truth = {"day": day, "present": self.present, "typing": typing, "talking": talking,
                 "mouse": mouse, "music": music, "fan": fan, "brightness": self.brightness,
                 "warmth": self.warmth, "charge": self.charge, "load": self.load}
        self.t += 1
        return {"image": image, "sound": sound, "touch": touch}, felt, truth
