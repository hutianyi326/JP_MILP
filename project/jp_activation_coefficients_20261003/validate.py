import csv
import hashlib
import io
import json
import math
import re
import zipfile
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DOC = ROOT / 'countries/JP/model/JP_milp_formulation.md'
checks = {}
evidence = []

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def check(name, condition):
    checks[name] = bool(condition)

paths = {
    'lfc': ('project/jp_activation_downloads_20261001/samples/kyushu_lfc_202606_4c5f53588b32.csv', '4c5f53588b3228fa25e69d33fd1598f0c50aa61343279d39ef7e02c96b8d1ee8'),
    'regional': ('project/jp_activation_downloads_20261001/samples/kyushu_jukyu_202606_259b239ae928.zip', '259b239ae928a27aae0524b37a3240cb25d8b1375019110752fdd6d092cb99a1'),
    'ics': ('data/raw/JP/activation_sources_20261001/ics_basis_202606.csv', '474f609911d7595a41381e9257e6f633ef6903edce48ee93bec9f3f9d1cef3ef'),
}
for key, (rel, expected) in paths.items():
    actual = sha(ROOT / rel)
    check(key + '_original_hash', actual == expected)
    evidence.append({'id': key, 'path': rel, 'sha256': actual})

lfc = list(csv.reader(io.StringIO((ROOT / paths['lfc'][0]).read_bytes().decode('cp932'))))
check('lfc_date_slot', lfc[1][:4] == ['20260601', '1', '0:00', '0:30'])
check('lfc_source_numbers', [float(lfc[1][i]) for i in (4,5,6,16,17,18)] == [.03,.08,-.03,-11,78,-82])
with zipfile.ZipFile(ROOT / paths['regional'][0]) as z:
    member = '11120_TSO9_0_202606_20260812132500030.csv'
    regional = list(csv.reader(io.StringIO(z.read(member).decode('cp932'))))
check('regional_date_slot', regional[1][:4] == ['20260601','1','0:00','0:30'])
check('regional_source_numbers', [float(regional[1][i]) for i in (7,10,8)] == [-34412,398289,8127])
ics_bytes = (ROOT / paths['ics'][0]).read_bytes()
for encoding in ('utf-8-sig','cp932'):
    try:
        ics = list(csv.reader(io.StringIO(ics_bytes.decode(encoding))))
        break
    except UnicodeDecodeError:
        continue
drow = next(row for row in ics if row[0] == 'D' and row[1] == '20260601' and int(row[2]) == 1)
check('ics_source_numbers', [float(drow[i]) for i in (21,39,57,75,93)] == [111560,1,5,13.78,5.06])

phi = lambda x: math.exp(-x*x/2)/math.sqrt(2*math.pi)
Phi = lambda x: (1+math.erf(x/math.sqrt(2)))/2
def H(m,s):
    return s*phi(m/s)+m*Phi(m/s) if s > 0 else max(m,0)

mu, sd, dt = -11, 40, .5
up, down = dt*H(mu,sd), dt*H(-mu,sd)
check('lfc_normal_expected_values', abs(up-5.528658650769268)<1e-10 and abs(down-11.028658650769268)<1e-10)
check('lfc_normal_net_identity', abs(up-down-mu*dt)<1e-12)
check('proxy_scales', math.isclose((.08-(-.03))/4,.0275) and (78-(-82))/4 == 40)

# Independently integrate the piecewise clipped frequency response in z-space.
# d and b below are numerical test parameters, not recommended Japanese settings.
def integrate(fn, lo=-10, hi=10, n=200000):
    step=(hi-lo)/n
    return step*sum(fn(lo+(i+.5)*step) for i in range(n))
frequency_tests=[]
for m,s,d,b in [(.03,.0275,.01,.1),(-.02,.04,.005,.2),(0,.02,0,.08)]:
    au=(H(-m-d,s)-H(-m-d-b,s))/b
    ad=(H(m-d,s)-H(m-d-b,s))/b
    nu=integrate(lambda z:min(1,max(-(m+s*z)-d,0)/b)*phi(z))
    nd=integrate(lambda z:min(1,max(m+s*z-d,0)/b)*phi(z))
    frequency_tests.append({'mean':m,'sd':s,'deadband':d,'span':b,'closed_up':au,'numeric_up':nu,'closed_down':ad,'numeric_down':nd})
    check('frequency_integral_'+str(len(frequency_tests)), max(abs(au-nu),abs(ad-nd))<1e-8 and au>=0 and ad>=0 and au+ad<=1+1e-12)
check('zero_variance_limit', math.isclose((H(.02,0)-H(-.08,0))/.1,.2,abs_tol=1e-12))

# Check conservation and capacity-time aggregation with transparent toy values.
check('net_to_gross_identity', all(math.isclose(max(n,0)+c-(max(-n,0)+c),n) for n in [-5.5,0,7] for c in [0,1,10]))
hour_alpha = (10*.5*.2+20*.5*.8)/(10*.5+20*.5)
check('hour_capacity_weighted_alpha', math.isclose(hour_alpha,.6) and not math.isclose(hour_alpha,(.2+.8)/2))

doc = DOC.read_text(encoding='utf-8')
base = (OUT/'before/JP_milp_formulation.md').read_text(encoding='utf-8')
def equations(s):
    return re.findall(r'\$\$(.*?)\$\$',s,re.S)
check('M4_baseline_equations_preserved', equations(base) == equations(doc.split('## 13.')[0]))
check('display_math_delimiters_balanced', doc.count('$$')%2==0)
check('no_lost_qquad_escape', re.search(r'(?<!\\)qquad',doc) is None)
links=[]
for target in re.findall(r'\]\(([^)]+)\)',doc):
    if target.startswith(('https://','http://','#')):
        continue
    resolved = (DOC.parent / unquote(target.split('#')[0])).resolve()
    links.append({'target':target,'exists':resolved.exists()})
check('local_links_exist', all(x['exists'] for x in links))

result={'date':'2026-10-03','scope':'New section 13 and integration boundary; no solver/backtest or empirical calibration',
    'document':str(DOC.relative_to(ROOT)), 'document_sha256':sha(DOC),
    'checks':checks,'passed':sum(checks.values()),'total':len(checks),'raw_evidence':evidence,
    'normal_example':{'up_mwh':up,'down_mwh':down,'net_mwh':up-down},
    'frequency_numerical_checks':frequency_tests,'local_links':links,
    'limits':['No empirical normality test','No identified product shares or reference capacity','No intra-interval path feasibility','No JP MILP solver run']}
(OUT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':result['passed'],'total':result['total'],'failed':[k for k,v in checks.items() if not v],'missing_links':[x['target'] for x in links if not x['exists']]},ensure_ascii=False))
