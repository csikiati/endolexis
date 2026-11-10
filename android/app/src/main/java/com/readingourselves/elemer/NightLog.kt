package com.readingourselves.elemer

import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import com.readingourselves.elemer.body.Level
import com.readingourselves.elemer.core.Nights
import java.io.File
import java.util.Calendar
import kotlin.math.log10
import kotlin.math.max

/**
 * The night log: records, every 4 seconds, whether the phone lies flat, the ambient light and the loudness (a number,
 * never the sound), and your mark ("going to sleep" / "awake"), into nights.csv in the app's own folder. It runs in
 * the background with a notification, so the phone can be locked or used for anything else. Olvasó does not live
 * while it records. `Nights.calibrate` turns the record into a guard of your own.
 */
class NightLog : Service() {
    private var thread: Thread? = null
    @Volatile private var running = false
    private var wake: PowerManager.WakeLock? = null
    private lateinit var level: Level

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            STOP -> { stopSelf(); return START_NOT_STICKY }
            ASLEEP -> setAsleep(this, true)
            AWAKE -> setAsleep(this, false)
        }
        startForegroundNow()
        if (!running) begin()
        return START_STICKY
    }

    private fun startForegroundNow() {
        val nm = getSystemService(NotificationManager::class.java)
        if (nm.getNotificationChannel(CHANNEL) == null)
            nm.createNotificationChannel(NotificationChannel(CHANNEL, "Night log", NotificationManager.IMPORTANCE_LOW))
        fun action(a: String, code: Int) = PendingIntent.getService(this, code, Intent(this, NightLog::class.java).setAction(a),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val asleep = isAsleep(this)
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        val n = NotificationCompat.Builder(this, CHANNEL)
            .setSmallIcon(R.drawable.ic_elemer)
            .setContentTitle(if (asleep) "Night log: you are asleep" else "Night log: recording")
            .setContentText("Light, loudness (a number, never the sound) and whether the phone lies flat")
            .setOngoing(true).setContentIntent(open)
            .addAction(0, if (asleep) "Awake" else "Going to sleep", action(if (asleep) AWAKE else ASLEEP, 1))
            .addAction(0, "Stop", action(STOP, 2))
            .build()
        ServiceCompat.startForeground(this, ID, n,
            if (Build.VERSION.SDK_INT >= 30) ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE else 0)
    }

    private fun begin() {
        running = true
        isRunning = true
        level = Level(this).also { it.start() }
        wake = (getSystemService(Context.POWER_SERVICE) as PowerManager)
            .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "elemer:nightlog").also { it.acquire(14 * 3600_000L) }
        thread = Thread({ record() }, "elemer-nightlog").also { it.start() }
    }

    @SuppressLint("MissingPermission")
    private fun record() {
        val file = file(this)
        if (!file.exists()) file.writeText(Nights.HEADER + "\n")
        var rec: AudioRecord? = null
        try {
            val min = AudioRecord.getMinBufferSize(8000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
            val r = AudioRecord(MediaRecorder.AudioSource.MIC, 8000, AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT, max(min, 2048 * 2 * 4))
            if (r.state == AudioRecord.STATE_INITIALIZED) { r.startRecording(); rec = r } else r.release()
        } catch (_: Exception) { /* no microphone: loudness unknown */ }
        val buf = ShortArray(2048)
        while (running) {
            var sum = 0.0
            var n = 0
            val start = System.currentTimeMillis()
            while (running && System.currentTimeMillis() - start < 4000) {
                val r = rec
                if (r == null) { Thread.sleep(250); continue }
                val got = r.read(buf, 0, buf.size)
                if (got <= 0) { Thread.sleep(250); continue }
                for (i in 0 until got) { val x = buf[i] / 32768.0; sum += x * x }
                n += got
            }
            if (!running) break
            val c = Calendar.getInstance()
            val hour = c.get(Calendar.HOUR_OF_DAY) + c.get(Calendar.MINUTE) / 60.0 + c.get(Calendar.SECOND) / 3600.0
            val loud = if (n > 0) 10 * log10(sum / n + 1e-12) else null
            val s = Nights.Sample(System.currentTimeMillis(), hour, level.lying(), level.lux(), loud, isAsleep(this))
            try { file.appendText(Nights.line(s) + "\n") } catch (_: Exception) {}
        }
        rec?.let { try { it.stop() } catch (_: Exception) {}; it.release() }
    }

    override fun onDestroy() {
        running = false
        isRunning = false
        thread?.join(5000)
        if (this::level.isInitialized) level.stop()
        wake?.let { if (it.isHeld) it.release() }
        setAsleep(this, false, update = false)
        super.onDestroy()
    }

    companion object {
        private const val CHANNEL = "nightlog"
        private const val ID = 7
        const val ASLEEP = "asleep"
        const val AWAKE = "awake"
        const val STOP = "stop"
        @Volatile var isRunning = false
            private set

        fun file(ctx: Context) = File(ctx.filesDir, "nights.csv")
        private fun prefs(ctx: Context) = ctx.getSharedPreferences("nightlog", Context.MODE_PRIVATE)
        fun isAsleep(ctx: Context) = prefs(ctx).getBoolean("asleep", false)

        /** Your mark: from now on the record says you sleep (or are awake). */
        fun setAsleep(ctx: Context, asleep: Boolean, update: Boolean = true) {
            prefs(ctx).edit().putBoolean("asleep", asleep).apply()
            if (update && isRunning) ctx.startService(Intent(ctx, NightLog::class.java))
        }

        fun start(ctx: Context) {
            ctx.startForegroundService(Intent(ctx, NightLog::class.java))
        }

        fun stop(ctx: Context) {
            isRunning = false
            ctx.stopService(Intent(ctx, NightLog::class.java))
        }
    }
}
