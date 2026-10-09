"""Independent transaction/ledger checks and user-facing revenue comparison."""
import csv,gzip,json,math,sys
from pathlib import Path
from datetime import timedelta
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from src.jp_milp.config import digest,timestamp
from project.jp_shikoku_202601_0830.assemble_full_period import read_json
HERE=Path(__file__).parent;BASE=ROOT/'outputs/JP/revenue_20261005_v6'
FOLDERS={s:ROOT/'outputs/JP'/v/s for s,v in {'LV_FCR':'revenue_20261005_v10','HV_SPOT_FCR':'revenue_20261005_v8','HV_SPOT_S1_T1':'revenue_20261005_v11'}.items()}
NAMES={'LV_FCR':'EV（LV场景，仅一次）','HV_SPOT_FCR':'高压：现货＋一次','HV_SPOT_S1_T1':'高压：现货＋二次①＋三次①复合'}

def close(x,y,tol=1e-5):assert abs(x-y)<=tol,(x,y)

def check(scenario):
    folder=FOLDERS[scenario];summary=read_json(folder/'summary.json');manifest=read_json(folder/'manifest.json')
    assert summary['status']=='COMPLETE',summary
    assert summary['executed_intervals']==11616 and summary['windows']==242
    state=manifest['initial_state'];parent=digest(manifest);rows=[];audits=0;max_gap=0.;polishes=0;seed_seconds=0.;limited_windows=0;limited_attempts=0;bound_roundoff=0.
    capacity_mwh=0.;bid_halfhours=0;events=read_json(ROOT/'data/processed/JP/shikoku_full_run_k1_v5/historical_events_by_scenario.json')['HV_SPOT_S1_T1' if scenario=='HV_SPOT_S1_T1' else 'HV_SPOT_FCR']
    for n,p in enumerate(sorted((folder/'windows').glob('*.json.gz'))):
        with gzip.open(p,'rt',encoding='utf-8') as f:tx=json.load(f)
        sha=tx.pop('sha256');assert sha==digest(tx) and tx['parent']==parent and tx['sequence']==n
        assert tx['previous_state_digest']==digest(state) and not set(tx['new_frozen'])&set(state['frozen'])
        window=tx['window'];assert window['audit']['status']=='PASS';audits+=1
        assert window['metrics']['gap'] is not None and math.isfinite(window['metrics']['gap'])
        assert window['metrics']['status'] in (0,1)
        m=window['metrics'];assert m['gap']<=.005+1e-12
        attempts=m.get('cross_solver_attempts',[m])
        assert all(x['bound_jpy'] is not None and math.isfinite(x['objective_jpy']) and math.isfinite(x['bound_jpy']) for x in attempts)
        best=max(x['objective_jpy'] for x in attempts);upper=min(x['bound_jpy'] for x in attempts)
        assert upper>=best-(1.+1e-8*max(abs(upper),abs(best)))
        bound_roundoff=max(bound_roundoff,max(0.,best-upper))
        close(m['objective_jpy'],best,.001);close(m['bound_jpy'],upper,.001)
        close(m['gap'],max(0.,upper-best)/max(abs(best),1e-10),1e-10)
        limited_windows+=any(x['status']==1 for x in attempts);limited_attempts+=sum(x['status']==1 for x in attempts)
        polish=window['metrics'].get('continuous_polish') or {}
        max_gap=max(max_gap,window['metrics']['gap'] or 0.);polishes+=bool(polish.get('accepted',polish.get('status')==0))
        seed_seconds+=window['metrics'].get('seed_seconds',0.)
        assert len(tx['executed'])==48
        close(tx['executed'][0]['soc_start_mwh'],state['soc'],1e-8)
        for r in tx['executed']:
            q=window['orders'][events[r['start']]['native_block_id']]
            capacity_mwh+=.5*q['common'];bid_halfhours+=q['common']>1e-6
            if scenario=='HV_SPOT_S1_T1':close(q['s'],q['t']);close(q['common'],q['s'])
            if scenario=='LV_FCR':close(r['baseline_mw'],tx['executed'][0]['baseline_mw'],1e-6)
        if scenario=='LV_FCR':close(tx['executed'][-1]['soc_end_mwh'],manifest['runtime']['asset']['target_mwh'],1e-6)
        state['frozen'].update(tx['new_frozen']);state.update(tx['next_state']);assert tx['next_state_digest']==digest(state)
        rows+=tx['executed'];parent=sha
    assert audits==242 and state==read_json(folder/'checkpoint.json')
    assert limited_windows==summary['time_limited_windows']
    first=timestamp('2026-01-01T00:00:00+09:00')
    assert all(timestamp(r['start'])==first+timedelta(minutes=30*i) for i,r in enumerate(rows))
    a=manifest['runtime']['asset'];close(state['soc'],a['target_mwh'],1e-6)
    previous=a['initial_mwh']
    for r in rows:
        close(r['soc_start_mwh'],previous,1e-8)
        physical=r['soc_start_mwh']+a['eta_charge']*r['charge_mwh']-r['discharge_mwh']/a['eta_discharge']-r['auxiliary_dc_mwh']
        close(physical,r['soc_end_mwh'],1e-6);previous=r['soc_end_mwh']
        assert a['minimum_mwh']-1e-6<=r['soc_lower_mwh']<=r['soc_upper_mwh']<=a['maximum_mwh']+1e-6
        close(r['total_jpy'],r['spot_jpy']+r['capacity_jpy']+r['activation_jpy'])
    sums={k:math.fsum(r[k] for r in rows) for k in ('spot_jpy','capacity_jpy','activation_jpy','total_jpy','efc','conversion_loss_mwh','charge_mwh','discharge_mwh','activation_up_mwh','activation_down_mwh')}
    for k in summary['cash']:close(sums[k],summary['cash'][k],.01)
    monthly=read_json(folder/'monthly_cash.json')
    for month,aggregate in monthly.items():
        subset=[r for r in rows if r['start'].startswith(month)]
        assert aggregate['intervals']==len(subset)
        for key in ('spot_jpy','capacity_jpy','activation_jpy','total_jpy','efc'):
            close(math.fsum(r[key] for r in subset),aggregate[key],.01 if key.endswith('jpy') else 1e-7)
    close(sums['efc'],state['used']['2026'],1e-7)
    assert sums['efc']<=manifest['annual_budgets_efc']['2026']+1e-6
    if scenario!='HV_SPOT_S1_T1':close(sums['activation_jpy'],0.)
    return dict(scenario=scenario,name=NAMES[scenario],power_mw=a['discharge_mw'],energy_mwh=a['nominal_mwh'],**sums,
        average_committed_mw=capacity_mwh/(242*24),bid_halfhours=bid_halfhours,maximum_gap=max_gap,
        initial_soc_mwh=a['initial_mwh'],end_soc_mwh=state['soc'],audited_windows=audits,polished_windows=polishes,
        solver_seconds=summary['solver_seconds'],seed_solver_seconds=seed_seconds,time_limited_windows=limited_windows,time_limited_attempts=limited_attempts,maximum_bound_roundoff_jpy=bound_roundoff)

if __name__=='__main__':
    values=[check(s) for s in NAMES]
    (HERE/'revenue_comparison.json').write_text(json.dumps(dict(status='PASS',period='2026-01-01/2026-08-30 JST',days=242,results=values),ensure_ascii=False,indent=2),encoding='utf-8')
    with (HERE/'revenue_comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(values[0]));w.writeheader();w.writerows(values)
    monthly_rows=[]
    for scenario,name in NAMES.items():
        for month,record in read_json(FOLDERS[scenario]/'monthly_cash.json').items():
            monthly_rows.append(dict(scenario=scenario,name=name,month=month,**record))
    with (HERE/'monthly_revenue.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(monthly_rows[0]));w.writeheader();w.writerows(monthly_rows)
    lines=['# 四国首轮收益测算：2026年1月1日至8月30日','',
        '三组均完成242天、11,616个半小时的日滚动求解，8月31日仅作观察尾部。金额为日元；下表使用万日元。结果为已确认假设下的完美信息事后上限情景测算（采用逐日滚动近似求解，不是全期联合优化的严格上界），不含偏差结算、投资成本、固定运维、电池衰减/更换成本、税费和未建模的合同费用。不是决策时可实现的策略收益。','',
        '|场景|功率/容量|容量收入|现货净现金或补电现金|激活收入|合计|',
        '|---|---|---:|---:|---:|---:|']
    for v in values:
        lines.append(f"|{v['name']}|{v['power_mw']:g} MW/{v['energy_mwh']:g} MWh|{v['capacity_jpy']/1e4:,.2f}|{v['spot_jpy']/1e4:,.2f}|{v['activation_jpy']/1e4:,.2f}|{v['total_jpy']/1e4:,.2f}|")
    lines+=['','EV按用户确认的LV一次场景运行，每日期末恢复50% SOC，允许补电及处理调频余电；日内恢复基线保持恒定，避免日内价差套利。能量恢复现金采用四国日前价格代理，未加入零售电价或输配电费用。一次激活收入为零。高压复合的激活现金沿用日前价代理，不是V1/V2实际结算。','',
        '|场景|EFC|转换损耗 MWh|上调激活 MWh|下调激活 MWh|平均共享容量 MW|',
        '|---|---:|---:|---:|---:|---:|']
    for v in values:lines.append(f"|{v['name']}|{v['efc']:,.2f}|{v['conversion_loss_mwh']:,.2f}|{v['activation_up_mwh']:,.2f}|{v['activation_down_mwh']:,.2f}|{v['average_committed_mw']:,.2f}|")
    lines+=['','两种高压场景使用相同电池，适合比较；EV电池规模不同，不能仅比较绝对收益判断模式优劣。平均容量包含未投标时段。初始日前已关门且没有明确初始承诺的合同为零，不能追溯投标，因此年初部分容量收入为零。','',
        '共同参数：95% DOD、SOC 5%—100%、初末50%、充放电各92%、零辅用、无附加线路损耗。EV 2 MW/8 MWh，高压100 MW/200 MWh。一次死区±0.01 Hz、满响应频差±0.20 Hz。LFC k=1，不做其他k对比；复合二次①和三次①等容量，1 MW步长。年度600 EFC按242天折算397.808219 EFC。','',
        '频率/LFC缺口使用此前批准的代理；归一尺度使用全期事后数据。容量行情采用区域价格代理、理想全额成交；本轮未建模100 MW报价对市场价格和可中标量的影响。收益须结合这些假设解释。','',
        '## 验证与求解范围','',
        '逐窗独立物理审计、冻结量一致性审计均通过；报告另验证事务散列链、日期连续、跨日SOC、期末SOC、年度循环预算、各现金项及月度账本。每日滚动的局部最优不代表242天联合优化的全局最优。复合后续窗口采用0.1%的相对停止精度；早期达到时间上限的窗口实际差距另列。窗口目标包含观察期与终端估值，窗口gap不是全期现金收益误差界。交叉求解只组合相同模型的较高可行目标与较低上界；全部窗口通过0.5%质量门禁的事后核验。货币界一致性采用1日元＋1e-8倍目标尺度的浮点容差，物理容差不变；超时窗口指任一求解尝试达到时限。','']
    for v in values:lines.append(f"- {v['name']}：{v['audited_windows']}窗，最大相对gap={v['maximum_gap']:.8g}，达到时限窗口{v['time_limited_windows']}个、尝试{v['time_limited_attempts']}次，主优化累计{v['solver_seconds']:.2f}秒，已记录起点求解{v['seed_solver_seconds']:.2f}秒（不含全部启发式及组装时间）；期末SOC={v['end_soc_mwh']:.6f} MWh，最大上界浮点反差{v['maximum_bound_roundoff_jpy']:.8g}日元。")
    lines+=['','## 实现及证据','',
        '本轮主线程批准对src/jp_milp/core.py、linear.py、audit.py的数值/等价压缩修改，以及新增本目录滚动驱动和汇总脚本。复合等容量候选仅在证明为完整网格且域约束已由满方向功率约束覆盖时压缩，其他菜单沿用原实现。固定功率直接计算充放电，不再重复引入方向二元。极小状态权重保留至1e-12，整数解固定后精修连续变量；不增加设备容量或修改冻结订单。初始SOC仅允许1e-9 MWh内浮点边界归整，并逐窗记录。货币审计将已规定的SOC容差按终端价格换算为日元。','',
        '区域来源、官方历史规则与规则/假设区分见[全期输入说明](../jp_shikoku_202601_0830/full_run_k1.md)。本轮复用EPRX历史规程及行情、四国送配电LFC/EDC、JEPX现货快照，没有新增规则结论或外部抓取。完整运行配置、代码指纹、源包指纹、逐窗状态与服务路径在各场景manifest和windows目录中。初期失败版本保留，不参与本报告。历史窗口未完整纳入numeric_states.py辅助脚本哈希；当前源码快照是补充证据，历史身份覆盖缺口保留，见source_snapshot_manifest_v2.json。','',
        '正式结果目录：EV为`outputs/JP/revenue_20261005_v10/`，高压一次为`outputs/JP/revenue_20261005_v8/`，高压复合为`outputs/JP/revenue_20261005_v11/`。各场景提供executed_30min.csv、monthly_cash.json、solver_metrics.json、summary.json以及压缩逐窗事务。本轮数值实现已由独立审核Agent复核：无P0/P1问题，两项P2证据/文字问题已补充；审核范围和验证见review_validation.json。三组全期账本已由主线程核验并通过独立审核Agent最终验收，24行月度明细亦一致；最终审核记录见review_validation.json。',
        '', '运行使用HiGHS 1.15.1及PySCIPOpt 6.2.1/SCIP接口，每场景单线程；续跑求解器和代码指纹逐窗记录。先构建保持既有承诺、暂不新增容量的可行起点，再释放全部新容量进行优化；起点不是最终结果。一次频率中权重低于1e-8的状态向同方向邻近状态合并，保留正负平均激活量，满方向服务极端不删除；固定调度下全期充放电量合并误差保守上界为高压0.001829 MWh、EV 0.00003658 MWh，见numerical_state_validation.json。该数值界不等于收益误差界。40项回归通过，包括等容量压缩等价性、EV日恢复、状态合并、原有模型、冻结及规则切换。']
    (HERE/'收益测算结果.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(values,ensure_ascii=False,indent=2))
