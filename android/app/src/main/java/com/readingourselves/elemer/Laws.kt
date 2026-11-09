package com.readingourselves.elemer

import android.content.Context
import com.readingourselves.elemer.body.Felt
import com.readingourselves.elemer.core.Guards
import com.readingourselves.elemer.core.Json
import com.readingourselves.elemer.core.Kinds
import java.io.File
import java.util.Calendar

/**
 * The body's laws, as units (the studio's guard and duty JSON): the built-in ones from the app's assets, and guard
 * files the person adds (kept in the app's own folder). Olvasó never learns that they exist, only what came after.
 */
class Laws(private val ctx: Context) {
    /** What the phone can tell a guard, and what each signal means (for the screen and for checking a new file). */
    val signals = linkedMapOf(
        "warmth_c" to "the battery's warmth, °C",
        "warmth_above_usual" to "how much warmer than usual, °C",
        "charge" to "the battery's charge, 0 to 1",
        "plugged" to "1 while charging, otherwise 0",
        "load" to "the work this app does (share of one core)",
        "busy" to "load beyond 1.5 × the usual load + 0.05 (above 0: busy)",
        "hour" to "the hour of the day, 0 to 23",
        "recent" to "acts of this hand in the last 100 moments (about 25 s)",
        "active" to "1 while any hand is at work (a tone, its window, a buzz)",
    )

    private val userDir = File(ctx.filesDir, "guards")
    var builtIn: List<Map<String, Any?>> = emptyList()
        private set
    var added: List<Map<String, Any?>> = emptyList()
        private set
    var duties: Guards.Duties = Guards.Duties(emptyList())
        private set
    /** All the guards at work now. */
    @Volatile var guards: List<Map<String, Any?>> = emptyList()
        private set
    /** How often each guard refused or limited an act since the app opened. */
    val acted = HashMap<String, Int>()

    fun load() {
        builtIn = assets("guards")
        duties = Guards.Duties(assets("duties"))
        added = (userDir.listFiles { f -> f.name.endsWith(".json") } ?: emptyArray()).sortedBy { it.name }
            .mapNotNull { f -> try { Json.obj(f.readText()).takeIf { problems(it, builtIn).isEmpty() } } catch (_: Exception) { null } }
        guards = builtIn + added
    }

    private fun assets(dir: String) = (ctx.assets.list(dir) ?: emptyArray()).filter { it.endsWith(".json") }.sorted()
        .map { Json.obj(ctx.assets.open("$dir/$it").bufferedReader().use { r -> r.readText() }) }

    /** What is wrong with a guard file (empty: it can be added). Its own scenarios must hold. */
    @Suppress("UNCHECKED_CAST")
    fun problems(u: Map<String, Any?>, others: List<Map<String, Any?>> = builtIn): List<String> {
        val bad = Guards.checkGuard(u).toMutableList()
        if (bad.isNotEmpty()) return bad
        val name = u["name"] as String
        if (others.any { it["name"] == name }) bad.add("a built-in guard is already called \"$name\"")
        for (h in (u["protects"] as List<Any?>)) if (h != "*" && h !in Kinds.NAMES)
            bad.add("this phone has no hand \"$h\" (its hands: ${Kinds.NAMES.joinToString()})")
        if (u["on_missing"] != "ignore") for (r in (u["rules"] as List<Map<String, Any?>>))
            for (c in (r["when"] as? List<Map<String, Any?>> ?: emptyList())) {
                val sig = c["signal"] as? String ?: continue
                if (sig !in signals && !sig.endsWith("@rate"))
                    bad.add("this phone cannot sense \"$sig\": the guard would always refuse")
            }
        for (t in Guards.runTests(listOf(u))) if (!t.ok) bad.add("scenario \"${t.test}\" gives ${t.got}")
        if ((u["tests"] as? List<*>).isNullOrEmpty()) bad.add("tests must hold at least one scenario")
        return bad.distinct()
    }

    /** Add a guard file (after `problems` found nothing). It is kept, and at work from the next moment. */
    fun add(text: String) {
        val u = Json.obj(text)
        userDir.mkdirs()
        val safe = (u["name"] as String).replace(Regex("[^A-Za-z0-9._-]"), "_")
        File(userDir, "$safe.json").writeText(text)
        load()
    }

    /** Back to the built-in guards only (the added files are removed from the app's folder). */
    fun builtInOnly() {
        userDir.listFiles()?.forEach { it.delete() }
        load()
    }

    fun count(guard: String?) {
        if (guard != null) synchronized(acted) { acted[guard] = (acted[guard] ?: 0) + 1 }
    }

    /** The signals for one hand now. */
    fun sense(felt: Felt, usualWarmth: Double, usualLoad: Double, recent: Int, active: Boolean): Map<String, Double?> = mapOf(
        "warmth_c" to felt.warmthC,
        "warmth_above_usual" to felt.warmthC - usualWarmth,
        "charge" to felt.charge,
        "plugged" to if (felt.plugged) 1.0 else 0.0,
        "load" to felt.load,
        "busy" to felt.load - (1.5 * usualLoad + 0.05),
        "hour" to Calendar.getInstance().get(Calendar.HOUR_OF_DAY).toDouble(),
        "recent" to recent.toDouble(),
        "active" to if (active) 1.0 else 0.0,
    )
}
