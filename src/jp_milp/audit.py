"""Recompute physical quantities and cash directly from public numeric output.

This intentionally does not reuse the matrix expressions or solver objective.
"""
from collections import defaultdict
from .config import Asset, DT, TOL, timestamp


def near(x, y, label, tolerance=TOL):
    if abs(x-y) > tolerance:
        raise ValueError(f'Audit {label}: {x} != {y}')


def within(value, low, high, label):
    if value < low-TOL or value > high+TOL:
        raise ValueError('Audit boundary: '+label)


def audit_window(data, output):
    a=Asset(**data['asset']); inputs={r['start']: r for r in data['intervals']}
    blocks={t: b for b in data['capacity_blocks'] for t in b['intervals']}
    states=defaultdict(list)
    for s in output['states']:
        states[s['interval']].append(s)
    previous=output['initial_soc_mwh']; annual=defaultdict(float); count=0
    for row in output['intervals']:
        t=row['start']; r=inputs[t]; b=blocks[t]; q=output['orders'][b['id']]
        near(q['common'], max(q['f'], q['s'], q['t']), 'common capacity')
        if not b.get('market_enabled',True):
            for p in ('f','s','t','common'):near(q[p],0.,'disabled capacity market')
        plan=sum(o['weights'].get(t, 0)*output['orders'][o['id']]
                 for o in data['spot_orders'] if o['id'] in output['orders'])
        base=(plan-a.service_offset_mw)/a.service_scale
        near(base, row['baseline_mw'], 'baseline')
        lo, hi=a.net_bounds
        lo=max(lo, -a.charge_mw*r['availability']-a.auxiliary_ac_mw)
        hi=min(hi, a.discharge_mw*r['availability']-a.auxiliary_ac_mw)
        within(base, lo, hi, 'baseline')
        for ext in b['extremes']:
            within(base+sum(ext[p]*q[p] for p in ('f', 's', 't'))/a.service_scale, lo, hi, 'full direction')
        charging=discharging=up=down=0.
        if len(states[t]) != len(r['states']):
            raise ValueError('Audit state count')
        for s, expected in zip(states[t], r['states']):
            response=sum(expected[p]*q[p] for p in ('f', 's', 't'))
            net=base+response/a.service_scale
            c=max(-net-a.auxiliary_ac_mw, 0.); d=max(net+a.auxiliary_ac_mw, 0.)
            near(response, s['response_mw'], 'response'); near(c, s['charge_mw'], 'charge sign')
            near(d, s['discharge_mw'], 'discharge sign'); near(expected['weight'], s['weight'], 'state weight')
            within(net, lo, hi, 'state POI/PCS')
            if b['response_envelope'] is not None:
                within(response, -b['response_envelope']['down']*q['common'],
                       b['response_envelope']['up']*q['common'], 'shared envelope')
            w=DT*expected['weight']; charging+=w*c; discharging+=w*d
            up+=w*max(response, 0.); down+=w*max(-response, 0.)
        A=a.eta_charge*charging; B=discharging/a.eta_discharge+DT*a.auxiliary_dc_mw
        near(row['soc_start_mwh'], previous, 'SOC continuity')
        previous=previous+A-B
        within(row['soc_start_mwh']-B, a.minimum_mwh, a.maximum_mwh, 'SOC lower')
        within(row['soc_start_mwh']+A, a.minimum_mwh, a.maximum_mwh, 'SOC upper')
        expected=dict(charge_mwh=charging, discharge_mwh=discharging, activation_up_mwh=up, activation_down_mwh=down,
                      soc_end_mwh=previous, soc_lower_mwh=row['soc_start_mwh']-B, soc_upper_mwh=row['soc_start_mwh']+A,
                      conversion_loss_mwh=(1-a.eta_charge)*charging+(1/a.eta_discharge-1)*discharging,
                      auxiliary_ac_mwh=DT*a.auxiliary_ac_mw, auxiliary_dc_mwh=DT*a.auxiliary_dc_mw,
                      efc=(A+discharging/a.eta_discharge)/(2*a.usable_mwh))
        expected['spot_jpy']=sum(DT*o['weights'].get(t, 0)*o['price_jpy_mwh']*output['orders'][o['id']]
                                 for o in data['spot_orders'] if o['id'] in output['orders'])
        expected['capacity_jpy']=q['common']*b['price_jpy_mw_30min'][t]
        pay=r['payment']
        expected['activation_jpy']=0. if data['scenario'] in ('LV_FCR', 'HV_SPOT_FCR') else (up*pay['recognition_up']*pay['signed_price_up']
                                                                          +down*pay['recognition_down']*pay['signed_price_down'])
        expected['total_jpy']=sum(expected[k] for k in ('spot_jpy', 'capacity_jpy', 'activation_jpy'))
        for key, value in expected.items():
            near(row[key], value, key, 1e-4 if key.endswith('jpy') else TOL)
        annual[str(timestamp(t).year)]+=expected['efc']; count+=len(expected)
        if timestamp(t).timestamp()+1800 == timestamp(output['formal_end']).timestamp():
            near(previous, a.target_mwh, 'formal target')
        # Check selected full-inner domain using independently recomputed rows.
        if q['candidate_id'] is not None:
            c=next(c for c in b['candidates'] if c['id'] == q['candidate_id'])
            allrows={x['start']: x for x in output['intervals']}
            names={'baseline': 'baseline_mw', 'soc': 'soc_start_mwh', 'soc_lower': 'soc_lower_mwh', 'soc_upper': 'soc_upper_mwh'}
            for domain in c['domain']:
                value=sum(term['coefficient']*allrows[term['interval']][names[term['variable']]] for term in domain['terms'])
                low=domain['rhs'] if domain['sense'] in ('>=', '==') else -float('inf')
                high=domain['rhs'] if domain['sense'] in ('<=', '==') else float('inf')
                within(value, low, high, 'candidate domain')
    chains={}; output_rows={r['start']: r for r in output['intervals']}
    block_ids={b['id']: b for b in data['capacity_blocks']}
    # Construct an independent duration/response expectation (no matrix path reuse).
    expected_steps={}
    ordered=[r['start'] for r in output['intervals']]
    for b in data['capacity_blocks']:
        if b['id'] not in output['orders'] or output['orders'][b['id']]['common'] <= 0:
            continue
        q=output['orders'][b['id']]
        for t in b['intervals']:
            if t not in output_rows:
                continue
            for j, service in enumerate(b['services']):
                pos=ordered.index(t); elapsed=0.; step=0
                for seg in service['segments']:
                    remaining=seg['hours']
                    while remaining > 1e-10:
                        duration=min(DT-elapsed, remaining)
                        expected_steps[(b['id'], t, j, step)]=(ordered[pos], duration, sum(seg[p]*q[p] for p in ('f', 's', 't')))
                        elapsed+=duration; remaining-=duration; step+=1
                        if elapsed >= DT-1e-10:
                            pos+=1; elapsed=0.
    if len(output['witnesses']) != len(expected_steps):
        raise ValueError('Audit missing/extra witness steps')
    seen=set()
    for w in output['witnesses']:
        identifier=(w['block'], w['start'], w['service'], w['step'])
        if identifier in seen or identifier not in expected_steps:
            raise ValueError('Audit duplicate/unknown witness step')
        seen.add(identifier)
        interval, duration, response=expected_steps[identifier]
        if interval != w['interval']:
            raise ValueError('Audit service interval')
        near(duration, w['hours'], 'service duration'); near(response, w['response_mw'], 'service response')
        b=block_ids[w['block']]; service=b['services'][w['service']]
        key=(w['block'], w['start'], w['service'])
        initial=output_rows[w['start']]['soc_'+service['initial_bound']+'_mwh']
        near(w['soc_in_mwh'], chains.get(key, initial), 'witness chain')
        r=inputs[w['interval']]; base=output_rows[w['interval']]['baseline_mw']
        net=base+w['response_mw']/a.service_scale
        lo, hi=a.net_bounds
        within(net, max(lo, -a.charge_mw*r['availability']-a.auxiliary_ac_mw),
               min(hi, a.discharge_mw*r['availability']-a.auxiliary_ac_mw), 'witness power')
        c=max(-net-a.auxiliary_ac_mw, 0); d=max(net+a.auxiliary_ac_mw, 0)
        near(c, w['charge_mw'], 'witness charge'); near(d, w['discharge_mw'], 'witness discharge')
        end=w['soc_in_mwh']+w['hours']*(a.eta_charge*c-d/a.eta_discharge-a.auxiliary_dc_mw)
        near(end, w['soc_out_mwh'], 'witness SOC'); within(end, a.minimum_mwh, a.maximum_mwh, 'witness SOC')
        chains[key]=end
    for y, consumed in annual.items():
        within(consumed, 0, output['budgets'][y]['allowance'], 'annual EFC')
    for key, old in output['frozen_input'].items():
        if key not in output['orders']:
            continue
        new=output['orders'][key]
        if isinstance(old, dict):
            for p in ('f', 's', 't', 'common'):
                near(old[p], new[p], 'frozen '+key)
        else:
            near(old, new, 'frozen '+key)
    objective=sum(r['total_jpy'] for r in output['intervals'])+data['terminal_value_jpy_mwh']*(previous-a.target_mwh)
    if data.get('daily_soc_recovery')=='CONSTANT_BASELINE_TARGET_50':
        daily={}
        for r in output['intervals']:daily.setdefault(r['start'][:10],[]).append(r)
        for day in daily.values():
            for r in day:near(r['baseline_mw'],day[0]['baseline_mw'],'LV daily constant baseline')
            near(day[-1]['soc_end_mwh'],a.target_mwh,'LV daily recovery target')
    # The independently reconstructed terminal SOC is already checked within TOL
    # MWh. Convert that tolerance to currency instead of comparing it as JPY.
    cash_tolerance=1e-3+abs(data['terminal_value_jpy_mwh'])*TOL
    near(objective, output['metrics']['objective_jpy'], 'objective including constants', cash_tolerance)
    return dict(status='PASS', numeric_recomputations=count, service_chains=len(chains),
                finite_service_scope=True, annual_efc=dict(annual))
