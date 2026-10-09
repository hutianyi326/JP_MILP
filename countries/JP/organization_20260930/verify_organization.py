"""Read-only package checks; writes only this migration's verification report."""
from pathlib import Path
import re,json,hashlib,csv,ast,os
ROOT=Path(__file__).resolve().parents[3]
JP=ROOT/'countries/JP'
AUDIT=Path(__file__).resolve().parent
manifest=json.loads((AUDIT/'migration_manifest.json').read_text(encoding='utf-8'))
rows=manifest['files']
checks={}
checks['all_676_files_present']=len(rows)==676 and all((ROOT/r['new_path']).is_file() for r in rows)
checks['no_original_files_left']=all(not (ROOT/r['old_path']).is_file() for r in rows)
bad=[]
for r in rows:
    if r['immutable'] and hashlib.sha256((ROOT/r['new_path']).read_bytes()).hexdigest()!=r['sha256_before']:
        bad.append(r['new_path'])
checks['immutable_hashes_unchanged']=not bad
links=[];missing=[]
for r in rows+[{'new_path':'countries/JP/README.md','immutable':False}]:
    if r['immutable'] or not r['new_path'].endswith('.md'):continue
    p=ROOT/r['new_path']
    for target in re.findall(r'!?\[[^\]\n]*\]\(([^\n]*?)\)',p.read_text(encoding='utf-8-sig')):
        if re.match(r'^(?:[a-zA-Z]+:|#)',target):continue
        path=target.strip('<>').split('#')[0]
        if not path:continue
        links.append([r['new_path'],target])
        if not (p.parent/path).exists():missing.append(links[-1])
checks['active_document_links_exist']=not missing
syntax=[]
for r in rows:
    if r['immutable'] or not r['new_path'].endswith('.py'):continue
    p=ROOT/r['new_path']
    try:ast.parse(p.read_text(encoding='utf-8-sig'))
    except SyntaxError as e:syntax.append([r['new_path'],str(e)])
checks['active_python_syntax']=not syntax
source_errors=[]
with (JP/'research/source_inventory.csv').open(encoding='utf-8-sig',newline='') as f:
    inventory=list(csv.DictReader(f))
for r in inventory:
    p=JP/'research'/r['path']
    if not p.is_file():source_errors.append([r['id'],'missing',r['path']]);continue
    data=p.read_bytes()
    if len(data)!=int(r['bytes']) or hashlib.sha256(data).hexdigest()!=r['sha256']:
        source_errors.append([r['id'],'hash mismatch',r['path']])
checks['source_inventory_paths_and_hashes']=not source_errors
old=AUDIT/'before_path_edits/model/JP_milp_formulation.md'
new=JP/'model/JP_milp_formulation.md'
formulas=lambda p: re.findall(r'\$\$(.*?)\$\$',p.read_text(encoding='utf-8'),re.S)
checks['all_51_milp_formulas_unchanged']=len(formulas(new))==51 and formulas(old)==formulas(new)
status=(ROOT/'project/country_status.yaml').read_text(encoding='utf-8')
status_paths=re.findall(r'"(countries/JP/[^"\n]+)"',status)
checks['country_status_paths_exist']=bool(status_paths) and all((ROOT/p).exists() for p in status_paths)
report={'date':'2026-09-30','checks':checks,'moved_files':len(rows),'immutable_files':sum(r['immutable'] for r in rows),'local_links_checked':len(links),'official_sources_checked':len(inventory),'missing_links':missing,'immutable_hash_errors':bad,'syntax_errors':syntax,'source_errors':source_errors,'solver_or_backtest_run':False}
(AUDIT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True,indent=2))
assert all(checks.values())
