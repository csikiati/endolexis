package com.readingourselves.elemer

import android.content.Context
import com.readingourselves.elemer.body.Ears
import com.readingourselves.elemer.body.Eyes
import com.readingourselves.elemer.body.Felt
import com.readingourselves.elemer.body.Hands
import com.readingourselves.elemer.body.Insides
import com.readingourselves.elemer.body.Level
import com.readingourselves.elemer.body.Skin
import com.readingourselves.elemer.core.ActingReaders
import com.readingourselves.elemer.core.GroupCollector
import com.readingourselves.elemer.core.Guards
import com.readingourselves.elemer.core.Kinds
import com.readingourselves.elemer.core.Mind
import com.readingourselves.elemer.core.Processors
import com.readingourselves.elemer.core.Request
import com.readingourselves.elemer.core.Senses
import java.io.File
import java.io.ObjectInputStream
import java.io.ObjectOutputStream
import java.io.Serializable
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.log10
import kotlin.math.sqrt

/**
 * Everything that makes up one life and survives between sessions: the mind, its secret key, the processors'
 * memory of the usual scene, the body's slow averages, and the observer's notes. Saved to the app's own folder.
 */
class Saved(val seed: Long, val feelIntention: Boolean = false, val feelSurprise: Boolean = false,
            val retry: Boolean = false) : Serializable {
    /** feelIntention (experiment 29): the life feels its own intentions as inner states; feelSurprise (experiment
     *  30): it feels a missing answer; retry (experiment 31): it tries again, and feels "stopped" when the answer
     *  is missing twice. All are chosen when it is born. */
    val mind = ActingReaders(Senses.SIZES, 4, learn = "answer", threshold = 20.0, seed = seed,
        maxWords = MAX_WORDS, radius = DoubleArray(3) { 3.0 * sqrt(Senses.SIZES[it] / 3.0) },
        mind = Mind(), answerBySense = true, kinds = Kinds.NAMES.size, feelIntention = feelIntention,
        feelSurprise = feelSurprise || retry, retry = retry)
    val collector = GroupCollector(Senses.SIZES, 4, seed)
    val processors = Processors()
    val insides = Insides(seed)
    var t = 0L
    var naps = 0
    var born = System.currentTimeMillis()
    var lived = 0L                                         // milliseconds actually lived (awake, app open)
    var executed = IntArray(Kinds.NAMES.size)
    var refused = IntArray(Kinds.NAMES.size)
    // the observer: how often each word came while its own hands were at work (a tone or its window)
    val occ = IntArray(mind.totalWords)
    val own = IntArray(mind.totalWords)

    /** A life saved before the phone had a vibration motor as a hand wakes up with it. */
    fun migrate() {
        val n = Kinds.NAMES.size
        mind.grow(n)
        if (executed.size < n) executed = executed.copyOf(n)
        if (refused.size < n) refused = refused.copyOf(n)
    }

    companion object {
        private const val serialVersionUID = 1L
        val MAX_WORDS = intArrayOf(100, 80, 20)
        /** Restless until this moment (about 43 minutes of life), patient afterwards, as in experiments 12-15. */
        const val CHILDHOOD = 10_000L
        const val NAP_EVERY = 1000L
    }
}

/** What the screen shows of one moment (made by the life thread, drawn by the screen). */
class Snapshot(
    val t: Long, val naps: Int, val livedMs: Long, val felt: Felt, val readings: IntArray, val feltAt: IntArray,
    val pressure: Double, val threshold: Double, val alive: BooleanArray, val wordsNow: IntArray,
    val expects: DoubleArray, val lastSignal: DoubleArray, val executed: IntArray, val refused: IntArray,
    val log: List<String>, val image: DoubleArray, val paint: Int, val toneOn: Boolean, val buzzOn: Boolean, val ownWords: Int,
    val seeing: Boolean, val hearing: Boolean, val asleep: Boolean,
    /** Where the readings "as change" begin (after every felt level), and the felt intentions now (null: not felt). */
    val nIn: Int = 4, val intent: DoubleArray? = null,
    /** The felt surprises now (null: not felt). */
    val surprise: DoubleArray? = null,
    /** The felt "stopped" now (null: it does not try again). */
    val stopped: DoubleArray? = null,
)

class Life(private val ctx: Context, val eyes: Eyes, val skin: Skin, val hands: Hands) {
    private val file = File(ctx.filesDir, "elemer.life")
    private val ears = Ears()
    private val level = Level(ctx)
    private var buzzesHere = 0                              // its buzzes since it was last laid down
    private var wasLying = false
    lateinit var s: Saved
        private set
    @Volatile var snapshot: Snapshot? = null
        private set
    var onMoment: (() -> Unit)? = null
    @Volatile private var running = false
    private var thread: Thread? = null
    private val log = ArrayDeque<String>()
    private val clock = SimpleDateFormat("HH:mm:ss", Locale.ROOT)
    /** The body's guards and duties (units). */
    val laws = Laws(ctx).also { it.load() }
    private val acts = ArrayDeque<Pair<Long, Int>>()        // (moment, kind) of the acts of the last 100 moments

    fun load() {
        s = try {
            ObjectInputStream(file.inputStream().buffered()).use { it.readObject() as Saved }
        } catch (e: Exception) {
            if (file.exists()) file.renameTo(File(ctx.filesDir, "elemer.life.unreadable"))
            Saved(System.nanoTime() and 0xFFFFFF)
        }
        s.migrate()
    }

    @Synchronized fun save() {
        if (!this::s.isInitialized) return
        val tmp = File(ctx.filesDir, "elemer.life.tmp")
        try {
            ObjectOutputStream(tmp.outputStream().buffered()).use { it.writeObject(s) }
            tmp.renameTo(file)
        } catch (_: Exception) {}
    }

    fun start(micAllowed: Boolean) {
        if (running) return
        if (!this::s.isInitialized) load()
        running = true
        ears.start(micAllowed)
        level.start()
        thread = Thread({ loop() }, "elemer-life").also { it.start() }
    }

    fun stop() {
        running = false
        thread?.join(3000)
        thread = null
        ears.stop()
        level.stop()
        save()
    }

    /** Whether the present life feels its own intentions. */
    val feelsIntention: Boolean get() = this::s.isInitialized && s.feelIntention

    /** Whether the present life feels a missing answer. */
    val feelsSurprise: Boolean get() = this::s.isInitialized && (s.feelSurprise || s.retry)

    /** Whether the present life tries again what came to nothing. */
    val triesAgain: Boolean get() = this::s.isInitialized && s.retry

    /** A new life: the old one is kept beside it, renamed, not deleted. feelIntention: it feels its intentions;
     *  feelSurprise: it feels a missing answer; retry: it tries again. */
    fun newLife(feelIntention: Boolean = false, feelSurprise: Boolean = false, retry: Boolean = false) {
        val wasRunning = running
        if (wasRunning) { running = false; thread?.join(3000) }
        if (file.exists()) file.renameTo(File(ctx.filesDir, "elemer.life.${System.currentTimeMillis()}"))
        s = Saved(System.nanoTime() and 0xFFFFFF, feelIntention, feelSurprise, retry)
        synchronized(log) { log.clear() }
        if (wasRunning) { running = true; thread = Thread({ loop() }, "elemer-life").also { it.start() } }
    }

    private fun loop() {
        var last = System.currentTimeMillis()
        while (running) {
            try {
                moment()
            } catch (e: Exception) {
                note("a moment failed: ${e.javaClass.simpleName}")
            }
            val now = System.currentTimeMillis()
            synchronized(this) { s.lived += now - last }
            last = now
        }
    }

    private fun note(line: String) = synchronized(log) {
        log.addFirst("${clock.format(Date())}  $line")
        while (log.size > 8) log.removeLast()
    }

    private fun moment() {
        val sound = ears.read()                             // a quarter of a second: the body's clock
        val image = eyes.latest()
        val touch = skin.take()
        val felt = s.insides.feel(ctx)
        hands.tick()
        val mind = s.mind
        synchronized(this) {
            if (s.t == Saved.CHILDHOOD) mind.threshold = 250.0
            if (s.t > 0 && s.t % Saved.NAP_EVERY == 0L) {
                val (retired, _) = mind.housekeeping(mergeDist = 0.0)    // a nap: retire unused words, never merge
                s.naps++
                if (retired > 0) note("nap ${s.naps}: $retired unused words retired")
            }
            val ends = s.processors(image, sound, touch)
            val (groups, f) = s.collector.anonymise(ends, felt.vector())
            val (req, r) = mind.live(groups, f)
            observe(mind)
            while (acts.isNotEmpty() && acts.first().first <= s.t - 100) acts.removeFirst()
            val guards = laws.guards
            val lying = level.lying()
            if (lying != 1.0 || !wasLying) buzzesHere = 0      // laid down anew (or not lying): the count starts again
            wasLying = lying == 1.0
            val light = if (eyes.seeing) image.average() else null
            val loudness = if (ears.hearing) 10 * log10(sound.sumOf { it * it } / sound.size + 1e-12) else null
            fun signals(hand: String): Map<String, Double?> {
                val k = Kinds.index(hand)
                return laws.sense(felt, s.insides.usualWarmth(), s.insides.usualLoad(), acts.count { it.second == k },
                    hands.atWork, lying, buzzesHere, light, loudness, level.lux())
            }
            // a duty first (a reflex of the body, through the guards; Olvasó does not learn from it)
            laws.duties.act(s.t, guards) { signals(it) }?.let { (hand, option, duty) ->
                val k = Kinds.index(hand)
                if (k >= 0) {
                    val dreq = Request(k, Kinds.nearest(k, (option as? Number)?.toDouble() ?: 0.0))
                    hands.execute(dreq, s.t, readingWords(r))
                    acts.addLast(s.t to k)
                    if (k == Kinds.VIBRATE) buzzesHere++
                    note("${dreq.name} ${detail(dreq)} — $duty (duty)")
                }
            }
            if (req != null) {
                val dec = Guards.decide(guards, req.name, req.value, signals(req.name))
                val done = when (dec.outcome) {
                    "allow" -> req
                    "limit" -> Request(req.kind, Kinds.nearest(req.kind, (dec.option as? Number)?.toDouble() ?: req.value))
                    else -> null
                }
                if (done != null) {
                    s.executed[req.kind]++
                    hands.execute(done, s.t, readingWords(r))
                    acts.addLast(s.t to req.kind)
                    if (req.kind == Kinds.VIBRATE) buzzesHere++
                    if (done != req) { laws.count(dec.guard); note("${req.name} ${detail(req)} — limited to ${detail(done)} (${dec.guard})") }
                    else if (req.kind != Kinds.BRIGHTNESS || s.t % 5 == 0L) note("${req.name} ${detail(req)}")
                } else {
                    s.refused[req.kind]++
                    laws.count(dec.guard)
                    note("${req.name} ${detail(req)} — refused (${dec.guard})")
                }
            }
            s.t++
            snapshot = Snapshot(s.t, s.naps, s.lived, felt, r, IntArray(4) { s.collector.feltIndex(it) },
                mind.pressure, mind.threshold, mind.alive(), mind.wordsNow(), DoubleArray(mind.kinds) { mind.W[it][mind.nIn] },
                mind.lastSignal.copyOf(), s.executed.copyOf(), s.refused.copyOf(), synchronized(log) { log.toList() },
                image, hands.paint, hands.toneLeft > 0, hands.buzzLeft > 0, ownWords(), eyes.seeing, ears.hearing, false,
                mind.parts[0].nfIn, mind.intent?.copyOf(), mind.surprise?.copyOf(), mind.stopped?.copyOf())
            if (s.t % 2400 == 0L) save()
        }
        onMoment?.invoke()
    }

    /** The observer counts, per word, how often it came while its own hands were at work. */
    private fun observe(mind: ActingReaders) {
        val busy = hands.atWork
        for ((i, w) in mind.wordsNow().withIndex()) {
            if (w < 0) continue
            val local = w - mind.offsets[i]
            if (mind.parts[i].wordUses[local] == 1) { s.occ[w] = 0; s.own[w] = 0 }  // a new word in an old place
            s.occ[w]++
            if (busy) s.own[w]++
        }
    }

    /** Words that come mostly while it acts: its own doing, as the observer sees it. */
    private fun ownWords(): Int {
        val alive = s.mind.alive()
        var n = 0
        for (w in s.occ.indices) if (alive[w] && s.occ[w] >= 10 && s.own[w] * 2 > s.occ[w]) n++
        return n
    }

    private fun detail(r: Request) = when (r.kind) {
        Kinds.BRIGHTNESS -> "${(r.value * 100).toInt()}%"
        Kinds.TONE_SOFT, Kinds.TONE_LOUD -> "${r.value.toInt()} Hz"
        Kinds.PAINT -> arrayOf("red", "green", "blue")[r.detail]
        Kinds.VIBRATE -> "${r.value.toInt()} ms"
        else -> ""
    }

    /** Its diary line: the words reading each inner state now (· unread, ~ quiet), in its own numbering. */
    fun readingWords(r: IntArray): String = r.joinToString(" ") { wordName(it) }

    fun wordName(w: Int): String {
        if (w == -1) return "·"
        if (w == -2) return "~"
        val m = s.mind
        val i = (m.offsets.size - 1 downTo 0).first { w >= m.offsets[it] }
        return "${"vht"[i]}${w - m.offsets[i]}"
    }
}
