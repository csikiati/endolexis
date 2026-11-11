package com.readingourselves.elemer.core

import java.io.InputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.abs
import kotlin.math.max

/**
 * Replays a life recorded by tools/make_golden.py through the Kotlin mind and compares, moment by moment, with
 * what the Python mind did. Plain code (no test framework), so it can also be run by hand.
 */
object GoldenReplay {
    class LifeReport(
        val moments: Int, val readingMismatches: Int, val wordMismatches: Int, val requestMismatches: Int,
        val firstMismatch: Int, val maxWError: Double, val requests: Int,
    ) {
        override fun toString() = "moments $moments, requests $requests: readings differ in $readingMismatches, " +
            "words in $wordMismatches, intentions in $requestMismatches (first difference at $firstMismatch), " +
            "largest difference in expectations $maxWError"
    }

    private fun buf(s: InputStream): ByteBuffer = ByteBuffer.wrap(s.readBytes()).order(ByteOrder.LITTLE_ENDIAN)

    /** Python's choices, replayed: the kind and detail it chose at each moment it formed an intention. */
    private class Replay(val kinds: ByteArray, val details: ByteArray) : Chooser {
        var t = 0
        override fun kind(p: DoubleArray) = max(kinds[t].toInt(), 0)
        override fun detail(n: Int) = max(details[t].toInt(), 0)
    }

    /** feel: the recorded Olvasó felt its own intentions (experiment 29); surprise: a missing answer (30);
     *  retry: it tried again, feeling "stopped" (31). */
    fun life(stream: InputStream, feel: Boolean = false, surprise: Boolean = false, retry: Boolean = false): LifeReport {
        val b = buf(stream)
        val T = b.int; val nIn = b.int; val nFelt = b.int; val nRead = b.int
        val inputs = Array(T) { DoubleArray(nIn) { b.float.toDouble() } }
        val felt = Array(T) { DoubleArray(nFelt) { b.float.toDouble() } }
        val readings = Array(T) { IntArray(nRead) { b.short.toInt() } }
        val words = Array(T) { IntArray(3) { b.short.toInt() } }
        val kinds = ByteArray(T) { b.get() }
        val details = ByteArray(T) { b.get() }
        val nW = nFelt + (if (feel) 5 else 0) + (if (surprise) 5 else 0) + (if (retry) 5 else 0) + 1     // over all felt levels
        val W = Array(5) { DoubleArray(nW) { b.double } }

        val sizes = Senses.SIZES
        val radius = DoubleArray(3) { 3.0 * Math.sqrt(sizes[it] / 3.0) }
        val replay = Replay(kinds, details)
        val mind = ActingReaders(sizes, nFelt, learn = "answer", threshold = 20.0, seed = 3,
            maxWords = intArrayOf(100, 80, 20), radius = radius, mind = Mind(), chooser = replay, feelIntention = feel,
            feelSurprise = surprise, retry = retry)
        var rMis = 0; var wMis = 0; var qMis = 0; var first = -1; var requests = 0
        for (t in 0 until T) {
            if (t == 10000) mind.threshold = 250.0
            if (t > 0 && t % 1000 == 0) mind.housekeeping(mergeDist = 0.0)
            replay.t = t
            val groups = listOf(inputs[t].copyOfRange(0, 11), inputs[t].copyOfRange(11, 20), inputs[t].copyOfRange(20, 22))
            val (req, r) = mind.live(groups, felt[t])
            val w = mind.wordsNow()
            var bad = false
            if (!r.contentEquals(readings[t])) { rMis++; bad = true }
            if (!w.contentEquals(words[t])) { wMis++; bad = true }
            if ((req != null) != (kinds[t] >= 0)) { qMis++; bad = true }
            if (req != null) requests++
            if (bad && first < 0) first = t
        }
        var werr = 0.0
        for (k in 0 until 5) for (i in 0 until nW) werr = max(werr, abs(W[k][i] - mind.W[k][i]))
        return LifeReport(T, rMis, wMis, qMis, first, werr, requests)
    }

    /** Largest relative difference between the Kotlin and Python processors over the recorded frames. */
    fun senses(stream: InputStream): DoubleArray {
        val b = buf(stream)
        val n = b.int
        val vision = Vision(); val hearing = Hearing()
        val worst = DoubleArray(20)
        repeat(n) {
            val img = DoubleArray(16 * 16 * 3) { b.float.toDouble() }
            val snd = DoubleArray(2048) { b.float.toDouble() }
            val pv = DoubleArray(11) { b.double }; val ph = DoubleArray(9) { b.double }
            val kv = vision(img); val kh = hearing(snd)
            for (i in 0 until 11) worst[i] = max(worst[i], abs(kv[i] - pv[i]) / (abs(pv[i]) + 1e-6))
            for (i in 0 until 9) worst[11 + i] = max(worst[11 + i], abs(kh[i] - ph[i]) / (abs(ph[i]) + 1e-6))
        }
        return worst
    }

    @JvmStatic
    fun main(args: Array<String>) {
        val dir = args.getOrElse(0) { "app/src/test/resources" }
        val w = senses(java.io.File("$dir/golden_senses.bin").inputStream())
        println("processors, largest relative difference: " +
            (Senses.VISION + Senses.HEARING).zip(w.toList()).joinToString { "${it.first} %.1e".format(it.second) })
        println(life(java.io.File("$dir/golden_life.bin").inputStream()))
    }
}
