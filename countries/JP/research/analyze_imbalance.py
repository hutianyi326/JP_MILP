from pathlib import Path
import pandas as pd
import csv,io,json,sys
sys.stdout.reconfigure(encoding='utf8')
B=Path(__file__).resolve().parent;O=B/'analysis'
areas=['北海道','東北','東京','中部','北陸','関西','中国','四国','九州'];data=[];vintages=[]
for f in sorted((B/'evidence').glob('IB_*.csv')):
    rows=list(csv.reader(io.StringIO(f.read_bytes().decode('cp932'))))
    meta=[r for r in rows if r[0]=='H'];vintages.append(dict(file=f.name,metadata=json.dumps(meta,ensure_ascii=False)))
    for r in rows:
        if r[0]!='D':continue
        for i,a in enumerate(areas):
            data.append(dict(timestamp=(pd.Timestamp(r[1])+pd.Timedelta(minutes=(int(r[2])-1)*30)).tz_localize('Asia/Tokyo'),area=a,surplus_JPY_kWh=pd.to_numeric(r[5+2*i],errors='coerce'),surplus_change_flag=r[6+2*i],shortfall_JPY_kWh=pd.to_numeric(r[23+2*i],errors='coerce'),shortfall_change_flag=r[24+2*i]))
d=pd.DataFrame(data);assert not d.duplicated(['timestamp','area']).any();assert len(d)==29184*9
d.to_csv(O/'imbalance_30min_JST_expost.csv',index=False,encoding='utf-8-sig');pd.DataFrame(vintages).to_csv(O/'imbalance_vintages.csv',index=False,encoding='utf-8-sig')
stats=[]
for (a,y),p in d.groupby(['area',d.timestamp.dt.year]):
    stats.append(dict(area=a,year=y,rows=len(p),surplus_mean=p.surplus_JPY_kWh.mean(),shortfall_mean=p.shortfall_JPY_kWh.mean(),shortfall_p95=p.shortfall_JPY_kWh.quantile(.95),shortfall_max=p.shortfall_JPY_kWh.max(),shortfall_missing=int(p.shortfall_JPY_kWh.isna().sum()),surplus_missing=int(p.surplus_JPY_kWh.isna().sum()),unequal_sides=int((p.surplus_JPY_kWh!=p.shortfall_JPY_kWh).sum())))
pd.DataFrame(stats).to_csv(O/'imbalance_statistics.csv',index=False,encoding='utf-8-sig');print(pd.DataFrame(stats).to_string(index=False))
