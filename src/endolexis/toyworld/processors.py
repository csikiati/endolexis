"""Processor entities: fixed, clockwork feature extractors between the raw senses and Olvaso.

They report perception, never names: "much motion, moving left", "a tone with a strong pitch,
pulsing four times a second", never "a person" or "a voice". Olvaso receives only their end
products, anonymised by the collector. Nothing here learns.

  vision  (11): V0 retina  - brightness, red-green, blue-yellow, contrast, left-right and
                             top-bottom balance
                V1 motion  - motion energy, and where the moving thing went (dx, dy)
                V2 form    - horizontal and vertical edge energy
  hearing  (9): A0 cochlea - loudness; low, mid and high band shares
                A1 timbre  - spectral centroid, flatness (noise vs tone), pitch strength
                A2 rhythm  - onsets, slow pulsing (envelope modulation)
  touch    (2): key presses, mouse movement
"""
import numpy as np

from .room import FS, NSAMP

VISION = ["brightness", "red_green", "blue_yellow", "contrast", "left_right", "top_bottom",
          "motion", "motion_dx", "motion_dy", "edges_h", "edges_v"]
HEARING = ["loudness", "low", "mid", "high", "centroid", "flatness", "pitch", "onsets", "pulsing"]
TOUCH = ["keys", "mouse"]
GROUPS = {"vision": VISION, "hearing": HEARING, "touch": TOUCH}
# the v0 body's three senses, for comparison: light, loudness, activity
V0_SENSES = [("vision", "brightness"), ("hearing", "loudness"), ("touch", "keys")]


class Vision:
    def __init__(self):
        self.prev = None
        self.background = None
        self.prev_c = None

    def __call__(self, img):
        lum = img.mean(axis=2)
        r, g, b = img[..., 0].mean(), img[..., 1].mean(), img[..., 2].mean()
        n = lum.shape[0] // 2
        v0 = [lum.mean(), r - g, b - (r + g) / 2, lum.std(),
              lum[:, :n].mean() - lum[:, n:].mean(), lum[:n].mean() - lum[n:].mean()]
        if self.prev is None:
            self.prev, self.background = lum.copy(), lum.copy()
        motion = np.abs(lum - self.prev).mean()
        fg = np.abs(lum - self.background)                 # what stands out from the usual scene
        self.background += 0.01 * (lum - self.background)
        w = fg.sum() + 1e-9
        yy, xx = np.mgrid[0:lum.shape[0], 0:lum.shape[1]]
        c = np.array([(fg * xx).sum() / w, (fg * yy).sum() / w])
        d = c - self.prev_c if self.prev_c is not None else np.zeros(2)
        self.prev_c, self.prev = c, lum.copy()
        eh = np.abs(np.diff(lum, axis=0)).mean()
        ev = np.abs(np.diff(lum, axis=1)).mean()
        return np.array(v0 + [motion, d[0], d[1], eh, ev])


class Hearing:
    def __init__(self, sub=8):
        self.sub = sub
        f = np.fft.rfftfreq(NSAMP // sub, 1 / FS)
        self.freqs = f
        self.bands = [(f < 300), (f >= 300) & (f < 1500), (f >= 1500)]
        lags = np.arange(int(FS / 400), int(FS / 60))
        self.lags = lags

    def __call__(self, s):
        frames = s.reshape(self.sub, -1)
        spec = np.abs(np.fft.rfft(frames * np.hanning(frames.shape[1]), axis=1)) ** 2
        p = spec.mean(axis=0) + 1e-12
        total = p.sum()
        loud = 10 * np.log10(np.mean(s ** 2) + 1e-9)
        shares = [p[m].sum() / total for m in self.bands]
        centroid = (self.freqs * p).sum() / total
        flat = np.exp(np.mean(np.log(p))) / np.mean(p)
        x = s[:1024] - s[:1024].mean()
        ac = np.correlate(x, x, "full")[1023:]
        pitch = ac[self.lags].max() / (ac[0] + 1e-9)
        env = np.sqrt((frames ** 2).mean(axis=1))
        onsets = float(np.sum(env[1:] > 2.0 * env[:-1] + 1e-4))
        pulsing = env.std() / (env.mean() + 1e-9)
        return np.array([loud] + shares + [centroid, flat, pitch, onsets, pulsing])


class Processors:
    """All processor entities of one body. Returns their end products, group by group."""
    def __init__(self):
        self.vision, self.hearing = Vision(), Hearing()

    def __call__(self, raw):
        return {"vision": self.vision(raw["image"]), "hearing": self.hearing(raw["sound"]),
                "touch": np.asarray(raw["touch"], float)}
