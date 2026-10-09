"""Memory-bounded full-period rolling runs; immutable, hash-chained window evidence."""
from pathlib import Path
from copy import deepcopy
from datetime import timedelta
import sys,json,gzip,argparse,csv,math
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from project.jp_shikoku_202601_0830.assemble_full_period import bind,read_json,hash_file
from src.jp_milp.config import timestamp,digest,require
from src.jp_milp.inputs import validate
from project.jp_kyushu_lv_20261006.daily_solver import solve_window
from src.jp_milp.scheduling import planning_end
from src.jp_milp.rolling import atomic_json,check_due_orders,code_identity
from project.jp_revenue_20261005.numeric_states import merge_tail_states,recovery_baseline_bounds
from project.jp_ev_offline_20261005.binding import apply_blocks as bind_ev_blocks

PACK=ROOT/'data/processed/JP/kyushu_lv_20251201_20260831_v1'
RUNTIME=ROOT/'project/jp_kyushu_lv_20261006/runtime_lv_2mw_8mwh.json'
END='2026-09-01T00:00:00+09:00'

def prepare(scenario):
    require(scenario=='LV_FCR','This package is LV offline only')
    manifest=read_json(PACK/'package_manifest.json')
    for name,expected in manifest['files'].items():require(hash_file(PACK/name)==expected,'Kyushu input fingerprint changed: '+name)
    sources=read_json(PACK/'source_manifest.json')
    for e in sources['entries']:require(hash_file(ROOT/e['path'])==e['sha256'],'Kyushu raw changed')
    require(hash_file(ROOT/sources['holiday_file'])==sources['holiday_sha256'],'Holiday source changed')
    prepared=read_json(PACK/'regional_prepared.json');a=read_json(PACK/'assumptions.json');runtime=read_json(RUNTIME)
    require(a['area']=='KYUSHU' and all(r['offline_quote']['area']=='九州' for r in prepared['intervals']),'Wrong area')
    events=read_json(PACK/'historical_events_by_scenario.json')['HV_SPOT_FCR']
    skeleton=bind(prepared['intervals'],prepared['metadata'],a,runtime,'HV_SPOT_FCR',historical_events=events)
    bind_ev_blocks(skeleton,prepared)
    return prepared,a,runtime,events,skeleton,skeleton['annual_budgets_efc'],skeleton['terminal_value_jpy_mwh']

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
        identity['offline_block_binding_sha256']=hash_file(ROOT/'project/jp_ev_offline_20261005/binding.py')
        identity['daily_solver_sha256']=hash_file(ROOT/'project/jp_kyushu_lv_20261006/daily_solver.py')
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
            try:
                window=solve_window(data,now.isoformat(),end.isoformat(),state['soc'],frozen,state['used'],END,incumbent=seed)
            except ValueError:
                alternate=deepcopy(data);alternate['solver'].update(backend='scip' if backend=='highspy' else 'highspy',time_limit_seconds=retry_time_limit)
                window=solve_window(alternate,now.isoformat(),end.isoformat(),state['soc'],frozen,state['used'],END,incumbent=seed)
                window['metrics']['primary_infeasible_cross_backend_retry']=True

            if window['metrics']['gap'] is None or window['metrics']['gap']>.005 or (window['metrics'].get('continuous_polish') or {}).get('status')==2:
                alternate=deepcopy(data)
                alternate['solver'].update(backend='highspy' if window['metrics']['backend']=='scip' else 'scip',time_limit_seconds=retry_time_limit)
                retry=solve_window(alternate,now.isoformat(),end.isoformat(),state['soc'],frozen,state['used'],END,incumbent=window)
                candidates=[window,retry]
                certified=[x for x in candidates if (x['metrics'].get('continuous_polish') or {}).get('status')!=2]
                require(bool(certified),'Both backends failed fixed-integer LP certificate; do not freeze')
                chosen=max(certified,key=lambda x:x['metrics']['objective_jpy'])
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
            require((window['metrics'].get('continuous_polish') or {}).get('status')!=2,'Failed fixed-integer LP certificate; do not freeze')
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
