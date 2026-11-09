"""The studio: processor units, architectures, the sleep schedule, and a short life of an ensemble."""
import json
import re
from pathlib import Path

import pytest

from endolexis.studio import (build, check, check_unit, from_template, library, live, load, schedule,
                              stagger, stub, templates)
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


def test_web_studio_is_built_from_the_package():
    html = (ROOT / "studio" / "index.html").read_text(encoding="utf-8")

    def block(name):
        m = re.search(rf'<script type="application/json" id="{name}">(.*?)</script>', html, re.S)
        return json.loads(m.group(1).replace("<\\/", "</"))
    assert block("data-library") == library(), "run python studio/build.py"
    assert block("data-templates") == templates(), "run python studio/build.py"
    examples = block("data-examples")
    for f in EXAMPLES.glob("*.json"):
        a = load(f)
        assert examples[a["name"]] == a, "run python studio/build.py"
