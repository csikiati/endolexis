"""Build the studio: embed the processor library, the templates, the example architectures and the
results of experiment 16 into the page (studio.html, the source), and write index.html, one
self-contained file to open in a browser.  python studio/build.py [--fragment PATH]"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))
from endolexis.studio import library, templates  # noqa: E402

COLUMNS = [
    dict(key="linked_read", label="States read", pct=True, bar=True, what="moments in which warmth, charge and load are read (mean of the three), from day 5"),
    dict(key="linked_read_night", label="…at night", pct=True, bar=True, what="the same, in the room's night"),
    dict(key="warmth_via_typing_words", label="Warmth, rightly", pct=True, what="warm moments read through a word of typing (the true cause)"),
    dict(key="load_via_music_words", label="Load, rightly", pct=True, what="loaded moments read through a word of music (the true cause)"),
    dict(key="charge_read_last_third", label="Charge read", pct=True, what="charge read, last third of life"),
    dict(key="drift_read", label="Drift read", pct=True, what="the control: drift is linked to nothing, so any reading of it is superstition (lower is better)"),
    dict(key="acts_per_day", label="Acts a day", pct=False, digits=1, what="intentions the body carried out or refused, per day"),
    dict(key="refused", label="Refused", pct=True, what="share of intentions the guard refused"),
    dict(key="answered", label="Answered", pct=True, what="share of intentions the world answered (the senses changed more than usual right after)"),
    dict(key="minds_on", label="Cost", pct=False, digits=2, what="Olvasós not asleep, on average (compute)"),
]


def embed(html, block, value):
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    pat = re.compile(rf'(<script type="application/json" id="{block}">)(.*?)(</script>)', re.S)
    assert pat.search(html), block
    return pat.sub(lambda m: m.group(1) + text + m.group(3), html)


def findings():
    res = ROOT / "experiments" / "toyworld" / "many_minds_results.json"
    txt = HERE / "findings.json"
    if not res.exists() or not txt.exists():
        return None
    r, t = json.loads(res.read_text()), json.loads(txt.read_text(encoding="utf-8"))
    order = t.pop("order", list(r))
    rows = [{"name": k, "mean": r[k]["mean"], "base": k == "one, never sleeps"} for k in order if k in r]
    return {**t, "columns": COLUMNS, "rows": rows}


HEAD = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
        'body{margin:0}img{max-width:100%}</style>\n</head>\n<body>\n')


def main():
    html = (HERE / "studio.html").read_text(encoding="utf-8")
    examples = {}
    for f in sorted((HERE / "examples").glob("*.json")):
        a = json.loads(f.read_text(encoding="utf-8"))
        examples[a["name"]] = a
    order = ["three, take turns", "one, never sleeps", "one, sleeps nights", "two, take turns"]
    examples = {k: examples[k] for k in order if k in examples} | examples
    for block, value in (("data-library", library()), ("data-templates", templates()),
                         ("data-examples", examples), ("data-findings", findings())):
        html = embed(html, block, value)
    p = HERE / "index.html"
    p.write_text(HEAD + html + "\n</body>\n</html>\n", encoding="utf-8")
    print(f"{p}: {len(html) // 1024} kB")
    if "--fragment" in sys.argv:
        Path(sys.argv[sys.argv.index("--fragment") + 1]).write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
