"""A feasible starting candidate, never a changed market/physical constraint."""
from pathlib import Path
import sys,json,gzip
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from project.jp_revenue_20261005.run_scenarios import prepare,assemble_window
from src.jp_milp.core import solve_window
from src.jp_milp.config import require

def main():
 p,a,r,e,s,b,v=prepare('LV_FCR');folder=ROOT/'outputs/JP/lv_offline_20261005_v1/LV_FCR'
 frozen={};last=None
 for path in sorted((folder/'windows').glob('*.json.gz'))[:237]:
  with gzip.open(path,'rt',encoding='utf-8') as stream:tx=json.load(stream)
  frozen.update(tx['new_frozen']);last=tx
 with gzip.open(folder/'windows/00237.json.gz','rt',encoding='utf-8') as stream:failed=json.load(stream)
 data=assemble_window(p,a,r,e,'LV_FCR','2026-08-26T00:00:00+09:00','2026-08-28T00:00:00+09:00',b,v)
 data['solver'].update(backend='highspy',time_limit_seconds=60)
 ids={x['id'] for x in data['capacity_blocks']+data['spot_orders']}
 fixed={k:v for k,v in frozen.items() if k in ids};adjusted=[]
 for block in data['capacity_blocks']:
  if block['id'] in fixed:continue
  q=failed['window']['orders'][block['id']]['common']
  if q>=block['maximum_mw']-block['grid_mw']/2:
   q-=block['grid_mw'];adjusted.append(block['id'])
  if q<block['minimum_mw']:q=0.
  fixed[block['id']]=dict(f=q,s=0.,t=0.,common=q,candidate_id=None)
 candidate=solve_window(data,soc=last['next_state']['soc'],frozen=fixed,used=last['next_state']['used'],formal_end='2026-08-31T00:00:00+09:00')
 require(candidate['audit']['status']=='PASS','Starting candidate audit failed')
 next_fixed={**frozen,**{k:v for k,v in candidate['orders'].items() if k not in frozen}}
 nxt=assemble_window(p,a,r,e,'LV_FCR','2026-08-27T00:00:00+09:00','2026-08-29T00:00:00+09:00',b,v)
 nxt['solver'].update(backend='highspy',time_limit_seconds=60)
 nids={x['id'] for x in nxt['capacity_blocks']+nxt['spot_orders']}
 nf={k:v for k,v in next_fixed.items() if k in nids}
 for block in nxt['capacity_blocks']:
  nf.setdefault(block['id'],dict(f=0.,s=0.,t=0.,common=0.,candidate_id=None))
 executed=candidate['intervals'][:48]
 next_used=last['next_state']['used'].copy()
 next_used['2026']+=sum(x['efc'] for x in executed)
 continued=solve_window(nxt,soc=executed[-1]['soc_end_mwh'],frozen=nf,used=next_used,formal_end='2026-08-31T00:00:00+09:00')
 require(continued['audit']['status']=='PASS','Starting candidate cannot continue')
 with gzip.open(Path(__file__).parent/'boundary_seed.json.gz','wt',encoding='utf-8') as stream:json.dump(candidate,stream,ensure_ascii=False,allow_nan=False)
 result=dict(status='PASS',classification='HEURISTIC_START_ONLY_NOT_EXECUTED_OR_FINAL_OPTIMUM',adjusted_free_capacity_blocks=adjusted,
  candidate_objective_jpy=candidate['metrics']['objective_jpy'],previous_infeasible_grid_objective_jpy=failed['window']['metrics']['objective_jpy'],
  physical_audit=candidate['audit'],continuation_audit=continued['audit'],continuation_initial_soc_mwh=executed[-1]['soc_end_mwh'],
  continuation_used_efc=next_used,solver_seconds=candidate['metrics']['seconds']+continued['metrics']['seconds'],
  evidence='Only reduces starting guesses by one allowed grid unit; optimizer feasible set and previous frozen obligations unchanged')
 (Path(__file__).parent/'boundary_seed_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
