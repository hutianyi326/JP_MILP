import pathlib,re,sys
sys.stdout.reconfigure(encoding='utf8')
B=pathlib.Path(__file__).resolve().parent
id=sys.argv[1]; s=next((B/'extracted').glob(id+'_*')).read_text(encoding='utf8')
pages=re.split(r'=== PDF PAGE (\d+) ===',s)
if sys.argv[2]=='pages':
    wanted={int(n) for n in sys.argv[3:]}
    for j in range(1,len(pages),2):
        if int(pages[j]) in wanted: print('PAGE',pages[j],pages[j+1])
else:
    pat=sys.argv[2];maxhits=int(sys.argv[3]) if len(sys.argv)>3 else 12;hits=0
    for j in range(1,len(pages),2):
        for m in re.finditer(pat,pages[j+1]):
            print('PAGE',pages[j],pages[j+1][max(0,m.start()-90):m.end()+240].replace('\n',' '));hits+=1
            if hits>=maxhits:sys.exit()
