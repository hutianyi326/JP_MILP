"""Synthetic assets only: full-grid preflight and real-data boundary integrations."""
from pathlib import Path
from copy import deepcopy
import sys,json
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(Path(__file__).parent))
from assemble_full_period import bind,read_json,save
from src.jp_milp.inputs import validate
from src.jp_milp.rolling import run
from project.jp_first_run_inputs_20261004.test_assembly import synthetic_runtime

PACK=ROOT/'data/processed/JP/shikoku_full_run_k1_v5'

def main():
    prepared=read_json(PACK/'regional_prepared.json');a=read_json(PACK/'assumptions.json');events=read_json(PACK/'historical_events_by_scenario.json')
    report=dict(classification='SYNTHETIC_DEVICE_REAL_REGIONAL_DATA_NOT_PROJECT_REVENUE',package=str(PACK.relative_to(ROOT)),metadata=prepared['metadata'],lfc_k=1.,sensitivity_runs=False,preflight={},integrations={})
    for scenario in ('HV_SPOT_FCR','HV_SPOT_S1_T1'):
        profile=synthetic_runtime()
        full=bind(prepared['intervals'],prepared['metadata'],a,profile,scenario,historical_events=events[scenario])
        report['preflight'][scenario]=validate(full)
        assert len(full['intervals'])==11664 and len(full['capacity_blocks'])==8784
        assert abs(full['annual_budgets_efc']['2026']-600*242/365)<1e-10
        del full
        # Real prices/proxy statistics across March14 reform and July1 rule boundary.
        for label,start,end,formal_end in [('weekly_gate','2026-01-06','2026-01-18','2026-01-17T00:00:00+09:00'),
                                         ('march_reform','2026-03-12','2026-03-16','2026-03-15T00:00:00+09:00'),
                                         ('july_version','2026-06-30','2026-07-03','2026-07-02T00:00:00+09:00')]:
            rows=deepcopy([r for r in prepared['intervals'] if start<=r['start'][:10]<end])
            for r in rows:r['period_role']='formal' if r['start']<formal_end else 'observation'
            data=bind(rows,prepared['metadata'],a,profile,scenario,historical_events=events[scenario])
            temp=ROOT/'outputs/JP'/('full_period_validation_'+uuid4().hex)
            temp.mkdir(parents=True)
            weekly=label=='weekly_gate'
            result=run(data,formal_end,temp/'run',max_windows=1 if weekly else None)
            if result['status']!=('PARTIAL' if weekly else 'COMPLETE'):raise AssertionError((scenario,label,result))
            if not weekly:assert abs(result['end_soc_mwh']-profile['asset']['target_mwh'])<1e-7
            if scenario=='HV_SPOT_FCR':assert result['cash']['activation_jpy']==0.
            tx=[read_json(p) for p in sorted((temp/'run/windows').glob('*.json'))]
            assert all(x['window']['audit']['status']=='PASS' for x in tx)
            if weekly:
                due=[b for b in data['capacity_blocks'] if b['gate']=='2026-01-06T14:00:00+09:00']
                assert len(due)==56 and all(b['id'] in tx[0]['next_state']['frozen'] for b in due)
                assert tx[0]['window']['end']=='2026-01-17T00:00:00+09:00'
            report['integrations'][scenario+'/'+label]=dict(status='PASS',scope='ONE_WEEKLY_GATE_WINDOW' if weekly else 'COMPLETE_BOUNDARY_ROLL',output=str(temp.relative_to(ROOT)),executed_intervals=result['executed_intervals'],windows=result['windows'],
                max_variables=result['max_variables'],solver_seconds=result['solver_seconds'],end_soc_mwh=result['end_soc_mwh'],
                solver_gaps=[x['window']['metrics']['gap'] for x in tx],presolve_rechecks=sum(len(x['window']['metrics'].get('attempts',[]))>1 for x in tx),
                nonzero_capacity_orders=sum(isinstance(v,dict) and v['common']>1e-8 for v in tx[-1]['next_state']['frozen'].values()))
            print(scenario,label,'PASS',result['solver_seconds'],flush=True)
        print(scenario,'PASS',flush=True)
    report['status']='PASS';save(Path(__file__).parent/'full_period_validation.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
