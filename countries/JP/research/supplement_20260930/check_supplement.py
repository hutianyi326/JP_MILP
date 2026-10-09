from pathlib import Path
import re,json,hashlib,math,csv
D=Path(__file__).resolve().parent;B=D.parent
files=[B/'research_report.md',B/'spot_eprx_coupling_supplement_20260930.md',B/'model_handoff.md',B/'evidence_register.md',B/'README.md',B.parent/'README.md']
checks={};missing=[];blocks=[]
for p in files:
    s=p.read_text(encoding='utf-8')
    for target in re.findall(r'!?\[[^\]\n]*\]\(([^\n]*?)\)',s):
        if re.match(r'^(?:[a-zA-Z]+:|#)',target):continue
        path=target.strip('<>').split('#')[0]
        if path and not (p.parent/path).exists():missing.append([p.name,target])
    blocks+=re.findall(r'\$\$(.*?)\$\$',s,re.S)
checks['active_relative_links']=not missing
checks['formula_delimiters_and_braces']=all(p.read_text(encoding='utf-8').count('$$')%2==0 for p in files) and all(x.count('{')==x.count('}') for x in blocks)
checks['M3_file_byte_identical']=(D/'before/JP_milp_formulation.md').read_bytes()==(B.parent/'model/JP_milp_formulation.md').read_bytes()
old=(D/'before/research_report.md').read_text(encoding='utf-8');new=(B/'research_report.md').read_text(encoding='utf-8')
section=lambda s:s.split('## JP-02 ')[1].split('## JP-03 ')[0]
checks['JP02_data_and_statistics_unchanged']=section(old)==section(new)
bad=[]
entries=json.loads((D/'source_manifest.json').read_text(encoding='utf-8'))
for r in entries:
    p=D/r['path'];raw=p.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=r['sha256'] or len(raw)!=int(r['bytes']):bad.append(r['id'])
checks['all_eight_source_hashes']=len(entries)==8 and not bad
checks['capacity_units_example']=2*1000*6==12000==2*6000
checks['four_MW_cross_zero_power']=2-(-2)==4 and -2+4==2
checks['half_hour_energy_example']=round(2*.5/.95,4)==1.0526 and round(.8+2*.5/.95,4)==1.8526
checks['two_hour_energy_example']=round(2*2/.95,4)==4.2105 and round(.8+2*2/.95,4)==5.0105
checks['five_minute_energy_example']=round(2*(5/60)/.95,4)==.1754
checks['composite_units_not_global_max']=sum(max(r) for r in [(2,1),(1,2)])==4 and max(sum(x) for x in zip((2,1),(1,2)))==3
checks['gross_threshold_unit_conversion']=(10000-7000)/2/1000==1.5
inventory=list(csv.DictReader((B/'source_inventory.csv').open(encoding='utf-8-sig',newline='')))
checks['original_336_sources_preserved']=len(inventory)==336 and all(hashlib.sha256((B/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in inventory)
report={'date':'2026-09-30','checks':checks,'passed':sum(checks.values()),'total':len(checks),'display_formulas_checked':len(blocks),'missing_links':missing,'source_errors':bad,'solver_run':False,'backtest_run':False,'visual_render_verified':False}
(D/'checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True,indent=2));assert all(checks.values())
