"""Immutable official price and physical-input snapshots for Kyushu LV."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib, json, urllib.request

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT/'data/raw/JP/kyushu_lv_20261006'
SOURCES = [
 ('FY2025_FINAL','https://www.eprx.or.jp/information/2025_1-1_result.zip'),
 ('FY2026_FINAL','https://www.eprx.or.jp/information/2026_1-1_result.zip'),
 ('FY2026_PROMPT','https://www.eprx.or.jp/information/files/2026_1-1_prompt.zip'),
 ('SPOT_FY2025','https://www.jepx.jp/market/excel/spot_2025.csv'),
 ('SPOT_FY2026','https://www.jepx.jp/market/excel/spot_2026.csv'),
 ('LFC_INDEX','https://www.kyuden.co.jp/td_power_usages/csv/lfc/kouiki_lfc_info_list.csv'),
 ('EPRX_RESULTS_PAGE','https://www.eprx.or.jp/information/results.php'),
]
MONTHS=['202512']+[f'2026{m:02d}' for m in range(1,10)]
for month in MONTHS:
 SOURCES.append(('LFC_'+month,f'https://www.kyuden.co.jp/td_power_usages/csv/lfc/jukyu_LFC_kyushu_{month}.csv'))
 SOURCES.append(('LOAD_'+month,f'https://www.kyuden.co.jp/td_area_jukyu/csv/eria_jukyu_{month}_09.csv'))

def fetch(item):
 key,url=item;entry=dict(source=key,url=url,accessed_utc=datetime.now(timezone.utc).isoformat())
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=45) as response:
   body=response.read();entry.update(resolved_url=response.url,headers=dict(response.headers))
  sha=hashlib.sha256(body).hexdigest();suffix='.zip' if url.endswith('.zip') else '.html' if url.endswith('.html') else '.csv'
  path=RAW/(key+'_'+sha[:16]+suffix)
  if path.exists():assert path.read_bytes()==body
  else:
   with path.open('xb') as stream:stream.write(body)
  entry.update(success=True,path=path.relative_to(ROOT).as_posix(),sha256=sha,bytes=len(body))
 except Exception as error:entry.update(success=False,error=str(error))
 print(key,entry.get('bytes'),entry.get('error','OK'),flush=True)
 return entry

def main():
 RAW.mkdir(parents=True,exist_ok=True)
 with ThreadPoolExecutor(max_workers=4) as pool:entries=list(pool.map(fetch,SOURCES))
 path=RAW/('source_manifest_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
 path.write_text(json.dumps(dict(entries=entries),ensure_ascii=False,indent=2),encoding='utf-8')
 print(path,flush=True)

if __name__=='__main__':main()
