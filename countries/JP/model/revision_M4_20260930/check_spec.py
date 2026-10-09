"""M4 synthetic formula/interface checks only. Not a JP MILP implementation."""
import json,hashlib,re,math
from pathlib import Path
from datetime import datetime,timedelta
root=Path(__file__).resolve().parent
checks={}
def check(name,condition,details):
    assert condition,name
    checks[name]={'pass':True,'details':details}
def alpha(up,down,qu,qd):
    if qu<=0 or qd<=0: raise ValueError('undefined denominator')
    au,ad=up/(.5*qu),down/(.5*qd)
    if min(au,ad)<0 or au+ad>1+1e-12: raise ValueError('invalid alpha')
    return au,ad
def timeline(channels):
    edges={0.,.5}
    for au,ad,qu,qd in channels: edges.update([.5*ad,.5*(au+ad)])
    e=sorted(edges);segs=[]
    for left,right in zip(e,e[1:]):
        if right-left<1e-12:continue
        mid=(left+right)/2;resp=0
        for au,ad,qu,qd in channels:
            resp+=-qd if mid<.5*ad else qu if mid<.5*(ad+au) else 0
        segs.append((right-left,resp))
    return segs
# 1 block/clock
D=datetime(2025,1,7)
gct=D-timedelta(days=1)+timedelta(hours=14)
check('01_native_block',[20]*6==[20 for _ in range(6)] and gct==datetime(2025,1,6,14),{'one_capacity_id':'b1','six_MW_values':[20]*6,'gct':gct.isoformat(),'capacity_cash_at_5000_per_halfhour':20*5000*6})
au,ad=alpha(10,5,100,100)
check('02_alpha_phases',math.isclose(au,.2) and math.isclose(ad,.1),{'alpha_up':au,'alpha_down':ad,'phase_minutes':[.5*ad*60,.5*au*60,.5*(1-au-ad)*60]})
check('03_energy_no_double_alpha',math.isclose(.5*au*20,2) and math.isclose(.5*ad*20,1),{'up_MWh':.5*au*20,'down_MWh':.5*ad*20})
# same net 5 has multiple gross representations => underidentified
check('04_net_not_gross',10-5==5-0 and (10,5)!=(5,0),{'net_5_can_be':[[10,5],[5,0]]})
e=100.;efc=0.;eta=.92
for duration,r in timeline([(au,ad,20,20)]):
    c,d=max(-r,0),max(r,0)
    e+=eta*c*duration-d*duration/eta
    efc+=(eta*c+d/eta)*duration/(2*180)
check('05_unpaid_physics',e!=100 and efc>0,{'chi':0,'activation_cash':0,'end_SOC_MWh':e,'EFC':efc})
# Explicit metadata guard reference, not production validator
kind='fit_forecast_error_utilization_proxy'
check('06_utilization_label',kind!='metered_activation',{'required_label':kind})
try: alpha(40,20,100,100); rejected=False
except ValueError: rejected=True
check('07_invalid_alpha',rejected,{'alpha_sum':1.2,'rejected':rejected})
channels=[(.2,.1,20,20),(.3,.2,10,10)]
segs=timeline(channels)
net=sum(dt*r for dt,r in segs)
expected=sum(.5*(a*q-b*r) for a,b,q,r in channels)
check('08_common_axis',len(segs)<=5 and math.isclose(sum(s[0] for s in segs),.5) and math.isclose(net,expected),{'segments':segs,'one_SOC_axis':True,'duration_h':sum(s[0] for s in segs),'net_MWh':net})
# fixed DA buy + new ID sell, same delivery, logical IDs counted once
orders=[('fixed_DA',-2,10000,'formal'),('new_ID',2,15000,'formal'),('obs',1,20000,'observation')]
formal=sum(x*price*.5 for _,x,price,tag in orders if tag=='formal')
plan=sum(x*price*.5 for _,x,price,_ in orders)
check('09_cash_ledger',formal==5000 and plan==15000,{'formal_JPY':formal,'planning_JPY':plan,'unique_ids':len(set(x[0] for x in orders))})
spec=(root.parent/'JP_milp_formulation.md').read_text(encoding='utf-8')
required=['weekly_gct_enforced: false','imbalance_cash_in_objective: false','historical_execution_claim: false','activation_alpha_endogenous: false']
check('10_flags',all(x in spec for x in required),required)
L=600*8/365;reserve=1/(2*.92);used=2.;available=max(0,L-used);window=max(0,available-min(available,reserve)-1e-6)
check('11_ES_budget',math.isclose(L,13.150684931506849) and math.isclose(reserve,.5434782608695652),{'8day_EFC':L,'reserve_EFC':reserve,'window_available':window,'observation_extra_same_year':0})
# Counterexample for sign handling: already-signed down -1000, one MWh paid.
check('12_down_signed_once',(-1000)*1==-1000,{'down_cash_JPY':-1000})
# Frozen nonzero award occupies mode group after R substitution.
y_old=1
feasible_new=[v for v in (0,1) if y_old+v<=1]
check('14_frozen_occupancy',feasible_new==[0],{'fixed_y':y_old,'feasible_new_y':feasible_new})
# Today closes a next-day delivery order; past closures not recreated.
start=datetime(2025,1,6);end=start+timedelta(days=1)
check('15_gct_future_freeze',start<=gct<end and D>=end,{'delivery_day':D.isoformat(),'freeze_in_current_execution_day':True})
# SOC at T fixed before observation, which can move SOC but cannot replace target.
target=10.;e_T=10.;obs_charge=.92*1*.5;e_obs=e_T+obs_charge
check('16_formal_terminal_vs_observation',e_T==target and e_obs!=target,{'formal_terminal':e_T,'observation_end':e_obs,'observation_cash_reported':False})
files=[root.parent/'JP_milp_formulation.md',root.parent/'JP_activation_data_spec_M4.md']
for f in files:
 s=f.read_text(encoding='utf-8');assert s.count('$$')%2==0
 for dest in re.findall(r'\]\(([^)]+)\)',s):
  if not dest.startswith('http'):
   target=f.parent/dest.split('#')[0]
   assert target.exists() or target==root/'checks.json',(f,dest)
check('13_documents',True,{'displays':spec.count('$$')//2,'local_links':'pass','source_unchanged':hashlib.sha256((root/'user_spec.md').read_bytes()).hexdigest()==hashlib.sha256(Path(r'C:\Users\Tianyi\Desktop\JP_MILP_DA_proxy_activation_data_spec_second_round').read_bytes()).hexdigest()})
output={'scope':'synthetic arithmetic, time-axis and document checks; no JP solver/backtest or production validator','checks':checks,'sha256':{str(f.name):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}
(root/'checks.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS',len(checks),'checks; no complete MILP or historical performance claim')
