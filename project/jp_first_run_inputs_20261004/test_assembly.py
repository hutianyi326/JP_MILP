"""Adapter validation. Device/control/menu below are isolated synthetic fixtures."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime,timedelta
import sys,json,unittest,importlib.util
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(Path(__file__).parent))
from assemble import prepare,bind,read_json,validate_assumptions,HERE,sensitivity_catalog
from src.jp_milp.config import InputError,digest
from src.jp_milp.inputs import validate
from src.jp_milp.activation import positive_normal
from src.jp_milp.core import solve_window
from tests.test_jp_milp import fixture,open_gates

def synthetic_runtime():
    test=fixture('HV_SPOT_S1_T1')
    return dict(profile_classification='SYNTHETIC_PIPELINE_TEST',asset=test['asset'],
                fcr_control=dict(response_model='BID_SCALED_NORMALIZED_CURVE',deadband_up_hz=.01,deadband_down_hz=.01,span_up_hz=.19,span_down_hz=.19,basis='SYNTHETIC_TEST_ONLY_NOT_PROJECT_CONTROL'),
                composite_offer=dict(asset_version=test['asset']['version'],evidence='SYNTHETIC_TEST_MENU_ONLY',full_inner_scope='FULL_CAPABILITY_NOT_MERELY_DELIVERABLE',bid_rules=test['capacity_blocks'][0]['bid_rules'],candidates=test['capacity_blocks'][0]['candidates']),initial_frozen={})

class AssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a=read_json(HERE/'assumptions.json');cls.rows,cls.coeff,cls.meta=prepare(cls.a)

    def test_reference_definition_and_no_asset_in_regional_data(self):
        self.assertEqual(self.meta['references']['fit_halfhours'],1440)
        self.assertFalse(self.meta['references']['is_observed_callable_capacity'])
        self.assertNotIn('asset',self.meta)
        self.assertEqual(len(self.rows),1488)
        self.assertEqual(len([r for r in self.rows if r['period_role']=='observation']),48)

    def test_fcr_binding_and_analytic_energy(self):
        data=bind(self.rows,self.meta,self.a,synthetic_runtime(),'HV_SPOT_FCR')
        self.assertEqual(validate(data)['status'],'READY_FOR_CONDITIONAL_SOLVE')
        self.assertEqual(data['classification'],'SYNTHETIC_VALIDATION')
        for raw,row in zip(self.rows,data['intervals']):
            self.assertEqual(row['payment']['recognition_up'],0.)
            self.assertEqual(row['payment']['recognition_down'],0.)
            self.assertIsNone(row['payment']['signed_price_up'])
            self.assertIsNone(row['payment']['signed_price_down'])
            m=raw['frequency_mean_hz'];s=raw['frequency_scale_proxy_hz'];d=.01;b=.19
            expected=(positive_normal(-m-d,s)-positive_normal(-m-d-b,s))/b
            self.assertAlmostEqual(sum(v['weight']*v['gamma_up'] for v in row['states']),expected,places=10)
            self.assertLessEqual(max(abs(v['f']) for v in row['states']),1+1e-12)
        self.assertEqual(len(data['capacity_blocks']),1488)
        self.assertAlmostEqual(data['annual_budgets_efc']['2026'],600*30/365)
        self.assertTrue(all(o['market']=='DA' for o in data['spot_orders']))

    def test_composite_binding_and_single_common_price(self):
        data=bind(self.rows,self.meta,self.a,synthetic_runtime(),'HV_SPOT_S1_T1')
        validate(data)
        for r in data['intervals']:
            self.assertAlmostEqual(sum(s['weight']*s['s'] for s in r['states']),0,places=10)
            self.assertAlmostEqual(sum(s['weight']*s['t'] for s in r['states']),r['joint_metadata']['edc_center'],places=10)
        for block in data['capacity_blocks']:
            self.assertEqual(block['candidates'][0]['common'],max(block['candidates'][0]['s'],block['candidates'][0]['t']))
            self.assertEqual(len(block['price_jpy_mw_30min']),1)

    def test_missing_asset_control_and_menu_rejected(self):
        with self.assertRaises((InputError,TypeError)):
            bind(self.rows,self.meta,self.a,read_json(HERE/'runtime_template.json'),'HV_SPOT_FCR')
        profile=synthetic_runtime();profile['fcr_control']['span_up_hz']=None
        with self.assertRaises(InputError):bind(self.rows,self.meta,self.a,profile,'HV_SPOT_FCR')
        profile=synthetic_runtime();profile['composite_offer']=None
        with self.assertRaises(InputError):bind(self.rows,self.meta,self.a,profile,'HV_SPOT_S1_T1')

    def test_stale_and_merely_deliverable_menu_rejected(self):
        p=synthetic_runtime();p['composite_offer']['asset_version']='different_station'
        with self.assertRaises(InputError):bind(self.rows,self.meta,self.a,p,'HV_SPOT_S1_T1')
        p=synthetic_runtime();p['composite_offer']['full_inner_scope']='DELIVERABLE_ONLY'
        with self.assertRaises(InputError):bind(self.rows,self.meta,self.a,p,'HV_SPOT_S1_T1')

    def test_payment_sign_not_absolute_and_raw_energy_not_added_to_cash(self):
        for r in self.rows:
            self.assertEqual(r['payment']['signed_price_down'],-r['payment']['signed_price_up'])
            self.assertIn('NOT_V1_V2',r['payment']['mapping_id'])
        for r in self.coeff:
            self.assertIn('NOT_MEASURED',r['classification'])

    def test_sensitivity_assumptions_are_separate_and_valid(self):
        original=digest(self.a);variants=sensitivity_catalog(self.a,self.meta)
        self.assertEqual(len(variants),14)
        for name,v in variants.items():validate_assumptions(v)
        self.assertEqual(digest(self.a),original)
        v=deepcopy(self.a);v['composite']['t1_share_A_up_down']=[1.1,1.1]
        with self.assertRaises(InputError):validate_assumptions(v)

    def test_state_ordering_matches_original_solver_including_incomparable_states(self):
        spec=importlib.util.spec_from_file_location('src.jp_milp._pre_ordering_core',HERE/'core_before_state_ordering.py')
        original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
        for scenario in ('HV_SPOT_S1_T1',):
            data=open_gates(fixture(scenario,n=8))
            if scenario=='HV_SPOT_S1_T1':
                for row in data['intervals']:
                    row['states']=[dict(weight=.5,f=0.,s=.5,t=-.2),dict(weight=.5,f=0.,s=-.5,t=.4)]
            else:
                for row in data['intervals']:
                    row['states']=[dict(weight=.4,f=.2,s=0.,t=0.),dict(weight=.2,f=0.,s=0.,t=0.),dict(weight=.4,f=-.2,s=0.,t=0.)]
            before=original.solve_window(data);after=solve_window(data)
            self.assertAlmostEqual(before['metrics']['objective_jpy'],after['metrics']['objective_jpy'],places=3)
            self.assertEqual(after['audit']['status'],'PASS')
            # Constant-power elimination/cache may now remove redundant rows;
            # objective equivalence and independent physical audit are invariant.
            if scenario=='HV_SPOT_S1_T1':self.assertLessEqual(after['metrics']['rows'],before['metrics']['rows'])
            else:self.assertGreater(after['metrics']['rows'],before['metrics']['rows'])

    def test_both_scenarios_synthetic_short_window_integration(self):
        # Full real regional inputs, synthetic device. This is NOT station revenue.
        results={}
        for scenario in ('HV_SPOT_FCR','HV_SPOT_S1_T1'):
            data=bind(self.rows[:96],self.meta,self.a,synthetic_runtime(),scenario)
            data['solver'].update(time_limit_seconds=120.,mip_rel_gap=1e-6)
            result=solve_window(data)
            self.assertEqual(len(result['intervals']),96)
            self.assertEqual(result['audit']['status'],'PASS')
            results[scenario]=dict(classification='SYNTHETIC_PIPELINE_TEST_NOT_FORMAL_REVENUE',metrics=result['metrics'],audit=result['audit'],nonzero_capacity_orders=sum(isinstance(v,dict) and v['common']>1e-8 for v in result['orders'].values()))
            self.assertGreater(results[scenario]['nonzero_capacity_orders'],0)
        (HERE/'integration_validation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':unittest.main(verbosity=2)
