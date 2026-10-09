"""Full-date evidence package, with explicit missing/blocked activation inputs.

Does not impute statistics, invent resource parameters, or silently adopt June
market clocks for earlier historical deliveries. Native capacity blocks survive.
"""
from pathlib import Path
from datetime import datetime,timedelta
from collections import Counter
import argparse,csv,hashlib,io,json,math,zipfile

ROOT=Path(__file__).resolve().parents[2]
ANALYSIS=ROOT/'countries/JP/research/analysis'
RAW=ROOT/'data/raw/JP/shikoku_202601_0830_20261005'
OLD=ROOT/'data/raw/JP/shikoku_20260930'
START=datetime.fromisoformat('2026-01-01T00:00:00+09:00')
FORMAL_END=datetime.fromisoformat('2026-08-31T00:00:00+09:00')
END=datetime.fromisoformat('2026-09-01T00:00:00+09:00')
TIMES=[(START+timedelta(minutes=30*i)).isoformat() for i in range(int((END-START).total_seconds()/1800))]
PRODUCTS=('F','S1','S2','T1','R','C')

def number(s):
    if s.strip() in ('','-'):return None
    v=float(s)
    if not math.isfinite(v):raise ValueError('Nonfinite value')
    return v

def stamp(day,slot):
    return (datetime.strptime(day,'%Y%m%d').replace(tzinfo=START.tzinfo)+timedelta(minutes=30*(int(slot)-1))).isoformat()

def decode(blob):
    return list(csv.reader(io.StringIO(blob.decode('utf-8-sig' if blob.startswith(b'\xef\xbb\xbf') else 'cp932'))))

def in_scope(t):return START<=datetime.fromisoformat(t)<END
def period(t):return 'formal' if datetime.fromisoformat(t)<FORMAL_END else 'observation'
def regime(t):
    if t<'2026-03-14':return 'S3_20250401'
    if t<'2026-04-01':return 'S4_20260314'
    if t<'2026-07-01':return 'S5_20260401'
    return 'S6_20260701'

def put(d,k,v):
    if k in d:raise ValueError(f'Duplicate key {k}')
    d[k]=v

def build(out):
    if out.exists():raise ValueError('Use a new output directory; prior packages are immutable')
    sources={};issues=[]
    def register(p,**extra):
        key=p.relative_to(ROOT).as_posix()
        sources[key]=dict(path=key,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),**extra)
        return key
    def table(p):
        register(p)
        with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
    def issue(t,f,reason):issues.append(dict(timestamp_jst=t,period_role=period(t),field=f,reason=reason,handling='retain_raw_and_null_unusable_model_values_no_imputation'))
    downloads={}
    for p in sorted(RAW.glob('manifest_*.json')):
        register(p)
        for r in json.loads(p.read_text(encoding='utf-8')):
            if r.get('success'):downloads[r['id']]=r
    def fresh(kind,month):
        r=downloads.get(kind+'_'+month)
        if r:
            p=ROOT/r['path'];register(p,url=r['url'],access_utc=r['access_utc'])
            assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
            return p
        candidates=(list(OLD.glob(f'jukyu_LFC_shikoku_{month}.csv')) if kind=='lfc'
                    else list((ROOT/'data/raw/JP/shikoku_preparation_20261004').glob(f'ics_basis_{month}_*.csv')))
        if not candidates:return None
        assert len(candidates)==1
        p=candidates[0];register(p,selection='local_fallback_after_refresh_unavailable');return p

    dictionary=table(ROOT/'data/processed/JP/shikoku_202606_20260701_expost/field_dictionary.csv')
    lfields=[r for r in dictionary if r['source_family']=='lfc']
    efields=[r for r in dictionary if r['source_family']=='edc']
    lfc={};edc={};ics={}
    for month in [f'2026{m:02d}' for m in range(1,9)]:
        p=fresh('lfc',month)
        if p:
            for line,r in enumerate(decode(p.read_bytes())[1:],2):
                if not r:continue
                t=stamp(r[0],r[1]);assert len(r)==28
                if not in_scope(t):continue
                v={f['field']:number(r[int(f['source_column_1based'])-1]) for f in lfields}
                v.update(lfc_source=p.relative_to(ROOT).as_posix(),lfc_source_line=line)
                put(lfc,t,v)
        p=fresh('ics',month)
        if p:
            rows=decode(p.read_bytes());header=next(r for r in rows if r and r[0]=='T')
            assert all(header[i]=='四国' for i in (19,37,55,91))
            for line,r in enumerate(rows,1):
                if not r or r[0]!='D':continue
                t=stamp(r[1],r[2])
                if not in_scope(t):continue
                code=r[37];net=number(r[19]);price=number(r[91])
                assert code in ('','-','0','1')
                if code=='-':assert net==0
                put(ics,t,dict(ics_imbalance_mwh=None if net is None else net/1000,
                    ics_condition_code=code,ics_condition={'':'missing','-':'none','0':'shortage','1':'surplus'}[code],
                    ics_partition=number(r[55]),ics_marginal_price_jpy_per_mwh=None if price is None else price*1000,
                    ics_update_date=rows[2][1],ics_update_time=rows[2][2],ics_source=p.relative_to(ROOT).as_posix(),ics_source_line=line))
    for p in sorted(OLD.glob('jukyu_shikoku_*')):
        register(p,url='https://www.yonden.co.jp/nw/assets/adjusting_power_supply/'+('2026' if p.suffix=='.csv' else p.stem[-4:])+'/'+p.name)
        if p.suffix=='.zip':
            with zipfile.ZipFile(p) as z:entries=[(n,z.read(n)) for n in z.namelist() if n.endswith('.csv')]
        else:entries=[(p.name,p.read_bytes())]
        for name,blob in entries:
            if not '202601'<=Path(name).stem[-6:]<='202608':continue
            for line,r in enumerate(decode(blob)[1:],2):
                if not r:continue
                assert len(r)==24
                t=stamp(r[0],r[1])
                if not in_scope(t):continue
                v={}
                for f in efields:
                    value=number(r[int(f['source_column_1based'])-1]);v[f['field']]=None if value is None else value*float(f['multiply'])
                v.update(edc_source=p.relative_to(ROOT).as_posix(),edc_member=name,edc_source_line=line)
                put(edc,t,v)
    assert set(edc)==set(TIMES)
    spot={}
    for r in table(ANALYSIS/'spot_30min_JST_expost.csv'):
        t=datetime.fromisoformat(r['timestamp']).isoformat()
        if in_scope(t):put(spot,t,float(r['四国'])*1000)
    assert set(spot)==set(TIMES)
    backgrounds={t:dict(timestamp_jst=t,period_role=period(t)) for t in TIMES}
    for r in table(ANALYSIS/'imbalance_30min_JST_expost.csv'):
        t=datetime.fromisoformat(r['timestamp']).isoformat()
        if in_scope(t) and r['area']=='四国':backgrounds[t].update(imbalance_surplus_jpy_per_mwh=float(r['surplus_JPY_kWh'])*1000,imbalance_shortfall_jpy_per_mwh=float(r['shortfall_JPY_kWh'])*1000)
    for r in table(ANALYSIS/'intraday_30min_JST_expost.csv'):
        t=datetime.fromisoformat(r['timestamp']).isoformat()
        if in_scope(t):backgrounds[t].update(id_marketwide_average_jpy_per_mwh=float(r['reported_average_JPY_kWh'])*1000,id_market_scope=r['market_scope'])
    assert all(len(r)==6 for r in backgrounds.values())

    # Entire suspect day quarantined, not an automatic unit repair.
    suspect_days={t[:10] for t,r in lfc.items() if r['frequency_mean_hz'] is not None and abs(r['frequency_mean_hz'])>1}
    regional=[];inputs=[]
    for t in TIMES:
        lv=lfc.get(t,{**{f['field']:None for f in lfields},'lfc_source':None,'lfc_source_line':None})
        iv=ics.get(t,dict(ics_imbalance_mwh=None,ics_condition_code='',ics_condition='missing',ics_partition=None,ics_marginal_price_jpy_per_mwh=None,ics_update_date=None,ics_update_time=None,ics_source=None,ics_source_line=None))
        missing=any(lv[f['field']] is None for f in lfields)
        width_bad=any(lv[f'{n}_upper_equivalent_{u}'] is not None and lv[f'{n}_lower_equivalent_{u}'] is not None and lv[f'{n}_upper_equivalent_{u}']<lv[f'{n}_lower_equivalent_{u}'] for n,u in [('frequency','hz'),('ar','mw'),('ar_share','mw'),('zar','mw'),('lfc','mw'),('lfc_share','mw'),('zlfc','mw'),('z_total','mw')])
        status=('NO_SOURCE_FILE' if t not in lfc else 'SOURCE_VALUES_MISSING' if missing else 'QUARANTINED_SUSPECT_DAY' if t[:10] in suspect_days else 'INVALID_STATISTICAL_WIDTH' if width_bad else 'OBSERVED_STATISTICS')
        # Quarantine must also cover otherwise blank rows within suspect days.
        usable=not missing and t[:10] not in suspect_days and not width_bad
        edc_ok=all(edc[t][f['field']] is not None for f in efields)
        r=dict(timestamp_jst=t,period_role=period(t),duration_h=.5,area='四国',rule_regime=regime(t),da_price_jpy_per_mwh=spot[t],**lv,**edc[t],**iv,
               lfc_frequency_quality=status,quarantined_day=t[:10] in suspect_days,activation_statistics_usable=usable,edc_core_complete=edc_ok)
        regional.append(r)
        if not usable:issue(t,'frequency_and_lfc',status)
        if not edc_ok:issue(t,'edc','SOURCE_VALUES_MISSING')
        if iv['ics_condition']=='missing' or iv['ics_imbalance_mwh'] is None:issue(t,'ics','SOURCE_OR_VALUES_MISSING')
        inputs.append(dict(timestamp_jst=t,period_role=period(t),frequency_mean_hz=lv['frequency_mean_hz'] if usable else None,
            frequency_equivalent_scale_hz=(lv['frequency_upper_equivalent_hz']-lv['frequency_lower_equivalent_hz'])/4 if usable else None,
            lfc_mean_mw=lv['lfc_mean_mw'] if usable else None,
            lfc_equivalent_scale_mw=(lv['lfc_upper_equivalent_mw']-lv['lfc_lower_equivalent_mw'])/4 if usable else None,
            edc_A_mwh=edc[t]['edc_own_area_own_mo_A_mwh'],edc_B_mwh=edc[t]['edc_forecast_error_other_B_mwh'],
            fcr_activation_payment='NOT_APPLICABLE_NO_SURPLUS_CONTRACT',fcr_activation_price_up=None,fcr_activation_price_down=None,
            composite_activation_price_mapping='UNBOUND_NOT_V1_V2',activation_statistics_usable=usable,
            alpha_fcr_up=None,alpha_fcr_down=None,alpha_s1_up=None,alpha_s1_down=None,alpha_t1_up=None,alpha_t1_down=None,
            input_status='STATISTICS_ONLY_RUNTIME_AND_ASSUMPTION_BINDING_REQUIRED' if usable and edc_ok else 'BLOCKED_MISSING_OR_QUARANTINED_STATISTICS'))

    native=[];cap={}
    for raw in table(ANALYSIS/'eprx_awards_native_blocks_expost.csv'):
        if raw['area']!='四国' or not in_scope(raw['timestamp_JST']):continue
        r={k:(number(v) if k.endswith(('_MW','_count','_30min','_h')) else v) for k,v in raw.items()}
        t=r['timestamp_JST'];block='SHIKOKU/'+r['product']+'/'+t
        r.update(native_block_id=block,period_role=period(t),rule_regime=regime(t))
        for side in ('source','TSO'):
            valid=r[f'award_{side}_MW'] is not None and r[f'award_{side}_MW']>0 and r[f'avg_price_{side}_JPY_kW_30min'] is not None
            r[f'{side}_price_observation_valid']=valid
            r[f'{side}_price_candidate_JPY_MW_30min']=r[f'avg_price_{side}_JPY_kW_30min']*1000 if valid else None
        native.append(r)
        steps=round(r['duration_h']*2);assert steps in (1,6)
        for i in range(steps):
            key=(datetime.fromisoformat(t)+timedelta(minutes=30*i)).isoformat()
            if not in_scope(key):continue
            v=dict(r);v.update(timestamp_JST=key,native_block_start=t,native_duration_h=r['duration_h'],duration_h=.5,period_role=period(key),is_independent_offer=False)
            put(cap,(key,r['product']),v)
    assert set(cap)=={(t,p) for t in TIMES for p in PRODUCTS}
    for t in TIMES:
        for p in PRODUCTS:
            if not cap[t,p]['source_price_observation_valid']:issue(t,'capacity_'+p,'NO_VALID_SOURCE_PRICE_NOT_ZERO_FILL')
    # Verify archive member hashes; preserve exact source IDs and vintage flags.
    wanted={(r['source_id'],r['member']) for r in native};verified=set()
    for r in table(ANALYSIS/'eprx_archive_member_inventory.csv'):
        if (r['source_id'],r['member']) not in wanted:continue
        p=ROOT/'countries/JP/research/evidence'/r['archive'];register(p)
        with zipfile.ZipFile(p) as z:
            members=[n for n in z.namelist() if n.endswith(r['member'])];assert len(members)==1
            assert hashlib.sha256(z.read(members[0])).hexdigest()==r['sha256']
        verified.add((r['source_id'],r['member']))
    assert verified==wanted,(wanted-verified)
    register(ROOT/'countries/JP/topics/history_settlement_revision_20260928.md')
    register(ROOT/'project/jp_first_run_inputs_20261004/assumptions.json')
    register(ROOT/'project/jp_first_run_inputs_20261004/settlement_correction_20261005.md')
    monthly=[]
    for month in sorted({t[:7] for t in TIMES}):
        rr=[r for r in regional if r['timestamp_jst'].startswith(month) and r['period_role']=='formal']
        monthly.append(dict(month=month,formal_halfhours=len(rr),spot_complete=sum(r['da_price_jpy_per_mwh'] is not None for r in rr),
            edc_complete=sum(r['edc_core_complete'] for r in rr),frequency_lfc_usable=sum(r['activation_statistics_usable'] for r in rr),
            ics_net_present=sum(r['ics_imbalance_mwh'] is not None for r in rr),ics_marginal_price_present=sum(r['ics_marginal_price_jpy_per_mwh'] is not None for r in rr),
            fcr_price_present=sum(cap[r['timestamp_jst'],'F']['source_price_observation_valid'] for r in rr),composite_price_present=sum(cap[r['timestamp_jst'],'C']['source_price_observation_valid'] for r in rr)))
    windows=[];first=None;previous=None
    for r in regional+[dict(activation_statistics_usable=False,edc_core_complete=False)]:
        good=r['activation_statistics_usable'] and r['edc_core_complete']
        if good:
            if first is None:first=r['timestamp_jst']
            previous=r['timestamp_jst']
        elif first is not None:
            windows.append(dict(start_inclusive=first,end_exclusive=(datetime.fromisoformat(previous)+timedelta(minutes=30)).isoformat(),scope='STATISTICAL_COVERAGE_NOT_SOLVE_READY'))
            first=None
    status=dict(status='ASSEMBLED_WITH_EXPLICIT_GAPS_NOT_RUNNABLE',timezone='Asia/Tokyo',currency='JPY',information_scope='EX_POST_ONLY',
        formal_start=START.isoformat(),formal_end_exclusive=FORMAL_END.isoformat(),observation_end_exclusive=END.isoformat(),
        formal_halfhours=sum(period(t)=='formal' for t in TIMES),observation_halfhours=48,regional_rows=len(regional),native_capacity_rows=len(native),expanded_capacity_rows=len(cap),
        formal_activation_statistics_usable=sum(r['activation_statistics_usable'] for r in regional if r['period_role']=='formal'),
        observation_activation_statistics_usable=sum(r['activation_statistics_usable'] for r in regional if r['period_role']=='observation'),
        suspect_days=sorted(suspect_days),quality_issue_rows=len(issues),capacity_vintages=dict(Counter(r['quality'] for r in native)),
        products=list(PRODUCTS),offline_primary_included=False,raw_archive_members_verified=len(verified),runnable_model_input=False,formal_solve_performed=False,
        unresolved=['Missing early frequency/LFC; no imputation authorized','Suspect LFC days including observation tail','Asset/control parameters and full-inner composite menu',
        'June adapter hardcodes month and D-1 clocks; not compatible with this package','Historical native blocks and gates require version-specific binding or an explicitly approved counterfactual scenario',
        'Initial commitments or preparation period','Composite activation assumptions/reference fit and proxy pricing require period-specific binding','Imbalance settlement excluded; not full net revenue'],
        checks=['complete unique JST grid','all six native products cover every halfhour without overlap','native block identity retained','no missing activation filled with zero',
        'quarantine raw values retained but unusable model statistics null','capacity price conversion x1000 only','archive member hashes checked','sources unchanged'])
    for r in sources.values():assert hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256']
    out.mkdir(parents=True)
    def save(name,obj):(out/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    def write(name,rows):
        with (out/name).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    write('regional_30min.csv',regional);write('activation_input_template.csv',inputs)
    write('capacity_native_blocks.csv',native);write('capacity_30min.csv',[cap[k] for k in sorted(cap)])
    write('background_prices_30min.csv',list(backgrounds.values()));write('coverage_monthly.csv',monthly)
    write('quality_issues.csv',issues);write('field_dictionary.csv',dictionary)
    save('source_manifest.json',list(sources.values()));save('readiness.json',status);save('usable_statistical_windows.json',windows)
    save('package_manifest.json',dict(builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file()}))
    return status

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='data/processed/JP/shikoku_20260101_20260830_expost_v1')
    print(json.dumps(build(ROOT/parser.parse_args().output),ensure_ascii=False,indent=2))
