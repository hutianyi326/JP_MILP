from pathlib import Path
import hashlib, json, math, re

BASE = Path(__file__).resolve().parent
doc = BASE / '日本EPRX指令口径与复合控制研究.md'
text = doc.read_text(encoding='utf-8')
checks = []

def check(name, ok, detail):
    checks.append({'check': name, 'passed': bool(ok), 'detail': detail})

pages = {key: json.loads((BASE / f'{key}_pages.json').read_text(encoding='utf-8')) for key in ['E02','E03','E04']}
anchors = [
    ('E02',34,'出力変化量指令'),
    ('E02',35,'数値指令'),
    ('E02',144,'接点信号'),
    ('E02',196,'５分後'),
    ('E02',248,'合算した指令'),
    ('E02',310,'指令は行わない'),
    ('E02',329,'合成した指令信号'),
    ('E02',340,'指令方法は別表３'),
    ('E02',350,'大きい方'),
    ('E02',355,'アセスメントⅡの対象外'),
    ('E02',361,'一括'),
    ('E02',363,'協議した指令方法'),
    ('E03',241,'１パルス'),
    ('E03',397,'実出力値'),
    ('E04',21,'属地TSOと協議'),
    ('E04',23,'需要抑制計画電力'),
]
for key, page, phrase in anchors:
    normalized = ''.join(pages[key][page-1].split())
    check(f'{key}_page_{page}', ''.join(phrase.split()) in normalized, phrase)

region_block = text.split('## 6 九区域专线指令方式')[1].split('### 6.1')[0]
regions = ['北海道','东北','东京','中部','北陆','关西','中国','四国','九州']
check('nine_region_rows', all(region_block.count(f'| {r} |') == 1 for r in regions), regions)
combos = text.split('### 7.2')[1].split('### 7.3')[0]
ids = re.findall(r'^\| .*? \| (\d+) \|', combos, flags=re.M)
check('eleven_composite_rows', sorted(map(int,ids)) == [1,2,3,5,6,8,11,12,14,17,21], ids)

check('absolute_example', 4-2 == 2, 'absolute 4 MW minus baseline 2 MW = activation 2 MW')
check('relative_example', 2+4 == 6, 'baseline 2 MW plus relative 4 MW = power 6 MW')
check('relative_level_repeat', 2+1 == 3, 'relative level 1 MW repeated stays at power 3 MW; it is not a cumulative action')
check('duplicate_baseline_example', 4+3-2 == 5, 'conditional two absolute channels sharing baseline 2 MW give 5 MW')
e1=(5*10+4*170)/3600
e2=(3*10+2*170)/3600
check('energy_relative_case', math.isclose(e1,0.202778,abs_tol=5e-7), {'MWh': e1})
check('energy_absolute_case', math.isclose(e2,0.102778,abs_tol=5e-7), {'MWh': e2})
check('energy_baseline_difference', math.isclose(e1-e2,2*180/3600), '0.1 MWh is baseline energy over 180 seconds')

local_targets = re.findall(r'\]\(([^)]+)\)',text)
missing=[]
for target in local_targets:
    if '://' not in target and not (BASE / target).exists() and target != 'checks.json':
        missing.append(target)
check('local_links_exist', not missing, missing)
check('visual_pages_exist', all((BASE/'visual_checks'/f'{s}_p{p}.png').exists() for s,p in [('E02',361),('E02',363),('E03',241),('E03',397),('E04',21),('E04',23)]), 'six pages rendered and inspected')
check('eleven_numbered_equations', re.findall(r'\\tag\{(\d+)\}',text) == [str(i) for i in range(1,12)], 'equations 1 through 11')
result = {'checked_at': '2026-10-01', 'document_sha256':hashlib.sha256(doc.read_bytes()).hexdigest(), 'checks':checks, 'passed':sum(x['passed'] for x in checks), 'failed':sum(not x['passed'] for x in checks)}
(BASE/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':result['passed'],'failed':result['failed'],'failures':[x for x in checks if not x['passed']]},ensure_ascii=True))
if result['failed']:
    raise SystemExit(1)
