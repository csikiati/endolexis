package com.readingourselves.elemer

import android.Manifest
import android.app.AlertDialog
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.view.WindowManager
import android.widget.Button
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

        It forms words from what it senses and learns what each word tends to be followed by inside. When an inner state is not read, pressure builds, and it acts: it dims or lights the screen, sings a soft or a loud tone, paints its window, or writes a line in its diary. A guard refuses some acts (a loud tone when the body is hot, painting when the battery is low…); it never learns that the guard exists, only what came after.

        Hold it in front of a mirror: does it come to find its own window and voice?

        Everything stays on this phone. Theory, papers and code: readingourselves.com · github.com/csikiati/endolexis
    """.trimIndent())

    private fun textDialog(title: String, body: String) {
        val tv = TextView(this).apply { text = body; setPadding(48, 24, 48, 24); setTextIsSelectable(true) }
        AlertDialog.Builder(this).setTitle(title).setView(ScrollView(this).apply { addView(tv) })
            .setPositiveButton("Close", null).show()
    }

    private fun confirmNewLife() {
        AlertDialog.Builder(this).setTitle("Start a new life?")
            .setMessage("A new Olvasó is born with no words. The present life is set aside (kept in the app's folder, not deleted).")
            .setPositiveButton("New life") { _, _ -> life.newLife() }
            .setNegativeButton("Cancel", null).show()
    }
}
