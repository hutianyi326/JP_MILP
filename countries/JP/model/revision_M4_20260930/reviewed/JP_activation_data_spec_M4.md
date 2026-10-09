# M4激活数据接口

2026-09-30；与[主文](JP_milp_formulation.md)共同使用。原始补充的§3–7详见[用户归档](revision_M4_20260930/user_spec.md)。本文件定义采集与校验，不宣称数据已经取得。

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
