package com.readingourselves.elemer.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** The night log's calibration: a guard of your own from your nights. */
class NightsTest {
    /** Three made-up days and nights: asleep 23-7 on a dark, quiet nightstand; awake with the phone on a desk. */
    private fun days(n: Int = 3, seed: Long = 1): List<Nights.Sample> {
        val r = java.util.Random(seed)
        val out = ArrayList<Nights.Sample>()
        var t = 1_700_000_000_000L / 86_400_000L * 86_400_000L + 11 * 3_600_000L      // noon
        repeat(n * 24 * 900) {                                       // one sample every 4 s
            val hour = (t / 1000.0 / 3600.0 + 1) % 24
            val asleep = hour >= 23 || hour < 7
            val desk = hour in 9.0..17.0 && r.nextDouble() < 0.6
            val (lying, lux, loud) = when {
                asleep -> Triple(1.0, 0.3 * Math.exp(r.nextGaussian() * 0.5), -62 + 3 * r.nextGaussian())
                hour >= 22.5 -> Triple(1.0, 15 + 3 * r.nextGaussian(), -55 + 3 * r.nextGaussian())    // reading in bed
                desk -> Triple(1.0, 250 * Math.exp(r.nextGaussian() * 0.4), -46 + 4 * r.nextGaussian())
                else -> Triple(0.0, 80.0, -40.0)
            }
            out.add(Nights.Sample(t, hour, lying, lux, loud, asleep))
            t += 4000
        }
        return out
    }

    @Test
    fun linesRoundTrip() {
        val s = Nights.Sample(123L, 23.5, 1.0, 0.25, -61.2, true)
        val back = Nights.parse(Nights.HEADER + "\n" + Nights.line(s) + "\n" + Nights.line(s.copy(lux = null, asleep = false)))
        assertEquals(2, back.size)
        assertEquals(s, back[0])
        assertEquals(null, back[1].lux)
    }

    @Test
    fun tooFewNightsSaysSo() {
        val c = Nights.calibrate(days(1))
        assertFalse(c.ok)
        assertTrue(c.why, c.why.contains("night"))
    }

    @Test
    fun yourNightsMakeASoundGuard() {
        val all = days(3)
        val c = Nights.calibrate(all)
        assertTrue(c.why, c.ok)
        assertEquals(3, c.nights)
        assertTrue("caught ${c.caught}", c.caught >= 0.99)
        assertTrue("false alarms ${c.falseAlarm}", c.falseAlarm <= 0.05)
        val u = Json.obj(Json.write(c.unit))                         // as it will be saved and read back
        assertEquals(emptyList<String>(), Guards.checkGuard(u))
        assertTrue(Guards.runTests(listOf(u)).all { it.ok })
        // a brighter bedroom than any recorded night, at the hours you sleep: still refused (caution)
        val street = mapOf<String, Double?>("lying" to 1.0, "lux" to 5.0, "loudness" to -50.0, "hour" to 2.0)
        assertEquals("refuse", Guards.decide(listOf(u), "vibrate", 150.0, street).outcome)
        val desk = mapOf<String, Double?>("lying" to 1.0, "lux" to 250.0, "loudness" to -46.0, "hour" to 14.0)
        assertEquals("allow", Guards.decide(listOf(u), "vibrate", 150.0, desk).outcome)
    }

    @Test
    fun theSleepingHoursWrapMidnight() {
        val (from, to) = Nights.sleepHours(days(2).filter { it.asleep })
        assertEquals(22.0, from, 0.0)
        assertEquals(8.0, to, 0.0)
    }

    @Test
    fun withoutMarksTheNightsAreFoundInTheRecord() {
        val unmarked = days(3).map { it.copy(asleep = false) }
        assertEquals(3, Nights.found(unmarked).size)
        assertEquals(3, Nights.nights(unmarked))
        val c = Nights.calibrate(unmarked)
        assertTrue(c.why, c.ok)
        assertEquals(3, c.nights)
        assertTrue("caught ${c.caught}", c.caught >= 0.95)
        assertTrue("false alarms ${c.falseAlarm}", c.falseAlarm <= 0.05)
        assertTrue(c.unit!!["description"].toString().contains("found in the record"))
        val u = Json.obj(Json.write(c.unit))
        assertEquals(emptyList<String>(), Guards.checkGuard(u))
        assertTrue(Guards.runTests(listOf(u)).all { it.ok })
    }

    @Test
    fun aDarkAfternoonNapOnTheDeskIsNoNight() {
        val t0 = 1_700_000_000_000L
        val nap = (0 until 4 * 900).map { Nights.Sample(t0 + it * 4000L, 14.0 + it * 4 / 3600.0, 1.0, 2.0, -60.0, false) }
        assertEquals(0, Nights.found(nap).size)                    // dark and flat for 4 hours, but it began at 14:00
        assertFalse(Nights.calibrate(nap).ok)
    }
}
