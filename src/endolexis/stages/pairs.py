"""Stages 18, 19 and 21: out of sight, strong meanings, the expanded self. Pairs in a rich world with the wider reader.
Port of test21.js (which contains test18.js).

sight          share of time each sees the other (in stretches of about 100 steps); out of sight, the other's four body
               channels are missing to the watcher, not grey (stage 18)
readC          the trembling it expects of the other unsettles it (stage 14's route, the only one left out of sight)
nameDistress   the visitor always names trembling when it sees it, as a caregiver does (stage 18)
voices         each speaker's words carry its own timbre (stage 18)
sal            moments that feel worse than usual are learned more strongly (stage 19)
couple         shared fate: the pair's steadiness pulls together at this rate per step (stage 21)
contagion      seeing the other tremble unsettles (0 switches it off, stage 21)
company        how strongly being reached steadies (stage 21)
"""
import math
from ..engine import Olvaso, OL, reset, body_look, voice_code
from ..rng import ORng
from ..worlds import setup, private_event, visitor_word, mean, nanmean
from .stage16 import eta


def cor(a, b):
    if len(a) < 30:
        return float('nan')
    ma, mb = mean(a), mean(b)
    s = x = y = 0.0
    for i in range(len(a)):
        s += (a[i] - ma) * (b[i] - mb); x += (a[i] - ma) ** 2; y += (b[i] - mb) ** 2
    return s / math.sqrt(x * y + 1e-12)


def self_boundary(e, ch):
    """The self's boundary, read from inside: across the patterns it has learned (weighted by use), how closely does the
    feeling it forecasts follow channel ch? ch = 13: the other's trembling; ch = 17: its own trembling."""
    K = len(e.n)
    N = mf = mx = 0.0
    for k in range(K):
        N += e.n[k]; mf += e.n[k] * e.F[k]; mx += e.n[k] * e.mu[k, ch]
    mf /= N; mx /= N
    sxy = sxx = syy = 0.0
    for k in range(K):
        a, b = e.F[k] - mf, e.mu[k, ch] - mx
        sxy += e.n[k] * a * b; sxx += e.n[k] * a * a; syy += e.n[k] * b * b
    return sxy / math.sqrt(sxx * syy + 1e-12)


def run(seed=1, T=40000, rich=True, hear=6, feel=12, sight=1.0, readC=0.05, sham=False, nameDistress=False, voices=False,
        sal=0.0, couple=0.0, contagion=0.05, company=1.0):
    N = 2
    reset(MAXC=60, RECALL=True, CONTAGION=contagion, REACH=True, GAMMA=0.8, COMPANY=company, COMPANY_CONTACT=False,
          READ_CONTAGION=readC, VOICES=voices, SALIENCE=sal)
    setup(rich, hear, feel)
    es = [Olvaso(seed * 100 + i) for i in range(N)]
    for i, e in enumerate(es):
        e.speech_log = []
        e.voice = i
    R = ORng(seed)
    pres = 0.0
    prevC, prevW = [None, None], [None, None]
    avgLook = [[0.5] * 4 for _ in range(N)]
    sees = [R.next() < sight, R.next() < sight]
    lastSpoke = [-99, -99]
    said = [[] for _ in range(N)]
    rows, asks, imag = [], [], []
    reachedTimes = [[] for _ in range(N)]
    for t in range(T):
        active = t % 600 < 420
        pres = min(.8, pres + .05) if active else pres * .985
        for i, e in enumerate(es):
            L = body_look(e.h)
            avgLook[i] = [v + 0.01 * (L[k] - v) for k, v in enumerate(avgLook[i])]
        for i in range(N):
            if R.next() < 0.01:
                sees[i] = R.next() < sight
        word = col = None
        if active and R.next() < 0.03:
            tg = int(R.next() * N)
            L = body_look(es[tg].h)
            word = 'uneasy' if nameDistress and L[1] > avgLook[tg][1] + 0.12 else visitor_word(L, avgLook[tg], R, rich)
        if active and R.next() < 0.01:
            col = int(R.next() * 6)
        if couple:
            a, b = es[0].h[1], es[1].h[1]
            es[0].h[1] += couple * (b - a); es[1].h[1] += couple * (a - b)
        looks = [body_look(e.h) for e in es]
        late = t > T / 2
        cs, ws = [], []
        for i, e in enumerate(es):
            private_event(e, R, rich)
            w = 1 - i
            ic = [prevC[w]] if prevC[w] is not None else []
            iw = [{'w': prevW[w], 'from': w}] if prevW[w] else []
            unseen = not sees[i]
            held = e.company_t > 0 or es[w].company_t > 0
            e.update_gate(1)
            r = e.tick(dict(typing=.4 if word else 0, vowels=.4, speed=.1, px=.5, py=.5, presence=pres, seen=None if unseen else looks[w], unseen=unseen),
                       col, word, ic, iw)
            reach = r['act'] == 11
            if reach:
                reachedTimes[w].append(t)
            if reach and not sham:
                es[w].company()
            if r['said']:
                lastSpoke[i] = t
            if late:
                if r['said']:
                    said[i].append([r['said'], list(e.h)])
                if unseen and e.belief is not None and len(e.belief):
                    ex = 0.0
                    for j, p in enumerate(e.belief):
                        ex += p * e.mu[j, 13]
                    imag.append([ex, looks[w][1], 1 if t - lastSpoke[w] <= 5 else 0])
                if not held:
                    rows.append(dict(unseen=unseen, tr=looks[w][1], reach=1 if reach else 0, acted=1 if r['act'] > 0 else 0, spoke=1 if t - lastSpoke[w] <= 3 else 0))
                    if looks[i][1] > 0.6:
                        asks.append(dict(t=t, i=i, spoke=bool(r['said']), unseenByOther=not sees[w]))
            cs.append(OL.HUES[r['act'] - 1] if 0 < r['act'] < 7 else None)
            ws.append(r['said'])
        prevC, prevW = cs, ws

    def thirds(L):
        L = sorted(L, key=lambda p: p['tr']); k = len(L) // 3
        return L[len(L) - k:], L[:k]
    share = lambda L: mean([p['reach'] for p in L]) / mean([p['acted'] for p in L])

    def lean(L):
        if len(L) < 300:
            return float('nan')
        top, bot = thirds(L)
        return share(top) - share(bot)
    S = [r for r in rows if not r['unseen']]
    U = [r for r in rows if r['unseen']]
    uTop, uBot = thirds(U) if len(U) > 300 else ([], [])
    got = lambda a: 1 if any(a['t'] < x <= a['t'] + 10 for x in reachedTimes[a['i']]) else 0
    aU = [a for a in asks if a['unseenByOther']]
    aS = [a for a in asks if not a['unseenByOther']]

    def efit(e):
        L = [x for x in e.speech_log if x['t'] > T / 2 and x['mine'] is not None and x['others'] is not None]
        return (mean([x['others'] for x in L]) - mean([x['mine'] for x in L])) / mean([x['others'] for x in L]) if L else float('nan')
    imW = [x for x in imag if x[2]]
    imN = [x for x in imag if not x[2]]
    run.last = es
    selfOther = mean([self_boundary(e, 13) for e in es])
    selfOwn = mean([self_boundary(e, 17) for e in es])

    def uneasy_other(i, e):
        a = e.expect_seen('uneasy', voice_code('uneasy', 1 - i if OL.VOICES else None))
        b = e.expect_seen('easy', voice_code('easy', 1 - i if OL.VOICES else None))
        return a[1] - b[1] if a and b else float('nan')

    def uneasy_own(i, e):
        a = e.evoke_word('uneasy', voice_code('uneasy', 1 - i if OL.VOICES else None))
        b = e.evoke_word('easy', voice_code('easy', 1 - i if OL.VOICES else None))
        return b['ev'][1] - a['ev'][1] if a and b else float('nan')
    spoken = [x for e in es for x in e.speech_log if x['t'] > T / 2]
    return dict(selfOther=selfOther, selfOwn=selfOwn, boundary=selfOther / selfOwn,
                wordState=nanmean([eta(s) for s in said]), fit=nanmean([efit(e) for e in es]),
                leanSeen=lean(S), leanUnseen=lean(U), unseenShare=len(U) / max(1, len(rows)),
                reachUnseenTrSpoke=mean([p['reach'] for p in uTop if p['spoke']]), reachUnseenTrSilent=mean([p['reach'] for p in uTop if not p['spoke']]),
                reachUnseenCalmSpoke=mean([p['reach'] for p in uBot if p['spoke']]), reachUnseenCalmSilent=mean([p['reach'] for p in uBot if not p['spoke']]),
                answeredSpokenUnseen=mean([got(a) for a in aU if a['spoke']]), answeredSilentUnseen=mean([got(a) for a in aU if not a['spoke']]),
                answeredSpokenSeen=mean([got(a) for a in aS if a['spoke']]), answeredSilentSeen=mean([got(a) for a in aS if not a['spoke']]),
                imagCorAfterWord=cor([x[0] for x in imW], [x[1] for x in imW]), imagCorNoWord=cor([x[0] for x in imN], [x[1] for x in imN]),
                uneasyShare=(sum(1 for x in spoken if x['w'] == 'uneasy') / len(spoken)) if spoken else float('nan'),
                uneasyOther=nanmean([uneasy_other(i, e) for i, e in enumerate(es)]), uneasyOwn=nanmean([uneasy_own(i, e) for i, e in enumerate(es)]),
                speaks=mean([len([x for x in e.speech_log if x['t'] > T / 2]) for e in es]) / (T / 2))


CONDITIONS = {
    "stage 18 · always in sight": dict(sight=1), "stage 18 · always in sight, sham": dict(sight=1, sham=True),
    "stage 18 · half the time": dict(sight=0.5), "stage 18 · half the time, sham": dict(sight=0.5, sham=True),
    "stage 18 · never": dict(sight=0), "stage 18 · never, sham": dict(sight=0, sham=True),
    "stage 18 · half, distress named, voices": dict(sight=0.5, nameDistress=True, voices=True),
    "stage 19 · salience 4": dict(sight=0.5, nameDistress=True, voices=True, sal=4),
    "stage 19 · salience 10": dict(sight=0.5, nameDistress=True, voices=True, sal=10),
    "stage 19 · salience 10, sham": dict(sight=0.5, nameDistress=True, voices=True, sal=10, sham=True),
    "stage 21 · no shared fate": dict(sight=1, couple=0, contagion=0, readC=0),
    "stage 21 · shared fate 0.1": dict(sight=1, couple=0.1, contagion=0, readC=0),
    "stage 21 · shared fate 0.1, sham": dict(sight=1, couple=0.1, contagion=0, readC=0, sham=True),
    "stage 21 · seeing unsettles": dict(sight=1, couple=0, contagion=0.05, readC=0),
    "stage 21 · seeing unsettles, sham": dict(sight=1, couple=0, contagion=0.05, readC=0, sham=True),
}
