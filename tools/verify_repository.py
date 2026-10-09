"""Verify staged release bytes, size limits and high-confidence credentials."""
from pathlib import Path
import hashlib, json, re, subprocess

ROOT = Path(__file__).resolve().parents[1]

def main():
    manifest=json.loads((ROOT/'repository_export_manifest.json').read_text(encoding='utf-8'))
    for rel,info in manifest['copied'].items():
        data=(ROOT/rel).read_bytes()
        assert hashlib.sha256(data).hexdigest()==info['sha256'],f'Export mismatch: {rel}'
    index=subprocess.check_output(['git','ls-files','--stage','-z'],cwd=ROOT).split(b'\0')
    patterns={
        'github_pat':rb'\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})\b',
        'aws_access_key':rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
        'private_key':rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        'openai_key':rb'\bsk-(?:proj-|svcacct-)[A-Za-z0-9_-]{40,}\b',
    }
    findings=[];count=0;total=0
    for entry in index:
        if not entry:continue
        head,name=entry.split(b'\t',1);rel=name.decode('utf-8');p=ROOT/rel
        assert not any(s in ('.git','.venv-es-milp','__pycache__','RO_MILP') for s in Path(rel).parts)
        data=p.read_bytes();assert len(data)<50_000_000,f'Large tracked file: {rel}'
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        assert blob==head.split()[1].decode(),f'Staged bytes differ: {rel}'
        if p.suffix.lower() in ('.py','.md','.json','.yaml','.yml','.toml','.txt','.csv','.html'):
            for kind,pattern in patterns.items():
                if re.search(pattern,data):findings.append(dict(file=rel,kind=kind))
        count+=1;total+=len(data)
    assert not findings,json.dumps(findings,ensure_ascii=False)
    print(json.dumps(dict(status='PASS',tracked_files=count,bytes=total,export_files=len(manifest['copied']),credential_findings=len(findings),staged_bytes_match=True),ensure_ascii=False))

if __name__=='__main__':main()
