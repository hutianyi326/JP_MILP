"""Descriptive, ex-post research only. No trading optimization or model inputs."""
from pathlib import Path
import io,json,zipfile,re,unicodedata,sys,hashlib
import pandas as pd
import numpy as np
sys.stdout.reconfigure(encoding='utf8')
B=Path(__file__).resolve().parent; OUT=B/'analysis';OUT.mkdir(exist_ok=True)
AREAS=['北海道','東北','東京','中部','北陸','関西','中国','四国','九州']
START=pd.Timestamp('2025-01-01',tz='Asia/Tokyo');END=pd.Timestamp('2026-09-01',tz='Asia/Tokyo')
EXPECTED=pd.date_range(START,END,freq='30min',inclusive='left')
PERIODS={'2025全年':('2025-01-01','2026-01-01'),'2025年1至8月':('2025-01-01','2025-09-01'),'2026年1至8月':('2026-01-01','2026-09-01')}
checks=[];lineage=[]
def decode(data):
    for enc in ['utf-8-sig','cp932']:
        try:return data.decode(enc)
        except UnicodeDecodeError:pass
    raise ValueError('unknown encoding')
def save(df,name):df.to_csv(OUT/name,index=False,encoding='utf-8-sig')
prices=[]
for id in ['J09','J08','J10']:
    f=next((B/'evidence').glob(id+'_*.csv'));d=pd.read_csv(io.StringIO(decode(f.read_bytes())))
    d['timestamp']=pd.to_datetime(d.iloc[:,0])+pd.to_timedelta((pd.to_numeric(d.iloc[:,1])-1)*30,unit='min')
    d['timestamp']=d.timestamp.dt.tz_localize('Asia/Tokyo');d=d[(d.timestamp>=START)&(d.timestamp<END)]
    p=d[['timestamp']].copy();p['system']=d.iloc[:,5]
    for i,a in enumerate(AREAS):p[a]=pd.to_numeric(d.iloc[:,6+i],errors='coerce')
    p['market_volume_kWh']=pd.to_numeric(d.iloc[:,4],errors='coerce');prices.append(p)
    lineage.append({'dataset':'spot','file':f.name,'rows_in_scope':len(p)})
price=pd.concat(prices).sort_values('timestamp').set_index('timestamp')
assert not price.index.duplicated().any();assert price.index.equals(EXPECTED)
assert price[AREAS+['system']].notna().all().all()
save(price.reset_index(),'spot_30min_JST_expost.csv')
stats=[];months=[];daily=[]
for a in AREAS:
    for period,(start,end) in PERIODS.items():
        d=price.loc[(price.index>=pd.Timestamp(start,tz='Asia/Tokyo'))&(price.index<pd.Timestamp(end,tz='Asia/Tokyo'))];p=d[a]
        dr=p.groupby(p.index.date).agg(lambda x:x.max()-x.min())
        stats.append(dict(area=a,period=period,intervals=len(p),mean_JPY_kWh=p.mean(),p05=p.quantile(.05),median=p.median(),p95=p.quantile(.95),min=p.min(),max=p.max(),at_or_below_001_pct=p.le(.01).mean()*100,below_5_pct=p.lt(5).mean()*100,above_30_pct=p.gt(30).mean()*100,mean_daily_range=dr.mean(),difference_from_system_pct=p.sub(d.system).abs().gt(1e-7).mean()*100))
    for month,d in price[a].groupby(price.index.strftime('%Y-%m')):months.append(dict(area=a,month=month,mean_JPY_kWh=d.mean(),low_price_pct=d.le(.01).mean()*100))
    for day,d in price[a].groupby(price.index.date):daily.append(dict(area=a,date=str(day),range_JPY_kWh=d.max()-d.min(),min=d.min(),max=d.max(),mean=d.mean()))
save(pd.DataFrame(stats),'price_statistics.csv');save(pd.DataFrame(months),'price_monthly.csv');save(pd.DataFrame(daily),'price_daily.csv')
save(price[AREAS].corr().rename_axis('area').reset_index(),'price_correlation.csv')
fuels=['原子力','火力(LNG)','火力(石炭)','火力(石油)','火力(その他)','水力','地熱','バイオマス','太陽光発電実績','風力発電実績']
fund=[];fstat=[];profiles=[];fuelstats=[];bins=[];coverage=[];duration=[]
for ai,a in enumerate(AREAS,1):
    files=list((B/'evidence').glob(f'TS{ai:02}_*.csv'));streams=[(f.name,f.read_bytes()) for f in files]
    for f in (B/'evidence').glob(f'TS{ai:02}_*.zip'):
        with zipfile.ZipFile(f) as z:
            streams +=[(f.name+'::'+n,z.read(n)) for n in z.namelist() if n.lower().endswith('.csv')]
    chunks=[]
    for name,data in streams:
        s=decode(data).replace('\r\r\n','\n');lines=s.splitlines();h=next(i for i,l in enumerate(lines) if l.startswith('DATE,'))
        assert 'MW' in '\n'.join(lines[:h]),(name,'unrecognized units')
        d=pd.read_csv(io.StringIO('\n'.join(lines[h:])),dtype=str)
        d.columns=[unicodedata.normalize('NFKC',c).strip() for c in d.columns]
        d=d[d.DATE.notna() & d.TIME.notna()].copy()
        date=pd.to_datetime(d.DATE.str.replace('/','-',regex=False),format='mixed')
        mins=d.TIME.str.split(':').map(lambda t:int(t[0])*60+int(t[1]))
        # Kyushu official DATE/TIME is period end: 00:30 ... 24:00.
        offset=30 if ai==9 else 0
        d['timestamp']=(date+pd.to_timedelta(mins-offset,unit='min')).dt.tz_localize('Asia/Tokyo')
        d=d[(d.timestamp>=START)&(d.timestamp<END)].drop(columns=['DATE','TIME'])
        for c in d.columns:
            if c!='timestamp':d[c]=pd.to_numeric(d[c].str.replace(',','',regex=False),errors='coerce')
        lineage.append(dict(dataset=a,file=name,rows_in_scope=len(d),native_unit='MW average',timestamp_shift_minutes=-offset))
        if len(d):chunks.append(d)
    d=pd.concat(chunks).set_index('timestamp').sort_index()
    assert not d.index.duplicated().any(),a
    absent=EXPECTED.difference(d.index)
    coverage.append(dict(area=a,rows=len(d),expected=len(EXPECTED),missing_timestamps=len(absent),missing_load=int(d['エリア需要'].isna().sum()),island_scope='未取得可逐项验证的离岛剔除证明；诊断数据，禁止模型输入'))
    for c in d.columns:
        if not c.startswith('Unnamed'):checks.append(dict(area=a,field=c,count=int(d[c].notna().sum()),missing=int(d[c].isna().sum()),min=d[c].min(),max=d[c].max()))
    d=d.reindex(EXPECTED);d.index.name='timestamp';d['price_JPY_kWh']=price[a]
    d['residual_load_MW']=d['エリア需要']-d['太陽光発電実績']-d['風力発電実績']
    d['area']=a;d['scope_status']='diagnostic_only_islands_unresolved';fund.append(d)
    for period,(start,end) in PERIODS.items():
        p=d.loc[(d.index>=pd.Timestamp(start,tz='Asia/Tokyo'))&(d.index<pd.Timestamp(end,tz='Asia/Tokyo'))]
        load=p['エリア需要']; net=p.residual_load_MW
        fstat.append(dict(area=a,period=period,load_TWh=load.sum(min_count=1)*.5/1e6,load_mean_MW=load.mean(),load_max_MW=load.max(),load_min_MW=load.min(),load_factor=load.mean()/load.max(),netload_min_MW=net.min(),max_up_ramp_MW_per_30min=net.diff().max(),max_down_ramp_MW_per_30min=net.diff().min(),corr_load_price=load.corr(p.price_JPY_kWh),corr_netload_price=net.corr(p.price_JPY_kWh),corr_solar_price=p['太陽光発電実績'].corr(p.price_JPY_kWh),net_interchange_TWh=p['連系線'].sum(min_count=1)*.5/1e6,pv_curtailment_GWh=p['太陽光出力制御量'].sum(min_count=1)*.5/1000,valid_load_pct=load.notna().mean()*100,scope_status='diagnostic_only'))
        for c in fuels+['揚水','蓄電池','連系線','その他']:
            if c not in p:continue
            v=p[c];fuelstats.append(dict(area=a,period=period,fuel=c,energy_TWh=v.sum(min_count=1)*.5/1e6,percent_of_load=v.sum(min_count=1)/load.sum(min_count=1)*100,valid_pct=v.notna().mean()*100,scope_status='diagnostic_only'))
        for q in [0,.01,.05,.25,.5,.75,.95,.99,1]:duration.append(dict(area=a,period=period,quantile=q,load_MW=load.quantile(q),netload_MW=net.quantile(q)))
    d['year']=d.index.year;d['month']=d.index.month;d['slot']=d.index.hour*2+d.index.minute//30
    d['day_type']=np.where(d.index.weekday<5,'Mon-Fri','Sat-Sun')
    numeric=['エリア需要','residual_load_MW','price_JPY_kWh']+fuels+['揚水','蓄電池','連系線']
    prof=d.groupby(['year','month','day_type','slot'])[numeric].mean().reset_index();prof.insert(0,'area',a);profiles.append(prof)
    valid=d[['residual_load_MW','price_JPY_kWh']].dropna().copy();valid['netload_bin']=pd.qcut(valid.residual_load_MW,5,duplicates='drop')
    bb=valid.groupby('netload_bin',observed=True).agg(netload_mean_MW=('residual_load_MW','mean'),price_mean_JPY_kWh=('price_JPY_kWh','mean'),count=('price_JPY_kWh','size')).reset_index();bb.insert(0,'area',a);bins.append(bb)
save(pd.DataFrame(coverage),'fundamental_coverage.csv');save(pd.DataFrame(checks),'field_quality.csv');save(pd.DataFrame(fstat),'fundamental_statistics_DIAGNOSTIC.csv')
save(pd.DataFrame(fuelstats),'fuel_statistics_DIAGNOSTIC.csv');save(pd.concat(profiles),'monthly_daily_profiles_DIAGNOSTIC.csv');save(pd.concat(bins),'netload_price_bins_DIAGNOSTIC.csv');save(pd.DataFrame(duration),'load_duration_DIAGNOSTIC.csv')
save(pd.concat(fund).reset_index(),'fundamentals_30min_DIAGNOSTIC.csv');save(pd.DataFrame(lineage),'data_lineage.csv')
report={'research_window':'[2025-01-01,2026-09-01) Asia/Tokyo','expected_intervals_per_area':len(EXPECTED),'spot_complete':True,'supply_coverage':coverage,'missing_policy':'no filling','weekend_definition':'Sat/Sun only, national holidays not mapped','vintage':'retrieved 2026-09-28 UTC; latest available revisions; ex-post only','scope_gate':'fundamentals held for island boundary validation','not_a_backtest':True}
(OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(pd.DataFrame(stats)[['area','period','mean_JPY_kWh','mean_daily_range','at_or_below_001_pct']].round(3).to_string(index=False));print(pd.DataFrame(coverage)[['area','rows','missing_timestamps']].to_string(index=False))
