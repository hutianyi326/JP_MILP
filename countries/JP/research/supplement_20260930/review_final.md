# 日本研究2026年9月30日补充独立审核

日期：2026-09-30。结论：**PASS，P0＝0、P1＝0、P2＝0**。主线程验收本轮研究补充；本结论不继承原第四轮PASS，也不重写原审核记录。

审核角色配置：gpt-6-astra / medium；审核员/root/jp_es_readability_review，仅只读核查，未委派、未修改文件。此为角色配置记录，不冒称额外运行时档位证明。

## 审核范围

- [修订主报告](../research_report.md)、[耦合与容量报价附件](../spot_eprx_coupling_supplement_20260930.md)、[建模交接](../model_handoff.md)。
- 官方证据登记、日本/研究目录入口、project/country_status.yaml新增补充状态。
- [用户补充原件](user_supplied_research_report.md)、[修改前快照](before)、[来源清单](source_manifest.json)、[采用对照](change_log.md)。

## 独立结论

|重点|结论|
|---|---|
|复合容量|每个正式约定单位分别取最大量；独立单位分别计费；无效内数与性能要求分开，符合E02/E07|
|价格与版本|E02第44/46条返还分支与普通上限处理分开；E19日期正确，9月为研究期外|
|单位与物理|MW/kW和半小时现金换算正确；SOC、连续义务和恢复交易边界清楚|
|容量补偿阈值|限定q>0、同口径毛收益；多块分母、不可行与限时界有说明；不是监管报价公式|
|模型边界|保持M3外生价格、理想接受的毛收益基准；不新增价格优化或未经审核的复合组合实现|

独立只读检查：7项官方原件加U30共8份哈希匹配；223个本地链接目标有效；MILP与修改前快照字节相同，51条显示公式未变；旧审核记录和本次新增内容的状态区分清楚。首轮即通过，没有待关闭P0/P1/P2事项。

## 审核快照

审核时三份主要文件SHA256如下，副本保存在[reviewed](reviewed)：

|文件|SHA256|
|---|---|
|research_report.md|81ae8e067ac31430b19f02890dffe49578df752bdb5f2d654bf573179fe5b383|
|spot_eprx_coupling_supplement_20260930.md|4ae686556b79444582ccf2bc6ad7c800528629f3fb561746bf56ba794777cf6c|
|model_handoff.md|b0d2f7293fdc2f28c5dc6d15d23a4b82fb0d4ea39c9fbdbf42fd0de2fcb10fbb|

其后仅更新审核状态、验收链接及入口元数据，正式交付哈希见[delivery_manifest.json](delivery_manifest.json)。主线程13项检查见[checks.json](checks.json)，包括336份原始来源、JP-02统计不变、MILP字节不变和数学算例。

## 保留限制

本轮采用EPRX规程、FAQ、产品日程、价格通知及JEPX规则；事实、解释、假设分开。具体项目PQ、下调范围、离线能量保障、未核历史复合分支、联合调用、计量/BG、恢复权限和METI正式定价口径仍按门禁处理，未被假设关闭。

不批准生产实现或真实收益回测；未运行MILP、性能基准或正式结算回放，未验证阅读器视觉渲染。本轮不重验全部历史研究内容，原数据统计与原审核边界保留。
