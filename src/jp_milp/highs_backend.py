"""Native HiGHS adapter with explicit option validation and one worker thread."""
from types import SimpleNamespace
import numpy as np

def native_milp(c,integrality,bounds,constraints,options):
    import highspy
    h=highspy.Highs();h.setOptionValue('output_flag',False)
    zeros=options.get('mip_start_zero_indices',[])
    for key,val in {**options,'threads':1}.items():
        if key in ('mip_start_zero_indices','mip_start_values'):continue
        if key=='presolve':val='on' if val else 'off'
        if h.setOptionValue(key,val)==highspy.HighsStatus.kError:raise ValueError('Unsupported HiGHS option: '+key)
    lp=highspy.HighsLp();lp.num_col_=len(c);lp.num_row_=constraints.A.shape[0]
    lp.col_cost_=np.asarray(c);lp.col_lower_=bounds.lb;lp.col_upper_=bounds.ub
    lp.row_lower_=constraints.lb;lp.row_upper_=constraints.ub
    lp.integrality_=[highspy.HighsVarType.kInteger if i else highspy.HighsVarType.kContinuous for i in integrality]
    matrix=constraints.A.tocsc();lp.a_matrix_.format_=highspy.MatrixFormat.kColwise
    lp.a_matrix_.start_=matrix.indptr;lp.a_matrix_.index_=matrix.indices;lp.a_matrix_.value_=matrix.data
    if h.passModel(lp)==highspy.HighsStatus.kError:raise ValueError('Native HiGHS model rejected')
    if 'mip_start_values' in options and any(integrality):
        seed=highspy.HighsSolution();seed.col_value=options['mip_start_values'];seed.value_valid=True;h.setSolution(seed)
    elif zeros and any(integrality):
        h.setSolution(len(zeros),np.asarray(zeros,dtype=np.int32),np.zeros(len(zeros)))
    h.run();status=h.getModelStatus();solution=h.getSolution();info=h.getInfo()
    mapping={highspy.HighsModelStatus.kOptimal:0,highspy.HighsModelStatus.kTimeLimit:1,
             highspy.HighsModelStatus.kInfeasible:2,highspy.HighsModelStatus.kUnbounded:3}
    feasible=solution.value_valid and (status==highspy.HighsModelStatus.kOptimal or info.primal_solution_status==highspy.SolutionStatus.kSolutionStatusFeasible)
    return SimpleNamespace(status=mapping.get(status,4),x=np.array(solution.col_value) if feasible else None,
        message=h.modelStatusToString(status),mip_dual_bound=info.mip_dual_bound if any(integrality) else info.objective_function_value)
