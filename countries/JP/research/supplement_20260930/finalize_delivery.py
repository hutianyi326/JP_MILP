from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent;B=D.parent;ROOT=B.parents[2]
reviewed=D/'reviewed';reviewed.mkdir(exist_ok=True)
names=['research_report.md','spot_eprx_coupling_supplement_20260930.md','model_handoff.md']
expected=['81ae8e067ac31430b19f02890dffe49578df752bdb5f2d654bf573179fe5b383','4ae686556b79444582ccf2bc6ad7c800528629f3fb561746bf56ba794777cf6c','b0d2f7293fdc2f28c5dc6d15d23a4b82fb0d4ea39c9fbdbf42fd0de2fcb10fbb']
for name,h in zip(names,expected):
    raw=(B/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==h,name
    target=reviewed/name;assert not target.exists();target.write_bytes(raw)
replacements={
'research_report.md':[
('**交付状态：原第四轮研究已PASS；2026-09-30补充修订待独立审核，不沿用原PASS作为新增内容的结论。**','**交付状态：2026-09-30补充修订独立审核PASS，P0/P1/P2均为0，主线程已验收。** 见[本轮审核](supplement_20260930/review_final.md)；原第四轮记录保留，本轮结论不继承旧PASS。'),
('本轮研究补充需单独复核。','本轮研究补充已通过单独复核。'),
('新增研究内容独立审核后才形成新的研究验收结论。','新增研究内容已通过[独立审核](supplement_20260930/review_final.md)并形成本轮验收结论。')],
'spot_eprx_coupling_supplement_20260930.md':[
('状态：待本轮独立审核。本附件与[研究主报告](research_report.md)、[建模交接](model_handoff.md)共同送审；原第四轮PASS不自动覆盖本次新增内容。','状态：本轮独立审核PASS，P0/P1/P2均为0；见[审核记录](supplement_20260930/review_final.md)。本附件与[研究主报告](research_report.md)、[建模交接](model_handoff.md)一并验收，原第四轮记录保留。')],
'model_handoff.md':[
('本轮新增交接内容待独立审核。','本轮新增交接内容已独立审核PASS，见[本轮记录](supplement_20260930/review_final.md)。'),
('本轮新增字段与解释单独送审。','本轮新增字段与解释已单独审核通过。')]
}
for name,pairs in replacements.items():
    p=B/name;s=p.read_text(encoding='utf-8')
    for a,b in pairs:assert s.count(a)==1,(name,a);s=s.replace(a,b)
    p.write_text(s,encoding='utf-8')
for p in [B/'README.md',B.parent/'README.md']:
    s=p.read_text(encoding='utf-8');prefix='' if p.parent==B else 'research/'
    s=s.replace('本轮补充待独立审核：','本轮补充已独立审核PASS，P0/P1/P2均为0；[审核记录]('+prefix+'supplement_20260930/review_final.md)：')
    s=s.replace('新增内容不自动继承旧研究PASS。','新增内容经本轮独立审核，未继承旧研究PASS。')
    p.write_text(s,encoding='utf-8')
p=ROOT/'project/country_status.yaml';s=p.read_text(encoding='utf-8')
s=s.replace('supplemental_research_status: "20260930_pending_independent_review"','supplemental_research_status: "20260930_PASS_role_config_gpt-6-astra_medium"\n    supplemental_research_review: "countries/JP/research/supplement_20260930/review_final.md"\n    supplemental_information_rechecked_on: "2026-09-30"')
p.write_text(s,encoding='utf-8')
paths=[B/n for n in names]+[B/'evidence_register.md',B/'README.md',B.parent/'README.md',ROOT/'project/country_status.yaml',B.parent/'model/JP_milp_formulation.md',D/'review_final.md',D/'source_manifest.json',D/'change_log.md']
manifest={'date':'2026-09-30','review':'PASS','issues':{'P0':0,'P1':0,'P2':0},'reviewer_role_configuration':'gpt-6-astra / medium','implementation_approved':False,'historical_backtest_approved':False,'files':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
(D/'delivery_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS status, review snapshots and delivery manifest saved.')
