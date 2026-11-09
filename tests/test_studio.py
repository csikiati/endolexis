"""The studio: processor units, architectures, the sleep schedule, and a short life of an ensemble."""
import json
import re
from pathlib import Path

import pytest

from endolexis.studio import (build, check, check_hand, check_unit, from_hand_template, from_template, hand_stub,
                              hand_templates, hands, library, live, load, schedule, stagger, stub, templates)
from endolexis.studio.__main__ import main as cli
from endolexis.toyworld.ensemble import ASLEEP, AWAKE, WAKING, state_at

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "studio" / "examples"


def test_library_and_templates_are_sound():
    for name, u in library().items():
        assert check_unit(u) == [], name
        assert u["name"] == name
    for t in templates():
        u = from_template(t)
        assert check_unit(u) == [], t["name"]
        compile(stub(u), t["name"], "exec")


def test_hands_and_hand_templates_are_sound():
    from endolexis.toyworld.hands import DETAILS
    from endolexis.toyworld.room import KINDS
    lib = hands()
    assert sorted(lib) == sorted(KINDS)
    for k, u in lib.items():
        assert check_hand(u) == [] and u["implementation"] == {"builtin": k}
        assert [o["value"] for o in u["options"]] == list(DETAILS[k])
    for t in hand_templates():
        u = from_hand_template(t)
        if t["name"] != "blank":                             # the blank one is filled in by its maker
            assert check_hand(u) == [], t["name"]
        compile(hand_stub(u), t["name"], "exec")


def test_a_hand_the_room_does_not_have_is_kept_and_left_out():
    arch = load(EXAMPLES / "one-never-sleeps.json")
    vib = from_hand_template({t["name"]: t for t in hand_templates()}["vibrate"])
    arch["outputs"] = [{"id": "h_paint", "kind": "paint", "unit": hands()["paint"]}, {"id": "h_vibrate", "unit": vib}]
    arch["links"] = [ln for ln in arch["links"] if ln["from"]["node"] != "o1"]
    arch["links"] += [{"from": {"node": "o1"}, "to": {"node": h}} for h in ("h_paint", "h_vibrate")]
    bad, warn = check(arch)
    assert bad == [] and any("Vibrate" in w and "left out" in w for w in warn)
    ens, _ = build(arch)
    assert ens.members[0].mind.kinds == [3]                  # paint only
    arch["outputs"][1]["unit"] = {"format": "endolexis-hand", "name": "x"}
    assert any("target is missing" in b for b in check(arch)[0])


def test_state_at_wraps_around_midnight():
    assert state_at(0.9, 0.3, 0.2, 0.8) == ASLEEP
    assert state_at(0.05, 0.3, 0.2, 0.8) == ASLEEP
    assert state_at(0.15, 0.3, 0.2, 0.8) == WAKING
    assert state_at(0.5, 0.3, 0.2, 0.8) == AWAKE
    assert state_at(0.5, 0.0, 0.0, 0.0) == AWAKE


def test_three_taking_turns_is_the_plan():
    arch = load(EXAMPLES / "three-take-turns.json")
    bad, warn = check(arch)
    assert bad == [] and warn == []
    s = schedule(arch)
    assert s["never_awake"] == 0 and s["two_asleep"] == 0 and s["ideal"] == 1.0
    assert abs(s["minds_on"] - 2.0) < 0.01


def test_check_finds_problems():
    arch = load(EXAMPLES / "one-never-sleeps.json")
    arch["olvasos"][0]["sleep"], arch["olvasos"][0]["waking"] = 0.8, 0.4
    arch["links"].append({"from": {"node": "p_touch", "port": 7}, "to": {"node": "o1"}})
    bad, _ = check(arch)
    assert any("at most 1" in b for b in bad) and any("no output 7" in b for b in bad)
    with pytest.raises(ValueError):
        build(arch)


def test_stagger_chains_the_sleeps():
    arch = load(EXAMPLES / "three-sleep-together.json")
    assert schedule(arch)["two_asleep"] > 0.3
    stagger(arch)
    assert schedule(arch)["two_asleep"] == 0


def test_port_level_wiring_and_hands():
    arch = load(EXAMPLES / "two-take-turns.json")
    # B sees only motion (ports 6-8 of vision) and may only paint
    arch["links"] = [ln for ln in arch["links"] if not (ln["to"]["node"] == "o2" or ln["from"]["node"] == "o2")]
    arch["links"] += [{"from": {"node": "p_vision", "port": k}, "to": {"node": "o2"}} for k in (6, 7, 8)]
    arch["links"].append({"from": {"node": "o2"}, "to": {"node": "h_paint"}})
    ens, senses = build(arch, seed=3)
    b = ens.members[1]
    assert b.wiring == [("p_vision", [6, 7, 8])]
    assert b.mind.kinds == [3]
    r = live(arch, seed=3, days=2, childhood_days=1)
    assert r["members"]["B"]["naps"] >= 1 and 0 <= r["linked_read"] <= 1


def test_a_short_life_of_three():
    r = live(load(EXAMPLES / "three-take-turns.json"), seed=2, days=2, childhood_days=1)
    assert r["someone_awake"] == 1.0 and abs(r["minds_on"] - 2.0) < 0.01
    assert set(r["members"]) == {"A", "B", "C"}


def test_command_line(tmp_path, capsys):
    out = tmp_path / "accel.json"
    assert cli(["new-processor", "accelerometer", "--name", "my-accel", "-o", str(out), "--stub", str(tmp_path / "my_accel.py")]) == 0
    u = json.loads(out.read_text())
    assert u["name"] == "my-accel" and u["implementation"] == {"python": "my_accel:process"}
    assert cli(["check", str(EXAMPLES / "three-take-turns.json")]) == 0
    assert "100%" in capsys.readouterr().out
    assert cli(["new-hand", "light", "--name", "lamp", "-o", str(tmp_path / "lamp.json"), "--stub", str(tmp_path / "lamp.py")]) == 0
    h = json.loads((tmp_path / "lamp.json").read_text())
    assert h["name"] == "lamp" and h["implementation"] == {"python": "lamp:act"} and check_hand(h) == []


def test_web_studio_is_built_from_the_package():
    html = (ROOT / "studio" / "index.html").read_text(encoding="utf-8")

    def block(name):
        m = re.search(rf'<script type="application/json" id="{name}">(.*?)</script>', html, re.S)
        return json.loads(m.group(1).replace("<\\/", "</"))
    assert block("data-library") == library(), "run python studio/build.py"
    assert block("data-templates") == templates(), "run python studio/build.py"
    assert block("data-hands") == hands(), "run python studio/build.py"
    assert block("data-hand-templates") == hand_templates(), "run python studio/build.py"
    from endolexis.studio import guard_templates as gt, guards as gl
    assert block("data-guards") == gl() and block("data-guard-templates") == gt(), "run python studio/build.py"
    examples = block("data-examples")
    for f in EXAMPLES.glob("*.json"):
        a = load(f)
        assert examples[a["name"]] == a, "run python studio/build.py"


# --- guards -------------------------------------------------------------------------------------

from endolexis.studio import from_guard_template, guard_templates, guards  # noqa: E402
from endolexis.toyworld.guards import RoomGuards, check_guard, decide, run_tests  # noqa: E402
from endolexis.toyworld.room import Room  # noqa: E402


def test_guard_units_and_templates_hold_their_scenarios():
    for u in list(guards().values()) + [from_guard_template(t) for t in guard_templates() if t["name"] != "blank"]:
        assert check_guard(u) == [], u["name"]
        assert u["tests"] and all(ok for *_, ok in run_tests([u])), u["name"]


def test_guards_only_take_away():
    blade = from_guard_template({t["name"]: t for t in guard_templates()}["blade"])
    assert decide([blade], "blade", "fast", {"person_distance": 5}) [:2] == ("limit", "slow")
    assert decide([blade], "blade", "fast", {"person_distance": 2})[0] == "stop"
    assert decide([blade], "paint", 0, {"person_distance": 0})[0] == "allow"        # not its hand
    assert decide([blade], "blade", "fast", {})[0] == "stop"                        # cannot sense: fails closed
    blade["on_missing"] = "ignore"
    assert decide([blade], "blade", "fast", {})[0] == "allow"


def test_the_room_guard_as_units_lives_the_same_life():
    arch = load(EXAMPLES / "three-take-turns.json")
    own = live(arch, seed=4, days=3, childhood_days=1)
    arch["guards"] = [{"id": k, "unit": u} for k, u in guards().items()]
    assert check(arch) == ([], [])
    as_units = live(arch, seed=4, days=3, childhood_days=1)
    counts = as_units.pop("guards")
    assert as_units == own and sum(c["refuse"] for c in counts.values()) > 0


def test_a_stop_rule_cuts_a_hand_at_work():
    room = Room(seed=1, hands=True)
    g = {"format": "endolexis-guard", "name": "shy", "description": "x", "version": "1", "protects": ["paint"],
         "rules": [{"when": [{"signal": "person", "op": "==", "value": 1}], "then": "stop"}]}
    rg = RoomGuards([g], {"paint": "paint"})
    room.charge = 0.9
    sent, out, _ = rg.request(room, ("paint", 1))
    room.step(act=sent)
    assert room.paint_left > 0
    room.present = True
    rg.watch(room)
    assert room.paint_left == 0 and rg.counts["shy"]["stop"] == 1


def test_a_failing_scenario_stops_the_life():
    arch = load(EXAMPLES / "one-never-sleeps.json")
    u = dict(guards()["paint-battery"])
    u["rules"] = [{"when": [{"signal": "charge", "op": "<", "value": 0.1}], "then": "refuse"}]   # too weak for its tests
    arch["guards"] = [{"id": "g", "unit": u}]
    bad, _ = check(arch)
    assert any("scenario 'low battery' gave allow" in b for b in bad)
    with pytest.raises(ValueError):
        build(arch)


def test_guard_command_line(tmp_path, capsys):
    out = tmp_path / "blade.json"
    assert cli(["new-guard", "blade", "-o", str(out)]) == 0
    assert cli(["test-guards", str(out)]) == 0
    assert "4 of 4 scenarios hold" in capsys.readouterr().out
