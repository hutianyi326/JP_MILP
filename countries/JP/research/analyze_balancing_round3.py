"""Published aggregate diagnostics, not an executable trading/backtest input."""
from pathlib import Path
import csv, json, calendar
import pandas as pd
B=Path(__file__).resolve().parent
OUT=B/'analysis'
areas=['北海道','東北','東京','中部','北陸','関西','中国','四国','九州']
frames=[]
for sid in ['E57','E56','E55']:
    p=next((B/'evidence').glob(sid+'_*.csv'))
    rows=list(csv.reader(p.read_text(encoding='cp932').splitlines()))
    for row in rows[2:]:
        if not row or not row[0]: continue
        ts=pd.Timestamp(row[0]+' '+row[1]).tz_localize('Asia/Tokyo')
        if not (pd.Timestamp('2025-01-01',tz='Asia/Tokyo')<=ts<pd.Timestamp('2026-09-01',tz='Asia/Tokyo')):continue
        assert rows[0][2:29:3]==areas
        for i,a in enumerate(areas):
            vals=[float(v) if v.strip() and v!='データ欠測' else float('nan') for v in row[2+3*i:5+3*i]]
            frames.append([ts.isoformat(),a,*vals,sid])
df=pd.DataFrame(frames,columns=['timestamp_JST','area','requirement_MW','FIT_forecast_error_MW','published_usage_pct','source_id'])
assert len(df)==29184*9 and not df.duplicated(['timestamp_JST','area']).any()
assert df.requirement_MW.dropna().ge(0).all() and df.published_usage_pct.dropna().between(0,100).all()
df.to_csv(OUT/'rrfit_forecast_usage_30min_JST_expost.csv',index=False,encoding='utf-8-sig')
df['month']=df.timestamp_JST.str[:7]
stats=df.groupby(['month','area'],sort=False).agg(n=('requirement_MW','size'),valid_requirement_n=('requirement_MW','count'),valid_error_n=('FIT_forecast_error_MW','count'),valid_usage_n=('published_usage_pct','count'),mean_requirement_MW=('requirement_MW','mean'),mean_published_usage_pct=('published_usage_pct','mean'),zero_requirement_fraction=('requirement_MW',lambda x:x.dropna().eq(0).mean()),negative_error_fraction=('FIT_forecast_error_MW',lambda x:x.dropna().lt(0).mean()),capped100_fraction=('published_usage_pct',lambda x:x.dropna().eq(100).mean())).reset_index()
stats.to_csv(OUT/'rrfit_forecast_usage_monthly.csv',index=False,encoding='utf-8-sig')
single=[]
for sid,month in [('E52','202604'),('E53','202605'),('E51','202607')]:
    p=next((B/'evidence').glob(sid+'_*.csv'))
    rows=list(csv.reader(p.read_text(encoding='cp932').splitlines()))
    assert rows[2][2:11]==areas
    n=calendar.monthrange(int(month[:4]),int(month[4:]))[1]*48*4
    data=[r for r in rows[3:] if r and r[0].startswith(month)]
    assert len(data)==n
    seen=set()
    for r in data:
        key=(r[0],r[1]);assert key not in seen;seen.add(key)
        vals=[float(v) for v in r[2:11]]
        assert all(v>=0 for v in vals) and sum(vals)==float(r[11])
        for a,v in zip(areas,vals):single.append([month,r[0],r[1],a,v,sid])
sf=pd.DataFrame(single,columns=['month','delivery_block','product','area','published_single_award_value','source_id'])
sf.groupby(['month','product','area'],sort=False).agg(n=('published_single_award_value','size'),mean_published_value=('published_single_award_value','mean'),zero_fraction=('published_single_award_value',lambda x:x.eq(0).mean())).reset_index().to_csv(OUT/'single_bid_award_monthly_rawunit.csv',index=False,encoding='utf-8-sig')
checks={'rrfit_rows':len(df),'rrfit_missing_by_field':df.iloc[:,2:5].isna().sum().to_dict(),'rrfit_area_months':len(stats),'single_area_product_blocks':len(sf),'single_total_equals_nine_areas':True,'time_zone':'Asia/Tokyo','rrfit_units':'MW; published percent','single_units':'original CSV does not state unit; not converted or used for revenue','missing_values_filled':False,'usage_is_measured_activation':False,'availability':'downloaded vintage; ex-post only; publication timestamps not reconstructed'}
(OUT/'balancing_round3_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(checks,ensure_ascii=False))
