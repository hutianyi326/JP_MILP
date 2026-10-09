> 当前模型更新（2026-09-30）：[M4主文](model/JP_milp_formulation.md)按用户新设定修订，本轮独立审核PASS（仅数学设计）。LV为单成员标签2 MW/8 MWh、EHV为100 MW/200 MWh；准入不建模、全历史统一容量日前时钟、等效时长激活、主收益排除imbalance。下文M3-R2及早期规模/资格/周采购要求属于旧模型或真实市场研究，不覆盖M4；历史研究事实保持。

# 日本市场研究与MILP总目录

整理日期：2026-09-30。日本相关研究文件已集中到本目录；本次仅整理路径，不改变研究规则、建模假设或审核结论。

## 优先阅读

|文件|内容与状态|
|---|---|
|[市场研究主报告](research/research_report.md)|研究基线V2，2025-01-01至2026-08-31，九区域，排除冲绳及离岛；第四轮研究审核PASS|
|[MILP数学模型](model/JP_milp_formulation.md)|M3-R2，完美信息毛收益；新增终端与连续服务闭合，本轮独立审核PASS|
|[研究基线及范围](research_scope_draft_20260928.md)|原始范围讨论与V2基线，以最新用户修订及MILP基线为准|
|[M3模型用户基线](research/milp_M3_user_baseline_20260929.md)|目标、参与范围与西班牙复用口径|
|[官方证据登记](research/evidence_register.md)|来源机构、文件版本、定位、URL与访问记录|
|[日本与西班牙模型比较](research/JP_ES_model_comparison_20260929.md)|保留历史比较；M3已更新目标口径，注意文件开头说明|

## 文件布局

|目录|内容|
|---|---|
|[research](research/README.md)|综合研究、专题修订、建模交接及分析脚本|
|model|当前日本MILP数学文档|
|topics|九区边界、装机、历史结算、容量、储能费用等专题附件|
|research/analysis|处理后的时序与统计结果；DIAGNOSTIC标签保留|
|research/figures|研究图表与证据页图像|
|research/evidence、research/extracted|官方原始快照及提取文本|
|data/raw|原data/raw/JP的补充原始数据与证据；内容未改写|
|research/review_initial、review_round1、milp_review_initial|历次冻结稿；原内容及原哈希保留|
|organization_20260930|迁移清单、旧新路径映射、检查记录及路径修改前备份|

## 审核与使用边界

- [研究第四轮审核](research/review_round4_result.md)：PASS；历次NOT_PASS文件属于历史记录。
- [M3数学审核](research/milp_M3_review_final.md)及[M3-R1排版复核](research/JP_M3_readability_change_notes.md)：PASS。
- 当前未批准生产代码和真实收益回测；项目资格、工程参数、调用与结算输入门禁保持。
- 无法拆分离岛的装机/供需代理仍仅限DIAGNOSTIC，不因迁移而转为正式模型输入。
- 原审核清单、冻结稿及原始数据中的旧路径按[迁移清单](organization_20260930/migration_manifest.json)映射；不重写历史哈希或冒称旧审核覆盖新路径字节。
- 本目录链接到西班牙共用代码及设计文件，这些共用资产仍保留在项目原位置。

本次未新增官方来源；EPRX、JEPX、OCCTO、METI及各区域TSO证据均沿用既有登记。

## 2026-09-30研究补充

本轮补充已独立审核PASS，P0/P1/P2均为0；[审核记录](research/supplement_20260930/review_final.md)：[现货与EPRX耦合及容量报价](research/spot_eprx_coupling_supplement_20260930.md)、[修订主报告](research/research_report.md)、[建模交接](research/model_handoff.md)。既有M3-R1公式保持不变；新增内容经本轮独立审核，未继承旧研究PASS。

## M3-R2数学修订

[规范性补充](model/JP_M3_R2_closure.md)与[变更登记](model/revision_M3_R2_20260930/change_log.md)共同适用；此前M3/M3-R1 PASS为历史结论，不覆盖R2。
