"""endolexis: the Endolexis theory's Olvasó engine and experiments.

Endolexis: the outside world is the dictionary with which a mind reads its own inside.
An Olvasó (Hungarian for "reader") is a small entity built that way: it learns who it is by reading itself
through what reaches it from outside.

    from endolexis import Olvaso, OL, reset, body_look
    reset()                       # all switches to their defaults
    e = Olvaso(seed=1)
    r = e.tick({"presence": 0.8, "typing": 0.2})
"""
from .rng import ORng
from .engine import Olvaso, Entity, OL, reset, body_look, word_code, voice_code, hear_idx, HNAMES, XNAMES

__version__ = "0.1.0"
__all__ = ["ORng", "Olvaso", "Entity", "OL", "reset", "body_look", "word_code", "voice_code", "hear_idx", "HNAMES", "XNAMES"]
