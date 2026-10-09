# 九州2026年6月输入核查

核查日期：2026-10-04。时区Asia/Tokyo，样本为6月1日00:00至7月1日00:00（右端不含），共1,440个半小时。

频率/LFC、EDC相关统计、ICS工况及现货价格共同具有所检数值字段的半小时：**1424 / 1,440**。再匹配一次F和综合复合C行情记录：**1424 / 1,440**。这只是同键数值覆盖，不等于产品归属、方向容量、结算或模型参数已闭合。

|数据|6月记录数|唯一半小时|所检数值齐备|7月1日记录数|
|---|---:|---:|---:|---:|
|lfc|1440|1440|1440|0|
|edc_related|1440|1440|1440|0|
|ics|1440|1440|1424|0|
|spot|1440|1440|1440|48|
|capacity_F|1440|1440|1440|48|
|capacity_S1|1440|1440|1440|48|
|capacity_T1|1440|1440|1440|48|
|capacity_C|1440|1440|1440|48|

## 已发现的处理边界

- LFC文件末尾有48行空白模板，已在读取时排除；原始文件未改写，不把空白模板当7月观测。
- ICS九州不平衡量和供需状态在6月7日第32—43格共12格为空；另4格不平衡量为0而供需状态为‘-’，须按字段字典映射，不直接当缺失或数值0。1424是全部所检字段均为数值的严格覆盖数，并不代表另外16格的全部数据不可用。
- ICS只影响使用对应工况分层的输入，不自动阻断未使用该条件的一次场景。若另建不依赖该条件的参数情景，须独立命名并说明适用范围，不能暗中填补。
- 一次F行情未在该标准化表按在线/离线标记，不能直接认定LV/高压模式专属价格；综合复合C不是二次①＋三次①特定组合的独立价格。
- source与TSO价格/中标量是不同口径，不能任取分母。价格为0不自动代表本站可按0结算，须同时检查成交状态与price_role。
- 已有地区中标量不代表已获得与LFC/EDC统计池匹配的上/下方向参考能力；不能由上调采购量补造下调分母。
- 完整6月滚动测算所需7月1日激活观察日输入未包含在本次月文件中。现货/容量观察日行见上表。可先在六月内验证短窗口，不免费重置SOC。
- 设备、控制、产品份额、报价状态域和激活付款映射尚未准备成已验证输入，三个场景均未就绪完整利润优化。

## 字段及来源

### lfc

本地：[原文件](../../../project/jp_activation_downloads_20261001/samples/kyushu_lfc_202606_4c5f53588b32.csv)。SHA256：4c5f53588b3228fa25e69d33fd1598f0c50aa61343279d39ef7e02c96b8d1ee8。编码：cp932。
官方：[来源链接](https://www.kyuden.co.jp/td_power_usages/csv/lfc/jukyu_LFC_kyushu_202606.csv)。本次读取已下载文件，未重新在线核验，发布时间以原登记为准。

|目标字段|原列（从1计）|原字段|
|---|---:|---|
|frequency_mean_hz|5|周波数偏差_30分平均値（Hz）|
|frequency_upper_equivalent_hz|6|周波数偏差_+2σ相当値（Hz）|
|frequency_lower_equivalent_hz|7|周波数偏差_-2σ相当値（Hz）|
|lfc_mean_mw|17|既LFC動作量_30分平均値（MW）|
|lfc_upper_equivalent_mw|18|既LFC動作量_+2σ相当値（MW）|
|lfc_lower_equivalent_mw|19|既LFC動作量_-2σ相当値（MW）|

### edc_related

本地：[原文件](../../../project/jp_activation_downloads_20261001/samples/kyushu_jukyu_202606_259b239ae928.zip)。SHA256：259b239ae928a27aae0524b37a3240cb25d8b1375019110752fdd6d092cb99a1。编码：cp932。
官方：[来源链接](https://www.kyuden.co.jp/td_power_usages/csv/kouhyo/jukyu/11120_TSO9_0_202606.zip)。本次读取已下载文件，未重新在线核验，发布时间以原登记为准。

|目标字段|原列（从1计）|原字段|
|---|---:|---|
|own_area_own_mo_kwh|8|自エリア対応_自MO_エリア内稼働量(kWh)|
|forecast_error_other_kwh|11|想定誤差他エリア内稼働量(kWh)|
|other_area_exchange_kwh|9|他エリア対応_自MO_エリア外送受電量(kWh)|

### ics

本地：[原文件](../../../data/raw/JP/activation_sources_20261001/ics_basis_202606.csv)。SHA256：474f609911d7595a41381e9257e6f633ef6903edce48ee93bec9f3f9d1cef3ef。编码：cp932。
官方：[来源链接](https://www.imbalanceprices-cs.jp/api/1.0/imb/basis/202606)。本次读取已下载文件，未重新在线核验，发布时间以原登记为准。

|目标字段|原列（从1计）|原字段|
|---|---:|---|
|kyushu_imbalance_kwh|22||
|kyushu_surplus_shortage|40||
|kyushu_partition|58||

### spot

本地：[原文件](../../../countries/JP/research/analysis/spot_30min_JST_expost.csv)。SHA256：40fcec1d723eb1c0ed0443ed37c58998e093af47f178f5ec4df16e5e047b53e4。编码：utf-8-sig。
追溯：[官方证据登记](../../../countries/JP/research/evidence_register.md)及既有lineage；行情汇总不是本站结算证据。

|目标字段|原列（从1计）|原字段|
|---|---:|---|
|九州|11|九州|

### capacity

本地：[原文件](../../../countries/JP/research/analysis/eprx_awards_native_blocks_expost.csv)。SHA256：bc338540944ca10bcd5a6cb71c9e9387af96555b11f5901c9800800a7303f1d1。编码：utf-8-sig。
追溯：[官方证据登记](../../../countries/JP/research/evidence_register.md)及既有lineage；行情汇总不是本站结算证据。

|目标字段|原列（从1计）|原字段|
|---|---:|---|
|avg_price_source_JPY_kW_30min|15|avg_price_source_JPY_kW_30min|
|avg_price_TSO_JPY_kW_30min|18|avg_price_TSO_JPY_kW_30min|
|award_source_MW|10|award_source_MW|
|award_TSO_MW|19|award_TSO_MW|
|duration_h|4|duration_h|

详细结果：[source_coverage.json](source_coverage.json)。本次没有修改原始CSV或既有处理后数据。
