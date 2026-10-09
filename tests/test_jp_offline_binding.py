"""Offline price identity, units, missing-trade treatment and disabled-order physics."""
from copy import deepcopy
import csv,io,unittest
from project.jp_ev_offline_20261005.build_inputs import decode
from src.jp_milp.core import solve_window
from src.jp_milp.inputs import validate
from tests.test_jp_milp import fixture

def csv_body(price='1.79',award='1.998',final=False,day='20260801',count=48):
 rows=[['H'],['P','確報値' if final else '速報値',day[:6],'一次オフライン',str(count)],
       ['TT','調達区分','取引情報','四国'] if final else ['TT','取引情報','四国']]
 for label,value in [('平均約定価格（電源属地別）[円/kW・30分]' if final else '平均落札価格（電源属地別）[円/kW・30分]',price),
                     ('約定量合計（電源属地別）[MW]' if final else '落札量合計（電源属地別）[MW]',award),
                     ('平均約定価格（TSO別）[円/kW・30分]' if final else '平均落札価格（TSO別）[円/kW・30分]','99')]:
  rows.append([day+'B01']+(['合計（確報値）'] if final else [])+[label,value])
 stream=io.StringIO();csv.writer(stream).writerows(rows);return stream.getvalue().encode('cp932')

def decoded(**kw):
 return list(decode(csv_body(**kw),'202608_1-1_result.csv',dict(source='TEST',url='TEST',sha256='TEST',accessed_utc='TEST')))[0]

class OfflineTests(unittest.TestCase):
 def test_source_not_tso_and_unit_conversion(self):
  for final in (True,False):
   q=decoded(final=final);self.assertEqual(q['price_jpy_mw_30min'],1790.)
   self.assertEqual(q['tso_average_raw_jpy_kw_30min'],99.)
 def test_no_trade_is_not_observed_zero_price(self):
  q=decoded(price='0',award='0');self.assertIsNone(q['price_jpy_mw_30min']);self.assertFalse(q['market_enabled'])
 def test_real_zero_price_with_award_is_retained(self):
  q=decoded(price='0');self.assertEqual(q['price_jpy_mw_30min'],0.);self.assertTrue(q['market_enabled'])
 def test_positive_award_without_price_rejected(self):
  with self.assertRaises(ValueError):decoded(price='-')
 def test_wrong_product_rejected(self):
  body=csv_body().decode('cp932').replace('一次オフライン','一次').encode('cp932')
  with self.assertRaises(ValueError):list(decode(body,'wrong',{}))
 def test_pre_march_price_not_divided_by_six(self):
  q=decoded(day='20260101',count=8)
  self.assertEqual(q['native_halfhours'],6);self.assertEqual(q['price_jpy_mw_30min']*6,10740.)
 def test_disabled_capacity_forced_zero_and_physical_audit(self):
  d=fixture(n=52)
  reference=solve_window(d)
  self.assertGreater(max(reference['orders'][b['id']]['common'] for b in d['capacity_blocks']),0.)
  for b in d['capacity_blocks']:b.update(market_enabled=False,market_disabled_reason='NO_OBSERVED_OFFLINE_PRICE')
  out=solve_window(d)
  self.assertEqual(out['audit']['status'],'PASS')
  for b in d['capacity_blocks']:self.assertEqual(out['orders'][b['id']]['common'],0.)
  self.assertEqual(sum(x['capacity_jpy'] for x in out['intervals']),0.)
 def test_disabled_cannot_erase_frozen_commitment(self):
  d=fixture(n=4);b=d['capacity_blocks'][0];b.update(market_enabled=False,market_disabled_reason='TEST')
  d['initial_frozen'][b['id']]=dict(f=1.,s=0.,t=0.,common=1.,candidate_id=None)
  with self.assertRaisesRegex(ValueError,'cannot erase'):solve_window(d)
 def test_strict_offline_evidence_rejects_ordinary_product(self):
  d=fixture(n=4);d['capacity_price_binding']='EV_OFFLINE_1_1_SOURCE_STRICT_V1'
  with self.assertRaisesRegex(ValueError,'offline 1-1'):validate(d)
 def test_disabled_reason_is_required(self):
  d=fixture(n=4);d['capacity_blocks'][0]['market_enabled']=False
  with self.assertRaisesRegex(ValueError,'explicit reason'):validate(d)
 def test_production_lv_cannot_omit_offline_binding(self):
  d=fixture(n=4);d['classification']='EX_POST_CONDITIONAL'
  with self.assertRaisesRegex(ValueError,'strict offline'):validate(d)

if __name__=='__main__':unittest.main()
