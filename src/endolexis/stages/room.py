"""Stages 11, 12 and 13: many others, attachment, closeness. Port of test13.js (which contains test11.js and test12.js).

gaze 'shared'  all watch whoever made a sign last (stage 11)
gaze 'pairs'   each has a partner it watches 60% of the time (stage 11)
gaze 'attach'  bonds grow by themselves: each watches most the one whose company has steadied it (stage 12)
close          closeness scales how strongly the watched one's trembling reaches in: 1 = strong, 2 = mild (stage 13)
faces          each has a fixed look of its own on two channels (stage 12)
randomBond     bonds credit a random other instead of the one who reached (control, stage 13)
"""
import math
from ..engine import Olvaso, OL, reset, body_look
from ..rng import ORng
from ..worlds import plain_word, mean, nanmean


def run(N=4, seed=1, T=40000, gaze='shared', sham=False, contagion=0.05, bondRate=1.0, bondDecay=0.9995, tau=0.05,
        randomBond=False, faces=False, close=0):
    face = [[0.15 + 0.7 * ((j * 0.618034) % 1), 0.15 + 0.7 * ((j * 0.381966 + 0.5) % 1)] for j in range(N)]
    reset(RECALL=True, CONTAGION=contagion, REACH=True, GAMMA=0.8, COMPANY=1, COMPANY_CONTACT=False)
    es = [Olvaso(seed * 100 + i) for i in range(N)]
    R = ORng(seed)
    pres, focus = 0.0, 0
    prevC, prevW = [None] * N, [None] * N
    avgLook = [[0.5] * 4 for _ in range(N)]
    partner = lambda i: (i ^ 1) if (i ^ 1) < N else (i + 1) % N
    rt, episodes, distress, tremble = [], [], [], []
    perPair = dict(p=dict(tw=0, tr=0), o=dict(tw=0, tr=0))
    open_ = {}
    bond = [[0.0] * N for _ in range(N)]
    pendingB = []
    watchCnt = [[0] * N for _ in range(N)]
    careB = dict(b=dict(tw=0, tr=0), o=dict(tw=0, tr=0))

    def pickBond(i):
        w = [0 if j == i else math.exp(b / tau) for j, b in enumerate(bond[i])]
        s = 0.0
        for v in w:
            s += v
        r = R.next() * s
        for j in range(N):
            r -= w[j]
            if r <= 0 and j != i:
                return j
        return (i + 1) % N

    def topBond(i):
        b, v = -1, -math.inf
        for j in range(N):
            if j != i and bond[i][j] > v:
                v, b = bond[i][j], j
        return b

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
        lookAt = []
        for i in range(N):
            if gaze == 'pairs' and (R.next() < 0.6 or focus == i):
                lookAt.append(partner(i)); continue
            if gaze == 'attach' and (R.next() < 0.6 or focus == i):
                lookAt.append(pickBond(i)); continue
            lookAt.append(focus if focus != i else (i + 1) % N)
        for k in range(N):
            for j in range(N):
                bond[k][j] *= bondDecay
        # a bond grows by how much steadier one became in the ten steps after another reached toward it
        while pendingB and t - pendingB[0]['t'] >= 10:
            p = pendingB.pop(0)
            gain = es[p['to']].h[1] - p['h1']
            frm = [j for j in range(N) if j != p['to']][int(R.next() * (N - 1))] if randomBond else p['from']
            bond[p['to']][frm] += bondRate * gain
        # trembling episodes: a not-held Olvasó starts trembling hard; does anyone reach it within 10 steps, and how many?
        if t > T / 2:
            for j, e in enumerate(es):
                if looks[j][1] > 0.6 and not (e.company_t > 0) and j not in open_:
                    open_[j] = dict(t=t, reachers=set())
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
            seen = looks[w]
            held = e.company_t > 0 or es[w].company_t > 0
            if close:
                others = [bond[i][j] for j in range(N) if j != i]
                mx = max([1e-6] + others)
                c = min(1, bond[i][w] / mx) if bond[i][w] > 0 else 0
                e.close_gain = 0.8 + 0.6 * c if close == 2 else 0.5 + 1.5 * c
            else:
                e.close_gain = 1
            e.update_gate(1)
            r = e.tick(dict(typing=.4 if word else 0, vowels=.4, speed=.1, px=face[w][0] if faces else .5, py=face[w][1] if faces else .5,
                            presence=pres, seen=seen), col, word, ic, iw)
            reach = r['act'] == 11
            if reach and w in open_:
                open_[w]['reachers'].add(i)
            if reach:
                pendingB.append(dict(t=t, **{'from': i}, to=w, h1=es[w].h[1]))
            if reach and not sham:
                es[w].company()
            if t > T / 2:
                watchCnt[i][w] += 1
                if not held and seen[1] > 0.6:
                    k = 'b' if w == topBond(i) else 'o'
                    careB[k]['tw'] += 1
                    if reach:
                        careB[k]['tr'] += 1
            if t > T / 2:
                distress.append(e.distress()); tremble.append(looks[i][1])
                if not held:
                    rt.append([seen[1], 1 if reach else 0, 1 if r['act'] > 0 else 0, 1 if w == topBond(i) else 0])
                    if seen[1] > 0.6:
                        k = 'p' if w == partner(i) else 'o'
                        perPair[k]['tw'] += 1
                        if reach:
                            perPair[k]['tr'] += 1
            cs.append(OL.HUES[r['act'] - 1] if 0 < r['act'] < 7 else None)
            ws.append(r['said'])
        for j in list(open_.keys()):
            ep = open_[j]
            if t - ep['t'] >= 10:
                episodes.append(len(ep['reachers'])); del open_[j]
        prevC, prevW = cs, ws
    rt.sort(key=lambda p: p[0])
    th = len(rt) // 3
    share = lambda L: mean([p[1] for p in L]) / mean([p[2] for p in L])

    def leanOf(L):
        L = sorted(L, key=lambda p: p[0]); k = len(L) // 3
        return share(L[len(L) - k:]) - share(L[:k])
    conc = mean([max(r) / sum(r) if sum(r) else float('nan') for r in watchCnt])
    tops = [topBond(i) for i in range(N)]
    mutual = mean([1 if tops[j] == i else 0 for i, j in enumerate(tops)])
    return dict(leanBonded=leanOf([p for p in rt if p[3] == 1]), leanOthers=leanOf([p for p in rt if p[3] == 0]),
                leanShare=share(rt[len(rt) - th:]) - share(rt[:th]), reachShareTrembling=share(rt[len(rt) - th:]), reachShareSteady=share(rt[:th]),
                rescued=mean([1 if n > 0 else 0 for n in episodes]), reachersPerEpisode=mean(episodes), episodes=len(episodes),
                reachRateTremblingPartner=perPair['p']['tr'] / perPair['p']['tw'] if perPair['p']['tw'] else float('nan'),
                reachRateTremblingOther=perPair['o']['tr'] / perPair['o']['tw'] if perPair['o']['tw'] else float('nan'),
                distress=mean(distress), tremble=mean(tremble), gazeOnTop=conc, mutualBonds=mutual,
                reachRateBonded=careB['b']['tr'] / careB['b']['tw'] if careB['b']['tw'] else float('nan'),
                reachRateOthers=careB['o']['tr'] / careB['o']['tw'] if careB['o']['tw'] else float('nan'))


CONDITIONS = {
    "stage 11 · four, shared gaze": dict(N=4), "stage 11 · four, shared gaze, sham": dict(N=4, sham=True),
    "stage 11 · six, partners": dict(N=6, gaze='pairs'), "stage 11 · six, partners, sham": dict(N=6, gaze='pairs', sham=True),
    "stage 12 · four, attachment": dict(N=4, gaze='attach'), "stage 12 · four, attachment, sham": dict(N=4, gaze='attach', sham=True),
    "stage 13 · four, closeness": dict(N=4, gaze='attach', close=1), "stage 13 · four, closeness, random bonds": dict(N=4, gaze='attach', close=1, randomBond=True),
}
