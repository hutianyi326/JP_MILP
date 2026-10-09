# 日本 MILP 实现范围（2026-10-04）

用户授权主 agent 编码，完成后交独立 review agent 审查。主线程据项目目录规则批准本任务新增 src/jp_milp/、tests/test_jp_milp.py、project/run_jp_milp.py、model/jp_milp_implementation.md 及 outputs/jp_implementation_validation_20261004/；不修改其他国家实现或原始数据。

依据 countries/JP/model/JP_milp_formulation.md，第14节已确认方案优先于历史三相位；电站参数为运行输入。实现包括三种固定场景、离散激活预处理、稀疏 MILP、有限连续服务路径、净合同与容量冻结、两日滚动、现金/SOC/EFC 独立复算、命令行和合成测试。正式历史测算不属于本次代码验收；未校准参考池、结算认可及能力全量内数证据保持运行门禁。

参考仓库 https://github.com/hutianyi326/ES_MILP ，读取 HEAD 70651210d0ad98ac820644754508f76363d2c799。只读参考保存在 reference_ES_MILP/。沿用其 code/src 数据适配、core、perfect/rolling、ledger、diagnostics 和 code/project 入口的职责划分，不复制西班牙调节三相位与设备默认值。

市场规则沿用现有日本证据登记，本次不新增未经核验规则。服务路径覆盖、理想全额中标、区域激活缩放及有限组合表均为明确的研究/工程假设；外部能力 validation_id 是证据引用，不代表程序认证了电站能力。后续审查记录单独保存。
