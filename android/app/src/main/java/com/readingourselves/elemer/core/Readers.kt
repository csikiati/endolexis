package com.readingourselves.elemer.core

import java.io.Serializable
import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.sqrt

/**
 * Anonymity per processor (endolexis/toyworld/readers.py GroupCollector): within each processor the numbers
 * are shuffled and given a random sign, scale and offset, with a fresh secret key per life. Which numbers come
 * from the same processor is anatomy, not dictionary.
 */
class GroupCollector(sizes: IntArray, nFelt: Int, seed: Long) : Serializable {
    private class Key(n: Int, r: java.util.Random) : Serializable {
        val perm = (0 until n).shuffled(r).toIntArray()
        val gain = DoubleArray(n) { (if (r.nextBoolean()) 1.0 else -1.0) * (0.3 + 4.7 * r.nextDouble()) }
        val off = DoubleArray(n) { -10.0 + 20.0 * r.nextDouble() }
        fun apply(x: DoubleArray) = DoubleArray(perm.size) { x[perm[it]] * gain[it] + off[it] }
    }

    private val groups: List<Key>
    private val felt: Key

    init {
        val r = java.util.Random(seed + 10_000)
        groups = sizes.map { Key(it, r) }
        felt = Key(nFelt, r)
    }

    fun anonymise(inputs: List<DoubleArray>, f: DoubleArray): Pair<List<DoubleArray>, DoubleArray> =
        inputs.mapIndexed { i, x -> groups[i].apply(x) } to felt.apply(f)

    /** For the observer only: where a true felt channel ended up. */
    fun feltIndex(trueIndex: Int) = felt.perm.indexOf(trueIndex)

    companion object { private const val serialVersionUID = 1L }
}

/** Settings shared by every vocabulary of one mind. */
data class Mind(
    val memory: Int? = 300, val doubtMemory: Int? = 3000, val doubtLimit: Double = 0.1, val doubtMin: Int = 30,
    val adapt: Int? = 300, val adaptBoth: Boolean = true, val salience: Double = 1.0, val slowFit: Boolean = true,
    val onsets: Boolean = false, val rehear: Int? = null,
) : Serializable

/**
 * Many vocabularies, one reader (readers.py ManyReaders): each vocabulary forms its own words from its own
 * processors and learns its own meanings; every inner state is read through whichever vocabulary's word fits it
 * best. Pressure and action are shared: one reader, one body.
 */
open class ManyReaders(
    sizes: IntArray, nFelt: Int, var threshold: Double = 100.0, seed: Long = 0,
    maxWords: IntArray, radius: DoubleArray, val compete: Boolean = false, mind: Mind = Mind(),
) : Serializable {
    val parts: List<Olvaso> = sizes.indices.map { i ->
        Olvaso(sizes[i], nFelt, threshold = Double.POSITIVE_INFINITY, seed = seed + 101 * i, maxWords = maxWords[i],
            radius = radius[i], memory = mind.memory, doubtMemory = mind.doubtMemory, doubtLimit = mind.doubtLimit,
            doubtMin = mind.doubtMin, adapt = mind.adapt, adaptBoth = mind.adaptBoth, salience = mind.salience,
            slowFit = mind.slowFit, onsets = mind.onsets, rehear = mind.rehear)
    }
    val offsets = IntArray(sizes.size).also { for (i in 1 until it.size) it[i] = it[i - 1] + maxWords[i - 1] }
    val totalWords = maxWords.sum()
    val nf = parts[0].nf
    var pressure = 0.0
    var brightness = 0.5
    protected val rng = java.util.Random(seed + 20_000)
    var t = 0L
        protected set

    /** One moment for every vocabulary; returns the shared readings. */
    fun read(inputs: List<DoubleArray>, felt: DoubleArray): IntArray {
        val k = parts.size
        val R = Array(k) { IntArray(0) }
        val E = Array(k) { DoubleArray(0) }
        for (i in 0 until k) {
            val r = parts[i].live(inputs[i], felt)
            R[i] = r
            E[i] = DoubleArray(nf) { d -> if (r[d] >= 0) parts[i].lastErr[d] else Double.POSITIVE_INFINITY }
        }
        val readings = IntArray(nf)
        for (d in 0 until nf) {
            var best = 0
            for (i in 1 until k) if (E[i][d] < E[best][d]) best = i
            var hit = E[best][d].isFinite()
            if (compete) {
                val offering = maxOf((0 until k).count { E[it][d].isFinite() }, 1)
                hit = hit && E[best][d] < parts[0].fit / offering
            }
            readings[d] = if (hit) offsets[best] + R[best][d] else -1
            if (!hit && (0 until k).any { R[it][d] == -2 }) readings[d] = -2
        }
        pressure = 0.99 * pressure + readings.count { it == -1 }
        return readings
    }

    /** True when unread pressure has grown past the threshold: it is time to act. */
    fun urge() = pressure > threshold && parts[0].fnorm.n > 200

    /** The word each vocabulary sensed this moment, in shared numbering (-1: none). */
    fun wordsNow() = IntArray(parts.size) { if (parts[it].sensedWord >= 0) offsets[it] + parts[it].sensedWord else -1 }

    fun alive(): BooleanArray = parts.flatMap { p -> p.alive.toList() }.toBooleanArray()

    fun housekeeping(retireAfter: Int = 5000, keepUses: Int = 200, mergeDist: Double = 0.0): Pair<Int, Int> {
        var a = 0; var m = 0
        for (p in parts) {
            val (x, y) = p.housekeeping(retireAfter, keepUses, mergeDist); a += x; m += y
        }
        return a to m
    }

    companion object {
        private const val serialVersionUID = 1L
    }
}

/**
 * The ways the body offers to act, and their details (hands.py DETAILS). The first five are those of the toy world;
 * the phone adds a sixth, its vibration motor (a short or a long buzz, in milliseconds).
 */
object Kinds {
    val NAMES = arrayOf("brightness", "tone_soft", "tone_loud", "paint", "note", "vibrate")
    val DETAILS = arrayOf(doubleArrayOf(0.0, 0.5, 1.0), doubleArrayOf(300.0, 900.0), doubleArrayOf(300.0, 900.0),
        doubleArrayOf(0.0, 1.0, 2.0), doubleArrayOf(0.0), doubleArrayOf(150.0, 600.0))
    const val BRIGHTNESS = 0; const val TONE_SOFT = 1; const val TONE_LOUD = 2; const val PAINT = 3; const val NOTE = 4
    const val VIBRATE = 5
    /** The toy world's hands (a mind made for a golden replay of Python has these five). */
    const val ROOM = 5

    fun index(name: String) = NAMES.indexOf(name)

    /** The detail of a kind nearest to an option (a guard's limit names an option; the hands work by detail). */
    fun nearest(kind: Int, option: Double): Int {
        val d = DETAILS[kind]
        var best = 0
        for (i in d.indices) if (abs(d[i] - option) < abs(d[best] - option)) best = i
        return best
    }
}

/** Where intentions come from: chance, weighted by expectation. Replaceable, so tests can replay a Python life. */
interface Chooser : Serializable {
    fun kind(p: DoubleArray): Int
    fun detail(n: Int): Int
}

class RandomChooser(seed: Long) : Chooser {
    private val r = java.util.Random(seed + 30_000)
    override fun kind(p: DoubleArray): Int {
        var u = r.nextDouble()
        for (i in p.indices) {
            u -= p[i]; if (u < 0) return i
        }
        return p.size - 1
    }
    override fun detail(n: Int) = r.nextInt(n)
    companion object { private const val serialVersionUID = 1L }
}

data class Request(val kind: Int, val detail: Int) : Serializable {
    val value get() = Kinds.DETAILS[kind][detail]
    val name get() = Kinds.NAMES[kind]
}

/**
 * Wanting (hands.py ActingReaders): when pressure builds, it forms an intention, one of the kinds of action the
 * body offers. Which kind depends on how it feels now: each kind has a small linear expectation over the felt
 * levels, learned by the delta rule from what followed earlier intentions of that kind. It never learns that a
 * guard exists; all it can know is what came after.
 *   learn = "answer": did the world answer (how much the senses changed right after, against usual)?
 *   learn = "read":   did reading improve afterwards?   learn = null: intentions at random.
 */
class ActingReaders(
    sizes: IntArray, nFelt: Int, val learn: String? = "answer", val lr: Double = 0.05, val temp: Double = 0.5,
    val answerAfter: Int = 3, val judgeAfter: Int = 50, val answerBySense: Boolean = false,
    threshold: Double = 20.0, seed: Long = 0, maxWords: IntArray, radius: DoubleArray, mind: Mind = Mind(),
    var chooser: Chooser = RandomChooser(seed), kinds: Int = Kinds.ROOM,
    /** Experiment 29: each intention is felt as an inner state of its own (a trace per hand, 1 when it forms,
     *  fading by [intentionFade] a moment), whether or not the act is carried out. Olvasó is never told that a
     *  guard refused it; it only feels that it wanted, and finds, or does not find, an outer echo to read it by. */
    val feelIntention: Boolean = false, val intentionFade: Double = 0.8,
    /** Experiment 30: a missing answer is felt. When the world answers a hand less than Olvasó expected ([W]),
     *  the shortfall is felt as that hand's surprise (half the shortfall, at most 1), fading by [surpriseFade] a
     *  moment. It does not say why: a guard's refusal and a world that did not answer feel the same. */
    val feelSurprise: Boolean = false, val surpriseFade: Double = 0.8,
) : ManyReaders(sizes, nFelt + kinds * ((if (feelIntention) 1 else 0) + (if (feelSurprise) 1 else 0)),
    threshold, seed, maxWords, radius, false, mind) {
    /** The body's own inner states (the felt intentions, then the surprises, if felt, come after them). */
    val nBody = nFelt
    /** The felt intentions now, one per hand (null: this mind does not feel them). */
    var intent: DoubleArray? = if (feelIntention) DoubleArray(kinds) else null
        private set
    /** The felt surprises now, one per hand (null: this mind does not feel them). */
    var surprise: DoubleArray? = if (feelSurprise) DoubleArray(kinds) else null
        private set
    private val bounds = IntArray(parts.size + 1).also { for (i in parts.indices) it[i + 1] = it[i] + parts[i].ns }
    private val senseMu = DoubleArray(parts.size)
    private val senseM2 = DoubleArray(parts.size)
    val nIn = parts[0].nfIn
    /** Expectations: one row per kind, over the felt levels plus a bias ("how much it expects an answer"). */
    var W = Array(kinds) { DoubleArray(nIn + 1) }
        private set

    private class Pending(val due: Long, val k: Int, val x: DoubleArray, val sBefore: DoubleArray, val readBefore: Double) : Serializable
    private val pending = ArrayList<Pending>()
    private val sHist = ArrayList<DoubleArray>()
    private var changeMu = 0.0
    private var changeM2 = 0.0
    private var changeN = 0
    private val readLog = ArrayList<Double>()
    /** The last signal each kind got (what followed), for the screen. */
    var lastSignal = DoubleArray(kinds)
        private set

    /** How many kinds of action it knows. */
    val kinds get() = W.size

    /** A new hand: a mind saved with fewer kinds wakes up knowing more, expecting nothing yet of the new ones. */
    fun grow(n: Int) {
        if (n <= W.size) return
        W = Array(n) { if (it < W.size) W[it] else DoubleArray(nIn + 1) }
        lastSignal = DoubleArray(n) { if (it < lastSignal.size) lastSignal[it] else 0.0 }
    }

    private fun sensedZ(inputs: List<DoubleArray>): DoubleArray {
        val out = DoubleArray(bounds.last())
        for (i in parts.indices) parts[i].snorm.z(inputs[i]).copyInto(out, bounds[i])
        return out
    }

    private fun perSense(a: DoubleArray) = DoubleArray(parts.size) { Num.mean(a, bounds[it], bounds[it + 1] - bounds[it]) }

    fun expect(x: DoubleArray) = DoubleArray(W.size) { k -> dot(W[k], x) }

    private fun dot(w: DoubleArray, x: DoubleArray): Double {
        var s = 0.0
        for (i in x.indices) s += w[i] * x[i]
        return s + w[x.size]
    }

    /** The body's felt states, and (with feelIntention) the felt intentions after them. */
    fun withIntention(felt: DoubleArray): DoubleArray {
        if (felt.size != nBody) return felt
        val i = if (feelIntention) intent else null
        val s = if (feelSurprise) surprise else null
        if (i == null && s == null) return felt
        val ni = i?.size ?: 0
        return DoubleArray(nBody + ni + (s?.size ?: 0)) {
            when {
                it < nBody -> felt[it]
                it < nBody + ni -> i!![it - nBody]
                else -> s!![it - nBody - ni]
            }
        }
    }

    /** One moment: returns the intention formed now (or null) and the readings. */
    fun live(inputs: List<DoubleArray>, bodyFelt: DoubleArray): Pair<Request?, IntArray> {
        val fading = intent
        if (feelIntention && fading != null) for (k in fading.indices) fading[k] *= intentionFade
        val surprised = surprise
        if (feelSurprise && surprised != null) for (k in surprised.indices) surprised[k] *= surpriseFade
        val felt = withIntention(bodyFelt)
        val readings = read(inputs, felt)
        val sZ = sensedZ(inputs)
        sHist.add(sZ)
        if (sHist.size > answerAfter + 1) {
            sHist.removeAt(0)
            val a = DoubleArray(sZ.size) { abs(sZ[it] - sHist[0][it]) }
            val change = Num.mean(a)
            changeN += 1
            val d = change - changeMu
            changeMu += d / changeN
            changeM2 += d * (change - changeMu)
            val per = perSense(a)
            for (i in per.indices) {
                val ds = per[i] - senseMu[i]
                senseMu[i] += ds / changeN
                senseM2[i] += ds * (per[i] - senseMu[i])
            }
        }
        readLog.add(readings.count { it >= 0 }.toDouble() / readings.size)
        if (readLog.size > 100) readLog.removeAt(0)
        settle(sZ)

        var request: Request? = null
        val x = parts[0].fnorm.z(felt)
        if (feelSurprise) {                // a rare surprise is far from its usual level: bounded, as the senses are
            for (i in nBody until x.size) x[i] = x[i].coerceIn(-3.0, 3.0)    // (and so are the felt intentions)
        }
        if (urge()) {
            val k = if (learn == null) chooser.kind(DoubleArray(W.size) { 1.0 / W.size }) else {
                val v = expect(x).map { it / temp }
                val mx = v.max()
                val p = v.map { exp(it - mx) }
                val s = p.sum()
                chooser.kind(DoubleArray(p.size) { p[it] / s })
            }
            request = Request(k, chooser.detail(Kinds.DETAILS[k].size))
            pressure = 0.0
            val due = if (learn == "answer") answerAfter else judgeAfter
            pending.add(Pending(t + due, k, x.copyOf(), sZ.copyOf(), recentRead()))
            val felt0 = intent
            if (feelIntention && felt0 != null && k < felt0.size) felt0[k] = 1.0     // felt from the next moment on
        }
        t += 1
        return request to readings
    }

    private fun recentRead(): Double {
        val n = minOf(50, readLog.size)
        return Num.mean(DoubleArray(n) { readLog[readLog.size - n + it] })
    }

    /** Learn from intentions whose aftermath has now been seen. */
    private fun settle(sZ: DoubleArray) {
        while (pending.isNotEmpty() && pending[0].due <= t) {
            val p = pending.removeAt(0)
            val a = DoubleArray(sZ.size) { abs(sZ[it] - p.sBefore[it]) }
            val signal = when {
                learn == "answer" && answerBySense -> {
                    val per = perSense(a)
                    var m = Double.NEGATIVE_INFINITY
                    for (i in per.indices) {
                        val sd = sqrt(senseM2[i] / maxOf(changeN - 1, 1)) + 1e-9
                        m = maxOf(m, (per[i] - senseMu[i]) / sd)
                    }
                    m.coerceIn(-2.0, 3.0)
                }
                learn == "answer" -> {
                    val sd = sqrt(changeM2 / maxOf(changeN - 1, 1)) + 1e-9
                    ((Num.mean(a) - changeMu) / sd).coerceIn(-2.0, 3.0)
                }
                learn == "read" -> 10 * (recentRead() - p.readBefore)
                else -> continue
            }
            lastSignal[p.k] = signal
            val expected = dot(W[p.k], p.x)
            val felt = surprise
            if (feelSurprise && felt != null && learn == "answer" && p.k < felt.size) {
                val level = ((expected - signal) / 2.0).coerceIn(0.0, 1.0)    // an expected answer that is missing
                if (level > 0.05) felt[p.k] = maxOf(felt[p.k], level)          // felt from the next moment on
            }
            val e = signal - expected
            val row = W[p.k]
            var step = lr
            if (feelSurprise) {                // with the expectation felt, it must not overshoot: never past the answer
                var xx = 1.0
                for (v in p.x) xx += v * v
                step = minOf(lr, 1.0 / xx)
            }
            for (i in p.x.indices) row[i] += step * e * p.x[i]
            row[p.x.size] += step * e * 1.0
        }
    }

    companion object { private const val serialVersionUID = 1L }
}
