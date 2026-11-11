"""Experiment 29's switch, shared by the guard experiments: Olvasó feels its own intentions.

    python wanting.py --intention        (any of the guard experiments: 13, 17-26)

With --intention, every Olvasó in the run feels each intention it forms as an inner state (`ActingReaders(
feel_intention=True)`), the results go to <experiment>_intention_results.json, and every life also reports what
the observer saw of its mind (`hands.mind_report`). Without it, the experiments run exactly as before, now also
reporting the mind (so that a run without the feeling can be compared).
"""
import os
import sys

ON = "--intention" in sys.argv or os.environ.get("ENDOLEXIS_FEEL_INTENTION") == "1"
if ON:
    os.environ["ENDOLEXIS_FEEL_INTENTION"] = "1"          # the pool's workers see it too
    sys.argv = [a for a in sys.argv if a != "--intention"]
BASELINE = "--mind-baseline" in sys.argv                # a run without the feeling, kept for the comparison
if BASELINE:
    sys.argv = [a for a in sys.argv if a != "--mind-baseline"]


def mind_kw():
    return {"feel_intention": True} if ON else {}


def results_name(name):
    """experiment_results.json, or with --intention experiment_intention_results.json (and --mind-baseline:
    experiment_mind_results.json, the same lives without the feeling, with the mind reported)."""
    return name.replace("_results.json", "_intention_results.json" if ON else
                        ("_mind_results.json" if BASELINE else "_results.json"))


def report(mind, days, childhood=None):
    """The mind's report for a life of `days` days: the first third, the last third (and the whole life)."""
    from endolexis.toyworld.hands import mind_report
    a = days // 3
    return {"early": mind_report(mind, 1, max(2, a)), "late": mind_report(mind, days - a, days),
            "life": mind_report(mind, 1, days)}


_last = {"mind": None}


def track(mind):
    """Called where a life's Olvasó is made: the wrapper below reports on it when the life is over."""
    _last["mind"] = mind
    return mind


def call(fn, *args):
    """fn(*args) (a life), and the report of the Olvasó it made: for Pool.starmap(intention.call, ...)."""
    _last["mind"] = None
    res = fn(*args)
    m = _last["mind"]
    return res, (report(m, max(2, m.t // 1000)) if m is not None else None)


def lives_and_minds(pairs):
    return [r for r, _ in pairs], [m for _, m in pairs]


def mind_mean(ms):
    """The mean of the lives' mind reports, part by part."""
    import numpy as np
    ms = [m for m in ms if m]
    if not ms:
        return None
    return {part: {k: (float(np.mean([m[part][k] for m in ms if m[part][k] is not None]))
                       if any(m[part][k] is not None for m in ms) else None) for k in ms[0][part]} for part in ms[0]}
