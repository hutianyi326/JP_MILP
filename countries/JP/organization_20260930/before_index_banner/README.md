# 日本市场研究（基线V2）

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
