"""Full LV offline ledger validation and user report; preserve prior runs."""
from pathlib import Path
from datetime import timedelta
import sys,json,csv,gzip,math,hashlib,shutil,zipfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from src.jp_milp.config import timestamp,digest,require
from src.jp_milp.audit import audit_window
from src.jp_milp.rolling import check_due_orders
from project.jp_revenue_20261005.run_scenarios import prepare,assemble_window
HERE=Path(__file__).parent
FOLDER=ROOT/'outputs/JP/lv_offline_20261005_v2/LV_FCR'

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def close(x,y,tol=1e-6):require(abs(x-y)<=tol,f'Ledger mismatch {x} != {y}')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

def main():
 summary=read(FOLDER/'summary.json');manifest=read(FOLDER/'manifest.json')
 transitions=[read(p) for p in sorted(FOLDER.glob('solver_update_*.json'))]
 stable=lambda identity:{k:v for k,v in identity.items() if k not in ('solver_code_sha256','runner_sha256','execution_backend')}
 known_identities=[manifest['identity']]+[x['current'] for x in transitions]
 require(all(stable(x)==stable(manifest['identity']) for x in known_identities),'Solver transition changed data or assumptions')
 require(summary['status']=='COMPLETE' and summary['windows']==242 and summary['executed_intervals']==11616,'Full run incomplete')
 prepared,a,runtime,events,skeleton,budget,terminal=prepare('LV_FCR')
 require(runtime==manifest['runtime'] and a==manifest['assumptions'] and prepared['metadata']==manifest['identity']['source_metadata'],'Run/input identity mismatch')
 require(sha(ROOT/'project/jp_revenue_20261005/numeric_states.py')==manifest['identity']['numerical_state_helper_sha256'],'Numerical helper changed')
 require(sha(ROOT/'project/jp_revenue_20261005/run_scenarios.py')==manifest['identity']['runner_sha256'],'Runner changed')
 from src.jp_milp.rolling import code_identity
 require(code_identity()==manifest['identity']['solver_code_sha256'],'Solver source changed')
 quotes={r['start']:r['offline_quote'] for r in prepared['intervals']}
 da={r['start']:r['da_price_jpy_mwh'] for r in prepared['intervals']}
 specs={x['id']:x for x in skeleton['capacity_blocks']+skeleton['spot_orders']}
 state=manifest['initial_state'];parent=digest(manifest);rows=[];native={};audits=[];bid_sum=0.;bid_halfhours=0
 max_gap=0.;max_bound_roundoff=0.;seed_seconds=0.;time_limited_windows=0;time_limited_attempts=0
 paths=sorted((FOLDER/'windows').glob('*.json.gz'));require(len(paths)==242,'Window count mismatch')
 for sequence,path in enumerate(paths):
  with gzip.open(path,'rt',encoding='utf-8') as stream:tx=json.load(stream)
  checksum=tx.pop('sha256');require(checksum==digest(tx) and tx['parent']==parent and tx['sequence']==sequence,'Transaction chain corrupted')
  require(tx['execution_identity'] in known_identities,'Unregistered run identity')
  require(tx['execution_identity']['execution_backend']==tx['solver_configuration']['backend'],'Backend evidence mismatch')
  require(tx['previous_state_digest']==digest(state),'Previous state discontinuity')
  require(not set(state['frozen'])&set(tx['new_frozen']),'Frozen orders replaced')
  window=tx['window'];start=window['start'];end=window['end']
  data=assemble_window(prepared,a,runtime,events,'LV_FCR',start,end,budget,terminal)
  data['solver']=tx['solver_configuration'];require(digest(data)==tx['input_sha256'],'Window input fingerprint mismatch')
  audit=audit_window(data,window);require(audit['status']=='PASS','Reconstructed physical audit failed')
  orders=window['orders'];m=window['metrics'];require(m['gap'] is not None and math.isfinite(m['gap']) and 0<=m['gap']<=.005+1e-12,'Quality gate failed')
  attempts=m.get('cross_solver_attempts',[m]);require(all(z['bound_jpy'] is not None and math.isfinite(z['bound_jpy']) and math.isfinite(z['objective_jpy']) for z in attempts),'Nonfinite bounds')
  best=max(z['objective_jpy'] for z in attempts);upper=min(z['bound_jpy'] for z in attempts)
  require(upper>=best-(1.+1e-8*max(abs(best),abs(upper))),'Inconsistent currency bounds')
  close(m['objective_jpy'],best,.001);close(m['bound_jpy'],upper,.001)
  close(m['gap'],max(0.,upper-best)/max(abs(best),1e-10),1e-10)
  max_gap=max(max_gap,m['gap']);max_bound_roundoff=max(max_bound_roundoff,max(0.,best-upper))
  time_limited_windows+=any(z['status']==1 for z in attempts);time_limited_attempts+=sum(z['status']==1 for z in attempts)
  seed_seconds+=m.get('seed_seconds',0.)
  for ident,value in state['frozen'].items():
   if ident not in orders:continue
   if isinstance(value,dict):
    for p in ('f','s','t','common'):close(orders[ident][p],value[p],1e-7)
    require(orders[ident]['candidate_id']==value['candidate_id'],'Frozen candidate changed')
   else:close(orders[ident],value,1e-7)
  for b in data['capacity_blocks']:
   q=orders[b['id']];close(q['f'],q['common']);close(q['s'],0.);close(q['t'],0.)
   require(0<=q['common']<=b['maximum_mw']+1e-7,'Offer above device capacity')
   if q['common']>1e-7:
    require(q['common']>=b['minimum_mw']-1e-7,'Offer below minimum');close(q['common']/b['grid_mw'],round(q['common']/b['grid_mw']),1e-6)
   if not b['market_enabled']:close(q['common'],0.)
  execute=tx['executed'];require(len(execute)==48 and execute==window['intervals'][:48],'Execution rows not actual window prefix')
  day=timestamp(start);close(execute[0]['soc_start_mwh'],state['soc'],1e-8)
  check_due_orders(specs,day,day+timedelta(days=1),orders,state['frozen'])
  expected_frozen={k:v for k,v in orders.items() if timestamp(specs[k]['gate'])<day+timedelta(days=1) and k not in state['frozen']}
  require(tx['new_frozen']==expected_frozen,'Gate freezing differs')
  for r in execute:
   q=quotes[r['start']];ident=q['native_block_id'];value=orders[ident]['common']
   if ident in native:close(native[ident]['committed_mw'],value,1e-7)
   else:native[ident]=dict(native_block_id=ident,delivery_start=q['start'],native_halfhours=q['native_halfhours'],committed_mw=value,market_enabled=q['market_enabled'],source_award_mw=q['source_award_mw'],observed_price_jpy_kw_30min=q['source_average_raw_jpy_kw_30min'] if q['market_enabled'] else None,quality=q['quality'])
   if not q['market_enabled']:close(value,0.)
   price=q['price_jpy_mw_30min'] if q['market_enabled'] else 0.
   close(r['capacity_jpy'],value*price,1e-5);close(r['spot_jpy'],r['baseline_mw']*.5*da[r['start']],1e-5);close(r['activation_jpy'],0.)
   close(r['total_jpy'],r['capacity_jpy']+r['spot_jpy']+r['activation_jpy'],1e-5)
   close(r['baseline_mw'],execute[0]['baseline_mw'],1e-7)
   bid_sum+=value;bid_halfhours+=value>1e-7
  close(execute[-1]['soc_end_mwh'],runtime['asset']['target_mwh'],1e-6)
  state['frozen'].update(tx['new_frozen']);state.update(tx['next_state']);require(digest(state)==tx['next_state_digest'],'Next state discontinuity')
  rows+=execute;parent=checksum
  audits.append(dict(day=start[:10],physical_audit=audit['status'],gap=m['gap'],service_chains=audit['service_chains'],input_sha256=tx['input_sha256']))
  if sequence%40==0:print('validated',sequence+1,'windows',flush=True)
 require(state==read(FOLDER/'checkpoint.json'),'Checkpoint mismatch')
 first=timestamp('2026-01-01T00:00:00+09:00');asset=runtime['asset'];previous=asset['initial_mwh']
 for i,r in enumerate(rows):
  require(timestamp(r['start'])==first+timedelta(minutes=30*i),'Execution timeline gap')
  close(r['soc_start_mwh'],previous,1e-8)
  close(r['soc_end_mwh'],r['soc_start_mwh']+asset['eta_charge']*r['charge_mwh']-r['discharge_mwh']/asset['eta_discharge']-.5*asset['auxiliary_dc_mw'],1e-6)
  require(asset['minimum_mwh']-1e-6<=r['soc_lower_mwh']<=r['soc_upper_mwh']<=asset['maximum_mwh']+1e-6,'SOC excursion')
  previous=r['soc_end_mwh']
 close(previous,asset['target_mwh'],1e-6)
 keys=('spot_jpy','capacity_jpy','activation_jpy','total_jpy','efc','conversion_loss_mwh','charge_mwh','discharge_mwh','activation_up_mwh','activation_down_mwh')
 sums={k:math.fsum(r[k] for r in rows) for k in keys}
 for k,v in summary['cash'].items():close(sums[k],v,.01)
 close(sums['efc'],state['used']['2026'],1e-7);require(sums['efc']<=budget['2026']+1e-6,'Cycle budget exceeded')
 with (FOLDER/'executed_30min.csv').open(encoding='utf-8-sig',newline='') as stream:export=list(csv.DictReader(stream))
 require(len(export)==len(rows),'CSV count differs')
 for expected,actual in zip(rows,export):
  require(actual['start']==expected['start'],'CSV key differs')
  for key,value in expected.items():
   if isinstance(value,(int,float)):close(float(actual[key]),value,1e-7)
 monthly=[];raw_monthly=read(FOLDER/'monthly_cash.json')
 for month,record in raw_monthly.items():
  subset=[r for r in rows if r['start'].startswith(month)];qs=[quotes[r['start']] for r in subset]
  require(len(subset)==record['intervals'],'Month count differs')
  for key in ('spot_jpy','capacity_jpy','activation_jpy','total_jpy','efc'):close(math.fsum(r[key] for r in subset),record[key],.01 if key.endswith('jpy') else 1e-7)
  quantities=[native[q['native_block_id']]['committed_mw'] for q in qs];denominator=math.fsum(quantities)
  monthly.append(dict(month=month,**record,valid_source_price_halfhours=sum(q['market_enabled'] for q in qs),bid_halfhours=sum(x>1e-7 for x in quantities),average_committed_mw=denominator/len(subset),bid_weighted_price_jpy_kw_30min=record['capacity_jpy']/1000/denominator if denominator>0 else None))
 old=read(ROOT/'outputs/JP/revenue_20261005_v10/LV_FCR/summary.json')
 result=dict(status='PASS',scenario='LV_FCR_OFFLINE',formal_period='2026-01-01/2026-08-30 JST',days=242,formal_halfhours=11616,
  cash=sums,initial_soc_mwh=asset['initial_mwh'],end_soc_mwh=previous,average_committed_mw=bid_sum/len(rows),bid_halfhours=bid_halfhours,
  source_valid_price_halfhours=sum(q['market_enabled'] for q in quotes.values() if q['period_role']=='formal'),annual_budget_efc=budget['2026'],
  max_gap=max_gap,solver_seconds=summary['solver_seconds'],seed_seconds=seed_seconds,time_limited_windows=time_limited_windows,time_limited_attempts=time_limited_attempts,max_bound_roundoff_jpy=max_bound_roundoff,
  original_ordinary_F_proxy_total_jpy=old['cash']['total_jpy'],difference_from_ordinary_F_proxy_jpy=sums['total_jpy']-old['cash']['total_jpy'],
  classification='EX_POST_CONDITIONAL_DAILY_ROLLING_NOT_REAL_EXECUTABLE_PROFIT_OR_STRICT_GLOBAL_UPPER_BOUND',
  no_source_award_policy='NO_OBSERVED_OFFLINE_PRICE_DISABLE_NEW_OFFERS_NOT_AN_OFFICIAL_BAN',output=str(FOLDER.relative_to(ROOT)),
  manifest_sha256=sha(FOLDER/'manifest.json'),last_transaction_sha256=parent,validation_code_sha256=sha(Path(__file__)),solver_transitions=transitions,window_audits=audits)
 save(HERE/'validation_and_results.json',result)
 for path,values in [('monthly_revenue.csv',monthly),('native_capacity_orders.csv',list(native.values()))]:
  with (HERE/path).open('w',encoding='utf-8-sig',newline='') as stream:
   writer=csv.DictWriter(stream,fieldnames=list(values[0]));writer.writeheader();writer.writerows(values)
 lines=['# 四国LV一次离线：2 MW/8 MWh全期重算','',
 '测算区间2026年1月1日—8月30日，242天、11,616个半小时；8月31日仅为观察尾部。使用2026-10-05下载的EPRX一次离线1-1确报、合计确报、四国电源属地平均价。所有正式日已完成并通过账本和物理核验。','',
 '|现金项|万日元|','|---|---:|',
 f"|一次离线容量收入|{sums['capacity_jpy']/1e4:,.2f}|",f"|SOC恢复购售电净现金|{sums['spot_jpy']/1e4:,.2f}|",f"|一次激活收入|{sums['activation_jpy']/1e4:,.2f}|",f"|合计条件现金|{sums['total_jpy']/1e4:,.2f}|",'',
 '激活收入为零，但保留调用电量对SOC、损耗及循环的影响。95% DOD，SOC 5%—100%，初始与每日期末50%（4 MWh），充放电单向效率均92%，并网进出各2 MW，辅用0。每天恒定能量恢复基线，允许按四国日前价格补电或处理余电，禁止日内价差套利。一次控制仍为死区±0.01 Hz、满响应频差±0.20 Hz。','',
 f"EFC {sums['efc']:.6f}；转换损耗{sums['conversion_loss_mwh']:.6f} MWh；上调调用{sums['activation_up_mwh']:.6f} MWh、下调调用{sums['activation_down_mwh']:.6f} MWh。全期平均申报容量{bid_sum/len(rows):.6f} MW（含零报价时段），有报价半小时{bid_halfhours}格，期末SOC {previous:.6f} MWh。年度预算按242天折算为{budget['2026']:.6f} EFC。",'',
 '|月份|容量收入（万日元）|恢复净现金（万日元）|合计（万日元）|有报价半小时|','|---|---:|---:|---:|---:|']
 for m in monthly:lines.append(f"|{m['month']}|{m['capacity_jpy']/1e4:,.2f}|{m['spot_jpy']/1e4:,.2f}|{m['total_jpy']/1e4:,.2f}|{m['bid_halfhours']}|")
 lines+=['',f"旧普通F价格代理EV结果为{old['cash']['total_jpy']/1e4:,.2f}万日元，本次离线结果差额{sums['total_jpy']/1e4-old['cash']['total_jpy']/1e4:,.2f}万日元。变化同时来自价格系列与无成交时段报价禁用，并重新优化了报价、SOC恢复、损耗和循环；不能只解释为单价变化。旧账本和高压结果未改写。",'',
 '规则事实：官方一次离线独立1-1行情，属地与TSO口径不同，容量公表价不含V1/V2；来源、适用月份、字段位置和获取日期见[已审核离线修正](../jp_ev_offline_20261005/README.md)及formulation §14.8。研究解释：属地均价是资源区域价格代理，不能保证本站成交。建模假设：仅在有属地成交价证据时参与，其他7,097个正式半小时不新增报价；这不是官方禁止投标。理想全额成交、无价格冲击；历史区域成交量不作为本站中标上限。年初已关门且无初始承诺的合同为零。频率缺口与控制沿用已确认代理。','',
 '结果属于逐日滚动的事后条件现金，不是事前可执行收益，也不是全期联合优化的严格上界。不含偏差结算、零售/输配电等合同费用、投资成本、固定运维、衰减更换和税费。本站准入、完整离线履约、反事实无成交时段价格与成交概率仍未认证。','',
 f"242个窗口按原始输入重新执行物理审计、冻结义务/事务散列链/报价网格/原生块/现金/SOC/循环/导出CSV/月度核验，均PASS。最大窗口gap={max_gap:.8g}（门禁0.5%）；达到时限窗口{time_limited_windows}个、尝试{time_limited_attempts}次；主优化累计{summary['solver_seconds']:.2f}秒，已记录起点{seed_seconds:.2f}秒（均不含全部启发式与组装时间）。窗口gap不代表全期现金误差界。",'',
 '失败V1保留：8月26日MIP解的固定整数LP不可行，8月27日在HiGHS和SCIP均不能继续。定位满功率边界且零基线下日能量残差约1.16e-8 MWh，虽在原审计容差内，但不接受其作为可持续冻结义务。V2沿用截至8月25日的237个已验证窗口并从8月26日用SCIP重新优化；8月27日义务在新版本中从关门前重新生成，不擦除任何前237天已冻结的义务，也不改写V1记录。数据、资产、报价规则及物理约束未变；求解器切换和有效前缀复用记录保留。','',
 '新增本目录报告脚本、validation_and_results.json、monthly_revenue.csv、native_capacity_orders.csv及本报告；正式求解账本在outputs/JP/lv_offline_20261005_v2/LV_FCR/，不覆盖旧运行。主线程批准新增输出和验证报告，未修改求解数学或生产代码。']
 (HERE/'收益测算结果.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 snapshot=HERE/'source_snapshot';snapshot.mkdir(exist_ok=False)
 files=list((ROOT/'src/jp_milp').glob('*.py'))+[ROOT/'project/jp_revenue_20261005/run_scenarios.py',ROOT/'project/jp_revenue_20261005/numeric_states.py',ROOT/'project/jp_ev_offline_20261005/binding.py',ROOT/'project/jp_ev_offline_20261005/build_inputs.py',ROOT/'project/jp_shikoku_202601_0830/assemble_full_period.py',ROOT/'project/jp_first_run_inputs_20261004/assemble.py',Path(__file__)]
 fingerprints={}
 for source in files:
  target=snapshot/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target);fingerprints[str(source.relative_to(ROOT))]=sha(source)
 save(HERE/'source_snapshot_manifest.json',fingerprints)
 archive=ROOT/'outputs/JP/shikoku_lv_offline_2mw_8mwh_20260101_0830_20261005.zip'
 with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
  for path in [HERE/'收益测算结果.md',HERE/'validation_and_results.json',HERE/'monthly_revenue.csv',HERE/'native_capacity_orders.csv',HERE/'source_snapshot_manifest.json']+[FOLDER/n for n in ('manifest.json','summary.json','checkpoint.json','executed_30min.csv','monthly_cash.json','solver_metrics.json')]:z.write(path,str(path.relative_to(ROOT)))
  for path in snapshot.rglob('*'):
   if path.is_file():z.write(path,str(path.relative_to(ROOT)))
  for path in sorted(FOLDER.glob('solver_update_*.json')):z.write(path,str(path.relative_to(ROOT)))
  z.write(FOLDER/'prefix_reuse.json',str((FOLDER/'prefix_reuse.json').relative_to(ROOT)))
 with zipfile.ZipFile(archive) as z:require(z.testzip() is None,'ZIP CRC failed')
 print(json.dumps({k:v for k,v in result.items() if k!='window_audits'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
