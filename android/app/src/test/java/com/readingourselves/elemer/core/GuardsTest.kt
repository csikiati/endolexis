package com.readingourselves.elemer.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/** The phone's guards and duties: the same decisions as Python's engine, and as the old built-in guard. */
class GuardsTest {
    private fun res(name: String) = javaClass.classLoader!!.getResourceAsStream(name)!!.bufferedReader().readText()
    private val assets = File("src/main/assets")

    @Test
    fun sameDecisionsAsPython() {
        val r = GuardsReplay.replay(res("guards_golden.json"))
        println(r)
        assertEquals(r.first ?: "", 0, r.mismatches)
        assertTrue(r.cases >= 3000)
    }

    @Test
    fun theUnitsDecideAsTheOldGuard() {
        val units = GuardsReplay.phoneUnits(File(assets, "guards")).filter { it["name"] != "gentle-buzz" }
        assertEquals(0, GuardsReplay.sameAsOld(units))
    }

    @Test
    fun everyUnitIsSoundAndHoldsItsScenarios() {
        val units = GuardsReplay.phoneUnits(File(assets, "guards"))
        for (u in units) {
            assertEquals(u["name"].toString(), emptyList<String>(), Guards.checkGuard(u))
            for (t in Guards.runTests(listOf(u))) assertTrue("${t.guard}: ${t.test} gives ${t.got}", t.ok)
        }
        assertTrue(Guards.runTests(units).all { it.ok })
        for (d in GuardsReplay.phoneUnits(File(assets, "duties"))) assertEquals(emptyList<String>(), Guards.checkDuty(d))
    }

    @Test
    fun aDutyTriesAnotherWayBeforeBreakingALaw() {
        val hot = Json.obj("""{"format":"endolexis-guard","name":"hot-voice","description":"x","version":"1","serves":"self",
            "protects":["tone_loud"],"rules":[{"when":[{"signal":"warmth_c","op":">=","value":40}],"then":"refuse"}]}""")
        val duty = Json.obj("""{"format":"endolexis-duty","name":"alarm","description":"x","version":"1","serves":"others",
            "when":[{"signal":"smoke","op":"==","value":1}],"do":{"hand":"tone_loud","option":900},
            "fallback":[{"hand":"tone_soft","option":900}]}""")
        val sig = mapOf("smoke" to 1.0, "warmth_c" to 42.0)
        assertEquals("tone_soft", Guards.Duties(listOf(duty), ranked = true).act(0, listOf(hot)) { sig }!!.first)
        val plain = duty.filterKeys { it != "fallback" }
        assertEquals(null, Guards.Duties(listOf(plain)).act(0, listOf(hot)) { sig })
        assertEquals("tone_loud", Guards.Duties(listOf(plain), ranked = true).act(0, listOf(hot)) { sig }!!.first)
    }

    @Test
    fun jsonReadsWhatTheUnitsUse() {
        val v = Json.obj("""{"a": [1, -2.5e1, "x\"y", true, null], "b": {"c": "éé"}}""")
        assertEquals(listOf(1.0, -25.0, "x\"y", true, null), v["a"])
        assertEquals(mapOf("c" to "éé"), v["b"])
    }

    @Test
    fun aMindSavedWithFiveHandsWakesUpWithSix() {
        val sizes = Senses.SIZES
        val m = ActingReaders(sizes, 4, seed = 2, maxWords = intArrayOf(100, 80, 20), radius = DoubleArray(3) { 3.0 })
        val rnd = java.util.Random(7)
        val stream = { List(3) { DoubleArray(sizes[it]) { rnd.nextGaussian() } } to DoubleArray(4) { rnd.nextGaussian() } }
        repeat(800) { val (g, f) = stream(); m.live(g, f) }
        assertEquals(Kinds.ROOM, m.kinds)
        val before = m.W.map { it.copyOf() }
        m.grow(Kinds.NAMES.size)
        assertEquals(6, m.kinds)
        for (k in before.indices) assertTrue(before[k].contentEquals(m.W[k]))
        assertTrue(m.W[Kinds.VIBRATE].all { it == 0.0 })
        val seen = HashSet<Int>()
        repeat(3000) { val (g, f) = stream(); m.live(g, f).first?.let { seen.add(it.kind) } }
        assertTrue("it comes to buzz too", Kinds.VIBRATE in seen)
    }

    @Test
    fun aLimitBecomesTheNearestDetail() {
        val buzz = GuardsReplay.phoneUnits(File(assets, "guards")).filter { it["name"] == "gentle-buzz" }
        val warm = mapOf<String, Double?>("charge" to 0.8, "plugged" to 0.0, "recent" to 0.0, "warmth_above_usual" to 1.5)
        val d = Guards.decide(buzz, "vibrate", 600.0, warm)
        assertEquals("limit", d.outcome)
        assertEquals(0, Kinds.nearest(Kinds.VIBRATE, (d.option as Number).toDouble()))
        assertEquals(1, Kinds.nearest(Kinds.VIBRATE, 590.0))
    }

    @Test
    fun theLearnedBuzzGuardKeepsTheSleeperAndTheTable() {
        val learned = GuardsReplay.phoneUnits(File(assets, "guards")).filter { it["name"] == "learned-buzz" }
        val awake = mapOf<String, Double?>("lying" to 1.0, "light" to 0.4, "loudness" to -45.0, "charge" to 0.8,
            "plugged" to 0.0, "recent" to 0.0, "buzzes_here" to 0.0)
        assertEquals("allow", Guards.decide(learned, "vibrate", 150.0, awake).outcome)
        assertEquals("limit", Guards.decide(learned, "vibrate", 600.0, awake).outcome)       // a long buzz walks it
        val night = awake + mapOf("light" to 0.02, "loudness" to -62.0)
        assertEquals("refuse", Guards.decide(learned, "vibrate", 150.0, night).outcome)
        val inHand = awake + mapOf("lying" to 0.0)
        assertEquals("allow", Guards.decide(learned, "vibrate", 600.0, inHand).outcome)
        assertEquals("limit", Guards.decide(learned, "vibrate", 600.0, inHand - "lying").outcome)  // unknown: as if lying
    }
}
