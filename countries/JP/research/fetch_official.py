"""Read-only HTTP acquisition of public Japanese official research sources."""
import concurrent.futures, datetime, hashlib, json, pathlib, sys, urllib.request, urllib.parse, subprocess, tempfile
BASE = pathlib.Path(__file__).resolve().parent
ALLOWED = ('jepx.jp','eprx.or.jp','occto.or.jp','meti.go.jp','e-gov.go.jp','cao.go.jp','hepco.co.jp','tohoku-epco.co.jp','tepco.co.jp','chuden.co.jp','rikuden.co.jp','kepco.co.jp','kansai-td.co.jp','energia.co.jp','yonden.co.jp','kyuden.co.jp','kyuden.jp','imbalanceprices.jp','imbalanceprices-cs.jp')
def acquire(item):
    u = item['url']; host = urllib.parse.urlparse(u).hostname or ''
    if not any(host == h or host.endswith('.'+h) for h in ALLOWED):
        return dict(item, status='disallowed_domain')
    try:
        post=urllib.parse.urlencode(item['post']).encode() if 'post' in item else None
        req = urllib.request.Request(u, data=post, headers={'User-Agent':'Mozilla/5.0 (public market research)'})
        if item.get('transport') == 'curl':
            with tempfile.TemporaryDirectory() as td:
                dest=pathlib.Path(td)/'download'
                run=subprocess.run(['curl.exe','--fail','--location','--max-time','45','--silent','--show-error','--output',str(dest),u],capture_output=True)
                if run.returncode: raise ValueError(run.stderr.decode(errors='replace'))
                data=dest.read_bytes(); ctype=''; final=u
        else:
            with urllib.request.urlopen(req, timeout=45) as r:
                data=r.read(35000001); ctype=r.headers.get('Content-Type',''); final=r.url
        if not data: raise ValueError('empty response: no usable evidence')
        if len(data)>35000000: raise ValueError('document exceeds 35 MB acquisition limit')
        sha=hashlib.sha256(data).hexdigest()
        ext=pathlib.PurePosixPath(urllib.parse.urlparse(u).path).suffix
        if 'extension' in item: ext=item['extension']
        if ext not in ('.pdf','.csv','.xlsx','.xls','.zip','.js','.json','.html'): ext='.html'
        folder=BASE/'evidence'; folder.mkdir(parents=True,exist_ok=True)
        p=folder/(item['id']+'_'+sha[:12]+ext)
        if not p.exists(): p.write_bytes(data)
        return dict(item,status='ok',final_url=final,bytes=len(data),sha256=sha,content_type=ctype,path=str(p.relative_to(BASE)),accessed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    except Exception as e: return dict(item,status='error',error=str(e),accessed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
if __name__=='__main__':
    jobs=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8-sig'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        rows=list(pool.map(acquire,jobs))
    with (BASE/'sources.jsonl').open('a',encoding='utf-8') as f:
        for row in rows: f.write(json.dumps(row,ensure_ascii=False)+'\n')
    for row in rows: print(json.dumps(row,ensure_ascii=True))
