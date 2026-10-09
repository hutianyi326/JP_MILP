"""Register the separately authorized immutable workbook and reconcile report status."""
from pathlib import Path
import json,hashlib
B=Path(__file__).resolve().parent
p=B/'../../data/raw/JP/enecho_ep002_2025_1-2.xlsx'
raw=p.read_bytes()
rows=[json.loads(x) for x in (B/'sources.jsonl').read_text(encoding='utf8').splitlines()]
if not any(x['id']=='M04' for x in rows):
    r=dict(id='M04',url='https://www.enecho.meti.go.jp/statistics/electric_power/ep002/xls/2025/1-2-2025.xlsx',status='ok',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),path='../../data/raw/JP/enecho_ep002_2025_1-2.xlsx',accessed_at='2026-09-28 (researcher acquisition date; exact time not retained)',content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    with (B/'sources.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(r,ensure_ascii=False)+'\n')
replacements={
'research_report.md':{
'资源能源厅月度装机绝对量未成功取得，九区域绝对MW、研究区总量、截至2026-08-31的装机变化尚未闭合，也未用比例倒推。':'本轮已取得METI 2025财年府县装机工作簿M04，含2025年4月至2026年3月；详见[边界与装机修订](../../countries/JP/boundary_revision_20260928.md)。附件逐列给出绝对MW和两期变化，但完整府县代理不是精确TSO区域，也未扣除离岛；关西代理核电为0是将福井整县归北陆造成，不能用于判断关西核电。九区域本土绝对MW、研究区总量及2026-08-31断面仍未闭合，不用比例倒推。',
'阅读顺序：本文':'新增专题附件：[九区边界和装机](../../countries/JP/boundary_revision_20260928.md)、[历史规则与结算逐版本修订](../../countries/JP/history_settlement_revision_20260928.md)。附件与本文同属整包审核；未闭合事项保持待确认。\n\n阅读顺序：本文'},
'model_handoff.md':{
'历史维度：2025-01—2026-03-13未闭合完整旧规程；即使现行路径可申请，历史同类项目仍须旧规则和当时合同佐证。2026-03-14—06-30已确定关键切换，但细节以当时版本补齐；2026-07-01后E02/E03为留存完整文本。':'历史维度：六段EPRX原规程已归档，关键条款逐版比较见[历史结算修订](../../countries/JP/history_settlement_revision_20260928.md)。这不代表JEPX、所有罚则、BG约款及历史合同已连续闭合；现行可申请路径不能自动回填历史。',
'资源能源厅入口403；留存O10/O11供给计划比例':'已取得M04府县绝对量及两期代理变化，O10/O11计划比例/财年末PV风电展望；代理映射及局限见boundary_revision_20260928.md',
'变更公告/回顾已留存，完整当前版已留存':'六段EPRX原规程及关键条文比较已补，见history_settlement_revision_20260928.md；其他市场与合同链仍缺',
'E02/E04与ICS价格已取得；监管公式旧新日期未闭合':'E02/E04、六段EPRX结算条文及ICS价格已取得；资源分支与BG端到端映射尚未闭合'},
'README.md':{'十二项完整性检查':'最新完整性检查','- analysis/：':'- [九区边界与装机修订](../../countries/JP/boundary_revision_20260928.md)：府县绝对量代理、年度展望、逐岛证据与限制。\n- [历史规则与结算修订](../../countries/JP/history_settlement_revision_20260928.md)：六段EPRX关键条款及仍待闭合分支。\n- analysis/：'}
}
for name,reps in replacements.items():
    p=B/name;t=p.read_text(encoding='utf8')
    for old,new in reps.items():
        if old in t:t=t.replace(old,new)
        elif new not in t:raise ValueError((name,old))
    p.write_text(t,encoding='utf8')
# Main-thread acceptance corrections across the report/annex boundary.
for name in ['research_report.md','revision_notes.md']:
    p=B/name;t=p.read_text(encoding='utf8').replace('E02別冊複合約定第32条','E02別冊三次調整力①第32条')
    p.write_text(t,encoding='utf8')
p=B/'../../countries/JP/history_settlement_revision_20260928.md'
t=p.read_text(encoding='utf8')
t=t.replace('第44—45条 PDF p42/印刷p39','第44条 PDF p42/印刷p39；第45条 PDF pp42—43/印刷pp39—40')
t=t.replace('第44条 PDF p64/印刷p60','第44条 PDF pp64—65/印刷pp60—61').replace('第44条 PDF p65/印刷p61','第44条 PDF pp65—66/印刷pp61—62')
t='\n'.join(x.replace('第46条 PDF pp46—47/印刷pp42—43','第46条 PDF pp46—48/印刷pp42—44') if x.startswith('| S2 |') else x for x in t.splitlines())+'\n'
t=t.replace('E36 第45条 PDF p42/印刷p39；E37/E38 第46条 PDF pp46—47/印刷pp42—43','E36 第45条 PDF pp42—43/印刷pp39—40；E37 第46条 PDF pp46—48/印刷pp42—44；E38 第46条 PDF pp46—47/印刷pp42—43')
p.write_text(t,encoding='utf8')
