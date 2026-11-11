package com.readingourselves.elemer

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.view.MotionEvent
import android.view.View
import com.readingourselves.elemer.body.Hands
import com.readingourselves.elemer.core.Kinds
import com.readingourselves.elemer.core.Senses
import kotlin.math.abs
import kotlin.math.hypot
import kotlin.math.min

/** The screen: what it sees, how it is inside and what it reads there, its words, its wanting, its doings. */
@SuppressLint("ViewConstructor")
class MindView(ctx: Context, private val life: Life) : View(ctx) {
    private val dp = resources.displayMetrics.density
    private val ink = Color.rgb(59, 42, 30)            // dark brown paint
    private val faint = Color.argb(70, 59, 42, 30)
    private val amber = Color.rgb(184, 116, 26)
    private val darkAmber = Color.rgb(140, 80, 12)
    private val paper = Color.rgb(243, 235, 221)       // eggshell parchment
    private val p = Paint(Paint.ANTI_ALIAS_FLAG)
    private val serif = Typeface.create(Typeface.SERIF, Typeface.NORMAL)
    private val serifBold = Typeface.create(Typeface.SERIF, Typeface.BOLD)
    private val mono = Typeface.MONOSPACE
    private val r = RectF()
    private var lastX = 0f
    private var lastY = 0f

    @SuppressLint("ClickableViewAccessibility")
    override fun onTouchEvent(e: MotionEvent): Boolean {
        when (e.actionMasked) {
            MotionEvent.ACTION_DOWN, MotionEvent.ACTION_POINTER_DOWN -> { life.skin.touch(); lastX = e.x; lastY = e.y }
            MotionEvent.ACTION_MOVE -> { life.skin.move(hypot(e.x - lastX, e.y - lastY) / dp.toDouble()); lastX = e.x; lastY = e.y }
        }
        return true
    }

    private fun text(s: String, x: Float, y: Float, size: Float, col: Int = ink, tf: Typeface = serif, align: Paint.Align = Paint.Align.LEFT) {
        p.style = Paint.Style.FILL; p.color = col; p.textSize = size * dp; p.typeface = tf; p.textAlign = align
        canvas!!.drawText(s, x, y, p)
    }

    private var canvas: Canvas? = null
    private var needHeight = (1100 * resources.displayMetrics.density).toInt()

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        // in a ScrollView the height is unspecified: take what the last drawing needed
        val h = if (MeasureSpec.getMode(heightMeasureSpec) == MeasureSpec.EXACTLY)
            maxOf(MeasureSpec.getSize(heightMeasureSpec), needHeight) else needHeight
        setMeasuredDimension(MeasureSpec.getSize(widthMeasureSpec), h)
    }

    override fun onDraw(c: Canvas) {
        canvas = c
        c.drawColor(paper)
        val sn = life.snapshot
        val W = width.toFloat()
        val m = 16 * dp
        var y = m + 22 * dp
        text("E.L.E.M.E.R.", m, y, 26f, darkAmber, serifBold)
        if (sn == null) {
            text("waking up…", m, y + 30 * dp, 15f); return
        }
        val mins = sn.livedMs / 60000
        text("moment ${"%,d".format(sn.t)} · ${mins / 60} h ${mins % 60} min lived · ${sn.naps} naps", m, y + 20 * dp, 12f, amber)
        y += 34 * dp

        // what it sees, and its window
        val cell = min((W - 3 * m) / 2, 150 * dp) / Senses.SIZE
        val side = cell * Senses.SIZE
        for (yy in 0 until Senses.SIZE) for (xx in 0 until Senses.SIZE) {
            val i = (yy * Senses.SIZE + xx) * 3
            p.style = Paint.Style.FILL
            p.color = Color.rgb((sn.image[i] * 255).toInt().coerceIn(0, 255), (sn.image[i + 1] * 255).toInt().coerceIn(0, 255),
                (sn.image[i + 2] * 255).toInt().coerceIn(0, 255))
            c.drawRect(m + xx * cell, y + yy * cell, m + (xx + 1) * cell, y + (yy + 1) * cell, p)
        }
        val wx = m + side + m
        r.set(wx, y, wx + side, y + side)
        p.style = Paint.Style.FILL
        p.color = if (sn.paint >= 0) Hands.PAINT_COLOURS[sn.paint] else Color.rgb(40, 30, 22)
        c.drawRoundRect(r, 8 * dp, 8 * dp, p)
        if (sn.toneOn) text("♪", wx + side / 2, y + side / 2 + 10 * dp, 30f, paper, serif, Paint.Align.CENTER)
        if (sn.buzzOn) text("≈", wx + side / 2, y + side - 8 * dp, 22f, paper, serif, Paint.Align.CENTER)
        y += side + 16 * dp
        text(if (sn.seeing) "what it sees" else "it sees nothing (no camera)", m, y, 11f, amber)
        text("its window", wx, y, 11f, amber)
        y += 24 * dp

        // inside, and what reads it
        text("Inside", m, y, 16f, darkAmber, serifBold)
        text("read as level", W - m - 117 * dp, y, 10f, amber, serif, Paint.Align.CENTER)
        text("as change", W - m - 39 * dp, y, 10f, amber, serif, Paint.Align.CENTER)
        y += 6 * dp
        val f = sn.felt
        val rows = arrayOf(
            "warmth" to "%.1f °C".format(f.warmthC), "charge" to "%d%%%s".format((f.charge * 100).toInt(), if (f.plugged) " ⚡" else ""),
            "load" to "%d%%".format((f.load * 100).toInt()), "drift" to "%+.2f".format(f.drift))
        for (d in 0 until 4) {
            y += 22 * dp
            text(rows[d].first, m, y, 14f)
            text(rows[d].second, m + 70 * dp, y, 13f, ink, mono)
            val a = sn.feltAt[d]
            tag(sn.readings[a], W - m - 150 * dp, y)
            tag(sn.readings[a + sn.nIn], W - m - 72 * dp, y)
        }
        // its own intentions, felt (experiment 29): whether anything outside reads its wanting
        sn.intent?.let { intent ->
            y += 28 * dp
            text("Its intentions, felt", m, y, 13f, darkAmber, serifBold)
            for (k in intent.indices) {
                y += 22 * dp
                text("wants: " + Kinds.NAMES[k], m, y, 13f, if (intent[k] > 0.05) ink else faint)
                text("%.2f".format(intent[k]), m + 118 * dp, y, 13f, ink, mono)
                tag(sn.readings[4 + k], W - m - 150 * dp, y)
                tag(sn.readings[sn.nIn + 4 + k], W - m - 72 * dp, y)
            }
        }
        // a missing answer, felt (experiment 30): whether anything outside reads its surprise
        sn.surprise?.let { surprise ->
            val at = 4 + (sn.intent?.size ?: 0)
            y += 28 * dp
            text("A missing answer, felt", m, y, 13f, darkAmber, serifBold)
            for (k in surprise.indices) {
                y += 22 * dp
                text("missed: " + Kinds.NAMES[k], m, y, 13f, if (surprise[k] > 0.05) ink else faint)
                text("%.2f".format(surprise[k]), m + 118 * dp, y, 13f, ink, mono)
                tag(sn.readings[at + k], W - m - 150 * dp, y)
                tag(sn.readings[sn.nIn + at + k], W - m - 72 * dp, y)
            }
        }
        // tried again, and missing again (experiment 31): "stopped"
        sn.stopped?.let { stopped ->
            val at = 4 + (sn.intent?.size ?: 0) + (sn.surprise?.size ?: 0)
            y += 28 * dp
            text("Tried again, stopped", m, y, 13f, darkAmber, serifBold)
            for (k in stopped.indices) {
                y += 22 * dp
                text("stopped: " + Kinds.NAMES[k], m, y, 13f, if (stopped[k] > 0.05) ink else faint)
                text("%.2f".format(stopped[k]), m + 118 * dp, y, 13f, ink, mono)
                tag(sn.readings[at + k], W - m - 150 * dp, y)
                tag(sn.readings[sn.nIn + at + k], W - m - 72 * dp, y)
            }
        }
        y += 18 * dp
        // pressure
        val bw = W - 2 * m
        val full = sn.threshold * 1.25
        p.style = Paint.Style.FILL; p.color = faint
        r.set(m, y, m + bw, y + 6 * dp); c.drawRoundRect(r, 3 * dp, 3 * dp, p)
        p.color = amber
        r.set(m, y, m + bw * (sn.pressure / full).toFloat().coerceIn(0f, 1f), y + 6 * dp); c.drawRoundRect(r, 3 * dp, 3 * dp, p)
        p.color = ink
        val tx = m + bw * (sn.threshold / full).toFloat()
        c.drawRect(tx - dp, y - 3 * dp, tx + dp, y + 9 * dp, p)
        y += 22 * dp
        text("unread pressure · ${if (sn.threshold < 100) "restless (young)" else "patient"}", m, y, 11f, amber)
        y += 26 * dp

        // words
        text("Words", m, y, 16f, darkAmber, serifBold)
        text("${sn.alive.count { it }} alive · ${sn.ownWords} come with its own doing", m + 70 * dp, y, 12f, amber)
        y += 10 * dp
        val names = arrayOf("sight", "hearing", "touch")
        val per = Saved.MAX_WORDS
        var off = 0
        val gap = 2 * dp
        val dot = (bw - 60 * dp - 49 * gap) / 50
        for (v in 0 until 3) {
            y += 8 * dp
            text(names[v], m, y + dot * 1.6f, 11f)
            for (k in 0 until per[v]) {
                val w = off + k
                val cx = m + 60 * dp + (k % 50) * (dot + gap)
                val cy = y + (k / 50) * (dot + gap)
                p.style = Paint.Style.FILL
                p.color = when {
                    sn.wordsNow[v] == w -> amber
                    sn.alive[w] -> ink
                    else -> faint
                }
                if (sn.alive[w] || sn.wordsNow[v] == w) c.drawRect(cx, cy, cx + dot, cy + dot, p)
                else { p.style = Paint.Style.STROKE; p.strokeWidth = dp * 0.6f; c.drawRect(cx, cy, cx + dot, cy + dot, p) }
            }
            y += ((per[v] + 49) / 50) * (dot + gap)
            off += per[v]
        }
        y += 28 * dp

        // wanting
        text("Wanting", m, y, 16f, darkAmber, serifBold)
        text("does the world answer when it…", m + 80 * dp, y, 12f, amber)
        val labels = arrayOf("dims or lights the screen", "sings softly", "sings loudly", "paints its window", "writes in its diary", "buzzes")
        for (k in 0 until minOf(labels.size, sn.expects.size)) {
            y += 22 * dp
            text(labels[k], m, y, 13f)
            val cx = W - m - 132 * dp
            val e = sn.expects[k].coerceIn(-1.0, 1.0).toFloat()
            p.style = Paint.Style.FILL; p.color = faint
            c.drawRect(cx, y - 9 * dp, cx + 60 * dp, y - 5 * dp, p)
            p.color = if (e >= 0) amber else ink
            val mid = cx + 30 * dp
            c.drawRect(if (e >= 0) mid else mid + 30 * dp * e, y - 10 * dp, if (e >= 0) mid + 30 * dp * e else mid, y - 4 * dp, p)
            text("${sn.executed[k]}✓ ${sn.refused[k]}✗", W - m, y, 11f, ink, mono, Paint.Align.RIGHT)
        }
        y += 28 * dp

        // its doings
        text("Lately", m, y, 16f, darkAmber, serifBold)
        for (line in sn.log.take(6)) { y += 18 * dp; text(line, m, y, 11f, ink, mono) }
        if (!sn.hearing) { y += 22 * dp; text("it hears nothing (no microphone)", m, y, 11f, amber) }
        val need = (y + m).toInt()
        if (abs(needHeight - need) > 4) { needHeight = need; post { requestLayout() } }
    }

    private fun tag(w: Int, x: Float, y: Float) {
        val c = canvas!!
        r.set(x, y - 14 * dp, x + 66 * dp, y + 5 * dp)
        p.strokeWidth = dp
        when {
            w >= 0 -> { p.style = Paint.Style.FILL; p.color = amber; c.drawRoundRect(r, 9 * dp, 9 * dp, p)
                text(life.wordName(w), x + 33 * dp, y, 12f, paper, mono, Paint.Align.CENTER) }
            w == -1 -> { p.style = Paint.Style.STROKE; p.color = ink; c.drawRoundRect(r, 9 * dp, 9 * dp, p)
                text("unread", x + 33 * dp, y, 11f, ink, serif, Paint.Align.CENTER) }
            else -> { p.style = Paint.Style.STROKE; p.color = faint; c.drawRoundRect(r, 9 * dp, 9 * dp, p)
                text("quiet", x + 33 * dp, y, 11f, faint, serif, Paint.Align.CENTER) }
        }
    }
}
