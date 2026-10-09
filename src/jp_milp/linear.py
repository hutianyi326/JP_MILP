"""Small sparse affine modelling layer around SciPy/HiGHS. No arbitrary big-M."""
from dataclasses import dataclass
from time import perf_counter
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import coo_matrix
from .config import TOL


@dataclass
class Expr:
    terms: dict
    constant: float = 0.

    def __add__(self, other):
        other = expr(other); terms = self.terms.copy()
        for i, value in other.terms.items():
            terms[i] = terms.get(i, 0.)+value
            if terms[i] == 0:
                del terms[i]
        return Expr(terms, self.constant+other.constant)

    __radd__ = __add__

    def __mul__(self, scalar):
        return Expr({i: v*scalar for i, v in self.terms.items() if v*scalar}, self.constant*scalar)

    __rmul__ = __mul__

    def __neg__(self):
        return self*-1

    def __sub__(self, other):
        return self+-expr(other)

    def __rsub__(self, other):
        return expr(other)+-self

    def __truediv__(self, scalar):
        return self*(1/scalar)

    def value(self, vector):
        return self.constant+sum(v*vector[i] for i, v in self.terms.items())


def expr(value):
    return value if isinstance(value, Expr) else Expr({}, float(value))


class Matrix:
    def __init__(self):
        self.lower = []; self.upper = []; self.kinds = []; self.names = []; self.rows = []

    def var(self, name, lo, hi, kind=0):
        if lo > hi:
            raise ValueError('Invalid variable bounds: '+name)
        if lo == hi:
            return expr(lo)
        i = len(self.lower)
        self.lower.append(lo); self.upper.append(hi); self.kinds.append(kind); self.names.append(name)
        return Expr({i: 1.})

    def bounds(self, value):
        e = expr(value)
        return (e.constant+sum(v*(self.lower[i] if v >= 0 else self.upper[i]) for i, v in e.terms.items()),
                e.constant+sum(v*(self.upper[i] if v >= 0 else self.lower[i]) for i, v in e.terms.items()))

    def row(self, value, lo=-np.inf, hi=np.inf, label=''):
        e = expr(value); lo -= e.constant; hi -= e.constant
        if not e.terms:
            if lo > TOL or hi < -TOL:
                raise ValueError('Infeasible constant constraint: '+label)
        else:
            self.rows.append((e.terms, lo, hi, label))

    def conditional(self, value, active, lo=-np.inf, hi=np.inf, label=''):
        low, high = self.bounds(value)
        if np.isfinite(lo):
            self.row(expr(value)+max(0, lo-low)*(1-active), lo=lo, label=label)
        if np.isfinite(hi):
            self.row(expr(value)-max(0, high-hi)*(1-active), hi=hi, label=label)

    def positive(self, value, name):
        low, high = self.bounds(value)
        if low >= 0:
            return expr(value)
        if high <= 0:
            return expr(0)
        p = self.var(name, 0, high); z = self.var(name+'_sign', 0, 1, 1)
        self.row(p-expr(value), lo=0)
        self.row(p-high*z, hi=0)
        self.row(p-expr(value)-(-low)*(1-z), hi=0)
        return p

    def solve(self, objective, solver, warm_values=None):
        solve=milp
        if solver.backend=='highspy':
            from .highs_backend import native_milp
            solve=native_milp
        elif solver.backend=='scip':
            from .scip_backend import native_milp
            solve=native_milp
        objective = expr(objective); n = len(self.lower)
        if not n:
            return np.zeros(0), dict(status=0, variables=0, integers=0, rows=len(self.rows),
                                    seconds=0., objective_jpy=objective.constant, gap=0., bound_jpy=objective.constant)
        rr=[]; cc=[]; vv=[]
        for r, (terms, _, _, _) in enumerate(self.rows):
            for c, v in terms.items():
                rr.append(r); cc.append(c); vv.append(v)
        matrix=coo_matrix((vv, (rr, cc)), shape=(len(self.rows), n)).tocsc()
        cost=np.zeros(n)
        for i, v in objective.terms.items():
            cost[i]=-v
        objective_scale=max(1.,float(np.max(np.abs(cost))))
        cost/=objective_scale
        begin=perf_counter()
        problem=dict(c=cost, integrality=np.array(self.kinds), bounds=Bounds(self.lower, self.upper),
                     constraints=LinearConstraint(matrix, [r[1] for r in self.rows], [r[2] for r in self.rows]))
        options=dict(time_limit=solver.time_limit_seconds, mip_rel_gap=solver.mip_rel_gap,
                                 presolve=solver.presolve,
                                 # Backend feasibility is tighter than our independent
                                 # 1e-6 MWh audit: small state residuals accumulate in SOC.
                                 # SciPy 1.15 forwards these native HiGHS options verbatim.
                                 mip_feasibility_tolerance=1e-9,
                                 primal_feasibility_tolerance=1e-9,
                                 dual_feasibility_tolerance=1e-9,
                                 # Preserve small tail-state weights: HiGHS' 1e-9
                                 # default drops terms material at 100 MW scale.
                                 small_matrix_value=1e-12)
        if solver.backend in ('highspy','scip'):
            options['mip_start_zero_indices']=[i for i,name in enumerate(self.names) if name.endswith(('/grid','/active')) and self.lower[i]==0]
            if warm_values is not None:
                options['mip_start_values']=[warm_values.get(name,max(self.lower[i],min(0.,self.upper[i]))) for i,name in enumerate(self.names)]
        result=solve(**problem, options=options)
        attempts=[dict(presolve=solver.presolve,status=int(result.status),message=result.message)]
        # Fixed floating-point schedules can cause a false presolve infeasibility
        # (reproduced with Shikoku 2026-03-14). Recheck the IDENTICAL matrix with
        # presolve off; never relax constraints, change orders, or extend the budget.
        remaining=solver.time_limit_seconds-(perf_counter()-begin)
        if result.status == 2 and solver.presolve and remaining > 0:
            result=solve(**problem,options={**options,'presolve':False,'time_limit':remaining})
            attempts.append(dict(presolve=False,status=int(result.status),message=result.message))
        if result.status not in (0, 1) or result.x is None or not np.all(np.isfinite(result.x)):
            raise ValueError('No feasible incumbent: '+result.message)
        x=result.x.copy()
        for i, kind in enumerate(self.kinds):
            if kind:
                if abs(x[i]-round(x[i])) > TOL:
                    raise ValueError('Nonintegral incumbent')
                x[i]=round(x[i])
        # Freeze the incumbent integers and polish continuous variables as an LP.
        # MILP crossover residuals can pass a 1e-6 audit yet make tomorrow's fixed
        # orders infeasible at tighter solver tolerances when SOC hits a bound.
        remaining=solver.time_limit_seconds-(perf_counter()-begin)
        polish=None
        def matrix_feasible(candidate):
            if not np.all(np.isfinite(candidate)):return False
            if max(np.max(np.array(self.lower)-candidate),np.max(candidate-np.array(self.upper)))>TOL:return False
            return all(lo-TOL<=sum(v*candidate[i] for i,v in terms.items())<=hi+TOL for terms,lo,hi,_ in self.rows)
        if any(self.kinds) and remaining>0:
            lower=np.array(self.lower,dtype=float);upper=np.array(self.upper,dtype=float)
            for i,kind in enumerate(self.kinds):
                if kind:lower[i]=upper[i]=x[i]
            polished=solve(**{**problem,'integrality':np.zeros(n),'bounds':Bounds(lower,upper)},
                options={**options,'presolve':False,'time_limit':remaining,
                         'primal_feasibility_tolerance':1e-10,'dual_feasibility_tolerance':1e-10})
            polish=dict(status=int(polished.status),message=polished.message)
            if polished.status==0 and polished.x is not None:
                candidate=polished.x.copy()
                for i,kind in enumerate(self.kinds):
                    if kind:candidate[i]=round(candidate[i])
                polish['accepted']=matrix_feasible(candidate)
                if polish['accepted']:x=candidate
            if not matrix_feasible(x) and solver.backend=='highspy':
                remaining=solver.time_limit_seconds-(perf_counter()-begin)
                if remaining>0:
                    retry=solve(**{**problem,'integrality':np.zeros(n),'bounds':Bounds(lower,upper)},
                        options={**options,'presolve':True,'solver':'ipm','time_limit':remaining})
                    polish['ipm_retry']=dict(status=int(retry.status),message=retry.message)
                    if retry.status==0 and retry.x is not None:
                        candidate=retry.x.copy()
                        for i,kind in enumerate(self.kinds):
                            if kind:candidate[i]=round(candidate[i])
                        if matrix_feasible(candidate):x=candidate
            # A failed optional LP polish never replaces the MIP incumbent.
            # Original matrix and independent physical audits remain mandatory.
        if max(np.max(np.array(self.lower)-x), np.max(x-np.array(self.upper))) > TOL:
            raise ValueError('Incumbent violates variable bounds')
        for terms, lo, hi, label in self.rows:
            value=sum(v*x[i] for i, v in terms.items())
            if value < lo-TOL or value > hi+TOL:
                raise ValueError('Incumbent violates constraint '+label)
        primal=objective.value(x)
        raw_bound=getattr(result, 'mip_dual_bound', None)
        bound=-float(raw_bound)*objective_scale+objective.constant if raw_bound is not None and np.isfinite(raw_bound) else None
        return x, dict(status=int(result.status), message=result.message, variables=n,
                       integers=sum(self.kinds), rows=len(self.rows), nnz=len(vv), seconds=perf_counter()-begin,
                       objective_jpy=primal, bound_jpy=bound,
                       gap=max(0., bound-primal)/max(abs(primal), 1e-10) if bound is not None else None,
                       attempts=attempts,continuous_polish=polish,backend=solver.backend,mip_start_supplied=warm_values is not None)
