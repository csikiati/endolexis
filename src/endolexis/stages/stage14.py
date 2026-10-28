"""Stage 14: asking. Does a trembling one's word become a request? Port of test14.js.

dim    the body is harder to see: its trembling shows only partly (seen moves toward the middle)
readC  the trembling it expects of the watched one unsettles it, as seeing would
"""
from ..engine import Olvaso, OL, reset, body_look
from ..rng import ORng
from ..worlds import plain_word, mean, nanmean


def run(N=2, seed=1, T=40000, sham=False, contagion=0.05, dim=0.0, readC=0.0):
    reset(READ_CONTAGION=readC, RECALL=True, CONTAGION=contagion, REACH=True, GAMMA=0.8, COMPANY=1, COMPANY_CONTACT=False)
    es = [Olvaso(seed * 100 + i) for i in range(N)]
    R = ORng(seed)
    pres, focus = 0.0, 0
    prevC, prevW = [None] * N, [None] * N
    avgLook = [[0.5] * 4 for _ in range(N)]
    own, heard, asks = [], [], []
    reachedTimes = [[] for _ in range(N)]
    for t in range(T):
        active = t % 600 < 420
        pres = min(.8, pres + .05) if active else pres * .985
        for i, e in enumerate(es):
            L = body_look(e.h)
            avgLook[i] = [v + 0.01 * (L[k] - v) for k, v in enumerate(avgLook[i])]
        word = col = None
        if active and R.next() < 0.03:
            tg = int(R.next() * N)
            word = plain_word(body_look(es[tg].h), avgLook[tg])
            if word:
                focus = tg
        if active and R.next() < 0.01:
            col = int(R.next() * 6)
        signers = [j for j in range(N) if prevW[j] or prevC[j] is not None]
        if signers:
            focus = signers[int(R.next() * len(signers))]
        looks = [body_look(e.h) for e in es]
        lookAt = [focus if focus != i else (i + 1) % N for i in range(N)]
        cs, ws = [], []
        for i, e in enumerate(es):
            if R.next() < 0.004:
                hh = int(R.next() * 6)
                for _ in range(3):
                    e.add_colour(OL.HUES[hh], 'you')
                e.h[0] = min(1, e.h[0] + 0.2); e.h[1] = max(0, e.h[1] - 0.25)
            ic, iw = [], []
            for j in range(N):
                if j != i:
                    if prevC[j] is not None:
                        ic.append(prevC[j])
                    if prevW[j]:
                        iw.append(prevW[j])
            w = lookAt[i]
            seen = [0.5 + (1 - dim) * (v - 0.5) if dim else v for v in looks[w]]
            held = e.company_t > 0 or es[w].company_t > 0
            watchedSpoke = bool(prevW[w])
            e.update_gate(1)
            r = e.tick(dict(typing=.4 if word else 0, vowels=.4, speed=.1, px=.5, py=.5, presence=pres, seen=seen), col, word, ic, iw)
            reach = r['act'] == 11
            if reach:
                reachedTimes[w].append(t)
            if reach and not sham:
                es[w].company()
            if t > T / 2 and not held:
                own.append([looks[i][1], 1 if r['said'] else 0, 1 if r['act'] > 0 else 0])
                heard.append([looks[w][1], 1 if watchedSpoke else 0, 1 if reach else 0, 1 if r['act'] > 0 else 0, prevW[w] if watchedSpoke else None])
                if looks[i][1] > 0.6:
                    asks.append(dict(t=t, i=i, spoke=bool(r['said'])))
            cs.append(OL.HUES[r['act'] - 1] if 0 < r['act'] < 7 else None)
            ws.append(r['said'])
        prevC, prevW = cs, ws

    def thirds(L):
        L = sorted(L, key=lambda p: p[0]); k = len(L) // 3
        return L[len(L) - k:], L[:k]
    oTop, oBot = thirds(own)
    hTop, _ = thirds(heard)
    reachSpoke = mean([p[2] for p in hTop if p[1]])
    reachSilent = mean([p[2] for p in hTop if not p[1]])
    byWord = {}
    for p in hTop:
        if p[1]:
            byWord.setdefault(p[4], []).append(p[2])
    got = lambda a: 1 if any(a['t'] < x <= a['t'] + 10 for x in reachedTimes[a['i']]) else 0
    return dict(speakWhenTrembling=mean([p[1] for p in oTop]), speakWhenSteady=mean([p[1] for p in oBot]),
                answeredSpoken=mean([got(a) for a in asks if a['spoke']]), answeredSilent=mean([got(a) for a in asks if not a['spoke']]),
                reachAfterWord=reachSpoke, reachNoWord=reachSilent, nWord=len([p for p in hTop if p[1]]),
                byWord={k: mean(v) for k, v in byWord.items() if len(v) > 30})


CONDITIONS = {
    "pairs": dict(N=2), "pairs, sham": dict(N=2, sham=True),
    "four": dict(N=4), "four, sham": dict(N=4, sham=True),
    "pairs, dimmed, reading unsettles": dict(N=2, dim=0.7, readC=0.05), "pairs, dimmed, reading unsettles, sham": dict(N=2, dim=0.7, readC=0.05, sham=True),
}
