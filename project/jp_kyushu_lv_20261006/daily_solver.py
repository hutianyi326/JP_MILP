"""Certified LV day decomposition; fall back when annual coupling is binding.

Each day's EFC <= the original annual window allowance is necessary for a
global feasible solution because EFC is nonnegative. Thus the sum of daily
dual bounds is a global upper bound. A concatenated incumbent is accepted
only after checking the original annual coupling and full-window audit.
"""
from copy import deepcopy
from datetime import timedelta
from math import fsum,isfinite
from src.jp_milp.config import require,timestamp,Asset
from src.jp_milp.core import solve_window as full_solve,allowance
from src.jp_milp.audit import audit_window
from src.jp_milp.inputs import validate

def solve_window(data,start,end,soc,frozen,used,formal_end,incumbent=None):
 validate(data);a=Asset(**data['asset']);first=timestamp(start);last=timestamp(end)
 supported=(data['scenario']=='LV_FCR' and data.get('daily_soc_recovery')=='CONSTANT_BASELINE_TARGET_50'
  and first.hour==last.hour==first.minute==last.minute==0
  and all(len({t[:10] for t in b['intervals']})==1 and all(sum(s['hours'] for s in p['segments'])<=.5 for p in b['services']) for b in data['capacity_blocks'])
  and all(len({t[:10] for t in o['weights']})==1 for o in data['spot_orders']))
 if not supported:return full_solve(data,start,end,soc,frozen,used,formal_end,incumbent)
 budgets=allowance(data,used,last,formal_end);parts=[];now=first
 terminal_year=(timestamp(formal_end)-timedelta(minutes=30)).year
 while now<last:
  next_day=now+timedelta(days=1);local=deepcopy(data)
  local['intervals']=[r for r in data['intervals'] if now<=timestamp(r['start'])<next_day]
  require(len(local['intervals'])==48,'Decomposition needs whole days')
  local['spot_orders']=[o for o in data['spot_orders'] if next(iter(o['weights']))[:10]==now.date().isoformat()]
  local['capacity_blocks']=[b for b in data['capacity_blocks'] if b['intervals'][0][:10]==now.date().isoformat()]
  ids={x['id'] for x in local['spot_orders']+local['capacity_blocks']}
  local_frozen={k:v for k,v in frozen.items() if k in ids};local['initial_frozen']=local_frozen
  # Undo ONLY the local allowance helper's engineering reserve and roundoff
  # margin so its returned allowance equals the original global allowance.
  local['annual_budgets_efc']={y:b['allowance']+(1/(2*a.eta_discharge) if int(y)==terminal_year and next_day<timestamp(formal_end) else 0.)+1e-6 for y,b in budgets.items()}
  expected=allowance(local,{},next_day,formal_end)
  require(all(abs(expected[y]['allowance']-b['allowance'])<1e-8 for y,b in budgets.items()),'Local/global allowance mismatch')
  hint=None
  if incumbent is not None:
   hint={**incumbent,'orders':{k:v for k,v in incumbent['orders'].items() if k in ids},
    'intervals':[r for r in incumbent['intervals'] if now<=timestamp(r['start'])<next_day],
    'states':[r for r in incumbent['states'] if now<=timestamp(r['interval'])<next_day],
    'witnesses':[r for r in incumbent['witnesses'] if r['block'] in ids]}
   if len(hint['intervals'])!=48 or set(hint['orders'])!=ids:hint=None
  part=full_solve(local,now.isoformat(),next_day.isoformat(),soc if now==first else a.target_mwh,local_frozen,{},formal_end,hint,decision_start=start)
  parts.append(part);now=next_day
 rows=[r for p in parts for r in p['intervals']]
 annual={y:fsum(r['efc'] for r in rows if r['start'][:4]==y) for y in budgets}
 if any(annual[y]>budgets[y]['allowance']+1e-8 for y in budgets):
  return full_solve(data,start,end,soc,frozen,used,formal_end,incumbent)
 # Never manufacture a fixed-integer LP certificate. Integer components need
 # an actually accepted polish; integer-free components are already LP solves.
 certified=lambda m: ((m.get('continuous_polish') or {}).get('status')==0 and (m.get('continuous_polish') or {}).get('accepted') is True) if m['integers'] else m['status']==0
 if not all(certified(p['metrics']) for p in parts):
  return full_solve(data,start,end,soc,frozen,used,formal_end,incumbent)
 metrics=[p['metrics'] for p in parts]
 if not all(m['bound_jpy'] is not None and isfinite(m['bound_jpy']) and isfinite(m['objective_jpy']) for m in metrics):
  return full_solve(data,start,end,soc,frozen,used,formal_end,incumbent)
 if not all(m['bound_jpy']>=m['objective_jpy']-(1.+1e-8*max(abs(m['bound_jpy']),abs(m['objective_jpy']))) for m in metrics):
  return full_solve(data,start,end,soc,frozen,used,formal_end,incumbent)
 reported_primal=fsum(m['objective_jpy'] for m in metrics);upper=fsum(m['bound_jpy'] for m in metrics)
 primal=fsum(r['total_jpy'] for r in rows)+data['terminal_value_jpy_mwh']*(rows[-1]['soc_end_mwh']-a.target_mwh)
 require(abs(primal-reported_primal)<=.01,'Original objective differs from daily sum')
 require(upper>=primal-(1.+1e-8*max(abs(primal),abs(upper))),'Inconsistent summed upper bound')
 combined={**parts[0],'intervals':rows,'states':[s for p in parts for s in p['states']],
  'witnesses':[w for p in parts for w in p['witnesses']],
  'orders':{k:v for p in parts for k,v in p['orders'].items()},
  'disabled_new_blocks':{k:v for p in parts for k,v in p['disabled_new_blocks'].items()},
  'budgets':budgets,'start':start,'end':end,'frozen_input':frozen,
  'metrics':dict(status=max(m['status'] for m in metrics),backend=data['solver']['backend'],
   message='Certified daily MILPs, original annual coupling and full-window audit checked',
   objective_jpy=primal,bound_jpy=upper,gap=max(0.,upper-primal)/max(abs(primal),1e-10),
   seconds=fsum(m['seconds'] for m in metrics),variables=sum(m['variables'] for m in metrics),
   integers=sum(m['integers'] for m in metrics),rows=sum(m['rows'] for m in metrics),
   continuous_polish=dict(status=0,accepted=True,message='Concatenated daily certificates checked against original annual coupling'),
   daily_decomposition=dict(proof='NONNEGATIVE_EFC_NECESSARY_DAY_BOUND_PLUS_ORIGINAL_COUPLING_FEASIBILITY',annual_efc=annual,days=len(parts),components=metrics,decision_start=start,
    summed_bound_roundoff_jpy=fsum(max(0.,m['objective_jpy']-m['bound_jpy']) for m in metrics)))}
 require(set(combined['orders'])=={x['id'] for x in data['spot_orders']+data['capacity_blocks']},'Order set changed in decomposition')
 require([r['start'] for r in rows]==[r['start'] for r in data['intervals']],'Delivery chronology changed')
 combined['audit']=audit_window(data,combined)
 require(combined['audit']['status']=='PASS','Decomposed incumbent failed original audit')
 return combined
