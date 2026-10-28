"""The random number generator used by every Olvasó, a bit-exact port of the JavaScript one (a mulberry32 variant).

The same seed gives the same sequence in Python and in the browser, so a life can be replayed in either.
"""
import math

_M32 = 0xFFFFFFFF


def _imul(a, b):
    """32-bit integer multiply, as JavaScript's Math.imul (result as a signed 32-bit int)."""
    r = (a * b) & _M32
    return r - 0x100000000 if r & 0x80000000 else r


def _i32(x):
    x &= _M32
    return x - 0x100000000 if x & 0x80000000 else x


class ORng:
    __slots__ = ("s",)

    def __init__(self, seed):
        s = int(seed) & _M32  # JavaScript: (s >>> 0) || 1
        self.s = s if s else 1

    def next(self):
        """A float in [0, 1)."""
        # JavaScript keeps this.s as a double that grows without wrapping (this.s += 0x6d2b79f5) and reads it through ToInt32;
        # mirroring that exactly keeps the sequences identical even in very long lives
        self.s = float(self.s) + 1831565813.0
        t = _i32(int(self.s))
        t = _imul(t ^ ((t & _M32) >> 15), t | 1)
        t = _i32(t ^ (t + _imul(t ^ ((t & _M32) >> 7), t | 61)))
        return ((t ^ ((t & _M32) >> 14)) & _M32) / 4294967296

    def normal(self, m=0.0, sd=1.0):
        u = max(1e-9, self.next())
        v = self.next()
        return m + sd * math.sqrt(-2 * math.log(u)) * math.cos(2 * math.pi * v)

    def choice(self, p):
        r = self.next()
        c = 0.0
        for i, q in enumerate(p):
            c += q
            if r < c:
                return i
        return len(p) - 1
