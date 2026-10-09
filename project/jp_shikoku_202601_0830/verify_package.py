"""Independent checks of assembled dates, exclusion gates and prior June values."""
from pathlib import Path
from datetime import datetime,timedelta
from collections import Counter,defaultdict
import csv,json,hashlib

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/processed/JP/shikoku_20260101_20260830_expost_v1'
def read(name,base=OUT):
    with (base/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
    checks=[]
    def check(condition,label):
        assert condition,label
        checks.append(label)
    manifest=json.loads((OUT/'package_manifest.json').read_text())
    for name,sha in manifest['files'].items():check(hashlib.sha256((OUT/name).read_bytes()).hexdigest()==sha,'package hash '+name)
    for row in json.loads((OUT/'source_manifest.json').read_text()):check(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'],'source hash '+row['path'])
    rows=read('regional_30min.csv');times=[r['timestamp_jst'] for r in rows]
    check(len(rows)==11664 and len(set(times))==11664,'complete unique 243-day grid')
    check(times[0]=='2026-01-01T00:00:00+09:00' and times[-1]=='2026-08-31T23:30:00+09:00','exact endpoint coverage')
    check(all(datetime.fromisoformat(b)-datetime.fromisoformat(a)==timedelta(minutes=30) for a,b in zip(times,times[1:])),'continuous halfhours')
    check(Counter(r['period_role'] for r in rows)=={'formal':11616,'observation':48},'formal versus observation separation')
    native={r['native_block_id']:r for r in read('capacity_native_blocks.csv')};expanded=read('capacity_30min.csv');groups=defaultdict(list)
    check(len(expanded)==69984,'six complete product grids')
    check(len({(r['timestamp_JST'],r['product']) for r in expanded})==69984,'no duplicate capacity rows')
    for r in expanded:groups[r['native_block_id']].append(r)
    for key,rr in groups.items():
        parent=native[key]
        assert len(rr)==int(float(parent['duration_h'])*2)
        assert all(r['native_block_start']==parent['timestamp_JST'] and r['is_independent_offer']=='False' for r in rr)
        for r in rr:
            for side in ('source','TSO'):
                price=r[f'{side}_price_candidate_JPY_MW_30min'];raw=r[f'avg_price_{side}_JPY_kW_30min'];valid=r[f'{side}_price_observation_valid']=='True'
                assert (float(price)==float(raw)*1000 if valid else price=='')
    checks.append('all native blocks and price conversion preserved; no-award prices null')
    inputs=read('activation_input_template.csv');bytime={r['timestamp_jst']:r for r in rows}
    for r in inputs:
        raw=bytime[r['timestamp_jst']];good=raw['activation_statistics_usable']=='True'
        if not good:
            assert all(r[f]=='' for f in ('frequency_mean_hz','frequency_equivalent_scale_hz','lfc_mean_mw','lfc_equivalent_scale_mw'))
            assert r['input_status'].startswith('BLOCKED')
        assert r['fcr_activation_price_up']==r['fcr_activation_price_down']==''
        assert all(r[f]=='' for f in r if f.startswith('alpha_'))
    checks.append('missing and quarantined inputs blocked; no invented alpha or FCR payment')
    oldbase=ROOT/'data/processed/JP/shikoku_202606_20260701_expost'
    count=0
    for old in read('regional_30min.csv',oldbase):
        new=bytime[old['timestamp_jst']]
        for k,v in old.items():
            if 'source' in k or 'update' in k or k=='period_role':continue
            if v=='':assert new[k]==''
            else:
                try:assert abs(float(new[k])-float(v))<=1e-8
                except ValueError:assert new[k]==v
            count+=1
    checks.append(f'{count} overlapping June/July1 regional fields agree with prior verified package')
    capidx={(r['timestamp_JST'],r['product']):r for r in expanded}
    for old in read('capacity_30min.csv',oldbase):
        if old['product']=='F_OFFLINE':continue
        new=capidx[old['timestamp_JST'],old['product']]
        for side in ('source','TSO'):
            assert new[f'{side}_price_candidate_JPY_MW_30min']==old[f'{side}_price_candidate_JPY_MW_30min']
    checks.append('June/July1 six-product prices agree with prior verified package')
    status=json.loads((OUT/'readiness.json').read_text())
    check(status['runnable_model_input'] is False and status['formal_solve_performed'] is False,'no false ready/solved claim')
    check(sum(r['activation_statistics_usable']=='True' for r in rows if r['period_role']=='formal')==5926,'formal usable statistics count')
    check(all(r['activation_statistics_usable']=='False' for r in rows if r['period_role']=='observation'),'observation day not silently filled')
    report=dict(status='PASS',check_count=len(checks),checks=checks,formal_solve_performed=False)
    (Path(__file__).parent/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(status='PASS',check_count=len(checks),overlap_numeric_and_text_fields=count)))
if __name__=='__main__':main()
