"""Synthetic fixtures are TEST INPUTS, never station defaults or historical revenue."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from scipy.integrate import quad
from src.jp_milp.config import JST, Asset, InputError
from src.jp_milp.activation import fcr_states, positive_normal, composite_states, edc_product_energy
from src.jp_milp.inputs import validate, capacity_price
from src.jp_milp.core import solve_window
from src.jp_milp.audit import audit_window
from src.jp_milp.rolling import run, check_due_orders
from src.jp_milp.sensitivity import composite_variant
from src.jp_milp.budget import common_coverage_budget


def fixture(scenario='LV_FCR', n=8, block_size=1):
    begin=datetime(2026, 6, 2, tzinfo=JST)
    asset=dict(version='SYNTHETIC_DEVICE_ONLY', charge_mw=4., discharge_mw=4., nominal_mwh=40.,
               minimum_mwh=2., maximum_mwh=38., initial_mwh=20., target_mwh=20., eta_charge=.95,
               eta_discharge=.95, auxiliary_ac_mw=0., auxiliary_dc_mw=0., import_mw=4., export_mw=4.,
               service_scale=1., service_offset_mw=0., poi_scale=1., poi_offset_mw=0.,
               port_domain_min_mw=-4., port_domain_max_mw=4.)
    result=dict(asset=asset, scenario=scenario, classification='SYNTHETIC_VALIDATION', currency='JPY',
                timezone='Asia/Tokyo', area='KYUSHU', assumption_version='SYNTHETIC_v1',
                provenance=[dict(source='synthetic fixture; not official historical data')],
                solver=dict(time_limit_seconds=20., mip_rel_gap=1e-6, presolve=True), intervals=[],
                spot_orders=[], capacity_blocks=[], initial_frozen={}, annual_budgets_efc={'2026': 100.},
                terminal_value_jpy_mwh=0.)
    composite=scenario == 'HV_SPOT_S1_T1'
    for i in range(n):
        t=begin+timedelta(minutes=30*i); key=t.isoformat()
        payment=dict(mapping_id='SYNTHETIC_RECOGNITION', basis='joint_physical_gross',
                     recognition_up=.7 if composite else 0.,
                     recognition_down=.8 if composite else 0.,
                     signed_price_up=700. if composite else None,
                     signed_price_down=-300. if composite else None)
        states=composite_states([(.5, -.4), (.5, .6)], .1, [(1., 0.)], 0.) if composite else [dict(weight=.5, f=-.2, s=0., t=0.), dict(weight=.5, f=.2, s=0., t=0.)]
        row=dict(start=key, area='KYUSHU', asset_version=asset['version'], availability=1., states=states, payment=payment)
        if composite:
            row['joint_metadata']=dict(theta=0., coupling='independent', lfc_mean=.1, edc_center=.1,
                                       normalization_id='SYNTHETIC_REFERENCE_POOL', lfc_marginal=[(.5, -.4), (.5, .6)],
                                       edc_deviations=[(1., 0.)])
        result['intervals'].append(row)
        gate=(t-timedelta(days=1)).replace(hour=10, minute=0)
        result['spot_orders'].append(dict(id='DA/'+key, market='DA', weights={key: 1.}, buy_limit_mw=4.,
                                          sell_limit_mw=4., price_jpy_mwh=1000.+2000.*((i//8)%2), grid_mw=0.,
                                          gate=gate.isoformat(), result=gate.replace(hour=11).isoformat()))
    for start in range(0, n, block_size):
        group=result['intervals'][start:start+block_size]; first=datetime.fromisoformat(group[0]['start'])
        gate=(first-timedelta(days=1)).replace(hour=14, minute=0)
        extremes=[dict(f=0., s=1., t=0.), dict(f=0., s=-1., t=0.),
                  dict(f=0., s=0., t=1.), dict(f=0., s=0., t=-1.)] if composite else [dict(f=1., s=0., t=0.), dict(f=-1., s=0., t=0.)]
        services=[dict(initial_bound='lower' if sum(ext.values()) > 0 else 'upper',
                       segments=[dict(hours=1/12, **ext)]) for ext in extremes]
        block=dict(id='CAP/'+group[0]['start'], asset_version=asset['version'], intervals=[r['start'] for r in group],
                   gate=gate.isoformat(), result=gate.replace(hour=15).isoformat(),
                   price_evidence='SYNTHETIC_PRICE', capability_validation_id='SYNTHETIC_FINITE_SCOPE',
                   price_jpy_mw_30min={r['start']: 2000. for r in group}, extremes=extremes, services=services,
                   response_envelope=None,
                   service_requirements={p: dict(up_coefficient=1., down_coefficient=1., up_hours=1/12,
                                                 down_hours=1/12, evidence_id='SYNTHETIC_ONLY')
                                         for p in (('s', 't') if composite else ('f',))})
        if composite:
            block['bid_rules']={p: dict(grid_mw=.001, minimum_mw=1. if p == 'common' else 0., maximum_mw=4.)
                                for p in ('s', 't', 'common')}
            block['candidates']=[dict(id='complete_1_2', s=1., t=2., common=2., asset_version=asset['version'],
                                      full_inner_validation_id='SYNTHETIC_ONLY', domain_validation_id='SYNTHETIC_WHOLE_DOMAIN', domain=[])]
        else:
            block.update(minimum_mw=1., maximum_mw=3., grid_mw=.001, response_scaling_validated=True)
        result['capacity_blocks'].append(block)
    return result


def open_gates(data):
    """Test helper: fixed orders permit first-day commitments without changing clocks."""
    for o in data['spot_orders']:
        # Retain free intraday event so physical recovery remains a legal contract.
        o.update(market='ID', gate=data['intervals'][0]['start'], result=data['intervals'][0]['start'])
    # Test fixed capacities exercise frozen domain separate from new bid grid.
    for b in data['capacity_blocks']:
        if data['scenario'] == 'HV_SPOT_S1_T1':
            data['initial_frozen'][b['id']]=dict(f=0., s=1., t=2., common=2., candidate_id='complete_1_2')
        else:
            data['initial_frozen'][b['id']]=dict(f=1.2345, s=0., t=0., common=1.2345, candidate_id=None)
    return data


class JapanMILPTests(unittest.TestCase):
    def test_fcr_only_cash_exclusion_preserves_physics_and_audit(self):
        for scenario in ('LV_FCR', 'HV_SPOT_FCR'):
            data=open_gates(fixture(scenario))
            out=solve_window(data)
            self.assertEqual(out['audit']['status'], 'PASS')
            self.assertEqual(sum(r['activation_jpy'] for r in out['intervals']), 0.)
            for field in ('activation_up_mwh', 'activation_down_mwh', 'conversion_loss_mwh', 'efc'):
                self.assertGreater(sum(r[field] for r in out['intervals']), 0.)
            tampered=deepcopy(out);tampered['intervals'][0]['activation_jpy']=1.
            with self.assertRaises(ValueError):audit_window(data,tampered)
            stale=deepcopy(data);stale['intervals'][0]['payment'].update(recognition_up=1.,signed_price_up=1000.)
            with self.assertRaises(InputError):validate(stale)

    def test_advance_gate_cannot_disappear(self):
        data=fixture(n=192, block_size=6)
        order=data['spot_orders'][144]
        order.update(market='ID', gate='2026-06-02T12:00:00+09:00', result='2026-06-02T12:30:00+09:00')
        with self.assertRaisesRegex(InputError, 'Unsupported advance gate'):
            validate(data)
        start=datetime(2026, 6, 2, tzinfo=JST); end=start+timedelta(days=1)
        with self.assertRaisesRegex(InputError, 'Due orders omitted'):
            check_due_orders({order['id']: order}, start, end, {}, {})
        order['gate']=end.isoformat()
        check_due_orders({order['id']: order}, start, end, {}, {})
        with self.assertRaises(InputError):
            check_due_orders({order['id']: order}, end, end+timedelta(days=1), {}, {})
        check_due_orders({order['id']: order}, end, end+timedelta(days=1), {}, {order['id']: 0.})

    def test_gate_on_execution_boundary_frozen_next_window(self):
        data=fixture(n=192, block_size=6)
        order=data['spot_orders'][96]
        order.update(market='ID', gate='2026-06-03T00:00:00+09:00', result='2026-06-03T00:30:00+09:00')
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'boundary'
            first=run(data, '2026-06-05T00:00:00+09:00', path, max_windows=1)
            self.assertEqual(first['status'], 'PARTIAL')
            checkpoint=json.loads((path/'checkpoint.json').read_text())
            self.assertNotIn(order['id'], checkpoint['frozen'])
            second=run(data, '2026-06-05T00:00:00+09:00', path, resume=True, max_windows=1)
            self.assertEqual(second['status'], 'PARTIAL')
            checkpoint=json.loads((path/'checkpoint.json').read_text())
            self.assertIn(order['id'], checkpoint['frozen'])

    def test_utc_delivery_keys_rejected_at_month_and_year_boundaries(self):
        for begin in (datetime(2026, 7, 1, tzinfo=JST), datetime(2027, 1, 1, tzinfo=JST)):
            data=fixture(n=96, block_size=6)
            original=datetime.fromisoformat(data['intervals'][0]['start']); shift=begin-original
            def convert(value):
                return (datetime.fromisoformat(value)+shift).astimezone(timezone.utc).isoformat()
            for row in data['intervals']:
                row['start']=convert(row['start'])
            for order in data['spot_orders']:
                order['weights']={convert(k): v for k,v in order['weights'].items()}
                order['gate']=convert(order['gate']); order['result']=convert(order['result'])
            for block in data['capacity_blocks']:
                block['intervals']=[convert(k) for k in block['intervals']]
                block['price_jpy_mw_30min']={convert(k): v for k,v in block['price_jpy_mw_30min'].items()}
                block['gate']=convert(block['gate']); block['result']=convert(block['result'])
            with self.assertRaisesRegex(InputError, 'canonical JST'):
                validate(data)
            # Explicit conversion to canonical JST restores a valid boundary run.
            jst=lambda value: datetime.fromisoformat(value).astimezone(JST).isoformat()
            for row in data['intervals']:
                row['start']=jst(row['start'])
            for order in data['spot_orders']:
                order['weights']={jst(k): v for k,v in order['weights'].items()}
            for block in data['capacity_blocks']:
                block['intervals']=[jst(k) for k in block['intervals']]
                block['price_jpy_mw_30min']={jst(k): v for k,v in block['price_jpy_mw_30min'].items()}
            data['annual_budgets_efc']={str(begin.year): 100.}
            with tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/'canonical'
                report=run(data, (begin+timedelta(days=1)).isoformat(), path)
                self.assertEqual(report['status'], 'COMPLETE')
                monthly=json.loads((path/'monthly_cash.json').read_text())
                self.assertEqual(set(monthly), {begin.strftime('%Y-%m')})
                self.assertEqual(monthly[begin.strftime('%Y-%m')]['intervals'], 48)

    def test_cross_year_budget_and_unfunded_year(self):
        budget=common_coverage_budget(['2025-12-31T23:30:00+09:00'], ['2026-01-01T00:00:00+09:00'])
        self.assertEqual(budget['lookahead_only_years'], ['2026'])
        self.assertAlmostEqual(budget['annual_budgets_efc']['2025'], 600/(48*365))
        data=fixture(); data['annual_budgets_efc']={}
        with self.assertRaises(InputError): solve_window(data)

    def test_free_menu_rejects_invalid_domain(self):
        data=fixture('HV_SPOT_S1_T1', n=96, block_size=6)
        for b in data['capacity_blocks']:
            bad=b['candidates'][0]
            good=deepcopy(bad); good.update(id='complete_2_1', s=2., t=1.)
            bad['domain']=[dict(sense='>=', rhs=10., terms=[dict(interval=b['intervals'][0], variable='baseline', coefficient=1.)])]
            b['candidates'].append(good)
        out=solve_window(data)
        positive=[q for key,q in out['orders'].items() if key.startswith('CAP/') and q['common'] > 0]
        self.assertTrue(positive)
        self.assertTrue(all(q['candidate_id'] == 'complete_2_1' for q in positive))

    def test_negative_cash_sign_and_nonunit_ports(self):
        data=open_gates(fixture('HV_SPOT_S1_T1'))
        for row in data['intervals']:
            row['payment']['signed_price_up']=-500.
            row['payment']['signed_price_down']=200.
        data['asset'].update(service_scale=2., poi_scale=.8, service_offset_mw=.1, poi_offset_mw=-.1,
                             auxiliary_ac_mw=.01, auxiliary_dc_mw=.001)
        out=solve_window(data)
        self.assertEqual(out['audit']['status'], 'PASS')
        self.assertLess(out['intervals'][0]['activation_jpy'], 0.)

    def test_service_coverage_and_stale_candidate_rejected(self):
        data=fixture(); data['capacity_blocks'][0]['services']=[]
        with self.assertRaises(InputError): validate(data)
        data=fixture('HV_SPOT_S1_T1'); data['capacity_blocks'][0]['candidates'][0]['asset_version']='old'
        with self.assertRaises(InputError): validate(data)
        data=fixture('HV_SPOT_S1_T1'); data['capacity_blocks'][0]['candidates'][0]['s']=1.0005
        with self.assertRaises(InputError): validate(data)

    def test_missing_station_and_reference(self):
        data=fixture(); del data['asset']['eta_charge']
        with self.assertRaises(TypeError): validate(data)
        data=fixture(); data['intervals'][0]['states'][0]['weight']=None
        with self.assertRaises(InputError): validate(data)
        data=fixture('HV_SPOT_S1_T1'); data['intervals'][0]['payment']['signed_price_up']=None
        with self.assertRaises(InputError): validate(data)

    def test_normal_bins_and_alpha(self):
        for count in (11, 21):
            states=fcr_states(.01, .035, .01, .012, .05, .06, 1., 1., count)
            self.assertAlmostEqual(sum(s['weight'] for s in states), 1.)
            alpha=(positive_normal(-.01-.01, .035)-positive_normal(-.01-.01-.05, .035))/.05
            self.assertAlmostEqual(sum(s['weight']*s['gamma_up'] for s in states), alpha, places=12)
        deterministic=fcr_states(-.1, 0., .01, .01, .05, .05, 1., 1.)
        self.assertEqual(len(deterministic), 1); self.assertEqual(deterministic[0]['f'], 1.)

    def test_joint_identity_and_gross(self):
        states=composite_states([(.5, -.5), (.5, .5)], .2, [(1., 0.)], 0.)
        self.assertAlmostEqual(.5*sum(s['weight']*max(s['s']+s['t'], 0) for s in states), .175)
        self.assertAlmostEqual(.5*sum(s['weight']*max(-s['s']-s['t'], 0) for s in states), .075)
        for theta in (0., .5, 1.):
            for coupling in ('independent', 'same', 'opposite'):
                states=composite_states([(.3, -.4), (.7, .6)], .2, [(.5, -.3), (.5, .3)], theta, coupling)
                self.assertAlmostEqual(sum(s['weight']*(3*s['s']+5*s['t']) for s in states), 1+3*theta*.3)

    def test_edc_allocation_and_units(self):
        v=edc_product_energy({'A': (10., 2.)}, {'S2': {'A': (.2, .3)}, 'T1': {'A': (.5, .4)}})
        self.assertEqual(v['T1'], [6., .8]); self.assertEqual(capacity_price(2., 'JPY/kW/30min'), 2000.)
        with self.assertRaises(InputError):
            edc_product_energy({'A': (10., 0.)}, {'S2': {'A': (.7, .3)}, 'T1': {'A': (.5, .4)}})

    def test_frozen_fractional_lv_physics_no_activation_cash(self):
        data=open_gates(fixture()); out=solve_window(data)
        self.assertEqual(out['audit']['status'], 'PASS')
        self.assertGreater(sum(r['activation_up_mwh'] for r in out['intervals']), 0.)
        self.assertGreater(sum(r['efc'] for r in out['intervals']), 0.)
        self.assertEqual(sum(r['activation_jpy'] for r in out['intervals']), 0.)
        self.assertAlmostEqual(out['orders'][data['capacity_blocks'][0]['id']]['f'], 1.2345)

    def test_composite_single_capacity_payment_and_domain(self):
        data=open_gates(fixture('HV_SPOT_S1_T1')); out=solve_window(data)
        self.assertAlmostEqual(sum(r['capacity_jpy'] for r in out['intervals']), 8*2*2000.)
        data['capacity_blocks'][0]['candidates'][0]['domain']=[dict(sense='>=', rhs=10., terms=[dict(interval=data['intervals'][0]['start'], variable='baseline', coefficient=1.)])]
        with self.assertRaises(ValueError): solve_window(data)

    def test_net_trades_once_and_audit_tamper(self):
        data=open_gates(fixture()); first=data['spot_orders'][0]
        second=deepcopy(first); second['id']='ID2'; second['price_jpy_mwh']=2000.
        data['spot_orders'].append(second)
        data['initial_frozen'][first['id']]=-1.; data['initial_frozen']['ID2']=1.
        out=solve_window(data)
        self.assertAlmostEqual(out['intervals'][0]['baseline_mw'], 0.)
        self.assertAlmostEqual(out['intervals'][0]['spot_jpy'], 500.)
        out['intervals'][0]['capacity_jpy']+=1.
        with self.assertRaises(ValueError): audit_window(data, out)

    def test_infeasible_fixed_no_clip_and_tail(self):
        data=open_gates(fixture()); data['initial_frozen'][data['capacity_blocks'][0]['id']]['f']=10.
        data['initial_frozen'][data['capacity_blocks'][0]['id']]['common']=10.
        with self.assertRaises(ValueError): solve_window(data)
        data=open_gates(fixture()); data['capacity_blocks'][-1]['services'][0]['segments'][0]['hours']=1.
        with self.assertRaises(InputError): solve_window(data)

    def test_native_three_hour_block(self):
        data=open_gates(fixture(n=12, block_size=6)); out=solve_window(data)
        self.assertEqual(len([k for k in out['orders'] if k.startswith('CAP/')]), 2)
        self.assertAlmostEqual(sum(r['capacity_jpy'] for r in out['intervals']), 12*1.2345*2000.)

    def test_service_chaining_and_conservative_bounds(self):
        data=open_gates(fixture(n=4))
        data['capacity_blocks'][0]['services'][0]['segments']=[dict(hours=.5, f=1., s=0., t=0.), dict(hours=.25, f=1., s=0., t=0.)]
        out=solve_window(data)
        witness=[w for w in out['witnesses'] if w['block'] == data['capacity_blocks'][0]['id'] and w['service'] == 0]
        self.assertEqual(len(witness), 2)
        self.assertAlmostEqual(witness[0]['soc_out_mwh'], witness[1]['soc_in_mwh'])

    def test_rolling_observation_resume_and_identity(self):
        data=fixture(n=144, block_size=6)
        end='2026-06-04T00:00:00+09:00'
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'run'
            first=run(data, end, path, max_windows=1); self.assertEqual(first['status'], 'PARTIAL')
            final=run(data, end, path, resume=True)
            self.assertEqual(final['status'], 'COMPLETE'); self.assertEqual(final['executed_intervals'], 96)
            self.assertAlmostEqual(final['end_soc_mwh'], 20.)
            data['asset']['eta_charge']=.9
            with self.assertRaises(InputError): run(data, end, path, resume=True)


if __name__ == '__main__':
    unittest.main()
