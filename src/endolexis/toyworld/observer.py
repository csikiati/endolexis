"""Observer: watches Olvasó read-only, and only afterwards matches what it saw to the truth.

It holds the collector's secret key. Nothing here is ever passed back to Olvasó.
"""
import numpy as np
from .world import FELT


class Observer:
    def __init__(self, key, max_words=200):
        self.felt_true = key["felt"]          # anon felt index -> true felt index
        self.reads = []                       # per tick: readings array
        self.truth_felt = []
        self.activity = []
        self.acted = []
        self.word_act_sum = np.zeros(max_words)  # true activity at each word occurrence
        self.word_occ = np.zeros(max_words)
        self.word_after_action = np.zeros(max_words)
        self.last_action_t = -10**9

    def watch(self, t, olvaso, readings, felt_true, truth):
        self.reads.append(readings.copy())
        self.truth_felt.append(felt_true.copy())
        self.activity.append(truth["activity"])
        self.acted.append(olvaso.acted)
        if olvaso.acted:
            self.last_action_t = t
        if olvaso.history:
            w = olvaso.history[0]
            self.word_occ[w] += 1
            self.word_act_sum[w] += truth["activity"]
            if t - self.last_action_t <= olvaso.window:
                self.word_after_action[w] += 1

    def report(self, olvaso, warmup):
        R = np.array(self.reads)[warmup:]
        T = np.array(self.truth_felt)[warmup:]
        n = len(R)
        out = {}
        # read rate per TRUE felt channel
        for anon_d, true_d in enumerate(self.felt_true):
            out[f"read_{FELT[true_d]}"] = float(np.mean(R[:, anon_d] >= 0))

        # warmth: when truly warm, was it read through an activity word?
        anon_w = self.felt_true.index(FELT.index("warmth"))
        warm = T[:, FELT.index("warmth")]
        hot = warm > np.quantile(warm, 0.85)
        word_activity = np.divide(self.word_act_sum, np.maximum(self.word_occ, 1))
        r = R[hot, anon_w]
        read_hot = r >= 0
        out["warm_moments_read"] = float(np.mean(read_hot))
        active_word = word_activity > 0.1   # words that carry some activity movement
        if read_hot.any():
            out["warm_read_via_activity_word"] = float(np.mean(active_word[r[read_hot]]))
        else:
            out["warm_read_via_activity_word"] = 0.0
        # chance level: share of all word occurrences that are activity words
        out["chance_activity_word"] = float(self.word_occ[active_word].sum() / self.word_occ.sum())

        # self-caused words: words that mostly appear right after own actions
        occ = np.maximum(self.word_occ, 1)
        frac_after = self.word_after_action / occ
        mask = self.word_occ >= 10
        out["self_caused_words"] = int(np.sum((frac_after > 0.6) & mask))

        # the last third of life only: what the grown-up reads
        late = R[-len(R) // 3:]
        for anon_d, true_d in enumerate(self.felt_true):
            out[f"late_read_{FELT[true_d]}"] = float(np.mean(late[:, anon_d] >= 0))

        out["actions"] = int(np.sum(self.acted))
        out["words"] = int(olvaso.n_words)
        out["final_threshold"] = round(olvaso.threshold, 1)
        out["overall_read"] = float(np.mean(R >= 0))
        return out
