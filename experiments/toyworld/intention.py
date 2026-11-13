"""Experiment 29's switch, shared by the guard experiments: Olvasó feels its own intentions.

    python wanting.py --intention        (any of the guard experiments: 13, 17-26)

With --intention, every Olvasó in the run feels each intention it forms as an inner state (`ActingReaders(
feel_intention=True)`), the results go to <experiment>_intention_results.json, and every life also reports what
the observer saw of its mind (`hands.mind_report`). Without it, the experiments run exactly as before, now also
reporting the mind (so that a run without the feeling can be compared).

Experiment 30 adds --surprise: Olvasó feels a missing answer, an answer it expected from a hand that did not come
(`ActingReaders(feel_surprise=True)`); results in <experiment>_surprise_results.json, or with both switches
<experiment>_both_results.json. --surprise-shuffled is the control (the same surprises on a random hand, 50-500
moments later): <experiment>_shuffled_results.json.

Experiment 31 adds --retry: with the surprise felt, Olvasó tries the same act again at once, and a second missing
answer is felt as "stopped" (`ActingReaders(retry=True)`, implies --surprise); results in
<experiment>_retry_results.json. --retry-untraced is the control (the same retries, nothing felt after them):
<experiment>_untraced_results.json.

Experiment 32 adds --autopilot: a habit learns from Olvasó's answered acts and, once confident in a familiar scene,
acts by itself while Olvasó only reads; an unanswered habit's act wakes Olvasó (`ActingReaders(autopilot=True)`);
results in <experiment>_autopilot_results.json. --autopilot-sleepwalk: a habit that never wakes Olvasó,
<experiment>_sleepwalk_results.json. Only for lives that learn from answers.

Experiment 33 adds --habit-teaches: the habit's acts teach Olvasó, which learns from their answers as if they were
its own (`ActingReaders(autopilot=True, habit_teaches="answers")`, implies --autopilot); results in
<experiment>_taught_results.json. --habit-felt: each habit act is felt afterwards on that hand
(`habit_teaches="felt"`), <experiment>_felthabit_results.json. --habit-felt-shuffled is its control (the same traces on
a random hand, 50-500 moments later): <experiment>_feltshuffled_results.json. --habit-felt-clipped: the felt trace
enters the choice bounded (clipped to -3..3), <experiment>_feltclipped_results.json. --habit-felt-answered: clipped, and
the trace turns to -1 when the habit act goes unanswered, <experiment>_feltanswered_results.json. --habit-felt-read:
clipped, and the words feel the trace bounded and learn it only while awake, <experiment>_feltread_results.json. --habit-felt-held:
as felt-read, but the trace is held while on autopilot and fades only once awake, <experiment>_feltheld_results.json.
--habit-felt-word: as felt-clipped, and the words are formed from the trace too and learn it always, <experiment>_feltword_results.json.
--habit-felt-sensed: as felt-clipped, and the habit's act has a faint sensed signature on touch,
<experiment>_feltsensed_results.json. --habit-felt-sensed-word: felt-word with that signature, <experiment>_feltsensedword_results.json.
--habit-felt-word-room: felt-word, and a daily tidy retires rare words long unheard, so that new words can be born late
in life (`ActingReaders(word_room=True)`), <experiment>_feltwordroom_results.json. --habit-felt-clipped-room: its
control, felt-clipped with the same tidy, <experiment>_feltclippedroom_results.json. --habit-felt-sensed-room: felt-sensed with the
same tidy, <experiment>_feltsensedroom_results.json.
"""
import os
import sys

ON = "--intention" in sys.argv or os.environ.get("ENDOLEXIS_FEEL_INTENTION") == "1"
if ON:
    os.environ["ENDOLEXIS_FEEL_INTENTION"] = "1"          # the pool's workers see it too
    sys.argv = [a for a in sys.argv if a != "--intention"]
SHUFFLED = "--surprise-shuffled" in sys.argv or os.environ.get("ENDOLEXIS_FEEL_SURPRISE") == "shuffled"
SURPRISE = SHUFFLED or "--surprise" in sys.argv or os.environ.get("ENDOLEXIS_FEEL_SURPRISE") == "1"
if SURPRISE:
    os.environ["ENDOLEXIS_FEEL_SURPRISE"] = "shuffled" if SHUFFLED else "1"
    sys.argv = [a for a in sys.argv if a not in ("--surprise", "--surprise-shuffled")]
UNTRACED = "--retry-untraced" in sys.argv or os.environ.get("ENDOLEXIS_RETRY") == "untraced"
RETRY = UNTRACED or "--retry" in sys.argv or os.environ.get("ENDOLEXIS_RETRY") == "1"
if RETRY:
    os.environ["ENDOLEXIS_RETRY"] = "untraced" if UNTRACED else "1"
    sys.argv = [a for a in sys.argv if a not in ("--retry", "--retry-untraced")]
    if not SHUFFLED:
        SURPRISE = True
        os.environ["ENDOLEXIS_FEEL_SURPRISE"] = "1"
ROOM = ("--habit-felt-word-room" in sys.argv or "--habit-felt-clipped-room" in sys.argv
        or "--habit-felt-sensed-room" in sys.argv
        or os.environ.get("ENDOLEXIS_WORD_ROOM") == "1")
if ROOM:
    os.environ["ENDOLEXIS_WORD_ROOM"] = "1"
    sys.argv = [{"--habit-felt-word-room": "--habit-felt-word", "--habit-felt-clipped-room": "--habit-felt-clipped",
                 "--habit-felt-sensed-room": "--habit-felt-sensed"}.get(a, a)
                for a in sys.argv]
TEACHES = ("answers" if "--habit-teaches" in sys.argv else "felt" if "--habit-felt" in sys.argv
           else "felt_shuffled" if "--habit-felt-shuffled" in sys.argv
           else "felt_clipped" if "--habit-felt-clipped" in sys.argv
           else "felt_answered" if "--habit-felt-answered" in sys.argv
           else "felt_read" if "--habit-felt-read" in sys.argv
           else "felt_held" if "--habit-felt-held" in sys.argv
           else "felt_word" if "--habit-felt-word" in sys.argv
           else "felt_sensed" if "--habit-felt-sensed" in sys.argv
           else "felt_sensed_word" if "--habit-felt-sensed-word" in sys.argv
           else os.environ.get("ENDOLEXIS_HABIT_TEACHES") or False)
if TEACHES:
    os.environ["ENDOLEXIS_HABIT_TEACHES"] = TEACHES
    sys.argv = [a for a in sys.argv if a not in ("--habit-teaches", "--habit-felt", "--habit-felt-shuffled",
                                          "--habit-felt-clipped", "--habit-felt-answered",
                                          "--habit-felt-read", "--habit-felt-held",
                                          "--habit-felt-word", "--habit-felt-sensed", "--habit-felt-sensed-word")]
SLEEPWALK = "--autopilot-sleepwalk" in sys.argv or os.environ.get("ENDOLEXIS_AUTOPILOT") == "sleepwalk"
AUTOPILOT = bool(TEACHES) or SLEEPWALK or "--autopilot" in sys.argv or os.environ.get("ENDOLEXIS_AUTOPILOT") == "1"
if AUTOPILOT:
    os.environ["ENDOLEXIS_AUTOPILOT"] = "sleepwalk" if SLEEPWALK else "1"
    sys.argv = [a for a in sys.argv if a not in ("--autopilot", "--autopilot-sleepwalk")]
BASELINE = "--mind-baseline" in sys.argv                # a run without the feeling, kept for the comparison
if BASELINE:
    sys.argv = [a for a in sys.argv if a != "--mind-baseline"]


def mind_kw():
    return {**({"feel_intention": True} if ON else {}), **({"feel_surprise": "shuffled" if SHUFFLED else True} if SURPRISE else {}),
            **({"retry": "untraced" if UNTRACED else True} if RETRY else {}),
            **({"autopilot": "sleepwalk" if SLEEPWALK else True} if AUTOPILOT else {}),
            **({"habit_teaches": TEACHES} if TEACHES else {}), **({"word_room": True} if ROOM else {})}


def results_name(name):
    """experiment_results.json, or with --intention experiment_intention_results.json (and --mind-baseline:
    experiment_mind_results.json, the same lives without the feeling, with the mind reported)."""
    if TEACHES:
        tag = {"answers": "_taught", "felt": "_felthabit", "felt_shuffled": "_feltshuffled",
               "felt_clipped": "_feltclipped", "felt_answered": "_feltanswered",
               "felt_read": "_feltread", "felt_held": "_feltheld", "felt_word": "_feltword",
               "felt_sensed": "_feltsensed", "felt_sensed_word": "_feltsensedword"}[TEACHES] + ("room" if ROOM else "")
        return name.replace("_results.json", tag + "_results.json")
    if AUTOPILOT:
        return name.replace("_results.json", "_sleepwalk_results.json" if SLEEPWALK else "_autopilot_results.json")
    if RETRY:
        return name.replace("_results.json", "_untraced_results.json" if UNTRACED else "_retry_results.json")
    tag = "_shuffled" if SHUFFLED else ("_both" if ON else "_surprise") if SURPRISE else "_intention" if ON else "_mind" if BASELINE else ""
    return name.replace("_results.json", tag + "_results.json")


def report(mind, days, childhood=None):
    """The mind's report for a life of `days` days: the first third, the last third (and the whole life)."""
    from endolexis.toyworld.hands import mind_report
    a = days // 3
    out = {"early": mind_report(mind, 1, max(2, a)), "late": mind_report(mind, days - a, days),
           "life": mind_report(mind, 1, days)}
    if getattr(mind, "word_room", False):          # how many places the daily tidy freed, a day
        out["life"]["words_retired_per_day"] = mind.words_retired / max(1, days)
    return out


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
