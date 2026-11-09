package com.readingourselves.elemer.core

/**
 * A small JSON reader (the guard and duty units are JSON), so that the guards stay plain Kotlin, testable without
 * a phone. Objects become Map<String, Any?>, arrays List<Any?>, numbers Double, and true/false/null themselves.
 */
object Json {
    fun parse(text: String): Any? {
        val p = Parser(text)
        val v = p.value()
        p.space()
        require(p.i == text.length) { "unexpected text after the JSON value at ${p.i}" }
        return v
    }

    @Suppress("UNCHECKED_CAST")
    fun obj(text: String): Map<String, Any?> = parse(text) as? Map<String, Any?> ?: error("not a JSON object")

    private class Parser(val s: String) {
        var i = 0

        fun space() { while (i < s.length && s[i].isWhitespace()) i++ }

        fun value(): Any? {
            space()
            require(i < s.length) { "unexpected end of JSON" }
            return when (val c = s[i]) {
                '{' -> obj()
                '[' -> arr()
                '"' -> str()
                't' -> word("true", true)
                'f' -> word("false", false)
                'n' -> word("null", null)
                else -> if (c == '-' || c.isDigit()) num() else error("unexpected '$c' at $i")
            }
        }

        private fun word(w: String, v: Any?): Any? {
            require(s.startsWith(w, i)) { "expected $w at $i" }
            i += w.length
            return v
        }

        private fun obj(): Map<String, Any?> {
            val m = LinkedHashMap<String, Any?>()
            i++
            space()
            if (s[i] == '}') { i++; return m }
            while (true) {
                space()
                val k = str()
                space()
                require(s[i] == ':') { "expected ':' at $i" }
                i++
                m[k] = value()
                space()
                when (s[i]) {
                    ',' -> i++
                    '}' -> { i++; return m }
                    else -> error("expected ',' or '}' at $i")
                }
            }
        }

        private fun arr(): List<Any?> {
            val a = ArrayList<Any?>()
            i++
            space()
            if (s[i] == ']') { i++; return a }
            while (true) {
                a.add(value())
                space()
                when (s[i]) {
                    ',' -> i++
                    ']' -> { i++; return a }
                    else -> error("expected ',' or ']' at $i")
                }
            }
        }

        private fun str(): String {
            require(s[i] == '"') { "expected a string at $i" }
            i++
            val b = StringBuilder()
            while (s[i] != '"') {
                if (s[i] == '\\') {
                    i++
                    when (val e = s[i]) {
                        'n' -> b.append('\n'); 't' -> b.append('\t'); 'r' -> b.append('\r'); 'b' -> b.append('\b')
                        'f' -> b.append('\u000c'); '/' -> b.append('/'); '\\' -> b.append('\\'); '"' -> b.append('"')
                        'u' -> { b.append(s.substring(i + 1, i + 5).toInt(16).toChar()); i += 4 }
                        else -> error("bad escape '\\$e' at $i")
                    }
                } else b.append(s[i])
                i++
            }
            i++
            return b.toString()
        }

        private fun num(): Double {
            val start = i
            if (s[i] == '-') i++
            while (i < s.length && (s[i].isDigit() || s[i] in ".eE+-")) i++
            return s.substring(start, i).toDouble()
        }
    }
}
