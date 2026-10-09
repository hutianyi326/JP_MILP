"""Synthetic subproblem checks only; not JP solver/backtest. Writes checks.json."""
from pathlib import Path
import itertools,json,hashlib,re
import numpy as np
from scipy.optimize import linprog
base=Path(__file__).resolve().parent
results={}
# Three hourly-equivalent halfhour energy slots: charge, discharge, boundary states.
def lp(terminal):
    n=3;c=np.zeros(9);c[3]=-10000
    eq=[];rhs=[]
    for t in range(n):
        row=np.zeros(9);row[6+t]=1;row[t]=-1;row[3+t]=1
        if t: row[6+t-1]=-1
        eq.append(row);rhs.append(1 if t==0 else 0)
    if terminal:
        row=np.zeros(9);row[8]=1;eq.append(row);rhs.append(1)
    return linprog(c,A_ub=[[*([1]*6),0,0,0]],b_ub=[1],A_eq=eq,b_eq=rhs,bounds=[(0,0),(0,1),(0,1),(0,1),(0,0),(0,0),(0,1),(0,1),(0,1)],method='highs')
a,b=lp(False),lp(True)
assert a.success and b.success
assert abs(-a.fun-10000)<1e-6 and abs(-b.fun-5000)<1e-6
assert all(min(b.x[t],b.x[3+t])<1e-8 for t in range(3))
results['REV01']={'pass':True,'unclosed_profit':-a.fun,'closed_profit':-b.fun,'closed_first_discharge_MWh':b.x[3], 'method':'reduced LP with feasible mutually exclusive optimum, no JP markets'}
one=1.9-2*.5/.95;two=1.9-2/.95
assert one>=.8 and two<.8
results['REV02']={'pass':True,'single_end_MWh':one,'chained_end_MWh':two}
# Same full-up service across two halfhours, varying baseline permitted.
# p=[-1,1], R=1 => actual PCS=[0,2], E=[2,2,1], bounds[0,4].
p=[-1,1];R=1;e=2;states=[e]
for x in p:
    w=x+R;assert -2<=w<=2;e-=w*.5;states.append(e)
assert all(0<=v<=4 for v in states) and p[0]!=p[1]
results['REV03']={'pass':True,'dynamic_baselines_MW':p,'witness_states_MWh':states,'fixed_baseline_rejects_same_schedule':True,'not_an_optimal_profit_benchmark':True}
bad=0;n=0
for ec,ed,aux,w,D,e in itertools.product([.8,.95,1],[.8,.95,1],[0,.02],[-2,-.1,0,.1,2],[.1,.5,2],[.8,1.9,4,7.2]):
    end=e-D*((w/ed if w>=0 else ec*w)+aux)
    exact=.8-1e-10<=end<=7.2+1e-10
    fast=(e-.8>=D*(w/ed+aux)-1e-10 and e-.8>=D*(ec*w+aux)-1e-10 and 7.2-e>=D*(-ec*w-aux)-1e-10)
    bad+=exact!=fast;n+=1
assert bad==0
results['P6']={'pass':True,'cases':n,'mismatches':bad}
assert 2*.5*(15000-10000)==5000
results['REV07']={'pass':True,'zero_throughput_trading_JPY':5000}
files=[base.parent/'JP_milp_formulation.md',base.parent/'JP_M3_R2_closure.md']
for f in files:
    s=f.read_text(encoding='utf-8');assert s.count('$$')%2==0
    for dest in re.findall(r'\]\(([^)]+)\)',s):
        if not dest.startswith('http'):
            assert (f.parent/dest.split('#')[0]).exists(), (f,dest)
results['document_checks']={'pass':True,'display_delimiters_balanced':True,'local_links_exist':True}
results['not_executed']=['full JP solver','historical backtest','market rule eligibility tests','control hardware tests','window performance benchmark']
results['sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
(base/'checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2))

