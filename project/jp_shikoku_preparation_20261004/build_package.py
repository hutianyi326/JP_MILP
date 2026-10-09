"""Prepare ex-post regional evidence, not a runnable asset/model configuration."""
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import csv, io, json, math, hashlib, zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
OUT = ROOT / 'data/processed/JP/shikoku_202606_20260701_expost'
RAW = ROOT / 'data/raw/JP/shikoku_preparation_20261004'
ANALYSIS = ROOT / 'countries/JP/research/analysis'
START = datetime.fromisoformat('2026-06-01T00:00:00+09:00')
END = datetime.fromisoformat('2026-07-02T00:00:00+09:00')
TIMES = [(START + timedelta(minutes=30*i)).isoformat() for i in range(1488)]
SOURCES, DICTIONARY, ISSUES = {}, [], []

def register(path, **extra):
    key = path.relative_to(ROOT).as_posix()
    SOURCES[key] = dict(path=key, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), **extra)
    return key

def table(path, encoding='utf-8-sig'):
    register(path)
    with path.open(encoding=encoding, newline='') as stream:
        yield from csv.DictReader(stream)

def rawrows(path):
    register(path)
    blob = path.read_bytes()
    return list(csv.reader(io.StringIO(blob.decode('utf-8-sig' if blob.startswith(b'\xef\xbb\xbf') else 'cp932'))))

def num(value):
    if value.strip() in ('', '-'): return None
    answer = float(value)
    if not math.isfinite(answer): raise ValueError(value)
    return answer

def stamp(day, slot):
    return (datetime.strptime(day, '%Y%m%d').replace(tzinfo=START.tzinfo) + timedelta(minutes=30*(int(slot)-1))).isoformat()

def scope(t): return START <= datetime.fromisoformat(t) < END
def write_csv(name, rows):
    assert rows, name
    with (OUT/name).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

def put(target, key, value):
    assert key not in target, ('duplicate', key)
    target[key] = value

def H(m,s):
    if s == 0: return max(m,0)
    z=m/s
    return s*math.exp(-z*z/2)/math.sqrt(2*math.pi) + m*(1+math.erf(z/math.sqrt(2)))/2

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # Actual data headers, all three-statistic groups retained.
    lfc_names = ['frequency','ar','ar_share','zar','lfc','lfc_share','zlfc','z_total']
    lfc_fields = [(4+3*g+k, f'{n}_{suffix}_{"hz" if g==0 else "mw"}', 1)
                  for g,n in enumerate(lfc_names)
                  for k,suffix in enumerate(['mean','upper_equivalent','lower_equivalent'])]
    edc_names = ['forecast_imbalance','netting','own_area_other_mo_exchange','own_area_own_mo_A',
                 'other_area_own_mo_O','after_wide_imbalance','forecast_error_other_B','actual_imbalance_reference']
    edc_fields = [(4+i,f'edc_{n}_mwh',.001) for i,n in enumerate(edc_names)]
    cost_names = ['netting','own_area_other_mo_exchange','A','O','B','actual_imbalance_reference']
    edc_fields += [(12+i,f'edc_{n}_cost_jpy',1) for i,n in enumerate(cost_names)]
    edc_fields += [(18+i,f'edc_{n}_unit_price_jpy_per_mwh',1000) for i,n in enumerate(cost_names)]
    channels = {}
    for kind, fields in [('lfc',lfc_fields),('edc',edc_fields)]:
        selected={}
        for month in ('202606','202607'):
            candidates=list(RAW.glob(f'shikoku_{kind}_{month}_*.csv')); assert len(candidates)==1
            path=candidates[0]; rows=rawrows(path); source=path.relative_to(ROOT).as_posix()
            for idx,name,factor in fields:
                if month=='202606': DICTIONARY.append(dict(table='regional_30min.csv',field=name,source_family=kind,source_column_1based=idx+1,source_header=rows[0][idx],multiply=factor,role='official_statistic'))
            for line,r in enumerate(rows[1:],2):
                if not r or len(r[0])!=8 or not r[0].isdigit():continue
                t=stamp(r[0],r[1])
                if not scope(t):continue
                out={name:None if num(r[idx]) is None else num(r[idx])*factor for idx,name,factor in fields}
                out.update({f'{kind}_source':source,f'{kind}_source_line':line})
                put(selected,t,out)
        assert set(selected)==set(TIMES)
        channels[kind]=selected

    ics={}
    for month in ('202606','202607'):
        paths=list(RAW.glob(f'ics_basis_{month}_*.csv'));assert len(paths)==1
        path=paths[0];rows=rawrows(path); header=next(r for r in rows if r[0]=='T')
        assert all(header[i]=='四国' for i in (19,37,55,91))
        groupheader=rows[2]
        for i,name,factor in [(19,'ics_imbalance_mwh',.001),(37,'ics_condition_code',1),(55,'ics_partition',1),(91,'ics_marginal_price_jpy_per_mwh',1000)]:
            if month=='202606':DICTIONARY.append(dict(table='regional_30min.csv',field=name,source_family='ics',source_column_1based=i+1,source_header=groupheader[i-14]+' / 四国',multiply=factor,role='conditioning_or_background_only'))
        for line,r in enumerate(rows,1):
            if not r or r[0]!='D':continue
            t=stamp(r[1],r[2])
            if not scope(t):continue
            imbalance=num(r[19]);code=r[37]
            label={'1':'surplus','0':'shortage','-':'none','':'missing'}[code]
            if code=='-': assert imbalance==0
            values=dict(ics_imbalance_mwh=None if imbalance is None else imbalance/1000,
                        ics_condition_code=code,ics_condition=label,ics_partition=num(r[55]),
                        ics_marginal_price_jpy_per_mwh=None if num(r[91]) is None else num(r[91])*1000,
                        ics_update_date=rows[2][1],ics_update_time=rows[2][2],ics_source=path.relative_to(ROOT).as_posix(),ics_source_line=line)
            put(ics,t,values)
            if imbalance is None or code=='': ISSUES.append(dict(timestamp_jst=t,table='regional_30min.csv',field='ics_imbalance_mwh / ics_condition',severity='conditional_input_gap',handling='retain_null; do_not_fill_zero; affects_ICS_conditioned_runs_only'))
    assert set(ics)==set(TIMES)
    spot={}
    for r in table(ANALYSIS/'spot_30min_JST_expost.csv'):
        t=datetime.fromisoformat(r['timestamp']).isoformat()
        if scope(t):put(spot,t,float(r['四国'])*1000)
    assert set(spot)==set(TIMES)
    regional=[]
    for t in TIMES:
        r=dict(timestamp_jst=t,period_role='formal' if t<'2026-07-01' else 'observation',duration_h=.5,area='四国',da_price_jpy_per_mwh=spot[t],**channels['lfc'][t],**channels['edc'][t],**ics[t])
        assert all(r[name] is not None for _,name,_ in lfc_fields+edc_fields)
        assert abs(r['frequency_mean_hz'])<1
        for n in lfc_names:
            unit='hz' if n=='frequency' else 'mw'
            assert r[f'{n}_upper_equivalent_{unit}']>=r[f'{n}_lower_equivalent_{unit}']
        regional.append(r)
    write_csv('regional_30min.csv',regional)

    capacity={}
    for r in table(ANALYSIS/'eprx_awards_native_blocks_expost.csv'):
        if r['area']!='四国':continue
        t=datetime.fromisoformat(r['timestamp_JST']).isoformat()
        if not scope(t):continue
        assert float(r['duration_h'])==.5
        out={k:(num(v) if k.endswith(('_MW','_count','_30min','_h')) else v) for k,v in r.items()}
        put(capacity,(t,r['product']),out)
    for month in ('202606','202607'):
        paths=list((ROOT/'countries/JP/data/raw/history_round3/E58_unpacked').glob(f'**/{month}_1-1_result.csv')); assert len(paths)==1
        path=paths[0];rows=rawrows(path);assert rows[1][3]=='一次オフライン' and rows[1][4]=='48' and rows[2][10]=='四国'
        archive=ROOT/'countries/JP/data/raw/history_round3/E58_2026_1-1_result.zip';register(archive)
        with zipfile.ZipFile(archive) as z:
            members=[n for n in z.namelist() if n.endswith(path.name)];assert len(members)==1 and z.read(members[0])==path.read_bytes()
        grouped=defaultdict(dict)
        for r in rows[3:]:
            if len(r)<11 or r[1]!='合計（確報値）':continue
            t=stamp(r[0][:8],r[0].split('B')[1])
            if scope(t):put(grouped[t],r[2],num(r[10]))
        mapping={'requirement_TSO_MW':'募集量（TSO別）[MW]','offer_source_MW':'応札量合計（電源属地別）[MW]',
                 'award_source_MW':'約定量合計（電源属地別）[MW]','offer_source_count':'応札件数（電源属地別）[件]',
                 'award_source_count':'約定件数（電源属地別）[件]','award_TSO_MW':'約定量合計（TSO別）[MW]',
                 'local_award_MW':'（内訳）自エリアからの約定量[MW]'}
        for side,jp in [('source','電源属地別'),('TSO','TSO別')]:
            for eng,jpstat in [('max','最高'),('min','最低'),('avg','平均')]:mapping[f'{eng}_price_{side}_JPY_kW_30min']=f'{jpstat}約定価格（{jp}）[円/kW・30分]'
        for t,g in grouped.items():
            out=dict(timestamp_JST=t,product='F_OFFLINE',area='四国',duration_h=.5,quality='final',source_id='E58_2026_1-1_result',member=path.name,**{k:g[v] for k,v in mapping.items()})
            put(capacity,(t,'F_OFFLINE'),out)
    assert set(capacity)=={(t,p) for t in TIMES for p in ('F','S1','S2','T1','R','C','F_OFFLINE')}
    # Corroborate existing processed prices/awards against downloaded official bytes.
    spot_raw=ROOT/'countries/JP/research/evidence/J10_f6c5ab4cee06.csv'
    spot_check={}
    for r in rawrows(spot_raw)[1:]:
        if not r or not r[0]:continue
        t=stamp(r[0].replace('/','').replace('-',''),r[1])
        if scope(t):spot_check[t]=float(r[13])*1000
    assert spot_check==spot
    archive_index=list(table(ANALYSIS/'eprx_archive_member_inventory.csv'))
    verified=set()
    for item in archive_index:
        if item['source_id'] not in {f'EA26{p}' for p in ('F','S1','S2','T1','R','C')}:continue
        if not Path(item['member']).name.startswith(('202606','202607')):continue
        p=item['source_id'][4:]
        archive=ROOT/'countries/JP/research/evidence'/item['archive'];register(archive)
        with zipfile.ZipFile(archive) as z:
            names=[n for n in z.namelist() if n.endswith(item['member'])];assert len(names)==1
            blob=z.read(names[0]);assert hashlib.sha256(blob).hexdigest()==item['sha256']
        parsed=list(csv.reader(io.StringIO(blob.decode('cp932'))));assert parsed[2][10]=='四国'
        for rr in parsed[3:]:
            if len(rr)<11 or rr[1]!='合計（確報値）':continue
            t=stamp(rr[0][:8],rr[0].split('B')[1])
            if not scope(t):continue
            for target,descriptor in mapping.items():
                if rr[2]==descriptor:
                    assert capacity[t,p][target]==num(rr[10]), (t,p,target)
                    verified.add((t,p,target))
    assert len(verified)==1488*6*len(mapping),len(verified)
    caprows=[]
    for (t,p),r in sorted(capacity.items()):
        r['period_role']='formal' if t<'2026-07-01' else 'observation'
        for side in ('source','TSO'):
            valid=r[f'award_{side}_MW'] is not None and r[f'award_{side}_MW']>0 and r[f'avg_price_{side}_JPY_kW_30min'] is not None
            r[f'{side}_price_observation_valid']=valid
            r[f'{side}_price_candidate_JPY_MW_30min']=r[f'avg_price_{side}_JPY_kW_30min']*1000 if valid else None
        r['model_price_approved']=False
        r['product_scope']='offline_subset' if p=='F_OFFLINE' else ('aggregate_composite_not_specific_S1_T1' if p=='C' else ('primary_unseparated' if p=='F' else 'published_product'))
        r['offline_registered_quota_MW']=r['requirement_TSO_MW'] if p=='F_OFFLINE' else None
        r['offline_effective_market_cap_MW']=min(r['requirement_TSO_MW'],capacity[t,'F']['requirement_TSO_MW']) if p=='F_OFFLINE' else None
        caprows.append(r)
    write_csv('capacity_30min.csv',caprows)
    # Keep optional background series apart: neither is a station activation price.
    background={t:dict(timestamp_jst=t) for t in TIMES}
    for r in table(ANALYSIS/'intraday_30min_JST_expost.csv'):
        t=datetime.fromisoformat(r['timestamp']).isoformat()
        if scope(t):background[t].update(id_marketwide_average_jpy_per_mwh=float(r['reported_average_JPY_kWh'])*1000,id_market_scope=r['market_scope'])
    for r in table(ANALYSIS/'imbalance_30min_JST_expost.csv'):
        t=datetime.fromisoformat(r['timestamp']).isoformat()
        if scope(t) and r['area']=='四国':background[t].update(imbalance_surplus_jpy_per_mwh=float(r['surplus_JPY_kWh'])*1000,imbalance_shortfall_jpy_per_mwh=float(r['shortfall_JPY_kWh'])*1000)
    assert all(len(r)==5 for r in background.values())
    write_csv('background_prices_30min.csv',list(background.values()))

    # Regional LFC scenarios only; no fabricated product fraction or capacity denominator.
    candidates=[]
    for r in regional:
        for kappa in (.5,1,1.5):
            m=r['lfc_mean_mw']; s=kappa*(r['lfc_upper_equivalent_mw']-r['lfc_lower_equivalent_mw'])/4
            up,down=.5*H(m,s),.5*H(-m,s)
            assert math.isclose(up-down,.5*m,abs_tol=1e-9)
            candidates.append(dict(timestamp_jst=r['timestamp_jst'],assumption_set=f'UNAPPROVED_normal_kappa_{kappa:g}_positive_is_up',kappa=kappa,
                                   regional_mean_mw=m,regional_scale_proxy_mw=s,regional_gross_up_proxy_mwh=up,regional_gross_down_proxy_mwh=down,
                                   rho_product_share=None,reference_up_mw=None,reference_down_mw=None,alpha_up=None,alpha_down=None,
                                   input_status='diagnostic_only_missing_pool_direction_mapping_and_capacity'))
    write_csv('lfc_regional_sensitivity_NOT_MODEL_INPUT.csv',candidates)
    write_csv('field_dictionary.csv',DICTIONARY)
    write_csv('quality_issues.csv',ISSUES)
    manifests=[json.loads(p.read_text(encoding='utf-8')) for p in RAW.glob('manifest_*.json')]
    for records in manifests:
        for r in records:
            if r.get('success') and r['path'].replace('\\','/') in SOURCES:
                SOURCES[r['path'].replace('\\','/')].update(r)
    summary=dict(timezone='Asia/Tokyo',currency='JPY',scope='ex_post_only',formal_halfhours=1440,observation_halfhours=48,
                 regional_rows=len(regional),capacity_rows=len(caprows),lfc_candidate_rows=len(candidates),
                 missing_core_frequency_lfc_edc_spot=0,
                 ics_conditions={period:dict(Counter(r['ics_condition'] for r in regional if r['period_role']==period)) for period in ('formal','observation')},
                 capacity={p:{period:dict(rows=len(selected:=[r for r in caprows if r['product']==p and r['period_role']==period]),
                                          valid_source_price=sum(r['source_price_observation_valid'] for r in selected),
                                          valid_tso_price=sum(r['TSO_price_observation_valid'] for r in selected),
                                          zero_source_award=sum(r['award_source_MW']==0 for r in selected)) for period in ('formal','observation')} for p in ('F','S1','S2','T1','R','C','F_OFFLINE')},
                 checks=['unique complete keys','JST explicit','numeric core fields','nonnegative equivalent widths','no extreme frequency means',
                         'spot all 1488 prices agree with JEPX original','six EPRX series all numeric fields agree with original archive members',
                         'offline CSV bytes equal archive member','offline final-total rows only','no-award price candidates null',
                         'gross-up minus gross-down equals signed net','raw source hashes preserved'],
                 runnable_model_input=False,formal_solve_performed=False,asset_values_populated=False)
    for key,r in SOURCES.items():assert hashlib.sha256((ROOT/key).read_bytes()).hexdigest()==r['sha256']
    (OUT/'source_manifest.json').write_text(json.dumps(list(SOURCES.values()),ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
