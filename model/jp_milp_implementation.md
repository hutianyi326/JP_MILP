# 日本 MILP 第一版：实现与运行

2026-10-04，由主 agent 编写，独立review agent复核PASS（P0/P1/P2均为0），见[验收记录](../project/jp_implementation_20261004/review_and_acceptance.md)。这是具备输入校验、求解和审计的条件测算程序。真实项目参数、区域校准与结算映射仍须提供，合成验证通过不等于历史收益已得到验证。

后续四国首轮输入接入：新增[假设和组装接口](../project/jp_first_run_inputs_20261004/README.md)，并针对两日联调增加严格等价的状态方向排序约束、收紧 HiGHS 可行性容差；审计容差未放宽。这些后续改动尚未独立 Agent 复审，不能沿用上述旧代码指纹的 PASS。验证及求解限制见[新验证记录](../project/jp_first_run_inputs_20261004/validation_report.md)。

## 1. 模型范围和结构

以[日本数学文档](../countries/JP/model/JP_milp_formulation.md)第14节最新确认方案为准。三个独立场景为 LV_FCR、HV_SPOT_FCR、HV_SPOT_S1_T1。LV 与高压一次均限于不含余力利用合同例外的一次场景，保留原现货权限，关闭激活现金，激活物理、损耗、SOC、循环仍在。现货权限由实际提供的有限合同事件定义；没有提供日内事件就没有日内自由交易。

参考 [ES_MILP](https://github.com/hutianyi326/ES_MILP) 的数据适配、内核、perfect/rolling、ledger、diagnostics 和 project 入口分层。读取版本为 70651210d0ad98ac820644754508f76363d2c799。日本没有复用西班牙三相位或默认设备数值；参考副本保持只读。

|文件|职责与对应方程|
|---|---|
|src/jp_milp/config.py|全部电站参数、JST、单位与求解配置；§14.7|
|src/jp_milp/inputs.py|规范化输入、原生块、时钟、付款、候选域与能力路径门禁；§14.6|
|src/jp_milp/sources.py|九州 LFC、EDC 相关表、ICS 只读字段抽取；§13；不自动生成缺失校准值|
|src/jp_milp/activation.py|正态正部期望、频率分箱、LFC 单位容量归一、EDC 分配、联合边际耦合；§13、S1-F1、S3-F1—4|
|src/jp_milp/linear.py|稀疏 MILP 和有限界推导，SciPy/HiGHS；不使用任意大 M|
|src/jp_milp/core.py|净现货、容量网格/组合表、联合物理、保守 SOC、连续服务路径、现金与预算|
|src/jp_milp/audit.py|从数值决策独立复算功率、SOC、毛量、损耗、现金、EFC、全容量与服务路径|
|src/jp_milp/budget.py|共同覆盖样本折算年度600 EFC，观察年独立额度；§9|
|src/jp_milp/rolling.py|两日规划/首日执行、唯一订单冻结、原子事务、恢复指纹、正式/观察期分离|
|src/jp_milp/sensitivity.py|均值归属、非零EDC波动、独立/同向/反向耦合；重优化与固定承诺压力分开|
|project/run_jp_milp.py|统一运行入口|

## 2. 运行输入

输入为一个 UTF-8 JSON 包，这是[十张逻辑表契约](../project/jp_model_closure_20261004/step4_input_package/input_contract.json)的可执行规范化视图。第一版没有把未知字段从原始CSV自动补齐，也没有声称十张生产表已全部生成。已有原表可用 sources.py 抽取统计；需完成工程/研究参数登记后组装输入。没有提供的设备参数不会自动取历史例子。

交付主键及其引用必须是规范JST字符串，例如2026-07-01T00:00:00+09:00。UTC交付键即使代表同一时刻也会被明确拒绝，需预处理统一转换；gate/result可以用带时区的等价时刻。月度与年度归属均再按JST解析。

|输入字段|对应逻辑表/内容|
|---|---|
|asset|asset_config：version、充放功率MW、名义与可用能量MWh、初末SOC、效率、AC/DC辅用、POI进出上限、service/POI仿射系数及有效域；全必填|
|intervals|activation_states 与 activation_assumptions：JST start、area、asset_version、availability、states、payment；每格30分钟、连续无缺口|
|states|正权重 weight（和为1）、f/s/t 三个有符号单位容量响应系数；合成 response=f×qF+s×qS+t×qT|
|joint_metadata|复合场景的 theta、lfc_mean、edc_center、normalization_id、coupling；敏感性另需 lfc_marginal；检查去均值与EDC均值恒等式|
|payment|settlement_mapping：mapping_id、basis=joint_physical_gross、上下认可系数、signed_price_up/down（JPY/MWh）；LV与高压一次认可系数0且价格null（明确不适用）|
|spot_orders|market_prices：唯一id、market=DA/ID、weights（交付格到功率权重）、买卖上限MW、同价JPY/MWh、grid_mw（0明确连续松弛）、gate、result|
|capacity_blocks|原生块id、intervals、资产版本、统一D−1 14:00/15:00时钟、有效价格JPY/MW/30min、价格及能力依据、完整方向极端、服务路径|
|candidates/domain|bid_candidates/bid_domains：cS、cT、common=max、full_inner_validation_id、状态域验证与线性条件；仅复合场景|
|bid_rules|复合新报价s/t/common分别适用的网格、最低量、注册上限；不得自行把单产品1MW最小值施加给两个内数|
|service_requirements|每产品、每方向的系数及持续时间、证据ID；extremes和services必须覆盖所有非零方向要求|
|initial_frozen|唯一id到已存在净现货量或容量记录（f/s/t/common/candidate_id）；未知或不支持的义务报错|
|annual_budgets_efc|按JST年份给定共同预算；同年观察期共用余额。budget.py可按明确共同覆盖生成，不按场景选择重新计算|
|provenance / assumption_version|publication_vintages、source_mapping、研究参考池与版本链；原始哈希、信息时点、质量与工程假设保留在此|
|classification|仅支持 SYNTHETIC_VALIDATION 或 EX_POST_CONDITIONAL；没有预测/真实可执行收益标签|

功率基线在设备净AC侧。现货服务端计划满足 B=service_scale×baseline+service_offset；状态响应在服务端定义，设备侧增量为 response/service_scale。POI另按其仿射映射校验。全端口参数必须显式输入；理想同端口可显式填1/0，程序不默认采用。

容量价格已经是每30分钟的价，目标不再乘0.5。原始JPY/kW/30min仅转换一次×1000。现货与激活价格为JPY/MWh，方向现金符号包含在signed_price中，下调不再重复取负。

复合候选条件为 terms 的线性和 sense rhs。每项term包含 interval、variable（baseline/soc/soc_lower/soc_upper）、coefficient。空条件仅在 domain_validation_id 明确证明整个适用域时使用；validation_id 是可追溯证据引用，代码无法代替技术认证或证明资料真实。候选表有限最优不能称连续能力域全局最优。能力相关版本换站必须重新生成并验证。

## 3. 物理与服务保证范围

状态权重是确定的等效时间占比，没有顺序。程序按每个状态的“现货基线＋合成响应＋AC辅用”确定真实充放方向，计算一次DC吞吐，再用半小时 A/B 递推SOC，并施加 e−B≥Emin、e+A≤Emax。转换损耗与辅用分列。不会把全部上调量当放电量，不会把两个产品毛量相加，也不会截断超功率响应。

服务见证与期望状态物理分开。每原生块的每个半小时起点，分别从该格保守下/上SOC起步，执行 services 中给定的连续分段；跨半小时沿相邻基线衔接，同一路径SOC只初始化一次。分段规定 hours 与 f/s/t 系数，持续期间使用起点承诺容量。能力服务路径不产生收入、不扣实际循环账本。这是有限列举路径保证，且从保守界出发可能更严格；不等于所有真实秒级控制轨迹。输入路径必须明确合法的连续履约范围。

窗口外缺少能力尾部时，新块整块禁用并标原因，已有非零义务停窗。本版不自动创建窗口外的新交易或扩展经济窗口；跨窗/跨日原生合同被显式拒绝，不能暗中拆块。标准日本30分钟/3小时同日块支持。额外尾部或非标准跨日合同需先按接口扩展后审核。

本运行期间关门的新增现货合同，完整交付必须落在其关门日开始的两日窗口内；不满足时预检拒绝提前关门模板。每次提交还扫描全体当日到期事件，凡未纳入求解且没有既有冻结记录的订单均停止提交。关门恰在执行日终点时留给下一窗处理，不套用首日开始前已过关门的零订单约定。

共享复合只检查各产品完整方向和给定额外联合极端，不把两个内数机械相加。可选 response_envelope 是明确的工程假设；没有它也继续检查合成功率的设备/SOC边界。付款当前支持“合成毛量×明确方向认可系数×签名价格”这一分支；其他净化、基线补正、跨池不可分结算不假冒支持，输入会拒绝。

## 4. 运行和输出

现有项目环境已经有NumPy/SciPy，HiGHS随SciPy提供。依赖版本见[requirements](../project/jp_implementation_20261004/requirements.txt)。从项目根目录运行：

```powershell
& ./.venv-es-milp/Scripts/python.exe -X utf8 project/run_jp_milp.py --input <完整输入.json> --preflight-only
& ./.venv-es-milp/Scripts/python.exe -X utf8 project/run_jp_milp.py --input <完整输入.json> --end 2026-06-04T00:00:00+09:00 --output <新输出目录>
```

正式起止为JST午夜，输入包含终点之后一个完整观察日。输出目录必须新建；恢复时加 --resume，输入、设备及代码指纹必须一致。不把未经决策的第一天旧日前订单追溯补报；过关门且无初始订单固定为0。真实初始义务必须填入initial_frozen。

输出包括 manifest（完整输入和指纹）、逐窗不可覆盖事务、checkpoint、executed_30min.csv、committed_orders.json、monthly_cash.json、solver_metrics.json、summary.json。逐窗保存全部状态、服务路径、禁用原因、独立审计、规划收益、求解界与gap。正式报告仅汇总首日执行格；观察日和终端估值只入规划目标。达到时限但有经审计可行解可提交并报告非零gap；无可行解停窗，保留失败前账本。BLOCKED的完整收益cash为null，executed_cash仅表示此前已提交部分，不能解读为完整情景零收益。

复合敏感性入口增加 --edc-sensitivity <扰动映射.json>。每格必须提供非零、零均值扰动及正权重；尺度需要研究或工程依据。套件分别求基准、加回均值、EDC独立/同向/反向情景，并固定基准全部承诺做压力检验；没有免费改基线/补交易/重置SOC。两类收益不能混作同一策略结果。

## 5. 验证和未解决事项

合成输入仅保存在测试和验证输出，不是运行默认。回归覆盖原生3小时块、旧容量非网格值、单次复合计费、候选状态域、净合同反向交易、负激活价、非单位端口、SOC连续、保守界、服务链、跨年预算、观察期、恢复指纹、不可行与缺失门禁。详见[验证记录](../project/jp_implementation_20261004/validation_report.md)。

11/21/41频率分位箱另按响应转折点分开，实际状态数会增加。示例对比用于检查电量/循环/收益及耗时；不能替代新设备、新月份的精度验证。建议接受阈值为收益、DC吞吐/EFC相对差各≤1%，并检查差值是否被求解gap掩盖；这是实施精度标准，不是监管标准。接近0时须用明确绝对容差。

仍需正式输入：电站参数；频率/LFC统计缩放与κ、同池方向Qref、EDC产品份额及隐含双向量；经过验证的完整内数组合和适用域；有效容量价格适用映射、激活认可/价格；完整观察日。缺失不能填零。第一版没有自动证明复合全量内数，也没有开展2025—2026完整真实数据收益测算。

## 6. 规则、解释与假设

规则事实沿用现有[证据登记](../countries/JP/research/evidence_register.md)及数学§13.10、§14.3.1：EPRX《取引規程》v18（2026-07-01实施，复合第31条，PDF336页）、《取引ガイド》v10（同日，PDF294页）、官方复合FAQ；来源访问记录2026-10-04在已保存研究中。官方链接：[规程](https://www.eprx.or.jp/outline/docs/kitei_ver.18_260701.pdf)、[指南](https://www.eprx.or.jp/outline/docs/guide_ver.10_260701.pdf)、[FAQ](https://www.eprx.or.jp/contact/jukyuchoseishijo/faq.html)。历史版本适用仍由数据预处理负责，不能把v18默认追溯到全期。

研究解释：公开LFC/EDC相关/ICS统计可以支持区域代理，但不能识别全部产品毛调用、格内耦合与单站付费。程序只读保留这一边界。

建模假设：统一日前时钟、理想全额成交、完美信息、有限状态、保守SOC、有限服务路径、外部完整内数组合、EDC慢变中心＋去均值LFC、循环预算及尾端估值。本次代码没有新增日本官方规则。

2026-10-05：一次单独中标结算修正覆盖此前高压一次付款口径；偏差结算未纳入，现金不是完整净收益。见[修正与审核记录](../project/jp_first_run_inputs_20261004/settlement_correction_20261005.md)。

2026-10-05全期接入更新：新增显式历史时钟与到期/冻结义务扩窗策略，覆盖四国1月1日至8月30日及8月31日观察日。使用此策略时，上文“固定两日、不自动扩窗”的限制由新策略取代；旧默认接口不变。周交易原生三小时容量不拆分，跨日SOC/循环/冻结义务连续，LFC k固定1。已处理冻结重放中的HiGHS预处理误报无解，保持同一矩阵与时间预算重试。完整假设、官方来源、验证与运行入口见[全期k=1说明](../project/jp_shikoku_202601_0830/full_run_k1.md)。这不是全期正式项目收益，也未新增独立审核。

2026-10-05收益执行补充：用户确认EV指LV一次场景，2 MW/8 MWh；每天恢复50% SOC，日内能量恢复基线恒定，允许按四国日前价格代理买电或出售调频余电。该方式属于建模假设，不是日本市场规定；一次激活现金为零，但调用能量、损耗和循环均计入。高压两场景为100 MW/200 MWh，偏差结算按用户指令排除。

本轮数值实现支持HiGHS和SCIP。主线程批准在完整等容量菜单等价条件下压缩整数变量、固定功率直接计算充放电，以及通过相同原始矩阵和独立物理审计检验连续精修结果。LV日能量守恒推导的基线上下界仅收紧冗余可行域；放松容量网格仅用于构造起点，最终订单仍由原整数网格求解并审计。数值状态合并误差和40项回归结果记录于`project/jp_revenue_20261005/`；全期完成状态以各场景summary和最终账本验证为准。

2026-10-05最终验收：EV一次、高压现货＋一次、高压现货＋二次①/三次①复合均完成242日、11,616个半小时。40项回归及独立审核通过，三组事务链、物理量、SOC、循环预算、冻结记录和24行月度账本全部核验通过。正式结果与求解精度、代理及费用边界见[收益测算结果](../project/jp_revenue_20261005/收益测算结果.md)和`final_validation.json`。辅助代码的历史身份覆盖缺口在源码快照说明中保留，不追溯伪造历史证据。
