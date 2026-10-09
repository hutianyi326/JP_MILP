"""Merge negligible same-direction FCR bins, preserving mass and direction means."""
from copy import deepcopy

def merge_tail_states(states,threshold=1e-8):
    rows=deepcopy(states);merged=0.;count=0
    for source in sorted(list(rows),key=lambda r:r['weight']):
        if source not in rows or source['weight']>=threshold:continue
        # Never cancel opposite activation directions through a mean.
        pool=[r for r in rows if r is not source and r['weight']>=threshold and
              ((source['f']>=0 and r['f']>=0) or (source['f']<=0 and r['f']<=0))]
        if not pool:continue
        target=min(pool,key=lambda r:abs(r['f']-source['f']))
        w=target['weight'];v=source['weight']
        for key in target:
            if key!='weight':target[key]=(w*target[key]+v*source[key])/(w+v)
        target['weight']=w+v;rows.remove(source);merged+=v;count+=1
    for k in ('f','s','t'):
        assert abs(sum(s['weight']*s[k] for s in states)-sum(s['weight']*s[k] for s in rows))<1e-12
    for sign in (-1,1):
        assert abs(sum(s['weight']*max(sign*s['f'],0) for s in states)-sum(s['weight']*max(sign*s['f'],0) for s in rows))<1e-12
    return rows,dict(threshold=threshold,merged_mass=merged,merged_states=count)


def recovery_baseline_bounds(rows,power,eta_charge,eta_discharge):
    """Valid daily-energy cuts, not a changed EV operating policy.

    With daily E_end=E_start and constant p, p=-mean(q*mu)-L*mean(c),
    L=1-eta_c*eta_d, and c<=max(-p,0)+Q*E[(-f)+]. Hence the bounds.
    Requires zero auxiliaries, identity ports and symmetric q<=Q.
    """
    means=[sum(s['weight']*s['f'] for s in r['states']) for r in rows]
    down=[sum(s['weight']*max(-s['f'],0) for s in r['states']) for r in rows]
    loss=1-eta_charge*eta_discharge
    a=power*sum(max(m,0) for m in means)/len(rows)
    b=power*sum(down)/len(rows)
    lower=-(a+loss*b)/(1-loss)
    upper=power*sum(max(-m,0) for m in means)/len(rows)
    return lower,upper
