from pathlib import Path
from itertools import permutations
import json, hashlib
here=Path(__file__).resolve().parent
root=here.parents[1]
paths=["countries/JP/model/JP_milp_formulation.md", "countries/JP/model/JP_activation_data_spec_M4.md"]
texts=[(root/p).read_text(encoding="utf-8-sig") for p in paths]
old=(here/"step1_before/JP_milp_formulation.md").read_text(encoding="utf-8-sig")
def sec13(s): return s[s.index("## 13."):s.index("## 14.")].strip()
checks={"section13_preserved":sec13(texts[0])==sec13(old),
        "confirmed_section_present":"### 14.2.1 已确认方案" in texts[0],
        "state_interface_present":"capacity_scaling_assumption_id" in texts[1]}
rows=[]
for base,q in [(-2,1),(-2,3),(0.3,1),(2,1)]:
    weights=[0.2,0.6,0.2]
    signals=[-1,0,1]
    eta_c,eta_d,dt,e0,aux=0.95,0.92,0.5,10,0.01
    net=[base+q*x for x in signals]
    c=[max(-x,0) for x in net]
    d=[max(x,0) for x in net]
    A=dt*sum(w*eta_c*x for w,x in zip(weights,c))
    B=dt*sum(w*x/eta_d for w,x in zip(weights,d))+aux
    loss=dt*sum(w*((1-eta_c)*ci+(1/eta_d-1)*di) for w,ci,di in zip(weights,c,d))
    increments=[dt*w*(eta_c*ci-di/eta_d)-aux*w for w,ci,di in zip(weights,c,d)]
    passed=all(abs(di-ci-ni)<1e-10 and ci*di==0 for ci,di,ni in zip(c,d,net))
    passed &= loss>=0 and abs(sum(increments)-(A-B))<1e-10
    for order in permutations(range(3)):
        e=e0
        for i in order:
            e+=increments[i]
            passed &= e0-B-1e-10 <= e <= e0+A+1e-10
        passed &= abs(e-(e0+A-B))<1e-10
    rows.append({"baseline_mw":base,"capacity_mw":q,"A_mwh":A,"B_mwh":B,"loss_mwh":loss,"passed":passed})
checks["four_cases_six_orders_each"]=all(r["passed"] for r in rows)
checks["decision_record_exists"]=(here/"step1_decision.md").exists()
out={"date":"2026-10-04","passed":all(checks.values()),"checks":checks,"examples":rows,
     "scope":"algebra and finite illustrative state checks; no solver, no empirical quadrature convergence, no independent review",
     "files":[{"path":p,"sha256":hashlib.sha256((root/p).read_bytes()).hexdigest()} for p in paths]}
(here/"step1_validation.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"passed":out["passed"],"checks":checks},ensure_ascii=False))
raise SystemExit(0 if out["passed"] else 1)

