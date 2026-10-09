import pathlib,re,json,sys
sys.stdout.reconfigure(encoding='utf-8')
B=pathlib.Path(__file__).resolve().parent
jobs=[]
for pre in ['J06','D04B','D06B','D07B','D09B']:
 p=next((B/'evidence').glob(pre+'_*'),None)
 if not p:continue
 s=p.read_text(encoding='utf-8',errors='replace')
 print('\n',p.name)
 if pre=='J06':print(s[:500]);continue
 if pre in ['D04B','D06B']:print('\n'.join(x for x in s.splitlines() if ('data-json' in x or '<script' in x) and len(x)<350))
 if pre in ['D07B','D09B']: print('\n'.join(x for x in s.splitlines() if any(k in x for k in ['eria','FileNm','fileNm','conData','ext1','dir1','path','prefix']) and len(x)<250)[:2000])
