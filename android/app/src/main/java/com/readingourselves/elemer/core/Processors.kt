package com.readingourselves.elemer.core

import java.io.Serializable
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.log10
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Processor entities (endolexis/toyworld/processors.py): fixed, clockwork feature extractors between the raw
 * senses and Olvasó. They report perception, never names. Nothing here learns.
 *   vision  (11): brightness, red-green, blue-yellow, contrast, left-right, top-bottom; motion, where the moving
 *                 thing went (dx, dy); horizontal and vertical edges
 *   hearing  (9): loudness; low, mid, high band shares; spectral centroid, flatness, pitch strength; onsets, pulsing
 *   touch    (2): touches, finger movement
 */
object Senses {
    const val SIZE = 16
    const val FS = 8000
    const val NSAMP = 2048
    val VISION = arrayOf("brightness", "red_green", "blue_yellow", "contrast", "left_right", "top_bottom",
        "motion", "motion_dx", "motion_dy", "edges_h", "edges_v")
    val HEARING = arrayOf("loudness", "low", "mid", "high", "centroid", "flatness", "pitch", "onsets", "pulsing")
    val TOUCH = arrayOf("touches", "movement")
    val SIZES = intArrayOf(VISION.size, HEARING.size, TOUCH.size)
}

/** Vision: image is SIZE x SIZE x 3, row-major (row, column, channel), values 0..1. */
class Vision : Serializable {
    private var prev: DoubleArray? = null
    private var background: DoubleArray? = null
    private var prevC: DoubleArray? = null

    operator fun invoke(img: DoubleArray): DoubleArray {
        val S = Senses.SIZE
        val lum = DoubleArray(S * S) { (img[3 * it] + img[3 * it + 1] + img[3 * it + 2]) / 3 }
        var r = 0.0; var g = 0.0; var b = 0.0
        for (i in 0 until S * S) { r += img[3 * i]; g += img[3 * i + 1]; b += img[3 * i + 2] }
        r /= S * S; g /= S * S; b /= S * S
        val n = S / 2
        var left = 0.0; var right = 0.0; var top = 0.0; var bottom = 0.0
        for (y in 0 until S) for (x in 0 until S) {
            val v = lum[y * S + x]
            if (x < n) left += v else right += v
            if (y < n) top += v else bottom += v
        }
        val half = (S * S / 2).toDouble()
        val v0 = doubleArrayOf(Num.mean(lum), r - g, b - (r + g) / 2, Num.std(lum), left / half - right / half, top / half - bottom / half)
        val p = prev ?: lum.copyOf().also { prev = it; background = lum.copyOf() }
        val bg = background!!
        var motion = 0.0
        for (i in lum.indices) motion += abs(lum[i] - p[i])
        motion /= lum.size
        val fg = DoubleArray(lum.size) { abs(lum[it] - bg[it]) }
        for (i in lum.indices) bg[i] += 0.01 * (lum[i] - bg[i])
        var w = 1e-9; var cx = 0.0; var cy = 0.0
        for (y in 0 until S) for (x in 0 until S) {
            val f = fg[y * S + x]; w += f; cx += f * x; cy += f * y
        }
        val c = doubleArrayOf(cx / w, cy / w)
        val pc = prevC
        val dx = if (pc != null) c[0] - pc[0] else 0.0
        val dy = if (pc != null) c[1] - pc[1] else 0.0
        prevC = c
        prev = lum.copyOf()
        var eh = 0.0; var ev = 0.0
        for (y in 0 until S - 1) for (x in 0 until S) eh += abs(lum[(y + 1) * S + x] - lum[y * S + x])
        for (y in 0 until S) for (x in 0 until S - 1) ev += abs(lum[y * S + x + 1] - lum[y * S + x])
        eh /= (S - 1) * S; ev /= S * (S - 1)
        return v0 + doubleArrayOf(motion, dx, dy, eh, ev)
    }

    companion object { private const val serialVersionUID = 1L }
}

/** Hearing: NSAMP samples at FS Hz, values about -1..1. */
class Hearing(private val sub: Int = 8) : Serializable {
    private val frame = Senses.NSAMP / sub                      // 256
    private val nBins = frame / 2 + 1
    private val freqs = DoubleArray(nBins) { it * Senses.FS.toDouble() / frame }
    private val hann = DoubleArray(frame) { 0.5 - 0.5 * cos(2 * PI * it / (frame - 1)) }
    private val lag0 = Senses.FS / 400                          // 20
    private val lag1 = Senses.FS / 60                           // 133 (exclusive)

    operator fun invoke(s: DoubleArray): DoubleArray {
        val p = DoubleArray(nBins)
        val re = DoubleArray(frame)
        val im = DoubleArray(frame)
        val env = DoubleArray(sub)
        for (f in 0 until sub) {
            var e = 0.0
            for (i in 0 until frame) {
                val x = s[f * frame + i]
                e += x * x
                re[i] = x * hann[i]; im[i] = 0.0
            }
            env[f] = sqrt(e / frame)
            fft(re, im)
            for (k in 0 until nBins) p[k] += re[k] * re[k] + im[k] * im[k]
        }
        for (k in 0 until nBins) p[k] = p[k] / sub + 1e-12
        val total = p.sum()
        var ms = 0.0
        for (x in s) ms += x * x
        val loud = 10 * log10(ms / s.size + 1e-9)
        var low = 0.0; var mid = 0.0; var high = 0.0; var cen = 0.0; var logSum = 0.0
        for (k in 0 until nBins) {
            when {
                freqs[k] < 300 -> low += p[k]
                freqs[k] < 1500 -> mid += p[k]
                else -> high += p[k]
            }
            cen += freqs[k] * p[k]
            logSum += ln(p[k])
        }
        val flat = exp(logSum / nBins) / (total / nBins)
        val m = 1024
        var mean = 0.0
        for (i in 0 until m) mean += s[i]
        mean /= m
        val x = DoubleArray(m) { s[it] - mean }
        var ac0 = 0.0
        for (i in 0 until m) ac0 += x[i] * x[i]
        var best = Double.NEGATIVE_INFINITY
        for (lag in lag0 until lag1) {
            var a = 0.0
            for (i in 0 until m - lag) a += x[i + lag] * x[i]
            if (a > best) best = a
        }
        val pitch = best / (ac0 + 1e-9)
        var onsets = 0.0
        for (i in 1 until sub) if (env[i] > 2.0 * env[i - 1] + 1e-4) onsets += 1
        val pulsing = Num.std(env) / (Num.mean(env) + 1e-9)
        return doubleArrayOf(loud, low / total, mid / total, high / total, cen / total, flat, pitch, onsets, pulsing)
    }

    /** In-place radix-2 complex FFT (length a power of two). */
    private fun fft(re: DoubleArray, im: DoubleArray) {
        val n = re.size
        var j = 0
        for (i in 1 until n) {
            var bit = n shr 1
            while (j and bit != 0) { j = j xor bit; bit = bit shr 1 }
            j = j xor bit
            if (i < j) {
                var t = re[i]; re[i] = re[j]; re[j] = t
                t = im[i]; im[i] = im[j]; im[j] = t
            }
        }
        var len = 2
        while (len <= n) {
            val ang = -2 * PI / len
            val wr = cos(ang); val wi = sin(ang)
            var i = 0
            while (i < n) {
                var cr = 1.0; var ci = 0.0
                for (k in 0 until len / 2) {
                    val a = i + k; val b = a + len / 2
                    val tr = re[b] * cr - im[b] * ci
                    val ti = re[b] * ci + im[b] * cr
                    re[b] = re[a] - tr; im[b] = im[a] - ti
                    re[a] += tr; im[a] += ti
                    val ncr = cr * wr - ci * wi
                    ci = cr * wi + ci * wr; cr = ncr
                }
                i += len
            }
            len = len shl 1
        }
    }

    companion object { private const val serialVersionUID = 1L }
}

/** All processor entities of one body. Returns their end products, processor by processor. */
class Processors : Serializable {
    private val vision = Vision()
    private val hearing = Hearing()
    operator fun invoke(image: DoubleArray, sound: DoubleArray, touch: DoubleArray): List<DoubleArray> =
        listOf(vision(image), hearing(sound), touch.copyOf())

    companion object { private const val serialVersionUID = 1L }
}
