"""Reconcile processed prices with original official member rows and donors."""
from pathlib import Path
from datetime import datetime,timedelta
from collections import defaultdict,Counter
import sys,csv,io,json,zipfile,hashlib,math
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from src.jp_milp.config import require
HERE=Path(__file__).parent;PACK=ROOT/'data/processed/JP/kyushu_lv_20251201_20260831_v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(x,y):require(abs(x-y)<1e-10,'Numeric source reconciliation failed')
def decode(b):
 for enc in ('utf-8-sig','cp932'):
  try:return list(csv.reader(io.StringIO(b.decode(enc))))
  except UnicodeError:pass
 raise ValueError('Unknown encoding')
def main():
 manifest=read(PACK/'package_manifest.json');sources=read(PACK/'source_manifest.json')
 for n,h in manifest['files'].items():require(sha(PACK/n)==h,'Processed checksum mismatch')
 byhash={e['sha256']:e for e in sources['entries']}
 for e in sources['entries']:require(sha(ROOT/e['path'])==e['sha256'],'Raw checksum mismatch')
 member_cache={};native=read(PACK/'offline_native_blocks.json');half=read(PACK/'offline_30min.json')
 for q in native:
  key=q['archive_sha256'],q['member']
  if key not in member_cache:
   with zipfile.ZipFile(ROOT/byhash[key[0]]['path']) as z:body=z.read(key[1])
   require(hashlib.sha256(body).hexdigest()==q['member_sha256'],'Member changed')
   rs=decode(body);header=rs[2];col=header.index('九州');info=header.index('取引情報')
   require(rs[1][3]=='一次オフライン' and int(rs[1][4])*q['native_halfhours']==48,'Wrong product/resolution')
   group=header.index('調達区分') if '調達区分' in header else None
   lookup={}
   for r in rs[3:]:
    if not r or not r[0][:8].isdigit():continue
    if group is not None and r[group]!='合計（確報値）':continue
    lookup[r[0],r[info].replace('落札','約定')]=r[col]
   member_cache[key]=lookup
  lookup=member_cache[key]
  rawprice=lookup[q['raw_block'],'平均約定価格（電源属地別）[円/kW・30分]']
  rawaward=lookup[q['raw_block'],'約定量合計（電源属地別）[MW]']
  close(float(rawaward),q['source_award_mw'])
  require(q['market_enabled']==(float(rawaward)>0),'Availability mismatch')
  if q['market_enabled']:
   close(float(rawprice),q['source_average_raw_jpy_kw_30min']);close(float(rawprice)*1000,q['price_jpy_mw_30min'])
  else:require(q['price_jpy_mw_30min'] is None,'No-trade mispriced')
 bynative={q['native_block_id']:q for q in native};counts=Counter(q['native_block_id'] for q in half)
 for q in half:
  source=bynative[q['native_block_id']]
  require(counts[q['native_block_id']]==q['native_halfhours'],'Native expansion inconsistent')
  require(q['price_jpy_mw_30min']==source['price_jpy_mw_30min'],'Price changed during expansion')
 spot={}
 for e in sources['entries']:
  if not e['source'].startswith('SPOT_'):continue
  rs=decode((ROOT/e['path']).read_bytes());column=rs[0].index('エリアプライス九州(円/kWh)')
  for r in rs[1:]:
   dt=datetime.strptime(r[0],'%Y/%m/%d');dt+=timedelta(minutes=30*(int(r[1])-1))
   spot[dt.isoformat()+'+09:00']=float(r[column])
 prepared=read(PACK/'regional_prepared.json')['intervals']
 with (PACK/'activation_statistics.csv').open(encoding='utf-8-sig') as f:stats=list(csv.DictReader(f))
 require(len(prepared)==13200 and len(stats)==13200,'Chronology size')
 require(all(math.isfinite(float(r['load_mw'])) and float(r['load_mw'])>0 for r in stats),'Invalid load matching covariate')
 for r in prepared:close(r['da_price_jpy_mwh'],spot[r['start']]*1000)
 observed={r['timestamp_jst']:r for r in stats if r['statistical_origin']=='OBSERVED_STATISTICS'}
 donors=defaultdict(list)
 with (PACK/'frequency_proxy_donors.csv').open(encoding='utf-8-sig') as f:
  for r in csv.DictReader(f):donors[r['target']].append(r)
 pool=defaultdict(list)
 for k,r in observed.items():
  require(r['period_role']=='formal','Observation donor')
  close(float(r['frequency_mean_hz']),float(r['raw_mean_hz']))
  close(float(r['frequency_scale_proxy_hz']),(float(r['raw_upper_hz'])-float(r['raw_lower_hz']))/4)
  pool[r['slot'],r['day_type']].append(k)
 outside=0
 for r in stats:
  k=r['timestamp_jst']
  if k in observed:require(k not in donors,'Observed row replaced');continue
  ds=donors[k];require(len(ds)==5 and len({d['donor'] for d in ds})==5,'Donor count')
  eligible=pool[r['slot'],r['day_type']]
  chosen=sorted(eligible,key=lambda key:(abs(float(observed[key]['load_mw'])-float(r['load_mw'])),key))[:5]
  require([d['donor'] for d in ds]==chosen,'Not exact closest load donors')
  for d in ds:
   require(d['slot']==r['slot'] and d['day_type']==r['day_type'],'Wrong matching features');close(float(d['weight']),.2)
  close(float(r['frequency_mean_hz']),sum(float(observed[d]['frequency_mean_hz']) for d in chosen)/5)
  close(float(r['frequency_scale_proxy_hz']),sum(float(observed[d]['frequency_scale_proxy_hz']) for d in chosen)/5)
  lo=min(float(observed[d]['load_mw']) for d in eligible);hi=max(float(observed[d]['load_mw']) for d in eligible)
  outside+=not lo<=float(r['load_mw'])<=hi
 errors={'mean':[],'scale':[]}
 for key,r in observed.items():
  eligible=[d for d in pool[r['slot'],r['day_type']] if d[:10]!=key[:10]]
  require(len(eligible)>=5,'Insufficient leave-day-out donors')
  chosen=sorted(eligible,key=lambda d:(abs(float(observed[d]['load_mw'])-float(r['load_mw'])),d))[:5]
  for name,field in [('mean','frequency_mean_hz'),('scale','frequency_scale_proxy_hz')]:
   errors[name].append(sum(float(observed[d][field]) for d in chosen)/5-float(r[field]))
 result=dict(status='PASS',raw_files=len(sources['entries']),native_blocks=len(native),halfhours=len(half),
  observed_frequency_halfhours=len(observed),proxy_halfhours=len(donors),proxy_outside_donor_load_range_halfhours=outside,
  leave_day_out_errors_hz={k:dict(mae=sum(abs(x) for x in vs)/len(vs),rmse=math.sqrt(sum(x*x for x in vs)/len(vs))) for k,vs in errors.items()},
  validation_limit='Observed-season diagnostics do not validate winter transfer or measured station activation',code_sha256=sha(Path(__file__)))
 (HERE/'input_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
