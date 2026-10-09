"""Strict EV offline quote binding; HV input paths are untouched."""
from pathlib import Path
from copy import deepcopy
import json, hashlib
from src.jp_milp.config import require
ROOT=Path(__file__).resolve().parents[2]
PACK=ROOT/'data/processed/JP/shikoku_ev_offline_20260101_0830_v1'

def file_sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def overlay(prepared,events,package=PACK):
 manifest=json.loads((package/'package_manifest.json').read_text(encoding='utf-8'))
 require(manifest['market_product']=='F_OFFLINE' and manifest['area']=='四国','EV requires Shikoku offline package')
 for name,expected in manifest['files'].items():require(file_sha(package/name)==expected,'Offline package fingerprint mismatch: '+name)
 require(file_sha(ROOT/manifest['source_manifest'])==manifest['source_manifest_sha256'],'Offline source manifest changed')
 source=json.loads((ROOT/manifest['source_manifest']).read_text(encoding='utf-8'))
 for entry in source['entries']:require(file_sha(ROOT/entry['path'])==entry['sha256'],'Offline raw snapshot changed')
 values=json.loads((package/'offline_30min.json').read_text(encoding='utf-8'))
 quotes={x['timestamp_jst']:x for x in values}
 require(len(quotes)==len(values),'Duplicate offline quote')
 require(set(quotes)=={x['start'] for x in prepared['intervals']},'EV offline timeline mismatch; no F fallback')
 data=deepcopy(prepared);clocks=deepcopy(events)
 for r in data['intervals']:
  q=quotes[r['start']]
  require(q['market_product']=='F_OFFLINE' and q['source_product_label']=='一次オフライン' and q['archive_family']=='1-1' and q['price_side']=='電源属地別','EV offline provenance mismatch')
  require(type(q['market_enabled']) is bool and q['market_enabled']==q['price_observation_valid'],'Offline availability inconsistency')
  require(q['market_enabled']==(q['source_award_mw']>0),'Offline award/availability inconsistency')
  if q['market_enabled']:
   require(q['price_jpy_mw_30min']==1000*q['source_average_raw_jpy_kw_30min'],'Offline price unit mismatch')
  else:require(q['price_jpy_mw_30min'] is None and bool(q['disabled_reason']),'Unavailable price must remain null in research input')
  r['offline_quote']=q
  # Numeric zero is an objective placeholder only for a capacity forced to zero.
  r['capacity_price']['fcr']=q['price_jpy_mw_30min'] if q['market_enabled'] else 0.
  ev=clocks[r['start']]
  require(ev['gate_nominal_jst']==q['gate_nominal_jst'] and ev['result_deadline_nominal_jst']==q['result_deadline_nominal_jst'] and int(ev['block_halfhour_count'])==q['native_halfhours'],'Offline historical clocks mismatch')
  ev.update(native_block_id=q['native_block_id'],product='F_OFFLINE')
 data['metadata']['ev_offline_binding']=dict(package_manifest=manifest,package_manifest_sha256=file_sha(package/'package_manifest.json'),binding_code_sha256=file_sha(Path(__file__)))
 return data,clocks

def apply_blocks(data,prepared):
 """Enforce offline provenance and availability after the generic FCR assembler."""
 quotes={r['start']:r['offline_quote'] for r in prepared['intervals']}
 for b in data['capacity_blocks']:
  qs=[quotes[t] for t in b['intervals']]
  require(all(q['native_block_id']==b['id'] and q['market_product']=='F_OFFLINE' for q in qs),'EV capacity identity must be offline')
  require(len({q['market_enabled'] for q in qs})==1,'Availability varies inside a native offline block')
  b.update(market_product='F_OFFLINE',market_enabled=qs[0]['market_enabled'],
   market_disabled_reason=qs[0]['disabled_reason'],
   price_evidence='EPRX_1_1_SOURCE_AVERAGE_AGGREGATE_PROXY/'+qs[0]['archive_sha256']+'/'+qs[0]['member_sha256'])
  for t,q in zip(b['intervals'],qs):
   expected=q['price_jpy_mw_30min'] if q['market_enabled'] else 0.
   require(b['price_jpy_mw_30min'][t]==expected,'EV offline price binding changed')
 data['capacity_price_binding']='EV_OFFLINE_1_1_SOURCE_STRICT_V1'
 data['provenance'].append(dict(ev_offline=data.get('capacity_price_binding'),quote_metadata=prepared['metadata']['ev_offline_binding'],no_ordinary_primary_fallback=True))
 return data
