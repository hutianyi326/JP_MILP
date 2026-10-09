"""Download immutable official June/July snapshots; no overwrite of originals."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, urllib.request

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/raw/JP/shikoku_preparation_20261004'
URLS={
    'shikoku_publication':'https://www.yonden.co.jp/nw/adjusting_power_supply/supply_demand.html',
    'shikoku_lfc_202606':'https://www.yonden.co.jp/nw/assets/adjusting_power_supply/2026/jukyu_LFC_shikoku_202606.csv',
    'shikoku_lfc_202607':'https://www.yonden.co.jp/nw/assets/adjusting_power_supply/2026/jukyu_LFC_shikoku_202607.csv',
    'shikoku_edc_202606':'https://www.yonden.co.jp/nw/assets/adjusting_power_supply/2026/jukyu_shikoku_202606.csv',
    'shikoku_edc_202607':'https://www.yonden.co.jp/nw/assets/adjusting_power_supply/2026/jukyu_shikoku_202607.csv',
    'ics_basis_202606':'https://www.imbalanceprices-cs.jp/api/1.0/imb/basis/202606',
    'ics_basis_202607':'https://www.imbalanceprices-cs.jp/api/1.0/imb/basis/202607',
}

def main():
    OUT.mkdir(parents=True,exist_ok=True);manifest=[]
    for name,url in URLS.items():
        record=dict(id=name,url=url,access_utc=datetime.now(timezone.utc).isoformat())
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(request,timeout=45) as response:
                blob=response.read();record.update(status=response.status,final_url=response.url,content_type=response.headers.get('Content-Type'),last_modified=response.headers.get('Last-Modified'))
            sha=hashlib.sha256(blob).hexdigest();suffix='.html' if name.endswith('publication') else '.csv'
            path=OUT/(name+'_'+sha[:12]+suffix)
            if path.exists():
                assert path.read_bytes()==blob
            else:
                with path.open('xb') as stream:stream.write(blob)
            record.update(path=str(path.relative_to(ROOT)),sha256=sha,bytes=len(blob),success=True)
        except Exception as exc:record.update(success=False,error=str(exc))
        manifest.append(record);print(json.dumps(record,ensure_ascii=False),flush=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    (OUT/('manifest_'+stamp+'.json')).write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
