from pathlib import Path
import json,re,hashlib
here=Path(__file__).resolve().parent
root=here.parents[1];pkg=here/"step4_input_package"
def load(p):return json.loads(p.read_text(encoding="utf-8"))
def save(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
params=load(pkg/"parameter_register.json")
params["status"]="runtime_asset_inputs_and_research_parameters_separated"
params["asset_input_policy"]="User supplies station parameters at formal calculation; no hardcoded default; fixed exogenous within a solve, not sizing decisions."
asset_scopes={"LV_and_HV","FCR_online_and_offline"}
for r in params["parameters"]:
    if r["parameter"] in ("nominal_power","nominal_energy") or r["scope"] in asset_scopes:
        if r["value"] is not None:r["historical_example_only"]=r["value"]
        r.update(value=None,status="deferred_runtime_input",basis="user_supplied_at_formal_calculation",
                 note="不阻碍建模/通用实现；运行前必填并验证；历史示例不自动载入",is_optimization_variable=False,default_value=None)
save(pkg/"parameter_register.json",params)
contract=load(pkg/"input_contract.json")
contract["version"]="2026-10-04_runtime_asset_inputs"
if "deferred_runtime_input" not in contract["quality_status_values"]:contract["quality_status_values"].append("deferred_runtime_input")
contract["asset_parameter_policy"]={"supplied_at":"formal_run_initialization","hardcoded_defaults":False,
"optimizer_selects_asset_size_or_efficiency":False,"missing_before_run":"deferred_runtime_input_not_research_gap",
"missing_at_run":"explicit_input_error","derived_tables_require":"asset_config_version",
"derived_bounds":"computed_from_validated_input_not_arbitrary_big_M"}
for t in contract["tables"]:
    if t["logical_file"] in ("activation_states.csv","bid_candidates.csv","bid_domains.csv"):
        if not any(f["name"]=="asset_config_version" for f in t["fields"]):
            t["fields"].append({"name":"asset_config_version","type":"string","unit":None,"missing_policy":"required when device dependent"})
        if "asset_config_version" not in t["primary_key"]:t["primary_key"].append("asset_config_version")
save(pkg/"input_contract.json",contract)
manifest=load(pkg/"run_manifest.json")
manifest["asset_parameters_deferred_until_formal_run"]=True
manifest["missing_station_values_block_model_design"]=False
manifest["reason"]="Formal run requires user-supplied station configuration; remaining research/data gaps are listed separately."
save(pkg/"run_manifest.json",manifest)
# Update the current, reader-facing gap inventory. Earlier audits remain historical snapshots.
p=pkg/"gap_register.md";s=p.read_text(encoding="utf-8")
s=s.replace("|G01|设备效率、可用SOC、初末SOC、辅用及端口限值|名义LV 2MW/8MWh、HV 100MW/200MWh已确认；其余未准备为完整配置|三个场景物理输入未就绪；补项目值或单独登记工程情景，不暗用ES值|",
"|G01（转为运行输入）|电站规模、效率、SOC、辅用和端口限制|用户确认正式计算时提供；旧规模仅历史示例，无默认值|不属于建模阶段研究缺口；运行前按配置校验|")
s=s.replace("|G02|在线/离线一次控制参数与容量缩放适用域|频率统计1,440格完整；死区/跨度/增益及匹配容量需落实|一次激活状态尚不可正式生成；不要把教学参数当已校准|",
"|G02（区分参数与方法）|在线/离线控制参数由运行配置提供；缩放方法仍需验证|频率统计1,440格完整，控制参数正式运行时传入|不催填具体参数；用该次配置生成状态，并验证缩放适用域|")
s=s.replace("|G01、G02、G06；完整月另有G10|","|G02中的缩放方法及G06；正式运行另需电站配置，完整月另有G10|")
s=s.replace("|G01、G02、G06、适用付款分支G07；完整月另有G10|","|G02中的缩放方法、G06及适用付款分支G07；正式运行另需电站配置，完整月另有G10|")
s=s.replace("|G01、G03—G08；使用ICS条件时需处理G09；完整月另有G10|","|G03—G08；正式运行另需电站配置；使用ICS条件时需处理G09，完整月另有G10|")
s+="\n用户后续明确电站参数正式测算时提供。G01不再计为研究缺口；候选表及激活状态在该次参数读入后生成/核验，并绑定asset_config版本。缺少具体数值不阻碍通用建模。\n"
p.write_text(s,encoding="utf-8")
p=pkg/"README.md";s=p.read_text(encoding="utf-8")
s=s.replace("- 物理参数、控制参数、匹配的方向参考容量、产品份额、可申报内数组合以及激活付款仍未准备为完整输入。三个场景目前都不能直接计算可信完整收益。",
"- 电站规模及设备/控制参数由用户在正式计算时输入，无硬编码默认值，当前留空不阻碍建模。参考池映射、产品份额、可申报组合生成方法及激活结算仍需继续落实。")
s=s.replace("当前参数登记并非穷尽整个项目中所有设备资料；它记录哪些数值尚未成为此版本经确认、同口径、可执行的输入。不能把早期教学例子中的0.92效率、SOC比例或频率跨度直接激活为项目参数。",
"当前参数登记将deferred_runtime_input与研究缺口分开。电站参数正式运行时由用户输入，在单次求解中作为外生给定值，不成为设备定容决策。历史2MW/8MWh、100MW/200MWh及教学效率/控制值不得自动成为默认参数。")
p.write_text(s,encoding="utf-8")
current=(root/"countries/JP/model/JP_milp_formulation.md").read_text(encoding="utf-8")
before=(here/"runtime_parameter_before/JP_milp_formulation.md").read_text(encoding="utf-8")
changed=[r for r in params["parameters"] if r["status"]=="deferred_runtime_input"]
checks={"all_station_inputs_null":all(r["value"] is None for r in changed),
"no_station_default_values":all(r.get("default_value") is None for r in changed),
"not_design_blocker":manifest["missing_station_values_block_model_design"] is False,
"not_sizing_decision":all(r["is_optimization_variable"] is False for r in changed),
"formulas_preserved":re.findall(r"\$\$(.*?)\$\$",current,re.S)==re.findall(r"\$\$(.*?)\$\$",before,re.S),
"LV_zero_activation_cash_unchanged":any(r["scope"]=="LV" and r["parameter"]=="activation_cash" and r["value"]==0 for r in params["parameters"]),
"asset_version_binding":all("asset_config_version" in t["primary_key"] for t in contract["tables"] if t["logical_file"] in ("activation_states.csv","bid_candidates.csv","bid_domains.csv"))}
out={"date":"2026-10-04","passed":all(checks.values()),"checks":checks,"station_parameter_rows":len(changed),
"scope":"documentation and parameter configuration checks, no solver test","main_sha256":hashlib.sha256((root/"countries/JP/model/JP_milp_formulation.md").read_bytes()).hexdigest()}
save(here/"runtime_parameter_validation.json",out)
print(json.dumps(out,ensure_ascii=False))
raise SystemExit(0 if out["passed"] else 1)

