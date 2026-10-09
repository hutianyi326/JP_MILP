from pathlib import Path
B=Path(__file__).resolve().parent

def change(s,a,b):
    assert s.count(a)==1,(a[:100],s.count(a))
    return s.replace(a,b)

p=B/'research_report.md';s=p.read_text(encoding='utf-8')
s=change(s,'研究日：2026-09-28。历史区间：2025-01-01至2026-08-31，Asia/Tokyo。对象：A类2 MW/8 MWh，以及规模待定的B类高压项目。地域：九个主体供电区域，排除冲绳及离岛。','初始研究日：2026-09-28；补充修订：2026-09-30。历史区间仍为2025-01-01至2026-08-31，Asia/Tokyo；九个主体供电区域，排除冲绳及离岛。当前建模对象为总名义2 MW/8 MWh低压成员聚合（LV）与默认同规模、可参数化的特別高圧项目（EHV）。正文保留A/B电压资格分支作为市场研究；不能把其早期规模设定替代当前用户策略。')
s=change(s,'**交付状态：第四轮 Astra / high 独立审核 PASS，P0/P1/P2=0，主线程已验收，允许带输入门禁的MILP数学说明。** 历史可执行数据及项目输入门禁仍保留，详见[第四轮审核与验收](review_round4_result.md)。','**交付状态：原第四轮研究已PASS；2026-09-30补充修订待独立审核，不沿用原PASS作为新增内容的结论。** 本轮增加现货—EPRX耦合、可报价容量、复合计费和M3交接，详见[补充附件](spot_eprx_coupling_supplement_20260930.md)。原审核见[第四轮审核与验收](review_round4_result.md)；项目输入及历史门禁继续有效。')
s=change(s,'## JP-03 两类项目准入和电压路径','## JP-03 两类项目准入和电压路径\n\n【用户策略更新】当前LV仅一次离线路径，EHV排除一次离线、可选其余合格产品；均以实际认证为前提。以下A/B分支说明市场上可能的资格，不等于当前模型启用全部分支。低压2 MW/8 MWh为多个实际合格成员合计，不视为单点低压接入；EHV默认同规模比较，实际接网电压与合同仍须确认。')
s=change(s,'【数据补正】J16—J18官方年度日内CSV','【补充解释：承诺冻结】按申报截止、结果收到、实际交付三个时刻记账。日前已成交头寸不因EPRX中标而删除；日内修改净计划仍须支持旧容量义务。容量约定冻结未来服务义务，并非自前日下午开始禁止电池运行。M3可在完美信息下联合安排各市场数量，但保留真实事件状态和关门约束；历史周产品须覆盖完整尾部。详见[补充第1节](spot_eprx_coupling_supplement_20260930.md#1-交易顺序与承诺冻结)。\n\n【数据补正】J16—J18官方年度日内CSV')
s=change(s,'### 市场实绩和竞争含义','''### 可报价能力与持续服务

【研究解释】可报价MW由认证、响应链路、注册/合同模式、基线功率空间、能量与恢复能力共同限制；不是直接等于设备铭牌，也不要求永远报满。充放电各2 MW时，计划充电2 MW到放电2 MW的几何上调跨度为4 MW；但仍须通过跨零、产品方向、SOC及POI检查。需要下调响应时单独检查其真实要求，不默认上调容量等于对称下调量。[E04 pp15–18；E05 p2；补充第2节]

【工程解释】连续中标不能每半小时重复使用同一份能量；最低持续时间不是累计调用上限。离线一次持续时间栏未设定，不能据此取消能量保障或套在线5分钟。实际SOC用PCS侧有序充放电更新，考核端与并网点先做有效端口换算。假设算例及M3 P5–P7对应见[补充第3节](spot_eprx_coupling_supplement_20260930.md#3-soc与连续服务)。

### 复合产品的约定单位和计费

【事实】一次至三次①复合报价中其他产品为内数；每个正式复合约定单位按其中各产品约定量的最大值确定复合量，须保持其可供出。容量费用以正式单位/资源的适用价格和复合计费量核算，不将内数逐项重复收费。[E02定义(129)，PDF pp20–21、p27、第46条p67；E07复合/计费问答]

【事实，现行FAQ解释】无效内数仍在复合量内，不能自动释放相同能力；但该无效产品不要求在对应出力上满足其产品性能。FAQ未标独立生效日期，历史回填须另核版本。[E07“無効ΔkW約定量”]

【解释/假设】一个正式复合单位的四项内数均2 MW，单价6 JPY/(kW·30分钟)，该格容量费12,000 JPY而非48,000 JPY。多个独立正式单位须先各自取最大再分别计费；三次②不得未经依据并入一次至三次①的同一个max。同资源多单和自动抵扣未核分支继续禁用。[补充第4节]

【M3边界】当前每格至多一个已核实模式；允许复合候选不代表任意组合已经实现。固定比例、共同计费及联合能力/调用映射须先审核，才可作为模式输入。单模式是计算假设，不是市场普遍禁止多产品。

### 价格、机会价值与M3口径

【事实】上限按交付日切换；2026-09-01的10.00仅为期外更新，不用于截至8月31日的研究。超限报价不等于系统拒单，精算按E19及E02第44、46条处理；涉及返还时不能一律仅用约定价和上限的min。[E19 p1；E02 pp65–67]

【建模解释】官方每kW容量价转为M3每MW价格只乘一次1000，计费不再乘0.5。当前外生价格、理想全额成交是明确基准，不优化申报价或中标概率。可选的“有/无容量义务”毛收益差分析仅衡量本模型口径的容量补偿阈值，不是完整商业保本价或监管报价公式；退化、手续费等仍按M3排除，不重复加恢复购电。详见[补充第5–6节](spot_eprx_coupling_supplement_20260930.md#5-容量价格与现金)。

### 市场实绩和竞争含义''')
s=change(s,'不平衡样本2025年北陆最大值200','【补充解释：四类账本】分别保留现货合同、容量承诺、实际物理路径及现金结算。报价MW、中标MW、占用MW、计费MW、激活MWh和认可付费MWh不混用。剩余偏差=实际电量−最终计划电量−完整BG补正，不能再重复减付费调节量。一次-only没有单独电量支付的合同路径仍保留SOC、损耗和必要偏差；恢复购电受关门及容量承诺约束。字段定义见[补充第7节](spot_eprx_coupling_supplement_20260930.md#7-输入输出与现有模型对应)。\n\n不平衡样本2025年北陆最大值200')
old='研究交接不等于建模输入发布：资格按设备容量、电压、通信、日期和产品形成矩阵；规则候选与未核实项见`model_handoff.md`。需首先闭合离岛统计、历史版本、产品结算接口、区域费用、B项目参数与历史成交可得性。独立审核后由主线程决定是否验收，仍不得直接启动策略、MILP、生产实现或收益回测。'
new='研究交接不等于正式模型输入发布：资格按设备容量、电压、通信、日期和产品形成矩阵；见[建模交接](model_handoff.md)。当前M3数学说明已另行通过审核；本轮研究补充需单独复核。离岛诊断边界、未核历史资格/结算及真实项目认证、端口、调用等门禁继续有效。M3毛收益排除的费用不再作为该限定目标的必填门禁；不得据此认定费用为零或放行生产实现、真实收益回测。'
s=change(s,old,new)
start=s.index('## 数学阶段最终交付')
s=s[:start]+'''## 当前数学交付与本次补充

[MILP数学说明](../model/JP_milp_formulation.md)当前为M3-R1：完美信息毛收益，LV一次离线、EHV其余合格路径。数学审核见[M3审核](milp_M3_review_final.md)，公式可读性复核见[M3-R1记录](JP_M3_readability_change_notes.md)；M2为历史版本。本轮未修改51条数学公式，也未增加真实竞价或任意复合组合实现。

详细补充：[现货—EPRX耦合及容量报价](spot_eprx_coupling_supplement_20260930.md)。本轮来源与修改前快照在[supplement_20260930](supplement_20260930/source_manifest.json)；新增研究内容独立审核后才形成新的研究验收结论。代码、真实收益回测和实测求解性能未批准状态保持。
'''
p.write_text(s,encoding='utf-8')

p=B/'model_handoff.md';s=p.read_text(encoding='utf-8')
s=change(s,'基线V2；2026-09-28。状态：第四轮独立研究审核PASS、主线程已验收，**modeling_approved=true（仅数学MD），implementation_approved=false**。本文不提供MILP方程、优化策略或收益测算。','基线V2；补充更新2026-09-30。原研究第四轮PASS，M3-R1数学说明另行通过；本轮新增交接内容待独立审核。**modeling_approved=true仅指既有数学设计，implementation_approved=false、historical_backtest_approved=false**。正式方程见[M3-R1](../model/JP_milp_formulation.md)，本文件负责研究需求与接口，不声称新增组合已经实现。')
s=change(s,'下表适用于九个研究主体区域的全国规则框架；','【当前用户策略】LV为合格低压成员聚合总量2 MW/8 MWh，仅一次离线；EHV默认同规模、可参数化，排除一次离线。实际资格和历史版本仍独立控制。下表A/B是较广的资格研究分支，不覆盖或扩大用户策略。\n\n下表适用于九个研究主体区域的全国规则框架；')
s=change(s,'最终验证结果另见`validation_report.md`。独立审核与修复记录另见`review_record.md`及review_round2_result.md（本轮新增错误已关闭，整体NOT_PASS）。','原研究数据验证见`validation_report.md`；review_record.md及review_round2_result.md保存早期NOT_PASS过程，当前已验收研究结论见review_round4_result.md。本轮新增字段与解释单独送审。')
s=s.replace('## 第三轮交接更新（待独立审核）','## 第三轮交接历史更新（已由第四轮验收）')
s=s.replace('尚待数学独立审核。','其后M3数学及M3-R1排版已经独立审核通过。')
start=s.index('## 数学阶段最终交付')
s=s[:start]+'''## 当前数学交付

[M3-R1数学文档](../model/JP_milp_formulation.md)、[M3审核](milp_M3_review_final.md)、[排版复核](JP_M3_readability_change_notes.md)为当前数学交付。M2保留为历史；本次未修改数学文件。

## 2026-09-30补充交接

详细规则、推导和工程假设见[耦合与报价附件](spot_eprx_coupling_supplement_20260930.md)。新增需求不得自动变成生产配置。

|ID|内容|类别及定位|当前模型/处理|
|---|---|---|---|
|C19|截止、结果收到、交付时刻及冻结订单分开|F/I；E05 p3、J04；补充第1节|E3、滚动账本；理想接受不篡改事件状态|
|C20|逐复合约定单位取最大，独立单位分别计费|F/I；E02 pp20–21/27/67；E07；补充第4节|固定记录可直接核算；自由内数优化未启用|
|C21|无效内数不释放复合量，但不要求该无效产品性能|F；E07问答，当前页面未标生效日|历史日期须证据；valid_flag与占用分开|
|C22|连续服务能量和恢复路径不能重复使用|I/A；补充第3节，工程参数|P5–P7；实际路径与硬能力检验分开|
|C23|上限日期、返还分支、价格单位分别处理|F/I；E19 p1、E02 pp65–67|O1预处理；不统一min，不重复1000/0.5|
|C24|容量补偿阈值采用同口径毛收益差|A；补充第6节|可选分析未实施；不是监管公式或净利润保本|

|字段组|必须保存|作用与限制|
|---|---|---|
|版本和时刻|rule_version、delivery_time_JST、bid_gate_closure、award_received_at、ID_gate_closure|结果收到不得用预计时刻替代；期外规则不回填|
|资源资格|resource_id、voltage_class、metering_mode、cross_zero_allowed、product_mask、PQ_MW|用户策略、正式资格、历史日期取交集|
|申报记录|bid_id、bid_group_id、product_mode、offered_MW、bid_price、minimum_acceptable_award|bid_price为记录/输入，非当前决策变量；新增申报与固定成交分开|
|正式约定|award_unit_id、award_MW、product_inner_MW、valid_flag|复合单位不能与电能合同事件j混用；保留实际拆分|
|能力及计费|occupied_MW、billable_MW、downward_required_MW|同一独立能力不可重复出售；不默认对称下调|
|物理与计量|PCS功率、POI/考核端映射、逐成员SOC、有序激活|不从净30分钟电量推断全部子步合格|
|结算|actual_activation_MWh、payable_activation_MWh、BG_correction_MWh、residual_imbalance_MWh|完整BG补正后不重复扣认可付费量|
|价格|raw_price_unit、model_price_unit、price_role、refund_branch|每kW至每MW转换一次；历史均价不是本站保证成交价|

当前仍取外生价格、理想全额接受、逐格至多一个已审核模式。未确认的同资源多单、复合自动分配、联合激活、PQ/下调范围、离线能量保障和恢复控制权限禁止默认为已闭合。本轮不恢复经济情景树、CVaR、价格档二元或全状态枚举。官方最低量/刻度用于适用申报单位，不机械约束成交内数；普通容量及长期脱碳收入继续不进入M3毛收益目标。
'''
s=s.replace('G05/G08的现行机器点、低压、多会员、零分母及BG接口补证见history_closure_round3.md','G05/G08的现行机器点、低压、多会员、零分母及BG接口补证见[历史闭合](../topics/history_closure_round3.md)')
p.write_text(s,encoding='utf-8')

p=B/'evidence_register.md';s=p.read_text(encoding='utf-8')
s+='''\n## 2026-09-30耦合与报价补充证据\n\n新增引用用途，不覆盖旧原件：E02定义(129)PDF pp20–21、p27及第44/46条pp65–67支持复合单位/供出与容量返还；E07官方FAQ的“複合約定”“約定料金の計算に用いる量”“無効ΔkW約定量”支持现行复合解释；E12页面第5–6项与E19 p1脚注1–4支持上限和日期。E04 pp15–18、E05 pp2–3、J04相关条款沿用原登记。\n\n2026-09-30已重读本地原件，并由浏览工具复核E07/E12/E05现行页面。FAQ发布日期未标明，不能按访问日倒推历史生效；E19的9月变更为研究期外。精确原始访问时间、URL、大小、哈希及副本路径见[本次来源清单](supplement_20260930/source_manifest.json)，详细采用位置见[补充来源表](spot_eprx_coupling_supplement_20260930.md#8-第一方来源与采用定位)。用户提供的U30文档仅为研究线索，不是第一方证据。\n'''
p.write_text(s,encoding='utf-8')
for p in [B/'README.md',B.parent/'README.md']:
    s=p.read_text(encoding='utf-8')
    prefix='' if p.parent==B else 'research/'
    s+='\n## 2026-09-30研究补充\n\n本轮补充待独立审核：[现货与EPRX耦合及容量报价]('+prefix+'spot_eprx_coupling_supplement_20260930.md)、[修订主报告]('+prefix+'research_report.md)、[建模交接]('+prefix+'model_handoff.md)。既有M3-R1公式保持不变；新增内容不自动继承旧研究PASS。\n'
    p.write_text(s,encoding='utf-8')
p=B.parents[2]/'project/country_status.yaml';s=p.read_text(encoding='utf-8')
s=change(s,'    research_review: "countries/JP/research/review_round4_result.md"','    research_review: "countries/JP/research/review_round4_result.md"\n    supplemental_research_status: "20260930_pending_independent_review"\n    supplemental_research_document: "countries/JP/research/spot_eprx_coupling_supplement_20260930.md"')
p.write_text(s,encoding='utf-8')
print('Report, handoff, evidence and entry points updated; mathematical file untouched.')
