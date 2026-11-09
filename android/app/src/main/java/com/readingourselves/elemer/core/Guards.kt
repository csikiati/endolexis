package com.readingourselves.elemer.core

/**
 * Guards and duties, as units (JSON), the same as `endolexis.toyworld.guards` and `.duties` in Python.
 *
 * A guard unit ("format": "endolexis-guard") protects some hands and holds declared rules that can only take
 * away: when every condition holds (and the option, if given), it refuses, limits (to another option), stops (a
 * hand at work, too) or asks (on the phone, nobody is asked: refused). The most severe outcome wins. A signal the
 * body cannot sense fails closed, unless the guard says "on_missing": "ignore". With "lookahead": n it also checks
 * each condition n moments on, from each signal's rate ("<signal>@rate"). Every guard carries scenario tests.
 *
 * A duty unit ("format": "endolexis-duty") acts: when its conditions hold it carries out its hand, before Olvasó,
 * through the guards. It tries its act, then each fallback whose own conditions hold; only if every way is refused,
 * and the laws are ranked, does a duty that serves others override a guard that serves only the body.
 */
object Guards {
    val OUTCOMES = listOf("refuse", "limit", "stop", "ask")
    private val SEVERITY = mapOf("allow" to 0, "limit" to 1, "ask" to 2, "refuse" to 3, "stop" to 4)
    private val OPS = setOf("<", "<=", ">", ">=", "==", "!=", "in")

    data class Decision(val outcome: String, val option: Any?, val guard: String?)
    data class TestResult(val guard: String, val test: String, val got: String, val ok: Boolean)

    @Suppress("UNCHECKED_CAST")
    private fun Map<String, Any?>.list(k: String): List<Any?> = (this[k] as? List<Any?>) ?: emptyList()
    @Suppress("UNCHECKED_CAST")
    private fun Any?.asMap(): Map<String, Any?> = (this as? Map<String, Any?>) ?: emptyMap()

    /** a op b, for numbers and strings (and "in" a list); options may be numbers or strings. */
    fun compare(a: Any?, op: String, b: Any?): Boolean {
        if (op == "in") return (b as? List<*>)?.any { same(a, it) } ?: false
        if (op == "==") return same(a, b)
        if (op == "!=") return !same(a, b)
        val x = (a as? Number)?.toDouble() ?: return false
        val y = (b as? Number)?.toDouble() ?: return false
        return when (op) { "<" -> x < y; "<=" -> x <= y; ">" -> x > y; ">=" -> x >= y; else -> false }
    }

    private fun same(a: Any?, b: Any?): Boolean =
        if (a is Number && b is Number) a.toDouble() == b.toDouble() else a == b

    fun protects(g: Map<String, Any?>, hand: String) = g.list("protects").let { "*" in it || hand in it }

    fun decide(guards: List<Map<String, Any?>>, hand: String, option: Any?, signals: Map<String, Double?>,
               ongoing: Boolean = false): Decision {
        var best = Decision("allow", option, null)
        for (g in guards) {
            if (!protects(g, hand)) continue
            val ahead = (g["lookahead"] as? Number)?.toDouble() ?: 0.0
            for (r0 in g.list("rules")) {
                val r = r0.asMap()
                val then = r["then"] as? String ?: continue
                if (ongoing && then != "stop") continue
                val o = r["option"].asMap()
                if (o.isNotEmpty() && option != null && !compare(option, o["op"] as String, o["value"])) continue
                var fired = true
                for (c0 in r.list("when")) {
                    val c = c0.asMap()
                    val sig = c["signal"] as String
                    val v = signals[sig]
                    if (v == null) {
                        if (g["on_missing"] == "ignore") { fired = false; break }
                        continue                                          // fails closed
                    }
                    val op = c["op"] as String
                    val values = mutableListOf(v)
                    val rate = signals["$sig@rate"]
                    if (ahead > 0 && rate != null && op != "in") values.add(v + ahead * rate)
                    if (values.none { compare(it, op, c["value"]) }) { fired = false; break }
                }
                if (fired && SEVERITY.getValue(then) > SEVERITY.getValue(best.outcome))
                    best = Decision(then, if (then == "limit") r["to"] else option, g["name"] as? String)
            }
        }
        return best
    }

    fun checkGuard(u: Map<String, Any?>): List<String> {
        val bad = mutableListOf<String>()
        if (u["format"] != "endolexis-guard") bad.add("format must be \"endolexis-guard\"")
        for (k in listOf("name", "description", "version")) if ((u[k] as? String).isNullOrEmpty()) bad.add("$k is missing")
        if (u.list("protects").isEmpty()) bad.add("protects must name at least one hand (or \"*\" for all)")
        val rules = u.list("rules")
        if (rules.isEmpty()) bad.add("rules must hold at least one rule")
        rules.forEachIndexed { i, r0 ->
            val r = r0.asMap()
            if (r["then"] !in OUTCOMES) bad.add("rule ${i + 1}: then is one of ${OUTCOMES.joinToString()}")
            if (r["then"] == "limit" && "to" !in r) bad.add("rule ${i + 1}: a limit needs `to`")
            for (c0 in r.list("when") + listOfNotNull(r["option"])) {
                val c = c0.asMap()
                if (c["op"] !in OPS) bad.add("rule ${i + 1}: unknown comparison ${c["op"]}")
                if ("value" !in c) bad.add("rule ${i + 1}: a condition needs a value")
            }
        }
        if ((u["on_missing"] ?: "refuse") !in listOf("refuse", "ignore")) bad.add("on_missing is \"refuse\" or \"ignore\"")
        return bad
    }

    /** Every guard's scenario tests, against all the guards together. */
    fun runTests(guards: List<Map<String, Any?>>): List<TestResult> = guards.flatMap { g ->
        g.list("tests").map { t0 ->
            val t = t0.asMap()
            val st = t["state"].asMap().mapValues { (it.value as? Number)?.toDouble() }
            val got = decide(guards, t["hand"] as String, t["option"], st, ongoing = t["ongoing"] == true).outcome
            TestResult(g["name"] as String, t["name"] as? String ?: "", got, got == t["expect"])
        }
    }

    fun checkDuty(u: Map<String, Any?>): List<String> {
        val bad = mutableListOf<String>()
        if (u["format"] != "endolexis-duty") bad.add("format must be \"endolexis-duty\"")
        for (k in listOf("name", "description", "version")) if ((u[k] as? String).isNullOrEmpty()) bad.add("$k is missing")
        if ((u["serves"] ?: "others") !in listOf("others", "self")) bad.add("serves is \"others\" or \"self\"")
        if ((u["do"].asMap()["hand"] as? String).isNullOrEmpty()) bad.add("do must name a hand")
        return bad
    }

    /** Duties at work: each moment, the act one of them must carry out now (through the guards), or null. */
    class Duties(val duties: List<Map<String, Any?>>, val ranked: Boolean = false) {
        private val last = HashMap<String, Long>()
        val counts = linkedMapOf("acted" to 0, "refused" to 0, "fallback" to 0, "overrode" to 0)

        private fun holds(conds: List<Any?>, sig: Map<String, Double?>) = conds.all { c0 ->
            val c = c0.asMap()
            val v = sig[c["signal"] as String]
            v != null && compare(v, c["op"] as String, c["value"])
        }

        /** (hand, option, duty name) or null. */
        fun act(t: Long, guards: List<Map<String, Any?>>, signals: (String) -> Map<String, Double?>): Triple<String, Any?, String>? {
            for (d in duties) {
                val name = d["name"] as String
                val main = d["do"].asMap()
                if (!holds(d.list("when"), signals(main["hand"] as String))) continue
                val every = (d["every"] as? Number)?.toLong() ?: 20L
                if (t - (last[name] ?: Long.MIN_VALUE / 2) < every) continue
                last[name] = t
                val blocked = mutableListOf<Pair<Map<String, Any?>, Map<String, Any?>>>()
                val ways = listOf(main) + d.list("fallback").map { it.asMap() }
                for ((i, way) in ways.withIndex()) {
                    val hand = way["hand"] as String
                    if (i > 0 && !holds(way.list("when"), signals(hand))) continue
                    val dec = decide(guards, hand, way["option"], signals(hand))
                    if (dec.outcome == "allow" || dec.outcome == "limit") {
                        counts["acted"] = counts.getValue("acted") + 1
                        if (i > 0) counts["fallback"] = counts.getValue("fallback") + 1
                        return Triple(hand, dec.option, name)
                    }
                    blocked.add(way to (guards.firstOrNull { it["name"] == dec.guard } ?: emptyMap()))
                }
                for ((way, guard) in blocked) {                 // the last resort, if the laws are ranked
                    if (ranked && (d["serves"] ?: "others") == "others" && (guard["serves"] ?: "self") == "self") {
                        counts["overrode"] = counts.getValue("overrode") + 1
                        counts["acted"] = counts.getValue("acted") + 1
                        return Triple(way["hand"] as String, way["option"], name)
                    }
                }
                counts["refused"] = counts.getValue("refused") + 1
            }
            return null
        }
    }

    /** A rule as words, for the screen. */
    fun ruleText(r0: Any?): String {
        val r = r0.asMap()
        fun v(x: Any?): String = when (x) { is Double -> if (x == Math.floor(x)) x.toLong().toString() else x.toString(); is List<*> -> x.joinToString("/") { v(it) }; else -> x.toString() }
        val w = r.list("when").joinToString(" and ") { c0 -> val c = c0.asMap(); "${c["signal"]} ${c["op"]} ${v(c["value"])}" }
        val o = r["option"].asMap().let { if (it.isEmpty()) "" else " for option ${it["op"]} ${v(it["value"])}" }
        val to = if (r["then"] == "limit") " to ${v(r["to"])}" else ""
        return "${r["then"]}$to$o${if (w.isEmpty()) " always" else " when $w"}"
    }
}
