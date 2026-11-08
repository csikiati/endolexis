package com.readingourselves.elemer.core

import java.io.Serializable
import kotlin.math.sqrt

/**
 * Small numeric helpers that do sums the way numpy does them (pairwise summation), so that the
 * Kotlin mind reaches the same decisions as the Python one, bit for bit, on the same inputs.
 */
object Num {
    /** numpy's pairwise sum of a[off until off+n]. */
    fun pairwise(a: DoubleArray, off: Int = 0, n: Int = a.size - off): Double {
        if (n < 8) {
            var r = 0.0
            for (i in 0 until n) r += a[off + i]
            return r
        }
        if (n <= 128) {
            val r = DoubleArray(8) { a[off + it] }
            var i = 8
            val end = n - (n % 8)
            while (i < end) {
                for (j in 0 until 8) r[j] += a[off + i + j]
                i += 8
            }
            var res = ((r[0] + r[1]) + (r[2] + r[3])) + ((r[4] + r[5]) + (r[6] + r[7]))
            while (i < n) {
                res += a[off + i]; i++
            }
            return res
        }
        var n2 = n / 2
        n2 -= n2 % 8
        return pairwise(a, off, n2) + pairwise(a, off + n2, n - n2)
    }

    fun mean(a: DoubleArray, off: Int = 0, n: Int = a.size - off): Double = pairwise(a, off, n) / n

    /** Population standard deviation, as numpy's std(). */
    fun std(a: DoubleArray): Double {
        val m = mean(a)
        val d = DoubleArray(a.size) { (a[it] - m) * (a[it] - m) }
        return sqrt(mean(d))
    }
}

/** Running mean and spread of a vector (Welford), and z-scores against them. */
class RunningNorm(n: Int) : Serializable {
    var n = 0
    val mean = DoubleArray(n)
    val m2 = DoubleArray(n)

    fun update(x: DoubleArray) {
        n += 1
        for (i in x.indices) {
            val d = x[i] - mean[i]
            mean[i] += d / n
            m2[i] += d * (x[i] - mean[i])
        }
    }

    fun z(x: DoubleArray): DoubleArray {
        if (n < 2) return DoubleArray(x.size)
        return DoubleArray(x.size) { (x[it] - mean[it]) / (sqrt(m2[it] / (n - 1)) + 1e-9) }
    }

    companion object { private const val serialVersionUID = 1L }
}
