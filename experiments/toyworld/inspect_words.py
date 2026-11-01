"""Open up one Olvasó after a life and draw what it learned.

For the words that read most often: the sensed movement each word stands for, and the felt
change it expects over the following ticks. Channel names are added here by the observer,
using the secret key. Olvasó itself never had them.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # run from a clone without installing
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from endolexis.toyworld import ToyWorld, Collector, Olvaso, SENSED, FELT


def live(seed=2, days=30, threshold=100.0):
    world = ToyWorld(seed=seed)
    col = Collector(len(SENSED), len(FELT), seed=seed)
    olv = Olvaso(len(SENSED), len(FELT), threshold=threshold, seed=seed)
    reads = np.zeros((olv.max_words, len(FELT)), dtype=int)
    b = None
    for _ in range(days * 1000):
        s, f, _truth = world.step(b)
        sa, fa = col.anonymise(s, f)
        b, r = olv.live(sa, fa)
        for d, w in enumerate(r):
            if w >= 0:
                reads[w, d] += 1
    return olv, col, reads


def main(seed=2, n_show=5, out="learned_words.png"):
    olv, col, reads = live(seed)
    ns, nf, W = olv.ns, olv.nf, olv.window
    s_sign = np.sign(col.sensed_gain)
    f_sign = np.sign(col.felt_gain)
    anon_of_true_felt = {col.felt_perm[a]: a for a in range(nf)}

    rows = []  # (title, word, true felt index)
    for true_f in (FELT.index("warmth"), FELT.index("charge")):
        a = anon_of_true_felt[true_f]
        top = np.argsort(reads[:, a])[::-1]
        k = 2
        for w in top[:k]:
            if reads[w, a] > 0:
                rows.append((FELT[true_f], int(w), true_f, int(reads[w, a])))
        if true_f == FELT.index("warmth"):
            # the busiest word that expects warmth to RISE (a readable lag above +1 z)
            n = olv.cnt[:, :, a]
            var = olv.m2[:, :, a] / np.maximum(n - 1, 1)
            mu = olv.mean[:, :, a] * f_sign[a]
            ok = (n >= olv.min_count) & (var < olv.consistency) & (mu > 1.0)
            warm_words = np.where(ok.any(axis=1) & (reads[:, a] > 0))[0]
            if len(warm_words):
                w = int(warm_words[np.argmax(reads[warm_words, a])])
                rows.append(("warmth", w, true_f, int(reads[w, a])))
    # a word that tried hardest to say something about drift
    a_drift = anon_of_true_felt[FELT.index("drift")]
    cnt = olv.cnt[:, :, a_drift]
    w_drift = int(np.argmax(cnt.sum(axis=1)))
    rows.append(("drift", w_drift, FELT.index("drift"), int(reads[w_drift, a_drift])))

    colors = {"light": "#BA7517", "activity": "#1D9E75", "sound": "#7F77DD"}
    fig, axes = plt.subplots(len(rows), 2, figsize=(9, 2.1 * len(rows)),
                             gridspec_kw={"width_ratios": [1, 1.6]})
    lags = np.arange(olv.max_lag + 1)
    for i, (felt_name, w, true_f, nreads) in enumerate(rows):
        ax_m, ax_f = axes[i]
        v = olv.centroids[w].reshape(W, ns)
        for a in range(ns):
            name = SENSED[col.sensed_perm[a]]
            ax_m.plot(range(-W + 1, 1), v[:, a] * s_sign[a], color=colors[name], lw=2, label=name)
        ax_m.axhline(0, color="#999", lw=0.5)
        ax_m.set_ylim(-3, 3.5)
        ax_m.set_ylabel(f"word {w}", fontsize=9)
        ax_m.tick_params(labelsize=8)
        if i == 0:
            ax_m.set_title("What the word is: a sensed movement\n(last 6 ticks, z-units)", fontsize=10)
            ax_m.legend(fontsize=7, loc="upper left", ncol=3, frameon=False)

        a = anon_of_true_felt[true_f]
        n = olv.cnt[w, :, a]
        mu = olv.mean[w, :, a] * f_sign[a]
        sd = np.sqrt(olv.m2[w, :, a] / np.maximum(n - 1, 1))
        ok = (n >= olv.min_count) & (sd ** 2 < olv.consistency)
        ax_f.fill_between(lags, mu - sd, mu + sd, color="#D85A30", alpha=0.15, lw=0)
        ax_f.plot(lags, mu, color="#D85A30", lw=1, alpha=0.5)
        ax_f.plot(lags[ok], mu[ok], "o", color="#993C1D", ms=2.5)
        ax_f.axhline(0, color="#999", lw=0.5)
        ax_f.set_ylim(-3, 3)
        ax_f.tick_params(labelsize=8)
        ax_f.text(0.99, 0.92, f"{felt_name}  ·  read {nreads}×", transform=ax_f.transAxes,
                  ha="right", va="top", fontsize=9)
        if i == 0:
            ax_f.set_title("What it means: expected felt state after the word\n"
                           "(band = spread, dots = consistent enough to read)", fontsize=10)
        if i == len(rows) - 1:
            ax_f.set_xlabel("ticks after the word", fontsize=9)
            ax_m.set_xlabel("ticks", fontsize=9)
    fig.tight_layout()
    path = Path(__file__).with_name(out)
    fig.savefig(path, dpi=130)
    print(path, rows, "words:", olv.n_words)


if __name__ == "__main__":
    main()
