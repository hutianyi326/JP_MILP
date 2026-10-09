"""Supplementary ex-post descriptions; never a trading strategy or live model input."""
from pathlib import Path
import pandas as pd, numpy as np, zipfile, hashlib, json, re, sys
sys.stdout.reconfigure(encoding='utf8')
B=Path(__file__).resolve().parent; A=B/'analysis'
expected=pd.date_range('2025-01-01','2026-09-01',freq='30min',inclusive='left',tz='Asia/Tokyo')
frames=[]
for sid in ['J16','J17','J18']:
    p=next((B/'evidence').glob(sid+'_*.csv')); d=pd.read_csv(p,encoding='cp932')
    assert d.columns.tolist()==['年月日','時刻コード','始値（円/kWh）','高値（円/kWh）','安値（円/kWh）','終値（円/kWh）','平均（円/kWh）','約定量合計（MWh/h）','約定件数']
    d.columns=['date','slot','open_JPY_kWh','high_JPY_kWh','low_JPY_kWh','close_JPY_kWh','reported_average_JPY_kWh','native_volume_MWh_per_h','trade_count']
    d['timestamp']=(pd.to_datetime(d.date)+pd.to_timedelta((d.slot-1)*30,unit='min')).dt.tz_localize('Asia/Tokyo')
    d=d[d.timestamp.isin(expected)].drop(columns=['date','slot']);d['source_id']=sid; frames.append(d)
d=pd.concat(frames).sort_values('timestamp').reset_index(drop=True)
assert pd.DatetimeIndex(d.timestamp).equals(expected)
assert not d.timestamp.duplicated().any()
prices=['open_JPY_kWh','high_JPY_kWh','low_JPY_kWh','close_JPY_kWh','reported_average_JPY_kWh']
assert d[prices+['native_volume_MWh_per_h','trade_count']].notna().all().all()
assert d[prices].ge(d.low_JPY_kWh,axis=0).all().all() and d[prices].le(d.high_JPY_kWh,axis=0).all().all()
spot=pd.read_csv(A/'spot_30min_JST_expost.csv');spot['timestamp']=pd.to_datetime(spot.timestamp)
d=d.merge(spot[['timestamp','system']],on='timestamp',validate='one_to_one').rename(columns={'system':'DA_system_JPY_kWh'})
d['ID_minus_DA_system_JPY_kWh']=d.reported_average_JPY_kWh-d.DA_system_JPY_kWh
d['market_scope']='JEPX_marketwide_not_area_execution_price'
# Retain the source unit: do not silently equate MWh/h with a half-hour energy quantity.
d.to_csv(A/'intraday_30min_JST_expost.csv',index=False,encoding='utf-8-sig')
periods={'2025全年':('2025-01-01','2026-01-01'),'2025年1至8月':('2025-01-01','2025-09-01'),'2026年1至8月':('2026-01-01','2026-09-01')}
stats=[]
for name,(start,end) in periods.items():
    g=d[(d.timestamp>=pd.Timestamp(start,tz='Asia/Tokyo'))&(d.timestamp<pd.Timestamp(end,tz='Asia/Tokyo'))]
    stats.append(dict(period=name,intervals=len(g),reported_average_time_mean=g.reported_average_JPY_kWh.mean(),DA_system_time_mean=g.DA_system_JPY_kWh.mean(),mean_ID_minus_DA=g.ID_minus_DA_system_JPY_kWh.mean(),p05_ID_minus_DA=g.ID_minus_DA_system_JPY_kWh.quantile(.05),p95_ID_minus_DA=g.ID_minus_DA_system_JPY_kWh.quantile(.95),mean_native_volume_MWh_per_h=g.native_volume_MWh_per_h.mean(),sum_trade_count=g.trade_count.sum(),mean_high_low_range=(g.high_JPY_kWh-g.low_JPY_kWh).mean()))
pd.DataFrame(stats).to_csv(A/'intraday_statistics.csv',index=False,encoding='utf-8-sig')
# Archive member inventory preserves original filenames, bytes and file-level applicability hints.
members=[]
for sid in ['E41','E42','E43']:
    with zipfile.ZipFile(next((B/'evidence').glob(sid+'_*.zip'))) as z:
        for n in z.namelist():
            if not n.lower().endswith('.csv'):continue
            raw=z.read(n); dates=re.findall(r'20\d{6}',n)
            text=raw.decode('cp932'); lines=[x for x in text.splitlines() if x.strip()]
            members.append(dict(source_id=sid,member=n,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),filename_dates=';'.join(dates),first_header=lines[0],scope='public_requirement_not_awarded_volume_or_price'))
pd.DataFrame(members).to_csv(A/'requirement_archive_inventory.csv',index=False,encoding='utf-8-sig')
print(pd.DataFrame(stats).round(4).to_string(index=False));print('requirement archive members',len(members))
fund=pd.read_csv(A/'fundamentals_30min_DIAGNOSTIC.csv',low_memory=False)
fund['timestamp']=pd.to_datetime(fund.timestamp);fund['date']=fund.timestamp.dt.strftime('%Y-%m-%d')
# OCCTO EV02 p1 explicitly selects these five days; the five values are PLANNED MW, not actual energy.
event_days=['2025-04-13','2025-04-17','2025-05-04','2025-05-25','2025-06-01']
planned=[4866,2690,4941,4393,4278]
event_rows=[]
for day,plan in zip(event_days,planned):
    g=fund[(fund.area=='九州')&(fund.date==day)]
    assert len(g)==48
    event_rows.append(dict(date=day,area='九州',official_case_source='EV01 pp3,12-14;EV02 p1',planned_curtailment_MW_at_reference_slot=plan,load_mean_MW=g['エリア需要'].mean(),load_min_MW=g['エリア需要'].min(),solar_actual_energy_MWh=g['太陽光発電実績'].sum()*.5,solar_curtailment_energy_MWh=g['太陽光出力制御量'].sum()*.5,net_import_mean_MW=g.net_import_MW.mean(),spot_mean_JPY_kWh=g.price_JPY_kWh.mean(),spot_floor_halfhours=g.price_JPY_kWh.le(.01).sum(),scope_status='TS09_diagnostic_island_boundary_unresolved'))
pd.DataFrame(event_rows).to_csv(A/'event_comparison_DIAGNOSTIC.csv',index=False,encoding='utf-8-sig')
print(pd.DataFrame(event_rows).round(3).to_string(index=False))
# A dated official requirement template, not awards, daily actual procurement, or offline caps.
import csv,io
req=[]
with zipfile.ZipFile(next((B/'evidence').glob('E43_*.zip'))) as z:
    member='2026_Requirement_archive/2026_Requirement_20260309(20260401).csv'
    rows=list(csv.reader(io.StringIO(z.read(member).decode('cp932').replace('\r\r\n','\n'))))
    product=None; header=None
    for r in rows:
        if not r or not any(r):continue
        if r[0].endswith('_[MW]'):product=r[0].replace('_Requirement_[MW]','');continue
        if re.match(r'2026/4_',r[0]):header=r;continue
        if not re.match(r'\d\d:\d\d～',r[0]):continue
        assert product and header
        for j in range(0,50,10):
            month=header[j].rstrip('_');year,m=map(int,month.split('/'))
            for offset in range(1,10):
                area=header[j+offset];value=r[j+offset]
                assert area in ['北海道','東北','東京','中部','北陸','関西','中国','四国','九州']
                assert value!=''
                req.append(dict(product=product,month=f'{year:04}-{m:02}',slot=r[j],area=area,requirement_MW=float(value),source_id='E43',source_member=member,publication_date_from_filename='2026-03-09',effective_from_filename='2026-04-01',scope='published_requirement_template_not_award_or_offline_cap'))
req=pd.DataFrame(req);assert len(req)==5*5*48*9
assert not req.duplicated(['product','month','slot','area']).any()
req.to_csv(A/'requirement_template_2026_AprAug_v20260309.csv',index=False,encoding='utf-8-sig')
rq=req.groupby(['product','month','area']).requirement_MW.agg(['min','mean','max']).reset_index()
rq.to_csv(A/'requirement_template_statistics.csv',index=False,encoding='utf-8-sig')
print('dated 2026 Apr-Aug requirement template cells',len(req))
