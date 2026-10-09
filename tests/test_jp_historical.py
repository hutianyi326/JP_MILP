"""Historical event closure, frozen quantities and regime boundary tests."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import json,tempfile,unittest
from tests.test_jp_milp import fixture
from src.jp_milp.config import timestamp,InputError
from src.jp_milp.inputs import validate
from src.jp_milp.scheduling import planning_end,capacity_clock,HISTORICAL,CLOSURE
from src.jp_milp.rolling import run

def historical_fixture(start='2026-01-06T00:00:00+09:00',days=12,scenario='HV_SPOT_FCR'):
    data=fixture(scenario,n=days*48,block_size=6)
    shift=timestamp(start)-timestamp(data['intervals'][0]['start'])
    rename={r['start']:(timestamp(r['start'])+shift).isoformat() for r in data['intervals']}
    for r in data['intervals']:r['start']=rename[r['start']]
    for o in data['spot_orders']:
        o['weights']={rename[t]:v for t,v in o['weights'].items()};o['id']='DA/'+next(iter(o['weights']))
        for k in ('gate','result'):o[k]=(timestamp(o[k])+shift).isoformat()
    blocks=[]
    for b in data['capacity_blocks']:
        b['intervals']=[rename[t] for t in b['intervals']];b['price_jpy_mw_30min']={rename[t]:v for t,v in b['price_jpy_mw_30min'].items()}
        groups=[[t] for t in b['intervals']] if b['intervals'][0][:10]>='2026-03-14' else [b['intervals']]
        for group in groups:
            n=deepcopy(b);n['intervals']=group;n['price_jpy_mw_30min']={t:b['price_jpy_mw_30min'][t] for t in group};n['id']='CAP/'+group[0]
            gate,result,count=capacity_clock(group[0]);n.update(gate=gate.isoformat(),result=result.isoformat(),clock_evidence='SYNTHETIC_HISTORICAL_CLOCK_TEST')
            blocks.append(n)
    data.update(capacity_blocks=blocks,capacity_clock_policy=HISTORICAL,planning_horizon_policy=CLOSURE)
    return data

class HistoricalTests(unittest.TestCase):
    def test_clock_boundaries_and_invalid_clock(self):
        data=historical_fixture('2026-03-12T00:00:00+09:00',4);validate(data)
        before=next(b for b in data['capacity_blocks'] if b['intervals'][0]=='2026-03-13T21:00:00+09:00')
        after=next(b for b in data['capacity_blocks'] if b['intervals'][0]=='2026-03-14T00:00:00+09:00')
        self.assertEqual(before['gate'],'2026-03-03T14:00:00+09:00');self.assertEqual(len(before['intervals']),6)
        self.assertEqual(after['gate'],'2026-03-13T14:00:00+09:00');self.assertEqual(len(after['intervals']),1)
        after['gate']=before['gate']
        with self.assertRaises(InputError):validate(data)

    def test_due_week_and_frozen_future_expand_without_omission(self):
        data=historical_fixture();start=timestamp(data['intervals'][0]['start'])
        self.assertEqual(planning_end(data,start,start+timedelta(days=1),{}).isoformat(),'2026-01-17T00:00:00+09:00')
        future=data['capacity_blocks'][80]
        # On a non-gate day, a frozen obligation still expands the horizon.
        now=start+timedelta(days=1)
        end=planning_end(data,now,now+timedelta(days=1),{future['id']:{'common':1.}})
        self.assertGreaterEqual(end,timestamp(future['intervals'][-1])+timedelta(minutes=30))
        future['services'][0]['segments'][0]['hours']=1000
        with self.assertRaises(InputError):planning_end(data,now,now+timedelta(days=1),{future['id']:{'common':1.}})

    def test_weekly_freeze_resume_budget_and_soc(self):
        data=historical_fixture();end='2026-01-17T00:00:00+09:00'
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'weekly'
            first=run(data,end,folder,max_windows=1);self.assertEqual(first['status'],'PARTIAL')
            tx=json.loads((folder/'windows/00000.json').read_text())
            self.assertEqual(tx['window']['end'],'2026-01-17T00:00:00+09:00')
            due=[b for b in data['capacity_blocks'] if b['gate']=='2026-01-06T14:00:00+09:00']
            self.assertEqual(len(due),56)
            fixed={b['id']:tx['next_state']['frozen'][b['id']] for b in due}
            self.assertTrue(any(v['common']>0 for v in fixed.values()))
            second=run(data,end,folder,resume=True,max_windows=1);self.assertEqual(second['status'],'PARTIAL')
            later=json.loads((folder/'windows/00001.json').read_text())
            for key,val in fixed.items():self.assertEqual(later['next_state']['frozen'][key],val)
            self.assertAlmostEqual(later['executed'][0]['soc_start_mwh'],tx['executed'][-1]['soc_end_mwh'])
            self.assertGreaterEqual(later['next_state']['used']['2026'],tx['next_state']['used']['2026'])
            self.assertEqual(second['cash']['activation_jpy'],0.)

    def test_cross_reform_complete_rolling(self):
        data=historical_fixture('2026-03-12T00:00:00+09:00',4)
        with tempfile.TemporaryDirectory() as temp:
            result=run(data,'2026-03-15T00:00:00+09:00',Path(temp)/'reform')
            self.assertEqual(result['status'],'COMPLETE');self.assertEqual(result['executed_intervals'],144)
            self.assertAlmostEqual(result['end_soc_mwh'],data['asset']['target_mwh'])

if __name__=='__main__':unittest.main()
