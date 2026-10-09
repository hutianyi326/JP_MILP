# 日本MILP输入包：九州2026年6月

日期：2026-10-04。四项方法与输入政策均已获用户确认。当前交付是字段契约、现有数据对应、参数登记和缺口清单；尚未生成全部可求解生产输入，也没有运行MILP。

## 当前结论

- LFC/频率、EDC相关统计、现货、一次F和综合复合C行情各覆盖1,440个半小时。ICS全部所检字段为数值的共同交集为1,424格。
- ICS有12格数值空白，另4格净量为0、状态为“-”待按字典解释；不能直接把这16格当成全部无效或填0。
- 电站规模及设备/控制参数由用户在正式计算时输入，无硬编码默认值，当前留空不阻碍建模。参考池映射、产品份额、可申报组合生成方法及激活结算仍需继续落实。
- 完整6月滚动需要7月1日激活观察日；选用月文件尚不包含。可先在六月内检验短窗口，保持原初末SOC与账本政策。

## 文件入口

|文件|作用|
|---|---|
|[source_mapping.md](source_mapping.md)|源文件、列映射、覆盖范围与实际发现|
|[input_contract.json](input_contract.json)|逻辑表的主键、字段、类型、单位和依赖|
|[parameter_register.json](parameter_register.json)|已确认数值及明确留空的参数|
|[gap_register.md](gap_register.md)|逐项缺口、影响范围和下一步|
|[run_manifest.json](run_manifest.json)|样本范围、原定最终范围和准备状态|
|[source_coverage.json](source_coverage.json)|同键/数值覆盖、字段标记问题及源文件哈希|

## 逻辑输入表结构

下列CSV是待构建的接口，不是声称本目录已存在相应数据文件。需要机器读取时以JSON契约为准。参数null不等于0；“已有资料但未完成适用映射”和“无源数据”在缺口表中区分。

|逻辑表|主键|
|---|---|
|market_prices.csv|interval_start_jst＋area_id＋product_or_mode＋price_role＋source_revision|
|settlement_mapping.csv|mapping_id＋valid_from_jst＋direction|
|regional_statistics.csv|interval_start_jst＋area_id＋metric＋source_revision|
|reference_capacity.csv|interval_start_jst＋area_id＋reference_pool_id＋product＋direction|
|asset_config.csv|asset_id＋parameter＋version|
|bid_candidates.csv|native_block_id＋resource_configuration_id＋bid_candidate_id|
|bid_domains.csv|eligibility_domain_id＋constraint_id＋term_id|
|activation_assumptions.csv|assumption_version＋scenario_id＋parameter＋scope_id|
|activation_states.csv|interval_start_jst＋area_id＋activation_scenario_id＋state_id|
|publication_vintages.csv|source_id＋source_revision|

### market_prices.csv

interval_start_jst, area_id, product_or_mode, price_role, price_value, price_unit, source_revision, source_id, adjustment_branch_id, quality_status

### settlement_mapping.csv

mapping_id, valid_from_jst, valid_to_jst, scenario_id, resource_mode, contract_branch, direction, recognition_rule_id, price_reference_id, cash_sign, chi, evidence_id, quality_status

### regional_statistics.csv

interval_start_jst, area_id, metric, raw_value, numeric_value, raw_unit, unit, source_id, source_column_1based, source_revision, quality_status

### reference_capacity.csv

interval_start_jst, area_id, reference_pool_id, product, direction, reference_mw, numerator_coverage_id, capacity_basis, source_id, quality_status

### asset_config.csv

asset_id, parameter, value, unit, basis, evidence_or_assumption_id, version, quality_status

### bid_candidates.csv

native_block_id, resource_configuration_id, bid_candidate_id, offered_s1_mw, offered_t1_mw, composite_max_mw, full_inner_quantity_validation_id, eligibility_domain_id, rule_vintage_id, quality_status

### bid_domains.csv

eligibility_domain_id, constraint_id, term_id, variable_reference, coefficient, sense, rhs, validation_id, quality_status

### activation_assumptions.csv

assumption_version, scenario_id, parameter, scope_id, value, unit, basis, valid_domain, evidence_id, quality_status

### activation_states.csv

interval_start_jst, area_id, activation_scenario_id, state_id, joint_weight, gamma_up, gamma_down, lfc_centered, lfc_mean, edc_center, edc_deviation, theta, coupling_method, direction_mapping_version, assumption_version, quality_status

### publication_vintages.csv

source_id, source_revision, local_path, sha256, period_start_jst, period_end_jst, obtained_at, publication_time, visibility_status

## 使用与证据

事实/项目输入、工程假设和敏感性参数分开。所有原值保留单位、来源与修订版本。JST半小时；MW、MWh、JPY；容量价格按原生单位转换，不重复乘0.5或1000。
本次对已有官方资料做本地数据核查，没有新增市场规则认定或在线复核。来源机构、标题、定位及原访问日期见[模型§13.10](../../../countries/JP/model/JP_milp_formulation.md)和[证据登记](../../../countries/JP/research/evidence_register.md)。
当前参数登记将deferred_runtime_input与研究缺口分开。电站参数正式运行时由用户输入，在单次求解中作为外生给定值，不成为设备定容决策。历史2MW/8MWh、100MW/200MWh及教学效率/控制值不得自动成为默认参数。
完整利润优化须检查当前场景全部依赖；只得到物理量或已知现金时明确标部分结果。LV不付激活现金例外沿用用户确认，但物理依赖不减少。
四项确认及检查：[第4项记录](../step4_decision.md)。

