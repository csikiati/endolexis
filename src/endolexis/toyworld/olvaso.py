"""Olvasó v0: reads its felt states through words formed from sensed movements.

1. Words: short windows of the sensed bundle (movements, not snapshots) are grouped by an
   online clustering; a new word is born when nothing known is close enough.
2. Felt profiles: for every word and every delay after it (0..max_lag), Olvasó keeps the mean
   and spread of each felt dimension that followed.
3. Reading: for each felt dimension, Olvasó looks at the words it recently sensed. A word can
   read the state if it has reliably preceded it (low spread, across separate occasions) and
   its expected value fits the present state. Otherwise the state is unread.
4. Pressure: unread states build pressure. Past a threshold, Olvasó acts (changes screen
   brightness) and lives with whatever the world then brings. A learning Olvasó lowers its
   threshold if acting was followed by more reading, and raises it if not.
Olvasó never sees channel names, nor the secret key.
"""
import numpy as np


class RunningNorm:
    def __init__(self, n):
        self.n = 0
        self.mean = np.zeros(n)
        self.m2 = np.zeros(n)

    def update(self, x):
        self.n += 1
        d = x - self.mean
        self.mean += d / self.n
        self.m2 += d * (x - self.mean)

    def z(self, x):
        if self.n < 2:
            return np.zeros_like(x)
        sd = np.sqrt(self.m2 / (self.n - 1)) + 1e-9
        return (x - self.mean) / sd


class Olvaso:
    def __init__(self, n_sensed, n_felt, threshold=100.0, learn_threshold=False, seed=0,
                 window=6, radius=3.0, max_words=200, max_lag=60,
                 consistency=0.35, fit=0.35, min_count=8, min_episodes=4, episode_gap=200,
                 memory=None, doubt_memory=None, doubt_limit=0.05, doubt_min=30):
        # memory: None = meanings are lifetime averages (never forget); a number N = each meaning
        # rests on roughly its last N experiences, so old experience slowly fades
        # doubt_memory: a slow memory (about N experiences) of how much each meaning has WANDERED.
        # A meaning may read only while its wandering stays below doubt_limit.
        self.memory = memory
        self.lt_mean = None
        self.doubt_memory, self.doubt_limit, self.doubt_min = doubt_memory, doubt_limit, doubt_min
        self.rng = np.random.default_rng(seed + 20_000)
        self.ns, self.nf = n_sensed, n_felt
        self.window, self.radius, self.max_words, self.max_lag = window, radius, max_words, max_lag
        self.consistency, self.fit = consistency, fit
        self.min_count, self.min_episodes, self.episode_gap = min_count, min_episodes, episode_gap

        self.snorm = RunningNorm(n_sensed)
        self.fnorm = RunningNorm(n_felt)
        self.sbuf = []
        self.centroids = np.zeros((max_words, window * n_sensed))
        self.n_words = 0

        L = max_lag + 1
        self.cnt = np.zeros((max_words, L, n_felt))
        self.mean = np.zeros((max_words, L, n_felt))
        self.m2 = np.zeros((max_words, L, n_felt))
        self.dn = np.zeros((max_words, L, n_felt))     # doubt: updates seen
        self.dmean = np.zeros((max_words, L, n_felt))  # doubt: slow average of the meaning
        self.dvar = np.zeros((max_words, L, n_felt))   # doubt: how much the meaning wanders
        self.word_last_seen = np.full(max_words, -10**9)
        self.word_episodes = np.zeros(max_words, dtype=int)
        self.history = []  # most recent word first, up to L entries

        self.threshold = float(threshold)
        self.learn_threshold = learn_threshold
        self.pressure = 0.0
        self.brightness = 0.5
        self.t = 0
        self.pending_eval = []  # (eval_time, read_rate_before)
        self.read_log = []      # recent fraction-read values

    # --- words -------------------------------------------------------------
    def _word(self, s_z):
        self.sbuf.append(s_z)
        if len(self.sbuf) > self.window:
            self.sbuf.pop(0)
        if len(self.sbuf) < self.window:
            return None
        v = np.concatenate(self.sbuf)
        if self.n_words == 0:
            self.centroids[0] = v
            self.n_words = 1
            return 0
        d = np.linalg.norm(self.centroids[:self.n_words] - v, axis=1)
        w = int(np.argmin(d))
        if d[w] > self.radius and self.n_words < self.max_words:
            w = self.n_words
            self.centroids[w] = v
            self.n_words += 1
        else:
            self.centroids[w] += 0.02 * (v - self.centroids[w])
        return w

    # --- one moment of life -----------------------------------------------
    def live(self, sensed, felt):
        """Takes one moment of anonymous input. Returns (brightness, readings).
        readings[d] = word index that read felt dimension d, or -1 if unread."""
        self.snorm.update(sensed)
        self.fnorm.update(felt)
        s_z, f_z = self.snorm.z(sensed), self.fnorm.z(felt)

        w = self._word(s_z)
        if w is not None:
            if self.t - self.word_last_seen[w] > self.episode_gap:
                self.word_episodes[w] += 1
            self.word_last_seen[w] = self.t
            self.history.insert(0, w)
            if len(self.history) > self.max_lag + 1:
                self.history.pop()

        readings = self._read(f_z)
        self._learn_profiles(f_z)
        self._pressure_and_act(readings)
        self.t += 1
        return self.brightness, readings

    def sleep_moment(self, felt, sensed=None, dream_word=None, learn=False):
        """Lid closed. No acting, norms frozen. `sensed` is None when nothing gets through, or a
        leaked fragment of the outer world. `dream_word` replays one of Olvaso's own words from
        memory, as if sensed. `learn` lets meanings learn from whatever the night brings (dreams
        included). Time still passes: each moment without a word pushes an empty slot into the
        delay line."""
        f_z = self.fnorm.z(felt)
        w = self._word(self.snorm.z(sensed)) if sensed is not None else None
        if dream_word is not None:
            w = int(dream_word)
        self.history.insert(0, -1 if w is None else w)
        if len(self.history) > self.max_lag + 1:
            self.history.pop()
        readings = self._read(f_z)
        if learn:
            self._learn_profiles(f_z)
        self.t += 1
        return readings, f_z

    # --- long-term memory, filled by consolidation during sleep ---------------
    def enable_long_term(self, slots=3):
        """Extra long-term slots per meaning (word x delay x felt): consolidation can add a new
        version of a meaning instead of overwriting the old one (cf. parameter expansion)."""
        shape = self.cnt.shape + (slots,)
        self.lt_mean = np.zeros(shape)
        self.lt_var = np.full(shape, np.inf)
        self.lt_used = np.zeros(shape, dtype=bool)
        self.lt_age = np.zeros(shape, dtype=int)

    def consolidate(self, merge=0.3, prune=False):
        """Copy every settled fast meaning into long-term memory: into the slot it resembles,
        or a free one, or over the oldest. With prune, the fast meaning then starts afresh."""
        var = self.m2 / np.maximum(self.cnt - 1, 1)
        ok = (self.cnt >= self.min_count) & (var < self.consistency)
        ok &= (self.word_episodes >= self.min_episodes)[:, None, None]
        if self.doubt_memory is not None:
            ok &= (self.dn >= self.doubt_min) & (self.dvar < self.doubt_limit)
        if not ok.any():
            return 0
        dist = np.where(self.lt_used, np.abs(self.lt_mean - self.mean[..., None]), np.inf)
        near = np.argmin(dist, axis=-1)
        near_d = np.take_along_axis(dist, near[..., None], -1)[..., 0]
        free = np.argmin(self.lt_used, axis=-1)                     # first unused slot
        has_free = ~np.take_along_axis(self.lt_used, free[..., None], -1)[..., 0]
        oldest = np.argmax(np.where(self.lt_used, self.lt_age, -1), axis=-1)
        slot = np.where(near_d < merge, near, np.where(has_free, free, oldest))
        merge_mask = ok & (near_d < merge)
        idx = np.nonzero(ok)
        k = slot[idx]
        old_m, old_v = self.lt_mean[idx + (k,)], self.lt_var[idx + (k,)]
        mm = merge_mask[idx]
        self.lt_mean[idx + (k,)] = np.where(mm, 0.7 * old_m + 0.3 * self.mean[idx], self.mean[idx])
        self.lt_var[idx + (k,)] = np.where(mm, 0.7 * old_v + 0.3 * var[idx], var[idx])
        self.lt_used[idx + (k,)] = True
        self.lt_age[self.lt_used] += 1
        self.lt_age[idx + (k,)] = 0
        if prune:
            for a in (self.cnt, self.mean, self.m2, self.dn, self.dmean, self.dvar):
                a[ok] = 0
        return int(ok.sum())

    def read_state(self, f_z):
        """Try to read a remembered felt state (already in z-units) with the words sensed lately."""
        return self._read(f_z)

    def _candidates(self):
        if not self.history:
            return None, None
        words = np.array(self.history)
        lags = np.arange(len(words))
        keep = words >= 0
        if not keep.any():
            return None, None
        return words[keep], lags[keep]

    def _read(self, f_z):
        readings = np.full(self.nf, -1)
        words, lags = self._candidates()
        if words is None or self.fnorm.n < 200:
            return readings
        cnt = self.cnt[words, lags]                     # (k, nf)
        mu = self.mean[words, lags]
        var = self.m2[words, lags] / np.maximum(cnt - 1, 1)
        eligible = (cnt >= self.min_count) & (var < self.consistency)
        eligible &= (self.word_episodes[words] >= self.min_episodes)[:, None]
        if self.doubt_memory is not None:
            eligible &= (self.dn[words, lags] >= self.doubt_min) & \
                        (self.dvar[words, lags] < self.doubt_limit)
        err = (mu - f_z[None, :]) ** 2
        err = np.where(eligible, err, np.inf)
        if getattr(self, "lt_mean", None) is not None:
            lt_ok = self.lt_used[words, lags] & (self.lt_var[words, lags] < self.consistency)
            lt_ok &= (self.word_episodes[words] >= self.min_episodes)[:, None, None]
            lt_err = np.where(lt_ok, (self.lt_mean[words, lags] - f_z[None, :, None]) ** 2, np.inf)
            err = np.minimum(err, lt_err.min(axis=-1))
        best = np.argmin(err, axis=0)
        best_err = err[best, np.arange(self.nf)]
        ok = best_err < self.fit
        readings[ok] = words[best[ok]]
        return readings

    def _learn_profiles(self, f_z):
        words, lags = self._candidates()
        if words is None:
            return
        if self.memory is not None:
            c = self.cnt[words, lags]
            full = c >= self.memory
            if full.any():
                # keep the spread estimate, but let the count stop growing: old experience fades
                scale = np.where(full, (self.memory - 2) / np.maximum(c - 1, 1), 1.0)
                self.m2[words, lags] *= scale
                self.cnt[words, lags] = np.where(full, self.memory - 1, c)
        self.cnt[words, lags] += 1
        n = self.cnt[words, lags]
        d = f_z[None, :] - self.mean[words, lags]
        self.mean[words, lags] += d / n
        self.m2[words, lags] += d * (f_z[None, :] - self.mean[words, lags])
        if self.doubt_memory is not None:
            self.dn[words, lags] += 1
            a = np.maximum(1.0 / self.doubt_memory, 1.0 / self.dn[words, lags])
            dd = self.mean[words, lags] - self.dmean[words, lags]
            self.dmean[words, lags] += a * dd
            self.dvar[words, lags] = (1 - a) * (self.dvar[words, lags] + a * dd * dd)

    def _pressure_and_act(self, readings):
        unread = int(np.sum(readings < 0))
        self.read_log.append(1 - unread / self.nf)
        if len(self.read_log) > 100:
            self.read_log.pop(0)
        self.pressure = 0.99 * self.pressure + unread

        # judge earlier actions: did reading improve afterwards?
        while self.pending_eval and self.pending_eval[0][0] <= self.t:
            _, before = self.pending_eval.pop(0)
            after = float(np.mean(self.read_log[-50:]))
            if self.learn_threshold:
                self.threshold *= 0.9 if after > before + 0.02 else 1.05
                self.threshold = float(np.clip(self.threshold, 5, 5000))

        if self.pressure > self.threshold and self.fnorm.n > 200:
            options = [b for b in (0.0, 0.5, 1.0) if b != self.brightness]
            self.brightness = float(self.rng.choice(options))
            self.pressure = 0.0
            before = float(np.mean(self.read_log[-50:]))
            self.pending_eval.append((self.t + 50, before))
            self.acted = True
        else:
            self.acted = False
