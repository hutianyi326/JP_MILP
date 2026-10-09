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
