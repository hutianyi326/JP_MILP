"""Decode official 1-1 records; preserve no-trade values as unavailable quotes."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import csv, io, json, hashlib, zipfile, re, math, sys, argparse
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from src.jp_milp.scheduling import capacity_clock
from src.jp_milp.config import require
RAW=ROOT/'data/raw/JP/ev_offline_20261005'
OUT=ROOT/'data/processed/JP/shikoku_ev_offline_20260101_0830_v1'
PRICE='平均約定価格（電源属地別）[円/kW・30分]'
AWARD='約定量合計（電源属地別）[MW]'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def number(value):
 if value in ('','-'):return None
 result=float(value);require(math.isfinite(result) and result>=0,'Invalid nonnegative official value')
 return result

def decode(body,member,entry):
 rows=list(csv.reader(io.StringIO(body.decode('cp932'))))
 require(rows[1][0]=='P' and rows[1][3]=='一次オフライン','Wrong market product: require offline 1-1')
 final=rows[1][1]=='確報値';require(final or rows[1][1]=='速報値','Unknown quality')
 count=int(rows[1][4]);require(count in (8,48),'Unknown native resolution')
 header=rows[2];area=header.index('四国');info=header.index('取引情報')
 selected='合計（確報値）' if final else None;blocks=defaultdict(dict)
 for row in rows[3:]:
  if not row or not re.fullmatch(r'20260[1-8]\d{2}B\d{2}',row[0]):continue
  if final and row[1]!=selected:continue
  # Official split-March files contain zero-padded rows outside their named range.
  outside=('0301-0313' in member and row[0][:8]>'20260313') or ('0314-0331' in member and row[0][:8]<'20260314')
  if outside:
   require(all(x in ('0','','-') for x in row[info+1:]),'Nonzero observation outside declared March split')
   continue
  label=row[info].replace('落札','約定')
  require(label not in blocks[row[0]],'Duplicate native field')
  blocks[row[0]][label]=row[area]
 for block,fields in blocks.items():
  require(PRICE in fields and AWARD in fields,'Missing source average/award fields')
  p=number(fields[PRICE]);award=number(fields[AWARD]);require(award is not None,'Missing award quantity')
  if award>0:require(p is not None,'Positive award without observed offline price; NOT_READY')
  enabled=award>0;start=datetime.strptime(block[:8],'%Y%m%d').replace(tzinfo=timezone(timedelta(hours=9)))
  start+=timedelta(minutes=(int(block[-2:])-1)*(1440/count))
  require((start.date().isoformat()<'2026-03-14')==(count==8),'Offline native resolution disagrees with historical regime')
  gate,result,n=capacity_clock(start.isoformat());require(n==48//count,'Native block mismatch')
  yield dict(start=start.isoformat(),native_block_id='SHIKOKU/F_OFFLINE/'+start.isoformat(),raw_block=block,
   native_halfhours=n,source_product_label='一次オフライン',archive_family='1-1',market_product='F_OFFLINE',
   quality=rows[1][1],procurement_category=selected or 'システム約定速報',price_side='電源属地別',
   source_average_raw_jpy_kw_30min=p,source_award_mw=award,
   source_offer_mw=number(fields.get('応札量合計（電源属地別）[MW]','')),
   tso_requirement_mw=number(fields.get('募集量（TSO別）[MW]','')),
   tso_award_mw=number(fields.get('約定量合計（TSO別）[MW]','')),
   tso_average_raw_jpy_kw_30min=number(fields.get('平均約定価格（TSO別）[円/kW・30分]','')),
   price_jpy_mw_30min=1000*p if enabled else None,price_observation_valid=enabled,
   market_enabled=enabled,disabled_reason='' if enabled else 'NO_SOURCE_OFFLINE_AWARD_NO_OBSERVED_PRICE',
   gate_nominal_jst=gate.isoformat(),result_deadline_nominal_jst=result.isoformat(),
   source_id=entry['source'],url=entry['url'],archive_sha256=entry['sha256'],member=member,
   member_sha256=hashlib.sha256(body).hexdigest(),accessed_utc=entry['accessed_utc'])

def main(manifest=None):
 manifest=Path(manifest) if manifest else sorted(RAW.glob('source_manifest_*.json'))[-1]
 source=json.loads(manifest.read_text(encoding='utf-8'));candidates=defaultdict(list)
 for entry in source['entries']:
  if not entry['path'].endswith('.zip'):continue
  archive=ROOT/entry['path'];require(sha(archive)==entry['sha256'],'Archive fingerprint changed')
  with zipfile.ZipFile(archive) as z:
   for member in z.namelist():
    if member.endswith('.csv') and re.search(r'20260[1-8]_1-1',member):
     for block in decode(z.read(member),member,entry):candidates[block['start']].append(block)
 selected=[]
 for key,values in sorted(candidates.items()):
  finals=[v for v in values if v['quality']=='確報値'];pool=finals or values
  require(len(pool)==1,'Ambiguous same-quality offline observation')
  selected.append(pool[0])
 half=[];monthly={}
 for b in selected:
  for i in range(b['native_halfhours']):
   t=(datetime.fromisoformat(b['start'])+timedelta(minutes=30*i)).isoformat()
   if not '2026-01-01'<=t[:10]<'2026-09-01':continue
   half.append({**b,'timestamp_jst':t,'period_role':'formal' if t<'2026-08-31' else 'observation'})
 require(len(half)==11664 and len({r['timestamp_jst'] for r in half})==11664,'Offline full coverage incomplete')
 expected=datetime(2026,1,1,tzinfo=timezone(timedelta(hours=9)))
 require(all(datetime.fromisoformat(r['timestamp_jst'])==expected+timedelta(minutes=30*i) for i,r in enumerate(half)), 'Offline timeline gap')
 for r in half:
  if r['period_role']!='formal':continue
  m=monthly.setdefault(r['timestamp_jst'][:7],dict(halfhours=0,observed_price_halfhours=0,no_source_award_halfhours=0,valid_price_sum=0.,quality_counts={}))
  m['halfhours']+=1;m['quality_counts'][r['quality']]=m['quality_counts'].get(r['quality'],0)+1
  if r['market_enabled']:m['observed_price_halfhours']+=1;m['valid_price_sum']+=r['source_average_raw_jpy_kw_30min']
  else:m['no_source_award_halfhours']+=1
 for m in monthly.values():
  m['mean_observed_price_jpy_kw_30min']=m.pop('valid_price_sum')/m['observed_price_halfhours'] if m['observed_price_halfhours'] else None
 require(not OUT.exists(),'Use a fresh processed version folder')
 OUT.mkdir(parents=True)
 save(OUT/'offline_native_blocks.json',selected);save(OUT/'offline_30min.json',half)
 for filename,records in [('offline_native_blocks.csv',selected),('offline_30min.csv',half)]:
  with (OUT/filename).open('w',encoding='utf-8-sig',newline='') as stream:
   writer=csv.DictWriter(stream,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
 save(OUT/'coverage_and_monthly_prices.json',monthly)
 metadata=dict(version='EV_OFFLINE_1_1_SOURCE_FINAL_PRIORITY_V1',market_product='F_OFFLINE',area='四国',timezone='Asia/Tokyo',
  formal_start='2026-01-01T00:00:00+09:00',formal_end_exclusive='2026-08-31T00:00:00+09:00',observation_halfhours=48,
  no_trade_policy='DISABLE_NEW_OFFER_WITHOUT_OBSERVED_SOURCE_OFFLINE_PRICE; NOT_PROOF_OF_NO_MARKET_OPPORTUNITY',
  missing_policy='Positive source award without valid price or absent timestamp: NOT_READY; no ordinary F fallback',
  price_policy='Final total source-region average first, prompt source-region average only if final absent; aggregate historical proxy',
  source_manifest=str(manifest.relative_to(ROOT)),source_manifest_sha256=sha(manifest),build_code_sha256=sha(Path(__file__)),
  files={p.name:sha(p) for p in OUT.iterdir()})
 save(OUT/'package_manifest.json',metadata)
 print(json.dumps(dict(output=str(OUT),monthly=monthly),ensure_ascii=False,indent=2))

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--manifest');main(parser.parse_args().manifest)
