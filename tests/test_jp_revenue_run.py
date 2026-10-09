import unittest
from tests.test_jp_milp import fixture
from src.jp_milp.core import solve_window
from src.jp_milp.activation import fcr_states
from project.jp_revenue_20261005.numeric_states import merge_tail_states, recovery_baseline_bounds

class RevenueRunTests(unittest.TestCase):
    def test_recovery_bounds_contain_balanced_physical_baseline(self):
        import random
        from scipy.optimize import brentq
        rng=random.Random(20261005)
        for _ in range(40):
            rows=[];capacities=[]
            for k in range(48):
                w=rng.random()
                rows.append({'states':[{'weight':w,'f':rng.random()},{'weight':1-w,'f':-rng.random()}]})
                capacities.append(2*rng.random())
            def balance(p):
                return sum(s['weight']*(.92*max(-(p+q*s['f']),0)-max(p+q*s['f'],0)/.92) for r,q in zip(rows,capacities) for s in r['states'])
            p=brentq(balance,-2,2)
            lower,upper=recovery_baseline_bounds(rows,2,.92,.92)
            self.assertLessEqual(lower,p+1e-9)
            self.assertGreaterEqual(upper,p-1e-9)

    def test_scip_backend_physical_and_cash_equivalence(self):
        data=fixture('HV_SPOT_FCR',n=52)
        data['solver']['backend']='highspy'
        reference=solve_window(data)
        data['solver']['backend']='scip'
        result=solve_window(data)
        self.assertEqual(result['audit']['status'],'PASS')
        self.assertAlmostEqual(reference['metrics']['objective_jpy'],result['metrics']['objective_jpy'],places=3)

    def test_daily_lv_recovery_no_intraday_arbitrage(self):
        data=fixture('LV_FCR',n=96)
        data['daily_soc_recovery']='CONSTANT_BASELINE_TARGET_50'
        data['solver']['backend']='highspy'
        result=solve_window(data)
        self.assertEqual(result['audit']['status'],'PASS')
        for offset in (0,48):
            rows=result['intervals'][offset:offset+48]
            self.assertLess(max(r['baseline_mw'] for r in rows)-min(r['baseline_mw'] for r in rows),1e-7)
            self.assertAlmostEqual(rows[-1]['soc_end_mwh'],data['asset']['target_mwh'],places=7)
        self.assertGreater(sum(r['capacity_jpy'] for r in result['intervals']),0)

    def test_negligible_tail_merge_preserves_both_activation_means(self):
        original=fcr_states(0,.02,.01,.01,.19,.19,1,1)
        reduced,metadata=merge_tail_states(original)
        self.assertGreater(metadata['merged_states'],0)
        self.assertAlmostEqual(sum(r['weight'] for r in reduced),1,places=12)
        for sign in (1,-1):
            self.assertAlmostEqual(sum(r['weight']*max(sign*r['f'],0) for r in original),sum(r['weight']*max(sign*r['f'],0) for r in reduced),places=12)

if __name__=='__main__':unittest.main()
