"""Read-only diagnostics of existing JP proxies; not an activation estimator."""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FIT = ROOT / 'countries/JP/research/analysis/rrfit_forecast_usage_30min_JST_expost.csv'
ICS = ROOT / 'data/raw/JP/activation_sources_20261001/ics_basis_202606.csv'

def regime(ts):
    d = ts[:10]
    return 'before_2025-03-14' if d < '2025-03-14' else ('2025-03-14_to_2026-03-13' if d < '2026-03-14' else 'from_2026-03-14')

def number(x):
    try:
        y = float(x)
        return y if math.isfinite(y) else None
    except (ValueError, TypeError):
        return None

def corr(x, y):
    if len(x) < 2:
        return None
    mx, my = mean(x), mean(y)
    den = math.sqrt(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))
    return sum((a-mx)*(b-my) for a,b in zip(x,y))/den if den else None

def summarize(rows):
    qualified = [r for r in rows if r['q'] > 0 and r['err'] is not None and r['usage'] is not None]
    ys = [r['usage']/100 for r in qualified]
    bytime = {r['dt']: r['usage']/100 for r in qualified}
    pairs = [(v,bytime[t+timedelta(minutes=30)]) for t,v in bytime.items() if t+timedelta(minutes=30) in bytime]
    return dict(rows=len(rows), requirement_zero=sum(r['q']==0 for r in rows),
                error_missing=sum(r['err'] is None for r in rows), qualified_rows=len(qualified),
                published_zero=sum(y==0 for y in ys), published_hundred=sum(y==1 for y in ys),
                published_interior=sum(0<y<1 for y in ys), qualified_usage_mean=mean(ys) if ys else None,
                lag1_adjacent_pairs=len(pairs),lag1_usage_correlation=corr([p[0] for p in pairs],[p[1] for p in pairs]))

rows=[]
with FIT.open(encoding='utf-8-sig',newline='') as f:
    for r in csv.DictReader(f):
        rows.append(dict(area=r['area'],ts=r['timestamp_JST'],dt=datetime.fromisoformat(r['timestamp_JST']),
                         q=number(r['requirement_MW']),err=number(r['FIT_forecast_error_MW']),usage=number(r['published_usage_pct'])))
assert len({(r['ts'],r['area']) for r in rows})==len(rows), 'Duplicate FIT keys'
assert all(r['q'] is not None and r['q']>=0 for r in rows)
assert all(r['usage'] is not None and 0<=r['usage']<=100 for r in rows)
areas=sorted({r['area'] for r in rows})
expected=int((datetime.fromisoformat('2026-09-01T00:00:00+09:00')-datetime.fromisoformat('2025-01-01T00:00:00+09:00')).total_seconds()/1800)
for area in areas:
    ts=sorted(r['dt'] for r in rows if r['area']==area)
    assert len(ts)==expected
    assert all(b-a==timedelta(minutes=30) for a,b in zip(ts,ts[1:]))
summary=[]
for area in areas:
    ar=[r for r in rows if r['area']==area]
    for label in ['all','before_2025-03-14','2025-03-14_to_2026-03-13','from_2026-03-14','2026-06']:
        group=[r for r in ar if label=='all' or (r['ts'].startswith(label) if label=='2026-06' else regime(r['ts'])==label)]
        summary.append(dict(area=area,period=label,**summarize(group)))
with (OUT/'fit_proxy_diagnostics.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)

with ICS.open(encoding='cp932',newline='') as f:
    raw=list(csv.reader(f))
assert raw[-1]==['E']
header=next(r for r in raw if r[0]=='T')
idx=[i for i,v in enumerate(header) if v=='四国']
assert idx[:5]==[19,37,55,73,91]
records=[]
for r in raw:
    if r[0]!='D': continue
    dt=datetime.strptime(r[1],'%Y%m%d')+timedelta(minutes=30*(int(r[2])-1))
    n=number(r[idx[0]])
    state=r[idx[1]]
    if n is not None:
        assert state==('1' if n>0 else '0' if n<0 else '-')
    else:
        assert state==''
    records.append(dict(dt=dt,state=state,imbalance_kwh=n,partition=r[idx[2]]))
assert len(records)==1440 and len({r['dt'] for r in records})==1440
records.sort(key=lambda r:r['dt'])
assert all(b['dt']-a['dt']==timedelta(minutes=30) for a,b in zip(records,records[1:]))
trans=Counter()
for a,b in zip(records,records[1:]):
    if a['state'] in ['0','1','-'] and b['state'] in ['0','1','-']:
        trans[(a['state'],b['state'])]+=1
transition=[]
for state in ['0','1','-']:
    total=sum(v for (a,b),v in trans.items() if a==state)
    transition.append(dict(from_state=state,eligible_pairs=total,counts={b:trans[(state,b)] for b in ['0','1','-']},
                           probabilities={b:trans[(state,b)]/total if total else None for b in ['0','1','-']}))
result=dict(access_date='2026-10-01',timezone='Asia/Tokyo',interval_minutes=30,
            source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [FIT,ICS]},
            fit_rows=len(rows),areas=len(areas),expected_slots_per_area=expected,
            fit_missing_error_total=sum(r['err'] is None for r in rows),
            shikoku_fit=[r for r in summary if r['area']=='四国'],
            ics_shikoku=dict(counts=dict(Counter(r['state'] for r in records)),transitions=transition),
            checks='PASS: source keys, complete timestamp grids, FIT ranges, ICS terminal record, ICS sign/flag agreement',
            scope='Descriptive proxy diagnostics only. No fitted product activation, forecast accuracy claim, revenue or production model change.')
(OUT/'available_data_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
