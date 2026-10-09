"""JP §§3/4/6/8/9/14: finite-state MILP, native orders and chained witnesses."""
from datetime import timedelta
from math import floor, ceil
from .config import Asset, Solver, DT, TOL, require, timestamp
from .inputs import validate
from .linear import Matrix, expr


def path_steps(intervals, start, segments):
    """Split an explicitly ordered SERVICE path at settlement boundaries.

    Activation state IDs are never interpreted as a temporal order.
    """
    index=start; offset=0.; steps=[]
    for segment in segments:
        remaining=segment['hours']
        while remaining > 1e-10:
            if index >= len(intervals):
                return None
            hours=min(DT-offset, remaining)
            steps.append((index, hours, segment))
            remaining-=hours; offset+=hours
            if offset >= DT-1e-10:
                index+=1; offset=0.
    return steps


def allowance(data, used, window_end, formal_end):
    terminal_year=timestamp(formal_end)-timedelta(minutes=30)
    budgets=data['annual_budgets_efc']; out={}
    require(set(used) <= set(budgets), 'Executed EFC year has no budget')
    for year, limit in budgets.items():
        consumption=used.get(year, 0.)
        require(0 <= consumption <= limit+1e-8, 'Executed EFC budget conflict')
        available=max(0., limit-consumption)
        reserve=min(available, 1/(2*data['asset']['eta_discharge'])) if int(year) == terminal_year.year and window_end < timestamp(formal_end) else 0.
        out[year]=dict(limit=limit, used=consumption, reserve=reserve,
                       allowance=max(0., available-reserve-1e-6))
    return out


def solve_window(data, start=None, end=None, soc=None, frozen=None, used=None, formal_end=None):
    validate(data)
    a=Asset(**data['asset']); solver=Solver(**data['solver'])
    start=timestamp(start or data['intervals'][0]['start'])
    end=timestamp(end) if end else timestamp(data['intervals'][-1]['start'])+timedelta(minutes=30)
    soc=a.initial_mwh if soc is None else soc
    require(a.minimum_mwh <= soc <= a.maximum_mwh, 'Starting SOC outside limits')
    frozen=data['initial_frozen'].copy() if frozen is None else frozen.copy()
    used={} if used is None else used
    formal_end=formal_end or end.isoformat()
    rows=[r for r in data['intervals'] if start <= timestamp(r['start']) < end]
    require(rows and timestamp(rows[0]['start']) == start and timestamp(rows[-1]['start'])+timedelta(minutes=30) == end,
            'Window input coverage incomplete')
    index={r['start']: i for i, r in enumerate(rows)}; keys=set(index)
    spots=[o for o in data['spot_orders'] if keys.intersection(o['weights'])]
    blocks=[b for b in data['capacity_blocks'] if keys.intersection(b['intervals'])]
    for order in spots:
        require(set(order['weights']) <= keys, 'Window splits native spot contract')
    for b in blocks:
        require(set(b['intervals']) <= keys, 'Window splits native capacity block')
    all_ids={o['id'] for o in data['spot_orders']} | {b['id'] for b in data['capacity_blocks']}
    require(set(frozen) <= all_ids, 'Unknown frozen obligation')
    matrix=Matrix(); orders={}; quantities={}; active={}; choices={}; disabled={}
    # Fixed orders retain objective constants. Passed gates without an order close at zero.
    for o in spots:
        key=o['id']; fixed=key in frozen or timestamp(o['gate']) < start
        value=frozen.get(key, 0.)
        if fixed:
            require(-o['buy_limit_mw']-TOL <= value <= o['sell_limit_mw']+TOL, 'Fixed spot exceeds contract limit')
            orders[key]=expr(value)
        elif o['grid_mw'] > 0:
            grid=o['grid_mw']
            orders[key]=grid*matrix.var(key, ceil(-o['buy_limit_mw']/grid), floor(o['sell_limit_mw']/grid), 1)
        else:
            orders[key]=matrix.var(key, -o['buy_limit_mw'], o['sell_limit_mw'])
    zero=dict(f=0., s=0., t=0., common=0., candidate_id=None)
    for b in blocks:
        key=b['id']; fixed=key in frozen or timestamp(b['gate']) < start
        record=frozen.get(key, zero)
        complete=all(path_steps(rows, index[t], service['segments']) is not None
                     for t in b['intervals'] for service in b['services'])
        if fixed:
            require(all(isinstance(record[p], (int, float)) and record[p] >= 0 for p in ('f', 's', 't', 'common')),
                    'Invalid frozen capacity value')
            require(abs(record['common']-max(record['f'], record['s'], record['t'])) <= TOL, 'Frozen common mismatch')
            require(complete or record['common'] == 0, 'Fixed service obligation lacks physical tail')
            quantities[key]={p: expr(record[p]) for p in ('f', 's', 't', 'common')}
            active[key]=expr(float(record['common'] > 0)); choices[key]=[]
            if record['candidate_id'] is not None:
                match=[c for c in b.get('candidates', []) if c['id'] == record['candidate_id']]
                require(len(match) == 1 and all(abs(match[0][p]-record[p]) <= TOL for p in ('s', 't', 'common')),
                        'Frozen candidate changed')
                choices[key]=[(match[0], active[key])]
        elif not complete:
            quantities[key]={p: expr(0) for p in ('f', 's', 't', 'common')}
            active[key]=expr(0); choices[key]=[]; disabled[key]='INCOMPLETE_SERVICE_TAIL'
        elif data['scenario'] == 'HV_SPOT_S1_T1':
            choices[key]=[(c, matrix.var(key+'/'+c['id'], 0, 1, 1)) for c in b['candidates']]
            active[key]=sum((y for _, y in choices[key]), expr(0)); matrix.row(active[key], hi=1)
            quantities[key]={p: sum((c[p]*y for c, y in choices[key]), expr(0)) for p in ('s', 't', 'common')}
            quantities[key]['f']=expr(0)
        else:
            y=matrix.var(key+'/active', 0, 1, 1); grid=b['grid_mw']
            q=grid*matrix.var(key+'/grid', 0, floor(b['maximum_mw']/grid+1e-10), 1)
            matrix.row(q-b['minimum_mw']*y, lo=0); matrix.row(q-b['maximum_mw']*y, hi=0)
            quantities[key]=dict(f=q, s=expr(0), t=expr(0), common=q)
            active[key]=y; choices[key]=[]
        if data['scenario'] != 'HV_SPOT_S1_T1':
            matrix.row(quantities[key]['f'], hi=b['maximum_mw'], label='registered upper')
        else:
            for p in ('s', 't', 'common'):
                matrix.row(quantities[key][p], hi=b['bid_rules'][p]['maximum_mw'], label='registered upper')
    by_time={t: b for b in blocks for t in b['intervals']}
    e=[matrix.var('soc/'+str(i), a.minimum_mwh, a.maximum_mwh) for i in range(len(rows)+1)]
    matrix.row(e[0], lo=soc, hi=soc, label='initial SOC')
    if start < timestamp(formal_end) <= end:
        target_index=int((timestamp(formal_end)-start).total_seconds()/1800)
        matrix.row(e[target_index], lo=a.target_mwh, hi=a.target_mwh, label='formal terminal')
    baseline=[]; row_expr=[]; state_expr=[]

    def physical(net, r, name, enabled=None):
        low, high=a.net_bounds
        low=max(low, -a.charge_mw*r['availability']-a.auxiliary_ac_mw)
        high=min(high, a.discharge_mw*r['availability']-a.auxiliary_ac_mw)
        if enabled is None:
            matrix.row(net, lo=low, hi=high, label=name+'/ports')
        else:
            matrix.conditional(net, enabled, lo=low, hi=high, label=name+'/ports')
        c=matrix.var(name+'/charge', 0, a.charge_mw*r['availability'])
        d=matrix.var(name+'/discharge', 0, a.discharge_mw*r['availability'])
        u=matrix.var(name+'/direction', 0, 1, 1)
        matrix.row(c+a.charge_mw*r['availability']*u, hi=a.charge_mw*r['availability'])
        matrix.row(d-a.discharge_mw*r['availability']*u, hi=0)
        balance=d-c-a.auxiliary_ac_mw-net
        if enabled is None:
            matrix.row(balance, lo=0, hi=0, label=name+'/balance')
        else:
            matrix.conditional(balance, enabled, lo=0, hi=0, label=name+'/balance')
        return c, d

    for i, r in enumerate(rows):
        t=r['start']; b=by_time[t]; q=quantities[b['id']]
        plan=sum((o['weights'].get(t, 0)*orders[o['id']] for o in spots), expr(0))
        p=(plan-a.service_offset_mw)/a.service_scale; baseline.append(p)
        low, high=a.net_bounds
        matrix.row(p, lo=max(low, -a.charge_mw*r['availability']-a.auxiliary_ac_mw),
                   hi=min(high, a.discharge_mw*r['availability']-a.auxiliary_ac_mw), label='baseline')
        for ext in b['extremes']:
            full=p+sum((ext[k]*q[k] for k in ('f', 's', 't')), expr(0))/a.service_scale
            matrix.row(full, lo=max(low, -a.charge_mw*r['availability']-a.auxiliary_ac_mw),
                       hi=min(high, a.discharge_mw*r['availability']-a.auxiliary_ac_mw), label='full direction')
        charge=expr(0); discharge=expr(0); gross_up=expr(0); gross_down=expr(0)
        for j, s in enumerate(r['states']):
            response=sum((s[k]*q[k] for k in ('f', 's', 't')), expr(0))
            if b['response_envelope'] is not None:
                matrix.row(response-b['response_envelope']['up']*q['common'], hi=0, label='shared envelope up')
                matrix.row(response+b['response_envelope']['down']*q['common'], lo=0, label='shared envelope down')
            c, d=physical(p+response/a.service_scale, r, f'state/{i}/{j}')
            charge+=DT*s['weight']*c; discharge+=DT*s['weight']*d
            # For a finite menu the positive response is linear in exclusive y.
            if choices[b['id']]:
                pos=sum((max(0., s['s']*cand['s']+s['t']*cand['t'])*y
                         for cand, y in choices[b['id']]), expr(0))
            elif data['scenario'] != 'HV_SPOT_S1_T1':
                pos=max(s['f'], 0.)*q['f']
            else:
                pos=matrix.positive(response, f'activation/{i}/{j}')
            gross_up+=DT*s['weight']*pos; gross_down+=DT*s['weight']*(pos-response)
            state_expr.append(dict(interval=t, state=j, weight=s['weight'], response_mw=response,
                                   charge_mw=c, discharge_mw=d))
        incoming=a.eta_charge*charge
        outgoing=discharge/a.eta_discharge+DT*a.auxiliary_dc_mw
        lower=e[i]-outgoing; upper=e[i]+incoming
        matrix.row(e[i+1]-e[i]-incoming+outgoing, lo=0, hi=0, label='SOC recursion')
        matrix.row(lower, lo=a.minimum_mwh, label='conservative SOC lower')
        matrix.row(upper, hi=a.maximum_mwh, label='conservative SOC upper')
        efc=(a.eta_charge*charge+discharge/a.eta_discharge)/(2*a.usable_mwh)
        spot=sum((DT*o['weights'].get(t, 0)*o['price_jpy_mwh']*orders[o['id']] for o in spots), expr(0))
        cap=b['price_jpy_mw_30min'][t]*q['common']
        pay=r['payment']
        cash=expr(0) if data['scenario'] == 'LV_FCR' else (gross_up*pay['recognition_up']*pay['signed_price_up']
                                                           +gross_down*pay['recognition_down']*pay['signed_price_down'])
        row_expr.append(dict(start=t, baseline_mw=p, soc_start_mwh=e[i], soc_end_mwh=e[i+1],
                             soc_lower_mwh=lower, soc_upper_mwh=upper, charge_mwh=charge, discharge_mwh=discharge,
                             activation_up_mwh=gross_up, activation_down_mwh=gross_down,
                             conversion_loss_mwh=(1-a.eta_charge)*charge+(1/a.eta_discharge-1)*discharge,
                             auxiliary_ac_mwh=DT*a.auxiliary_ac_mw, auxiliary_dc_mwh=DT*a.auxiliary_dc_mw,
                             efc=efc, spot_jpy=spot, capacity_jpy=cap, activation_jpy=cash,
                             total_jpy=spot+cap+cash))
    # State applicability is a constraint, not merely a capacity feasibility check.
    for b in blocks:
        for c, selected in choices[b['id']]:
            for domain in c['domain']:
                lhs=expr(0)
                for term in domain['terms']:
                    i=index[term['interval']]
                    value={'baseline': baseline[i], 'soc': e[i], 'soc_lower': row_expr[i]['soc_lower_mwh'],
                           'soc_upper': row_expr[i]['soc_upper_mwh']}[term['variable']]
                    lhs+=term['coefficient']*value
                limits=dict(lo=domain['rhs']) if domain['sense'] == '>=' else dict(hi=domain['rhs'])
                if domain['sense'] == '==':
                    limits=dict(lo=domain['rhs'], hi=domain['rhs'])
                matrix.conditional(lhs, selected, **limits, label='full-inner domain')
    witness_expr=[]
    for b in blocks:
        key=b['id']; q=quantities[key]; on=active[key]
        if matrix.bounds(on)[1] == 0:
            continue
        for t in b['intervals']:
            for service_id, service in enumerate(b['services']):
                steps=path_steps(rows, index[t], service['segments'])
                require(steps is not None, 'Service tail unavailable')
                value=row_expr[index[t]]['soc_'+service['initial_bound']+'_mwh']
                for step, (i, hours, segment) in enumerate(steps):
                    r=rows[i]; response=sum((segment[k]*q[k] for k in ('f', 's', 't')), expr(0))
                    c, d=physical(baseline[i]+response/a.service_scale, r,
                                  f'witness/{key}/{index[t]}/{service_id}/{step}', on)
                    next_value=matrix.var(f'witness_soc/{key}/{index[t]}/{service_id}/{step}', a.minimum_mwh, a.maximum_mwh)
                    matrix.conditional(next_value-value-hours*(a.eta_charge*c-d/a.eta_discharge-a.auxiliary_dc_mw),
                                       on, lo=0, hi=0, label='chained service SOC')
                    witness_expr.append(dict(block=key, start=t, service=service_id, step=step, interval=r['start'],
                                             hours=hours, active=on, soc_in_mwh=value, soc_out_mwh=next_value,
                                             charge_mw=c, discharge_mw=d, response_mw=response))
                    value=next_value
    budgets=allowance(data, used, end, formal_end)
    years={str(timestamp(r['start']).year) for r in rows}
    require(years <= set(budgets), 'Planning year lacks explicit annual/observation budget')
    for year in years:
        matrix.row(sum((r['efc'] for r in row_expr if str(timestamp(r['start']).year) == year), expr(0)),
                   hi=budgets[year]['allowance'], label='annual EFC')
    objective=sum((r['total_jpy'] for r in row_expr), expr(0))+data['terminal_value_jpy_mwh']*(e[-1]-a.target_mwh)
    vector, metrics=matrix.solve(objective, solver)

    def evaluate(row):
        return {k: float(v.value(vector)) if hasattr(v, 'value') else v for k, v in row.items()}

    result_orders={k: float(v.value(vector)) for k, v in orders.items()}
    for b in blocks:
        key=b['id']; result_orders[key]=evaluate(quantities[key])
        chosen=[c['id'] for c, y in choices[key] if y.value(vector) > .5]
        result_orders[key]['candidate_id']=chosen[0] if chosen else None
    result=dict(intervals=[evaluate(r) for r in row_expr], states=[evaluate(r) for r in state_expr],
                witnesses=[evaluate(r) for r in witness_expr if r['active'].value(vector) > .5],
                orders=result_orders, metrics=metrics, budgets=budgets, disabled_new_blocks=disabled,
                start=start.isoformat(), end=end.isoformat(), initial_soc_mwh=soc, formal_end=formal_end,
                frozen_input=frozen)
    from .audit import audit_window
    result['audit']=audit_window(data, result)
    return result
