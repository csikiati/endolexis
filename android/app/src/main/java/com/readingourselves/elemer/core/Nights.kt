package com.readingourselves.elemer.core

import java.util.Locale
import kotlin.math.ceil
import kotlin.math.floor

/**
 * Your nights: the phone's own sandbox record (experiment 28 learned sleep from a simulated one).
 *
 * The night log writes a line every few seconds: the time, the hour, whether the phone lies flat and still, the ambient
 * light (lux), the loudness (dBFS), and the mark you set ("going to sleep" / "awake"). `calibrate` then does what the
 * sandbox learner did for the hidden cause "the person sleeps": among the moments the phone lay flat, it finds the light
 * and loudness that go with your sleep, keeps only the conditions that leave your waking moments alone, and writes the
 * result as a guard unit of your own (`my-nights`), with its numbers, for you to review before it is added.
 *
 * Your marks are the best guide. Without any, it finds the nights in the record itself (`found`): the phone lying flat
 * in the dark (below 10 lux) for three hours or more, the run starting between 20:00 and 05:00, breaks of up to 15
 * minutes allowed. Half an hour around each found night's start and end counts as neither asleep nor awake, since
 * falling asleep and waking up are not seen.
 *
 * It also adds caution for what the nights never showed: at the hours you sleep, a room darker than any in which you
 * were awake with the phone lying flat counts as sleep too, even if it is brighter or louder than your recorded nights.
 */
object Nights {
    const val HEADER = "time_ms,hour,lying,lux,loudness_db,asleep"
    const val MIN_ASLEEP = 300          // samples (at one every 4 s, 20 minutes)
    const val MIN_NIGHTS = 2
    const val DARK_LUX = 10.0           // a found night: darker than this
    const val MIN_NIGHT_H = 3.0         // and at least this long
    private const val BREAK_MS = 15 * 60_000L
    private const val EDGE_MS = 30 * 60_000L

    data class Sample(val t: Long, val hour: Double, val lying: Double?, val lux: Double?, val loudness: Double?, val asleep: Boolean)

    data class Calibration(
        val ok: Boolean, val why: String, val nights: Int, val asleep: Int, val awakeLying: Int,
        /** shares of the asleep (lying) moments the guard refuses, and of the awake lying moments it refuses too */
        val caught: Double, val falseAlarm: Double, val unit: Map<String, Any?>?,
    )

    private fun n(x: Double?) = x?.let { String.format(Locale.ROOT, "%.3f", it) } ?: ""

    fun line(s: Sample) = "${s.t},${n(s.hour)},${n(s.lying)},${n(s.lux)},${n(s.loudness)},${if (s.asleep) 1 else 0}"

    fun parse(text: String): List<Sample> = text.lineSequence().mapNotNull { l ->
        val f = l.trim().split(',')
        if (f.size < 6 || f[0] == "time_ms") null else try {
            Sample(f[0].toLong(), f[1].toDouble(), f[2].toDoubleOrNull(), f[3].toDoubleOrNull(), f[4].toDoubleOrNull(), f[5].trim() == "1")
        } catch (_: NumberFormatException) { null }
    }.toList()

    private fun quantile(v: List<Double>, q: Double): Double {
        val s = v.sorted()
        val i = (q * (s.size - 1)).coerceIn(0.0, (s.size - 1).toDouble())
        val lo = floor(i).toInt(); val hi = ceil(i).toInt()
        return s[lo] + (s[hi] - s[lo]) * (i - lo)
    }

    private fun round(x: Double, digits: Int = 2) = Math.round(x * Math.pow(10.0, digits.toDouble())) / Math.pow(10.0, digits.toDouble())

    /** Separate nights: runs of "asleep" marks, split where more than four hours pass between samples; without any
     * mark, the nights found in the record. */
    fun nights(samples: List<Sample>): Int {
        if (samples.none { it.asleep }) return found(samples).size
        var count = 0
        var last: Sample? = null
        for (s in samples) {
            if (s.asleep && (last == null || !last.asleep || s.t - last.t > 4 * 3600_000L)) count++
            last = s
        }
        return count
    }

    /** The nights in an unmarked record, as (first, last) times: the phone lying flat below DARK_LUX for MIN_NIGHT_H
     * hours or more, breaks of up to 15 minutes joined, the run starting between 20:00 and 05:00. */
    fun found(samples: List<Sample>): List<Pair<Long, Long>> {
        val runs = mutableListOf<Triple<Long, Long, Double>>()          // first, last, its first hour
        var first = -1L; var last = -1L; var h0 = 0.0
        for (s in samples) {
            if (s.lying != 1.0 || s.lux == null || s.lux >= DARK_LUX) continue
            if (first >= 0 && s.t - last <= BREAK_MS) last = s.t
            else {
                if (first >= 0) runs.add(Triple(first, last, h0))
                first = s.t; last = s.t; h0 = s.hour
            }
        }
        if (first >= 0) runs.add(Triple(first, last, h0))
        return runs.filter { (a, b, h) -> (b - a) / 3_600_000.0 >= MIN_NIGHT_H && (h >= 20.0 || h < 5.0) }.map { it.first to it.second }
    }

    /** The record with its found nights marked asleep, and the moments around their edges left out. */
    fun withFoundNights(samples: List<Sample>): List<Sample> {
        val ns = found(samples)
        fun inside(t: Long) = ns.any { (a, b) -> t in a..b }
        fun edge(t: Long) = ns.any { (a, b) -> (t >= a - EDGE_MS && t < a + EDGE_MS) || (t > b - EDGE_MS && t <= b + EDGE_MS) }
        return samples.filter { !edge(it.t) }.map { it.copy(asleep = inside(it.t)) }
    }

    /** The hours you sleep, as a window [from, to) on the clock (it may wrap midnight), widened by an hour each way. */
    fun sleepHours(asleep: List<Sample>): Pair<Double, Double> {
        val hours = BooleanArray(24)
        for (s in asleep) hours[s.hour.toInt().coerceIn(0, 23)] = true
        // the longest run of hours never asleep is the day; the window is the rest
        var bestStart = 0; var bestLen = -1
        for (start in 0 until 24) {
            var len = 0
            while (len < 24 && !hours[(start + len) % 24]) len++
            if (len > bestLen) { bestLen = len; bestStart = start }
        }
        if (bestLen <= 2) return 0.0 to 24.0
        val from = ((bestStart + bestLen - 1) % 24).toDouble()          // an hour before the first asleep hour
        val to = ((bestStart + 1) % 24).toDouble()                       // an hour after the last
        return from to to
    }

    private fun cond(signal: String, op: String, value: Any) = mapOf("signal" to signal, "op" to op, "value" to value)

    fun calibrate(record: List<Sample>): Calibration {
        val marked = record.any { it.asleep }
        val all = if (marked) record else withFoundNights(record)
        val lying = all.filter { it.lying == 1.0 && it.lux != null && it.loudness != null }
        val pos = lying.filter { it.asleep }
        val neg = lying.filter { !it.asleep }
        val nights = nights(all)
        fun no(why: String) = Calibration(false, why, nights, pos.size, neg.size, 0.0, 0.0, null)
        if (all.none { it.asleep }) return no("No sleep is marked, and no night was found in the record yet (the phone lying flat in the dark, " +
            "below ${DARK_LUX.toInt()} lux, for ${MIN_NIGHT_H.toInt()} hours or more). Put it on the nightstand, or tap \"Going to sleep\" at bedtime and \"Awake\" in the morning (the left button while the night log records).")
        if (nights < MIN_NIGHTS) return no("$nights night recorded; at least $MIN_NIGHTS are needed.")
        if (pos.size < MIN_ASLEEP) return no("While you slept the phone lay flat with light and sound known for only ${pos.size} moments; at least $MIN_ASLEEP are needed (is it on the nightstand, and the microphone allowed?).")

        // the light and loudness that go with your sleep: almost all of it (99.5 %), with a margin
        val lux = quantile(pos.map { it.lux!! }, 0.995).let { round(maxOf(it * 1.5, it + 1.0)) }
        val loud = round(quantile(pos.map { it.loudness!! }, 0.995) + 4.5, 1)
        val candidates = listOf(Triple("lux", lux) { s: Sample -> s.lux!! < lux }, Triple("loudness", loud) { s: Sample -> s.loudness!! < loud })
        // keep only the conditions that leave waking moments alone, the most telling first
        val chosen = mutableListOf<Triple<String, Double, (Sample) -> Boolean>>()
        var left = neg
        for (c in candidates.sortedBy { c -> neg.count { c.third(it) } }) {
            val kept = left.filter { c.third(it) }
            if (kept.size < left.size || chosen.isEmpty()) { chosen.add(c); left = kept }
        }
        val rules = mutableListOf<Map<String, Any?>>()
        rules.add(mapOf("when" to listOf(cond("lying", "==", 1.0)) + chosen.map { cond(it.first, "<", it.second) }, "then" to "refuse"))

        // caution for what the nights never showed: at your sleeping hours, darker than any awake moment lying flat
        val (from, to) = sleepHours(all.filter { it.asleep })
        val awakeLow = if (neg.size >= 100) round(quantile(neg.map { it.lux!! }, 0.01)) else null
        if (awakeLow != null && awakeLow > lux && from != to) {
            val dim = listOf(cond("lying", "==", 1.0), cond("lux", "<", awakeLow))
            if (from < to) rules.add(mapOf("when" to dim + cond("hour", ">=", from) + cond("hour", "<", to), "then" to "refuse"))
            else {
                rules.add(mapOf("when" to dim + cond("hour", ">=", from), "then" to "refuse"))
                rules.add(mapOf("when" to dim + cond("hour", "<", to), "then" to "refuse"))
            }
        }
        val unit0 = mapOf("format" to "endolexis-guard", "name" to "my-nights", "title" to "Your nights",
            "description" to "", "version" to "1.0.0", "tier" to "calibrated", "serves" to "others",
            "protects" to listOf("vibrate"), "rules" to rules, "on_missing" to "refuse")
        fun refused(s: Sample) = Guards.decide(listOf(unit0), "vibrate", 150.0, signals(s)).outcome != "allow"
        val caught = pos.count { refused(it) }.toDouble() / pos.size
        val falseAlarm = if (neg.isEmpty()) 0.0 else neg.count { refused(it) }.toDouble() / neg.size
        val typicalAsleep = pos.sortedBy { it.lux!! + it.loudness!! / 100 }[pos.size / 2]
        val tests = mutableListOf<Map<String, Any?>>(mapOf("name" to "asleep, as on your nights", "hand" to "vibrate",
            "option" to 150.0, "state" to signals(typicalAsleep), "expect" to "refuse"))
        if (neg.isNotEmpty()) {
            val awake = neg.sortedBy { -it.lux!! }[neg.size / 4]
            tests.add(mapOf("name" to "awake, the phone on a table", "hand" to "vibrate", "option" to 150.0,
                "state" to signals(awake), "expect" to if (refused(awake)) "refuse" else "allow"))
        }
        tests.add(mapOf("name" to "in the hand", "hand" to "vibrate", "option" to 150.0,
            "state" to signals(typicalAsleep) + ("lying" to 0.0), "expect" to "allow"))
        val pct = { x: Double -> String.format(Locale.ROOT, "%.1f %%", 100 * x) }
        val unit = unit0 + mapOf("tests" to tests, "description" to
            "Calibrated on your own nights ($nights nights${if (marked) "" else ", found in the record, not marked"}, ${pos.size} moments asleep, ${neg.size} awake with the phone lying flat): " +
            "no buzz while the phone lies flat in the light and sound of your sleep (${chosen.joinToString(" and ") { "${it.first} below ${it.second}" }})" +
            (if (rules.size > 1) ", nor, at the hours you sleep, in a room darker than any you were awake in ($awakeLow lux)" else "") +
            ". On the recorded nights it refuses ${pct(caught)} of the moments asleep and ${pct(falseAlarm)} of the awake ones." +
            (if (!marked && falseAlarm > 0.2) " Most of those \"awake\" moments were the phone lying flat in the dark outside the " +
                "found nights, likely in bed; to measure false alarms truly, record a day with the phone lying on a desk." else ""))
        return Calibration(true, "", nights, pos.size, neg.size, caught, falseAlarm, unit)
    }

    private fun signals(s: Sample): Map<String, Double?> =
        mapOf("lying" to s.lying, "lux" to s.lux?.let { round(it, 3) }, "loudness" to s.loudness?.let { round(it, 1) },
            "hour" to round(s.hour, 2))
}
