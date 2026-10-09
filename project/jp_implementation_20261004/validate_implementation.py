"""Repeatable synthetic acceptance and measured solver/discretization evidence."""
from copy import deepcopy
from pathlib import Path
import argparse
import importlib.util
import json
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec=importlib.util.spec_from_file_location('jp_test_fixture', ROOT/'tests/test_jp_milp.py')
fixtures=importlib.util.module_from_spec(spec); spec.loader.exec_module(fixtures)
from src.jp_milp.activation import fcr_states
from src.jp_milp.rolling import run, atomic_json, code_identity
from src.jp_milp.sensitivity import suite
from src.jp_milp.sources import kyushu_lfc, kyushu_edc_related, kyushu_ics
from src.jp_milp.inputs import validate
from src.jp_milp.core import solve_window


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output', required=True); args=parser.parse_args()
    out=Path(args.output); out.mkdir(parents=True, exist_ok=False)
    tests=unittest.defaultTestLoader.loadTestsFromModule(fixtures)
    with (out/'tests.txt').open('w', encoding='utf-8') as log:
        result=unittest.TextTestRunner(stream=log, verbosity=2).run(tests)
    if not result.wasSuccessful():
        raise RuntimeError('Regression tests failed')
    cases={}
    for scenario in ('LV_FCR', 'HV_SPOT_FCR', 'HV_SPOT_S1_T1'):
        data=fixtures.fixture(scenario, n=144, block_size=6)
        atomic_json(out/(scenario+'_synthetic_input.json'), data)
        cases[scenario]=run(data, '2026-06-04T00:00:00+09:00', out/scenario)
    base=fixtures.fixture('HV_SPOT_S1_T1', n=144, block_size=6)
    deviations={r['start']: [(.5, -.2), (.5, .2)] for r in base['intervals']}
    atomic_json(out/'synthetic_edc_deviations.json', deviations)
    sensitivities=suite(base, '2026-06-04T00:00:00+09:00', deviations, out/'composite_sensitivity')
    refinement={}
    for count in (11, 21, 41):
        data=fixtures.fixture('HV_SPOT_FCR', n=144, block_size=6)
        states=fcr_states(.01, .035, .01, .012, .05, .06, 1., 1., count)
        for row in data['intervals']:
            row['states']=deepcopy(states)
        data['assumption_version']+=f'/normal_frequency_{count}'
        refinement[str(count)]=run(data, '2026-06-04T00:00:00+09:00', out/f'fcr_bins_{count}')
        refinement[str(count)]['actual_states']=len(states)
    raw={}
    paths=[('lfc', ROOT/'project/jp_activation_downloads_20261001/samples/kyushu_lfc_202606_4c5f53588b32.csv'),
           ('edc', ROOT/'project/jp_activation_downloads_20261001/samples/kyushu_jukyu_202606_259b239ae928.zip'),
           ('ics', ROOT/'data/raw/JP/activation_sources_20261001/ics_basis_202606.csv')]
    for name, path in paths:
        if path.exists():
            r=(kyushu_lfc(path) if name == 'lfc' else kyushu_ics(path) if name == 'ics' else
               kyushu_edc_related(path, '11120_TSO9_0_202606_20260812132500030.csv'))
            raw[name]=dict(rows=len(r['rows']), first=r['rows'][0], source=r['source'], status=r['status'])
        else:
            raw[name]=dict(status='FILE_NOT_PRESENT')
    summary=dict(code_sha256=code_identity(), tests=result.testsRun, tests_passed=result.wasSuccessful(),
                 cases=cases, sensitivities=sensitivities, refinement=refinement, source_readers=raw,
                 historical_calibration_complete=False, official_rules_changed=False)
    atomic_json(out/'validation.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
