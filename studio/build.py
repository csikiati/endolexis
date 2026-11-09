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
from endolexis.studio import guard_templates, guards, hand_templates, hands, library, templates  # noqa: E402

def embed(html, block, value):
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    pat = re.compile(rf'(<script type="application/json" id="{block}">)(.*?)(</script>)', re.S)
    assert pat.search(html), block
    return pat.sub(lambda m: m.group(1) + text + m.group(3), html)


def findings():
    """Every experiment shown in the studio: its findings (studio/findings/NN.json) with the means of its results."""
    out = []
    for f in sorted((HERE / "findings").glob("*.json")):
        t = json.loads(f.read_text(encoding="utf-8"))
        res = ROOT / "experiments" / "toyworld" / t.pop("results")
        if not res.exists():
            continue
        r = json.loads(res.read_text())
        order = t.pop("order", list(r))
        rows = [{"name": k, "mean": r[k]["mean"], "base": k == t.get("base")} for k in order if k in r]
        out.append({**t, "rows": rows})
    return out


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
                         ("data-hands", hands()), ("data-hand-templates", hand_templates()),
                         ("data-guards", guards()), ("data-guard-templates", guard_templates()),
                         ("data-learned-guards", [json.loads(f.read_text(encoding="utf-8"))
                                                  for f in sorted((HERE / "examples" / "learned").glob("*.json"))]),
                         ("data-examples", examples), ("data-findings", findings())):
        html = embed(html, block, value)
    p = HERE / "index.html"
    p.write_text(HEAD + html + "\n</body>\n</html>\n", encoding="utf-8")
    print(f"{p}: {len(html) // 1024} kB")
    if "--fragment" in sys.argv:
        Path(sys.argv[sys.argv.index("--fragment") + 1]).write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
