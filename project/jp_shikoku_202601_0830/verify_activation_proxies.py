"""Verify donor provenance, fill arithmetic, sensitivity scope and immutability."""
from pathlib import Path
from collections import defaultdict
import csv,json,hashlib,math

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/processed/JP/shikoku_20260101_20260830_rules_v2'
OUT=ROOT/'data/processed/JP/shikoku_20260101_20260830_proxy_v3'
KEYS=('frequency_mean_hz','frequency_equivalent_scale_hz','lfc_mean_mw','lfc_equivalent_scale_mw')
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
    checks=[]
    def check(condition,text):
        assert condition,text
        checks.append(text)
    original=json.loads((BASE/'package_manifest.json').read_text())
    for name,h in original['files'].items():
        check(hashlib.sha256((BASE/name).read_bytes()).hexdigest()==h,'original unchanged '+name)
        if name!='readiness.json':check((BASE/name).read_bytes()==(OUT/name).read_bytes(),'raw copied unchanged '+name)
    rows=read(OUT/'activation_statistics_base_proxy.csv');raw={r['timestamp_jst']:r for r in read(BASE/'activation_input_template.csv')}
    observed={r['timestamp_jst'] for r in rows if r['statistical_origin']=='OBSERVED_STATISTICS'}
    check(len(rows)==len(raw)==11664 and len(observed)==5926,'full grid and observed counts')
    donors=defaultdict(list)
    for r in read(OUT/'proxy_donor_mapping.csv'):
        assert r['donor_timestamp_jst'] in observed
        assert r['donor_timestamp_jst'][:10] not in ('2026-07-31','2026-08-31')
        assert r['target_slot']==r['donor_slot'] and r['target_day_type']==r['donor_day_type']
        donors[r['target_timestamp_jst']].append(r)
    check(len(donors)==5738,'all and only imputed targets have donors')
    for r in rows:
        t=r['timestamp_jst'];checkable=raw[t]
        assert r['model_statistics_complete']=='True'
        assert all(math.isfinite(float(r[k])) for k in KEYS)
        assert all(float(r[k])>=0 for k in (KEYS[1],KEYS[3]))
        assert r['activation_statistics_usable']==checkable['activation_statistics_usable']
        assert r['fcr_activation_price_up']==r['fcr_activation_price_down']==''
        assert r['edc_A_mwh']==checkable['edc_A_mwh'] and r['edc_B_mwh']==checkable['edc_B_mwh']
        if t in observed:
            assert all(float(r[k])==float(checkable[k]) for k in KEYS)
        else:
            dd=donors[t];assert len(dd)==len({d['donor_timestamp_jst'] for d in dd})==5
            assert abs(sum(float(d['weight']) for d in dd)-1)<1e-12
            for k in KEYS:assert abs(float(r[k])-sum(float(d['weight'])*float(d[k]) for d in dd))<1e-10
    checks.append('Every proxy reconstructed from five valid same-slot/day-type donors; observed statistics exact')
    checks.append('Nonnegative finite scales; EDC, raw flags and zero FCR payment convention preserved')
    baseline={r['timestamp_jst']:r for r in rows}
    for variant in json.loads((OUT/'scenario_index.json').read_text()):
        vv=read(OUT/variant['path']);assert len(vv)==11664
        for r in vv:
            b=baseline[r['timestamp_jst']]
            for k in KEYS:
                multiplier=(variant['early_lfc_k'] if k.startswith('lfc') and b['proxy_reason']=='EARLY_MISSING'
                            else variant['frequency_proxy_scale_q'] if k=='frequency_equivalent_scale_hz' and b['statistical_origin']=='EX_POST_MATCHED_PROXY' else 1)
                assert abs(float(r[k])-float(b[k])*multiplier)<1e-10
        checks.append('Sensitivity scope and arithmetic '+variant['name'])
    status=json.loads((OUT/'readiness.json').read_text())
    check(not status['runnable_model_input'] and not status['formal_solve_performed'],'no false runnable or actual revenue claim')
    for name,h in json.loads((OUT/'package_manifest.json').read_text())['files'].items():assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==h
    checks.append('New package hashes verified')
    result=dict(status='PASS',checks=checks,check_count=len(checks),filled_targets=5738,donor_mapping_rows=sum(map(len,donors.values())))
    (Path(__file__).parent/'proxy_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='checks'}))
if __name__=='__main__':main()
