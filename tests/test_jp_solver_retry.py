"""Presolve recheck must preserve constraints and the total solver budget."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from src.jp_milp.linear import Matrix
from src.jp_milp.config import Solver


class SolverRetryTests(unittest.TestCase):
    def test_invalid_polish_cannot_replace_valid_incumbent(self):
        matrix=Matrix();x=matrix.var('x',0,1,1);y=matrix.var('y',0,2)
        matrix.row(x+y,hi=2)
        original=SimpleNamespace(status=0,x=np.array([1.,1.]),message='optimal',mip_dual_bound=-2.)
        invalid=SimpleNamespace(status=0,x=np.array([1.,100.]),message='optimal',mip_dual_bound=-101.)
        with patch('src.jp_milp.linear.milp',side_effect=[original,invalid]):
            vector,metrics=matrix.solve(x+y,Solver())
        self.assertEqual(list(vector),[1.,1.]);self.assertFalse(metrics['continuous_polish']['accepted'])

    def test_infeasible_presolve_recheck_uses_identical_problem(self):
        matrix=Matrix();x=matrix.var('x',0,1);matrix.row(x,lo=.25)
        failed=SimpleNamespace(status=2,x=None,message='infeasible')
        solved=SimpleNamespace(status=0,x=np.array([1.]),message='optimal',mip_dual_bound=-1.)
        with patch('src.jp_milp.linear.milp',side_effect=[failed,solved]) as call:
            vector,metrics=matrix.solve(x,Solver(time_limit_seconds=10))
        first,second=[c.kwargs for c in call.call_args_list]
        for key in ('c','bounds','constraints','integrality'):
            self.assertIs(first[key],second[key])
        self.assertFalse(second['options']['presolve'])
        self.assertLessEqual(second['options']['time_limit'],10)
        self.assertEqual(second['options']['mip_feasibility_tolerance'],1e-9)
        self.assertEqual(len(metrics['attempts']),2);self.assertEqual(vector[0],1.)

    def test_genuine_infeasibility_still_rejected(self):
        matrix=Matrix();x=matrix.var('x',0,1)
        failed=SimpleNamespace(status=2,x=None,message='infeasible')
        with patch('src.jp_milp.linear.milp',return_value=failed) as call:
            with self.assertRaises(ValueError):matrix.solve(x,Solver())
        self.assertEqual(call.call_count,2)


if __name__=='__main__':unittest.main()
