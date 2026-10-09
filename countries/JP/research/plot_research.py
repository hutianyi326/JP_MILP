from pathlib import Path
import pandas as pd,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
B=Path(__file__).resolve().parent;A=B/'analysis';F=B/'figures'
plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','DejaVu Sans'],'axes.unicode_minus':False,'font.size':9})
areas=['北海道','東北','東京','中部','北陸','関西','中国','四国','九州']
def finish(fig,name,title,diagnostic=False):
    fig.suptitle(title,fontsize=14,y=.99)
    fig.text(.02,.01,'来源：官方CSV，2026-09-28获取；JST；事后描述性统计。'+('  诊断图：离岛边界未闭合，禁止作为基线合规数据或模型输入。' if diagnostic else '  历史价差不等于储能收益。'),fontsize=8)
    fig.tight_layout(rect=[0,.09 if name=='generation_profiles_DIAGNOSTIC.png' else .04,1,.96]);fig.savefig(F/name,dpi=160);plt.close(fig)
p=pd.read_csv(A/'price_monthly.csv');m=p.pivot(index='area',columns='month',values='mean_JPY_kWh').reindex(areas)
fig,ax=plt.subplots(figsize=(13,5));im=ax.imshow(m,aspect='auto',cmap='YlOrRd');ax.set_yticks(range(9),areas);ax.set_xticks(range(20),m.columns,rotation=60);fig.colorbar(im,ax=ax,label='JPY/kWh');finish(fig,'price_heatmap.png','九区域日前现货月均价格 | 2025-01—2026-08')
d=pd.read_csv(A/'fundamentals_30min_DIAGNOSTIC.csv',low_memory=False);d['timestamp']=pd.to_datetime(d.timestamp);d['month']=d.timestamp.dt.strftime('%Y-%m');d['slot']=d.timestamp.dt.hour*2+d.timestamp.dt.minute//30
fig,axes=plt.subplots(3,3,figsize=(14,10))
for a,ax in zip(areas,axes.flat):
    s=d[(d.area==a)&(d.month=='2026-04')].groupby('slot').mean(numeric_only=True)
    ax.plot(s.index/2,s['エリア需要']/1000,label='负荷');ax.plot(s.index/2,s.residual_load_MW/1000,label='净负荷');ax.set_title(a);ax.set_ylabel('GW');ax.set_xlabel('JST小时');a2=ax.twinx();a2.plot(s.index/2,s.price_JPY_kWh,color='tab:red',ls='--',label='现货价');a2.set_ylabel('JPY/kWh');ax.grid(alpha=.2)
axes.flat[0].plot([],[],color='tab:red',ls='--',label='现货价（右轴）');axes.flat[0].legend(loc='upper left');finish(fig,'load_price_profiles_DIAGNOSTIC.png','2026年4月平均日内曲线 | 净负荷=负荷−光伏−风电',True)
fuels=['原子力','火力(LNG)','火力(石炭)','火力(石油)','火力(その他)','水力','地熱','バイオマス','太陽光発電実績','風力発電実績']
fig,axes=plt.subplots(3,3,figsize=(14,10))
for a,ax in zip(areas,axes.flat):
    s=d[(d.area==a)&(d.month=='2026-04')].groupby('slot').mean(numeric_only=True);cols=[c for c in fuels if s[c].notna().all()]
    ax.stackplot(s.index/2,*[s[c]/1000 for c in cols],labels=cols,colors=[plt.get_cmap('tab20')(fuels.index(c)*2) for c in cols]);ax.plot(s.index/2,s['エリア需要']/1000,'k--',lw=1);ax.set_title(a+('（缺少部分分类）' if len(cols)<len(fuels) else ''));ax.set_ylabel('GW');ax.set_xlabel('JST小时')
handles,labels=axes.flat[0].get_legend_handles_labels();fig.legend(handles,labels,ncol=5,loc='lower center',bbox_to_anchor=(.5,.035),fontsize=8);finish(fig,'generation_profiles_DIAGNOSTIC.png','2026年4月平均日内分电源出力 | 不含净抽蓄、电池及联络线堆叠',True)
mix=pd.read_csv(A/'installed_mix_DIAGNOSTIC.csv');cols=['oil_other','coal','LNG','nuclear','hydro','pumped','solar','wind','other_new_energy','other'];fig,ax=plt.subplots(figsize=(13,6));v=mix[mix.fiscal_year_end==2025].set_index('area').reindex(areas);bot=np.zeros(9)
for c in cols:ax.bar(areas,v[c],bottom=bot,label=c);bot+=v[c]
ax.legend(ncol=5,loc='upper center',bbox_to_anchor=(.5,-.07));ax.set_ylabel('%');finish(fig,'installed_mix_DIAGNOSTIC.png','供给计划报告中的2025财年末装机占比 | O11 图3-2转录，非已核验实绩',True)
fig,axes=plt.subplots(3,3,figsize=(14,10))
for a,ax in zip(areas,axes.flat):
    s=d[(d.area==a)&(d.timestamp.dt.year==2025)]
    for c,label in [('エリア需要','负荷'),('residual_load_MW','净负荷')]:
        x=s[c].dropna().sort_values(ascending=False).to_numpy();ax.plot(np.arange(len(x))/len(x)*100,x/1000,label=label)
    ax.set_title(a);ax.set_xlabel('持续占比%');ax.set_ylabel('GW');ax.grid(alpha=.2)
axes.flat[0].legend();finish(fig,'load_duration_DIAGNOSTIC.png','2025年负荷与净负荷持续曲线',True)
bb=pd.read_csv(A/'netload_price_bins_DIAGNOSTIC.csv');fig,ax=plt.subplots(figsize=(11,6))
for a in areas:
    v=bb[bb.area==a];ax.plot(range(1,len(v)+1),v.price_mean_JPY_kWh,'o-',label=a)
ax.set_xticks(range(1,6));ax.set_xlabel('区域自身净负荷五分位组（低→高）');ax.set_ylabel('平均现货价格 JPY/kWh');ax.legend(ncol=3);ax.grid(alpha=.2);finish(fig,'netload_price_bins_DIAGNOSTIC.png','2025-01—2026-08净负荷分箱与现货价格 | 相关性不构成因果识别',True)
print('6 figures written')
