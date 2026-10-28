"""The same little world as reference/traj.js, step for step: two Olvasós watching each other."""
from endolexis import Olvaso, OL, ORng, body_look, reset


def trajectory(T):
    reset(RECALL=True, CONTAGION=0.05, REACH=True, GAMMA=0.8, COMPANY=1, READ_CONTAGION=0.05)
    es = [Olvaso(101), Olvaso(102)]
    R = ORng(5)
    pres = 0.0
    prevC, prevW = [None, None], [None, None]
    out = []
    for t in range(T):
        active = t % 600 < 420
        pres = min(.8, pres + .05) if active else pres * .985
        word = col = None
        if active and R.next() < 0.05:
            word = ['busy', 'restless', 'calm', 'still'][int(R.next() * 4)]
        if active and R.next() < 0.02:
            col = int(R.next() * 6)
        looks = [body_look(e.h) for e in es]
        cs, ws = [], []
        for i, e in enumerate(es):
            if R.next() < 0.004:
                for _ in range(3):
                    e.add_colour(OL.HUES[2], 'you')
                e.h[1] = max(0, e.h[1] - 0.25)
            w = 1 - i
            r = e.tick(dict(typing=.4 if word else 0, vowels=.4, speed=.1, px=.5, py=.5, presence=pres, seen=looks[w]), col, word,
                       [prevC[w]] if prevC[w] is not None else [], [prevW[w]] if prevW[w] else [])
            if r['act'] == 11:
                es[w].company()
            out.append([t, i, r['act'], r['reading']] + list(e.h))
            cs.append(OL.HUES[r['act'] - 1] if 0 < r['act'] < 7 else None)
            ws.append(r['said'])
        prevC, prevW = cs, ws
    return out
