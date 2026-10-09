"""One-time main-thread integration; preserves earlier review records."""
from pathlib import Path
B=Path(__file__).resolve().parent
p=B/'research_report.md';s=p.read_text(encoding='utf-8')
a=s.index('**交付状态：');b=s.index('\n\n',a)
s=s[:a]+'**交付状态：第三轮修订，尚待独立整包复核，研究和建模均未宣布通过。** 前轮NOT_PASS记录保留于review_round2_result.md。本轮补充官方年度调整力成交包、九区储能费率特措、容量年度工作簿、计量结算分支和边界检索；新增内容详见revision_round3.md。资料获取跨至2026-09-29，研究信息基线和历史期不变。'+s[b:]
dup='新增专题附件：[九区边界和装机](../topics/boundary_revision_20260928.md)、[历史规则与结算逐版本修订](../topics/history_settlement_revision_20260928.md)。附件与本文同属整包审核；未闭合事项保持待确认。\n\n'
s=s.replace(dup+dup,dup)
s=s.replace('EPRX结果页明确自动大量获取须事先承诺；本次使用公开年度汇总，未自动抓取整个历史逐时结果库。2026-04—08的逐时容量报价/中标/激活序列仍缺，不据此输出调频收入回测。','第三轮已由官方年度ZIP取得完整研究期六产品九区容量成交量价，见[调整力成交比较](auction_comparison_round3.md)。2026年8月为速報，其余使用确报；实测激活仍缺，不能输出真实项目收益回测。')
s=s.replace('【缺口】开始供给期限、价格调整、期待容量具体系数及全部历史合同差异尚未闭合；','【补证】开始供给期限、期待容量工作簿及2024/2025长期合同差异已补于[容量补证](../topics/capacity_closure_round3.md)，仍须按具体合同年度和项目参数使用；')
s=s.replace('由于区域网络费、2026调整力时序和离岛合规基本面尚未齐全，','第三轮已补九区需求侧标准费率及储能特措、完整历史调整力成交量价；研究选择以东北为建模案例基准、东京/九州为对照，具体依据见[成交比较](auction_comparison_round3.md)。由于接入点合同、真实激活和离岛合规基本面仍有待确认项，')
s+='\n\n## 第三轮补证阅读索引\n\n本节与正文共同组成当前研究版本，前轮审核档案不追溯改写。\n\n- [历史规则与计量结算完整分支](../topics/history_closure_round3.md)：历史版本、离线枠、机器点/低压/BG分支。\n- [容量工作簿与历史合同](../topics/capacity_closure_round3.md)：年度系数、期待/管理/应札容量与普通/长期合同。\n- [九区边界进一步核查](../topics/boundary_closure_round3.md)：官方原始边界与不可分离数据限制，不能将代理量转为合规实际量。\n- [九区储能费率特措](../topics/storage_tariff_round3.md)及[费用与使用率](regional_closure_round3.md)。\n- [完整调整力成交区域比较](auction_comparison_round3.md)：本轮候选案例选择的新增量化依据。\n'
p.write_text(s,encoding='utf-8')
p=B/'regional_closure_round3.md';s=p.read_text(encoding='utf-8')
s=s.replace('九区特措、线损、法定附加费与历史适用仍由独立费用附件继续核查。','九区2026-04-01特措、线损及法定附加费已逐区补证，见[储能费用附件](../topics/storage_tariff_round3.md)；历史适用待核部分保持明确。')
s=s.replace('**未据此宣布最终优胜区域**，仍需完整调整力成交价格、真实参与配置与费用、接入限制等证据。最终区域选择尚未关闭。','随后取得完整调整力成交档案，当前案例选择更新为东北基准、东京和九州对照，见[成交比较](auction_comparison_round3.md)；仍不宣布投资优胜或项目已可接网。')
s=s.replace('仍未关闭：费用完整历史链及九区储能特措适用、全产品区域成交时序与实测激活、单一札单位、最终区域选择。','后续补证：九区现行储能特措与全产品区域成交时序已取得；参见储能费用附件及成交比较。仍待确认费用完整历史链、项目实测激活、单一札原单位及实际合同参数。')
p.write_text(s,encoding='utf-8')
p=B/'README.md';s=p.read_text(encoding='utf-8');lines=s.splitlines();seen=set();lines=[line for line in lines if not (line.startswith('- [') and (line in seen or seen.add(line)))];s='\n'.join(lines)+'\n'
s+='\n第三轮当前补证：[修订总表](revision_round3.md)、[成交量价比较](auction_comparison_round3.md)、[费用/使用率补证](regional_closure_round3.md)、[容量](../topics/capacity_closure_round3.md)、[计量/历史](../topics/history_closure_round3.md)、[储能特措](../topics/storage_tariff_round3.md)、[边界](../topics/boundary_closure_round3.md)。这些附件待独立整包审核，前轮NOT_PASS并未自行改为通过。\n'
p.write_text(s,encoding='utf-8')
p=B/'model_handoff.md';s=p.read_text(encoding='utf-8');s+='\n\n## 第三轮交接更新（待独立审核）\n\nG04中的历史公开成交缺口已补：六类产品、九区、608日，763,416个原生块区域值，2026年8月速報单独标记；实测激活和历史决策可见版本仍缺。G06现行九区标准费率及储能特措已补，历史版本和具体合同不能默认相同。G09年度容量工作簿、管理/期待/应札容量及历史合同差异已补。G05/G08的现行机器点、低压、多会员、零分母及BG接口补证见history_closure_round3.md，以该附件当前修订为准，历史未核项仍禁用。G01/G02按基线V2允许的不可拆分数据缺口登记；不得把诊断基本面或府县代理升级为模型输入。\n\n本轮候选研究案例：东北为基准，东京/九州作对照；这不是已认证项目或净收益排名。用户新增要求的“2MW/8MWh低压”暂同时保留单点资格待核与低压资源聚合两条解释；特別高圧方案规模参数化，可用2MW/8MWh作等规模比较，不能凭名义规模批准电压路径。最终数学化须先通过研究独立审核。\n'
p.write_text(s,encoding='utf-8')
