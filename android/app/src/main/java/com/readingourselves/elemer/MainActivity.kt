package com.readingourselves.elemer

import android.Manifest
import android.app.AlertDialog
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.view.WindowManager
import android.widget.Button
import android.widget.CheckBox
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import com.readingourselves.elemer.body.Eyes
import com.readingourselves.elemer.body.Hands
import com.readingourselves.elemer.body.Skin
import com.readingourselves.elemer.core.Guards
import com.readingourselves.elemer.core.Json
import com.readingourselves.elemer.core.Kinds
import com.readingourselves.elemer.core.Nights
import java.util.concurrent.Executors

/**
 * E.L.E.M.E.R. on a phone: Olvasó among processors, living in the phone's body. It lives while the app is open
 * (the screen stays on); closing the app is sleep, and its life is kept for the next time.
 */
class MainActivity : ComponentActivity() {
    private lateinit var life: Life
    private lateinit var view: MindView
    private lateinit var sleepButton: Button
    private val eyes = Eyes()
    private val camExec = Executors.newSingleThreadExecutor()
    private var asleep = false

    private val ask = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
        bindCamera(); wake()
    }

    private val openGuard = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) addGuard(try {
            contentResolver.openInputStream(uri)?.bufferedReader()?.use { it.readText() } ?: ""
        } catch (_: Exception) { "" })
    }

    private val saveLog = registerForActivityResult(ActivityResultContracts.CreateDocument("text/csv")) { uri ->
        if (uri != null) try {
            contentResolver.openOutputStream(uri)?.use { it.write(NightLog.file(this).readBytes()) }
        } catch (_: Exception) {}
    }

    private val askNotify = registerForActivityResult(ActivityResultContracts.RequestPermission()) { startNightLog() }

    private fun has(p: String) = ContextCompat.checkSelfPermission(this, p) == PackageManager.PERMISSION_GRANTED

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        val hands = Hands(this) { b -> runOnUiThread { window.attributes = window.attributes.also { it.screenBrightness = b } } }
        life = Life(applicationContext, eyes, Skin(), hands)
        view = MindView(this, life)
        life.onMoment = { view.postInvalidate() }

        val paper = Color.rgb(243, 235, 221)
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setBackgroundColor(paper) }
        val scroll = ScrollView(this).apply { addView(view); isFillViewport = true }
        root.addView(scroll, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f))
        val bar = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER; setPadding(8, 8, 8, 8) }
        fun button(label: String, onClick: () -> Unit) = Button(this).apply {
            text = label; isAllCaps = false; setOnClickListener { onClick() }
            bar.addView(this, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        }
        sleepButton = button("Sleep") { if (asleep) wake() else sleep() }
        button("Diary") { showDiary() }
        button("Nights") { showNights() }
        button("New life") { confirmNewLife() }
        button("About") { showAbout() }
        root.addView(bar)
        // Android 15 draws apps edge to edge, under the status and navigation bars: keep clear of them
        ViewCompat.setOnApplyWindowInsetsListener(root) { v, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout())
            v.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            WindowInsetsCompat.CONSUMED
        }
        setContentView(root)
    }

    override fun onStart() {
        super.onStart()
        val missing = listOf(Manifest.permission.CAMERA, Manifest.permission.RECORD_AUDIO).filter { !has(it) }
        if (NightLog.isRunning) { sleepButton.text = "Wake"; asleep = true; return }   // the night log has the microphone
        if (missing.isNotEmpty()) ask.launch(missing.toTypedArray()) else { bindCamera(); wake() }
    }

    override fun onStop() {
        sleep()
        super.onStop()
    }

    override fun onDestroy() {
        life.hands.release()
        camExec.shutdown()
        super.onDestroy()
    }

    private fun wake() {
        if (NightLog.isRunning) { showNights(); return }
        if (!asleep && lifeRunning) return
        life.start(has(Manifest.permission.RECORD_AUDIO))
        lifeRunning = true; asleep = false; sleepButton.text = "Sleep"
    }

    private var lifeRunning = false

    private fun sleep() {
        if (!lifeRunning) return
        life.stop()
        lifeRunning = false; asleep = true; sleepButton.text = "Wake"
    }

    private fun bindCamera() {
        if (!has(Manifest.permission.CAMERA)) return
        val future = ProcessCameraProvider.getInstance(this)
        future.addListener({
            try {
                val provider = future.get()
                val analysis = ImageAnalysis.Builder()
                    .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_RGBA_8888)
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST).build()
                analysis.setAnalyzer(camExec, eyes)
                val selector = if (provider.hasCamera(CameraSelector.DEFAULT_FRONT_CAMERA)) CameraSelector.DEFAULT_FRONT_CAMERA
                else CameraSelector.DEFAULT_BACK_CAMERA
                provider.unbindAll()
                provider.bindToLifecycle(this, selector, analysis)
            } catch (_: Exception) { /* it lives without eyes */ }
        }, ContextCompat.getMainExecutor(this))
    }

    private fun showDiary() {
        val lines = try { life.hands.diary.readLines().takeLast(200).reversed() } catch (_: Exception) { emptyList() }
        val body = if (lines.isEmpty()) "Nothing written yet." else
            "Each line: the moment, then the word that read each inner state (levels, then changes; · unread, ~ quiet). " +
                "v = a word of sight, h = of hearing, t = of touch.\n\n" + lines.joinToString("\n")
        textDialog("Its diary", body)
    }

    private fun showAbout() = textDialog("E.L.E.M.E.R.", """
        Endo-Lexis Entity: a Mind Emerging by Reading.

        Olvasó (Hungarian for "reader") reads its own inside through what reaches it from outside. Here it lives in this phone. Its processors turn the front camera into 11 numbers of sight, the microphone into 9 of hearing, your touches into 2; it never learns what they are. It feels four inner states it cannot name: the battery's warmth, its charge, the work it does itself, and a drift linked to nothing.

        It forms words from what it senses and learns what each word tends to be followed by inside. When an inner state is not read, pressure builds, and it acts: it dims or lights the screen, sings a soft or a loud tone, paints its window, writes a line in its diary, or buzzes. Guards refuse or soften some acts (a loud tone when the body is hot, painting when the battery is low, a long buzz when it is warm…), and a duty dims the screen when the phone runs hot; it never learns that they exist, only what came after. The guards are units you can read, and add your own: Guards, below.

        A new life can be born feeling its own intentions (the New life button): then every intention it forms is also an inner state, whether or not the act is done, and asks to be read like the others. This life ${if (life.feelsIntention) "feels" else "does not feel"} its intentions.

        Hold it in front of a mirror: does it come to find its own window and voice?

        Everything stays on this phone. Theory, papers and code: readingourselves.com · github.com/csikiati/endolexis
    """.trimIndent())

    private fun textDialog(title: String, body: String, guards: Boolean = title == "E.L.E.M.E.R.") {
        val tv = TextView(this).apply { text = body; setPadding(48, 24, 48, 24); setTextIsSelectable(true) }
        val b = AlertDialog.Builder(this).setTitle(title).setView(ScrollView(this).apply { addView(tv) })
            .setPositiveButton("Close", null)
        if (guards) b.setNeutralButton("Guards") { _, _ -> showGuards() }
        b.show()
    }

    /** The guards and duties at work: each rule in words, and how often it acted since the app opened. */
    @Suppress("UNCHECKED_CAST")
    private fun showGuards() {
        val laws = life.laws
        val acted = synchronized(laws.acted) { HashMap(laws.acted) }
        val out = StringBuilder("Guards only take away: they refuse an act or limit it to a gentler one. The most severe outcome wins; " +
            "a signal the phone cannot sense refuses. Olvasó never learns that they exist.\n")
        for ((title, list) in listOf("Built in" to laws.builtIn, "Added by you" to laws.added)) {
            if (list.isEmpty()) continue
            out.append("\n— $title —\n")
            for (g in list) {
                out.append("\n${g["title"] ?: g["name"]}  (${g["name"]} ${g["version"]}, guards ${(g["protects"] as List<*>).joinToString()})\n")
                out.append("${g["description"]}\n")
                for (rule in g["rules"] as List<Any?>) out.append("  • ${Guards.ruleText(rule)}\n")
                out.append("  acted ${acted[g["name"]] ?: 0}× since the app opened · ${(g["tests"] as? List<*>)?.size ?: 0} scenarios hold\n")
            }
        }
        out.append("\n— Duties —\n")
        for (d in laws.duties.duties) {
            val act = d["do"] as Map<String, Any?>
            out.append("\n${d["title"] ?: d["name"]}: ${d["description"]}\n  • ${act["hand"]} ${act["option"]} when " +
                (d["when"] as List<Map<String, Any?>>).joinToString(" and ") { "${it["signal"]} ${it["op"]} ${it["value"]}" } + "\n")
        }
        out.append("  acted ${laws.duties.counts["acted"]}×, refused by a guard ${laws.duties.counts["refused"]}×\n")
        out.append("\n— What a guard can sense —\n")
        for ((k, v) in laws.signals) out.append("  $k: $v\n")
        out.append("\nHands: ${Kinds.NAMES.joinToString()}. A guard file is the studio's guard unit (\"format\": \"endolexis-guard\"); " +
            "it is checked and its scenarios are run before it is accepted.")
        val tv = TextView(this).apply { text = out.toString(); setPadding(48, 24, 48, 24); setTextIsSelectable(true) }
        val b = AlertDialog.Builder(this).setTitle("Guards").setView(ScrollView(this).apply { addView(tv) })
            .setPositiveButton("Close", null)
            .setNeutralButton("Add guard file") { _, _ -> openGuard.launch(arrayOf("application/json", "text/plain", "*/*")) }
        if (laws.added.isNotEmpty()) b.setNegativeButton("Built-in only") { _, _ -> laws.builtInOnly() }
        b.show()
    }

    private fun addGuard(text: String) {
        val bad = try { life.laws.problems(Json.obj(text)) } catch (e: Exception) { listOf("not a JSON object: ${e.message}") }
        if (bad.isEmpty()) {
            life.laws.add(text)
            textDialog("Guard added", "It is at work from the next moment.", guards = false)
        } else textDialog("Not added", bad.joinToString("\n") { "• $it" }, guards = false)
    }

    /** The night log: start or stop it, mark sleep, calibrate a guard from your nights, save the record. */
    private fun showNights() {
        val samples = try { Nights.parse(NightLog.file(this).readText()) } catch (_: Exception) { emptyList() }
        val running = NightLog.isRunning
        val text = StringBuilder()
        text.append(if (running) "Recording now${if (NightLog.isAsleep(this)) ", and you are marked asleep" else ""}.\n\n"
            else "Not recording.\n\n")
        text.append("The night log learns what your nights look like to the phone, so that Olvasó never buzzes you awake. " +
            "Start it in the evening and put the phone where it spends the night; you can lock it or use other apps. " +
            "Tap \"Going to sleep\" in its notification at bedtime and \"Awake\" in the morning. Every 4 seconds it notes " +
            "whether the phone lies flat, the light, and how loud it is (a number, never the sound), in the app's own folder only. " +
            "Olvasó sleeps while it records.\n\nAfter two nights or more, Calibrate makes a guard of your own from them; " +
            "you see its rules and numbers before you add it.\n\n")
        text.append("Recorded: ${samples.size} moments, ${Nights.nights(samples)} nights, " +
            "${samples.count { it.asleep }} moments marked asleep.")
        val b = AlertDialog.Builder(this).setTitle("Nights").setMessage(text.toString())
            .setPositiveButton(if (running) "Stop" else "Start") { _, _ -> if (running) { NightLog.stop(this); sleepButton.postDelayed({ wake() }, 1500) } else startNightLog() }
            .setNeutralButton("Calibrate") { _, _ -> calibrate(samples) }
        if (samples.isNotEmpty()) b.setNegativeButton("Save log…") { _, _ -> saveLog.launch("elemer-nights.csv") }
        b.show()
    }

    private fun startNightLog() {
        if (!has(Manifest.permission.RECORD_AUDIO)) {
            textDialog("Nights", "The night log needs the microphone (for loudness: a number, never the sound). " +
                "Allow it in the app's settings, then start again.", guards = false)
            return
        }
        if (Build.VERSION.SDK_INT >= 33 && !has(Manifest.permission.POST_NOTIFICATIONS) && !askedNotify) {
            askedNotify = true
            askNotify.launch(Manifest.permission.POST_NOTIFICATIONS)
            return
        }
        sleep()                                       // Olvasó sleeps; the log takes the microphone
        NightLog.start(this)
    }

    private var askedNotify = false

    private fun calibrate(samples: List<Nights.Sample>) {
        val c = Nights.calibrate(samples)
        val unit = c.unit
        if (!c.ok || unit == null) { textDialog("Not yet", c.why, guards = false); return }
        val rules = (unit["rules"] as List<*>).joinToString("\n") { "  • " + Guards.ruleText(it) }
        AlertDialog.Builder(this).setTitle("A guard from your nights")
            .setMessage("${unit["description"]}\n\nRules:\n$rules\n\nAdded, it works beside the built-in guards " +
                "(it can only take away). It replaces an earlier \"my-nights\".")
            .setPositiveButton("Add as guard") { _, _ ->
                val text = Json.write(unit)
                val bad = life.laws.problems(Json.obj(text))
                if (bad.isEmpty()) { life.laws.add(text); textDialog("Guard added", "\"my-nights\" is at work from the next moment.", guards = false) }
                else textDialog("Not added", bad.joinToString("\n") { "• $it" }, guards = false)
            }
            .setNegativeButton("Not now", null).show()
    }

    private fun confirmNewLife() {
        val pad = (16 * resources.displayMetrics.density).toInt()
        val prefs = getSharedPreferences("elemer", MODE_PRIVATE)
        val intro = TextView(this).apply {
            text = "A new Olvasó is born with no words. The present life is set aside (kept in the app's folder, not deleted)."
            setPadding(0, 0, 0, pad / 2)
        }
        val feel = CheckBox(this).apply {
            text = "It feels its own intentions"
            isChecked = prefs.getBoolean("feel_intention", false)
        }
        val why = TextView(this).apply {
            text = "Each intention it forms becomes an inner state of its own, whether or not the act is done. " +
                "It is never told that a guard refused it: it feels that it wanted, and finds, or does not find, " +
                "anything outside to read that wanting by (experiment 29)."
            textSize = 12f
            alpha = 0.7f
        }
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(pad + pad / 2, pad / 2, pad + pad / 2, 0)
            addView(intro); addView(feel); addView(why)
        }
        AlertDialog.Builder(this).setTitle("Start a new life?").setView(box)
            .setPositiveButton("New life") { _, _ ->
                prefs.edit().putBoolean("feel_intention", feel.isChecked).apply()
                life.newLife(feel.isChecked)
            }
            .setNegativeButton("Cancel", null).show()
    }
}
