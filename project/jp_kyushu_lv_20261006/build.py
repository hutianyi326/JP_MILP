"""Kyushu prices, load-matched frequency proxies and immutable model inputs."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
import sys,csv,io,json,hashlib,zipfile,re,math
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from src.jp_milp.config import require,digest
from project.jp_shikoku_202601_0830.assemble_full_period import assumptions
from project.jp_ev_offline_20261005.build_inputs import PRICE,AWARD,number
from src.jp_milp.scheduling import capacity_clock
HERE=Path(__file__).parent;RAW=ROOT/'data/raw/JP/kyushu_lv_20261006'
PACK=ROOT/'data/processed/JP/kyushu_lv_20251201_20260831_v1'
JST=timezone(timedelta(hours=9));START='2025-12-01T00:00:00+09:00'
END='2026-09-01T00:00:00+09:00';TAIL='2026-09-02T00:00:00+09:00'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def write(p,rs):
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
def rows(body):
 for enc in ('utf-8-sig','cp932'):
  try:return list(csv.reader(io.StringIO(body.decode(enc))))
  except UnicodeError:pass
 raise ValueError('Unknown encoding')
def date(s):
 return datetime.strptime(s,'%Y/%m/%d' if '/' in s else '%Y%m%d').replace(tzinfo=JST)
def decode(body,member,entry):
 rs=rows(body);require(rs[1][3]=='一次オフライン','Wrong product')
 final=rs[1][1]=='確報値';require(final or rs[1][1]=='速報値','Unknown quality')
 count=int(rs[1][4]);require(count in (8,48),'Unknown native resolution')
 area=rs[2].index('九州');info=rs[2].index('取引情報');blocks=defaultdict(dict)
 for r in rs[3:]:
  if not r or not re.fullmatch(r'\d{8}B\d{2}',r[0]):continue
  if final and r[1]!='合計（確報値）':continue
  outside=('0301-0313' in member and r[0][:8]>'20260313') or ('0314-0331' in member and r[0][:8]<'20260314')
  if outside:
   require(all(x in ('0','','-') for x in r[info+1:]),'Nonzero padded March row');continue
  if not '20251201'<=r[0][:8]<='20260901':continue
  label=r[info].replace('落札','約定');require(label not in blocks[r[0]],'Duplicate field')
  blocks[r[0]][label]=r[area]
 for key,fs in blocks.items():
  require(PRICE in fs and AWARD in fs,'Missing offline price/award')
  p=number(fs[PRICE]);award=number(fs[AWARD]);require(award is not None,'Missing award')
  if award>0:require(p is not None,'Award without price')
  index=int(key[-2:]);require(1<=index<=count,'Block outside day')
  t=date(key[:8])+timedelta(minutes=(index-1)*1440//count)
  gate,result,n=capacity_clock(t.isoformat());require(n==48//count,'Clock/resolution mismatch')
  yield dict(start=t.isoformat(),native_block_id='KYUSHU/F_OFFLINE/'+t.isoformat(),raw_block=key,native_halfhours=n,
   source_product_label='一次オフライン',archive_family='1-1',market_product='F_OFFLINE',area='九州',
   quality=rs[1][1],procurement_category='合計（確報値）' if final else 'システム約定速報',price_side='電源属地別',
   source_average_raw_jpy_kw_30min=p,source_award_mw=award,price_jpy_mw_30min=1000*p if award>0 else None,
   price_observation_valid=award>0,market_enabled=award>0,disabled_reason='' if award>0 else 'NO_SOURCE_OFFLINE_AWARD_NO_OBSERVED_PRICE',
   gate_nominal_jst=gate.isoformat(),result_deadline_nominal_jst=result.isoformat(),
   source_id=entry['source'],url=entry['url'],archive_sha256=entry['sha256'],member=member,
   member_sha256=hashlib.sha256(body).hexdigest(),accessed_utc=entry['accessed_utc'])

def main():
 require(not (PACK/'package_manifest.json').exists(),'Use fresh input version');PACK.mkdir(parents=True,exist_ok=True)
 entries={}
 for p in sorted(RAW.glob('source_manifest_*.json')):
  for e in json.loads(p.read_text(encoding='utf-8'))['entries']:
   if e['success']:entries[e['source']]=e
 for e in entries.values():require(sha(ROOT/e['path'])==e['sha256'],'Raw changed')
 holiday=ROOT/'countries/JP/research/evidence/H02_cec37a743c96.csv'
 holidays={date(r[0]).date() for r in rows(holiday.read_bytes())[1:] if r}
 save(PACK/'source_manifest.json',dict(entries=list(entries.values()),holiday_file=str(holiday.relative_to(ROOT)),holiday_sha256=sha(holiday)))
 timeline=[];t=datetime.fromisoformat(START)
 while t<datetime.fromisoformat(TAIL):timeline.append(t.isoformat());t+=timedelta(minutes=30)
 require(len(timeline)==13200,'274 days plus observation expected')
 candidates=defaultdict(list)
 for key in ('FY2025_FINAL','FY2026_FINAL','FY2026_PROMPT'):
  e=entries[key]
  with zipfile.ZipFile(ROOT/e['path']) as z:
   for member in z.namelist():
    if member.endswith('.csv') and re.search(r'(202512|20260[1-9])_1-1',member):
     for b in decode(z.read(member),member,e):candidates[b['start']].append(b)
 native=[];half=[]
 for t,vs in sorted(candidates.items()):
  pool=[v for v in vs if v['quality']=='確報値'] or vs;require(len(pool)==1,'Ambiguous quote')
  b=pool[0];native.append(b)
  for i in range(b['native_halfhours']):
   key=(datetime.fromisoformat(t)+timedelta(minutes=30*i)).isoformat()
   half.append({**b,'timestamp_jst':key,'period_role':'formal' if key<END else 'observation'})
 require([r['timestamp_jst'] for r in half]==timeline,'Offline chronology incomplete')
 spot={};load={};observed={};frequency_raw={}
 for e in entries.values():
  if e['source'].startswith('SPOT_'):
   rs=rows((ROOT/e['path']).read_bytes());col=rs[0].index('エリアプライス九州(円/kWh)')
   for r in rs[1:]:
    key=(date(r[0])+timedelta(minutes=30*(int(r[1])-1))).isoformat()
    if START<=key<TAIL:
     require(key not in spot,'Duplicate spot');spot[key]=float(r[col])*1000
  elif e['source'].startswith('LOAD_'):
   rs=rows((ROOT/e['path']).read_bytes());col=rs[1].index('エリア需要')
   for r in rs[2:]:
    if not r:continue
    clock=list(map(int,r[1].split(':')));h,m=clock[:2]
    require(len(clock)==2 or (len(clock)==3 and clock[2]==0),'Unexpected subminute load time')
    key=(date(r[0])+timedelta(hours=h,minutes=m-30)).isoformat()
    if START<=key<TAIL:require(key not in load,'Duplicate load');load[key]=float(r[col])
  elif e['source'].startswith('LFC_') and e['source']!='LFC_INDEX':
   rs=rows((ROOT/e['path']).read_bytes())
   for r in rs[1:]:
    if not r or not r[0].isdigit():continue
    key=(date(r[0])+timedelta(minutes=30*(int(r[1])-1))).isoformat()
    if not START<=key<TAIL:continue
    require(key not in frequency_raw,'Duplicate frequency')
    vals=[float(x) if x else None for x in r[4:7]]
    frequency_raw[key]=dict(mean=vals[0],upper=vals[1],lower=vals[2],source=e['source'],sha256=e['sha256'])
    if None not in vals and abs(vals[0])<=1 and vals[1]>=vals[2] and key<END:
     observed[key]=(vals[0],(vals[1]-vals[2])/4)
 require(set(spot)==set(load)==set(timeline),'Spot/load incomplete')
 # Quarantine entire suspect days rather than keep their apparently normal rows.
 bad_days={k[:10] for k,v in frequency_raw.items() if v['mean'] is not None and abs(v['mean'])>1}
 observed={k:v for k,v in observed.items() if k[:10] not in bad_days}
 def features(key):
  dt=datetime.fromisoformat(key);kind='National-holiday' if dt.date() in holidays else 'Weekend' if dt.weekday()>=5 else 'Workday'
  return dt.hour*2+dt.minute//30+1,kind
 pool=defaultdict(list)
 for key in observed:pool[features(key)].append(key)
 prepared=[];proxy=[];prices=[];counts=Counter();events={};statistics=[]
 rules=[('2025-04-01','https://www.eprx.or.jp/outline/docs/kitei_250401.pdf'),('2026-03-14','https://www.eprx.or.jp/outline/docs/kitei_ver.16.1_260314.pdf'),('2026-04-01','https://www.eprx.or.jp/outline/docs/kitei_ver.17_260401.pdf'),('2026-07-01','https://www.eprx.or.jp/outline/docs/kitei_ver.18_260701.pdf')]
 for q in half:
  key=q['timestamp_jst'];slot,kind=features(key);donors=[]
  if key in observed:mu,sd=observed[key];origin='OBSERVED_STATISTICS';reason='NOT_FILLED'
  else:
   eligible=pool[slot,kind];require(len(eligible)>=5,'Insufficient exact slot/day-type donors')
   donors=sorted(eligible,key=lambda k:(abs(load[k]-load[key]),k))[:5]
   mu=sum(observed[k][0] for k in donors)/5;sd=sum(observed[k][1] for k in donors)/5
   origin='EX_POST_MATCHED_PROXY';reason='QUARANTINED_DAY' if key[:10] in bad_days else 'EARLY_MISSING' if key<'2026-04-28' else 'OBSERVATION_OR_OTHER_MISSING'
   for k in donors:proxy.append(dict(target=key,donor=k,weight=.2,slot=slot,day_type=kind,target_load_mw=load[key],donor_load_mw=load[k],mean_hz=observed[k][0],scale_hz=observed[k][1],load_gap_mw=abs(load[k]-load[key])))
  require(math.isfinite(mu) and math.isfinite(sd) and sd>=0,'Invalid frequency proxy')
  counts[q['period_role']+'/'+origin]+=1
  rule=max((r for r in rules if r[0]<=key[:10]),key=lambda r:r[0])
  events[key]=dict(native_block_id=q['native_block_id'],product='F_OFFLINE',gate_nominal_jst=q['gate_nominal_jst'],result_deadline_nominal_jst=q['result_deadline_nominal_jst'],block_halfhour_count=q['native_halfhours'],evidence_url=rule[1])
  prepared.append(dict(start=key,period_role=q['period_role'],da_price_jpy_mwh=spot[key],capacity_price=dict(fcr=q['price_jpy_mw_30min'] if q['market_enabled'] else 0),frequency_mean_hz=mu,frequency_scale_proxy_hz=sd,statistical_origin=origin,proxy_reason=reason,offline_quote=q,payment={}))
  statistics.append(dict(timestamp_jst=key,period_role=q['period_role'],frequency_mean_hz=mu,frequency_scale_proxy_hz=sd,statistical_origin=origin,proxy_reason=reason,donors=len(donors),load_mw=load[key],slot=slot,day_type=kind,raw_mean_hz=frequency_raw.get(key,{}).get('mean'),raw_upper_hz=frequency_raw.get(key,{}).get('upper'),raw_lower_hz=frequency_raw.get(key,{}).get('lower')))
  prices.append(dict(timestamp_jst=key,period_role=q['period_role'],area='九州',spot_jpy_kwh=spot[key]/1000,spot_jpy_mwh=spot[key],offline_jpy_kw_30min=q['source_average_raw_jpy_kw_30min'] if q['market_enabled'] else None,offline_raw_jpy_kw_30min=q['source_average_raw_jpy_kw_30min'],offline_jpy_mw_30min=q['price_jpy_mw_30min'],source_award_mw=q['source_award_mw'],price_observation_valid=q['market_enabled'],quality=q['quality'],native_block_id=q['native_block_id'],native_halfhours=q['native_halfhours'],rule_effective_date=rule[0]))
 a=assumptions();a.update(area='KYUSHU',version='KYUSHU_LV_20251201_20260831_V1',formal_end=END)
 a['market']['fcr_capacity_product']='F_OFFLINE';a['solver']['mip_rel_gap']=.001
 meta=dict(assumption_sha256=digest(a),source_manifest_sha256=sha(PACK/'source_manifest.json'),assembly_code_sha256=sha(Path(__file__)),ev_offline_binding=dict(package='KYUSHU_OFFLINE_NATIVE_1_1',source_manifest_sha256=sha(PACK/'source_manifest.json')))
 save(PACK/'assumptions.json',a);save(PACK/'regional_prepared.json',dict(metadata=meta,intervals=prepared));save(PACK/'historical_events_by_scenario.json',{'HV_SPOT_FCR':events})
 save(PACK/'offline_native_blocks.json',native);save(PACK/'offline_30min.json',half)
 write(PACK/'offline_native_blocks.csv',native);write(PACK/'market_prices_30min.csv',prices);write(PACK/'activation_statistics.csv',statistics);write(PACK/'frequency_proxy_donors.csv',proxy)
 # Save the confirmed LV runtime independently of the old Shikoku run.
 old=json.loads((ROOT/'outputs/JP/lv_offline_20261005_v2/LV_FCR/manifest.json').read_text(encoding='utf-8'))['runtime']
 old['user_confirmed_scope']['lv_purchase_price']='KYUSHU_DA_PROXY_NO_RETAIL_TARIFF_OR_GRID_CHARGES';save(HERE/'runtime_lv_2mw_8mwh.json',old)
 monthly={}
 for m in sorted({p['timestamp_jst'][:7] for p in prices if p['period_role']=='formal'}):
  rs=[p for p in prices if p['timestamp_jst'].startswith(m) and p['period_role']=='formal'];valid=[r for r in rs if r['price_observation_valid']]
  monthly[m]=dict(halfhours=len(rs),valid_offline_price_halfhours=len(valid),no_source_award_halfhours=len(rs)-len(valid),spot_mean_jpy_kwh=sum(r['spot_jpy_kwh'] for r in rs)/len(rs),offline_valid_mean_jpy_kw_30min=sum(r['offline_jpy_kw_30min'] for r in valid)/len(valid) if valid else None)
 save(PACK/'coverage.json',dict(formal_days=274,formal_halfhours=13152,observation_halfhours=48,frequency_counts=dict(counts),frequency_donor_start=min(observed),frequency_donor_end=max(observed),quarantined_days=sorted(bad_days),monthly=monthly))
 save(PACK/'package_manifest.json',dict(area='九州',market_product='F_OFFLINE',formal_start=START,formal_end=END,files={p.name:sha(p) for p in PACK.iterdir()}))
 print(json.dumps(json.loads((PACK/'coverage.json').read_text(encoding='utf-8')),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
