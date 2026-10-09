from pathlib import Path
import json,re,hashlib
here=Path(__file__).resolve().parent
root=here.parents[1];pkg=here/"step4_input_package"
main=root/"countries/JP/model/JP_milp_formulation.md"
now=main.read_text(encoding="utf-8-sig")
old=(here/"step4_before/JP_milp_formulation.md").read_text(encoding="utf-8-sig")
def sec(s,a,b):return s[s.index(a):s.index(b)].strip()
checks={
"section13_unchanged":sec(now,"## 13.","## 14.")==sec(old,"## 13.","## 14."),
"steps1_3_display_equations_preserved":re.findall(r"\$\$(.*?)\$\$",sec(now,"### 14.2.1","### 14.5"),re.S)==re.findall(r"\$\$(.*?)\$\$",sec(old,"### 14.2.1","### 14.5"),re.S),
"step4_confirmed":"### 14.6 第4项已确认" in now,
"no_stale_step3_pending":"第3项联合响应尚未确认" not in now,
"no_stale_step4_pending":"第4项数据文件、参数值及缺失处理尚待确认" not in now,
"math_delimiters_even":now.count("$$")%2==0,
}
coverage=json.loads((pkg/"source_coverage.json").read_text(encoding="utf-8"))
contract=json.loads((pkg/"input_contract.json").read_text(encoding="utf-8"))
params=json.loads((pkg/"parameter_register.json").read_text(encoding="utf-8"))
manifest=json.loads((pkg/"run_manifest.json").read_text(encoding="utf-8"))
checks["coverage_expected_1440"]=coverage["expected_intervals"]==1440
checks["lfc_full_numeric"]=coverage["sources"]["lfc"]["groups"]["all"]["numeric_complete_intervals"]==1440
checks["edc_full_numeric"]=coverage["sources"]["edc_related"]["groups"]["all"]["numeric_complete_intervals"]==1440
checks["ics_strict_numeric_1424"]=coverage["sources"]["ics"]["groups"]["all"]["numeric_complete_intervals"]==1424
issues=coverage["sources"]["ics"]["groups"]["all"]["field_issues"]
checks["ics_missing_distinguished_from_marker"]=len({(r["date"],r["slot"]) for r in issues if r["status"]=="missing"})==12 and len({(r["date"],r["slot"]) for r in issues if r["status"]=="marker_requires_semantic_mapping"})==4
checks["blank_padding_not_observations"]=coverage["sources"]["lfc"]["blank_padding_rows"]==48
checks["input_hashes_unchanged"]=all(hashlib.sha256((root/r["path"]).read_bytes()).hexdigest()==r["sha256"] for r in coverage["sources"].values())
checks["missing_parameter_values_null"]=all(r["value"] is None for r in params["parameters"] if r["status"] in ("missing","missing_assumption"))
checks["LV_zero_cash_explicit"]=any(r["scope"]=="LV" and r["parameter"]=="activation_cash" and r["value"]==0 and r["status"]=="confirmed_zero" for r in params["parameters"])
checks["all_table_primary_keys_defined"]=all(set(t["primary_key"])<=set(f["name"] for f in t["fields"]) for t in contract["tables"])
checks["all_tables_unique"]=len(contract["tables"])==len(set(t["logical_file"] for t in contract["tables"]))
checks["not_falsely_solver_ready"]=manifest["full_profit_ready"] is False and manifest["solver_run"] is False
# Check new/current local links; earlier old model links kept within existing files.
docs=[main,root/"countries/JP/model/JP_activation_data_spec_M4.md",here/"step4_decision.md",here/"step4_proposal.md"]+list(pkg.glob("*.md"))
bad=[]
for p in docs:
    for target in re.findall(r"\]\(([^)]+)\)",p.read_text(encoding="utf-8-sig")):
        if "://" in target or target.startswith("#"):continue
        target=target.split("#")[0]
        if target=="step4_validation.json":continue # output created below
        if not (p.parent/target).resolve().exists():bad.append({"file":str(p.relative_to(root)),"target":target})
checks["local_link_targets_exist"]=not bad
out={"date":"2026-10-04","passed":all(checks.values()),"checks":checks,"broken_links":bad,
"scope":"document/input-contract and local CSV coverage validation only; identified source gaps retained; no solver or independent review",
"main_sha256":hashlib.sha256(main.read_bytes()).hexdigest()}
(here/"step4_validation.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"passed":out["passed"],"checks":checks,"broken_links":bad},ensure_ascii=False))
raise SystemExit(0 if out["passed"] else 1)

