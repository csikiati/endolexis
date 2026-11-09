"""python -m endolexis.studio <command> ...

  check ARCH.json                    is the architecture sound? who sleeps when?
  run ARCH.json [--seeds 1 2] [--days 30] [--out results.json]
                                     live it in the room and report what the observer saw
  stagger ARCH.json                  set the phases so the Olvasós take turns to sleep (rewrites the file)
  units                              the built-in processor units
  templates                          the use-case templates for new processor units
  new-processor TEMPLATE [--name N] [--version V] [-o unit.json] [--stub unit.py]
                                     make a processor unit (and a Python skeleton for it) from a template
  hands                              the built-in hand units (the room's hands)
  hand-templates                     the use-case templates for new hand units
  new-hand TEMPLATE [--name N] [--version V] [-o hand.json] [--stub hand.py]
                                     make a hand unit (and a Python skeleton for it) from a template
"""
import argparse
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from . import (check, from_hand_template, from_template, hand_stub, hand_templates, hands, library, live, load,
               schedule, stagger, stub, templates)


def _live(args):
    arch, seed, days = args
    return live(arch, seed=seed, days=days)


def mean_of(lives):
    keys = [k for k in lives[0] if k != "members"]
    return {k: (round(float(np.mean([l[k] for l in lives if l[k] is not None])), 3)
                if any(l[k] is not None for l in lives) else None) for k in keys}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m endolexis.studio", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("check"); a.add_argument("arch")
    a = sub.add_parser("run"); a.add_argument("arch"); a.add_argument("--seeds", type=int, nargs="+", default=[1])
    a.add_argument("--days", type=int, default=30); a.add_argument("--out")
    a = sub.add_parser("stagger"); a.add_argument("arch")
    sub.add_parser("units")
    sub.add_parser("templates")
    a = sub.add_parser("new-processor"); a.add_argument("template"); a.add_argument("--name")
    a.add_argument("--version", default="1.0.0"); a.add_argument("-o", "--out"); a.add_argument("--stub")
    sub.add_parser("hands")
    sub.add_parser("hand-templates")
    a = sub.add_parser("new-hand"); a.add_argument("template"); a.add_argument("--name")
    a.add_argument("--version", default="1.0.0"); a.add_argument("-o", "--out"); a.add_argument("--stub")
    o = ap.parse_args(argv)

    if o.cmd == "check":
        arch = load(o.arch)
        bad, warn = check(arch)
        for b in bad:
            print("problem:", b)
        for w in warn:
            print("note:", w)
        s = schedule(arch)
        print(f"{len(arch.get('olvasos', []))} Olvasós; on average {s['minds_on']:.2f} not asleep; "
              f"someone awake {1 - s['never_awake']:.0%} of the day; one asleep at most and someone awake "
              f"{s['ideal']:.0%} of the day")
        return 1 if bad else 0
    if o.cmd == "run":
        arch = load(o.arch)
        jobs = [(arch, s, o.days) for s in o.seeds]
        lives = Pool(min(len(jobs), 4)).map(_live, jobs) if len(jobs) > 1 else [_live(jobs[0])]
        res = {"architecture": arch.get("name"), "days": o.days, "seeds": o.seeds, "mean": mean_of(lives), "lives": lives}
        print(json.dumps(res["mean"], indent=2))
        if o.out:
            Path(o.out).write_text(json.dumps(res, indent=2))
        return 0
    if o.cmd == "stagger":
        arch = stagger(load(o.arch))
        Path(o.arch).write_text(json.dumps(arch, indent=2, ensure_ascii=False) + "\n")
        for ol in arch["olvasos"]:
            print(f"{ol.get('name', ol['id'])}: sleeps from {ol.get('phase', 0):.3f} of the day for {ol.get('sleep', 0):.3f}")
        return 0
    if o.cmd == "units":
        for name, u in library().items():
            print(f"{name:18} {u['inputs']:5} in {u['outputs']:3} out  {u['source']['kind']}: {u['description']}")
        return 0
    if o.cmd == "templates":
        for t in templates():
            print(f"{t['name']:20} {t['use_case']:34} {len(t['outputs'])} outputs  ({t['source']['kind'] or 'your own'})")
        return 0
    if o.cmd == "hands":
        for name, u in hands().items():
            opts = ", ".join(str(x.get("label", x["value"])) for x in u["options"])
            print(f"{name:11} {u['target']['kind']:8} {u['description']}  [{opts}]  guard: {u['guard']}")
        return 0
    if o.cmd == "hand-templates":
        for t in hand_templates():
            print(f"{t['name']:12} {t['use_case']:36} {len(t['options'])} options  ({t['target']['kind'] or 'your own'})")
        return 0
    if o.cmd == "new-hand":
        tpl = {t["name"]: t for t in hand_templates()}.get(o.template)
        if tpl is None:
            print("no such template; see: python -m endolexis.studio hand-templates", file=sys.stderr)
            return 1
        unit = from_hand_template(tpl, o.name, o.version)
        if o.stub:
            unit["implementation"] = {"python": f"{Path(o.stub).stem}:act"}
            Path(o.stub).write_text(hand_stub(unit))
        text = json.dumps(unit, indent=2, ensure_ascii=False) + "\n"
        Path(o.out).write_text(text) if o.out else print(text)
        return 0
    if o.cmd == "new-processor":
        tpl = {t["name"]: t for t in templates()}.get(o.template)
        if tpl is None:
            print("no such template; see: python -m endolexis.studio templates", file=sys.stderr)
            return 1
        unit = from_template(tpl, o.name, o.version)
        if o.stub:
            unit["implementation"] = {"python": f"{Path(o.stub).stem}:process"}
            Path(o.stub).write_text(stub(unit))
        text = json.dumps(unit, indent=2, ensure_ascii=False) + "\n"
        Path(o.out).write_text(text) if o.out else print(text)
        return 0


if __name__ == "__main__":
    sys.exit(main())
