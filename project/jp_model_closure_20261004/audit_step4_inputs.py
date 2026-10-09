from pathlib import Path
from datetime import timedelta,datetime
from collections import Counter,defaultdict
import csv,io,zipfile,json,hashlib,math
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent/"step4_input_package"
OUT.mkdir(exist_ok=True)
spec={
"lfc":{"path":"project/jp_activation_downloads_20261001/samples/kyushu_lfc_202606_4c5f53588b32.csv","fields":{"frequency_mean_hz":4,"frequency_upper_equivalent_hz":5,"frequency_lower_equivalent_hz":6,"lfc_mean_mw":16,"lfc_upper_equivalent_mw":17,"lfc_lower_equivalent_mw":18},"url":"https://www.kyuden.co.jp/td_power_usages/csv/lfc/jukyu_LFC_kyushu_202606.csv"},
"edc_related":{"path":"project/jp_activation_downloads_20261001/samples/kyushu_jukyu_202606_259b239ae928.zip","member":"11120_TSO9_0_202606_20260812132500030.csv","fields":{"own_area_own_mo_kwh":7,"forecast_error_other_kwh":10,"other_area_exchange_kwh":8},"url":"https://www.kyuden.co.jp/td_power_usages/csv/kouhyo/jukyu/11120_TSO9_0_202606.zip"},
"ics":{"path":"data/raw/JP/activation_sources_20261001/ics_basis_202606.csv","fields":{"kyushu_imbalance_kwh":21,"kyushu_surplus_shortage":39,"kyushu_partition":57},"url":"https://www.imbalanceprices-cs.jp/api/1.0/imb/basis/202606"},
"spot":{"path":"countries/JP/research/analysis/spot_30min_JST_expost.csv","fields":["九州"]},
"capacity":{"path":"countries/JP/research/analysis/eprx_awards_native_blocks_expost.csv","fields":["avg_price_source_JPY_kW_30min","avg_price_TSO_JPY_kW_30min","award_source_MW","award_TSO_MW","duration_h"]},
}
expected={(f"202606{d:02}",s) for d in range(1,31) for s in range(1,49)}
obs={("20260701",s) for s in range(1,49)}
def decode(raw):
    for enc in ("utf-8-sig","cp932"):
        try:return list(csv.reader(io.StringIO(raw.decode(enc)))),enc
        except UnicodeDecodeError:pass
    raise ValueError("cannot decode")
def num(v):
    try:return math.isfinite(float(v))
    except (ValueError,TypeError):return False
def tskey(v):
    dt=datetime.fromisoformat(v)
    assert dt.utcoffset()==timedelta(hours=9) and dt.minute in (0,30) and dt.second==0
    return dt.strftime("%Y%m%d"),dt.hour*2+dt.minute//30+1
reports={};keysets={};hashes={}
for name,cfg in spec.items():
    raw=(ROOT/cfg["path"]).read_bytes()
    hashes[name]=hashlib.sha256(raw).hexdigest()
    data=raw
    if "member" in cfg:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:data=z.read(cfg["member"])
    rows,enc=decode(data);header=rows[0];keyed=[]
    if name in ("lfc","edc_related"):
        keyed=[((r[0],int(r[1])),r,n) for n,r in enumerate(rows[1:],2) if len(r)>1 and r[0].isdigit() and r[1].isdigit()]
    elif name=="ics":
        keyed=[((r[1],int(r[2])),r,n) for n,r in enumerate(rows,1) if len(r)>2 and r[0]=="D"]
        header=max((r for r in rows if r and r[0]=="H"),key=len)
    else:
        for n,row in enumerate(rows[1:],2):
            r=dict(zip(header,row))
            if name=="capacity" and r["area"]!="九州":continue
            keyed.append((tskey(r["timestamp"] if name=="spot" else r["timestamp_JST"]),r,n))
    groups={"all":keyed}
    if name=="capacity":
        groups=defaultdict(list)
        for x in keyed:groups[x[1]["product"]].append(x)
    gr={}
    for product,values in groups.items():
        selected=[x for x in values if x[0] in expected]
        keys=Counter(k for k,r,n in selected);valid=set();missing=Counter();issues=[]
        for k,r,n in selected:
            ok=True
            fields=cfg["fields"].items() if isinstance(cfg["fields"],dict) else [(f,f) for f in cfg["fields"]]
            for field,idx in fields:
                value=r[idx] if isinstance(idx,str) or idx<len(r) else None
                if not num(value):
                    missing[field]+=1;ok=False
                    issues.append({"date":k[0],"slot":k[1],"source_line":n,"field":field,"raw_value":value,"status":"missing" if value is None or str(value).strip()=="" else "marker_requires_semantic_mapping"})
            if ok:valid.add(k)
        info={"rows_in_june":len(selected),"unique_intervals":len(keys),"duplicate_keys":sum(n-1 for n in keys.values()),
              "expected_intervals":1440,"missing_intervals":len(expected-set(keys)),"numeric_complete_intervals":len(valid),
              "missing_or_invalid_numeric_fields":dict(missing),"field_issues":issues,"observation_day_july1_unique_intervals":len({k for k,r,n in values}&obs)}
        if selected:info.update(first_source_line=selected[0][2],last_source_line=selected[-1][2])
        if name=="capacity":
            info.update(durations_h=sorted({r["duration_h"] for k,r,n in selected}),qualities=dict(Counter(r["quality"] for k,r,n in selected)),
                sources=sorted({r["source_id"] for k,r,n in selected}),
                source_award_positive_price_numeric_rows=sum(float(r["award_source_MW"])>0 and num(r["avg_price_source_JPY_kW_30min"]) for k,r,n in selected),
                tso_award_positive_price_numeric_rows=sum(float(r["award_TSO_MW"])>0 and num(r["avg_price_TSO_JPY_kW_30min"]) for k,r,n in selected),
                price_role="aggregate_proxy_candidate_not_site_settlement")
        gr[product]=info;keysets[name if product=="all" else name+"_"+product]=valid
    report={"path":cfg["path"],"sha256":hashes[name],"encoding":enc,"source_rows_including_headers":len(rows),"groups":gr,
            "source_metadata":{k:v for k,v in cfg.items() if k not in ("fields","path")}}
    fi=cfg["fields"].items() if isinstance(cfg["fields"],dict) else [(f,header.index(f)) for f in cfg["fields"]]
    report["field_mapping"]={f:{"column_1based":i+1,"source_header":header[i]} for f,i in fi}
    if name=="lfc":
        report["outside_date_counts"]=dict(Counter(k[0] for k,r,n in keyed if k not in expected))
        report["blank_padding_rows"]=sum(not any(c.strip() for c in r) for r in rows[1:])
        report["upper_lower_inversions"]=sum(float(r[5])<float(r[6]) or float(r[17])<float(r[18]) for k,r,n in keyed if k in expected and all(num(r[i]) for i in [5,6,17,18]))
    reports[name]=report
common=set.intersection(*(keysets[k] for k in ["lfc","edc_related","ics","spot"]))
common_prices=common & keysets["capacity_F"] & keysets["capacity_C"]
unchanged=all(hashlib.sha256((ROOT/spec[k]["path"]).read_bytes()).hexdigest()==h for k,h in hashes.items())
out={"inspection_date":"2026-10-04","timezone":"Asia/Tokyo","sample_start":"2026-06-01T00:00:00+09:00",
"sample_end_exclusive":"2026-07-01T00:00:00+09:00","expected_intervals":1440,"sources":reports,
"common_numeric_core_intervals":len(common),"common_with_F_C_numeric_rows":len(common_prices),
"raw_and_existing_processed_files_unchanged":unchanged,"scope":"keys and finite numeric availability; not pool equivalence, calibration, eligibility, payment certification or solver readiness",
"full_profit_ready":False,"gaps":["device_efficiency_soc_aux_control_parameters","directional_reference_capacity_mapping",
"product_allocation_and_response_parameters","verified_full_inner_bid_candidates_and_domains","mode_specific_prices_and_activation_payment_mapping",
"nonzero_edc_variation_and_coupling","observation_day_activation_inputs"]}
(OUT/"source_coverage.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
lines=["# 九州2026年6月输入核查","","核查日期：2026-10-04。时区Asia/Tokyo，样本为6月1日00:00至7月1日00:00（右端不含），共1,440个半小时。","",
f"频率/LFC、EDC相关统计、ICS工况及现货价格共同具有所检数值字段的半小时：**{len(common)} / 1,440**。再匹配一次F和综合复合C行情记录：**{len(common_prices)} / 1,440**。这只是同键数值覆盖，不等于产品归属、方向容量、结算或模型参数已闭合。","",
"|数据|6月记录数|唯一半小时|所检数值齐备|7月1日记录数|","|---|---:|---:|---:|---:|"]
for name,rep in reports.items():
    for product,g in rep["groups"].items():
        if name=="capacity" and product not in ("F","S1","T1","C"):continue
        label=name if product=="all" else name+"_"+product
        lines.append(f"|{label}|{g['rows_in_june']}|{g['unique_intervals']}|{g['numeric_complete_intervals']}|{g['observation_day_july1_unique_intervals']}|")
lines+=["","## 已发现的处理边界","",
f"- LFC文件末尾有{reports['lfc']['blank_padding_rows']}行空白模板，已在读取时排除；原始文件未改写，不把空白模板当7月观测。",
"- ICS九州不平衡量和供需状态在6月7日第32—43格共12格为空；另4格不平衡量为0而供需状态为‘-’，须按字段字典映射，不直接当缺失或数值0。1424是全部所检字段均为数值的严格覆盖数，并不代表另外16格的全部数据不可用。",
"- ICS只影响使用对应工况分层的输入，不自动阻断未使用该条件的一次场景。若另建不依赖该条件的参数情景，须独立命名并说明适用范围，不能暗中填补。",
"- 一次F行情未在该标准化表按在线/离线标记，不能直接认定LV/高压模式专属价格；综合复合C不是二次①＋三次①特定组合的独立价格。",
"- source与TSO价格/中标量是不同口径，不能任取分母。价格为0不自动代表本站可按0结算，须同时检查成交状态与price_role。",
"- 已有地区中标量不代表已获得与LFC/EDC统计池匹配的上/下方向参考能力；不能由上调采购量补造下调分母。",
"- 完整6月滚动测算所需7月1日激活观察日输入未包含在本次月文件中。现货/容量观察日行见上表。可先在六月内验证短窗口，不免费重置SOC。",
"- 设备、控制、产品份额、报价状态域和激活付款映射尚未准备成已验证输入，三个场景均未就绪完整利润优化。",
"","## 字段及来源",""]
for name,rep in reports.items():
    lines += [f"### {name}","",f"本地：[原文件](../../../{rep['path']})。SHA256：{rep['sha256']}。编码：{rep['encoding']}。"]
    if "url" in rep["source_metadata"]:
        lines += [f"官方：[来源链接]({rep['source_metadata']['url']})。本次读取已下载文件，未重新在线核验，发布时间以原登记为准。"]
    else:lines += ["追溯：[官方证据登记](../../../countries/JP/research/evidence_register.md)及既有lineage；行情汇总不是本站结算证据。"]
    lines += ["","|目标字段|原列（从1计）|原字段|","|---|---:|---|"]
    for f,m in rep["field_mapping"].items():lines.append(f"|{f}|{m['column_1based']}|{m['source_header']}|")
    lines += [""]
lines += ["详细结果：[source_coverage.json](source_coverage.json)。本次没有修改原始CSV或既有处理后数据。"]
(OUT/"source_mapping.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
print(json.dumps({"core":len(common),"with_F_C":len(common_prices),"lfc_outside":reports["lfc"].get("outside_date_counts"),"unchanged":unchanged,
"F":reports["capacity"]["groups"]["F"],"C":reports["capacity"]["groups"]["C"]},ensure_ascii=False))
