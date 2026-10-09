# M4激活数据接口

> 当前接口范围（2026-10-04）：以[主文§14](JP_milp_formulation.md#14-2026-10-04用户确认的固定测算场景)及[用户回复](../../../project/jp_scenario_revision_20261004/user_scope.md)为准。下段PASS仅针对旧M4版本；本次接口扩展未独立审核或实现。

## 当前场景接口覆盖

|scenario_id|允许新增容量|物理激活依赖|激活付款依赖|
|---|---|---|---|
|LV_FCR|仅一次离线|保留，不能置零代替缺失|按用户设定现金为零，不要求激活能量价格|
|HV_SPOT_FCR|仅一次在线|保留§13.4输入及响应路径|按已登记认可映射|
|HV_SPOT_S1_T1|二次①＋三次①不等容量复合|§13.5/13.6边际输入＋同基线、去重后的LFC/EDC联合路径|有效复合容量计价及激活认可映射|

三个场景各自保留既有现货权限。高压两个场景独立求解，不在同一运行中逐时切换。LV不新增省略物理激活的依赖例外；无付款仍须估算SOC、损耗及循环。

接口扩展字段如下；这是待实现契约，不宣称已有对应CSV：

```text
scenario_id,composite_bid_feasible_set_id,composite_capacity_pricing_id,
joint_response_scenario_id,subinterval_id,subinterval_duration_h,
lfc_per_mw_signed,edc_per_mw_signed,response_basis,deduplication_status,
shared_envelope_assumption_id,capacity_ratio_validity_domain,
activation_payment_mapping_id,assumption_version
```

二次①、三次①的本站中标容量是两个优化输出，不写入外生单位容量响应系数。外生共同路径保持固定；如果参数依赖容量比例，必须登记适用范围并另建分段或离散情景，不得隐含变量乘积。共享容量最大值、报价集合及复合计价按主文§14.3。报价可行域须明确正容量包允许的内数组合及适用最小量。

仅有半小时边际alpha不能填造联合路径。合成绝对指令必须先统一基线且只计算一次；缺少去重映射、报价可行域或有效计价函数时，阻断对应完整收益计算，不静默采用相加或零值。区域EDC产品分配仍保留未参与产品的残差份额；本站不投二次②不得推出三次①份额为1。

以下旧M4字段保留作为历史接口。末节“三相位预处理”只适用于旧M4代理，不作为当前三个场景的自动默认；当前联合响应入口按主文§14.4定义，尚须校准。

2026-09-30；本轮独立审核PASS，见[审核记录](revision_M4_20260930/review_final.md)；与[主文](JP_milp_formulation.md)共同使用。原始补充的§3–7详见[用户归档](revision_M4_20260930/user_spec.md)。本文件定义采集与校验，不宣称数据已经取得。

## 第1项已确认接口：一次频率状态

2026-10-04用户确认；数学定义见主文§14.2.1。LV_FCR与HV_SPOT_FCR不再默认进入旧三相位预处理。以下是待实现的外生输入字段，不宣称已生成实际时序文件：

    scenario_id,area_id,interval_start_jst,frequency_state_id,
    weight,gamma_up,gamma_down,distribution_version,control_version,
    capacity_validity_min_mw,capacity_validity_max_mw,capacity_scaling_assumption_id,
    discretization_version,state_count,auxiliary_assumption_id,publication_vintage_id

每个半小时权重非负且和为1，响应比例在[0,1]内；同一代表状态上、下响应不能同时为正。零权重删除，退化分布允许一个状态。尾部不得截掉后无说明地归一化。权重是半小时等效时间占比，不是按编号排序的物理路径。

需校验加权响应与§13.4 alpha一致，以及11/21离散精度、叠加基线后的充放电、转换损耗、循环、保守SOC边界。容量适用域内归一化响应必须与容量决策无关，否则此接口不适用。DC辅用非负且单列，AC辅用恒定代理需登记。数据缺失不置零；上述字段不取代现有价格、设备、服务能力及信息时点依赖。


## 第2项已确认A接口：可申报组合与单一复合计价

2026-10-04用户选择A，数学定义见主文§14.3.1；覆盖前文将复合计价整体视为未知函数的表述。候选组合必须满足实际供出能力、全量内数原则及状态适用条件，不允许两个容量无耦合独立任取。

待准备的逻辑输入字段：

    native_block_id,resource_configuration_id,bid_candidate_id,
    offered_s1_mw,offered_t1_mw,composite_max_mw,
    capability_evidence_id,full_inner_quantity_validation_id,
    eligibility_domain_id,grid_validation_id,rule_vintage_id,
    composite_price_source_id,composite_price_effective,price_unit,price_role,
    price_adjustment_branch_id,formal_award_unit_assumption_id

eligibility_domain_id须解析为基线、SOC等决策的已核验线性状态域。它要验证该状态下内数已完整申报，不能仅验证能够交付已报量。资源/控制设定不能通过任意降额标签切换来隐藏内数。正容量行必须是目标二次①＋三次①组合；整包不投可行；原生块不能拆分后重新优化。

本次并未生成该组合表。至少一条已验证行及适用复合有效价格齐备后，才允许对应场景正式收益计算。综合复合均价可以作为明确代理，不能冒充对应组合或本站的真实结算单价。容量现金为有效复合单价×单单位max容量：每kW价格需乘1000，每MW价格不再转换；两者均不再乘0.5。冻结真实成交按实际正式单位保存，不由候选表重新报价。


## 第3项已确认接口：复合联合离散状态

2026-10-04用户确认基准“EDC慢变中心＋LFC去均值波动”，以及加回LFC均值、EDC格内非零波动两类敏感性；数学定义见主文§14.4.1。当前复合经济代理使用状态占比，不将下列状态编号视为时间顺序。

    area_id,interval_start_jst,activation_scenario_id,theta,
    lfc_state_id,lfc_weight,lfc_normalized_raw,lfc_normalized_mean,lfc_centered,
    edc_state_id,edc_weight,edc_center,edc_zero_mean_deviation,
    joint_weight,coupling_method,reference_pool_mapping_id,
    product_allocation_version,direction_mapping_version,assumption_version,
    quality_status,signal_stage,publication_vintage_id

若复用旧subinterval接口，必须将状态占比和实际时长路径区分，不伪造sent_time/effective_time。去均值后的LFC加权均值为零，EDC扰动加权均值为零，联合权重行/列和等于对应边际。edc_center一般为h_up*alpha_up-h_down*alpha_down；只有单位方向映射已一致时才能简写alpha_up-alpha_down。

至少包含theta=0无EDC扰动的基准、theta=1均值额外贡献情景、非零EDC波动情景。所有数值均为求解前参数，情景不能由MILP择优选择或无依据按概率合成一个收益。可分别登记独立/同向/反向耦合，不把半小时均值相关性当格内相关性。缺少波动幅值依据/假设时保持missing_assumption并报告敏感性未完成，不当作零扰动。

signal_stage标记为regional_statistical_proxy；deduplication_status需明确assumed_mean_overlap，不能标记verified_deduplicated。单产品原始边际代理继续保存用于对照，复合状态不宣称同时匹配所有单产品毛量。ICS不作为第三条响应。物理毛量与付款量继续分开；后续已确认的第4项输入/缺失处理见下一节。


## 第4项已确认接口：输入包与质量语义

**后续用户修订：电站参数正式计算时输入。** asset_config不提供硬编码功率/能量/效率/SOC/控制默认值；当前留空标deferred_runtime_input，不属于建模阶段研究缺口。运行时必填并校验。它们是单次求解的外生参数，非设备定容决策；SOC运行轨迹仍是决策。设备相关的状态和报价域绑定asset_config_version后生成/验证，不能沿用另一电站的缓存。系统参考容量、产品份额及结算映射继续独立研究。

2026-10-04用户确认。先九州2026年6月验证，再扩展原定九区域和历史期。最新完整字段契约、参数与状态见[输入包](../../../project/jp_model_closure_20261004/step4_input_package/README.md)。该包是契约、登记及源数据核查，不宣称全部生产输入已生成。

统一主键含scenario/assumption版本、JST半小时、area_id、resource/reference_pool及必要product/direction。所有源值保留来源与原单位。quality_status至少区分available、missing、missing_assumption、not_applicable、confirmed_zero、marker_requires_semantic_mapping和proxy；数值空值保持null，不把0当缺失，也不将缺失当0。

对每个场景按所使用的字段检查依赖，不能让ICS条件缺口无差别禁用一次模型。缺参考池能力时MWh代理与alpha准备状态分离；缺付款映射/价格时不进行完整利润优化，不把已知现金总和命名总收益。LV不付激活现金为用户设定的not_applicable价格依赖。待填参数不由MILP挑选或从ES静默复制。

复合C行情只能先登记综合价格代理；一次F行情的在线/离线适用性另核。地区中标量与上/下参考能力不能自动等同。空白模板排除不改变原件；有效日期、原生块及观察日缺口单独检查。实际发布时间未知时只标ex_post，不用下载时间冒充决策时可见性。


## 原始能力与激活证据

```text
interval_start_jst,interval_end_jst,area_id,reference_pool_id,
capacity_group_id,activation_channel_id,product_or_mode,native_block_id,
award_mw,reference_up_mw,reference_down_mw,
activated_up_mwh,activated_down_mwh,
paid_up_mwh,paid_down_mwh,chi_up,chi_down,
up_price_jpy_mwh,down_signed_price_jpy_mwh,activation_cash_jpy,
raw_unit,source_uri,source_revision,publication_time,quality_status
```

主键须含记录生效版本、池及通道，修订不覆盖原始文件。粒度半小时×池/区域×去重通道×方向；容量从原生块映射。币种JPY，功率MW，电量MWh，能量单价JPY/MWh，时间Asia/Tokyo。原单位保留，不二次乘1000或时长。

本站优化R不进入此原始表；award与方向参考能力不自动相等。付款池另有payment_pool_id和固定认可映射；上/下毛量不能被净量替代。数据可空，但必须附`not_applicable`、`confirmed_zero`、`missing`等语义；未知与不适用不可混用。

## 求解前归一接口

```text
interval_start_jst,area_id,reference_pool_id,activation_channel_id,
product_or_mode,alpha_up,alpha_down,h_up,h_down,chi_up,chi_down,
activation_price_up_signed,activation_price_down_signed,
model_gct,model_result_time,historical_gct,historical_result_time,
native_block_id,native_duration_h,capacity_group_id,payment_pool_id,
activation_proxy_type,price_role,quality_status
```

历史时钟仅追溯可空；模型时钟按主文统一日前。完整记录还须链接设备、事件、共享/互斥、通道映射、服务路径、原生价格单位及网格元数据，不把这些全部展开重复到时序表。

alpha可由可靠原始物理毛量/同方向参考能力计算，或直接导入带定义/来源的已核验alpha。单方向Q=0且A=0为比值未定义；模式本来不提供该方向时须通过h=0及不适用语义删除该方向，而不是制造实测零样本。

## 输入依赖

|依赖|允许处理|
|---|---|
|物理方向h>0|需有效alpha和能力/来源定义，无独立付款也不能省略|
|已确认chi=0|不需要该方向能量付款单价，保留物理响应|
|alpha可靠确认为0|该记录激活现金恒零，可不需要有效价格；不是用缺价格推断alpha=0|
|可能付费且物理激活非零|必须有合格认可映射与有符号能量价或现金/付费量推导|
|净化付款池|提供联合认可规则；不能毛通道相加重复付费|
|只有3小时激活总量|均分仅作为另命名合成场景，不能写实测半小时|
|只有三次②使用率|仅允许fit_forecast_error_utilization_proxy，不得标metered_activation|
|观察日不完整|保留缺失标记，按依赖禁用新变量；冻结非零义务受影响则停窗|

本轮未授权/实施外部批量下载、采购付费数据或发送索取邮件。采集优先官方批量文件及已授权导出；未来采集时按适用许可条件执行。

## 可复现预处理

按来源时区解析→检查唯一性及版本→原生单位转换→按同池毛方向电量构造alpha→检查非负和方向和≤1→生成每通道下/上/基线边界→排序并集→固定方向指示参数→交叉校验电量与时长。错误原记录原样留存，不能封顶、归一化或填零隐藏。

基线/实测功率只在无可靠毛电量时用于推导。一次约1秒采样是工程代理建议，不是本版重新引入设备准入门槛。没有站级高频实测时，必须标可缩放性与顺序假设，不能声称秒级重演。
