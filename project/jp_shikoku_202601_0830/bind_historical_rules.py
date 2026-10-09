"""Bind nominal historical EPRX schedules to evidence; no optimizer changes.

Each original block remains one obligation. Segments are reporting partitions,
not permission to reset SOC, budgets, frozen orders or discard observation data.
"""
from pathlib import Path
from datetime import datetime,timedelta
from collections import Counter
import csv,json,hashlib,shutil

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/processed/JP/shikoku_20260101_20260830_expost_v1'
OUT=ROOT/'data/processed/JP/shikoku_20260101_20260830_rules_v2'
RULES=[
 dict(id='S3_20250401',start='2026-01-01',end='2026-03-14',effective_date='2025-04-01',file='E38_9e43ab56febd.txt',url='https://www.eprx.or.jp/outline/docs/kitei_250401.pdf',capacity_location='Composite booklet Articles 27-32 PDF pp278-281; tertiary2 Articles29-32 PDF pp68-70',settlement_location='Articles42-46 PDF pp43-47',metering_scope='POI_PRE_DEVICE_METERING_RULES'),
 dict(id='S4_20260314',start='2026-03-14',end='2026-04-01',effective_date='2026-03-14',file='E34_c50d1df600d2.txt',url='https://www.eprx.or.jp/outline/docs/kitei_ver.16.1_260314.pdf',capacity_location='Composite booklet Articles29-32 PDF pp333-336',settlement_location='Articles42-46 PDF pp56-67',metering_scope='DEVICE_OR_POI_CONTRACT_MAPPING_REQUIRED'),
 dict(id='S5_20260401',start='2026-04-01',end='2026-07-01',effective_date='2026-04-01',file='E35_88290aca54ce.txt',url='https://www.eprx.or.jp/outline/docs/kitei_ver.17_260401.pdf',capacity_location='Composite booklet Articles29-32 PDF pp335-338',settlement_location='Articles42-46 PDF pp57-68',metering_scope='DEVICE_OR_POI_CONTRACT_MAPPING_REQUIRED'),
 dict(id='S6_20260701',start='2026-07-01',end='2026-09-01',effective_date='2026-07-01',file='E02_1c1881b3a21a.txt',url='https://www.eprx.or.jp/outline/docs/kitei_ver.18_260701.pdf',capacity_location='Composite booklet Articles29-32 PDF pp335-338',settlement_location='Articles42-46 PDF pp57-68',metering_scope='DEVICE_OR_POI_CONTRACT_MAPPING_REQUIRED')]

def choose(t):
    found=[r for r in RULES if r['start']<=t[:10]<r['end']]
    assert len(found)==1
    return found[0]

def clock(t,product):
    day=datetime.fromisoformat(t).replace(hour=0,minute=0,second=0,microsecond=0)
    weekly=t[:10]<'2026-03-14' and product!='R'
    if weekly:
        saturday=day-timedelta(days=(day.weekday()-5)%7)
        opening=(saturday-timedelta(days=5)).replace(hour=14)
        closing=(saturday-timedelta(days=4)).replace(hour=14)
        return opening,closing,closing.replace(hour=15),3.,saturday.isoformat(),(saturday+timedelta(days=7)).isoformat()
    opening=(day-timedelta(days=1)).replace(hour=12 if t[:10]<'2026-03-14' else 11,minute=0 if t[:10]<'2026-03-14' else 30)
    closing=opening.replace(hour=14,minute=0)
    return opening,closing,closing.replace(hour=15),.5,day.isoformat(),(day+timedelta(days=1)).isoformat()

def read(name):
    with (BASE/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def save(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    assert not OUT.exists(),'Preserve previous releases'
    original=json.loads((BASE/'package_manifest.json').read_text())
    for name,digest in original['files'].items():assert sha(BASE/name)==digest
    native=read('capacity_native_blocks.csv');bindings={};checks=[]
    for r in native:
        t=r['timestamp_JST'];rule=choose(t)
        opening,closing,result,hours,weekstart,weekend=clock(t,r['product'])
        assert float(r['duration_h'])==hours,(t,r['product'])
        delivery=datetime.fromisoformat(t);end=delivery+timedelta(hours=hours)
        assert end<=datetime.fromisoformat(rule['end']+'T00:00:00+09:00')
        assert opening<closing<result<delivery
        bindings[r['native_block_id']]=dict(native_block_id=r['native_block_id'],product=r['product'],rule_regime=rule['id'],
            delivery_start=t,delivery_end_exclusive=end.isoformat(),native_duration_h=hours,
            procurement_mode='WEEKLY_SATURDAY_FRIDAY' if hours==3 else 'DAY_AHEAD',
            auction_delivery_start=weekstart,auction_delivery_end_exclusive=weekend,
            bid_open_nominal_jst=opening.isoformat(),gate_nominal_jst=closing.isoformat(),result_deadline_nominal_jst=result.isoformat(),
            actual_result_timestamp=None,clock_basis='RULE_NOMINAL_NOT_ACTUAL_EVENT_LOG',exception_calendar_verified=False,
            evidence_url=rule['url'],evidence_location=rule['capacity_location'],
            gate_before_run_start=closing<datetime.fromisoformat('2026-01-01T00:00:00+09:00'),
            required_calendar_days_from_gate_to_delivery_end=(end.date()-closing.date()).days+1,
            solver_gate_policy_compatible=hours==.5,
            cash_capacity_unit='JPY/MW/30min',block_halfhour_count=int(hours*2),
            quantity_tied_across_block=True)
    # Non-tautological boundary tests: Friday belongs to preceding Saturday;
    # Saturday starts new delivery week, including a gate in the previous year.
    samples=[('2026-01-01T00:00:00+09:00','F','2025-12-23T14:00:00+09:00',3.),
             ('2026-01-03T00:00:00+09:00','C','2025-12-30T14:00:00+09:00',3.),
             ('2026-03-13T21:00:00+09:00','F','2026-03-03T14:00:00+09:00',3.),
             ('2026-03-14T00:00:00+09:00','F','2026-03-13T14:00:00+09:00',.5),
             ('2026-01-01T00:00:00+09:00','R','2025-12-31T14:00:00+09:00',.5)]
    for t,p,g,h in samples:
        b=bindings['SHIKOKU/'+p+'/'+t];assert b['gate_nominal_jst']==g and b['native_duration_h']==h
    checks.append('Five year/week/reform boundary examples PASS')
    regional=read('regional_30min.csv');expanded=read('capacity_30min.csv')
    for r in regional:
        rule=choose(r['timestamp_jst']);assert r['rule_regime']==rule['id']
        day=r['timestamp_jst'][:10]
        r.update(rule_evidence_url=rule['url'],metering_rule_scope=rule['metering_scope'],settlement_evidence_location=rule['settlement_location'],
            lfc_operation_phase='PRE_WIDE_OPERATION' if day<'2026-04-13' else 'WIDE_TRIAL' if day<'2026-04-28' else 'FORMAL_START_DAY_EXACT_SWITCH_TIME_UNVERIFIED' if day=='2026-04-28' else 'WIDE_FORMAL_OPERATION',
            lfc_start_basis='OCCTO63_20260915_p2_p13_p14; first CSV nonblank 20260428T1300 is not proof of switching time',
            rule_binding_status='VERSION_AND_NOMINAL_CLOCK_BOUND_NOT_SETTLEMENT_CALIBRATED')
    for r in expanded:
        b=bindings[r['native_block_id']];assert b['rule_regime']==r['rule_regime']
        for k in ('gate_nominal_jst','bid_open_nominal_jst','result_deadline_nominal_jst','procurement_mode','quantity_tied_across_block','evidence_url','clock_basis'):r[k]=b[k]
    for r in native:
        b=bindings[r['native_block_id']]
        for k in ('gate_nominal_jst','bid_open_nominal_jst','result_deadline_nominal_jst','procurement_mode','quantity_tied_across_block','evidence_url','clock_basis'):r[k]=b[k]
    checks.extend(['Every native block matches applicable historical duration and regime','All original rows, values, flags and block IDs retained','Auction deadlines precede all deliveries','No block straddles a rule-version boundary'])
    OUT.mkdir(parents=True)
    for p in BASE.iterdir():
        if p.is_file() and p.name not in ('package_manifest.json','regional_30min.csv','capacity_native_blocks.csv','capacity_30min.csv','readiness.json'):shutil.copyfile(p,OUT/p.name)
    write(OUT/'regional_30min.csv',regional);write(OUT/'capacity_native_blocks.csv',native);write(OUT/'capacity_30min.csv',expanded)
    write(OUT/'historical_capacity_events.csv',list(bindings.values()))
    segments=[]
    for rule in RULES:
        rr=[r for r in regional if r['rule_regime']==rule['id']];nn=[r for r in native if r['rule_regime']==rule['id']]
        folder=OUT/'segments'/rule['id'];folder.mkdir(parents=True)
        write(folder/'regional_30min.csv',rr);write(folder/'capacity_native_blocks.csv',nn)
        write(folder/'historical_capacity_events.csv',[b for b in bindings.values() if b['rule_regime']==rule['id']])
        segments.append(dict(rule_regime=rule['id'],start=rule['start'],end_exclusive=rule['end'],formal_halfhours=sum(r['period_role']=='formal' for r in rr),
            observation_halfhours=sum(r['period_role']=='observation' for r in rr),native_capacity_rows=len(nn),
            usable_frequency_lfc_halfhours=sum(r['activation_statistics_usable']=='True' for r in rr),
            inherited_state_required=True,standalone_ready=False))
    assert sum(s['formal_halfhours'] for s in segments)==11616 and sum(s['observation_halfhours'] for s in segments)==48
    checks.append('Four segments partition all 11664 halfhours exactly')
    save(OUT/'rule_versions.json',RULES);write(OUT/'segment_summary.csv',segments)
    status=json.loads((BASE/'readiness.json').read_text());status.update(status='HISTORICAL_VERSIONS_AND_NOMINAL_EVENTS_BOUND_NOT_RUNNABLE',
        history_binding_complete_for=['version_date','native_block_duration','nominal_bid_window','nominal_result_deadline','settlement_article_reference'],
        history_binding_excludes=['actual exceptional auction timestamps','station-specific settlement coefficients','fees and penalties cash implementation'],
        weekly_native_blocks=sum(b['native_duration_h']==3 for b in bindings.values()),
        events_before_formal_start=sum(b['gate_before_run_start'] for b in bindings.values()),
        max_calendar_lookahead_days=max(b['required_calendar_days_from_gate_to_delivery_end'] for b in bindings.values()),
        optimizer_weekly_gate_support=False,soc_and_frozen_orders_must_continue_across_segments=True)
    status['unresolved']=[s for s in status['unresolved'] if not s.startswith('Historical native blocks and gates require')]
    status['unresolved'].append('Nominal historical gates are bound; weekly-event solver horizon and exceptional event verification remain outside this data binding')
    save(OUT/'readiness.json',status)
    sources=json.loads((OUT/'source_manifest.json').read_text())
    for rule in RULES:
        p=ROOT/'countries/JP/research/extracted'/rule['file']
        sources.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),url=rule['url'],effective_date=rule['effective_date'],access_date='2026-10-05 local archived official evidence recheck'))
    sources.append(dict(path=(BASE/'package_manifest.json').relative_to(ROOT).as_posix(),sha256=sha(BASE/'package_manifest.json')))
    save(OUT/'source_manifest.json',sources)
    save(OUT/'binding_validation.json',dict(status='PASS',checks=checks,rows_preserved=len(regional),native_blocks_bound=len(bindings),formal_solve_performed=False))
    save(OUT/'package_manifest.json',dict(builder_sha256=sha(Path(__file__)),files={p.relative_to(OUT).as_posix():sha(p) for p in sorted(OUT.rglob('*')) if p.is_file()}))
    print(json.dumps(dict(status='PASS',segments=segments,weekly_blocks=status['weekly_native_blocks'],lookahead_days=status['max_calendar_lookahead_days']),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
