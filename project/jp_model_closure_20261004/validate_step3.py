from pathlib import Path
import json,hashlib
here=Path(__file__).resolve().parent
root=here.parents[1]
main=root/"countries/JP/model/JP_milp_formulation.md"
now=main.read_text(encoding="utf-8-sig")
old=(here/"step3_before/JP_milp_formulation.md").read_text(encoding="utf-8-sig")
def section(s,a,b): return s[s.index(a):s.index(b)].strip()
checks={
"section13_preserved":section(now,"## 13.","## 14.")==section(old,"## 13.","## 14."),
"step1_preserved":section(now,"### 14.2.1","### 14.3 ")==section(old,"### 14.2.1","### 14.3 "),
"step2_preserved":section(now,"### 14.3.1","### 14.4 ")==section(old,"### 14.3.1","### 14.4 "),
"step3_confirmed":"### 14.4.1 第3项已确认" in now,
}
w=[0.25,0.5,0.25]
v=[0.5,0.5]
ell=[-0.12,0.02,0.16]
eps=[-0.03,0.03]
mu=sum(x*p for x,p in zip(ell,w))
centered=[x-mu for x in ell]
checks["lfc_centered_zero"]=abs(sum(x*p for x,p in zip(centered,w)))<1e-12
checks["edc_deviation_zero"]=abs(sum(x*p for x,p in zip(eps,v)))<1e-12
# Marginal-preserving monotone or reverse quantile coupling.
def coupling(reverse=False):
    ri=w[:]; rj=v[:]
    mat=[[0.0]*len(v) for _ in w]
    order=list(range(len(v)))
    if reverse: order.reverse()
    i=k=0
    while i<len(w) and k<len(v):
        j=order[k]
        mass=min(ri[i],rj[j])
        mat[i][j]+=mass
        ri[i]-=mass; rj[j]-=mass
        if ri[i]<1e-12: i+=1
        if rj[j]<1e-12: k+=1
    return mat
matrices={
"independent":[[wi*vj for vj in v] for wi in w],
"same_rank":coupling(),
"opposite_rank":coupling(True),
}
results=[]
for name,omega in matrices.items():
    marginal=all(abs(sum(row)-wi)<1e-12 for row,wi in zip(omega,w))
    marginal &= all(abs(sum(omega[i][j] for i in range(len(w)))-v[j])<1e-12 for j in range(len(v)))
    checks["marginals_"+name]=marginal
    for theta in [0,0.5,1]:
        qs,qt,dt,d0=3,5,0.5,0.04
        net=up=down=0.0
        for i,row in enumerate(omega):
            for j,prob in enumerate(row):
                r=qt*(d0+eps[j])+qs*(centered[i]+theta*mu)
                net+=dt*prob*r
                up+=dt*prob*max(r,0)
                down+=dt*prob*max(-r,0)
        expected=dt*(qt*d0+theta*qs*mu)
        passed=abs(net-expected)<1e-12 and abs(up-down-net)<1e-12
        results.append({"coupling":name,"theta":theta,"net_mwh":net,"up_mwh":up,"down_mwh":down,"passed":passed})
checks["joint_net_and_gross_identities"]=all(r["passed"] for r in results)
r=[0.2+0.5,0.2-0.5]
up=0.25*sum(max(x,0) for x in r)
down=0.25*sum(max(-x,0) for x in r)
checks["teaching_example"]=abs(up-0.175)<1e-12 and abs(down-0.075)<1e-12 and abs(up-down-0.1)<1e-12
checks["physics_not_payment"]="物理毛量自动当付费量" in now
out={"date":"2026-10-04","passed":all(checks.values()),"checks":checks,"examples":results,
"scope":"illustrative algebra only; no empirical overlap identification, calibration, solver, or independent review",
"sha256":hashlib.sha256(main.read_bytes()).hexdigest()}
(here/"step3_validation.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"passed":out["passed"],"checks":checks},ensure_ascii=False))
raise SystemExit(0 if out["passed"] else 1)

