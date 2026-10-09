"""Read-only inventory of downloaded JP data, with Shikoku coverage detail."""
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import csv, io, zipfile, json, math, hashlib

ROOT=Path(__file__).resolve().parents[2]
START=datetime.fromisoformat('2025-01-01T00:00:00+09:00')
END=datetime.fromisoformat('2026-09-01T00:00:00+09:00')
EXPECTED={START+timedelta(minutes=30*i) for i in range(29184)}
OUT=Path(__file__).parent

def finite(x):
    try: return math.isfinite(float(x))
    except (ValueError, TypeError): return False

def records(path):
    with path.open(encoding='utf-8-sig',newline='') as stream:
        yield from csv.DictReader(stream)

def span(times):
    return dict(first=min(times).isoformat(),last=max(times).isoformat(),rows=len(times),unique=len(set(times)),
                missing_formal=len(EXPECTED-set(times)),observation_20260901=sum(END<=t<END+timedelta(days=1) for t in times))

result={'date':'2026-10-04','scope':'local files only; no new download; no source edits','timezone':'Asia/Tokyo'}
analysis=ROOT/'countries/JP/research/analysis'
rows=list(records(analysis/'spot_30min_JST_expost.csv'))
result['spot']=span([datetime.fromisoformat(r['timestamp']) for r in rows])
result['spot']['missing_by_area']={area:sum(not finite(r[area]) for r in rows) for area in ['北海道','東北','東京','中部','北陸','関西','中国','四国','九州']}
for filename in ('intraday_30min_JST_expost.csv','imbalance_30min_JST_expost.csv'):
    values=[r for r in records(analysis/filename) if 'area' not in r or r['area']=='四国']
    result[filename]=span([datetime.fromisoformat(r['timestamp']) for r in values])
cap=defaultdict(lambda:dict(times=[],quality=Counter(),missing_price=0,zero_source_award=0,zero_tso_award=0,native_rows=0,durations=Counter()))
for r in records(analysis/'eprx_awards_native_blocks_expost.csv'):
    if r['area']!='四国':continue
    v=cap[r['product']]; t=datetime.fromisoformat(r['timestamp_JST']); duration=float(r['duration_h'])
    v['native_rows']+=1;v['durations'][str(duration)]+=1;v['quality'][r['quality']]+=1
    v['missing_price']+=not finite(r['avg_price_source_JPY_kW_30min'])
    v['zero_source_award']+=float(r['award_source_MW'])==0
    v['zero_tso_award']+=float(r['award_TSO_MW'])==0
    v['times'].extend(t+timedelta(minutes=30*i) for i in range(round(duration*2)))
result['shikoku_capacity']={k:dict(span(v.pop('times')),**v) for k,v in cap.items()}
raw=ROOT/'data/raw/JP/shikoku_20260930'
lfc=[];edc=[];sources=[]
for path in sorted(raw.iterdir()):
    if path.suffix not in ('.csv','.zip'):continue
    sources.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    if path.suffix=='.zip':
        with zipfile.ZipFile(path) as archive:
            members=[(name,archive.read(name)) for name in archive.namelist() if name.endswith('.csv')]
    else:members=[(path.name,path.read_bytes())]
    for name,blob in members:
        encoding='utf-8-sig' if blob.startswith(b'\xef\xbb\xbf') else 'cp932'
        parsed=list(csv.reader(io.StringIO(blob.decode(encoding))))
        data=[r for r in parsed[1:] if r and len(r[0])==8 and r[0].isdigit()]
        if 'LFC' in name:lfc.extend(data)
        else:edc.extend(data)
def localtime(row):
    day=datetime.strptime(row[0],'%Y%m%d').replace(tzinfo=START.tzinfo)
    return day+timedelta(minutes=30*(int(row[1])-1))
lv=span([localtime(r) for r in lfc]);valid=[r for r in lfc if all(finite(r[i]) for i in (4,5,6,16,17,18))]
lv.update(numeric_frequency_lfc=len(valid), first_numeric=localtime(valid[0]).isoformat(),
          all_numeric_columns_blank=sum(all(not x.strip() for x in r[4:]) for r in lfc),
          missing_numeric_by_day=dict(Counter(r[0] for r in lfc if not all(finite(r[i]) for i in (4,5,6,16,17,18)))),
          frequency_abs_mean_gt1_by_day=dict(Counter(r[0] for r in lfc if finite(r[4]) and abs(float(r[4]))>1)))
result['shikoku_lfc']=lv
formal_edc=[r for r in edc if START<=localtime(r)<END]
result['shikoku_edc_related']=dict(all_downloaded=span([localtime(r) for r in edc]),
                                 formal=span([localtime(r) for r in formal_edc]),
                                 formal_blank_cells=sum(not x.strip() for r in formal_edc for x in r[4:]),
                                 pure_product_activation=False)
with (ROOT/'data/raw/JP/activation_sources_20261001/ics_basis_202606.csv').open(encoding='cp932',newline='') as stream:
    ics_all=list(csv.reader(stream))
    ics=[r for r in ics_all if r and r[0]=='D']
    header=next(r for r in ics_all if r and r[0]=='T')
    assert header[19]==header[37]=='四国'
result['ics_shikoku']=dict(rows=len(ics),first=ics[0][1:3],last=ics[-1][1:3],
                           imbalance_missing=sum(not finite(r[19]) for r in ics),
                           surplus_status=dict(Counter(r[37] for r in ics)))
assert result['ics_shikoku']['surplus_status']=={'1':901,'0':504,'-':16,'':19}
result['sources']=sources
(OUT/'inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
