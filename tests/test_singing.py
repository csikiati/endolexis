"""The singing hand (experiment 34): three octaves of notes and pauses, a whole to a sixteenth long."""
import numpy as np

from endolexis.toyworld.hands import ActingReaders, DETAILS
from endolexis.toyworld.processors import Processors
from endolexis.toyworld.room import LENGTHS, SONG, Room, note_freq


def sing(acts, n, voice="mirror"):
    room, proc, out = Room(seed=1, hands=True, voice=voice), Processors(), []
    for t in range(n):
        raw, _, truth = room.step(act=acts.get(t))
        out.append((proc(raw)["hearing"], truth))
    return room, out


def test_the_song_has_three_octaves_of_notes_and_pauses_of_five_lengths():
    assert sorted(LENGTHS.values()) == [1, 2, 4, 8, 16]
    assert len(SONG) == 37 * 5 and (None, 16) in SONG and (35, 1) in SONG
    assert abs(note_freq(12) / note_freq(0) - 2) < 1e-9 and abs(note_freq(0) - 130.81) < 0.01
    assert DETAILS["sing"] == SONG


def test_a_note_sounds_as_long_as_it_lasts_and_is_heard_at_its_pitch():
    _, out = sing({0: ("sing", (0, 4)), 4: ("sing", (24, 1)), 5: ("sing", (None, 2)), 7: ("sing", (35, 1))}, 9)
    assert [o[1]["own_song"] for o in out] == [True] * 4 + [True, False, False, True, False]
    centroid = [o[0][4] for o in out]
    assert centroid[0] < 200 < centroid[4] < 700 < centroid[7]          # C3, C5, B5
    assert out[0][0][0] > out[5][0][0] + 10                              # a pause is quiet


def test_a_new_note_cuts_off_the_one_sounding_and_only_the_mirror_hears_it():
    room, out = sing({0: ("sing", (0, 16)), 2: ("sing", (None, 1))}, 4)
    assert [o[1]["own_song"] for o in out] == [True, True, False, False]
    assert room.sung == {0: (0, 16), 2: (None, 1)}
    _, deaf = sing({0: ("sing", (0, 4))}, 2, voice="deaf")
    assert deaf[0][1]["own_song"] and not deaf[0][1]["heard_song"]
    assert deaf[0][0][0] < out[0][0][0] - 10


def test_an_olvaso_can_have_the_voice_as_its_only_hand():
    m = ActingReaders([3, 2], 2, learn="answer", hands=["sing"], seed=1)
    r = np.random.default_rng(0)
    reqs = []
    for _ in range(600):
        req, _ = m.live([r.normal(size=3), r.normal(size=2)], r.normal(size=2))
        if req is not None:
            reqs.append(req)
            m.outcome(True)
    assert reqs and all(k == "sing" and d in SONG for k, d in reqs)
