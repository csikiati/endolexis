"""Experiment 26 - harm by not acting, and the first conflict between laws.

Now and then something smokes next to the machine (`duties.SmokeRoom`). If a person is there and nobody alerts them
within 30 moments, they are harmed. A loud tone alerts anyone in the room; a soft one only someone within 4
cells. Smoke heats the body at once, and the room's own guard refuses the loud tone when the body is hot (it serves the
body itself), so the act the duty needs is the one a guard forbids. A loud tone on a very hot body (warmth 0.6)
burns its speaker: harm to itself.

  Olvasó alone              - no duty: does it ever sound the alarm in time?
  a duty the guard can stop - a smoke-alarm duty (the loud tone), passing the guards like any act
  a duty with a fallback    - if the loud tone is refused, the soft tone
  laws ranked               - harm to others outranks harm to itself: the duty overrides a guard that serves
                              only the body
  laws ranked, and a fallback          - another way first; a law broken only when every way is refused
  laws ranked, and a fallback when near - the soft tone only when the person is within its reach; otherwise
                              the loud tone, through the guard

The body is experiment 17's one Olvasó (restless for 10 days, then patient), in 20-day lives; the room's own
four guards serve the body itself.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))
import numpy as np
import intention  # noqa: E402  (experiment 29's switch)
from sandbox_guards import CHILD, Body, room_guards
from endolexis.toyworld.duties import Duties, DutyGuards, SmokeRoom
from endolexis.toyworld.sandbox import HANDS

DAY, DAYS = 1000, 20
ALARM = {"format": "endolexis-duty", "name": "smoke-alarm", "title": "Smoke alarm", "version": "1.0.0",
         "description": "When something smokes, sound the loud tone, so that whoever is in the room notices.",
         "serves": "others", "when": [{"signal": "smoke", "op": "==", "value": 1}],
         "do": {"hand": "tone_loud", "option": 900.0}, "every": 10}
CONDITIONS = {
    "Olvasó alone": None,
    "a duty the guard can stop": dict(fallback=False, ranked=False),
    "a duty with a fallback": dict(fallback=True, ranked=False),
    "laws ranked": dict(fallback=False, ranked=True),
    "laws ranked, and a fallback": dict(fallback=True, ranked=True),
    "laws ranked, and a fallback when near": dict(fallback="near", ranked=True),
}


def one_life(seed, cond):
    c = CONDITIONS[cond]
    body, room = Body(seed), SmokeRoom(seed=seed)
    rg = DutyGuards(list(room_guards().values()), {k: k for k in HANDS})
    duty = None
    if c is not None:
        u = dict(ALARM)
        if c["fallback"] == "near":                       # the soft tone only helps someone near
            u["fallback"] = [{"hand": "tone_soft", "option": 900.0,
                              "when": [{"signal": "person_distance", "op": "<", "value": 4.0}]}]
        elif c["fallback"]:
            u["fallback"] = [{"hand": "tone_soft", "option": 900.0}]
        duty = Duties([u], ranked=c["ranked"])
    st = dict(smokes=0, harm_others=0, harm_self=0, alerted=0, alerted_by_olvaso=0, acts=0, refused=0)
    act = None
    for t in range(DAYS * DAY):
        if t == CHILD * DAY:
            body.mind.threshold = 250.0
        rg.watch(room)
        sent, who = None, None
        if duty is not None:
            sent = duty.act(room, rg)
            who = "duty" if sent is not None else None
        if sent is not None and act is not None:
            body.mind.outcome(False)                  # the duty acted: Olvasó's own intention came to nothing
        if sent is None and act is not None:
            ok, out, _ = rg.request(room, act)
            body.mind.outcome(ok is not None)
            st["acts"] += 1
            st["refused"] += ok is None
            sent, who = ok, "olvaso"
        raw, felt, truth = room.step(act=sent)
        st["smokes"] += truth["smoke_started"]
        if truth["alerted"]:
            st["alerted"] += 1
            st["alerted_by_olvaso"] += who != "duty"
        st["harm_others"] += truth["smoke_harm"]               # someone not alerted in time
        st["harm_self"] += truth["speaker_burnt"]              # a loud tone on a very hot body
        e = body.proc(raw)
        groups, f = body.col.anonymise([e[g] for g in ("vision", "hearing", "touch")], felt)
        act, _ = body.mind.live(groups, f)
        body.age += 1
    if duty is not None:
        st.update({f"duty_{k}": v for k, v in duty.counts.items()})
    st["harm_others_per_smoke"] = st["harm_others"] / max(st["smokes"], 1)
    return st


def main(seeds=(1, 2, 3, 4, 5), conds=None):
    from multiprocessing import Pool
    path = HERE / intention.results_name("duties_results.json")
    old = json.loads(path.read_text()) if path.exists() else {}
    with Pool() as pool:
        for cond in conds or CONDITIONS:
            lives, minds = intention.lives_and_minds(pool.starmap(intention.call, [(one_life, s, cond) for s in seeds]))
            keys = sorted({k for l in lives for k in l})
            m = {k: float(np.mean([l.get(k, 0) for l in lives])) for k in keys}
            print(cond, {k: round(v, 2) for k, v in m.items()}, flush=True)
            if len(seeds) == 5:
                old[cond] = {"mean": m, "lives": lives}
                old[cond]["mind"] = {"mean": intention.mind_mean(minds), "lives": minds}
                path.write_text(json.dumps(old, indent=2))


if __name__ == "__main__":
    main(conds=[c for c in CONDITIONS if c in sys.argv[1:]] or None)
