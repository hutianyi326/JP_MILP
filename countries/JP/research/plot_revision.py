from pathlib import Path
import pandas as pd, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
B=Path(__file__).resolve().parent;A=B/'analysis';F=B/'figures'
plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','DejaVu Sans'],'axes.unicode_minus':False,'font.size':9})
areas=['北海道','東北','東京','中部','北陸','関西','中国','四国','九州']
d=pd.read_csv(A/'daytype_statistics_DIAGNOSTIC.csv');d=d[d.period=='2026年1至8月']
fig,axes=plt.subplots(1,2,figsize=(14,5))
for k,(typ,label) in enumerate([('Workday','其余周一至五'),('Weekend','其余周末'),('National-holiday','法定祝日/休日')]):
    v=d[d.day_type==typ].set_index('area').reindex(areas)
    for ax,col,unit in zip(axes,['load_mean_MW','price_mean_JPY_kWh'],['平均负荷 MW','日前均价 JPY/kWh']):
        ax.bar(np.arange(9)+(k-1)*.25,v[col],.25,label=label);ax.set_xticks(np.arange(9),areas);ax.set_ylabel(unit)
axes[0].legend();fig.suptitle('2026年1—8月：法定日历分类与负荷/价格（事后诊断）')
fig.text(.02,.01,'来源：内阁府H02、九家TSO、JEPX。假日优先，其余再分周末/周一至五；供需离岛边界未闭合；差异不证明节假日因果。',fontsize=8)
fig.tight_layout(rect=[0,.06,1,.94]);fig.savefig(F/'holiday_comparison_DIAGNOSTIC.png',dpi=160);plt.close(fig)
d=pd.read_csv(A/'intraday_30min_JST_expost.csv');d['month']=pd.to_datetime(d.timestamp).dt.strftime('%Y-%m')
m=d.groupby('month')[['reported_average_JPY_kWh','DA_system_JPY_kWh']].mean()
fig,ax=plt.subplots(figsize=(12,5));ax.plot(m.index,m.reported_average_JPY_kWh,'o-',label='日内公布平均价的时段均值');ax.plot(m.index,m.DA_system_JPY_kWh,'o-',label='日前系统价时段均值');ax.set_ylabel('JPY/kWh');ax.tick_params(axis='x',rotation=60);ax.legend();ax.grid(alpha=.2)
fig.suptitle('JEPX市场级日内与日前系统价 | 2025-01—2026-08')
fig.text(.02,.01,'来源：J16—J18、J08—J10；JST，事后修订版。市场级日内平均不是某区域可成交价；均差不等于储能收益。',fontsize=8)
fig.tight_layout(rect=[0,.06,1,.94]);fig.savefig(F/'intraday_vs_DA_system.png',dpi=160);plt.close(fig)
print('2 revision figures written')
