"""What happens around and to the Olvasós in the experiments: private events, the visitor's words, the reader's width.

plain world (stages 8-15): one kind of private event (a jolt with a random colour), four visitor words.
rich world (stages 16-21): four kinds of private event, each with its own colour, and eight visitor words about
four sides of how a body looks, chosen so their sounds stay apart.
"""
from .engine import OL

KINDS = [
    dict(name="jolt", hue=8, rate=0.004),
    dict(name="warmth", hue=48, rate=0.002),
    dict(name="drain", hue=228, rate=0.002),
    dict(name="flash", hue=290, rate=0.002),
]


def _apply(kind, h):
    if kind == "jolt":
        h[0] = min(1, h[0] + 0.2); h[1] = max(0, h[1] - 0.25)
    elif kind == "warmth":
        h[2] = min(1, h[2] + 0.3); h[1] = min(1, h[1] + 0.15)
    elif kind == "drain":
        h[0] = max(0, h[0] - 0.25); h[1] = max(0, h[1] - 0.1)
    elif kind == "flash":
        h[3] = min(1, h[3] + 0.5); h[0] = min(1, h[0] + 0.1)


def setup(rich, hear=3, feel=6):
    """Vocabulary size and the reader's width (stage 17: numbers per sound, felt channels)."""
    OL.NWORDS = 8 if rich else 4
    OL.HEAR = hear
    OL.FEEL = feel
    OL.NX = 18 + hear - 3
    OL.NY = feel + 2


def jolt(e, R):
    """The plain world's private event: only the one it happens to sees its (random) colour."""
    if R.next() < 0.004:
        hh = int(R.next() * 6)
        for _ in range(3):
            e.add_colour(OL.HUES[hh], "you")
        _apply("jolt", e.h)
        return "jolt"
    return None


def private_event(e, R, rich):
    if not rich:
        return jolt(e, R)
    for K in KINDS:
        if R.next() < K["rate"]:
            for _ in range(3):
                e.add_colour(K["hue"], "you")
            _apply(K["name"], e.h)
            return K["name"]
    return None


def plain_word(L, A):
    """The visitor names how one of them looks, compared with how it usually looks (stages 8-15)."""
    if L[3] > 0.45:
        return "busy"
    if L[1] > A[1] + 0.12:
        return "restless"
    if L[1] < A[1] - 0.06:
        return "calm"
    if L[3] < 0.15:
        return "still"
    return None


def visitor_word(L, A, R, rich):
    if not rich:
        return plain_word(L, A)
    side = int(R.next() * 4)
    if side == 0:
        return "uneasy" if L[1] > A[1] + 0.12 else ("easy" if L[1] < A[1] - 0.06 else None)
    if side == 1:
        return "doing" if L[3] > 0.45 else ("lazy" if L[3] < 0.15 else None)
    if side == 2:
        return "large" if L[0] > A[0] + 0.08 else ("weak" if L[0] < A[0] - 0.08 else None)
    return "close" if L[2] > A[2] + 0.08 else ("apart" if L[2] < A[2] - 0.08 else None)


def presence(t, pres):
    """The visitor comes and goes: 420 steps present, 180 away, in a 600-step cycle."""
    active = t % 600 < 420
    return active, (min(.8, pres + .05) if active else pres * .985)


NAN = float("nan")


def mean(a):
    """The JavaScript harnesses' mean: a plain average (NaN for an empty list; a NaN inside makes it NaN)."""
    a = list(a)
    return sum(a) / len(a) if a else NAN


def nanmean(a):
    """Average over the values that are numbers (how results are pooled across runs)."""
    return mean([v for v in a if v is not None and v == v])
