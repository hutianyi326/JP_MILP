"""Independent integrity checks for the descriptive research package, not a model test."""
from pathlib import Path
import json,hashlib,sys
sys.stdout.reconfigure(encoding='utf8')
import pandas as pd
import openpyxl,re
B=Path(__file__).resolve().parent
areas=['北海道','東北','東京','中部','北陸','関西','中国','四国','九州']
expected=pd.date_range('2025-01-01','2026-09-01',freq='30min',inclusive='left',tz='Asia/Tokyo')
results=[]
def check(name,ok,detail):
    results.append((name,bool(ok),str(detail)))
inventory=pd.read_csv(B/'source_inventory.csv')
bad=[]
for r in inventory.to_dict('records'):
    p=B/r['path']; raw=p.read_bytes()
    if len(raw)!=r['bytes'] or hashlib.sha256(raw).hexdigest()!=r['sha256']:bad.append(r['id'])
check('原始文件大小及SHA256',not bad,f'{len(inventory)}个非空来源；异常={bad}')
spot=pd.read_csv(B/'analysis/spot_30min_JST_expost.csv')
check('日前时标',pd.DatetimeIndex(pd.to_datetime(spot.timestamp)).tz_convert('Asia/Tokyo').equals(expected),f'{len(spot)}时段')
check('九区日前价格完整',spot[areas].notna().all().all(),'九区域；未引入冲绳')
for filename,required in [('fundamentals_30min_DIAGNOSTIC.csv',['エリア需要']),('imbalance_30min_JST_expost.csv',['surplus_JPY_kWh','shortfall_JPY_kWh'])]:
    d=pd.read_csv(B/'analysis'/filename,low_memory=False)
    good=set(d.area)==set(areas) and not d.duplicated(['area','timestamp']).any()
    for a,g in d.groupby('area'):good=good and pd.DatetimeIndex(pd.to_datetime(g.timestamp)).tz_convert('Asia/Tokyo').equals(expected)
    check(filename+' 时标/区域',good,f'{len(d)}行；每区{len(expected)}')
    check(filename+' 必填字段',d[required].notna().all().all(),','.join(required))
    if 'scope_status' in d:
        check('基本面禁用标签',d.scope_status.eq('diagnostic_only_islands_unresolved').all(),'全部仅限诊断；字段缺失见field_quality.csv')
        check('九州联络线方向转换',d.loc[d.area.eq('九州'),'net_import_MW'].eq(-d.loc[d.area.eq('九州'),'連系線']).all(),'原始連系線保留，统一net_import_MW以进口为正；D09官方注记')
        parts=['原子力','火力(LNG)','火力(石炭)','火力(石油)','火力(その他)','水力','地熱','バイオマス','太陽光発電実績','風力発電実績','揚水','蓄電池','その他','net_import_MW']
        residual=d[parts].sum(axis=1,min_count=1)-d['合計']
        balance=pd.DataFrame({'area':d.area,'residual_MW':residual}).groupby('area').residual_MW.agg(['min','max','median']).reset_index()
        balance.to_csv(B/'analysis/balance_check_DIAGNOSTIC.csv',index=False,encoding='utf-8-sig')
        check('已公布分项对源合计平衡',residual.abs().le(3).all(),f'最大绝对差{residual.abs().max():.1f}MW（北陆分项舍入）；缺失分项跳过求和，不填写原值、不证明缺失真实为零')
installed=pd.read_csv(B/'analysis/installed_mix_DIAGNOSTIC.csv')
cols=['oil_other','coal','LNG','nuclear','hydro','pumped','solar','wind','other_new_energy','other']
deviation=(installed[cols].sum(axis=1)-100).abs().max()
check('装机比例抄录合计',deviation<=.5,f'18个区域年度；最大舍入偏差{deviation:.2f}个百分点；非实际在线容量')
ps=pd.read_csv(B/'analysis/price_statistics.csv')
check('统计窗口区分',set(ps.intervals)=={17520,11664},'2025全年17520；两年1—8月各11664时段')
intraday=pd.read_csv(B/'analysis/intraday_30min_JST_expost.csv')
check('日内时标与市场范围',pd.DatetimeIndex(pd.to_datetime(intraday.timestamp)).tz_convert('Asia/Tokyo').equals(expected) and intraday.market_scope.eq('JEPX_marketwide_not_area_execution_price').all(),'29,184时段；不伪装九区成交价')
icols=['open_JPY_kWh','high_JPY_kWh','low_JPY_kWh','close_JPY_kWh','reported_average_JPY_kWh']
check('日内OHLC与必填字段',intraday[icols+['native_volume_MWh_per_h','trade_count']].notna().all().all() and intraday[icols].ge(intraday.low_JPY_kWh,axis=0).all().all() and intraday[icols].le(intraday.high_JPY_kWh,axis=0).all().all(),'平均及开收盘价在公布高低范围内；数量保留MWh/h')
calendar=pd.read_csv(B/'analysis/calendar_JST.csv',keep_default_na=False).set_index('date')
check('日历覆盖及补休日',len(calendar)==608 and not calendar.index.duplicated().any() and calendar.loc[['2025-02-24','2025-05-06','2025-11-24','2026-05-06'],'day_type'].eq('National-holiday').all(),'内阁府H02；包括振替休日')
days=pd.read_csv(B/'analysis/daytype_statistics_DIAGNOSTIC.csv')
counts=days.groupby(['area','period']).intervals.sum().reset_index().merge(ps[['area','period','intervals']],on=['area','period'],suffixes=('_daytypes','_expected'),validate='one_to_one')
check('日类型互斥完备',len(counts)==27 and counts.intervals_daytypes.eq(counts.intervals_expected).all(),'81组日类型统计合计回到27组区域期间样本')
ev=pd.read_csv(B/'analysis/event_comparison_DIAGNOSTIC.csv')
check('事件日期与计划实绩分离',set(ev.date)=={'2025-04-13','2025-04-17','2025-05-04','2025-05-25','2025-06-01'} and ev.scope_status.str.contains('diagnostic').all(),'EV02代表日；计划MW及事后MWh分列；仍为边界诊断')
check('返还说明算术',abs((20*.95+40*.90+40*.85)-89)<1e-9 and abs((10*.95+90*.85)-86)<1e-9,'仅核对两个假设例子的算术，非项目结算或合同验证')
rq=pd.read_csv(B/'analysis/requirement_template_2026_AprAug_v20260309.csv')
check('固定版本需求模板完整性',len(rq)==10800 and not rq.duplicated(['product','month','slot','area']).any() and rq.requirement_MW.notna().all() and rq.publication_date_from_filename.eq('2026-03-09').all(),'5产品×5个月×48模板时段×9区；非逐日成交或离线上限')
w=openpyxl.load_workbook(B/'../../data/raw/JP/enecho_ep002_2025_1-2.xlsx',data_only=True)
groups=[[5],list(range(6,12))+[19],list(range(12,19))+[23],list(range(24,29)),list(range(20,23)),list(range(29,35)),list(range(35,40)),list(range(40,44)),list(range(44,51))]
boundary=(B/'../../countries/JP/boundary_revision_20260928.md').read_text(encoding='utf8')
table=boundary.split('### 5.2')[1].split('### 5.3')[0]
reported=[]
for line in table.splitlines():
    parts=[x.strip().replace(',','') for x in line.strip('|').split('|')]
    if len(parts)==8 and parts[0] in ['北海道','东北','东京','中部','北陆','关西','中国','四国','九州']:
        reported.append([float(x) for x in parts[1:]])
calculated=[[round(sum(float(w['2026.3'].cell(r,c).value or 0) for r in g)/1000,3) for c in [3,5,7,9,11,19,25]] for g in groups]
check('府县装机代理逐格复算',len(reported)==9 and reported==calculated,'M04 2026.3；9×7数值与附件一致；仅府县代理，不是TSO本土装机')
check('手续费时间单位换算',.02*.5*1000==.01*1000==10 and .03*1000==30,'1000kW一个30分钟块，未税：旧小时报价换算10JPY；2025费率30JPY；已归一F30不再次除2')
usage=pd.read_csv(B/'analysis/rrfit_forecast_usage_30min_JST_expost.csv')
check('三次②使用率时间轴与缺测',len(usage)==262656 and not usage.duplicated(['timestamp_JST','area']).any() and usage.FIT_forecast_error_MW.isna().sum()==23 and usage.requirement_MW.notna().all(),'9区×29184时段；误差23缺测保留；非实测激活')
single=pd.read_csv(B/'analysis/single_bid_award_monthly_rawunit.csv')
check('单一札月度范围',len(single)==108 and single.n.sum()==158976 and set(single.month.astype(str))=={'202604','202605','202607'},'3月×4产品×9区；原单位未确认，未转换成收益')
check('储能特措示例算术',abs(220*653.87+11000*1.84-164091.4)<1e-6,'东京规则的假设例；不证明任何实际项目满足特措或合同参数')
aw=pd.read_csv(B/'analysis/eprx_awards_native_blocks_expost.csv')
check('调整力年度包时段覆盖',len(aw)==763416 and not aw.duplicated(['timestamp_JST','product','area']).any() and aw.groupby(['product','area']).duration_h.sum().eq(14592).all(),'6产品×9区×608天；保留原3h/0.5h块')
native_grid_ok=True
for product,g in aw.groupby('product'):
    cut='2025-03-14' if product=='R' else '2026-03-14'
    grid=pd.date_range('2025-01-01',cut,freq='3h',inclusive='left',tz='Asia/Tokyo').append(pd.date_range(cut,'2026-09-01',freq='30min',inclusive='left',tz='Asia/Tokyo'))
    for area,a in g.groupby('area'):
        native_grid_ok=native_grid_ok and pd.DatetimeIndex(pd.to_datetime(a.timestamp_JST)).tz_convert('Asia/Tokyo').sort_values().equals(grid)
check('调整力全部原生时间标签',native_grid_ok,'54条序列逐时间标签匹配官方3h转30min日期，不只检查小时合计')
check('调整力确报速報分离',aw.loc[aw.timestamp_JST.str[:7].eq('2026-08'),'quality'].eq('prompt').all() and aw.loc[aw.timestamp_JST.str[:7].lt('2026-08'),'quality'].eq('final').all(),'2026年8月仅速報，不伪装确报；9月不进入研究')
inv=pd.read_csv(B/'analysis/eprx_archive_member_inventory.csv')
member_ok=True
import zipfile
for archive,g in inv.groupby('archive'):
    with zipfile.ZipFile(B/'evidence'/archive) as z:
        for r in g.itertuples():member_ok=member_ok and hashlib.sha256(z.read(r.member)).hexdigest()==r.sha256
check('调整力ZIP成员哈希',member_ok,f'{len(inv)}成员；分割3月文件按有效日期去填充零行')
offline=pd.read_csv(B/'../../data/raw/JP/history_round3/E58_offline_cap_effective_timeseries.csv')
cap_ok=len(offline)==11704 and not offline.duplicated(['date','block_id']).any()
for area in areas:
    cap_ok=cap_ok and offline[f'F_offline_effective_{area}_MW'].eq(offline[[f'F_offline_registered_{area}_MW',f'F_primary_requirement_{area}_MW']].min(axis=1)).all()
check('历史一次离线枠合成算术',cap_ok,'11704原生块；9区逐块min登记枠/主产品募集量；仅市场枠，不是个体中标承诺')
from decimal import Decimal,ROUND_HALF_UP
round_int=lambda x:int(Decimal(str(x)).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
check('无发电量合同地点覆盖反例',round_int(100/(.98*.97))==105 and round_int(-100*.98)+round_int(200/(.98*.97))==112,'B/C无合同须整体G=0/D=A；105与错误普通分支112不同，只核假设算术')
check('容量返金假设金额算术',1000*10000*.05==500000 and 1000*10000*.05-1000*(10200-10000)==300000,'通常返金300000JPY；附则例外由原文及独立审核核实，不以此算术检查证明适用性')
report=['# 日本研究包验证记录','', '执行日期：2026-09-29（JST）。可重复运行validate_package.py。检查针对研究数据完整性，不证明市场资格、收益可实现或研究已获批准。','', '|检查|结果|证据/数量|','|---|---|---|']
report += [f'|{n}|{"PASS" if ok else "FAIL"}|{detail}|' for n,ok,detail in results]
report += ['','## 研究验收与输入门禁','', '- 研究独立审核第四轮PASS及主线程验收见review_round4_result.md；这些检查只验证数据/算术，不替代审核。','- 离岛不可拆分装机及供需维持DIAGNOSTIC，禁止正式模型输入；按V2登记缺口。','- 未核历史条款/费用/合同版本仍禁用，真实项目合同、预认证、工程及激活数据须另验收。','- 回测信息可得性未通过：下载时修订版只供事后研究，缺少历史决策时版本。','- 允许带输入门禁数学Markdown，数学验收由单独记录决定；生产代码和真实收益回测未批准。','', '原始来源包括失败/空响应记录，只有source_inventory.csv中的非空文件参与以上哈希检查。研究PASS不等于所有历史数据或项目输入闭合。']
(B/'validation_report.md').write_text('\n'.join(report)+'\n',encoding='utf8')
print(json.dumps({'checks':len(results),'passed':sum(r[1] for r in results),'failed':[r[0] for r in results if not r[1]]},ensure_ascii=False))
assert all(r[1] for r in results)
