"""SCIP adapter for cross-solving difficult windows without changing the MILP."""
from types import SimpleNamespace
import numpy as np

def native_milp(c,integrality,bounds,constraints,options):
    from pyscipopt import Model,quicksum
    model=Model();model.hideOutput()
    model.setRealParam('limits/time',float(options['time_limit']))
    model.setRealParam('limits/gap',float(options['mip_rel_gap']))
    model.setRealParam('numerics/feastol',max(1e-9,float(options.get('primal_feasibility_tolerance',1e-9))))
    model.setIntParam('parallel/maxnthreads',1)
    if not options.get('presolve',True):model.setIntParam('presolving/maxrounds',0)
    variables=[model.addVar(name=f'v{i}',vtype='I' if integrality[i] else 'C',lb=float(bounds.lb[i]),ub=float(bounds.ub[i]),obj=float(c[i])) for i in range(len(c))]
    matrix=constraints.A.tocsr()
    for r in range(matrix.shape[0]):
        row=quicksum(float(matrix.data[k])*variables[int(matrix.indices[k])] for k in range(matrix.indptr[r],matrix.indptr[r+1]))
        lo=float(constraints.lb[r]);hi=float(constraints.ub[r])
        if lo==hi:model.addCons(row==lo)
        else:
            if np.isfinite(lo):model.addCons(row>=lo)
            if np.isfinite(hi):model.addCons(row<=hi)
    if 'mip_start_values' in options and any(integrality):
        start=model.createSol()
        for variable,value in zip(variables,options['mip_start_values']):model.setSolVal(start,variable,float(value))
        model.addSol(start,free=True)
    model.optimize();status=str(model.getStatus());best=model.getBestSol()
    x=np.array([model.getSolVal(best,v) for v in variables]) if best is not None else None
    result=SimpleNamespace(status={'optimal':0,'gaplimit':0,'timelimit':1,'infeasible':2,'unbounded':3}.get(status,4),
        message='SCIP '+status,x=x,mip_dual_bound=float(model.getDualbound()))
    model.freeProb();return result
