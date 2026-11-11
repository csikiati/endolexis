package com.readingourselves.elemer.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.ObjectInputStream
import java.io.ObjectOutputStream

/** The Kotlin mind against the Python one (endolexis 0.3.0), on the same recorded life. */
class GoldenTest {
    private fun res(name: String) = javaClass.classLoader!!.getResourceAsStream(name)!!

    @Test
    fun sameLifeAsPython() {
        val r = GoldenReplay.life(res("golden_life.bin"))
        println(r)
        assertEquals("readings", 0, r.readingMismatches)
        assertEquals("words", 0, r.wordMismatches)
        assertEquals("intentions", 0, r.requestMismatches)
        assertTrue("expectations", r.maxWError < 1e-9)
        assertTrue(r.requests > 100)
    }

    @Test
    fun sameLifeAsPythonWhenItFeelsItsIntentions() {
        val r = GoldenReplay.life(res("golden_life_intention.bin"), feel = true)
        println(r)
        assertEquals("readings", 0, r.readingMismatches)
        assertEquals("words", 0, r.wordMismatches)
        assertEquals("intentions", 0, r.requestMismatches)
        assertTrue("expectations", r.maxWError < 1e-9)
        assertTrue(r.requests > 100)
    }

    @Test
    fun sameProcessorsAsPython() {
        val w = GoldenReplay.senses(res("golden_senses.bin"))
        for (i in w.indices) assertTrue("feature $i differs by ${w[i]}", w[i] < 1e-8)
    }

    @Test
    fun mindSurvivesSavingAndLoading() {
        val sizes = Senses.SIZES
        val m = ActingReaders(sizes, 4, seed = 1, maxWords = intArrayOf(100, 80, 20), radius = DoubleArray(3) { 3.0 })
        val rnd = java.util.Random(5)
        val stream = { List(3) { DoubleArray(sizes[it]) { rnd.nextGaussian() } } to DoubleArray(4) { rnd.nextGaussian() } }
        repeat(500) { val (g, f) = stream(); m.live(g, f) }
        val bytes = ByteArrayOutputStream().also { ObjectOutputStream(it).use { o -> o.writeObject(m) } }.toByteArray()
        val m2 = ObjectInputStream(ByteArrayInputStream(bytes)).readObject() as ActingReaders
        repeat(300) {
            val (g, f) = stream()
            val a = m.live(g.map { it.copyOf() }, f.copyOf()).second
            val b = m2.live(g, f).second
            assertTrue(a.contentEquals(b))
        }
    }
}
