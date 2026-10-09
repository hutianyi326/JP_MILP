"""Immutable refresh of official Shikoku and ICS evidence; failures are explicit."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib, json, urllib.request

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/raw/JP/shikoku_202601_0830_20261005'

def fetch(item):
    name,url=item
    result=dict(id=name,url=url,access_utc=datetime.now(timezone.utc).isoformat())
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=20) as response:
            blob=response.read()
            result.update(status=response.status,content_type=response.headers.get('Content-Type'))
        sha=hashlib.sha256(blob).hexdigest();p=OUT/(name+'_'+sha[:12]+'.csv')
        if p.exists():assert p.read_bytes()==blob
        else:
            with p.open('xb') as f:f.write(blob)
        result.update(success=True,path=p.relative_to(ROOT).as_posix(),sha256=sha)
    except Exception as e:result.update(success=False,error=str(e))
    print(json.dumps(result,ensure_ascii=False),flush=True)
    return result

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    urls=[]
    for m in range(1,9):
        month=f'2026{m:02d}'
        urls.append((f'lfc_{month}',f'https://www.yonden.co.jp/nw/assets/adjusting_power_supply/2026/jukyu_LFC_shikoku_{month}.csv'))
        urls.append((f'ics_{month}',f'https://www.imbalanceprices-cs.jp/api/1.0/imb/basis/{month}'))
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(fetch,urls))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    (OUT/f'manifest_{stamp}.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
