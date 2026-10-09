"""External alternatives and fixed-commitment stress, never optimizer-selected assumptions."""
from copy import deepcopy
from pathlib import Path
import json
from .activation import composite_states
from .config import require
from .rolling import run, atomic_json


def composite_variant(data, theta, deviations, coupling):
    result=deepcopy(data)
    require(result['scenario'] == 'HV_SPOT_S1_T1', 'Composite scenario required')
    for row in result['intervals']:
        meta=row['joint_metadata']; marginal=meta['lfc_marginal']
        perturbations=deviations[row['start']]
        row['states']=composite_states(marginal, meta['edc_center'], perturbations, theta, coupling)
        meta.update(theta=theta, coupling=coupling, edc_deviations=perturbations)
    result['assumption_version']+=f'/theta={theta}/coupling={coupling}'
    return result


def suite(data, formal_end, deviations, output_dir):
    require(all(any(w > 0 and abs(x) > 1e-12 for w, x in deviations[r['start']]) for r in data['intervals']),
            'Mandatory EDC fluctuation sensitivity requires nonzero supported perturbations')
    out=Path(output_dir); out.mkdir(parents=True, exist_ok=False)
    zeros={r['start']: [(1., 0.)] for r in data['intervals']}
    variants={'base': composite_variant(data, 0., zeros, 'independent'),
              'mean_added': composite_variant(data, 1., zeros, 'independent')}
    for coupling in ('independent', 'same', 'opposite'):
        variants['edc_'+coupling]=composite_variant(data, 0., deviations, coupling)
    baseline=run(variants['base'], formal_end, out/'base_reoptimized')
    require(baseline['status'] == 'COMPLETE', 'Baseline incomplete; cannot claim completed sensitivity')
    committed={}; last=None
    for path in sorted((out/'base_reoptimized'/'windows').glob('*.json')):
        tx=json.loads(path.read_text(encoding='utf-8'))
        committed.update(tx['next_state']['frozen']); last=tx
    # Include last planned observation orders so stress cannot purchase free recovery.
    committed.update(last['window']['orders'])
    results={'base': {'reoptimized': baseline}}
    for name, variant in variants.items():
        if name == 'base':
            continue
        stress=deepcopy(variant); stress['initial_frozen']=deepcopy(committed)
        results[name]=dict(reoptimized=run(variant, formal_end, out/(name+'_reoptimized')),
                           fixed_commitments=run(stress, formal_end, out/(name+'_fixed')))
    atomic_json(out/'comparison.json', results)
    return results
