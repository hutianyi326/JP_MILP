"""Preserve failed run; reuse only its verified prefix before the failed commitment."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,gzip,shutil
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from src.jp_milp.config import require,digest
SOURCE=ROOT/'outputs/JP/lv_offline_20261005_v1/LV_FCR'
TARGET=ROOT/'outputs/JP/lv_offline_20261005_v2/LV_FCR'

def main():
 require(not TARGET.exists(),'New version required')
 manifest=json.loads((SOURCE/'manifest.json').read_text(encoding='utf-8'))
 parent=digest(manifest);state=manifest['initial_state'];paths=[]
 for p in sorted((SOURCE/'windows').glob('*.json.gz')):
  with gzip.open(p,'rt',encoding='utf-8') as stream:tx=json.load(stream)
  if tx['window']['start']>='2026-08-26T00:00:00+09:00':break
  sha=tx.pop('sha256');require(sha==digest(tx) and tx['parent']==parent and tx['sequence']==len(paths),'Invalid prefix')
  require(tx['previous_state_digest']==digest(state),'Invalid prefix state')
  state['frozen'].update(tx['new_frozen']);state.update(tx['next_state'])
  require(digest(state)==tx['next_state_digest'],'Invalid prefix next state')
  paths.append(p);parent=sha
 require(len(paths)==237 and state['next_start']=='2026-08-26T00:00:00+09:00','Prefix boundary must precede problematic commitment')
 TARGET.mkdir(parents=True);(TARGET/'windows').mkdir()
 shutil.copyfile(SOURCE/'manifest.json',TARGET/'manifest.json')
 for p in paths:shutil.copyfile(p,TARGET/'windows'/p.name)
 provenance=dict(source=str(SOURCE.relative_to(ROOT)),target=str(TARGET.relative_to(ROOT)),prefix_windows=237,
  resume_start=state['next_start'],prefix_last_sha256=parent,prefix_state_sha256=digest(state),accessed_utc=datetime.now(timezone.utc).isoformat(),
  reason='V1 Aug26 integer solution failed fixed-LP polish; Aug27 frozen continuation infeasible in both backends. Preserve V1; recompute Aug26 onward with SCIP before Aug27 obligations were formed.',
  excluded_window='00237.json.gz',physical_energy_residual_at_zero_baseline_mwh=1.1624465857609664e-08,
  changed_asset_or_input_or_physical_constraints=False)
 (TARGET/'prefix_reuse.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(provenance,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
