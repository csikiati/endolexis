"""Stage 20: symbiosis. One body, two components: the Olvasó reads the body from inside; the Processor reads the world
and nothing of itself, and decides what to fetch, rewarded by how the shared body feels. Port of test20.js.

The body has two needs that take turns (charge = food, contact = warmth); each resource is only there while its cue is lit.
modes: 'processor'        the Processor alone: sees the cues, chooses what to fetch
       'olvaso'           the Olvasó alone: sees the same cues (as outside channels) and fetches with its own colour acts
       'pair'             the Processor sees the cues and the Olvasó's latest colour; the Olvasó only marks
       'scrambled'        as pair, but the colour the Processor sees is random (control)
       'reading'          the Processor sees which pattern the Olvasó reads itself as (its self-interpretation)
       'readingScrambled' as reading, but a random pattern (control)
       'feeling'          the Processor sees the raw felt channels instead (uninterpreted inside)
       'oracle'           the Processor is told which need is draining (upper bound)
       'processorSeason'  the Processor sees the season itself (relay check, with ambiguous=True)
ambiguous=True: low charge and low contact feel exactly alike from inside; which one drains is set by a season that
shows outside, only to the Olvasó.
"""
import math
from ..engine import Olvaso, OL, reset
from ..rng import ORng
from ..worlds import mean


def run(seed=1, T=60000, mode='pair', drain=0.02, gain=0.15, every=5, eps=0.05, ambiguous=False):
    reset(RECALL=False, CONTAGION=0, REACH=False, GAMMA=0.8, COMPANY=1, READ_CONTAGION=0, VOICES=False, SALIENCE=0, HEAR=3, FEEL=6,
          NX=18, NY=8, NWORDS=4, MAXC=60)
    e = Olvaso(seed * 100 + 7)
    R = ORng(seed * 7 + 1)
    if ambiguous:
        e.A = [[(row[0] + row[2]) / 2, row[1], (row[0] + row[2]) / 2, row[3]] for row in e.A]
    season = need = 0
    cue = [True, False]
    lastColour, colourAge = 6, 99
    Q, Nn = {}, {}

    def qget(c):
        if c not in Q:
            Q[c] = [0.0, 0.0, 0.0]; Nn[c] = [0, 0, 0]
        return Q[c]
    pending = None
    late = []
    byNeed = [[0] * 7, [0] * 7]
    fetches = dict(right=0, wrong=0, empty=0)
    for t in range(T):
        if R.next() < 1 / 300:  # what matters changes (and with it the season)
            need = 1 - need; season = need
        for k in range(2):  # resources come and go
            if R.next() < 1 / 60:
                cue[k] = R.next() < 0.5
        if need == 0:
            e.h[0] = max(0, e.h[0] - drain)
        else:
            e.h[2] = max(0, e.h[2] - drain)
        sense = dict(typing=0, vowels=0.4, speed=(0.9 if season else 0.1) if ambiguous else 0.1, px=0.9 if cue[0] else 0.1, py=0.9 if cue[1] else 0.1,
                     presence=0.42, seen=None, noBody=False)
        e.update_gate(1)
        r = e.tick(sense, None, None, [], [])
        colour = r['act'] - 1 if 1 <= r['act'] <= 6 else None
        if colour is not None:
            lastColour, colourAge = colour, 0
        else:
            colourAge += 1
            if colourAge > 10:
                lastColour = 6
        if t > T / 2 and colour is not None:
            byNeed[need][colour] += 1
        fetch = 0  # 0 nothing, 1 food, 2 warmth
        if mode == 'olvaso':
            if colour is not None:
                fetch = 1 if colour < 3 else 2
        elif t % every == 0:
            if pending:
                rw = pending['d0'] - e.distress()
                q, n = Q[pending['c']], Nn[pending['c']]
                n[pending['a']] += 1
                q[pending['a']] += (rw - q[pending['a']]) / min(n[pending['a']], 50)
                pending = None
            if mode == 'pair':
                seen = lastColour
            elif mode == 'scrambled':
                seen = int(R.next() * 7)
            elif mode == 'oracle':
                seen = need
            elif mode == 'reading':
                seen = e.reading
            elif mode == 'feeling':
                seen = "".join('1' if v > 0 else '0' for v in r['y'][:6])
            elif mode == 'processorSeason':
                seen = season
            elif mode == 'readingScrambled':
                seen = int(R.next() * max(1, len(e.n)))
            else:
                seen = 0
            c = f"{1 if cue[0] else 0}{1 if cue[1] else 0}|{'-' if mode == 'processor' else seen}"
            q = qget(c)
            a = 0
            if R.next() < eps:
                a = int(R.next() * 3)
            else:
                for k in (1, 2):
                    if q[k] > q[a]:
                        a = k
            fetch = a
            pending = dict(c=c, a=a, d0=e.distress())
        if fetch:
            k = fetch - 1
            if not cue[k]:
                fetches['empty'] += 1
            else:
                if k == 0:
                    e.h[0] = min(1, e.h[0] + gain)
                else:
                    e.h[2] = min(1, e.h[2] + gain)
                fetches['right' if k == need else 'wrong'] += 1
        if t > T / 2:
            late.append(e.distress())
    tot = sum(sum(r) for r in byNeed)
    mi = 0.0
    if tot > 50:  # how much the Olvasó's colours say about which need is draining (0 = nothing, 1 = everything)
        pn = [sum(r) / tot for r in byNeed]
        for c in range(7):
            pc = (byNeed[0][c] + byNeed[1][c]) / tot
            for n in range(2):
                p = byNeed[n][c] / tot
                if p > 0:
                    mi += p * math.log(p / (pn[n] * pc))
        hn = -sum(p * math.log(p) if p > 0 else 0 for p in pn)
        mi = mi / hn if hn > 0 else 0
    else:
        mi = float('nan')
    return dict(distress=mean(late), danger=mean([1 if d > 0.35 else 0 for d in late]), colourSaysNeed=mi, marks=tot / (T / 2), **fetches)


CONDITIONS = {m: dict(mode=m) for m in ['processor', 'olvaso', 'pair', 'scrambled', 'reading', 'readingScrambled', 'feeling', 'oracle']}
CONDITIONS.update({f"ambiguous {m}": dict(mode=m, ambiguous=True) for m in ['processor', 'feeling', 'reading', 'readingScrambled', 'oracle', 'processorSeason']})
