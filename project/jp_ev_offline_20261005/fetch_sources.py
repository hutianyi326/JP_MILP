"""Bounded official offline-only downloads; immutable content-addressed snapshots."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, urllib.request, zipfile, io

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'data/raw/JP/ev_offline_20261005'
SOURCES=[
 ('FY2025_FINAL','https://www.eprx.or.jp/information/2025_1-1_result.zip'),
 ('FY2026_FINAL','https://www.eprx.or.jp/information/2026_1-1_result.zip'),
 ('FY2026_PROMPT','https://www.eprx.or.jp/information/files/2026_1-1_prompt.zip'),
 ('EPRX_FAQ','https://www.eprx.or.jp/contact/jukyuchoseishijo/faq.html')]

def main():
 RAW.mkdir(parents=True,exist_ok=True);entries=[]
 for source,url in SOURCES:
  req=urllib.request.Request(url,headers={'User-Agent':'Japan-storage-research/1.0'})
  with urllib.request.urlopen(req,timeout=90) as response:
   body=response.read();headers=dict(response.headers);final_url=response.url
  sha=hashlib.sha256(body).hexdigest();suffix='.zip' if url.endswith('.zip') else '.html'
  path=RAW/(source+'_'+sha[:16]+suffix)
  if path.exists():assert path.read_bytes()==body
  else:path.write_bytes(body)
  members=zipfile.ZipFile(io.BytesIO(body)).namelist() if suffix=='.zip' else []
  entries.append(dict(source=source,url=url,resolved_url=final_url,accessed_utc=datetime.now(timezone.utc).isoformat(),
   sha256=sha,bytes=len(body),path=str(path.relative_to(ROOT)),headers=headers,members=members))
  print(source,len(body),[x for x in members if '20260' in x],flush=True)
 manifest=dict(institution='EPRX',scope='Offline 1-1 only, bounded three archives and FAQ; newly downloaded',entries=entries)
 name='source_manifest_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json'
 (RAW/name).write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 print(RAW/name)

if __name__=='__main__':main()
