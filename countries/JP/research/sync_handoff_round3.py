from pathlib import Path
B=Path(__file__).resolve().parent
p=B/'model_handoff.md';s=p.read_text(encoding='utf-8')
replacements={
'|G04 ':'|G04 调整力成交与激活|真实项目调用和历史决策版本|年度ZIP已补六产品九区全研究期量价，763416行；三次②预测误差使用率262656行|成交不等于个体可成交量；实测激活/私有计量和当时发布版本仍须取得|',
'|G06 ':'|G06 区域费用与接网|项目净收入与真实地点比较|九区现行电压费率、储能特措及发电侧机制已补，见regional_closure_round3.md及storage_tariff_round3.md|未核历史版本、月度调整、地点折扣及代理商业报价不能默认零|',
'|G09 ':'|G09 容量合同及历史财年|具体项目容量收入|年度工作簿、期待/应札/管理容量、普通和长期合同差异见capacity_closure_round3.md|对应年度的实际中标容量、月管理参数及合同金额仍属项目输入|',
'|G08 ':'|G08 计划/激活/不平衡接口|真实偏差成本|完整现行机器点/低压/多会员/零分母分支见history_closure_round3.md；前轮缺项继续独立复核|适用BG合同、补正通知、真实指令及计量；历史版本按登记启用|'
}
s='\n'.join(next((new for key,new in replacements.items() if line.startswith(key)),line) for line in s.splitlines())+'\n'
s=s.replace('G01—G06、G08—G10是研究证据/数据缺口，不能归咎于用户尚未提供B类参数。','G01/G02为公开统计边界缺口；G03/G04的个体可成交性、激活及历史版本与已完成市场级统计分开；G05及未核历史费用仍为规则证据限制；G06/G08/G09中的私人合同参数与公开规则缺口分别登记。不能归咎于用户尚未提供B类参数。')
p.write_text(s,encoding='utf-8')
p=B/'settlement_branches.md';s=p.read_text(encoding='utf-8').replace('待完整提取|','第三轮完整展开见history_closure_round3.md|').replace('缺少这一接口仍属于G08，不能声称下列案例已经关闭它。','现行完整分支已在第三轮history_closure_round3.md补充；实际合同及补正接口仍需输入，下列假设案例不能证明项目端到端结算通过。');p.write_text(s,encoding='utf-8')
