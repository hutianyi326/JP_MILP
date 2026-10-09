"""Ex-post matched statistical scenarios; never modify original observations.

Use same slot/day-type, five closest regional-load donors, uniform weights.
This is a parameter-average normal proxy, NOT an empirical distribution fit.
"""
from pathlib import Path
from datetime import datetime
from collections import defaultdict,Counter
import csv,json,hashlib,math,shutil

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/processed/JP/shikoku_20260101_20260830_rules_v2'
OUT=ROOT/'data/processed/JP/shikoku_20260101_20260830_proxy_v3'
LOAD=ROOT/'countries/JP/research/analysis/fundamentals_30min_DIAGNOSTIC.csv'
KEYS=('frequency_mean_hz','frequency_equivalent_scale_hz','lfc_mean_mw','lfc_equivalent_scale_mw')

def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def write(p,rows):
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def select(target,pool,exclude_day=None):
    eligible=[r for r in pool[target['slot'],target['day_type']] if r['timestamp_jst'][:10]!=exclude_day]
    assert len(eligible)>=5,'Do not silently relax slot/day-type requirements'
    return sorted(eligible,key=lambda r:(abs(r['load_mw']-target['load_mw']),r['timestamp_jst']))[:5]

def average(donors):return {k:sum(r[k] for r in donors)/len(donors) for k in KEYS}

def main():
    assert not OUT.exists(),'Preserve prior versions'
    manifest=json.loads((BASE/'package_manifest.json').read_text())
    for n,h in manifest['files'].items():assert sha(BASE/n)==h
    regional=read(BASE/'regional_30min.csv');templates=read(BASE/'activation_input_template.csv')
    loads={}
    for r in read(LOAD):
        if r['area']!='四国':continue
        t=datetime.fromisoformat(r['timestamp']).isoformat()
        if not '2026-01-01'<=t<'2026-09-01':continue
        assert t not in loads
        value=float(r['エリア需要']);assert math.isfinite(value) and value>0
        loads[t]=dict(load_mw=value,day_type=r['day_type'],slot=int(r['slot']),load_scope=r['scope_status'])
    assert set(loads)=={r['timestamp_jst'] for r in regional}
    pool=defaultdict(list);observed={}
    for r in regional:
        t=r['timestamp_jst']
        if r['activation_statistics_usable']!='True':continue
        assert r['period_role']=='formal','Observation day must never calibrate the donor pool'
        v=dict(timestamp_jst=t,**loads[t],frequency_mean_hz=float(r['frequency_mean_hz']),
               frequency_equivalent_scale_hz=(float(r['frequency_upper_equivalent_hz'])-float(r['frequency_lower_equivalent_hz']))/4,
               lfc_mean_mw=float(r['lfc_mean_mw']),
               lfc_equivalent_scale_mw=(float(r['lfc_upper_equivalent_mw'])-float(r['lfc_lower_equivalent_mw']))/4)
        assert all(math.isfinite(v[k]) for k in KEYS) and v[KEYS[1]]>=0 and v[KEYS[3]]>=0
        observed[t]=v;pool[v['slot'],v['day_type']].append(v)
    assert len(observed)==5926
    filled=[];provenance=[];counts=Counter();outside=0
    for raw,template in zip(regional,templates):
        t=raw['timestamp_jst'];assert template['timestamp_jst']==t
        target=dict(timestamp_jst=t,**loads[t]);new=dict(template)
        if t in observed:
            values={k:observed[t][k] for k in KEYS};origin='OBSERVED_STATISTICS';reason='NOT_FILLED';donors=[];weight=None;nearest=None;maxgap=None;extrapolated=False
        else:
            donors=select(target,pool);values=average(donors);weight=1/len(donors)
            origin='EX_POST_MATCHED_PROXY';reason='EARLY_MISSING' if t<'2026-04-28T13:00:00+09:00' else 'QUARANTINED_DAY_REPLACEMENT'
            candidates=pool[target['slot'],target['day_type']]
            extrapolated=not min(r['load_mw'] for r in candidates)<=target['load_mw']<=max(r['load_mw'] for r in candidates)
            gaps=[abs(r['load_mw']-target['load_mw']) for r in donors];nearest=min(gaps);maxgap=max(gaps);outside+=extrapolated
            for d in donors:
                provenance.append(dict(target_timestamp_jst=t,target_period_role=raw['period_role'],reason=reason,
                    target_slot=target['slot'],target_day_type=target['day_type'],target_load_mw=target['load_mw'],
                    donor_timestamp_jst=d['timestamp_jst'],donor_day_type=d['day_type'],donor_slot=d['slot'],donor_load_mw=d['load_mw'],
                    weight=weight,load_gap_mw=abs(d['load_mw']-target['load_mw']),donor_later_than_target=d['timestamp_jst']>t,
                    target_outside_donor_load_range=extrapolated,**{k:d[k] for k in KEYS}))
        new.update(values);new.update(original_activation_statistics_usable=template['activation_statistics_usable'],
            activation_statistics_usable=template['activation_statistics_usable'],model_statistics_complete=True,
            statistical_origin=origin,proxy_reason=reason,donor_count=len(donors),
            target_load_mw=target['load_mw'],target_day_type=target['day_type'],nearest_load_gap_mw=nearest,max_selected_load_gap_mw=maxgap,
            outside_donor_load_range=extrapolated,parameter_aggregation='UNIFORM_PARAMETER_MEAN_NOT_MIXTURE_VARIANCE' if donors else 'SOURCE_WIDTH_DIVIDED_BY_4',
            input_status='COMPLETE_CONDITIONAL_STATISTICS_NOT_RUNNABLE_MODEL',information_scope='EX_POST_ONLY_NOT_DECISION_TIME_DATA')
        assert all(math.isfinite(new[k]) for k in KEYS)
        filled.append(new);counts[raw['period_role']+'/'+reason]+=1
    # Out-of-sample diagnostic within the observed season: remove the whole
    # target day from eligible donors; it does NOT validate winter/regime transfer.
    held=[]
    for t,target in observed.items():
        estimate=average(select(target,pool,exclude_day=t[:10]))
        held.append(dict(timestamp_jst=t,**{k+'_error':estimate[k]-target[k] for k in KEYS}))
    diagnostics={k:dict(mae=sum(abs(r[k+'_error']) for r in held)/len(held),rmse=math.sqrt(sum(r[k+'_error']**2 for r in held)/len(held))) for k in KEYS}
    assumptions=dict(version='SHIKOKU_MATCHED_PROXY_V1_20261005',classification='EX_POST_CONDITIONAL_NOT_OBSERVED_ACTIVATION',
        matching=dict(exact=['half_hour_slot','day_type'],distance='absolute_area_load_MW',neighbors=5,weights='uniform',tie_break='donor_timestamp_ascending',
                      day_types=['Workday','Weekend','National-holiday'],load_role='matching_covariate_only_not_settlement_or_reference_pool',
                      load_scope='diagnostic_only_islands_unresolved; accepted matching-only assumption'),
        donors=dict(count=len(observed),start=min(observed),end=max(observed),observation_excluded=True,missing_and_quarantined_excluded=True),
        formulas=dict(mean='sum(weight_i * donor_mean_i)',scale='sum(weight_i * donor_equivalent_scale_i)',
                      early_lfc_sensitivity='mu_pre=k*mu_proxy; s_pre=k*s_proxy; only EARLY_MISSING rows',
                      frequency_sensitivity='scale_proxy=q*scale_proxy; mean unchanged; only imputed rows'),
        early_lfc_k=[1.,1.25,1.5],frequency_proxy_scale_q=[.75,1.,1.25],
        sensitivities_are='illustrative stress choices, not official settings, confidence intervals or calibrated corrections',
        fixes_normalization='Any downstream reference capacity must be identical across amplitude scenarios; do not refit and cancel k',
        not_changed=['EDC A/B','ICS gaps','historical gates and raw prices','raw frequency/LFC statistics','asset/control settings','FCR zero activation cash'],
        limitations=['Winter not represented in donor season','Regional-to-wide-LFC regime transfer uncalibrated','Load matching diagnostic scope only',
        'Uses later observations for early dates; not an executable historical forecast','Averages parameters, does not preserve multimodal mixtures or serial dependence',
        'k>=1 is a stress assumption, not proof every earlier slot required more activation','Composite centering theta=0 may remove mu effects; recompute joint states and SOC, not cash scaling'])
    OUT.mkdir(parents=True)
    # Preserve raw evidence and existing rule bindings byte-for-byte, under
    # original filenames. New scenario inputs have distinct names.
    for p in BASE.rglob('*'):
        if p.is_file() and p.name not in ('package_manifest.json','readiness.json'):
            dest=OUT/p.relative_to(BASE);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    write(OUT/'activation_statistics_base_proxy.csv',filled);write(OUT/'proxy_donor_mapping.csv',provenance)
    save(OUT/'proxy_assumptions.json',assumptions)
    variants=[]
    for name,k,q in [('base',1.,1.),('early_lfc_k1_25',1.25,1.),('early_lfc_k1_5',1.5,1.),('frequency_scale_0_75',1.,.75),('frequency_scale_1_25',1.,1.25)]:
        rows=[]
        for r in filled:
            v=dict(r)
            if r['proxy_reason']=='EARLY_MISSING':
                v['lfc_mean_mw']*=k;v['lfc_equivalent_scale_mw']*=k
            if r['statistical_origin']=='EX_POST_MATCHED_PROXY':v['frequency_equivalent_scale_hz']*=q
            v.update(proxy_scenario=name,early_lfc_k=k,frequency_proxy_scale_q=q);rows.append(v)
        dest=OUT/'scenarios'/name;dest.mkdir(parents=True)
        write(dest/'activation_statistics.csv',rows)
        variants.append(dict(name=name,path=f'scenarios/{name}/activation_statistics.csv',early_lfc_k=k,frequency_proxy_scale_q=q))
    monthly=[]
    for month in sorted({r['timestamp_jst'][:7] for r in filled}):
        rows=[r for r in filled if r['timestamp_jst'].startswith(month) and r['period_role']=='formal']
        monthly.append(dict(month=month,formal_halfhours=len(rows),observed=sum(r['statistical_origin']=='OBSERVED_STATISTICS' for r in rows),
                            imputed=sum(r['statistical_origin']=='EX_POST_MATCHED_PROXY' for r in rows),
                            outside_donor_load_range=sum(r['outside_donor_load_range'] for r in rows)))
    write(OUT/'proxy_coverage_monthly.csv',monthly)
    save(OUT/'proxy_validation_diagnostics.json',dict(method='leave_one_day_out_on_observed_slots_only',rows=len(held),metrics=diagnostics,
         validates_winter_or_pre_wide_regime=False,acceptance='diagnostic disclosure, not proof of statistical calibration'))
    save(OUT/'scenario_index.json',variants)
    status=json.loads((BASE/'readiness.json').read_text())
    status.update(status='CONDITIONAL_ACTIVATION_STATISTICS_FILLED_NOT_RUNNABLE_MODEL',model_statistics_complete_halfhours=len(filled),
                  proxy_counts=dict(counts),proxy_target_outside_donor_load_range=outside,
                  original_observed_statistic_counts_unchanged=True,conditional_proxy_inputs='activation_statistics_base_proxy.csv',
                  raw_template_retained='activation_input_template.csv',scenarios=len(variants),proxy_validation_is_calibration=False)
    status['unresolved']=[s for s in status['unresolved'] if not s.startswith(('Missing early frequency','Suspect LFC'))]
    status['unresolved'].append('Observed missing/suspect data remain absent; matched proxies fill only conditional input statistics, not truth')
    status['unresolved'].append('Downstream FCR curve and composite reference/joint-state binding still required; do not use observed-usability flag to discard approved proxies')
    save(OUT/'readiness.json',status)
    save(OUT/'proxy_source_manifest.json',[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in (LOAD,BASE/'package_manifest.json',Path(__file__))])
    save(OUT/'package_manifest.json',dict(files={p.relative_to(OUT).as_posix():sha(p) for p in sorted(OUT.rglob('*')) if p.is_file()}))
    print(json.dumps(dict(counts=dict(counts),extrapolated_targets=outside,validation=diagnostics),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
