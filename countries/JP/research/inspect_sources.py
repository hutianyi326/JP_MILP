import pathlib,sys,re,json,html
sys.stdout.reconfigure(encoding='utf-8')
from html.parser import HTMLParser
BASE=pathlib.Path(__file__).resolve().parent
class Links(HTMLParser):
    def __init__(self): super().__init__(); self.links=[];self.u=None;self.t=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='a': self.u=a.get('href');self.t=[]
    def handle_data(self,data):
        if self.u:self.t.append(data)
    def handle_endtag(self,tag):
        if tag=='a' and self.u:self.links.append((self.u,' '.join(self.t).strip()));self.u=None
for prefix in sys.argv[1:]:
    for p in (BASE/'evidence').glob(prefix+'_*'):
        if p.suffix=='.pdf':
            from pypdf import PdfReader
            target=BASE/'extracted'/p.with_suffix('.txt').name;target.parent.mkdir(exist_ok=True)
            if not target.exists():
                reader=PdfReader(p)
                target.write_text('\n'.join(f'\n=== PDF PAGE {i+1} ===\n'+(page.extract_text() or '') for i,page in enumerate(reader.pages)),encoding='utf-8')
            print(str(target))
        elif p.suffix=='.html':
            data=p.read_bytes()
            try:s=data.decode('utf-8')
            except UnicodeDecodeError:s=data.decode('cp932',errors='replace')
            parser=Links();parser.feed(s)
            print('\n'+p.name)
            for u,t in parser.links:
                if re.search(r'csv|xlsx|xls|zip|pdf|2025|2026|実績|履歴|統計表|ダウンロード',u+' '+t,re.I):print(u,t)
