package com.readingourselves.elemer.core

import java.io.Serializable
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.sqrt

/**
 * Olvasó v0, the reader: a port of endolexis/toyworld/olvaso.py (the parts the symbiote uses).
 *
 * 1. Words: short windows of the sensed bundle (movements, not snapshots) are grouped by an online
 *    clustering; a new word is born when nothing known is close enough.
 * 2. Meanings: for every word and every delay after it (0..maxLag), the mean and spread of each felt
 *    dimension that followed.
 * 3. Reading: a felt dimension is read by a recently sensed word that has reliably preceded it (low spread,
 *    across separate occasions, settled under doubt, fitting now and over the last days).
 * 4. Pressure: unread states build pressure; past a threshold it acts.
 *
 * Readings: word number, -1 unread (adds to pressure), -2 disregarded (habituated).
 * Olvasó never sees channel names.
 */
class Olvaso(
    val ns: Int,
    nFelt: Int,
    var threshold: Double = 100.0,
    var learnThreshold: Boolean = false,
    seed: Long = 0,
    val window: Int = 6,
    val radius: Double = 3.0,
    val maxWords: Int = 200,
    val maxLag: Int = 60,
    val consistency: Double = 0.35,
    val fit: Double = 0.35,
    val minCount: Int = 8,
    val minEpisodes: Int = 4,
    val episodeGap: Int = 200,
    val memory: Int? = null,
    val doubtMemory: Int? = null,
    val doubtLimit: Double = 0.05,
    val doubtMin: Int = 30,
    val adapt: Int? = null,
    val adaptBoth: Boolean = false,
    val salience: Double = 1.0,
    val onsets: Boolean = false,
    val rehear: Int? = null,
    val slowFit: Boolean = false,
) : Serializable {
    val nfIn = nFelt
    val nf = if (adapt != null && adaptBoth) 2 * nFelt else nFelt
    private val L = maxLag + 1
    private val dim = window * ns
    private val rng = java.util.Random(seed + 20_000)

    val snorm = RunningNorm(ns)
    val fnorm = RunningNorm(nfIn)
    private val anorm = RunningNorm(nfIn)
    private var base: DoubleArray? = null
    private var nSeen = 0

    private val sbuf = DoubleArray(dim)
    private var sbufLen = 0
    val centroids = DoubleArray(maxWords * dim)
    var nWords = 0
        private set

    // meanings: index ((w * L) + lag) * nf + d
    private val cnt = DoubleArray(maxWords * L * nf)
    private val mean = DoubleArray(maxWords * L * nf)
    private val m2 = DoubleArray(maxWords * L * nf)
    private val dn = DoubleArray(maxWords * L * nf)
    private val dmean = DoubleArray(maxWords * L * nf)
    private val dvar = DoubleArray(maxWords * L * nf)
    val alive = BooleanArray(maxWords)
    val wordUses = IntArray(maxWords)
    val wordLastSeen = LongArray(maxWords) { NEVER }
    val wordEpisodes = IntArray(maxWords)

    /** Most recent word first, up to L entries (-1: an empty place). */
    private val history = IntArray(L)
    private var histLen = 0

    var pressure = 0.0
    var brightness = 0.5
    var t = 0L
        private set
    var sensedWord = -1
        private set
    var lastErr = DoubleArray(nf) { Double.POSITIVE_INFINITY }
        private set
    var acted = false
        private set
    private var prevWord = -1
    private var run = 0
    private val pendingEval = ArrayList<Pair<Long, Double>>()
    private val readLog = ArrayList<Double>()

    private fun ix(w: Int, lag: Int) = (w * L + lag) * nf

    // --- words -------------------------------------------------------------
    private fun word(sZ: DoubleArray): Int? {
        if (sbufLen == window) {
            System.arraycopy(sbuf, ns, sbuf, 0, dim - ns)
            sbufLen--
        }
        System.arraycopy(sZ, 0, sbuf, sbufLen * ns, ns)
        sbufLen++
        if (sbufLen < window) return null
        val v = sbuf
        if (nWords == 0) return newWord(v)
        val tmp = DoubleArray(dim)
        var best = 0
        var bestD = Double.POSITIVE_INFINITY
        for (w in 0 until nWords) {
            val d = if (!alive[w]) Double.POSITIVE_INFINITY else {
                val o = w * dim
                for (i in 0 until dim) {
                    val e = centroids[o + i] - v[i]; tmp[i] = e * e
                }
                sqrt(Num.pairwise(tmp))
            }
            if (w == 0 || d < bestD) { best = w; bestD = d }      // numpy argmin: the first smallest
        }
        if (bestD > radius && (nWords < maxWords || !alive.all { it })) return newWord(v)
        val o = best * dim
        for (i in 0 until dim) centroids[o + i] += 0.02 * (v[i] - centroids[o + i])
        wordUses[best] += 1
        return best
    }

    private fun newWord(v: DoubleArray): Int {
        val w: Int
        if (nWords < maxWords) {
            w = nWords; nWords++
        } else {
            w = alive.indexOfFirst { !it }.let { if (it < 0) 0 else it }
            clear(w)
        }
        System.arraycopy(v, 0, centroids, w * dim, dim)
        alive[w] = true
        wordUses[w] = 1
        return w
    }

    private fun clear(w: Int) {
        val a = ix(w, 0)
        val b = ix(w + 1, 0)
        for (arr in arrayOf(cnt, mean, m2, dn, dmean, dvar)) java.util.Arrays.fill(arr, a, b, 0.0)
        wordEpisodes[w] = 0
        wordLastSeen[w] = NEVER
        wordUses[w] = 0
        alive[w] = false
    }

    // --- housekeeping in sleep ------------------------------------------------
    /**
     * Retires words not met for [retireAfter] moments that were never used much, freeing their places;
     * merges near-identical words that mean the same (mergeDist = 0: never merge). Returns (retired, merged).
     */
    fun housekeeping(retireAfter: Int = 5000, keepUses: Int = 200, mergeDist: Double = 1.5,
                     mergeAgree: Double = 0.3, careful: Boolean = false): Pair<Int, Int> {
        val n = nWords
        val retired = (0 until n).filter { alive[it] && t - wordLastSeen[it] > retireAfter && wordUses[it] < keepUses }
        for (w in retired) clear(w)
        var merged = 0
        val live = (0 until n).filter { alive[it] }
        if (live.size > 1 && mergeDist > 0) {
            val gone = HashSet<Int>()
            val tmp = DoubleArray(dim)
            val close = ArrayList<Pair<Int, Int>>()          // distances before any merge, as in Python
            for (a in live.indices) for (b in a + 1 until live.size) {
                val i = live[a]; val j = live[b]
                for (k in 0 until dim) {
                    val e = centroids[i * dim + k] - centroids[j * dim + k]; tmp[k] = e * e
                }
                if (sqrt(Num.pairwise(tmp)) < mergeDist) close.add(i to j)
            }
            for ((i, j) in close) {
                if (i in gone || j in gone) continue
                var any = false; var sum = 0.0; var mx = 0.0; var c = 0
                for (q in 0 until L * nf) {
                    if (cnt[i * L * nf + q] >= minCount && cnt[j * L * nf + q] >= minCount) {
                        val df = abs(mean[i * L * nf + q] - mean[j * L * nf + q])
                        any = true; sum += df; mx = max(mx, df); c++
                    }
                }
                if (any && (if (careful) mx else sum / c) > mergeAgree) continue
                val (keep, drop) = if (wordUses[i] >= wordUses[j]) i to j else j to i
                merge(keep, drop)
                if (careful) {
                    for (q in 0 until L * nf) {
                        dn[keep * L * nf + q] = 0.0; dmean[keep * L * nf + q] = mean[keep * L * nf + q]; dvar[keep * L * nf + q] = 0.0
                    }
                }
                gone.add(drop); merged++
            }
        }
        val dead = retired.toHashSet()
        for (k in 0 until histLen) {
            val h = history[k]
            if (h in dead || (h >= 0 && !alive[h])) history[k] = -1
        }
        return retired.size to merged
    }

    private fun merge(keep: Int, drop: Int) {
        for (q in 0 until L * nf) {
            val a = keep * L * nf + q; val b = drop * L * nf + q
            val nk = cnt[a]; val nd = cnt[b]; val n = nk + nd; val safe = max(n, 1.0)
            val delta = mean[b] - mean[a]
            mean[a] = (nk * mean[a] + nd * mean[b]) / safe
            m2[a] = m2[a] + m2[b] + delta * delta * nk * nd / safe
            cnt[a] = n
            dn[a] = minOf(dn[a], dn[b])
        }
        val uk = wordUses[keep]; val ud = wordUses[drop]
        for (k in 0 until dim) centroids[keep * dim + k] =
            (uk * centroids[keep * dim + k] + ud * centroids[drop * dim + k]) / max(uk + ud, 1)
        wordUses[keep] = uk + ud
        wordEpisodes[keep] = max(wordEpisodes[keep], wordEpisodes[drop])
        wordLastSeen[keep] = max(wordLastSeen[keep], wordLastSeen[drop])
        for (k in 0 until histLen) if (history[k] == drop) history[k] = keep
        clear(drop)
    }

    // --- one moment of life ---------------------------------------------------
    /** One awake moment of anonymous input. Returns the readings; [brightness] holds its action. */
    fun live(sensed: DoubleArray, felt: DoubleArray): IntArray {
        snorm.update(sensed)
        fnorm.update(felt)
        val sZ = snorm.z(sensed)
        val fZ = feel(fnorm.z(felt))
        val w = word(sZ)
        sensedWord = w ?: -1
        if (w != null) {
            if (t - wordLastSeen[w] > episodeGap) wordEpisodes[w] += 1
            wordLastSeen[w] = t
            var heard = w
            if (onsets) {
                run = if (w == prevWord) run + 1 else 0
                prevWord = w
                if (run > 0 && !(rehear != null && rehear > 0 && run % rehear == 0)) heard = -1
            }
            pushHistory(heard)
        }
        val readings = read(fZ)
        learnProfiles(fZ)
        pressureAndAct(readings)
        t += 1
        return readings
    }

    private fun pushHistory(h: Int) {
        val n = minOf(histLen, L - 1)
        System.arraycopy(history, 0, history, 1, n)
        history[0] = h
        histLen = n + 1
    }

    private fun feel(fZ: DoubleArray): DoubleArray {
        val ad = adapt ?: return fZ
        val b = base ?: fZ.copyOf().also { base = it }
        val dev = DoubleArray(nfIn) { fZ[it] - b[it] }
        for (i in 0 until nfIn) b[i] += (fZ[i] - b[i]) / ad
        nSeen += 1
        if (nSeen > 2 * ad) anorm.update(dev)
        val a = if (anorm.n > 1) anorm.z(dev) else DoubleArray(nfIn)
        return if (adaptBoth) fZ + a else a
    }

    private fun read(fZ: DoubleArray): IntArray {
        val readings = IntArray(nf) { -1 }
        val err = DoubleArray(nf) { Double.POSITIVE_INFINITY }
        val bestWord = IntArray(nf) { -1 }
        lastErr = err
        var any = false
        for (k in 0 until histLen) if (history[k] >= 0) { any = true; break }
        if (!any || fnorm.n < 200) return readings
        var first = true
        for (lag in 0 until histLen) {
            val w = history[lag]
            if (w < 0) continue
            val o = ix(w, lag)
            val epOk = wordEpisodes[w] >= minEpisodes
            for (d in 0 until nf) {
                val c = cnt[o + d]
                val v = m2[o + d] / max(c - 1, 1.0)
                var ok = c >= minCount && v < consistency && epOk
                if (doubtMemory != null) ok = ok && dn[o + d] >= doubtMin && dvar[o + d] < doubtLimit
                val e1 = mean[o + d] - fZ[d]
                val e = e1 * e1
                if (slowFit && doubtMemory != null) {
                    val s = dmean[o + d] - fZ[d]
                    ok = ok && s * s < fit
                }
                val ee = if (ok) e else Double.POSITIVE_INFINITY
                if (first || ee < err[d]) { err[d] = ee; bestWord[d] = w }
            }
            first = false
        }
        for (d in 0 until nf) if (err[d] < fit) readings[d] = bestWord[d]
        if (adapt != null) {
            val from = if (adaptBoth) nfIn else 0
            for (d in from until nf) if (abs(fZ[d]) < salience) readings[d] = -2
        }
        return readings
    }

    private fun learnProfiles(fZ: DoubleArray) {
        for (lag in 0 until histLen) {
            val w = history[lag]
            if (w < 0) continue
            val o = ix(w, lag)
            for (d in 0 until nf) {
                val i = o + d
                if (memory != null) {
                    val c = cnt[i]
                    if (c >= memory) {
                        m2[i] *= (memory - 2) / max(c - 1, 1.0)
                        cnt[i] = (memory - 1).toDouble()
                    }
                }
                cnt[i] += 1.0
                val n = cnt[i]
                val dd0 = fZ[d] - mean[i]
                mean[i] += dd0 / n
                m2[i] += dd0 * (fZ[d] - mean[i])
                if (doubtMemory != null) {
                    dn[i] += 1.0
                    val a = max(1.0 / doubtMemory, 1.0 / dn[i])
                    val dd = mean[i] - dmean[i]
                    dmean[i] += a * dd
                    dvar[i] = (1 - a) * (dvar[i] + a * dd * dd)
                }
            }
        }
    }

    private fun pressureAndAct(readings: IntArray) {
        val unread = readings.count { it == -1 }
        readLog.add(1 - unread.toDouble() / nf)
        if (readLog.size > 100) readLog.removeAt(0)
        pressure = 0.99 * pressure + unread
        while (pendingEval.isNotEmpty() && pendingEval[0].first <= t) {
            val before = pendingEval.removeAt(0).second
            val after = recentRead()
            if (learnThreshold) {
                threshold *= if (after > before + 0.02) 0.9 else 1.05
                threshold = threshold.coerceIn(5.0, 5000.0)
            }
        }
        if (pressure > threshold && fnorm.n > 200) {
            val options = doubleArrayOf(0.0, 0.5, 1.0).filter { it != brightness }
            brightness = options[rng.nextInt(options.size)]
            pressure = 0.0
            pendingEval.add(t + 50 to recentRead())
            acted = true
        } else acted = false
    }

    private fun recentRead(): Double {
        val n = minOf(50, readLog.size)
        val a = DoubleArray(n) { readLog[readLog.size - n + it] }
        return Num.mean(a)
    }

    /** How many meanings may read now, for the screen (word, delay, felt dimension). */
    fun settledMeanings(): Int {
        var n = 0
        for (w in 0 until nWords) {
            if (!alive[w] || wordEpisodes[w] < minEpisodes) continue
            for (q in 0 until L * nf) {
                val i = w * L * nf + q
                val c = cnt[i]
                if (c >= minCount && m2[i] / max(c - 1, 1.0) < consistency &&
                    (doubtMemory == null || (dn[i] >= doubtMin && dvar[i] < doubtLimit))) n++
            }
        }
        return n
    }

    companion object {
        const val NEVER = -1_000_000_000L
        private const val serialVersionUID = 1L
    }
}
