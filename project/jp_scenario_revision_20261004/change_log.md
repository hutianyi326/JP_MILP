# 日本MILP场景修订记录

日期：2026-10-04。状态：用户范围及澄清已登记；主线程文档一致性检查，不是独立审核PASS或生产验收。

## 修改文件

- countries/JP/model/JP_milp_formulation.md：更新当前范围与优先级，新增§14；LV激活现金为零但保留物理影响；高压两个独立运行场景；二次①、三次①自由内数、共享最大容量线性化、候选联合响应接口及缺口。
- countries/JP/model/JP_activation_data_spec_M4.md：追加场景、自由内数、共同响应及复合计价依赖；不删除LV物理数据依赖。
- countries/JP/README.md、countries/JP/research/README.md、countries/JP/research/model_handoff.md：同步最新范围，保留旧审核和研究历史。
- 本目录：用户确认、原文件备份、本记录、检查脚本及结果。

## 依据与边界

本次变更依据[用户原话与明确回复](user_scope.md)，属于模型范围选择和建模假设，没有新增或重新核验官方市场规则。既有官方依据继续见[主文§13.10](../../countries/JP/model/JP_milp_formulation.md)、[官方证据登记](../../countries/JP/research/evidence_register.md)：九州LFC/广域调整力CSV、东京字段说明、ICS手册、OCCTO二次①广域运用设计及既有EPRX组合规则研究。访问日期和定位保留在原登记中，不冒称本次在线复核。

规则事实与模型假设分开记录。共享包络、单位容量线性响应是需校准的设计，不是TSO自动限幅事实。高压两场景是候选策略，不是已证明的全局最优组合。旧§13完整保留；生产代码、原始CSV和历史独立审核记录未编辑。

## 尚未解决

有效报价可行域、复合计价函数、LFC/EDC共同响应与付款映射尚须闭合；半小时边际统计不足以确定联合时序。本站排除二次②不消除区域历史数据中的二次②份额。自由容量比例不能直接使用旧固定比例包的激活系数。尚未运行MILP求解或历史收益计算，也未证明求解速度改善。

## 检查

运行[validate.py](validate.py)，结果见[validation.json](validation.json)。覆盖§13内容保留、三场景及用户回复的一致性、关键边界说明、最大值线性化样例及本次新增链接目标。原文件与当前文件哈希一并记录。检查不替代官方规则复核、参数校准或独立审核。

