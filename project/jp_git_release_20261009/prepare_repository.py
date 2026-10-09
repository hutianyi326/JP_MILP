"""Create an isolated, traceable Japan release without changing original files."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'JP_MILP'
EXCLUDED_PARTS = {'__pycache__', '.git', '.pytest_cache', 'reference_ES_MILP', 'source_snapshot', 'data'}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if DEST.exists():
        raise RuntimeError('Destination already exists; inspect before updating')
    DEST.mkdir()
    sources = [ROOT/'src/jp_milp', ROOT/'countries/JP']
    sources += sorted((ROOT/'project').glob('jp_*'))
    candidates = set()
    for base in sources:
        candidates.update(p for p in base.rglob('*') if p.is_file())
    candidates.update((ROOT/'tests').glob('test_jp*.py'))
    candidates.update([ROOT/'AGENTS.md', ROOT/'project/run_jp_milp.py', ROOT/'model/jp_milp_implementation.md'])
    if (ROOT/'tests/__init__.py').exists(): candidates.add(ROOT/'tests/__init__.py')
    copied, omitted = {}, {}
    for p in sorted(candidates):
        rel = p.relative_to(ROOT)
        reason = None
        if any(s in EXCLUDED_PARTS or s.startswith('execution_source_snapshot') for s in rel.parts):
            reason = 'Local data, cache or duplicate historical source snapshot'
        elif p.suffix.lower() in ('.zip', '.gz', '.bin', '.exe', '.pyc'):
            reason = 'Local archive, ledger or executable'
        elif p.suffix.lower() == '.csv' and p.stat().st_size > 5_000_000:
            reason = 'Large time-series data retained in original workspace'
        elif p.stat().st_size >= 50_000_000:
            reason = 'Large local artifact'
        if reason:
            omitted[rel.as_posix()] = dict(bytes=p.stat().st_size, reason=reason)
            continue
        q = DEST/rel
        q.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p,q)
        assert sha(q) == sha(p)
        copied[rel.as_posix()] = dict(bytes=q.stat().st_size, sha256=sha(q))
    # Namespace packages work without __init__; tests must import locally.
    (DEST/'tests/__init__.py').touch(exist_ok=True)
    (DEST/'.gitignore').write_text('''__pycache__/
*.py[cod]
.pytest_cache/
.venv*/
.env
.env.*
!.env.example
*.pem
*.key
/data/
/outputs/
/countries/JP/data/
*.zip
*.gz
*.bin
*.log
.DS_Store
Thumbs.db
''',encoding='utf-8')
    (DEST/'.gitattributes').write_text('* text=auto\n*.py text eol=lf\n*.md text eol=lf\n*.json text eol=lf\n*.csv text eol=lf\n*.pdf binary\n*.xlsx binary\n*.xls binary\n*.png binary\n*.jpg binary\n',encoding='utf-8')
    (DEST/'requirements.txt').write_text('numpy==2.4.6\nscipy==1.15.3\nhighspy==1.15.1\npyscipopt==6.2.1\nrequests\npandas\nopenpyxl\nbeautifulsoup4\n',encoding='utf-8')
    manifest = dict(created_utc=datetime.now(timezone.utc).isoformat(), copied=copied, omitted=omitted,
        policy='Japan source/research/reports only. Large market data and full execution ledgers remain local. Official evidence files below 50 MB included.',
        origin_workspace='Counry_Investigation',remote='https://github.com/hutianyi326/JP_MILP.git')
    (DEST/'repository_export_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(files=len(copied),bytes=sum(x['bytes'] for x in copied.values()),omitted=len(omitted),repo=str(DEST)),ensure_ascii=False))

if __name__ == '__main__': main()
