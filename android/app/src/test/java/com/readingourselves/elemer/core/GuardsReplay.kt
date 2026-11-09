package com.readingourselves.elemer.core

import java.io.File

/**
 * The Kotlin guards against the Python ones: every recorded case of android/tools/make_guard_golden.py must get the
 * same outcome, option and guard; and the phone's own guard units must decide exactly as its old built-in guard did.
 */
object GuardsReplay {
    data class Result(val cases: Int, val mismatches: Int, val first: String?)

    @Suppress("UNCHECKED_CAST")
    fun replay(text: String): Result {
        val g = Json.obj(text)
        val units = (g["units"] as List<Map<String, Any?>>).associateBy { it["name"] as String }
        var bad = 0
        var first: String? = null
        val cases = g["cases"] as List<Map<String, Any?>>
        for (c in cases) {
            val sel = (c["guards"] as List<String>).map { units.getValue(it) }
            val sig = (c["signals"] as Map<String, Any?>).mapValues { (it.value as Number).toDouble() }
            val d = Guards.decide(sel, c["hand"] as String, c["option"], sig, ongoing = c["ongoing"] == true)
            val same = d.outcome == c["outcome"] && d.guard == c["by"] &&
                (d.option == c["to"] || (d.option is Number && c["to"] is Number && (d.option as Number).toDouble() == (c["to"] as Number).toDouble()))
            if (!same) {
                bad++
                if (first == null) first = "$c -> $d"
            }
        }
        return Result(cases.size, bad, first)
    }

    /** The old guard (Insides.guard before the units), from the same signals. */
    fun oldGuard(kind: String, option: Double, warmthC: Double, slowWarmth: Double, charge: Double, plugged: Boolean,
                 load: Double, slowLoad: Double): Boolean {
        val hot = warmthC >= 40.0 || warmthC >= slowWarmth + 1.5
        fun low(limit: Double) = !plugged && charge < limit
        return when (kind) {
            "brightness" -> option >= 1.0 && low(0.25)
            "tone_loud" -> hot
            "paint" -> low(0.35)
            "note" -> load > 1.5 * slowLoad + 0.05
            else -> false
        }
    }

    /** Random phone states: the units must refuse exactly when the old guard did. Returns the disagreements. */
    fun sameAsOld(units: List<Map<String, Any?>>, n: Int = 20000): Int {
        val r = java.util.Random(5)
        var bad = 0
        val kinds = listOf("brightness" to listOf(0.0, 0.5, 1.0), "tone_soft" to listOf(300.0, 900.0),
            "tone_loud" to listOf(300.0, 900.0), "paint" to listOf(0.0, 1.0, 2.0), "note" to listOf(0.0))
        repeat(n) {
            val w = 25 + 20 * r.nextDouble(); val sw = w - 3 + 5 * r.nextDouble()
            val ch = r.nextDouble(); val pl = r.nextBoolean()
            val ld = r.nextDouble(); val sl = r.nextDouble() * 0.6
            val (kind, opts) = kinds[r.nextInt(kinds.size)]
            val o = opts[r.nextInt(opts.size)]
            val sig = mapOf("warmth_c" to w, "warmth_above_usual" to w - sw, "charge" to ch, "plugged" to if (pl) 1.0 else 0.0,
                "load" to ld, "busy" to ld - (1.5 * sl + 0.05), "recent" to 0.0, "active" to 0.0)
            val units = Guards.decide(units, kind, o, sig).outcome != "allow"
            if (units != oldGuard(kind, o, w, sw, ch, pl, ld, sl)) bad++
        }
        return bad
    }

    fun phoneUnits(dir: File) = dir.listFiles { f -> f.name.endsWith(".json") }!!.sortedBy { it.name }.map { Json.obj(it.readText()) }

    @JvmStatic
    fun main(args: Array<String>) {
        println(replay(File(args[0]).readText()))
        val units = phoneUnits(File(args[1]))
        println("disagreements with the old guard: ${sameAsOld(units)}")
        println("checks: " + units.map { Guards.checkGuard(it) })
        println("scenarios: " + Guards.runTests(units).count { !it.ok } + " fail of " + Guards.runTests(units).size)
    }
}
