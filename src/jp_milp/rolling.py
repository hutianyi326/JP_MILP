"""Daily execution with default two-day or obligation-aware planning horizon."""
from datetime import timedelta
from pathlib import Path
from collections import defaultdict
import csv
import json
import os
import uuid
from .config import timestamp, digest, require
from .inputs import validate
from .core import solve_window
from .scheduling import planning_end


def atomic_json(path, payload, immutable=False):
    path=Path(path); temp=path.with_name('.'+path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temp.open('x', encoding='utf-8') as stream:
            json.dump(payload, stream, ensure_ascii=False, allow_nan=False, indent=2)
            stream.flush(); os.fsync(stream.fileno())
        if immutable:
            os.link(temp, path); temp.unlink()
        else:
            os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def code_identity():
    return digest({p.name: p.read_text(encoding='utf-8') for p in sorted(Path(__file__).parent.glob('*.py'))})


def check_due_orders(specs, start, execute_end, solved_orders, frozen):
    """Check the full event universe, not only delivery-selected solver columns."""
    missing=[key for key, spec in specs.items()
             if start <= timestamp(spec['gate']) < execute_end
             and key not in solved_orders and key not in frozen]
    require(not missing, 'Due orders omitted from planning window: '+', '.join(missing))


def run(data, formal_end, output_dir, resume=False, max_windows=None):
    validate(data)
    start=timestamp(data['intervals'][0]['start']); end=timestamp(formal_end)
    require(start.hour == end.hour == 0 and start.minute == end.minute == 0 and start < end,
            'Rolling uses complete JST days')
    require(timestamp(data['intervals'][-1]['start'])+timedelta(minutes=30) == end+timedelta(days=1),
            'Exactly one complete observation day required')
    identity=dict(input_sha256=digest(data), code_sha256=code_identity(), formal_end=end.isoformat())
    output=Path(output_dir)
    state=dict(next_start=start.isoformat(), soc=data['asset']['initial_mwh'], used={}, frozen=data['initial_frozen'].copy())
    transactions=[]
    if resume:
        manifest=json.loads((output/'manifest.json').read_text(encoding='utf-8'))
        require(manifest['identity'] == identity, 'Resume code/input identity mismatch')
        parent=digest(manifest)
        for sequence, path in enumerate(sorted((output/'windows').glob('*.json'))):
            tx=json.loads(path.read_text(encoding='utf-8')); sha=tx.pop('sha256')
            require(sha == digest(tx) and tx['parent'] == parent and tx['sequence'] == sequence
                    and tx['previous_state'] == state and path.name == f'{sequence:05d}.json', 'Corrupt transaction chain')
            state=tx['next_state']; parent=sha; transactions.append(dict(tx, sha256=sha))
    else:
        output.mkdir(parents=True, exist_ok=False); (output/'windows').mkdir()
        manifest=dict(identity=identity, input=data, initial_state=state,
                      classification=data['classification'], guarantee_scope='finite_chained')
        atomic_json(output/'manifest.json', manifest, immutable=True); parent=digest(manifest)
    specs={o['id']: o for o in data['spot_orders']}
    specs.update({b['id']: b for b in data['capacity_blocks']})
    solved=0; failure=None
    while timestamp(state['next_start']) < end and (max_windows is None or solved < max_windows):
        now=timestamp(state['next_start']); execute_end=now+timedelta(days=1)
        try:
            plan_end=planning_end(data,now,execute_end,state['frozen'])
            result=solve_window(data, now.isoformat(), plan_end.isoformat(), state['soc'], state['frozen'], state['used'], end.isoformat())
            check_due_orders(specs, now, execute_end, result['orders'], state['frozen'])
            executed=[r for r in result['intervals'] if timestamp(r['start']) < execute_end]
            future_frozen=state['frozen'].copy()
            for key, quantity in result['orders'].items():
                if timestamp(specs[key]['gate']) < execute_end:
                    if key not in future_frozen:
                        future_frozen[key]=quantity
            consumed=state['used'].copy()
            for row in executed:
                year=str(timestamp(row['start']).year); consumed[year]=consumed.get(year, 0.)+row['efc']
            next_state=dict(next_start=execute_end.isoformat(), soc=executed[-1]['soc_end_mwh'], used=consumed, frozen=future_frozen)
            statuses={key: ('RESULT' if timestamp(specs[key]['result']) <= execute_end else 'SUBMITTED') for key in future_frozen}
            tx=dict(sequence=len(transactions), parent=parent, previous_state=state, next_state=next_state,
                    executed=executed, order_status=statuses, window=result)
            sha=digest(tx); tx['sha256']=sha
            atomic_json(output/'windows'/f'{len(transactions):05d}.json', tx, immutable=True)
            transactions.append(tx); state=next_state; parent=sha; solved+=1
            atomic_json(output/'checkpoint.json', state)
        except (ValueError, KeyError) as exc:
            failure=str(exc); break
    records=[r for tx in transactions for r in tx['executed']]
    fields=list(records[0]) if records else ['start']
    with (output/'executed_30min.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer=csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(records)
    monthly=defaultdict(lambda: dict(intervals=0, spot_jpy=0., capacity_jpy=0., activation_jpy=0., total_jpy=0., efc=0.))
    for row in records:
        values=monthly[timestamp(row['start']).strftime('%Y-%m')]; values['intervals']+=1
        for key in ('spot_jpy', 'capacity_jpy', 'activation_jpy', 'total_jpy', 'efc'):
            values[key]+=row[key]
    atomic_json(output/'monthly_cash.json', dict(monthly))
    atomic_json(output/'committed_orders.json', state['frozen'])
    atomic_json(output/'solver_metrics.json', [dict(start=tx['window']['start'], **tx['window']['metrics']) for tx in transactions])
    cash={k: sum(r[k] for r in records) for k in ('spot_jpy', 'capacity_jpy', 'activation_jpy', 'total_jpy')}
    summary=dict(status='BLOCKED' if failure else ('COMPLETE' if timestamp(state['next_start']) == end else 'PARTIAL'),
                 classification=data['classification'], scenario=data['scenario'], area=data['area'],
                 formal_end=end.isoformat(), executed_intervals=len(records), windows=len(transactions),
                 cash=None if failure else cash, executed_cash=cash,
                 end_soc_mwh=state['soc'], used_efc=state['used'], failure=failure,
                 solver_seconds=sum(tx['window']['metrics']['seconds'] for tx in transactions),
                 max_variables=max((tx['window']['metrics']['variables'] for tx in transactions), default=0),
                 max_integers=max((tx['window']['metrics']['integers'] for tx in transactions), default=0),
                 finite_state_approximation=True, perfect_information=True, verified_real_revenue=False,
                 settlement_scope=('FCR_ONLY_NO_SURPLUS_CONTRACT_NO_V1_V2_IMBALANCE_EXCLUDED_NOT_FULL_NET_REVENUE'
                                   if data['scenario'] in ('LV_FCR', 'HV_SPOT_FCR')
                                   else 'CONDITIONAL_EXPLICIT_PAYMENT_MAPPING_NOT_VERIFIED_REAL_REVENUE'))
    atomic_json(output/'summary.json', summary)
    return summary
