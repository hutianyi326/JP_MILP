"""Validated normalized input bundle. Original source CSVs remain read-only.

The JSON bundle is the executable view of the ten logical CSV tables in the
2026-10-04 contract, not an automatic claim that those tables are populated.
"""
from dataclasses import asdict
from datetime import timedelta
import json
from pathlib import Path
from .config import Asset, Solver, SCENARIOS, require, number, timestamp, digest
from .scheduling import capacity_clock, HISTORICAL, CLOSURE


def load(path):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    validate(data)
    return data


def validate(data):
    a = Asset(**data['asset']); a.validate()
    Solver(**data['solver']).validate()
    scenario = data['scenario']; require(scenario in SCENARIOS, 'Unknown scenario')
    horizon=data.get('planning_horizon_policy','TWO_DAYS')
    clock_policy=data.get('capacity_clock_policy','NOMINAL_D1')
    require(horizon in ('TWO_DAYS',CLOSURE) and clock_policy in ('NOMINAL_D1',HISTORICAL),'Unknown scheduling policy')
    require(clock_policy!=HISTORICAL or horizon==CLOSURE,'Historical weekly clocks require obligation horizon closure')
    require(data['classification'] in ('SYNTHETIC_VALIDATION', 'EX_POST_CONDITIONAL'),
            'This version does not implement a forecast strategy')
    if scenario=='LV_FCR' and data['classification']!='SYNTHETIC_VALIDATION':
        require(data.get('capacity_price_binding')=='EV_OFFLINE_1_1_SOURCE_STRICT_V1',
                'Production EV requires strict offline 1-1 capacity price binding')
    require(data['currency'] == 'JPY' and data['timezone'] == 'Asia/Tokyo', 'JPY/JST required')
    require(bool(data['assumption_version']) and bool(data['provenance']), 'Version and provenance required')
    rows = data['intervals']; require(bool(rows), 'Empty grid')
    times = [timestamp(r['start']) for r in rows]
    require(all(r['start'] == t.isoformat() for r, t in zip(rows, times)),
            'Delivery keys must be canonical JST ISO strings (+09:00, seconds included)')
    require(all(y-x == timedelta(minutes=30) for x, y in zip(times, times[1:])), 'Missing/duplicate time grid')
    require(len({r['start'] for r in rows}) == len(rows), 'Duplicate interval key')
    keys = {r['start'] for r in rows}; coverage = {}
    for r in rows:
        require(r['asset_version'] == a.version, 'Activation state asset version mismatch')
        require(r['area'] == data['area'], 'Mixed TSO area')
        require(0 <= number(r['availability'], 'availability') <= 1, 'Invalid availability')
        states = r['states']; require(bool(states), 'Missing activation states')
        require(abs(sum(number(s['weight'], 'weight') for s in states)-1) < 1e-9, 'State weights must sum to one')
        for s in states:
            require(s['weight'] > 0, 'Zero/negative state weight: remove zero states before optimization')
            for p in ('f', 's', 't'):
                number(s[p], 'state coefficient')
            require((s['f'] == 0 if scenario == 'HV_SPOT_S1_T1' else s['s'] == s['t'] == 0),
                    'Inactive product response present')
        payment = r['payment']
        require(bool(payment['mapping_id']), 'Missing settlement recognition evidence/assumption')
        require(payment['basis'] == 'joint_physical_gross', 'Unsupported settlement basis; no silent substitution')
        for d in ('up', 'down'):
            require(0 <= number(payment['recognition_'+d], 'recognition') <= 1, 'Invalid recognition')
            if scenario in ('LV_FCR', 'HV_SPOT_FCR'):
                require(payment['recognition_'+d] == 0 and payment['signed_price_'+d] is None,
                        'FCR-only activation cash must be explicitly not applicable; surplus-contract exceptions require a separate model')
            else:
                number(payment['signed_price_'+d], 'signed JPY/MWh activation price')
        if scenario == 'HV_SPOT_S1_T1':
            m = r['joint_metadata']
            require(0 <= number(m['theta'], 'theta') <= 1 and bool(m['coupling'])
                    and bool(m['normalization_id']), 'Missing joint assumptions')
            for k in ('lfc_mean', 'edc_center'):
                number(m[k], k)
            require(abs(sum(s['weight']*s['s'] for s in states)-m['theta']*m['lfc_mean']) < 1e-8,
                    'LFC centering identity failed')
            require(abs(sum(s['weight']*s['t'] for s in states)-m['edc_center']) < 1e-8,
                    'EDC mean identity failed')
    ids = set()
    for order in data['spot_orders']:
        require(order['id'] not in ids, 'Duplicate order ID'); ids.add(order['id'])
        require(bool(order['weights']) and set(order['weights']) <= keys, 'Spot delivery outside grid')
        require(all(number(w, 'delivery weight') > 0 for w in order['weights'].values()), 'Positive weights required')
        require(min(number(order['buy_limit_mw'], 'buy limit'), number(order['sell_limit_mw'], 'sell limit')) >= 0,
                'Finite nonnegative trade limits required')
        number(order['price_jpy_mwh'], 'spot price')
        gate, result = timestamp(order['gate']), timestamp(order['result'])
        require(gate <= result <= min(timestamp(t) for t in order['weights']), 'Invalid spot clock')
        # A gate within this run must be handled in its own execution-day window.
        # Explicit initial commitments already exist; missing pre-start commitments
        # are the separately documented first-day zero-order convention.
        if horizon=='TWO_DAYS' and gate >= times[0] and order['id'] not in data['initial_frozen']:
            gate_day=gate.replace(hour=0, minute=0)
            delivery_end=max(timestamp(t) for t in order['weights'])+timedelta(minutes=30)
            require(delivery_end <= gate_day+timedelta(days=2),
                    'Unsupported advance gate: full delivery must fit the gate-day two-day window')
        require(order['market'] in ('DA', 'ID'), 'Unsupported spot market')
        if order['market'] == 'DA':
            first = min(timestamp(t) for t in order['weights'])
            expected = (first-timedelta(days=1)).replace(hour=10, minute=0)
            require(gate == expected and result < expected.replace(hour=14), 'DA nominal clock mismatch')
        number(order['grid_mw'], 'spot grid'); require(order['grid_mw'] >= 0, 'Negative spot grid')
    for b in data['capacity_blocks']:
        require(type(b.get('market_enabled',True)) is bool,'Market enabled must be boolean')
        if not b.get('market_enabled',True):
            require(bool(b.get('market_disabled_reason')),'Disabled capacity market needs an explicit reason')
        if data.get('capacity_price_binding')=='EV_OFFLINE_1_1_SOURCE_STRICT_V1':
            require(b.get('market_product')=='F_OFFLINE' and '/F_OFFLINE/' in b['id']
                    and b['price_evidence'].startswith('EPRX_1_1_SOURCE_AVERAGE_AGGREGATE_PROXY/'),
                    'EV strict binding requires offline 1-1 evidence and identity')
        require(b['id'] not in ids, 'Duplicate order ID'); ids.add(b['id'])
        require(b['asset_version'] == a.version, 'Candidate asset version mismatch')
        require(bool(b['intervals']) and set(b['intervals']) <= keys, 'Native block outside grid')
        bt = [timestamp(t) for t in b['intervals']]
        require(all(y-x == timedelta(minutes=30) for x, y in zip(bt, bt[1:])), 'Noncontiguous native block')
        require(all(t not in coverage for t in b['intervals']), 'Overlapping formal capacity units unsupported')
        coverage.update({t: b['id'] for t in b['intervals']})
        first = bt[0]; previous = (first-timedelta(days=1)).replace(hour=14, minute=0)
        result_clock=previous.replace(hour=15)
        if clock_policy==HISTORICAL:
            previous,result_clock,count=capacity_clock(b['intervals'][0])
            require(len(bt)==count and (count==1 or first.hour%3==0 and first.minute==0),'Historical native block shape mismatch')
            require(bool(b.get('clock_evidence')),'Historical clock evidence required')
        require(timestamp(b['gate']) == previous and timestamp(b['result']) == result_clock,
                'Capacity nominal clock mismatch')
        require(bool(b['price_evidence']) and bool(b['capability_validation_id']), 'Price/capability evidence required')
        require(set(b['price_jpy_mw_30min']) == set(b['intervals']), 'Capacity price coverage mismatch')
        for price in b['price_jpy_mw_30min'].values():
            number(price, 'capacity JPY/MW/30min price')
        require(bool(b['extremes']) and bool(b['services']), 'Full-power and finite-service definitions required')
        products=('s', 't') if scenario == 'HV_SPOT_S1_T1' else ('f',)
        require(set(b['service_requirements']) == set(products), 'Product service requirements incomplete')
        for p in products:
            req=b['service_requirements'][p]
            require(bool(req['evidence_id']), 'Direction/duration source or assumption required')
            for direction, sign, bound in (('up', 1., 'lower'), ('down', -1., 'upper')):
                h=number(req[direction+'_coefficient'], 'full direction coefficient')
                duration=number(req[direction+'_hours'], 'required continuous service duration')
                require(h >= 0 and duration >= 0 and (h == 0 or duration > 0), 'Invalid service requirement')
                if h == 0:
                    continue
                def matches(vector):
                    return all(abs(vector[k]-(sign*h if k == p else 0.)) < 1e-10 for k in ('f', 's', 't'))
                require(any(matches(v) for v in b['extremes']), 'Missing full product direction extreme')
                require(any(s['initial_bound'] == bound and all(matches(seg) for seg in s['segments'])
                            and sum(seg['hours'] for seg in s['segments']) >= duration-1e-10 for s in b['services']),
                        'Required full continuous service not covered by declared witness paths')
        for vector in b['extremes']:
            for p in ('f', 's', 't'):
                number(vector[p], 'extreme coefficient')
        for service in b['services']:
            require(service['initial_bound'] in ('lower', 'upper'), 'Service must use conservative intra-slot SOC bounds')
            require(bool(service['segments']), 'Empty continuous service path')
            for seg in service['segments']:
                require(number(seg['hours'], 'service duration') > 0, 'Positive service duration required')
                for p in ('f', 's', 't'):
                    number(seg[p], 'service coefficient')
        require({'lower', 'upper'} <= {s['initial_bound'] for s in b['services']},
                'Both SOC extremes must have declared service paths')
        if scenario == 'HV_SPOT_S1_T1':
            require(bool(b['candidates']), 'No validated full-inner menu; NOT_READY')
            names = set()
            for c in b['candidates']:
                require(c['id'] not in names, 'Duplicate candidate'); names.add(c['id'])
                require(c['asset_version'] == a.version and bool(c['full_inner_validation_id']), 'Unvalidated/stale candidate')
                require(min(number(c['s'], 'S1 MW'), number(c['t'], 'T1 MW')) > 0, 'Both composite products required')
                require(abs(number(c['common'], 'common MW')-max(c['s'], c['t'])) < 1e-9,
                        'Common capacity must be max, never sum')
                for p in ('s', 't', 'common'):
                    rule=b['bid_rules'][p]
                    require(number(rule['grid_mw'], 'candidate grid') > 0
                            and 0 <= number(rule['minimum_mw'], 'minimum') <= number(rule['maximum_mw'], 'maximum'),
                            'Invalid composite offer limits')
                    require(rule['minimum_mw'] <= c[p] <= rule['maximum_mw']
                            and abs(c[p]/rule['grid_mw']-round(c[p]/rule['grid_mw'])) < 1e-7,
                            'Candidate violates new offer grid or bounds')
                require(bool(c['domain_validation_id']), 'Candidate domain validation required (including whole domain)')
                for d in c['domain']:
                    require(d['sense'] in ('<=', '>=', '==') and bool(d['terms']), 'Invalid candidate domain')
                    number(d['rhs'], 'domain rhs')
                    for term in d['terms']:
                        require(term['interval'] in b['intervals'] and term['variable'] in ('baseline', 'soc', 'soc_lower', 'soc_upper'),
                                'Unknown domain variable')
                        number(term['coefficient'], 'domain coefficient')
        else:
            require(number(b['minimum_mw'], 'minimum offer') > 0 and number(b['maximum_mw'], 'capacity upper') > 0,
                    'Positive capacity bounds required')
            require(number(b['grid_mw'], 'capacity grid') > 0, 'Capacity grid required')
            require(b['response_scaling_validated'] is True, 'Fixed gamma requires validated capacity scaling')
        if b['response_envelope'] is not None:
            require(bool(b['response_envelope']['assumption_id']), 'Shared envelope is an explicit engineering assumption')
            require(min(number(b['response_envelope'][d], d) for d in ('up', 'down')) >= 0, 'Invalid envelope')
    require(set(coverage) == keys, 'Each interval needs exactly one native capacity opportunity definition')
    block_by_id={b['id']:b for b in data['capacity_blocks']}
    require(set(data['initial_frozen']) <= ids, 'Unknown fixed order; cannot erase external obligation')
    for key, value in data['initial_frozen'].items():
        if key in {s['id'] for s in data['spot_orders']}:
            number(value, 'fixed spot MW')
        else:
            require(set(value) == {'f', 's', 't', 'common', 'candidate_id'}, 'Unsupported frozen capacity record')
            for p in ('f', 's', 't', 'common'):
                require(number(value[p], 'fixed capacity') >= 0, 'Negative frozen capacity')
            require(abs(value['common']-max(value['f'], value['s'], value['t'])) < 1e-9, 'Fixed common mismatch')
            block=block_by_id[key]
            require(block.get('market_enabled',True) or value['common']==0,
                    'Disabled market conflicts with frozen capacity; cannot erase an obligation')
            require((value['f'] == 0 if scenario == 'HV_SPOT_S1_T1' else value['s'] == value['t'] == 0),
                    'Frozen obligation incompatible with scenario')
    for y, value in data['annual_budgets_efc'].items():
        require(str(int(y)) == y and number(value, 'annual EFC budget') >= 0, 'Invalid annual budget')
    number(data['terminal_value_jpy_mwh'], 'explicit terminal estimate')
    require(data['terminal_value_jpy_mwh'] >= 0, 'Negative terminal estimate')
    return dict(intervals=len(rows), blocks=len(data['capacity_blocks']), spot_orders=len(data['spot_orders']),
                asset_sha256=digest(asdict(a)), input_sha256=digest(data), status='READY_FOR_CONDITIONAL_SOLVE')


def capacity_price(value, unit):
    number(value, 'price')
    require(unit in ('JPY/kW/30min', 'JPY/MW/30min'), 'Explicit native capacity unit required')
    return value*1000 if unit == 'JPY/kW/30min' else value
