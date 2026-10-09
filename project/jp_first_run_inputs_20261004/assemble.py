"""Prepare regional scenarios and assemble asset-bound inputs without station defaults.

The statistical envelope is an explicit alternative research hypothesis. It is
NOT an estimate of an observed market resource pool or proven product alpha.
Original evidence remains unchanged. FCR-only cash excludes V1/V2 settlement.
"""
from pathlib import Path
import argparse
import csv
import json
import hashlib
from copy import deepcopy
from datetime import datetime, timedelta
import math
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from src.jp_milp.config import Asset, InputError, require, number, digest
from src.jp_milp.activation import normal_bins, fcr_states, lfc_normal_states, composite_states, positive_normal
from src.jp_milp.inputs import validate
from src.jp_milp.budget import common_coverage_budget

HERE=Path(__file__).parent
DATA=ROOT/'data/processed/JP/shikoku_202606_20260701_expost'

def read_json(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,obj):
    Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def records(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))
def write_csv(p,rows):
    with Path(p).open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
def hash_file(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def validate_assumptions(a):
    require(a['scope']=='EX_POST_CONDITIONAL','Ex-post conditional only')
    require(a['market']['spot_scope']=='DA_ONLY','Only explicit DA-only assembly supported')
    require(a['market']['capacity_price_side'] in ('source','TSO'),'Unknown price side')
    require(a['market']['activation_payment']=='DA_PRICE_SYMMETRIC_ECONOMIC_PROXY_NOT_V1_V2','Unsupported payment scenario')
    require(a['market']['fcr_activation_payment']=='NOT_APPLICABLE_FCR_ONLY_NO_SURPLUS_CONTRACT', 'Unsupported FCR settlement scope')
    require(a['market']['fcr_imbalance_settlement']=='EXCLUDED_UNRESOLVED_NOT_FULL_NET_REVENUE', 'Imbalance settlement requires a separate verified mapping')
    for k in ('capacity_price_multiplier','activation_price_multiplier','annual_efc'):
        require(number(a['market'][k],k)>=0,'Negative factor')
    for key in ('recognition_up','recognition_down'):
        require(0<=number(a['market'][key],key)<=1,'Invalid payment recognition')
    c=a['composite']
    require(c['normalization']=='STATISTICAL_ENVELOPE_REFERENCE_NOT_OBSERVED_CALLABLE_CAPACITY','Use explicit envelope scheme; other pools need new mapping')
    require(c['lfc_positive_is_up'] and c['edc_positive_is_up'],'Alternative sign mapping not implemented')
    require(c['lfc_pool_share_up']==c['lfc_pool_share_down']==1,'Whole-published-LFC surrogate only')
    require(c['edc_channels']==['A','B'] and not c['edc_O_included'],'Non-overlapping A/B net proxy only; O excluded')
    require(c['edc_hidden_counterflow_mwh']==0,'Hidden counterflow not supported in this first-round net-center adapter')
    for key in ('t1_share_A_up_down','t1_share_B_up_down'):
        require(len(c[key])==2 and all(0<=number(v,key)<=1 for v in c[key]),'Invalid directional share')
    for key in ('normalization_headroom_factor','reference_scale_multiplier','reference_fit_max_kappa'):
        require(number(c[key],key)>0,'Positive normalization values required')
    require(c['reference_fit_max_kappa']>=c['lfc_kappa']>=0,'Kappa outside reference fit scope')
    require(c['lfc_state_count'] in c['reference_fit_state_counts'],'State count not covered by reference fit')
    require(not a['ics_conditioning'],'No missing ICS imputation implemented')
    require(a['frequency']['kappa']>=0,'Negative frequency scale')
    require(c['theta'] in (0,1),'Theta must be a fixed declared scenario')
    for name in ('base_edc_deviations','stress_edc_deviations'):
        v=c[name];require(all(w>0 and math.isfinite(x) for w,x in v) and abs(sum(w for w,x in v)-1)<1e-10 and abs(sum(w*x for w,x in v))<1e-10,'Invalid deviations')
    require(any(abs(x)>0 for w,x in c['stress_edc_deviations']),'Nonzero stress required')

def edc_allocated(r,c):
    up=down=0.
    for field,key in [('edc_own_area_own_mo_A_mwh','t1_share_A_up_down'),('edc_forecast_error_other_B_mwh','t1_share_B_up_down')]:
        v=float(r[field]);u,d=c[key]
        up+=max(v,0)*u;down+=max(-v,0)*d
    return up,down

def prepare(a):
    validate_assumptions(a)
    regional=records(DATA/'regional_30min.csv')
    cap={(r['timestamp_JST'],r['product']):r for r in records(DATA/'capacity_30min.csv')}
    require(len(regional)==1488 and len({r['timestamp_jst'] for r in regional})==1488,'Unexpected sample')
    c=a['composite'];formal=[r for r in regional if r['period_role']=='formal']
    # Fit once on formal-month statistics, excluding the observation day. Use the
    # same references for base and sensitivities; never fit on optimized bids.
    l_peak=0.;e_peak=0.
    for r in formal:
        m=float(r['lfc_mean_mw']);s=c['reference_fit_max_kappa']*(float(r['lfc_upper_equivalent_mw'])-float(r['lfc_lower_equivalent_mw']))/4
        for n in c['reference_fit_state_counts']:
            l_peak=max(l_peak,max(abs(x) for w,x,lo,hi in normal_bins(m,s,n,[0.])))
        # Unallocated component sum prevents product share changes from cancelling
        # through re-fitting the denominator. This is a net, not gross, envelope.
        e_peak=max(e_peak,2*abs(float(r['edc_own_area_own_mo_A_mwh'])+float(r['edc_forecast_error_other_B_mwh'])))
    require(l_peak>0 and e_peak>0,'Zero reference statistics require explicit alternative scenario')
    ql=c['normalization_headroom_factor']*l_peak*c['reference_scale_multiplier']
    qe=c['normalization_headroom_factor']*e_peak*c['reference_scale_multiplier']
    prepared=[];coeff=[]
    for r in regional:
        key=r['timestamp_jst'];m=float(r['lfc_mean_mw']);s=c['lfc_kappa']*(float(r['lfc_upper_equivalent_mw'])-float(r['lfc_lower_equivalent_mw']))/4
        lfc=lfc_normal_states(m,s,1,1,ql,ql,1,1,c['lfc_state_count'])
        eup,edown=edc_allocated(r,c);center=2*(eup-edown)/qe
        joint=composite_states(lfc,center,c['base_edc_deviations'],c['theta'])
        require(max(abs(x) for w,x in lfc)<=1+1e-9,'LFC outside declared unit capability; no clipping')
        require(abs(center)+max(abs(x) for w,x in c['stress_edc_deviations'])<=1+1e-9,'EDC outside capability; change explicit assumptions, no clipping')
        prices={}
        for label,product in [('fcr',a['market']['fcr_capacity_product']),('composite',a['market']['composite_capacity_product'])]:
            cr=cap[key,product];side=a['market']['capacity_price_side']
            require(cr[f'{side}_price_observation_valid']=='True','No valid capacity price; no silent zero fill')
            prices[label]=float(cr[f'{side}_price_candidate_JPY_MW_30min'])*a['market']['capacity_price_multiplier']
        da=float(r['da_price_jpy_per_mwh']);scale=a['market']['activation_price_multiplier']
        prepared.append(dict(start=key,period_role=r['period_role'],da_price_jpy_mwh=da,capacity_price=prices,
                             frequency_mean_hz=float(r['frequency_mean_hz']),frequency_scale_proxy_hz=a['frequency']['kappa']*(float(r['frequency_upper_equivalent_hz'])-float(r['frequency_lower_equivalent_hz']))/4,
                             lfc_marginal=lfc,lfc_mean=sum(w*x for w,x in lfc),edc_center=center,composite_states=joint,
                             payment=dict(mapping_id='A_PAYMENT_DA_SYMMETRIC_NOT_V1_V2',basis='joint_physical_gross',recognition_up=a['market']['recognition_up'],recognition_down=a['market']['recognition_down'],signed_price_up=scale*da,signed_price_down=-scale*da)))
        coeff.append(dict(timestamp_jst=key,period_role=r['period_role'],classification='CONDITIONAL_STATISTICAL_PROXY_NOT_MEASURED_ACTIVATION',
                          lfc_reference_proxy_mw=ql,edc_reference_proxy_mw=qe,lfc_up_proxy_mwh=.5*positive_normal(m,s),lfc_down_proxy_mwh=.5*positive_normal(-m,s),
                          s1_alpha_up_proxy=positive_normal(m,s)/ql,s1_alpha_down_proxy=positive_normal(-m,s)/ql,
                          t1_allocated_up_proxy_mwh=eup,t1_allocated_down_proxy_mwh=edown,
                          t1_alpha_up_proxy=2*eup/qe,t1_alpha_down_proxy=2*edown/qe,
                          edc_center=center,lfc_centered_mean=sum(v['weight']*v['s'] for v in joint),
                          joint_state_count=len(joint)))
    metadata=dict(assumption_version=a['version'],assumption_sha256=digest(a),assembly_code_sha256=hash_file(__file__),
                  solver_code_sha256=digest({p.name:p.read_text(encoding='utf-8') for p in sorted((ROOT/'src/jp_milp').glob('*.py'))}),
                  references=dict(lfc_statistical_peak_mw=l_peak,edc_net_statistical_peak_mw=e_peak,
                  lfc_reference_proxy_mw=ql,edc_reference_proxy_mw=qe,fit_halfhours=len(formal),fit_scope='formal_month_expost_only',
                  is_observed_callable_capacity=False,is_product_identification=False),
                  source_sha256={p.name:hash_file(p) for p in [DATA/'regional_30min.csv',DATA/'capacity_30min.csv']})
    return prepared,coeff,metadata

def services(products,a):
    extremes=[];paths=[];req={}
    for p,hours in products.items():
        req[p]=dict(up_coefficient=1.,down_coefficient=1.,up_hours=hours,down_hours=hours,evidence_id='A_SYMMETRIC_ENGINEERING_SERVICE_'+a['version'])
        for sign in (1.,-1.):
            v={k:sign if k==p else 0. for k in ('f','s','t')};extremes.append(v)
            paths.append(dict(initial_bound='lower' if sign>0 else 'upper',segments=[dict(hours=hours,**v)]))
    return extremes,paths,req

def bind(prepared,metadata,a,runtime,scenario,historical_events=None):
    require(metadata['assumption_sha256']==digest(a),'Prepared states and assumptions are from different versions')
    require(scenario in ('HV_SPOT_FCR','HV_SPOT_S1_T1'),'Only two requested HV scenarios')
    require(runtime['profile_classification'] in ('PROJECT_RUNTIME','SYNTHETIC_PIPELINE_TEST'),'Runtime classification missing')
    asset=Asset(**runtime['asset']);asset.validate();comp=scenario=='HV_SPOT_S1_T1'
    if not comp:
        ctrl=runtime['fcr_control']
        require(ctrl['response_model']=='BID_SCALED_NORMALIZED_CURVE','Fixed gamma requires an explicitly bid-scaled curve')
        for k in ('deadband_up_hz','deadband_down_hz'):require(number(ctrl[k],k)>=0,'Negative deadband')
        for k in ('span_up_hz','span_down_hz'):require(number(ctrl[k],k)>0,'Invalid response span')
        require(bool(ctrl['basis']),'Control setting basis required')
    else:
        menu=runtime['composite_offer']
        require(isinstance(menu,dict) and bool(menu.get('candidates')),'Asset-bound full-inner menu required; arbitrary ratios are not generated')
        require(menu['asset_version']==asset.version,'Stale composite menu')
        require(bool(menu['evidence']) and menu['full_inner_scope']=='FULL_CAPABILITY_NOT_MERELY_DELIVERABLE','Missing full-inner capability evidence')
    rows=[];orders=[];blocks=[]
    for r in prepared:
        key=r['start'];t=datetime.fromisoformat(key);prev=t-timedelta(days=1)
        if comp:states=deepcopy(r['composite_states'])
        else:states=fcr_states(r['frequency_mean_hz'],r['frequency_scale_proxy_hz'],ctrl['deadband_up_hz'],ctrl['deadband_down_hz'],ctrl['span_up_hz'],ctrl['span_down_hz'],1,1,a['frequency']['state_count'])
        row=dict(start=key,area=a['area'],asset_version=asset.version,availability=1.,states=states,payment=deepcopy(r['payment']))
        if not comp:
            row['payment']=dict(mapping_id='FCR_ONLY_NO_SURPLUS_CONTRACT_ART43',basis='joint_physical_gross',recognition_up=0.,recognition_down=0.,signed_price_up=None,signed_price_down=None)
        if comp:row['joint_metadata']=dict(theta=a['composite']['theta'],coupling='independent',lfc_mean=r['lfc_mean'],edc_center=r['edc_center'],normalization_id='A_STATISTICAL_ENVELOPE_'+metadata['assumption_sha256'],lfc_marginal=r['lfc_marginal'],edc_deviations=a['composite']['base_edc_deviations'])
        rows.append(row)
        lo,hi=asset.net_bounds
        require(lo<hi,'No valid net AC domain')
        srvlo,srvhi=asset.service_scale*lo+asset.service_offset_mw,asset.service_scale*hi+asset.service_offset_mw
        orders.append(dict(id='DA/'+key,market='DA',weights={key:1.},buy_limit_mw=max(-srvlo,0),sell_limit_mw=max(srvhi,0),price_jpy_mwh=r['da_price_jpy_mwh'],grid_mw=a['market']['spot_grid_mw'],gate=prev.replace(hour=10,minute=0).isoformat(),result=prev.replace(hour=11,minute=0).isoformat()))
        products={'s':a['services']['s1_hours'],'t':a['services']['t1_hours']} if comp else {'f':a['services']['fcr_hours']}
        ex,paths,req=services(products,a)
        b=dict(id='CAP/'+key,asset_version=asset.version,intervals=[key],gate=prev.replace(hour=14,minute=0).isoformat(),result=prev.replace(hour=15,minute=0).isoformat(),
               price_evidence='A_AGGREGATE_SOURCE_PRICE_PROXY_'+a['version'],capability_validation_id='A_FINITE_ENGINEERING_PATHS_'+asset.version,
               price_jpy_mw_30min={key:r['capacity_price']['composite' if comp else 'fcr']},extremes=ex,services=paths,service_requirements=req,
               response_envelope=dict(up=a['composite']['shared_response_envelope'],down=a['composite']['shared_response_envelope'],assumption_id='A_SHARED_ENVELOPE_NOT_TSO_CLIPPING') if comp else None)
        if comp:
            b['bid_rules']=deepcopy(menu['bid_rules']);b['candidates']=deepcopy(menu['candidates'])
            for candidate in b['candidates']:
                require(candidate['asset_version']==asset.version,'Candidate from another asset')
                for condition in candidate['domain']:
                    for term in condition['terms']:
                        require(term['interval']=='*','Template domain must use current-interval placeholder *')
                        term['interval']=key
        else:
            maximum=(srvhi-srvlo)/2
            require(maximum>0,'No symmetric reserve capability')
            b.update(minimum_mw=1.,maximum_mw=maximum,grid_mw=.001,response_scaling_validated=True)
        blocks.append(b)
    formal=[r['start'] for r in prepared if r['period_role']=='formal'];obs=[r['start'] for r in prepared if r['period_role']=='observation']
    budget=common_coverage_budget(formal,obs,a['market']['annual_efc'])
    last=max(formal)[:10];mean=sum(r['da_price_jpy_mwh'] for r in prepared if r['start'].startswith(last))/48
    result=dict(asset=runtime['asset'],solver=a['solver'],scenario=scenario,classification='SYNTHETIC_VALIDATION' if runtime['profile_classification']=='SYNTHETIC_PIPELINE_TEST' else 'EX_POST_CONDITIONAL',currency='JPY',timezone='Asia/Tokyo',area=a['area'],
                assumption_version=a['version'],provenance=[dict(assembly_metadata=metadata,assumptions=a,runtime_sha256=digest(runtime),input_ready_does_not_certify_resource_qualification=True,initial_commitment_convention=a['market']['first_day_commitment'])],
                intervals=rows,spot_orders=orders,capacity_blocks=blocks,initial_frozen=runtime['initial_frozen'],annual_budgets_efc=budget['annual_budgets_efc'],terminal_value_jpy_mwh=max(mean,0)*asset.eta_discharge*asset.service_scale)
    if historical_events is not None:
        merged={}
        for b in blocks:
            key=b['intervals'][0];ev=historical_events[key];ident=ev['native_block_id']
            if ident not in merged:
                b.update(id=ident,gate=ev['gate_nominal_jst'],result=ev['result_deadline_nominal_jst'],clock_evidence=ev['evidence_url'])
                merged[ident]=b
            else:
                first=merged[ident]
                require(first['gate']==ev['gate_nominal_jst'],'Conflicting historical event')
                first['intervals']+=b['intervals'];first['price_jpy_mw_30min'].update(b['price_jpy_mw_30min'])
                if comp:
                    for x,y in zip(first['candidates'],b['candidates']):
                        require({k:v for k,v in x.items() if k!='domain'}=={k:v for k,v in y.items() if k!='domain'},'Candidate changes inside native block')
                        x['domain']+=y['domain']
        result.update(capacity_blocks=list(merged.values()),capacity_clock_policy='HISTORICAL_JP_2026',planning_horizon_policy='DUE_AND_FROZEN_CLOSURE')
    validate(result)
    return result

def sensitivity_catalog(a,baseline_meta):
    """One-factor variants; not optimizer choices. Refit formula remains fixed."""
    out={}
    def add(name,section,key,value):
        v=deepcopy(a);v[section][key]=value;v['version']=a['version']+'/'+name;out[name]=v
    for k in (.5,1.5):add('frequency_kappa_'+str(k),'frequency','kappa',k)
    for n in (21,41):add('frequency_bins_'+str(n),'frequency','state_count',n)
    for k in (.5,1.5):add('lfc_kappa_'+str(k),'composite','lfc_kappa',k)
    for s in (.75,1.25):add('reference_scale_'+str(s),'composite','reference_scale_multiplier',s)
    for multiplier in (.5,1.5):
        name='edc_product_share_'+str(multiplier);v=deepcopy(a);v['version']+='/'+name
        for key in ('t1_share_A_up_down','t1_share_B_up_down'):v['composite'][key]=[x*multiplier for x in a['composite'][key]]
        out[name]=v
    for x in (.8,1.2):
        add('capacity_price_'+str(x),'market','capacity_price_multiplier',x)
        add('activation_price_'+str(x),'market','activation_price_multiplier',x)
    # theta and coupling variants use the existing mandatory sensitivity suite.
    return out

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--assumptions',default=str(HERE/'assumptions.json'))
    parser.add_argument('--output',required=True)
    parser.add_argument('--runtime')
    parser.add_argument('--scenario',choices=['HV_SPOT_FCR','HV_SPOT_S1_T1'])
    args=parser.parse_args()
    try:
        a=read_json(args.assumptions);rows,coeff,meta=prepare(a)
        out=Path(args.output);require(not out.exists(),'Use a new output directory to preserve prior versions')
        bundle=None
        if args.runtime:
            require(args.scenario is not None,'Select a scenario with runtime input')
            bundle=bind(rows,meta,a,read_json(args.runtime),args.scenario)
        out.mkdir(parents=True)
        save(out/'assumptions.json',a);save(out/'regional_prepared.json',dict(metadata=meta,intervals=rows))
        write_csv(out/'activation_proxy_coefficients.csv',coeff)
        write_csv(out/'fcr_regional_inputs.csv',[{k:r[k] for k in ('start','period_role','da_price_jpy_mwh','frequency_mean_hz','frequency_scale_proxy_hz')} | dict(capacity_price_proxy_jpy_mw_30min=r['capacity_price']['fcr'],activation_payment='NOT_APPLICABLE_FCR_ONLY_NO_SURPLUS_CONTRACT',signed_activation_up_proxy_jpy_mwh=None,signed_activation_down_proxy_jpy_mwh=None) for r in rows])
        save(out/'edc_sensitivity.json',{r['start']:a['composite']['stress_edc_deviations'] for r in rows})
        (out/'sensitivity_assumptions').mkdir()
        variants=sensitivity_catalog(a,meta)
        for name,values in variants.items():save(out/'sensitivity_assumptions'/f'{name}.json',values)
        save(out/'sensitivity_plan.json',dict(base='assumptions.json',one_factor_variants=list(variants),
                 composite_mandatory_suite=['base','mean_added','edc_independent','edc_same','edc_opposite'],
                 comparison='reoptimized_and_fixed_base_commitments_are_separate',
                 binning_acceptance='income_and_DC_throughput_relative_difference_at_most_1pct_unless_near_zero_then_explicit_absolute_tolerance',
                 no_sensitivity_solve_performed=True))
        status=dict(status='REGIONAL_PREPARED_RUNTIME_BINDING_REQUIRED' if bundle is None else 'READY_FOR_CONDITIONAL_SOLVE',formal_halfhours=1440,observation_halfhours=48,
                    real_station_values_supplied=bundle is not None and bundle['classification']=='EX_POST_CONDITIONAL',formal_solve_performed=False,
                    fcr_pending=['runtime_asset','runtime_control_curve'],composite_pending=['runtime_asset','asset_bound_full_inner_menu_and_domains'],
                    activation_is_empirically_calibrated=False,metadata=meta)
        if bundle is not None:
            save(out/'model_input.json',bundle);status['preflight']=validate(bundle);status['classification']=bundle['classification']
            status['selected_scenario']=args.scenario;status['selected_scenario_pending']=[]
        save(out/'readiness.json',status)
        print(json.dumps(status,ensure_ascii=False,indent=2))
        return 0
    except (ValueError,KeyError,TypeError,OSError) as e:
        print(json.dumps(dict(status='NOT_READY',reason=str(e)),ensure_ascii=False));return 2

if __name__=='__main__':raise SystemExit(main())
