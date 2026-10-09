# JP_MILP — 日本独立储能交易与 MILP 测算

日本调整力市场研究、激活统计假设、储能 MILP、历史测算与独立审核。2026-10-09从本地 `Counry_Investigation` 的日本交付整理为独立仓库，保留原目录和模块相对路径；文件来源与散列见 [repository_export_manifest.json](repository_export_manifest.json)。

## 固定场景

- `LV_FCR`：一次离线市场；一次激活现金为零，调用仍影响 SOC、效率损耗和 EFC。按已确认方案，每天以恒定恢复基线恢复目标 SOC，不做日内现货套利。
- `HV_SPOT_FCR`：现货＋一次调整力。
- `HV_SPOT_S1_T1`：现货＋二次①＋三次①，复合产品容量由模型在已确认的能力域内优化。

电站参数是运行时输入。事实、研究解释和建模假设必须分开；不使用西班牙的三相激活假设。历史名义采购时钟按规则日期绑定，冻结订单、SOC和年度 EFC连续保存。

## 导航

|内容|入口|
|---|---|
|数学模型及激活假设|[JP_milp_formulation.md](countries/JP/model/JP_milp_formulation.md)|
|实现、参数与命令说明|[jp_milp_implementation.md](model/jp_milp_implementation.md)|
|核心代码|[src/jp_milp](src/jp_milp)|
|研究及官方来源|[countries/JP](countries/JP/README.md)|
|初始实现审核|[review_and_acceptance.md](project/jp_implementation_20261004/review_and_acceptance.md)|
|四国测算与比较|[收益测算结果](project/jp_revenue_20261005/收益测算结果.md)|
|四国一次离线 LV 最新复算|[收益测算结果](project/jp_lv_offline_run_20261005/收益测算结果.md)|
|九州2 MW/8 MWh，2025-12至2026-08|[收益测算结果](project/jp_kyushu_lv_20261006/收益测算结果.md)|
|九州数据口径与假设|[README](project/jp_kyushu_lv_20261006/README.md)|
|九州完整独立审核|[review.md](project/jp_kyushu_lv_20261006/review.md)|

## 环境与运行

记录的运行环境为 Python 3.12、NumPy 2.4.6、SciPy 1.15.3、HiGHS 1.15.1、PySCIPOpt 6.2.1。安装依赖后可检查入口与运行合成回归测试：

```powershell
python -m pip install -r requirements.txt
python project/run_jp_milp.py --help
python -m unittest discover -s tests -p "test_jp*.py"
```

历史运行需要对应输入包。输入规范和正式运行命令见实现说明；九州入口为 `project/jp_kyushu_lv_20261006/run.py`，四国入口与离线绑定分别见相关项目目录。抓取脚本、源文件URL、下载清单与散列记录均保留。

## Git 与本地数据

仓库纳入日本源代码、测试、数学文档、研究、官方证据、参数及下载清单、月度结果、较小的价格表和审核报告。`data/`、`outputs/`、`countries/JP/data/`、大型时间序列CSV、ZIP归档、完整求解账本、虚拟环境和重复源码快照留在原本地工作区，不随Git上传。具体未导入项及原因见导出清单。

克隆仓库后不能仅凭摘要重新运行完整历史测算，需将相应原始/处理数据与执行账本恢复至相同相对路径。九州的完整本地归档为 `outputs/JP/kyushu_lv_2mw_8mwh_20251201_20260831_20261006_reviewed.zip`，其校验值见已保留的 `project/jp_kyushu_lv_20261006/delivery_manifest.json`。本仓库是2026-10-09交付副本，原工作区未移动；后续开发应明确以该Git目录为工作入口，避免双份修改。

## 结果边界

收益是登记假设下的事后条件现金测算，不是完整项目净利润或可执行策略收益。九州2026-03-14前的低压参与部分为反事实；之后亦未认证具体电站资格。频率缺口代理、区域均价、理想全额成交、无价格冲击和未计合同费用等限制见各期报告。窗口gap不等于全期收益误差界。

本次仓库整理不新增市场规则或修改模型数学约束。官方来源仍以各研究文档的机构、版本、页码、URL和访问日期为准。
