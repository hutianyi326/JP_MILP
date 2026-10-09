"""Package verified raw inputs, source code, full rolling evidence and reports."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,zipfile,shutil,sys,platform,importlib.metadata
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
PACK=ROOT/'data/processed/JP/kyushu_lv_20251201_20260831_v1'
RUN=ROOT/'outputs/JP/kyushu_lv_20251201_20260831_20261006_v3/LV_FCR'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
 assert read(RUN/'summary.json')['status']=='COMPLETE'
 assert read(HERE/'validation_and_results.json')['status']==read(HERE/'input_validation.json')['status']=='PASS'
 assert (HERE/'review.md').exists(),'Independent review record required'
 snapshot=HERE/'source_snapshot';snapshot.mkdir(exist_ok=False)
 code=list((ROOT/'src/jp_milp').glob('*.py'))+list(HERE.glob('*.py'))+list((ROOT/'tests').glob('test_jp*.py'))+[
  ROOT/'project/jp_first_run_inputs_20261004/assemble.py',ROOT/'project/jp_shikoku_202601_0830/assemble_full_period.py',
  ROOT/'project/jp_ev_offline_20261005/binding.py',ROOT/'project/jp_ev_offline_20261005/build_inputs.py',ROOT/'project/jp_revenue_20261005/numeric_states.py']
 if (ROOT/'tests/__init__.py').exists():code.append(ROOT/'tests/__init__.py')
 hashes={}
 for p in code:
  rel=p.relative_to(ROOT);dest=snapshot/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);hashes[rel.as_posix()]=sha(p)
 save(HERE/'source_snapshot_manifest.json',hashes)
 env=dict(python=sys.version,platform=platform.platform(),libraries={k:importlib.metadata.version(k) for k in ('numpy','scipy','highspy','pyscipopt')})
 save(HERE/'execution_environment.json',env)
 files=list(PACK.glob('*'))+list(RUN.rglob('*'))+list(snapshot.rglob('*'))
 files+=[p for p in HERE.iterdir() if p.is_file()]
 sources=read(PACK/'source_manifest.json');files += [ROOT/e['path'] for e in sources['entries']]+[ROOT/sources['holiday_file']]
 unique={p.relative_to(ROOT).as_posix():p for p in files if p.is_file()}
 archive=ROOT/'outputs/JP/kyushu_lv_2mw_8mwh_20251201_20260831_20261006_reviewed.zip'
 with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
  for rel,p in sorted(unique.items()):z.write(p,rel)
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None and len(z.namelist())==len(set(z.namelist()))
 delivery=dict(status='VERIFIED_DELIVERY',archive=str(archive.relative_to(ROOT)),bytes=archive.stat().st_size,sha256=sha(archive),files=len(unique),created_utc=datetime.now(timezone.utc).isoformat(),files_sha256={rel:sha(p) for rel,p in unique.items()})
 save(HERE/'delivery_manifest.json',delivery)
 print(json.dumps({k:v for k,v in delivery.items() if k!='files_sha256'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
