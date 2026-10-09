from pathlib import Path
import hashlib,json,datetime,re,sys,csv
sys.stdout.reconfigure(encoding='utf-8')
B=Path(__file__).resolve().parent
D=B/'supplement_20260930'
D.mkdir(exist_ok=True)
before=D/'before';before.mkdir(exist_ok=True)
files={'research_report.md':B/'research_report.md','model_handoff.md':B/'model_handoff.md','evidence_register.md':B/'evidence_register.md','research_README.md':B/'README.md','JP_README.md':B.parent/'README.md','JP_milp_formulation.md':B.parent/'model/JP_milp_formulation.md','country_status.yaml':B.parents[2]/'project/country_status.yaml'}
for name,p in files.items():
    dest=before/name
    if not dest.exists():dest.write_bytes(p.read_bytes())
user=Path('C:/Users/Tianyi/Desktop/research_report_with_JP_supplement_20260930.md')
dest=D/'user_supplied_research_report.md'
if not dest.exists():dest.write_bytes(user.read_bytes())
entries=[]
with (B/'source_inventory.csv').open(encoding='utf-8-sig',newline='') as f:
    inventory=list(csv.DictReader(f))
for r in inventory:
    if r['id'] not in {'E02','E04','E05','E07','E12','E19','J04'}:continue
    path=B/r['path'];raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==r['sha256']
    item=dict(r);item['path']='../'+r['path'].replace('\\','/')
    item['local_rechecked_on']='2026-09-30'
    if r['id'] in {'E05','E07','E12'}:
        item['web_rechecked_on']='2026-09-30；浏览工具重读，沿用已存原始快照，不冒称新增下载'
    entries.append(item)
entries.append(dict(id='U30',organization='用户提供，非官方证据',path=dest.name,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),bytes=dest.stat().st_size,original_path=str(user)))
(D/'source_manifest.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8')
(D/'acquisition_note.txt').write_text('2026-09-30：本地直连下载FAQ尝试DNS失败，未形成新HTML。浏览工具已成功重读FAQ、上限页面及产品PDF；证据使用已有E07/E12/E05不可变快照及E02/E04/E19/J04原件，不覆盖、不伪称新快照。\n',encoding='utf-8')
s=(B/'extracted/E02_1c1881b3a21a.txt').read_text(encoding='utf-8')
for t in ['(129)','なお，複合商品の場合，複合市場商品約定単位ごとに','第44条 取引会員','第46条 本市場']:
    p=s.find(t);print(t,'PDF page',re.findall(r'=== PDF PAGE (\d+) ===',s[:p])[-1:],s[p:p+480])
print('Evidence and before snapshots saved')
