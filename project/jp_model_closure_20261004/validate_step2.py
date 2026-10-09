from pathlib import Path
import json,hashlib
here=Path(__file__).resolve().parent
root=here.parents[1]
main=root/"countries/JP/model/JP_milp_formulation.md"
now=main.read_text(encoding="utf-8-sig")
old=(here/"step2_before/JP_milp_formulation.md").read_text(encoding="utf-8-sig")
def section(text,a,b): return text[text.index(a):text.index(b)].strip()
checks={
"section13_preserved":section(now,"## 13.","## 14.")==section(old,"## 13.","## 14."),
"confirmed_step1_preserved":section(now,"### 14.2.1","### 14.3 ")==section(old,"### 14.2.1","### 14.3 "),
"step2_A_present":"### 14.3.1 第2项已确认A" in now,
"no_free_inner_reduction":"不能只写$q_p\\le C_p$" in now,
"single_price_formula":"1000\\,\\pi^{comp,eff}_tR_b" in now,
"not_production_certification":"未完成具体电站能力认证" in now,
}
# Synthetic menu rows check selection and units, not actual admissibility.
menu=[(3.0,5.0),(5.0,3.0),(4.0,4.0)]
examples=[]
for i in range(-1,len(menu)):
    selected=[int(j==i) for j in range(len(menu))]
    qs=sum(row[0]*y for row,y in zip(menu,selected))
    qt=sum(row[1]*y for row,y in zip(menu,selected))
    R=sum(max(row)*y for row,y in zip(menu,selected))
    fee=1000*6*R
    examples.append({"selection":i,"q_s":qs,"q_t":qt,"R":R,"fee_jpy_30min":fee,
                     "passed":R==max(qs,qt) and sum(selected)<=1})
checks["menu_max_and_no_bid"]=all(x["passed"] for x in examples)
checks["3_5_example_30000"]=examples[1]["fee_jpy_30min"]==30000
checks["already_MW_price_same_result"]=6000*5==1000*6*5
# Basic input contract gate cannot certify physics; missing evidence blocks.
def basic_gate(qs,qt,verified,domain,price):
    return qs>0 and qt>0 and verified and domain and price is not None
checks["reject_missing_verification"]=not basic_gate(3,5,False,True,6)
checks["reject_missing_domain"]=not basic_gate(3,5,True,False,6)
checks["reject_missing_price"]=not basic_gate(3,5,True,True,None)
checks["reject_single_product_row"]=not basic_gate(0,5,True,True,6)
result={"date":"2026-10-04","passed":all(checks.values()),"checks":checks,"examples":examples,
        "scope":"document preservation and illustrative algebra/input checks only; no actual capacity menu certification, no solver, no independent review",
        "sha256":hashlib.sha256(main.read_bytes()).hexdigest()}
(here/"step2_validation.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"passed":result["passed"],"checks":checks},ensure_ascii=False))
raise SystemExit(0 if result["passed"] else 1)

