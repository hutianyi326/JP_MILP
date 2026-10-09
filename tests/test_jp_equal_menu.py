import unittest
from copy import deepcopy
from tests.test_jp_milp import fixture,open_gates
from src.jp_milp.core import solve_window,equal_menu_grid
from src.jp_milp.config import Asset

class EqualMenuTests(unittest.TestCase):
    def test_exact_objective_and_audit(self):
        data=fixture('HV_SPOT_S1_T1',n=52)
        low,high=Asset(**data['asset']).net_bounds
        for b in data['capacity_blocks']:
            template=b['candidates'][0];b['candidates']=[]
            for q in (1.,2.,3.,4.):
                c=deepcopy(template);c.update(id=str(q),s=q,t=q,common=q,domain=[])
                for t in b['intervals']:
                    for sense,rhs in [('<=',high-q),('>=',low+q)]:
                        c['domain'].append(dict(sense=sense,rhs=rhs,terms=[dict(interval=t,variable='baseline',coefficient=1.)]))
                b['candidates'].append(c)
        ordinary=solve_window(data)
        data['compact_equal_menu']=True;compact=solve_window(data)
        self.assertAlmostEqual(ordinary['metrics']['objective_jpy'],compact['metrics']['objective_jpy'],places=5)
        self.assertEqual(compact['audit']['status'],'PASS')
        self.assertLess(compact['metrics']['integers'],ordinary['metrics']['integers'])
        bad=deepcopy(data['capacity_blocks'][0]);bad['candidates'][0]['domain'][0]['rhs']-=.1
        self.assertIsNone(equal_menu_grid(bad,Asset(**data['asset'])))

if __name__=='__main__':unittest.main()
