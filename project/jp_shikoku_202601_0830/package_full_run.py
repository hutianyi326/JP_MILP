"""Seal the validated asset-free k=1 input package and its delivery evidence."""
from pathlib import Path
import json,hashlib,zipfile
ROOT=Path(__file__).resolve().parents[2]
PACK=ROOT/'data/processed/JP/shikoku_full_run_k1_v5'
HERE=Path(__file__).parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

if __name__=='__main__':
    from sys import path
    path.insert(0,str(ROOT))
    from src.jp_milp.config import digest
    report=read(HERE/'full_period_validation.json');meta=read(PACK/'regional_prepared.json')['metadata']
    assert report['status']=='PASS' and report['metadata']==meta
    assert meta['assumption_sha256']==digest(read(PACK/'assumptions.json'))
    assert meta['assembly_code_sha256']==sha(HERE/'assemble_full_period.py')
    assert meta['shared_binding_code_sha256']==sha(ROOT/'project/jp_first_run_inputs_20261004/assemble.py')
    assert meta['solver_code_sha256']==digest({p.name:p.read_text(encoding='utf-8') for p in sorted((ROOT/'src/jp_milp').glob('*.py'))})
    assert all(v['intervals']==11664 and v['blocks']==8784 for v in report['preflight'].values())
    assert len(report['integrations'])==6 and all(v['status']=='PASS' for v in report['integrations'].values())
    files=list(PACK.glob('*.json'))+list(PACK.glob('*.csv'))
    files += [HERE/'full_run_k1.md',HERE/'full_period_validation.json',HERE/'assemble_full_period.py',HERE/'validate_full_period.py',
              ROOT/'project/jp_first_run_inputs_20261004/runtime_template.json']
    manifest=dict(status='PASS',classification='ASSET_FREE_CONDITIONAL_INPUT_NOT_PROJECT_REVENUE',lfc_k=1.,
        files={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in files})
    target=ROOT/'outputs/JP/shikoku_full_run_k1_v5.zip'
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as archive:
        for p in files:archive.write(p,str(p.relative_to(ROOT)))
        archive.writestr('delivery_manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for name,expected in manifest['files'].items():assert hashlib.sha256(archive.read(name)).hexdigest()==expected
    manifest.update(archive=str(target.relative_to(ROOT)),archive_sha256=sha(target),archive_bytes=target.stat().st_size)
    (HERE/'full_run_delivery.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if k!='files'},ensure_ascii=False,indent=2))
