> 当前场景范围（2026-10-04）：[MILP主文§14](../model/JP_milp_formulation.md)按用户确认调整：LV仅一次，激活现金为零但保留SOC、损耗及循环影响；高压分别测算现货＋一次、现货＋二次①＋三次①。后一场景按复合产品投标，两项容量允许不同并分别优化。本次文档修订未独立审核、未实现或回测；旧PASS不自动覆盖本次扩展，历史市场研究不变。

> 历史模型更新（2026-09-30）：[M4主文](../model/JP_milp_formulation.md)按用户新设定修订，本轮独立审核PASS（仅数学设计）。LV为单成员标签2 MW/8 MWh、EHV为100 MW/200 MWh；准入不建模、全历史统一容量日前时钟、等效时长激活、主收益排除imbalance。下文M3-R2及早期规模/资格/周采购要求属于旧模型或真实市场研究，不覆盖M4；历史研究事实保持。

> 数学更新：M3-R2本轮独立审核PASS；本页旧数学PASS和旧版本进度属于历史记录。

> 2026-09-30整理：请先阅读[日本资料总目录](../README.md)。当前MILP为[M3-R2](../model/JP_milp_formulation.md)；下文M2及更早进度属于历史记录。

# 日本市场研究（基线V2）

> 最新研究补充（2026-10-02）：[主报告JP-05](research_report.md)已汇总激活指令与报价组合八部分。本批次已独立审核PASS（限研究汇总），见[本批次审核](../../../project/jp_research_consolidation_20261002/review_20261002.md)；下文各次PASS仍只覆盖各自原交付，本批次不改变正式M4及实施门禁。

## 激活指令与报价组合阅读入口

主报告八部分依次说明：五类产品响应；11种四产品组合及三次②同时中标边界；储能组合适配性；GF/LFC/EDC与三种信号；九区接口和合成；4 MW共享/5 MW案例；设备和接入；历史数据与第一版推算/MILP衔接。

- [主研究报告](research_report.md)、[新增证据登记](evidence_register.md)、[研究交接](model_handoff.md)、[本批次补充与检查记录](../../../project/jp_research_consolidation_20261002/补充记录.md)。
- [指令口径与复合控制专题](../../../project/jp_instruction_semantics_20261001/日本EPRX指令口径与复合控制研究.md)：详细九区周期、端口公式、条件合成及原件定位。
- [指令选择与设备接入专题](../../../project/jp_instruction_semantics_20261001/储能指令方式选择与设备接入影响.md)：接口选择条件和工程影响。
- [历史LFC/EDC下载核查](../../../project/jp_activation_downloads_20261001/日本历史LFC和EDC数据下载入口核查.md)：公开入口、实际样本、结构检查及数据限制。
- [激活推算方法研究](../../../project/jp_activation_methods_20261001/日本EPRX激活推算方法研究.md)：第5节首版推荐、第12—22节七类数学规格；[数学研究审核](../../../project/jp_activation_methods_20261001/revision_math_20261001/review_math_20261001.md)不覆盖本次新增LFC统计解释。
- [MILP求解规模与耗时评估](../../../project/jp_activation_methods_20261001/MILP求解规模与耗时影响评估.md)：结构计数及待实测性能，未承诺求解时间。

三次②不属于正式四产品复合报价成员，但规程别表3列有其与其他产品同时中标后的指令关系；公开LFC半小时统计已经取得部分样本，仍缺电站高频原始指令。阅读早期附件中的“缺激活数据”时，应按这两个精确边界理解。



研究窗口2025-01-01—2026-08-31，信息截止2026-09-28。九区域比较，排除冲绳及离岛。主线程编制；整包提交gpt-6-astra/high只读独立审核。



- [综合研究报告](research_report.md)：JP-01—JP-10机制、数据比较及条件性选区。

- [建模交接候选与缺口](model_handoff.md)：资格矩阵、候选约束、数据字典和G01—G10。

- [证据登记](evidence_register.md)、[来源清单](source_inventory.csv)：官方定位、原文及哈希。

- [验证记录](validation_report.md)：最新完整性检查及未通过的研究门禁。

- [审核记录](review_record.md)：保留历次Astra high判定；本轮R11/R12关闭，整体仍NOT_PASS，R02—R07余项保留。

- [审核修订](revision_notes.md)：联络线正负方向、采购地域规则及历史产品证据补充；初稿在review_initial/留档。

- [结算分支与核对案例](settlement_branches.md)：V1/V2合同例外及电量接口；案例是假设演示，G08未关闭。

- [第二轮实质修订与复核提交](revision_round2.md)：完整日内汇总、法定日历、官方事件和剩余问题。

- [容量机制修订](capacity_mechanisms_revision.md)：履约罚款、长期95%/90%/85%分段返还。

- [区域费用修订](regional_cost_revision.md)：九区发电侧基准及项目计费边界。

- [本次整包审核及修复](review_round2_result.md)：R01—R12判定、独立检查和手续费/引用修正。

- [九区边界与装机修订](../topics/boundary_revision_20260928.md)：府县绝对量代理、年度展望、逐岛证据与限制。

- [历史规则与结算修订](../topics/history_settlement_revision_20260928.md)：六段EPRX关键条款及仍待闭合分支。

- analysis/：日前、不平衡及诊断基本面CSV；figures/：研究图表；evidence/：不可覆盖原始快照。



所有价格序列是获取日可得的事后修订版，不是历史决策时已知数据。供需及装机图表尚未证明离岛剔除，全部标为DIAGNOSTIC。第四轮研究已PASS，可进入带输入门禁数学说明；不放行历史收益回测。



复现：analyze_history.py → analyze_imbalance.py → plot_research.py；build_register.py生成证据目录；validate_package.py独立核验。图中装机比例由O10/O11图3-2人工转录，2024九州风电占比经高分辨率原图复核为1.8%。原始PDF始终保留。



第三轮当前补证：[修订总表](revision_round3.md)、[成交量价比较](auction_comparison_round3.md)、[费用/使用率补证](regional_closure_round3.md)、[容量](../topics/capacity_closure_round3.md)、[计量/历史](../topics/history_closure_round3.md)、[储能特措](../topics/storage_tariff_round3.md)、[边界](../topics/boundary_closure_round3.md)。这些附件已在第四轮独立整包审核PASS，历次NOT_PASS保留为审核历史。



第三轮记录见[第三轮审核记录](review_round3_result.md)；其2项P1和1项P2已在第四轮关闭。



**当前状态：[第四轮研究审核PASS及主线程验收](review_round4_result.md)。** 上文第三轮及更早记录保留为历史；数学说明阶段已开放，代码与真实收益回测未批准。



## 数学阶段最终交付



[2MW/8MWh低压聚合与特別高圧MILP数学说明](../model/JP_milp_formulation.md)已在M2获Astra/high独立审核PASS，主线程验收见[最终数学审核](milp_review_final.md)。研究和数学两阶段均通过；上文历史进度以该最终记录为准。实际输入门禁、代码/回测未批准状态保持。


## 2026-09-30研究补充

本轮补充已独立审核PASS，P0/P1/P2均为0；[审核记录](supplement_20260930/review_final.md)：[现货与EPRX耦合及容量报价](spot_eprx_coupling_supplement_20260930.md)、[修订主报告](research_report.md)、[建模交接](model_handoff.md)。既有M3-R1公式保持不变；新增内容经本轮独立审核，未继承旧研究PASS。
