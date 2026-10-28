"""Command line: python -m endolexis <command>

  list                              the experiments and their named conditions
  run <experiment> [condition] [--runs 12] [--seed0 1] [--set key=value ...]
                                    run a condition over several seeds and print the averages
  check [--runs 2] [--only text]    re-run the first seeds of every published condition and compare, value by value,
                                    with the results reported in the documents (they should be identical)
"""
import argparse
import importlib
import json
import math
import os
import sys
import time

EXPERIMENTS = {
    "caring": ("stage09", "Stages 9-10: answering and caring (pairs)"),
    "room": ("room", "Stages 11-13: many others, attachment, closeness"),
    "asking": ("stage14", "Stage 14: asking"),
    "newcomers": ("stage15", "Stage 15 (and 16-17 rich/wide): newcomers"),
    "richer": ("stage16", "Stages 16-17: richer lives, a richer reader"),
    "pairs": ("pairs", "Stages 18, 19, 21: out of sight, strong meanings, the expanded self"),
    "symbiosis": ("stage20", "Stage 20: symbiosis with a Processor"),
}
HARNESS_OF = {v[0]: k for k, v in EXPERIMENTS.items()}


def _mod(name):
    return importlib.import_module(f"endolexis.stages.{name}")


def _isnum(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _avg(vals):
    vals = [v for v in vals if _isnum(v) and v == v]
    return sum(vals) / len(vals) if vals else float("nan")


def summarize(results):
    out = {}
    for k, v in results[0].items():
        if _isnum(v):
            out[k] = _avg(r[k] for r in results)
        elif isinstance(v, list) and v and all(_isnum(x) for x in v):
            out[k] = [_avg(r[k][i] for r in results) for i in range(len(v))]
    for k in ("lean", "leanShare", "leanSeen", "leanUnseen"):
        if k in out:
            out[k + "PositiveRuns"] = f"{sum(1 for r in results if _isnum(r.get(k)) and r[k] > 0)}/{len(results)}"
    return out


def _parse_val(s):
    for f in (int, float):
        try:
            return f(s)
        except ValueError:
            pass
    return {"true": True, "false": False}.get(s.lower(), s)


def cmd_list(_):
    for key, (mod, title) in EXPERIMENTS.items():
        print(f"{key:10s} {title}")
        conds = getattr(_mod(mod), "CONDITIONS", {})
        for name, opts in conds.items():
            print(f"{'':12s}{name!r:62s} {json.dumps(opts)}")


def cmd_run(a):
    mod_name = EXPERIMENTS[a.experiment][0] if a.experiment in EXPERIMENTS else a.experiment
    mod = _mod(mod_name)
    opts = dict(getattr(mod, "CONDITIONS", {}).get(a.condition, {})) if a.condition else {}
    if a.condition and a.condition not in getattr(mod, "CONDITIONS", {}):
        sys.exit(f"unknown condition {a.condition!r}; see: python -m endolexis list")
    for kv in a.set or []:
        k, v = kv.split("=", 1)
        opts[k] = _parse_val(v)
    t0 = time.time()
    if mod_name == "stage09":
        summary, runs = mod.caring(runs=a.runs, seed0=a.seed0, **opts)
    else:
        runs = []
        for s in range(a.seed0, a.seed0 + a.runs):
            runs.append(mod.run(seed=s, **opts))
            print(f"  seed {s} done ({time.time() - t0:.0f}s)", file=sys.stderr)
        summary = summarize(runs)
    print(json.dumps(dict(experiment=a.experiment, condition=a.condition, options=opts, runs=a.runs, summary=summary),
                     indent=1, default=lambda v: None if (isinstance(v, float) and math.isnan(v)) else str(v)))


def _same(a, b, tol):
    if a is None:
        return b is None or (_isnum(b) and b != b)
    if _isnum(a) and _isnum(b):
        if a != a and b != b:
            return True
        return abs(a - b) <= tol * max(1.0, abs(a))
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same(x, y, tol) for x, y in zip(a, b))
    return a == b


def cmd_check(a):
    ref = json.load(open(os.path.join(os.path.dirname(__file__), "reference", "published.json")))
    items = [(k, v) for k, v in ref.items() if not a.only or a.only.lower() in (k + v["name"]).lower()]
    if a.shard:
        i, n = map(int, a.shard.split("/"))
        items = items[i - 1::n]
    n_ok = n_bad = 0
    t0 = time.time()
    for fn, e in items:
        mod = _mod(e["harness"])
        bad = []
        for i in range(min(a.runs, len(e["runs"]))):
            seed = e["seed0"] + i
            got = mod.run(seed=seed, **e["opts"])
            want = e["runs"][i]
            for k, v in want.items():
                if k in got and not _same(v, got[k], a.tol):
                    bad.append((seed, k, v, got[k]))
        status = "identical" if not bad else f"DIFFERENT in {len(bad)} values"
        n_ok += not bad
        n_bad += bool(bad)
        print(f"{HARNESS_OF[e['harness']]:9s} {e['name'][:48]:48s} seeds {e['seed0']}-{e['seed0'] + min(a.runs, len(e['runs'])) - 1}: {status}  ({time.time() - t0:.0f}s)")
        for b in bad[:3]:
            print("     seed %s %s: published %s, now %s" % b)
    print(f"\n{n_ok} conditions reproduced exactly, {n_bad} differ.")
    return 1 if n_bad else 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m endolexis", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    r = sub.add_parser("run")
    r.add_argument("experiment")
    r.add_argument("condition", nargs="?")
    r.add_argument("--runs", type=int, default=12)
    r.add_argument("--seed0", type=int, default=1)
    r.add_argument("--set", nargs="*", help="override options, e.g. --set T=20000 sham=true")
    c = sub.add_parser("check")
    c.add_argument("--runs", type=int, default=1)
    c.add_argument("--only", default="")
    c.add_argument("--tol", type=float, default=1e-9)
    c.add_argument("--shard", default="", help="i/n: check every n-th condition starting at i (to use several processes)")
    a = p.parse_args(argv)
    return {"list": cmd_list, "run": cmd_run, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
