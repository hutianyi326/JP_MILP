"""Scope and historical-boundary tests for the Kyushu LV extension."""
import unittest
from unittest.mock import patch
from src.jp_milp.scheduling import capacity_clock
from src.jp_milp.budget import common_coverage_budget

class KyushuScope(unittest.TestCase):
 def test_week_gate_and_reform(self):
  cases=[('2025-12-01T00:00:00+09:00','2025-11-25T14:00:00+09:00',6),
   ('2025-12-06T00:00:00+09:00','2025-12-02T14:00:00+09:00',6),
   ('2026-01-03T00:00:00+09:00','2025-12-30T14:00:00+09:00',6),
   ('2026-03-13T21:00:00+09:00','2026-03-03T14:00:00+09:00',6),
   ('2026-03-14T00:00:00+09:00','2026-03-13T14:00:00+09:00',1),
   ('2026-09-01T00:00:00+09:00','2026-08-31T14:00:00+09:00',1)]
  for delivery,gate,n in cases:
   actual,result,size=capacity_clock(delivery)
   self.assertEqual(actual.isoformat(),gate);self.assertEqual(size,n);self.assertEqual(result.hour,15)
 def test_year_budget_separate(self):
  from datetime import datetime,timedelta
  t=datetime.fromisoformat('2025-12-01T00:00:00+09:00');formal=[]
  while t.isoformat()<'2026-09-01T00:00:00+09:00':formal.append(t.isoformat());t+=timedelta(minutes=30)
  self.assertEqual(len(formal),13152)
  budgets=common_coverage_budget(formal,[t.isoformat()],600)['annual_budgets_efc']
  self.assertAlmostEqual(budgets['2025'],600*31/365)
  self.assertAlmostEqual(budgets['2026'],600*243/365)

 def test_daily_decomposition_future_orders_keep_global_clock(self):
  from tests.test_jp_milp import fixture
  from src.jp_milp.core import solve_window
  from project.jp_kyushu_lv_20261006.daily_solver import solve_window as daily
  from datetime import timedelta
  from src.jp_milp.config import timestamp
  d=fixture('LV_FCR',n=96);d['daily_soc_recovery']='CONSTANT_BASELINE_TARGET_50';d['solver']['backend']='highspy'
  for block in d['capacity_blocks']:block['grid_mw']=1.
  start=d['intervals'][0]['start'];end=(timestamp(start)+timedelta(days=2)).isoformat()
  original=solve_window(d,start,end,d['asset']['initial_mwh'],{}, {},end)
  result=daily(d,start,end,d['asset']['initial_mwh'],{}, {},end)
  self.assertIn('daily_decomposition',result['metrics'])
  self.assertGreater(sum(r['capacity_jpy'] for r in result['intervals'][48:]),0)
  self.assertAlmostEqual(original['metrics']['objective_jpy'],result['metrics']['objective_jpy'],places=3)
  self.assertGreaterEqual(result['metrics']['bound_jpy']+.01,original['metrics']['objective_jpy'])
  self.assertEqual(result['audit']['status'],'PASS')

 def test_binding_annual_coupling_falls_back_to_full_mip(self):
  from tests.test_jp_milp import fixture
  from src.jp_milp.core import solve_window
  from project.jp_kyushu_lv_20261006.daily_solver import solve_window as daily
  from datetime import timedelta
  from src.jp_milp.config import timestamp
  # First day has already closed; two subsequent open days independently use
  # the same annual allowance, so their concatenation must trigger fallback.
  d=fixture('LV_FCR',n=144);d['daily_soc_recovery']='CONSTANT_BASELINE_TARGET_50';d['solver']['backend']='highspy'
  for block in d['capacity_blocks']:block['grid_mw']=1.
  d['annual_budgets_efc']={'2026':.03}
  start=d['intervals'][0]['start'];end=(timestamp(start)+timedelta(days=3)).isoformat()
  with patch('project.jp_kyushu_lv_20261006.daily_solver.full_solve',wraps=solve_window) as wrapped:
   result=daily(d,start,end,d['asset']['initial_mwh'],{}, {},end)
  self.assertNotIn('daily_decomposition',result['metrics'])
  self.assertGreaterEqual(wrapped.call_count,4)
  self.assertLessEqual(sum(r['efc'] for r in result['intervals']),.03+1e-6)

 def test_daily_contradictory_bound_not_hidden_by_other_day(self):
  from tests.test_jp_milp import fixture
  from src.jp_milp.core import solve_window
  from project.jp_kyushu_lv_20261006.daily_solver import solve_window as daily
  from datetime import timedelta
  from src.jp_milp.config import timestamp
  d=fixture('LV_FCR',n=96);d['daily_soc_recovery']='CONSTANT_BASELINE_TARGET_50';d['solver']['backend']='highspy'
  for b in d['capacity_blocks']:b['grid_mw']=1.
  start=d['intervals'][0]['start'];end=(timestamp(start)+timedelta(days=2)).isoformat()
  calls=[]
  def tampered(*args,**kwargs):
   r=solve_window(*args,**kwargs);calls.append(len(args[0]['intervals']))
   if len(args[0]['intervals'])==48:r['metrics']['bound_jpy']+=-9 if len(calls)==1 else 9
   return r
  with patch('project.jp_kyushu_lv_20261006.daily_solver.full_solve',side_effect=tampered):
   r=daily(d,start,end,d['asset']['initial_mwh'],{}, {},end)
  self.assertEqual(calls,[48,48,96]);self.assertNotIn('daily_decomposition',r['metrics'])

 def test_daily_decomposition_cross_year_and_observation_tail(self):
  from tests.test_jp_historical import historical_fixture
  from project.jp_kyushu_lv_20261006.daily_solver import solve_window as daily
  from src.jp_milp.config import timestamp
  from datetime import timedelta
  for start,days,formal_end in [('2025-12-30T00:00:00+09:00',7,'2026-01-06T00:00:00+09:00'),
                              ('2026-08-31T00:00:00+09:00',2,'2026-09-01T00:00:00+09:00')]:
   d=historical_fixture(start,days,scenario='LV_FCR');d['daily_soc_recovery']='CONSTANT_BASELINE_TARGET_50'
   d['solver']['backend']='highspy';d['annual_budgets_efc']={'2025':100.,'2026':100.}
   for b in d['capacity_blocks']:b['grid_mw']=1.
   end=(timestamp(start)+timedelta(days=days)).isoformat()
   r=daily(d,start,end,d['asset']['initial_mwh'],{}, {},formal_end)
   self.assertEqual(r['audit']['status'],'PASS');self.assertEqual(len(r['intervals']),48*days)
   self.assertEqual(r['budgets']['2025']['limit'],100.);self.assertEqual(r['budgets']['2026']['limit'],100.)
   self.assertAlmostEqual(r['intervals'][-1]['soc_end_mwh'],d['asset']['target_mwh'],places=7)

if __name__=='__main__':unittest.main()
