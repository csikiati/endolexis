"""Stages 16 and 17: richer lives, and a richer reader. Plain against rich worlds (stage 16) and wider readers
(stage 17: hear = numbers per sound, feel = felt channels). Port of test16.js.

Measures: wordState (share of the speaker's hidden state that goes with which word it says), fit (its own word fits
its state better than its other words), readCor (a heard word tracks the speaker's look more than a bystander's;
rooms of three or more), lean (caring), reachAfterWord / reachNoWord (asking), answeredSpoken / answeredSilent.
"""
import math
from ..engine import Olvaso, OL, reset, body_look
from ..rng import ORng
from ..worlds import setup, private_event, visitor_word, mean, nanmean


def cor(a, b):
    ma, mb = mean(a), mean(b)
    s = x = y = 0.0
    for i in range(len(a)):
        s += (a[i] - ma) * (b[i] - mb); x += (a[i] - ma) ** 2; y += (b[i] - mb) ** 2
    return s / math.sqrt(x * y + 1e-12)


def eta(rows):
    """Share of the variance of the hidden state that goes with which word was said (0 = none, 1 = all), averaged over the four."""
    by = {}
    for w, h in rows:
        by.setdefault(w, []).append(h)
    groups = [g for g in by.values() if len(g) >= 5]
    if len(groups) < 2:
        return float('nan')
    allh = [h for g in groups for h in g]
    s = 0.0
    for i in range(4):
        m = mean([h[i] for h in allh])
        tot = mean([(h[i] - m) ** 2 for h in allh])
        bet = 0.0
        for g in groups:
            bet = bet + len(g) * (mean([h[i] for h in g]) - m) ** 2
        bet /= len(allh)
        s += bet / tot if tot > 1e-9 else 0
    return s / 4


def run(N=4, seed=1, T=40000, rich=False, sham=False, dim=0.0, maxc=60, hear=3, feel=6):
    reset(RECALL=True, CONTAGION=0.05, REACH=True, GAMMA=0.8, COMPANY=1, COMPANY_CONTACT=False, READ_CONTAGION=0, MAXC=maxc)
    setup(rich, hear, feel)
    es = [Olvaso(seed * 100 + i) for i in range(N)]
    for e in es:
        e.speech_log = []
    R = ORng(seed)
    pres, focus = 0.0, 0
    prevC, prevW = [None] * N, [None] * N
    avgLook = [[0.5] * 4 for _ in range(N)]
    said = [[] for _ in range(N)]
    care, heard, asks, readSp, readBy, readC = [], [], [], [], [], []
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
            word = visitor_word(body_look(es[tg].h), avgLook[tg], R, rich)
            if word:
                focus = tg
        if active and R.next() < 0.01:
            col = int(R.next() * 6)
        signers = [j for j in range(N) if prevW[j] or prevC[j] is not None]
        if signers:
            focus = signers[int(R.next() * len(signers))]
        looks = [body_look(e.h) for e in es]
        lookAt = []
        for i in range(N):
            if N == 2:
                lookAt.append(1 - i); continue
            if focus != i and R.next() >= 0.6:
                lookAt.append(focus); continue
            j = int(R.next() * (N - 1))
            lookAt.append(j + 1 if j >= i else j)
        late = t > T / 2
        if late and N >= 3:  # reading the speaker: a word just heard from j; what does it lead i to expect to see?
            for i in range(N):
                for j in range(N):
                    if j != i and prevW[j] and R.next() < 0.2:
                        ex = es[i].expect_seen(prevW[j])
                        if not ex:
                            continue
                        k = int(R.next() * N)
                        while k == i or k == j:
                            k = (k + 1) % N
                        err = lambda L: sum(abs(v - L[q]) for q, v in enumerate(ex)) / 4
                        readSp.append(err(looks[j])); readBy.append(err(looks[k])); readC.append([ex, looks[j], looks[k]])
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
            if late:
                if r['said']:
                    said[i].append([r['said'], list(e.h)])
                if not held:
                    care.append([looks[w][1], 1 if reach else 0, 1 if r['act'] > 0 else 0])
                    heard.append([looks[w][1], 1 if watchedSpoke else 0, 1 if reach else 0])
                    if looks[i][1] > 0.6:
                        asks.append(dict(t=t, i=i, spoke=bool(r['said'])))
            cs.append(OL.HUES[r['act'] - 1] if 0 < r['act'] < 7 else None)
            ws.append(r['said'])
        prevC, prevW = cs, ws

    def thirds(L):
        L = sorted(L, key=lambda p: p[0]); k = len(L) // 3
        return L[len(L) - k:], L[:k]
    share = lambda L: mean([p[1] for p in L]) / mean([p[2] for p in L])
    cTop, cBot = thirds(care)
    hTop, _ = thirds(heard)
    got = lambda a: 1 if any(a['t'] < x <= a['t'] + 10 for x in reachedTimes[a['i']]) else 0

    def efit(e):
        L = [x for x in e.speech_log if x['t'] > T / 2 and x['mine'] is not None and x['others'] is not None]
        return (mean([x['others'] for x in L]) - mean([x['mine'] for x in L])) / mean([x['others'] for x in L]) if L else float('nan')
    return dict(wordState=nanmean([eta(s) for s in said]), fit=nanmean([efit(e) for e in es]), nWords=mean([len(e.top_words()) for e in es]),
                readSpeaker=(mean(readBy) - mean(readSp)) / mean(readBy) if readSp else float('nan'),
                readCor=mean([cor([c[0][q] for c in readC], [c[1][q] for c in readC]) - cor([c[0][q] for c in readC], [c[2][q] for c in readC]) for q in range(4)]) if len(readC) > 50 else float('nan'),
                lean=share(cTop) - share(cBot), reachTop=mean([p[1] for p in cTop]),
                reachAfterWord=mean([p[2] for p in hTop if p[1]]), reachNoWord=mean([p[2] for p in hTop if not p[1]]),
                answeredSpoken=mean([got(a) for a in asks if a['spoke']]), answeredSilent=mean([got(a) for a in asks if not a['spoke']]),
                concepts=mean([len(e.n) for e in es]), speaks=mean([len([x for x in e.speech_log if x['t'] > T / 2]) for e in es]) / (T / 2))


CONDITIONS = {
    "stage 16 · four, plain": dict(N=4), "stage 16 · four, rich": dict(N=4, rich=True),
    "stage 16 · pairs dimmed, plain": dict(N=2, dim=0.7), "stage 16 · pairs dimmed, rich": dict(N=2, dim=0.7, rich=True),
    "stage 16 · pairs dimmed, rich, sham": dict(N=2, dim=0.7, rich=True, sham=True),
    "stage 16 · pairs dimmed, rich, long": dict(N=2, dim=0.7, rich=True, T=80000), "stage 16 · pairs dimmed, rich, long, big": dict(N=2, dim=0.7, rich=True, T=80000, maxc=150),
    "stage 17 · pairs dimmed, rich, finer hearing": dict(N=2, dim=0.7, rich=True, hear=6),
    "stage 17 · pairs dimmed, rich, finer feeling": dict(N=2, dim=0.7, rich=True, feel=12),
    "stage 17 · pairs dimmed, rich, wide": dict(N=2, dim=0.7, rich=True, hear=6, feel=12),
    "stage 17 · pairs dimmed, plain, wide": dict(N=2, dim=0.7, hear=6, feel=12),
    "stage 17 · four, rich, wide": dict(N=4, rich=True, hear=6, feel=12),
}
