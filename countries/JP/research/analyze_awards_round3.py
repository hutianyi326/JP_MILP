"""Ex-post official EPRX archives; native blocks, no trading simulation."""
from pathlib import Path
import csv, hashlib, json, re, zipfile
import pandas as pd
B=Path(__file__).resolve().parent
areas=['北海道','東北','東京','中部','北陸','関西','中国','四国','九州']
fields=['requirement_TSO_MW','offer_source_MW','award_source_MW','offer_source_count','award_source_count','max_price_source_JPY_kW_30min','min_price_source_JPY_kW_30min','avg_price_source_JPY_kW_30min','max_price_TSO_JPY_kW_30min','min_price_TSO_JPY_kW_30min','avg_price_TSO_JPY_kW_30min','award_TSO_MW','local_award_MW']
def field_name(s):
    s=s.replace('落札','約定')
    labels=['募集量（TSO別）[MW]','応札量合計（電源属地別）[MW]','約定量合計（電源属地別）[MW]','応札件数（電源属地別）[件]','約定件数（電源属地別）[件]','最高約定価格（電源属地別）[円/kW・30分]','最低約定価格（電源属地別）[円/kW・30分]','平均約定価格（電源属地別）[円/kW・30分]','最高約定価格（TSO別）[円/kW・30分]','最低約定価格（TSO別）[円/kW・30分]','平均約定価格（TSO別）[円/kW・30分]','約定量合計（TSO別）[MW]','（内訳）自エリアからの約定量[MW]']
    return fields[labels.index(s)]
records=[]; inventory=[]; padding=0
for product in ['F','S1','S2','T1','R','C']:
    for sid in [f'EA{y}{product}' for y in ['24','25','26']]+[f'EP26{product}']:
        p=next((B/'evidence').glob(sid+'_*.zip'))
        prompt=sid.startswith('EP')
        with zipfile.ZipFile(p) as z:
            for member in z.namelist():
                if not member.endswith('.csv'):continue
                raw=z.read(member)
                rows=[r for r in csv.reader(raw.decode('cp932').splitlines()) if r]
                ym=rows[1][2]; blocks=int(rows[1][4]); duration=24/blocks
                if not ('202501'<=ym<='202608') or (prompt and ym!='202608'):continue
                span=re.search(r'_(\d{4})-(\d{4})_',member)
                off=2 if prompt else 3
                assert rows[2][off:off+9]==areas,(sid,member,rows[2])
                values={}; dropped=0
                for r in rows[3:]:
                    if not re.fullmatch(r'\d{8}B\d{2}',r[0]):continue
                    if span and not span[1]<=r[0][4:8]<=span[2]:
                        dropped+=1;continue
                    if not prompt and r[1]!='合計（確報値）':continue
                    key=r[0]; name=field_name(r[off-1]); vals=[float(v) if v not in ('-','') else float('nan') for v in r[off:off+9]]
                    assert name not in values.setdefault(key,{}),(sid,member,key,name)
                    values[key][name]=vals
                for key,vals in values.items():
                    assert set(vals)==set(fields),(sid,member,key,set(vals))
                    ts=pd.Timestamp(key[:8],tz='Asia/Tokyo')+pd.Timedelta(hours=(int(key[-2:])-1)*duration)
                    for i,area in enumerate(areas):
                        records.append([ts.isoformat(),product,area,duration,'prompt' if prompt else 'final',sid,member,*[vals[f][i] for f in fields]])
                padding+=dropped
                inventory.append(dict(source_id=sid,archive=p.name,member=member,sha256=hashlib.sha256(raw).hexdigest(),native_blocks_per_day=blocks,retained_blocks=len(values),excluded_padding_rows=dropped,quality='prompt' if prompt else 'final'))
df=pd.DataFrame(records,columns=['timestamp_JST','product','area','duration_h','quality','source_id','member',*fields])
assert not df.duplicated(['timestamp_JST','product','area']).any()
coverage=df.groupby(['product','area']).duration_h.sum()
assert coverage.eq(608*24).all(),coverage
for product,g in df.groupby('product'):
    cut='2025-03-14' if product=='R' else '2026-03-14'
    expected=list(pd.date_range('2025-01-01',cut,freq='3h',inclusive='left',tz='Asia/Tokyo'))+list(pd.date_range(cut,'2026-09-01',freq='30min',inclusive='left',tz='Asia/Tokyo'))
    for area,a in g.groupby('area'):
        actual=pd.DatetimeIndex(pd.to_datetime(a.timestamp_JST)).tz_convert('Asia/Tokyo').sort_values()
        assert actual.equals(pd.DatetimeIndex(expected)),(product,area,'native time grid mismatch')
assert df[fields].min().min()>=0
df.to_csv(B/'analysis/eprx_awards_native_blocks_expost.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(inventory).to_csv(B/'analysis/eprx_archive_member_inventory.csv',index=False,encoding='utf-8-sig')
df['month']=df.timestamp_JST.str[:7]
stats=[]
for (month,product,area,quality),g in df.groupby(['month','product','area','quality'],sort=False):
    hours=g.duration_h.sum(); s=dict(month=month,product=product,area=area,quality=quality,native_blocks=len(g),hours=hours)
    for side in ['source','TSO']:
        weights=g[f'award_{side}_MW']*g.duration_h
        s[f'average_award_{side}_MW']=weights.sum()/hours
        s[f'weighted_price_{side}_JPY_kW_30min']=(weights*g[f'avg_price_{side}_JPY_kW_30min']).sum()/weights.sum() if weights.sum()>0 else float('nan')
    offered=(g.offer_source_MW*g.duration_h).sum()
    s['aggregate_award_offer_ratio']=(g.award_source_MW*g.duration_h).sum()/offered if offered else float('nan')
    s['average_requirement_TSO_MW']=(g.requirement_TSO_MW*g.duration_h).sum()/hours
    stats.append(s)
pd.DataFrame(stats).to_csv(B/'analysis/eprx_awards_area_monthly.csv',index=False,encoding='utf-8-sig')
checks=dict(rows=len(df),product_area_series=len(coverage),hours_per_series=608*24,duplicates=0,excluded_padding_rows=padding,months=20,area_month_product_rows=len(stats),source_price_unit='JPY/kW/30min even when block=3h',final_through='2026-07-31',prompt_window='2026-08-01/2026-08-31',ex_post_only=True,geography='official nine procurement areas; not physical island-filtered generation',missing_fields=df[fields].isna().sum().to_dict())
(B/'analysis/awards_round3_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(checks,ensure_ascii=False))
