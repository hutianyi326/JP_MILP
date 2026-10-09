"""Asset-free full-period preprocessing and historical binding, LFC k=1 only."""
from pathlib import Path
import sys,json,argparse
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'project/jp_first_run_inputs_20261004'))
from assemble import bind,read_json,records,save,write_csv,hash_file,validate_assumptions
from src.jp_milp.config import require,digest
from src.jp_milp.activation import normal_bins,lfc_normal_states,composite_states,positive_normal

DATA=ROOT/'data/processed/JP/shikoku_20260101_20260830_proxy_v3'
HERE=Path(__file__).parent

def assumptions():
    a=read_json(ROOT/'project/jp_first_run_inputs_20261004/assumptions.json')
    a.update(version='SHIKOKU_FULL_20260101_0830_K1_V1',formal_end='2026-08-31T00:00:00+09:00')
    a['frequency'].update(kappa=1.,kappa_sensitivity=[],refinement_counts=[])
    a['composite'].update(lfc_kappa=1.,lfc_kappa_sensitivity=[],reference_fit_max_kappa=1.,reference_fit_state_counts=[11],
        normalization_fit_scope='FULL_FORMAL_PERIOD_EX_POST_K1_ONLY',reference_scale_sensitivity=[],theta_sensitivity=[],coupling_sensitivity=[])
    a.update(early_lfc_amplitude_k=1.,proxy_scenario='base',sensitivity_runs_enabled=False,
             historical_clock_policy='HISTORICAL_JP_2026',planning_horizon_policy='DUE_AND_FROZEN_CLOSURE',
             edc_reference_basis='2*MAX_FORMAL_ABSOLUTE_NET_A_PLUS_B_MWH_TIMES_HEADROOM',
             rule_binding_scope='nominal market clocks; no exceptional actual timestamp replay')
    return a

def prepare(a):
    validate_assumptions(a)
    require(a['early_lfc_amplitude_k']==a['composite']['lfc_kappa']==1. and a['proxy_scenario']=='base','Only user-selected LFC k=1 supported')
    require(a['sensitivity_runs_enabled'] is False,'Sensitivity runs are disabled')
    manifest=read_json(DATA/'package_manifest.json')
    for name,expected in manifest['files'].items():require(hash_file(DATA/name)==expected,'Proxy package fingerprint mismatch: '+name)
    stats=records(DATA/'scenarios/base/activation_statistics.csv')
    region={r['timestamp_jst']:r for r in records(DATA/'regional_30min.csv')}
    caps={(r['timestamp_JST'],r['product']):r for r in records(DATA/'capacity_30min.csv')}
    events={r['native_block_id']:r for r in records(DATA/'historical_capacity_events.csv')}
    require(len(stats)==11664 and sum(r['period_role']=='formal' for r in stats)==11616,'Full coverage required')
    c=a['composite'];l_peak=e_peak=0.
    for r in stats:
        require(float(r['early_lfc_k'])==1. and float(r['frequency_proxy_scale_q'])==1.,'Nonbaseline proxy passed as k1')
        if r['period_role']!='formal':continue
        l_peak=max(l_peak,max(abs(x) for w,x,lo,hi in normal_bins(float(r['lfc_mean_mw']),float(r['lfc_equivalent_scale_mw']),c['lfc_state_count'],[0.])))
        e_peak=max(e_peak,2*abs(float(r['edc_A_mwh'])+float(r['edc_B_mwh'])))
    require(l_peak>0 and e_peak>0,'Missing reference envelope')
    ql=l_peak*c['normalization_headroom_factor']*c['reference_scale_multiplier'];qe=e_peak*c['normalization_headroom_factor']*c['reference_scale_multiplier']
    prepared=[];coeff=[];mapping={'HV_SPOT_FCR':{},'HV_SPOT_S1_T1':{}}
    for r in stats:
        key=r['timestamp_jst'];raw=region[key];m=float(r['lfc_mean_mw']);s=float(r['lfc_equivalent_scale_mw'])
        marginal=lfc_normal_states(m,s,1,1,ql,ql,1,1,c['lfc_state_count'])
        up=down=0.
        for field,share in [('edc_A_mwh','t1_share_A_up_down'),('edc_B_mwh','t1_share_B_up_down')]:
            value=float(r[field]);up+=max(value,0)*c[share][0];down+=max(-value,0)*c[share][1]
        center=2*(up-down)/qe;joint=composite_states(marginal,center,c['base_edc_deviations'],c['theta'])
        require(max(abs(x) for w,x in marginal)<=1+1e-10 and abs(center)<=1+1e-10,'Unit response envelope overflow; no clipping')
        prices={}
        for name,product,scenario in [('fcr','F','HV_SPOT_FCR'),('composite','C','HV_SPOT_S1_T1')]:
            cap=caps[key,product];require(cap['source_price_observation_valid']=='True','Unresolved capacity price')
            prices[name]=float(cap['source_price_candidate_JPY_MW_30min'])
            mapping[scenario][key]=events[cap['native_block_id']]
        da=float(raw['da_price_jpy_per_mwh'])
        prepared.append(dict(start=key,period_role=r['period_role'],da_price_jpy_mwh=da,capacity_price=prices,
            frequency_mean_hz=float(r['frequency_mean_hz']),frequency_scale_proxy_hz=float(r['frequency_equivalent_scale_hz']),
            lfc_marginal=marginal,lfc_mean=sum(w*x for w,x in marginal),edc_center=center,composite_states=joint,
            statistical_origin=r['statistical_origin'],proxy_reason=r['proxy_reason'],
            payment=dict(mapping_id='A_COMPOSITE_DA_PROXY_NOT_V1_V2',basis='joint_physical_gross',recognition_up=1.,recognition_down=1.,signed_price_up=da,signed_price_down=-da)))
        coeff.append(dict(timestamp_jst=key,period_role=r['period_role'],statistical_origin=r['statistical_origin'],proxy_reason=r['proxy_reason'],
            early_lfc_k=1.,lfc_scale_kappa=1.,reference_lfc_mw=ql,reference_edc_mw=qe,
            alpha_s1_up=positive_normal(m,s)/ql,alpha_s1_down=positive_normal(-m,s)/ql,
            alpha_t1_up=2*up/qe,alpha_t1_down=2*down/qe,edc_center=center,
            classification='CONDITIONAL_PROXY_NOT_MEASURED_ACTIVATION',fcr_alpha_status='REQUIRES_RUNTIME_CONTROL'))
    meta=dict(assumption_sha256=digest(a),assembly_code_sha256=hash_file(Path(__file__)),
        shared_binding_code_sha256=hash_file(ROOT/'project/jp_first_run_inputs_20261004/assemble.py'),
        references=dict(lfc_reference_proxy_mw=ql,edc_reference_proxy_mw=qe,fit_halfhours=11616,fit_scope='FULL_FORMAL_EX_POST',
                        is_observed_callable_capacity=False,lfc_k=1.),
        source_manifest_sha256=hash_file(DATA/'package_manifest.json'),
        solver_code_sha256=digest({p.name:p.read_text(encoding='utf-8') for p in sorted((ROOT/'src/jp_milp').glob('*.py'))}))
    return prepared,coeff,meta,mapping

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--runtime');parser.add_argument('--scenario',choices=['HV_SPOT_FCR','HV_SPOT_S1_T1'])
    args=parser.parse_args();out=Path(args.output);require(not out.exists(),'Use a new output folder')
    a=assumptions();rows,coeff,meta,events=prepare(a);bundle=None
    if args.runtime:
        require(args.scenario is not None,'Select scenario')
        bundle=bind(rows,meta,a,read_json(args.runtime),args.scenario,historical_events=events[args.scenario])
    out.mkdir(parents=True);save(out/'assumptions.json',a);save(out/'regional_prepared.json',dict(metadata=meta,intervals=rows))
    save(out/'historical_events_by_scenario.json',events);write_csv(out/'activation_coefficients_k1.csv',coeff)
    if bundle:save(out/'model_input.json',bundle)
    status=dict(status='VALIDATED_CONDITIONAL_INPUT' if bundle else 'PREPARED_RUNTIME_BINDING_REQUIRED',formal_halfhours=11616,observation_halfhours=48,
        lfc_k=1.,sensitivity_runs=False,formal_project_solve=False,bound_scenario=args.scenario,
        remaining=['real battery/control parameters','verified station-specific composite menu','no full actual imbalance settlement'],metadata=meta)
    save(out/'readiness.json',status);print(json.dumps(status,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
