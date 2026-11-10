package com.readingourselves.elemer.body

import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.AudioTrack
import android.media.MediaRecorder
import android.os.BatteryManager
import android.os.Build
import android.os.Process
import android.os.SystemClock
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import com.readingourselves.elemer.core.Kinds
import com.readingourselves.elemer.core.Request
import com.readingourselves.elemer.core.Senses
import java.io.File
import java.io.Serializable
import java.util.concurrent.atomic.AtomicReference
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

/** One moment is one hearing: 2048 samples at 8 kHz, a quarter of a second. */
const val MOMENT_MS = 256L

/**
 * Eyes: the front camera, seen as 16 x 16 colours (the toy world's retina). The camera runs on its own; each
 * moment takes the latest picture. Without a camera (or permission) the eyes see darkness.
 */
class Eyes : ImageAnalysis.Analyzer {
    private val latest = AtomicReference(DoubleArray(Senses.SIZE * Senses.SIZE * 3))
    @Volatile var seeing = false
        private set
    private var lastAt = 0L

    fun latest(): DoubleArray = latest.get()

    override fun analyze(image: ImageProxy) {
        try {
            val now = SystemClock.elapsedRealtime()
            if (now - lastAt < 120) return
            lastAt = now
            val plane = image.planes[0]
            val buf = plane.buffer
            val rs = plane.rowStride; val ps = plane.pixelStride
            val w = image.width; val h = image.height
            val S = Senses.SIZE
            val grid = DoubleArray(S * S * 3)
            val k = 4                                        // 4 x 4 samples per cell
            for (cy in 0 until S) for (cx in 0 until S) {
                var r = 0.0; var g = 0.0; var b = 0.0
                for (sy in 0 until k) for (sx in 0 until k) {
                    val x = ((cx + (sx + 0.5) / k) * w / S).toInt().coerceIn(0, w - 1)
                    val y = ((cy + (sy + 0.5) / k) * h / S).toInt().coerceIn(0, h - 1)
                    val o = y * rs + x * ps
                    r += (buf.get(o).toInt() and 0xFF); g += (buf.get(o + 1).toInt() and 0xFF); b += (buf.get(o + 2).toInt() and 0xFF)
                }
                // turn upright and mirror (a selfie view), so the picture on screen looks like what it faces
                val (ux, uy) = upright(cx, cy, S, image.imageInfo.rotationDegrees)
                val i = (uy * S + (S - 1 - ux)) * 3
                val n = 255.0 * k * k
                grid[i] = r / n; grid[i + 1] = g / n; grid[i + 2] = b / n
            }
            latest.set(grid)
            seeing = true
        } finally {
            image.close()
        }
    }

    private fun upright(x: Int, y: Int, S: Int, rot: Int): Pair<Int, Int> = when (rot) {
        90 -> (S - 1 - y) to x
        180 -> (S - 1 - x) to (S - 1 - y)
        270 -> y to (S - 1 - x)
        else -> x to y
    }
}

/**
 * Level: the accelerometer, for the guards only (not one of Olvasó's senses). Lying = flat (gravity nearly all on
 * the axis through the screen) and still (hardly any change over the last second). Without an accelerometer it
 * knows nothing (null), and a guard that asks fails closed.
 */
class Level(ctx: Context) : SensorEventListener {
    private val sm = ctx.getSystemService(Context.SENSOR_SERVICE) as? SensorManager
    private val sensor = sm?.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
    private val recent = ArrayDeque<Double>()
    @Volatile private var flat = false
    @Volatile private var known = false

    fun start() { sensor?.let { sm?.registerListener(this, it, SensorManager.SENSOR_DELAY_NORMAL) } }
    fun stop() { try { sm?.unregisterListener(this) } catch (_: Exception) {} }

    /** 1 lying flat and still, 0 not, null not known. */
    fun lying(): Double? = if (!known) null else synchronized(recent) {
        val still = recent.size >= 4 && recent.max() - recent.min() < 0.3
        if (flat && still) 1.0 else 0.0
    }

    override fun onSensorChanged(e: SensorEvent) {
        val (x, y, z) = Triple(e.values[0].toDouble(), e.values[1].toDouble(), e.values[2].toDouble())
        flat = abs(z) > 9.0 && sqrt(x * x + y * y) < 1.5
        synchronized(recent) {
            recent.addLast(sqrt(x * x + y * y + z * z))
            while (recent.size > 5) recent.removeFirst()       // about a second at the normal rate
        }
        known = true
    }

    override fun onAccuracyChanged(s: Sensor?, accuracy: Int) {}
}

/**
 * Ears: the microphone at 8 kHz. Reading one moment's sound blocks for a quarter of a second: the ears are
 * the body's clock. Without a microphone the moment is silent and time is kept by sleeping.
 */
class Ears {
    private var rec: AudioRecord? = null
    private var decimate = 1
    private var buf = ShortArray(Senses.NSAMP)
    var hearing = false
        private set

    @SuppressLint("MissingPermission")
    fun start(allowed: Boolean) {
        if (!allowed) return
        for ((rate, dec) in listOf(8000 to 1, 16000 to 2)) {
            try {
                val min = AudioRecord.getMinBufferSize(rate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
                if (min <= 0) continue
                val r = AudioRecord(MediaRecorder.AudioSource.MIC, rate, AudioFormat.CHANNEL_IN_MONO,
                    AudioFormat.ENCODING_PCM_16BIT, max(min, Senses.NSAMP * dec * 2 * 4))
                if (r.state != AudioRecord.STATE_INITIALIZED) { r.release(); continue }
                r.startRecording()
                rec = r; decimate = dec; buf = ShortArray(Senses.NSAMP * dec); hearing = true
                return
            } catch (e: Exception) { /* try the next rate */ }
        }
    }

    fun read(): DoubleArray {
        val r = rec
        val out = DoubleArray(Senses.NSAMP)
        if (r == null) {
            SystemClock.sleep(MOMENT_MS)
            return out
        }
        var got = 0
        while (got < buf.size) {
            val n = r.read(buf, got, buf.size - got)
            if (n <= 0) { SystemClock.sleep(MOMENT_MS); return out }
            got += n
        }
        for (i in 0 until Senses.NSAMP) {
            var s = 0.0
            for (j in 0 until decimate) s += buf[i * decimate + j]
            out[i] = s / decimate / 32768.0
        }
        return out
    }

    fun stop() {
        rec?.let { try { it.stop() } catch (_: Exception) {}; it.release() }
        rec = null; hearing = false
    }
}

/** Skin: touches on the screen and how far the finger moved, gathered between moments. */
class Skin {
    private var touches = 0
    private var movement = 0.0
    @Synchronized fun touch() { touches++ }
    @Synchronized fun move(px: Double) { movement += px }
    @Synchronized fun take(): DoubleArray {
        val out = doubleArrayOf(touches.toDouble(), movement / 100.0)
        touches = 0; movement = 0.0
        return out
    }
}

/** What the body is like inside, as the world (not Olvasó) knows it. */
data class Felt(val warmthC: Double, val charge: Double, val load: Double, val drift: Double, val plugged: Boolean) {
    /** The four inner states, in the order of the toy world: warmth, charge, load, drift. */
    fun vector() = doubleArrayOf(warmthC, charge, load, drift)
}

/**
 * Insides: the phone's own inner states. Warmth is the battery's temperature, charge its level, load the work this
 * app's own process does (share of one core), drift a random wandering linked to nothing (the control: it must
 * stay unread). It also holds the guard, the spine: the hand that will not go into the fire.
 */
class Insides(seed: Long) : Serializable {
    private val rng = java.util.Random(seed + 40_000)
    var drift = 0.0
        private set
    private var load = 0.0
    private var slowWarmth = Double.NaN
    private var slowLoad = Double.NaN
    @Transient private var lastCpu = -1L
    @Transient private var lastWall = -1L
    @Transient private var battery: Intent? = null
    @Transient private var batteryAt = 0L
    var last = Felt(30.0, 0.5, 0.0, 0.0, false)
        private set

    fun feel(ctx: Context): Felt {
        val now = SystemClock.elapsedRealtime()
        if (battery == null || now - batteryAt > 2000) {
            battery = ctx.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
            batteryAt = now
        }
        val b = battery
        val temp = (b?.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, 300) ?: 300) / 10.0
        val level = b?.getIntExtra(BatteryManager.EXTRA_LEVEL, 50) ?: 50
        val scale = (b?.getIntExtra(BatteryManager.EXTRA_SCALE, 100) ?: 100).coerceAtLeast(1)
        val plugged = (b?.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0) ?: 0) != 0
        val cpu = Process.getElapsedCpuTime()
        if (lastWall > 0 && now > lastWall) {           // (after loading a saved life the clocks start again)
            val share = (cpu - lastCpu).toDouble() / (now - lastWall)
            load = 0.7 * load + 0.3 * share.coerceIn(0.0, 4.0)
        }
        lastCpu = cpu; lastWall = now
        drift = 0.999 * drift + rng.nextGaussian() * 0.05
        slowWarmth = if (slowWarmth.isNaN()) temp else 0.999 * slowWarmth + 0.001 * temp
        slowLoad = if (slowLoad.isNaN()) load else 0.999 * slowLoad + 0.001 * load
        last = Felt(temp, level.toDouble() / scale, load, drift, plugged)
        return last
    }

    /** Hot: 40 °C or more, or clearly warmer than it usually is. */
    fun hot() = last.warmthC >= 40.0 || last.warmthC >= slowWarmth + 1.5
    fun lowBattery(limit: Double) = !last.plugged && last.charge < limit
    /** Busy: working clearly harder than it usually does. */
    fun busy() = last.load > 1.5 * slowLoad + 0.05

    /** Its usual warmth and load (slow averages), as the guard units see them. */
    fun usualWarmth() = if (slowWarmth.isNaN()) last.warmthC else slowWarmth
    fun usualLoad() = if (slowLoad.isNaN()) last.load else slowLoad

    companion object { private const val serialVersionUID = 1L }
}

/**
 * Hands: what Olvasó can do. Screen brightness, a soft or loud tone from the speaker, its window glowing red,
 * green or blue, a note in its diary (a file in its own sandbox, nowhere else), and a short or long buzz of the
 * vibration motor.
 */
class Hands(private val ctx: Context, private val setBrightness: (Float) -> Unit) {
    @Volatile var paint = -1
        private set
    @Volatile var toneLeft = 0
        private set
    @Volatile var brightness = 0.5
        private set
    @Volatile var buzzLeft = 0
        private set
    private var paintLeft = 0
    private var track: AudioTrack? = null
    private val vibrator: Vibrator? = try {
        if (Build.VERSION.SDK_INT >= 31) (ctx.getSystemService(VibratorManager::class.java))?.defaultVibrator
        else @Suppress("DEPRECATION") (ctx.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator)
    } catch (_: Exception) { null }
    /** Whether this phone has a vibration motor at all. */
    val canBuzz get() = vibrator?.hasVibrator() == true
    val diary = File(ctx.filesDir, "diary.txt")

    fun tick() {
        if (paintLeft > 0 && --paintLeft == 0) paint = -1
        if (toneLeft > 0) toneLeft--
        if (buzzLeft > 0) buzzLeft--
    }

    /** Any of its hands at work now (a tone, its window, a buzz). */
    val atWork get() = toneLeft > 0 || paint >= 0 || buzzLeft > 0

    fun execute(r: Request, moment: Long, readingWords: String) {
        when (r.kind) {
            Kinds.BRIGHTNESS -> { brightness = r.value; setBrightness(max(0.03, r.value).toFloat()) }
            Kinds.TONE_SOFT, Kinds.TONE_LOUD -> tone(r.value, if (r.kind == Kinds.TONE_LOUD) 0.5 else 0.12)
            Kinds.PAINT -> { paint = r.detail; paintLeft = PAINT_MOMENTS }
            Kinds.NOTE -> try {
                diary.appendText("$moment  $readingWords\n")
            } catch (_: Exception) {}
            Kinds.VIBRATE -> buzz(r.value.toLong())
        }
    }

    private fun buzz(ms: Long) {
        try {
            vibrator?.vibrate(VibrationEffect.createOneShot(ms, VibrationEffect.DEFAULT_AMPLITUDE))
            buzzLeft = ((ms + MOMENT_MS - 1) / MOMENT_MS).toInt()
        } catch (_: Exception) {}
    }

    private fun tone(freq: Double, amp: Double) {
        val rate = 22050
        val n = (rate * TONE_MOMENTS * MOMENT_MS / 1000).toInt()
        val fade = rate / 50
        val pcm = ShortArray(n) {
            val env = min(1.0, min(it, n - 1 - it).toDouble() / fade)
            (amp * env * sin(2 * PI * freq * it / rate) * 32767).toInt().toShort()
        }
        try {
            track?.release()
            val t = AudioTrack.Builder()
                .setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build())
                .setAudioFormat(AudioFormat.Builder().setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                    .setSampleRate(rate).setChannelMask(AudioFormat.CHANNEL_OUT_MONO).build())
                .setTransferMode(AudioTrack.MODE_STATIC).setBufferSizeInBytes(n * 2).build()
            t.write(pcm, 0, n)
            t.play()
            track = t
            toneLeft = TONE_MOMENTS
        } catch (_: Exception) {}
    }

    fun release() {
        track?.release(); track = null
        try { vibrator?.cancel() } catch (_: Exception) {}
    }

    companion object {
        const val TONE_MOMENTS = 6       // a tone lasts about a second and a half
        const val PAINT_MOMENTS = 30     // its window glows for about eight seconds
        val PAINT_COLOURS = intArrayOf(0xFFE04030.toInt(), 0xFF40C060.toInt(), 0xFF3070E0.toInt())
    }
}
