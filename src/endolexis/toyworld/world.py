"""Toy world: a simulated body with three outer (sensed) and three inner (felt) channels.

Ground truth, known only to the world and the observer:
  sensed: light    - day/night cycle + Olvasó's own brightness action + noise
          activity - random bursts, more likely by day
          sound    - follows activity, plus noise
  felt:   warmth   - rises ~10 ticks AFTER activity, then fades   (hidden link 1, delayed)
          charge   - drains slowly, refills by day; brightness costs charge (hidden link 2, slow,
                     and partly self-caused)
          drift    - random wandering linked to nothing           (control: must stay unread)
"""
import numpy as np

SENSED = ["light", "activity", "sound"]
FELT = ["warmth", "charge", "drift"]


class ToyWorld:
    def __init__(self, seed=0, day_length=1000, warmth_delay=10, night_heat=0.0):
        # night_heat: chance per dark, quiet moment of an inner warmth surge with no outer cause
        self.night_heat = night_heat
        self.rng = np.random.default_rng(seed)
        self.day_length = day_length
        self.warmth_delay = warmth_delay
        self.t = 0
        self.brightness = 0.5
        self.burst_left = 0
        self.activity_hist = [0.0] * (warmth_delay + 1)
        self.warmth = 0.0
        self.charge = 0.7
        self.drift = 0.0

    def set_warmth_delay(self, delay):
        """Change how long warmth lags behind activity (e.g. a change of season)."""
        hist = self.activity_hist[-(delay + 1):]
        self.activity_hist = [0.0] * (delay + 1 - len(hist)) + hist
        self.warmth_delay = delay

    def daylight(self):
        phase = 2 * np.pi * self.t / self.day_length
        return max(0.0, np.sin(phase))

    def step(self, brightness=None):
        r = self.rng
        if brightness is not None:
            self.brightness = float(np.clip(brightness, 0.0, 1.0))
        day = self.daylight()

        # activity bursts, more likely by day
        if self.burst_left > 0:
            self.burst_left -= 1
            activity = 1.0
        else:
            activity = 0.0
            if r.random() < 0.001 + 0.006 * day:
                self.burst_left = int(r.integers(30, 80))
        activity_obs = activity + r.normal(0, 0.1)

        light = day + 0.5 * self.brightness + r.normal(0, 0.05)
        sound = 0.8 * activity + r.normal(0, 0.15)

        # felt
        self.activity_hist.append(activity)
        delayed = self.activity_hist.pop(0)
        self.warmth = 0.94 * self.warmth + 0.06 * delayed
        inner_event = False
        if self.night_heat and day == 0 and activity == 0 and r.random() < self.night_heat:
            self.warmth += 0.8
            inner_event = True
        warmth_obs = self.warmth + r.normal(0, 0.03)

        self.charge += 0.004 * day * (1 - self.charge) - 0.0006 - 0.0012 * self.brightness
        self.charge = float(np.clip(self.charge, 0.0, 1.0))
        charge_obs = self.charge + r.normal(0, 0.01)

        self.drift = 0.999 * self.drift + r.normal(0, 0.05)

        self.t += 1
        sensed = np.array([light, activity_obs, sound])
        felt = np.array([warmth_obs, charge_obs, self.drift])
        truth = {"activity": activity, "day": day, "brightness": self.brightness,
                 "inner_event": inner_event, "warmth": self.warmth}
        return sensed, felt, truth
