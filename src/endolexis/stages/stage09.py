"""Stages 9 and 10: answering and caring.

Stage 9: does what one Olvasó reads of another change what it does? Stage 10 (caring): pairs, 40 000 steps, reaching
steadies the one reached, and seeing another tremble more than oneself unsettles; does it learn to reach toward a
trembling one? The published caring numbers use the corrected count (moments when either is being held are left out).
Port of test9.js and care10.js.
"""
import math
from ..engine import Olvaso, OL, reset, body_look
from ..rng import ORng
from ..worlds import plain_word, mean, nanmean


def _mi(pairs):
    n = len(pairs)
    if not n:
        return float("nan")
    cx, cy, cxy = {}, {}, {}
    for a, b in pairs:
        cx[a] = cx.get(a, 0) + 1; cy[b] = cy.get(b, 0) + 1; cxy[(a, b)] = cxy.get((a, b), 0) + 1
    m = 0.0
    for (a, b), c in cxy.items():
        p = c / n
        m += p * math.log2(p / ((cx[a] / n) * (cy[b] / n)))
    return m


def run(N=4, seed=1, T=16000, directed=False, contagion=0.0, jolts=True, recall=True, reach=False, sham=False, gamma=0.8,
        mutual=False, company=1.0, companyContact=False):
    reset(COMPANY=company, COMPANY_CONTACT=bool(companyContact), GAMMA=gamma, RECALL=recall, CONTAGION=contagion, REACH=reach)
    es = [Olvaso(seed * 100 + i) for i in range(N)]
    R = ORng(seed)
    pres, focus = 0.0, 0
    prevC, prevW, prevLook = [None] * N, [None] * N, [0] * N
    avgLook = [[0.5] * 4 for _ in range(N)]
    resp = dict(hi=[], lo=[], ot=[], rt=[], rh=[], rl=[], ra=[], rn=[], rw=[])
    wordAct, acted, notActed, distress, trembLog = [], [], [], [], []
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
        trembLog.append([l[1] for l in looks])
        lookAt = [focus if focus != i else (i + 1) % N for i in range(N)]
        cs, ws = [], []
        for i, e in enumerate(es):
            if jolts and R.next() < 0.004:
                hh = int(R.next() * 6)
                for _ in range(3):
                    e.add_colour(OL.HUES[hh], 'you')
                e.h[0] = min(1, e.h[0] + 0.2); e.h[1] = max(0, e.h[1] - 0.25)
            ic, iw = [], []
            for j in range(N):
                if j != i:
                    if prevC[j] is not None and (not directed or prevLook[j] == i):
                        ic.append(prevC[j])
                    if prevW[j]:
                        iw.append(prevW[j])
            w = lookAt[i]
            seen = looks[w]
            pre_self, pre_other = e.company_t, es[w].company_t
            e.update_gate(1)
            r = e.tick(dict(typing=.4 if word else 0, vowels=.4, speed=.1, px=.5, py=.5, presence=pres, seen=seen), col, word, ic, iw)
            a = r['act']
            kind = 'rest' if a == 0 else ('colour' if a < 7 else ('reach' if a == 11 else 'speak'))
            if kind == 'reach' and not sham:
                es[w].company()
                if mutual:
                    e.company()
            if t > T / 2 and not (pre_self > 0) and not (pre_other > 0):
                resp['ot'].append([body_look(e.h)[1], 1 if kind == 'reach' else 0, 0 if kind == 'rest' else 1])
                resp['rt'].append([seen[1], 1 if kind == 'reach' else 0, 0 if kind == 'rest' else 1, 0 if kind in ('reach', 'rest') else 1])
                if seen[1] > 0.6:
                    resp['rh'].append(1 if kind == 'reach' else 0)
                elif seen[1] < 0.35:
                    resp['rl'].append(1 if kind == 'reach' else 0)
                if seen[1] > 0.6 and t + 8 < T:
                    (resp['ra'] if kind == 'reach' else resp['rn']).append(dict(t=t, w=w, tr=seen[1]))
                if iw and not word:
                    resp['rw'].append([iw[0], 1 if kind == 'reach' else 0])
            if t > T / 2:
                if seen[1] > 0.5:
                    resp['hi'].append(1 if kind == 'colour' else 0)
                elif seen[1] < 0.2:
                    resp['lo'].append(1 if kind == 'colour' else 0)
                if iw and not word:
                    wordAct.append([iw[0], kind])
                if seen[1] > 0.4 and t + 8 < T:
                    (acted if (kind == 'colour' and directed) else notActed).append(dict(t=t, w=w, tr=seen[1]))
                distress.append(e.distress())
            cs.append(OL.HUES[a - 1] if kind == 'colour' else None)
            ws.append(r['said'])
        prevC, prevW, prevLook = cs, ws, lookAt

    def dTr(L):
        return mean([trembLog[x['t'] + 8][x['w']] - x['tr'] for x in L if x['t'] + 8 < len(trembLog)])
    sh = [p[1] for p in wordAct]
    for k in range(len(sh) - 1, 0, -1):
        j = int(R.next() * (k + 1)); sh[k], sh[j] = sh[j], sh[k]
    rt = sorted(resp['rt'], key=lambda p: p[0])
    third = len(rt) // 3
    top, bot = rt[len(rt) - third:] if third else [], rt[:third]
    topR, botR = mean([p[1] for p in top]), mean([p[1] for p in bot])

    def pr(w):
        L = [p for p in resp['rw'] if p[0] == w]
        return mean([p[1] for p in L]) if len(L) > 20 else float('nan')
    anyTop, anyBot = mean([p[2] for p in top]), mean([p[2] for p in bot])
    othTop, othBot = mean([p[3] for p in top]), mean([p[3] for p in bot])
    ot = sorted(resp['ot'], key=lambda p: p[0])
    t3 = len(ot) // 3
    otop, obot = ot[len(ot) - t3:] if t3 else [], ot[:t3]
    selfTop = mean([p[1] for p in otop]) / mean([p[2] for p in otop]) if otop else float('nan')
    selfBot = mean([p[1] for p in obot]) / mean([p[2] for p in obot]) if obot else float('nan')
    return dict(selfReachShareTrembling=selfTop, selfReachShareSteady=selfBot, anyActTop=anyTop, anyActBottom=anyBot,
                otherActsTop=othTop, otherActsBottom=othBot, reachTopThird=topR, reachBottomThird=botR,
                seenTrembleMean=mean([p[0] for p in resp['rt']]), reachWhenTrembling=mean(resp['rh']), reachWhenSteady=mean(resp['rl']),
                trembleAfterReach=dTr(resp['ra']), trembleAfterNoReach=dTr(resp['rn']), reachAfterRestless=pr('restless'),
                reachAfterCalm=pr('calm'), reachAfterBusy=pr('busy'), colourWhenTrembling=mean(resp['hi']), colourWhenSteady=mean(resp['lo']),
                wordActMI=_mi(wordAct), wordActMIshuffled=_mi([[p[0], sh[k]] for k, p in enumerate(wordAct)]),
                trembleAfterGiven=dTr(acted), trembleAfterNot=dTr(notActed), nGiven=len(acted), distress=mean(distress))


def caring(runs=12, seed0=1, **opts):
    """Stage 10 as published: pairs, 40 000 steps, reaching on, seeing-based unsettling 0.05. The lean is the share of acts
    that are reaches toward the watched one when it trembles most (top third) minus when it is steadiest (bottom third)."""
    R = [run(N=2, T=40000, seed=s, reach=True, contagion=0.05, **opts) for s in range(seed0, seed0 + runs)]
    share = lambda r, top: r['reachTopThird'] / r['anyActTop'] if top else r['reachBottomThird'] / r['anyActBottom']
    return dict(runs=runs, reachShareTrembling=nanmean(share(r, True) for r in R), reachShareSteady=nanmean(share(r, False) for r in R),
                lean=nanmean(share(r, True) - share(r, False) for r in R), leanRuns=sum(share(r, True) > share(r, False) for r in R),
                distress=nanmean(r['distress'] for r in R)), R


CONDITIONS = {
    "caring": dict(),
    "caring, sham": dict(sham=True),
}
