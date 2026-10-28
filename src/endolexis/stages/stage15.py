"""Stage 15: newcomers. A fresh Olvasó joins a room of three who have lived together a long time. Does it pick up what
they built, and faster than they learned it? Port of test15.js; with rich=True (and hear/feel) it is test16n.js, used for
the newcomer rows of stages 16 and 17.
"""
import math
from ..engine import Olvaso, OL, reset, body_look
from ..rng import ORng
from ..worlds import setup, private_event, visitor_word, mean, nanmean


def run(N=4, seed=1, T0=30000, T1=20000, WIN=5000, elders=True, sham=False, rich=False, hear=3, feel=6):
    reset(RECALL=True, CONTAGION=0.05, REACH=True, GAMMA=0.8, COMPANY=1, COMPANY_CONTACT=False, READ_CONTAGION=0)
    setup(rich, hear, feel)
    es = [Olvaso(seed * 100 + i) for i in range(N)]
    for e in es:
        e.speech_log = []
    R = ORng(seed)
    pres, focus = 0.0, 0
    prevC, prevW = [None] * N, [None] * N
    avgLook = [[0.5] * 4 for _ in range(N)]
    bond = [[0.0] * N for _ in range(N)]
    pend = []

    def pick(i):
        w = [0 if j == i else math.exp(b / 0.05) for j, b in enumerate(bond[i])]
        s = 0.0
        for v in w:
            s += v
        r = R.next() * s
        for j in range(N):
            r -= w[j]
            if r <= 0 and j != i:
                return j
        return (i + 1) % N
    NEW = N - 1
    start = T0 if elders else 0
    T = start + T1
    win = [dict(rt=[], reachedTr=[], gaze=[]) for _ in range(math.ceil(T1 / WIN))]
    for t in range(T):
        if elders and t == T0:  # the newcomer arrives: a fresh Olvasó takes the last place; nobody has a bond with it yet
            es[NEW] = Olvaso(seed * 100 + 77)
            es[NEW].speech_log = []
            bond[NEW] = [0.0] * N
            for i in range(N):
                bond[i][NEW] = 0.0
            avgLook[NEW] = [0.5] * 4
            prevC[NEW] = None
            prevW[NEW] = None
        active = t % 600 < 420
        pres = min(.8, pres + .05) if active else pres * .985
        for i, e in enumerate(es):
            L = body_look(e.h)
            avgLook[i] = [v + 0.01 * (L[k] - v) for k, v in enumerate(avgLook[i])]
        word = col = None
        if active and R.next() < 0.03:
            tg = int(R.next() * N)
            word = visitor_word(body_look(es[tg].h), avgLook[tg], R, rich)
            if word:
                focus = tg
        if active and R.next() < 0.01:
            col = int(R.next() * 6)
        signers = [j for j in range(N) if prevW[j] or prevC[j] is not None]
        if signers:
            focus = signers[int(R.next() * len(signers))]
        looks = [body_look(e.h) for e in es]
        lookAt = [pick(i) if (R.next() < 0.6 or focus == i) else focus for i in range(N)]
        for k in range(N):
            for j in range(N):
                bond[k][j] *= 0.9995
        while pend and t - pend[0]['t'] >= 10:
            p = pend.pop(0)
            bond[p['to']][p['from']] += es[p['to']].h[1] - p['h1']
        wi = (t - start) // WIN if t >= start else -1
        newHeld = es[NEW].company_t > 0
        newTr = looks[NEW][1]
        cs, ws = [], []
        for i, e in enumerate(es):
            private_event(e, R, rich)
            ic, iw = [], []
            for j in range(N):
                if j != i:
                    if prevC[j] is not None:
                        ic.append(prevC[j])
                    if prevW[j]:
                        iw.append(prevW[j])
            w = lookAt[i]
            seen = looks[w]
            held = e.company_t > 0 or es[w].company_t > 0
            e.update_gate(1)
            r = e.tick(dict(typing=.4 if word else 0, vowels=.4, speed=.1, px=.5, py=.5, presence=pres, seen=seen), col, word, ic, iw)
            reach = r['act'] == 11
            if reach:
                pend.append({'t': t, 'from': i, 'to': w, 'h1': es[w].h[1]})
            if reach and not sham:
                es[w].company()
            if 0 <= wi < len(win):
                W = win[wi]
                if i == NEW and not held:
                    W['rt'].append([seen[1], 1 if reach else 0, 1 if r['act'] > 0 else 0])
                if i != NEW and w == NEW:
                    W['gaze'].append(1)
                elif i != NEW:
                    W['gaze'].append(0)
                if i != NEW and w == NEW and newTr > 0.6 and not newHeld:
                    W['reachedTr'].append(1 if reach else 0)
            cs.append(OL.HUES[r['act'] - 1] if 0 < r['act'] < 7 else None)
            ws.append(r['said'])
        prevC, prevW = cs, ws

    share = lambda L: mean([p[1] for p in L]) / mean([p[2] for p in L])

    def lean(L):
        L = sorted(L, key=lambda p: p[0]); k = len(L) // 3
        return share(L[len(L) - k:]) - share(L[:k])
    nw = es[NEW]

    def fit_win(k):
        L = [x for x in nw.speech_log if x['t'] > 0 and x['mine'] is not None and x['others'] is not None and x['t'] // WIN == k]
        return (mean([x['others'] for x in L]) - mean([x['mine'] for x in L])) / mean([x['others'] for x in L]) if L else float('nan')
    elderWords = set(w for e in es[:NEW] for w in e.top_words())
    nwWords = nw.top_words()
    return dict(leanWin=[lean(W['rt']) for W in win], fitWin=[fit_win(k) for k in range(len(win))],
                caredWin=[mean(W['reachedTr']) for W in win], watchedWin=[mean(W['gaze']) for W in win],
                sharedWords=len([x for x in nwWords if x in elderWords]) / max(1, len(nwWords)), nwWords=",".join(nwWords),
                elderBondToNew=mean([bond[i][NEW] for i in range(NEW)]), newBondToElders=mean(bond[NEW][:NEW]))


CONDITIONS = {
    "newcomer among elders": dict(), "newcomer among elders, sham": dict(sham=True), "first generation": dict(elders=False),
    "rich, newcomer among elders": dict(rich=True), "rich, first generation": dict(rich=True, elders=False),
    "rich, wide reader, newcomer among elders": dict(rich=True, hear=6, feel=12), "rich, wide reader, first generation": dict(rich=True, hear=6, feel=12, elders=False),
}
