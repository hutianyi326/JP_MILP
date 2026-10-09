"""Full input preflight plus a short physical solve, not an EV revenue rerun."""
from pathlib import Path
import sys,json
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from project.jp_revenue_20261005.run_scenarios import prepare,assemble_window,PACK
from project.jp_ev_offline_20261005.binding import overlay
from src.jp_milp.config import require,digest
from src.jp_milp.core import solve_window
from src.jp_milp.inputs import validate
from src.jp_milp.rolling import code_identity

def main():
 prepared,a,runtime,events,skeleton,budget,terminal=prepare('LV_FCR')
 full_preflight=validate(skeleton)
 quote={r['start']:r['offline_quote'] for r in prepared['intervals']}
 for b in skeleton['capacity_blocks']:
  require(b['market_product']=='F_OFFLINE' and len(b['intervals'])==quote[b['intervals'][0]]['native_halfhours'],'Wrong offline native block')
  for t,p in b['price_jpy_mw_30min'].items():require(p==(quote[t]['price_jpy_mw_30min'] if b['market_enabled'] else 0.),'Wrong offline price')
 old=json.loads((PACK/'regional_prepared.json').read_text(encoding='utf-8'))
 hv=prepare('HV_SPOT_FCR')[0];require(hv==old,'HV ordinary input changed')
 old_f=[r['capacity_price']['fcr'] for r in old['intervals']]
 changed=sum(r['capacity_price']['fcr']!=p for r,p in zip(prepared['intervals'],old_f))
 require(changed>0,'EV still uses ordinary F')
 cprepared=prepare('HV_SPOT_S1_T1')[0];require(cprepared==old,'HV composite input changed')
 damaged=deepcopy(prepared);damaged['intervals'].pop()
 try:overlay(damaged,events)
 except ValueError:missing_rejected=True
 else:raise ValueError('Missing offline coverage silently allowed')
 start='2026-08-02T00:00:00+09:00';end='2026-08-04T00:00:00+09:00'
 data=assemble_window(prepared,a,runtime,events,'LV_FCR',start,end,budget,terminal)
 preflight=validate(data);out=solve_window(data,start,end,formal_end='2026-08-31T00:00:00+09:00')
 require(out['audit']['status']=='PASS','Physical audit failed')
 require(any(out['orders'][b['id']]['common']>0 for b in data['capacity_blocks']),'Short solve must exercise a new positive offline order')
 require(sum(x['efc'] for x in out['intervals'])>0,'Short solve must exercise physical activation')
 for b in data['capacity_blocks']:
  if not b['market_enabled']:require(out['orders'][b['id']]['common']==0,'No-quote block has positive capacity')
 before=json.loads((ROOT/'outputs/JP/revenue_20261005_v10/LV_FCR/manifest.json').read_text(encoding='utf-8'))['identity']
 require(before['source_metadata']!=prepared['metadata'],'Old EV identity can still resume')
 result=dict(status='PASS',scope='Offline full-input binding and Aug2-3 short physics solve with positive new capacity; not formal revenue',
  solver_code_sha256=code_identity(),verification_code_sha256=__import__('hashlib').sha256(Path(__file__).read_bytes()).hexdigest(),
  formal_halfhours=11616,observation_halfhours=48,native_blocks=len(skeleton['capacity_blocks']),
  unavailable_native_blocks=sum(not b['market_enabled'] for b in skeleton['capacity_blocks']),
  changed_ev_price_halfhours=changed,ordinary_hv_input_unchanged=True,composite_hv_input_unchanged=True,
  missing_coverage_rejected=missing_rejected,old_ev_resume_identity_changed=True,
  full_preflight=full_preflight,preflight=preflight,short_solve_audit=out['audit'],short_solve_seconds=out['metrics']['seconds'],
  short_solve_capacity_cash_jpy=sum(x['capacity_jpy'] for x in out['intervals']),short_solve_efc=sum(x['efc'] for x in out['intervals']),
  august_first_quote=quote['2026-08-01T00:00:00+09:00'],current_binding_metadata=prepared['metadata']['ev_offline_binding'])
 path=Path(__file__).parent/'validation.json';path.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k not in ('current_binding_metadata','august_first_quote','short_solve_audit')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
