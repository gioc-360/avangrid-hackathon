import numpy as np, pandas as pd, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, os
OUT=os.path.expanduser('~/mnt/00_Hackathon Materials/_prototype'); os.makedirs(OUT,exist_ok=True)
df=pd.read_csv('features.csv',index_col=0); seg=pd.read_csv('seg_k5.csv',index_col=0).seg.astype(str)
v=df.loc[seg.index].copy(); v['seg']=seg
names={'4':'High use, heavy AC','0':'Evening AC peakers','3':'Steady mid users','1':'Low use, light cooling','2':'Electric heating homes','V':'Seasonal and intermittent','S':'Solar prosumers'}
order=['4','0','3','1','2','V','S']
col={'4':'#d62728','0':'#ff7f0e','3':'#8c564b','1':'#7f7f7f','2':'#1f77b4','V':'#9467bd','S':'#2ca02c'}
v['segment']=v.seg.map(names)
Z=np.load('feat_device.npz'); prof=pd.DataFrame(index=df.index)
P=Z['prof']  # N,3season,2(wkday/wkend),24
pos=df.index.get_indexer(v.index)
fig,ax=plt.subplots(1,2,figsize=(13,4.6),sharey=True)
for j,(si,title) in enumerate([(1,'Summer weekday (Jun to Aug)'),(0,'Winter weekday (Dec to Feb)')]):
    for s in order:
        m=pos[(v.seg==s).values]; ax[j].plot(range(24),np.nanmedian(P[m,si,0,:],0),label=names[s],color=col[s],lw=2.2 if s in '42' else 1.6)
    ax[j].axvspan(15,20,color='grey',alpha=.12); ax[j].set_title(title); ax[j].set_xlabel('Hour of day (start)'); ax[j].set_xticks(range(0,24,3)); ax[j].grid(alpha=.3)
ax[0].set_ylabel('Median kWh per hour'); fig.legend(*ax[0].get_legend_handles_labels(),loc='lower center',ncol=7,fontsize=8.5,frameon=False); fig.suptitle('Typical day by segment (grey band = system peak window, 3pm to 8pm)')
fig.tight_layout(rect=(0,0.07,1,1)); fig.savefig(f'{OUT}/01_segment_daily_profiles.png',dpi=150); plt.close()
# temperature response
T=np.load('daily_temp.npy'); D=Z['daily']; bins=np.arange(-5,90,5); bc=(bins[:-1]+bins[1:])/2; b=np.digitize(T,bins)-1
fig,ax=plt.subplots(figsize=(7.5,4.6))
for s in order:
    m=pos[(v.seg==s).values]; med=np.nanmedian(D[m],0)
    y=[np.nanmean(med[b==i]) if (b==i).any() else np.nan for i in range(len(bc))]
    ax.plot(bc,y,'-o',ms=3,label=names[s],color=col[s])
ax.set_xlabel('Daily average temperature (°F)'); ax.set_ylabel('Median daily kWh'); ax.set_title('How each segment responds to temperature'); ax.grid(alpha=.3); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(f'{OUT}/02_temperature_response.png',dpi=150); plt.close()
# share of customers vs share of peaks
g=v.groupby('seg'); sh=pd.DataFrame({'Customers':g.size()/len(v)*100,'Annual energy':g.annual_kwh.sum()/v.annual_kwh.sum()*100,'Summer peak':g.coinc_summer_kw.sum()/v.coinc_summer_kw.sum()*100,'Winter peak':g.coinc_winter_kw.sum()/v.coinc_winter_kw.sum()*100}).loc[order]
fig,ax=plt.subplots(figsize=(11,4.6)); w=.2; x=np.arange(len(order))
for i,(c,cc) in enumerate(zip(sh.columns,['#bbbbbb','#555555','#d62728','#1f77b4'])):
    ax.bar(x+(i-1.5)*w,sh[c],w,label=c,color=cc)
ax.set_xticks(x); ax.set_xticklabels([names[s].replace(', ',',\n').replace(' and ','\nand ').replace('Electric heating homes','Electric\nheating homes') for s in order],fontsize=9); ax.set_ylabel('% of total'); ax.legend(); ax.grid(axis='y',alpha=.3)
ax.set_title('Share of customers vs share of energy and system peak (top 100 summer and winter hours)')
fig.tight_layout(); fig.savefig(f'{OUT}/03_peak_contribution.png',dpi=150); plt.close()
# summary table
base_ev=v.lab_EV.mean(); base_hp=v.lab_HP.mean()
t=pd.DataFrame({'Customers':g.size(),'Share %':g.size()/len(v)*100,'Median kWh/yr':g.annual_kwh.median(),'Median max kW':g.pmax.median(),'Night baseload kW':g.base_night_p05.median(),
 'Heating slope kWh/day/F':g.heat_slope.median(),'Cooling slope kWh/day/F':g.cool_slope.median(),'Winter/summer kWh':g.winter_summer_ratio.median(),'Evening share %':g.evening_share.median()*100,
 'Load factor':g.load_factor.median(),'Avg kW at summer peak':g.coinc_summer_kw.median(),'Avg kW at winter peak':g.coinc_winter_kw.median(),
 'Summer peak share %':sh['Summer peak'],'Winter peak share %':sh['Winter peak'],'Labeled EV rate %':g.lab_EV.mean()*100,'EV lift vs avg':g.lab_EV.mean()/base_ev,'Labeled HP rate %':g.lab_HP.mean()*100,'HP lift vs avg':g.lab_HP.mean()/base_hp,'Labeled PV rate %':g.lab_PV.mean()*100}).loc[order]
t.index=[names[s] for s in order]; t.round(2).to_csv(f'{OUT}/segment_summary.csv'); print(t.round(2).T.to_string())
v[['segment']].to_csv(f'{OUT}/customer_segments.csv')
print('files',os.listdir(OUT))
