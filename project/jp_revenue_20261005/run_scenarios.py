"""Memory-bounded full-period rolling runs; immutable, hash-chained window evidence."""
from pathlib import Path
from copy import deepcopy
from datetime import timedelta
import sys,json,gzip,argparse,csv,math
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from project.jp_shikoku_202601_0830.assemble_full_period import bind,read_json,hash_file
from src.jp_milp.config import timestamp,digest,require
from src.jp_milp.inputs import validate
from src.jp_milp.core import solve_window
from src.jp_milp.scheduling import planning_end
from src.jp_milp.rolling import atomic_json,check_due_orders,code_identity
from project.jp_revenue_20261005.numeric_states import merge_tail_states,recovery_baseline_bounds
from project.jp_ev_offline_20261005.binding import overlay as bind_ev_quotes, apply_blocks as bind_ev_blocks

PACK=ROOT/'data/processed/JP/shikoku_full_run_k1_v5'
RUNTIME=ROOT/'project/jp_shikoku_202601_0830/runtime_100mw_200mwh_v1.json'
END='2026-08-31T00:00:00+09:00'

def prepare(scenario):
    prepared=read_json(PACK/'regional_prepared.json');a=read_json(PACK/'assumptions.json');runtime=read_json(RUNTIME)
    if scenario=='LV_FCR':
        runtime['asset'].update(version='USER_EV_LV_2MW_8MWH_DOD95_ETA92_V1',charge_mw=2.,discharge_mw=2.,nominal_mwh=8.,
            minimum_mwh=.4,maximum_mwh=8.,initial_mwh=4.,target_mwh=4.,import_mw=2.,export_mw=2.,port_domain_min_mw=-2.,port_domain_max_mw=2.)
        runtime['composite_offer']=None
        for key in ('composite_technical_capability','composite_optimization_grid_mw','composite_grid_basis','composite_equal_capacity_basis','composite_menu_interpretation'):
            runtime['user_confirmed_scope'].pop(key,None)
        runtime['user_confirmed_scope'].update(usable_energy_mwh=7.6,lv_operation='USER_CONFIRMED_DAILY_50PCT_SOC_CONSTANT_DAILY_BASELINE_BIDIRECTIONAL_ENERGY_RECOVERY_NO_INTRADAY_ARBITRAGE',
            grid_limit_basis='USER_CONFIRMED_2MW_IMPORT_2MW_EXPORT',power_interpretation='2 MW charge and discharge',energy_interpretation='8 MWh nominal, 7.6 MWh usable',
            lv_purchase_price='SHIKOKU_DA_PROXY_NO_RETAIL_TARIFF_OR_GRID_CHARGES',lv_asset_basis='User confirmed 2MW/8MWh and remaining assumptions inherited')
    event_scenario='HV_SPOT_S1_T1' if scenario=='HV_SPOT_S1_T1' else 'HV_SPOT_FCR'
    events=read_json(PACK/'historical_events_by_scenario.json')[event_scenario]
    if scenario=='LV_FCR':
        prepared,events=bind_ev_quotes(prepared,events)
        runtime['user_confirmed_scope']['lv_capacity_price']='EPRX_OFFLINE_1_1_SOURCE_AVERAGE_ONLY_NO_F_FALLBACK'
    # Scheduling requires only event clocks, delivery keys and service tails. A
    # light FCR skeleton avoids materializing 8784 copies of a 100-row menu.
    skeleton=bind(prepared['intervals'],prepared['metadata'],a,runtime,'HV_SPOT_FCR',historical_events=events)
    if scenario=='LV_FCR':bind_ev_blocks(skeleton,prepared)
    budget=skeleton['annual_budgets_efc'];terminal=skeleton['terminal_value_jpy_mwh']
    if scenario=='HV_SPOT_S1_T1':
        for b in skeleton['capacity_blocks']:
            b['services']=[dict(segments=[dict(hours=max(a['services']['s1_hours'],a['services']['t1_hours']))])]
    return prepared,a,runtime,events,skeleton,budget,terminal

def assemble_window(prepared,a,runtime,events,scenario,start,end,budget,terminal):
    rows=[r for r in prepared['intervals'] if start<=r['start']<end]
    data=bind(rows,prepared['metadata'],a,runtime,'HV_SPOT_FCR' if scenario=='LV_FCR' else scenario,historical_events=events)
    data.update(annual_budgets_efc=budget,terminal_value_jpy_mwh=terminal,compact_equal_menu=scenario=='HV_SPOT_S1_T1')
    data['solver']={**data['solver'],'backend':'highspy'}
    if scenario!='HV_SPOT_S1_T1':
        for r in data['intervals']:
            r['states'],r['numerical_state_compression']=merge_tail_states(r['states'])
    if scenario=='LV_FCR':
        data['scenario']='LV_FCR'
        bind_ev_blocks(data,prepared)
        data['daily_soc_recovery']='CONSTANT_BASELINE_TARGET_50'
        asset=data['asset'];require(asset['auxiliary_ac_mw']==asset['auxiliary_dc_mw']==0 and asset['service_scale']==1 and asset['service_offset_mw']==0,'Daily energy cuts require the confirmed ideal ports')
        days={}
        for r in data['intervals']:days.setdefault(r['start'][:10],[]).append(r)
        bounds={day:recovery_baseline_bounds(rs,asset['discharge_mw'],asset['eta_charge'],asset['eta_discharge']) for day,rs in days.items()}
        for o in data['spot_orders']:
            low,high=bounds[next(iter(o['weights']))[:10]]
            o['buy_limit_mw']=min(o['buy_limit_mw'],-low+1e-9)
            o['sell_limit_mw']=min(o['sell_limit_mw'],high+1e-9)
        data['provenance'].append(dict(valid_daily_energy_bounds=bounds))
        data['provenance'].append(dict(lv_operation=runtime['user_confirmed_scope']['lv_operation'],purchase_price='DA_PRICE_PROXY'))
    validate(data)
    return data

def run(scenario,out,resume=False,limit=None,solver_update=False,backend='highspy',time_limit=None,retry_time_limit=600):
    require(time_limit is None or time_limit>0,'Positive primary time budget required')
    require(retry_time_limit>0,'Positive retry time budget required')
    prepared,a,runtime,events,skeleton,budget,terminal=prepare(scenario)
    identity=dict(scenario=scenario,runtime_sha256=digest(runtime),assumption_sha256=digest(a),source_metadata=prepared['metadata'],
        solver_code_sha256=code_identity(),runner_sha256=hash_file(Path(__file__)),execution_backend=backend,binding_sha256=hash_file(ROOT/'project/jp_first_run_inputs_20261004/assemble.py'))
    if scenario=='LV_FCR':
        identity['numerical_state_helper_sha256']=hash_file(ROOT/'project/jp_revenue_20261005/numeric_states.py')
    initial=dict(next_start=prepared['intervals'][0]['start'],soc=runtime['asset']['initial_mwh'],used={},frozen=runtime['initial_frozen'].copy())
    state=deepcopy(initial);records=[];metrics=[];sequence=0
    if resume:
        manifest=read_json(out/'manifest.json')
        if solver_update:
            stable=lambda v:{k:x for k,x in v.items() if k not in ('solver_code_sha256','runner_sha256','execution_backend')}
            require(stable(manifest['identity'])==stable(identity),'Solver update cannot change runtime/data/binding assumptions')
            update=out/('solver_update_'+identity['solver_code_sha256'][:12]+'.json')
            if not update.exists():atomic_json(update,dict(previous=manifest['identity'],current=identity,scope='Equivalent numerical backend continuation; existing transactions immutable'),immutable=True)
        else:require(manifest['identity']==identity,'Resume identity changed')
    else:
        out.mkdir(parents=True,exist_ok=False);(out/'windows').mkdir()
        manifest=dict(identity=identity,runtime=runtime,assumptions=a,initial_state=initial,annual_budgets_efc=budget,
            formal_end=END,classification='EX_POST_CONDITIONAL_NO_IMBALANCE_SETTLEMENT',
            solver_backend='highspy 1.15.1, one thread per scenario',
            fcr_numerical_tail_merge='Weights below 1e-8 merged into same-direction adjacent states, preserving directional activation means; full service extremes retained',
            input_assembly='Window view of unchanged full-period data; full annual budget and final-day terminal value retained')
        atomic_json(out/'manifest.json',manifest,immutable=True)
    parent=digest(manifest)
    for file in sorted((out/'windows').glob('*.json.gz')):
        with gzip.open(file,'rt',encoding='utf-8') as stream:tx=json.load(stream)
        sha=tx.pop('sha256');require(sha==digest(tx) and tx['parent']==parent and tx['sequence']==sequence,'Invalid transaction chain')
        require(tx['previous_state_digest']==digest(state),'State discontinuity')
        require(not set(state['frozen']).intersection(tx['new_frozen']),'Frozen obligation overwritten')
        state['frozen'].update(tx['new_frozen']);state.update(tx['next_state'])
        require(tx['next_state_digest']==digest(state),'Next state mismatch')
        records+=tx['executed'];metrics.append(tx['window']['metrics']);parent=sha;sequence+=1
    specs={x['id']:x for x in skeleton['spot_orders']+skeleton['capacity_blocks']}
    solved=0;failure=None

    def summary(status):
        cash={k:sum(x[k] for x in records) for k in ('spot_jpy','capacity_jpy','activation_jpy','total_jpy')}
        return dict(status=status,scenario=scenario,classification='EX_POST_CONDITIONAL_NOT_EXECUTABLE_STRATEGY_RETURN',
            formal_end=END,executed_intervals=len(records),windows=sequence,cash=cash if status=='COMPLETE' else None,executed_cash=cash,
            end_soc_mwh=state['soc'],used_efc=state['used'],failure=failure,solver_seconds=sum(x['seconds'] for x in metrics),
            max_gap=max((x['gap'] or 0 for x in metrics),default=0),
            time_limited_windows=sum(any(z['status']==1 for z in x.get('cross_solver_attempts',[x])) for x in metrics),
            max_variables=max((x['variables'] for x in metrics),default=0),max_integers=max((x['integers'] for x in metrics),default=0),
            imbalance_settlement='EXCLUDED_BY_USER',lfc_k=1.,formal_terminal_target_mwh=runtime['asset']['target_mwh'])

    while timestamp(state['next_start'])<timestamp(END) and (limit is None or solved<limit):
        now=timestamp(state['next_start']);execute_end=now+timedelta(days=1)
        try:
            end=planning_end(skeleton,now,execute_end,state['frozen'])
            data=assemble_window(prepared,a,runtime,events,scenario,now.isoformat(),end.isoformat(),budget,terminal)
            data['solver']['backend']=backend
            if time_limit is not None:data['solver']['time_limit_seconds']=time_limit
            if scenario=='LV_FCR' and now.date().isoformat()=='2026-08-06':
                data['solver']['time_limit_seconds']=600
                data['solver']['mip_rel_gap']=1e-4
            if scenario=='HV_SPOT_S1_T1':
                # Numerical stopping tolerance only: 0.1%, with actual bounds
                # reported per window; all physical/integer constraints remain.
                data['solver']['mip_rel_gap']=1e-3
            ids={x['id'] for x in data['spot_orders']+data['capacity_blocks']}
            frozen={k:v for k,v in state['frozen'].items() if k in ids}
            seed_frozen=frozen.copy()
            for b in data['capacity_blocks']:
                if b['id'] not in seed_frozen:
                    seed_frozen[b['id']]=dict(f=0.,s=0.,t=0.,common=0.,candidate_id=None)
            seed=solve_window(data,now.isoformat(),end.isoformat(),state['soc'],seed_frozen,state['used'],END)
            if scenario=='LV_FCR' and any(b['id'] not in frozen and timestamp(b['gate'])>=now for b in data['capacity_blocks']):
                # Relax only the capacity grid to find a good heuristic, then
                # round DOWN and repair with the real grid before using a start.
                relaxed={**data,'relax_capacity_grid_for_seed':True}
                candidate=solve_window(relaxed,now.isoformat(),end.isoformat(),state['soc'],frozen,state['used'],END,incumbent=seed)
                repaired_frozen=frozen.copy()
                for b in data['capacity_blocks']:
                    if b['id'] not in repaired_frozen:
                        q=candidate['orders'][b['id']]['common'];grid=b['grid_mw']
                        q=grid*math.floor(q/grid+1e-7)
                        if q<b['minimum_mw']-1e-9:q=0.
                        repaired_frozen[b['id']]=dict(f=q,s=0.,t=0.,common=q,candidate_id=None)
                try:
                    repaired=solve_window(data,now.isoformat(),end.isoformat(),state['soc'],repaired_frozen,state['used'],END)
                    if repaired['metrics']['objective_jpy']>seed['metrics']['objective_jpy']:seed=repaired
                except ValueError:pass  # Retain the already audited feasible start.
            window=solve_window(data,now.isoformat(),end.isoformat(),state['soc'],frozen,state['used'],END,incumbent=seed)
            if window['metrics']['gap'] is None or window['metrics']['gap']>.005:
                alternate=deepcopy(data)
                alternate['solver'].update(backend='highspy' if backend=='scip' else 'scip',time_limit_seconds=retry_time_limit)
                retry=solve_window(alternate,now.isoformat(),end.isoformat(),state['soc'],frozen,state['used'],END,incumbent=window)
                candidates=[window,retry]
                chosen=max(candidates,key=lambda x:x['metrics']['objective_jpy'])
                # Both audited solves have exactly the same mathematical model.
                # The smaller upper bound and larger incumbent are valid together.
                upper=min(x['metrics']['bound_jpy'] for x in candidates if x['metrics']['bound_jpy'] is not None)
                primal=chosen['metrics']['objective_jpy']
                require(all(math.isfinite(x['metrics']['objective_jpy']) and x['metrics']['bound_jpy'] is not None and math.isfinite(x['metrics']['bound_jpy']) for x in candidates),'Cross-solver nonfinite objective or bound')
                require(upper>=primal-(1.+1e-8*max(abs(upper),abs(primal))),'Cross-solver contradictory upper bound and incumbent')
                chosen['metrics']['cross_solver_attempts']=[deepcopy(x['metrics']) for x in candidates]
                chosen['metrics']['seconds']=sum(x['metrics']['seconds'] for x in candidates)
                chosen['metrics']['bound_jpy']=upper
                chosen['metrics']['gap']=max(0.,upper-chosen['metrics']['objective_jpy'])/max(abs(chosen['metrics']['objective_jpy']),1e-10)
                window=chosen
            if window['metrics']['gap'] is None or window['metrics']['gap']>.005:
                diagnostic=dict(start=now.isoformat(),input_sha256=digest(data),previous_state_digest=digest(state),solver_configuration=data['solver'],window=window,execution_identity=identity)
                (out/'diagnostics').mkdir(exist_ok=True)
                atomic_json(out/'diagnostics'/f'{sequence:05d}_{digest(diagnostic)[:12]}.json',diagnostic,immutable=True)
                raise ValueError('Optimality quality gate: window gap exceeds 0.5%; do not freeze or execute')
            window['metrics']['seed_seconds']=seed['metrics']['seconds']
            check_due_orders(specs,now,execute_end,window['orders'],state['frozen'])
            executed=[x for x in window['intervals'] if timestamp(x['start'])<execute_end]
            require(len(executed)==48,'Execution day incomplete')
            added={k:v for k,v in window['orders'].items() if timestamp(specs[k]['gate'])<execute_end and k not in state['frozen']}
            used=state['used'].copy()
            for x in executed:
                year=x['start'][:4];used[year]=used.get(year,0.)+x['efc']
            small=dict(next_start=execute_end.isoformat(),soc=executed[-1]['soc_end_mwh'],used=used)
            next_state=dict(**small,frozen={**state['frozen'],**added})
            tx=dict(sequence=sequence,parent=parent,previous_state_digest=digest(state),next_state_digest=digest(next_state),
                next_state=small,new_frozen=added,executed=executed,window=window,input_sha256=digest(data),execution_identity=identity,solver_configuration=data['solver'])
            sha=digest(tx);tx['sha256']=sha
            path=out/'windows'/f'{sequence:05d}.json.gz'
            with path.open('xb') as raw:
                with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as stream:
                    stream.write(json.dumps(tx,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8'))
            state=next_state;records+=executed;metrics.append(window['metrics']);sequence+=1;solved+=1;parent=sha
            atomic_json(out/'checkpoint.json',state);atomic_json(out/'summary.json',summary('RUNNING'))
            print(scenario,now.date(),sequence,'PASS',round(window['metrics']['seconds'],2),'seconds',flush=True)
        except (ValueError,KeyError,TypeError) as error:
            failure=str(error);print(scenario,'BLOCKED',state['next_start'],failure,flush=True);break
    status='BLOCKED' if failure else ('COMPLETE' if state['next_start']==END else 'PARTIAL')
    result=summary(status);atomic_json(out/'summary.json',result)
    with (out/'executed_30min.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(records[0]) if records else ['start']);writer.writeheader();writer.writerows(records)
    monthly={}
    for x in records:
        m=monthly.setdefault(x['start'][:7],dict(intervals=0,spot_jpy=0.,capacity_jpy=0.,activation_jpy=0.,total_jpy=0.,efc=0.))
        m['intervals']+=1
        for k in ('spot_jpy','capacity_jpy','activation_jpy','total_jpy','efc'):m[k]+=x[k]
    atomic_json(out/'monthly_cash.json',monthly);atomic_json(out/'solver_metrics.json',metrics)
    print(json.dumps(result,ensure_ascii=False),flush=True)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scenario',required=True,choices=['LV_FCR','HV_SPOT_FCR','HV_SPOT_S1_T1'])
    parser.add_argument('--output',required=True);parser.add_argument('--resume',action='store_true');parser.add_argument('--max-windows',type=int)
    parser.add_argument('--solver-update',action='store_true')
    parser.add_argument('--backend',choices=['highspy','scip'],default='highspy')
    parser.add_argument('--time-limit',type=float)
    parser.add_argument('--retry-time-limit',type=float,default=600)
    args=parser.parse_args();run(args.scenario,Path(args.output),args.resume,args.max_windows,args.solver_update,args.backend,args.time_limit,args.retry_time_limit)
