"""Full LV offline ledger validation and user report; preserve prior runs."""
from pathlib import Path
from datetime import timedelta
import sys,json,csv,gzip,math,hashlib,shutil,zipfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from src.jp_milp.config import timestamp,digest,require
from src.jp_milp.audit import audit_window
from src.jp_milp.rolling import check_due_orders
from src.jp_milp.core import allowance
from project.jp_kyushu_lv_20261006.run import prepare,assemble_window
HERE=Path(__file__).parent
FOLDER=ROOT/'outputs/JP/kyushu_lv_20251201_20260831_20261006_v3/LV_FCR'

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
 require(summary['status']=='COMPLETE' and summary['windows']==274 and summary['executed_intervals']==13152,'Full run incomplete')
 prepared,a,runtime,events,skeleton,budget,terminal=prepare('LV_FCR')
 require(runtime==manifest['runtime'] and a==manifest['assumptions'] and prepared['metadata']==manifest['identity']['source_metadata'],'Run/input identity mismatch')
 require(sha(ROOT/'project/jp_revenue_20261005/numeric_states.py')==manifest['identity']['numerical_state_helper_sha256'],'Numerical helper changed')
 require(sha(ROOT/'project/jp_kyushu_lv_20261006/daily_solver.py')==manifest['identity']['daily_solver_sha256'],'Daily solver helper changed')
 require(sha(ROOT/'project/jp_ev_offline_20261005/binding.py')==manifest['identity']['offline_block_binding_sha256'],'Offline block helper changed')
 require(sha(ROOT/'project/jp_kyushu_lv_20261006/run.py')==manifest['identity']['runner_sha256'],'Runner changed')
 from src.jp_milp.rolling import code_identity
 require(code_identity()==manifest['identity']['solver_code_sha256'],'Solver source changed')
 quotes={r['start']:r['offline_quote'] for r in prepared['intervals']}
 da={r['start']:r['da_price_jpy_mwh'] for r in prepared['intervals']}
 specs={x['id']:x for x in skeleton['capacity_blocks']+skeleton['spot_orders']}
 state=manifest['initial_state'];parent=digest(manifest);rows=[];native={};audits=[];bid_sum=0.;bid_halfhours=0
 max_gap=0.;max_bound_roundoff=0.;sum_bound_roundoff=0.;daily_roundoffs=[];seed_seconds=0.;time_limited_windows=0;time_limited_attempts=0
 paths=sorted((FOLDER/'windows').glob('*.json.gz'));require(len(paths)==274,'Window count mismatch')
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
  require(window['budgets']==allowance(data,state['used'],timestamp(end),'2026-09-01T00:00:00+09:00'),'Original annual allowance was not restored')
  audit=audit_window(data,window);require(audit['status']=='PASS','Reconstructed physical audit failed')
  orders=window['orders'];m=window['metrics'];require(m['gap'] is not None and math.isfinite(m['gap']) and 0<=m['gap']<=.005+1e-12,'Quality gate failed')
  for attempt in m.get('cross_solver_attempts',[m]):
   proof=attempt.get('daily_decomposition')
   if proof:
    components=proof['components'];require(proof['decision_start']==start and len(components)==proof['days'],'Daily decision/coverage evidence differs')
    require(len(components)==int((timestamp(end)-timestamp(start)).total_seconds()/86400),'Incomplete daily proof')
    for component in components:
     require(component['bound_jpy'] is not None and math.isfinite(component['bound_jpy']) and math.isfinite(component['objective_jpy']),'Nonfinite daily bound')
     require(component['bound_jpy']>=component['objective_jpy']-(1+1e-8*max(abs(component['bound_jpy']),abs(component['objective_jpy']))),'Contradictory daily bound')
     daily_roundoffs.append(max(0.,component['objective_jpy']-component['bound_jpy']))
     polish=component.get('continuous_polish')
     require((polish is not None and polish['status']==0 and polish.get('accepted') is True) if component['integers'] else component['status']==0,'Daily certificate missing')
    close(math.fsum(c['bound_jpy'] for c in components),attempt['bound_jpy'],.01)
    close(math.fsum(c['objective_jpy'] for c in components),attempt['objective_jpy'],.01)
  attempts=m.get('cross_solver_attempts',[m]);require(all(z['bound_jpy'] is not None and math.isfinite(z['bound_jpy']) and math.isfinite(z['objective_jpy']) for z in attempts),'Nonfinite bounds')
  require((m.get('continuous_polish') or {}).get('status')!=2,'Uncertified frozen LP')
  certified=[z for z in attempts if (z.get('continuous_polish') or {}).get('status')!=2]
  best=max(z['objective_jpy'] for z in certified);upper=min(z['bound_jpy'] for z in attempts)
  require(upper>=best-(1.+1e-8*max(abs(best),abs(upper))),'Inconsistent currency bounds')
  close(m['objective_jpy'],best,.001);close(m['bound_jpy'],upper,.001)
  close(m['gap'],max(0.,upper-best)/max(abs(best),1e-10),1e-10)
  max_gap=max(max_gap,m['gap']);max_bound_roundoff=max(max_bound_roundoff,max(0.,best-upper))
  sum_bound_roundoff+=max(0.,best-upper)
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
 first=timestamp('2025-12-01T00:00:00+09:00');asset=runtime['asset'];previous=asset['initial_mwh']
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
 for year,used in state['used'].items():
  close(math.fsum(r['efc'] for r in rows if r['start'][:4]==year),used,1e-7);require(used<=budget[year]+1e-6,'Cycle budget exceeded')
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
 result=dict(status='PASS',formal_days=274,formal_halfhours=13152,formal_start=first.isoformat(),formal_end='2026-09-01T00:00:00+09:00',
  cash=sums,initial_soc_mwh=asset['initial_mwh'],end_soc_mwh=previous,annual_budget_efc=budget,used_efc=state['used'],
  average_committed_mw=bid_sum/len(rows),bid_halfhours=bid_halfhours,max_gap=max_gap,solver_seconds=summary['solver_seconds'],
  seed_seconds=seed_seconds,time_limited_windows=time_limited_windows,classification='EX_POST_CONDITIONAL_ROLLING_NOT_REAL_EXECUTABLE_PROFIT',
  bound_roundoff_jpy=dict(window_max=max_bound_roundoff,window_sum=sum_bound_roundoff,daily_component_max=max(daily_roundoffs,default=0.),daily_component_sum=math.fsum(daily_roundoffs),daily_component_count=len(daily_roundoffs)),
  monetary_bound_tolerance='1 JPY + 1e-8 * max(abs(primal), abs(bound))',physical_audit_tolerance=1e-6,
  manifest_sha256=sha(FOLDER/'manifest.json'),last_transaction_sha256=parent,validation_code_sha256=sha(Path(__file__)),window_audits=audits)
 segments={}
 for label,subset in [('before_lv_entry',[r for r in rows if r['start']<'2026-03-14']),('from_lv_entry',[r for r in rows if r['start']>='2026-03-14'])]:
  segments[label]=dict(days=len(subset)//48,halfhours=len(subset),**{k:math.fsum(r[k] for r in subset) for k in keys})
 result['entry_segments']=segments
 above_source=[r for r in rows if native[quotes[r['start']]['native_block_id']]['committed_mw']>quotes[r['start']]['source_award_mw']+1e-7]
 result['project_bid_above_historical_source_award_halfhours']=len(above_source)
 result['cash_in_above_historical_source_award_halfhours_jpy']=math.fsum(r['capacity_jpy'] for r in above_source)
 save(HERE/'validation_and_results.json',result)
 for path,values in [('monthly_revenue.csv',monthly),('native_capacity_orders.csv',list(native.values()))]:
  with (HERE/path).open('w',encoding='utf-8-sig',newline='') as stream:
   writer=csv.DictWriter(stream,fieldnames=list(values[0]));writer.writeheader();writer.writerows(values)
 lines=['# 九州 LV 一次离线：2 MW/8 MWh','',
 '正式测算：2025-12-01—2026-08-31（JST），274天、13,152个半小时；2026-09-01仅为观察尾部。价格来自2026-10-06重新下载的JEPX九州现货和EPRX一次离线1-1行情。',
 '', '|项目|万日元|','|---|---:|']
 for label,key in [('一次离线容量收入','capacity_jpy'),('SOC恢复购售电净现金','spot_jpy'),('一次激活收入','activation_jpy'),('合计条件现金','total_jpy')]:lines.append(f"|{label}|{sums[key]/1e4:,.2f}|")
 lines+=['','|区间|天数|合计条件现金（万日元）|','|---|---:|---:|']
 for label,seg in segments.items():lines.append(f"|{'2025-12-01—2026-03-13' if label=='before_lv_entry' else '2026-03-14—2026-08-31'}|{seg['days']}|{seg['total_jpy']/1e4:,.2f}|")
 lines+=['','3月14日前为等效资源置于历史市场下的反事实部分，官方低压资源准入不支持该期真实参与。之后亦未认证本站的聚合、计量、通信、性能及合同资格。两个区间是同一连续账本的分段，未各自重置初始义务。',
 '', 'SOC 5%—100%，每天初末50%（4 MWh），充放电单向效率92%，并网进出各2 MW；零辅用假设。一次激活收入为零，调用电量仍计入SOC、损耗及循环。每天恒定恢复基线，按九州现货价代理购售电，不做日内套利。控制死区±0.01 Hz、满响应±0.20 Hz、满功率服务5分钟为沿用的工程假设。',
 '', f"EFC合计{sums['efc']:.6f}，分年{state['used']}，分年上限{budget}。转换损耗{sums['conversion_loss_mwh']:.6f} MWh，上调调用{sums['activation_up_mwh']:.6f} MWh，下调调用{sums['activation_down_mwh']:.6f} MWh。期末SOC {previous:.6f} MWh。全期平均申报容量{bid_sum/len(rows):.6f} MW（含零时段），有报价半小时{bid_halfhours}格。",
 '', '|月份|容量收入（万日元）|恢复净现金（万日元）|合计（万日元）|有报价半小时|','|---|---:|---:|---:|---:|']
 for m in monthly:lines.append(f"|{m['month']}|{m['capacity_jpy']/1e4:,.2f}|{m['spot_jpy']/1e4:,.2f}|{m['total_jpy']/1e4:,.2f}|{m['bid_halfhours']}|")
 lines+=['',f"274个逐日窗口已按原输入重建并核验物理响应、SOC、冻结义务、原生报价块、整数网格、散列链、现金与月度及半小时导出，均PASS。最大窗口gap {max_gap:.8g}，质量门禁0.5%；主求解累计{summary['solver_seconds']:.2f}秒，达到时限窗口{time_limited_windows}。窗口gap不代表全期收益误差界。",'',
 f"货币上下界比较容差为1日元＋1e-8×上下界绝对值的较大值，仅处理浮点舍入。原窗上界低于可行目标的最大/累计反差为{max_bound_roundoff:.12g}/{sum_bound_roundoff:.12g}日元；全部尝试中的日组件对应最大/累计为{max(daily_roundoffs,default=0.):.12g}/{math.fsum(daily_roundoffs):.12g}日元（{len(daily_roundoffs)}个组件，滚动预测重叠计入）。物理审核容差仍为1e-6，未因货币容差而放宽。",'',
 f"正式行情共11,587格有属地成交价、1,565格无属地成交而不新增报价。本次有{len(above_source)}格的优化容量大于当期历史属地成交量；这些格的容量现金合计{math.fsum(r['capacity_jpy'] for r in above_source)/1e4:,.2f}万日元。模型没有以历史成交量限制本站容量，理想全额成交假设和价格冲击风险须保留，不能把历史平均价格乘容量视为成交保证。",'',
 '规则事实、来源和假设详见[README](README.md)。本结果为逐日滚动事后条件现金，不是可执行策略收益或全期严格理论上界。频率正态尺度和缺口匹配为统计代理；冬季跨季节迁移未实证校准。理想全额成交、无价格冲击；区域均价不保证本站报价成交。无属地成交价时不新增报价为保守假设，不是官方禁止投标。不含偏差结算、投资、固定运维、衰减、税、零售及输配电合同费用。']
 (HERE/'收益测算结果.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k!='window_audits'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
