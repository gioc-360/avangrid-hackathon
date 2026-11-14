import numpy as np, pandas as pd, matplotlib, os; matplotlib.use('Agg'); import matplotlib.pyplot as plt
OUT=os.path.expanduser('~/mnt/00_Hackathon Materials/_prototype'); M=np.load('kwh.npy',mmap_mode='r')
v=pd.read_pickle('v_scored.pkl'); c=pd.read_csv('classification.csv',index_col=0,keep_default_na=False); Td=np.load('daily_temp.npy')
Z=np.load('feat_device.npz'); D=Z['daily']; P=Z['prof']; allidx=pd.read_csv('features.csv',index_col=0).index
days=pd.date_range('2025-09-01',periods=365,freq='D')
ink='#222'; acc='#d62728'; blue='#1f77b4'; grey='#999'
fig,ax=plt.subplots(2,3,figsize=(15,8.4))
# 1 EV: labeled high-tier EV with most mild blocks; show 7 mild days
cand=v[(c.ev=='High')&(v.lab_EV==1)].sort_values('ev_mild_45_2',ascending=False).index[0]
x=np.array(M[cand-1]).reshape(365,24); mild=np.where((Td>=50)&(Td<=65))[0]
st=mild[np.argmax([np.nanmax(x[d]) for d in mild[:-7]])]; wk=x[st:st+7].ravel()
ax[0,0].plot(np.arange(len(wk)),wk,color=acc,lw=1.6); ax[0,0].set_title('EV (Level 2): short 9 to 13 kW blocks, mild weather',fontsize=10.5)
ax[0,0].set_xticks(range(0,168,24)); ax[0,0].set_xticklabels([d.strftime('%a %b %d') for d in days[st:st+7]],fontsize=7.5,rotation=20); ax[0,0].set_ylabel('kWh per hour')
# 2 Electric heat: daily kWh vs temp, primary vs none (median customers)
def med_daily(mask):
    pos=allidx.get_indexer(c.index[mask]); return np.nanmedian(D[pos],0)
for lab,mask,col in [('Primary electric heat',c.electric_heat=='Primary',blue),('Supplemental',c.electric_heat=='Supplemental','#6baed6'),('No electric heat',c.electric_heat=='No',grey)]:
    ax[0,1].scatter(Td,med_daily(mask),s=7,color=col,label=f'{lab} ({mask.sum():,})')
ax[0,1].set_title('Electric heating: use climbs as temperature falls',fontsize=10.5); ax[0,1].set_xlabel('Daily average temperature (°F)'); ax[0,1].set_ylabel('Median daily kWh'); ax[0,1].legend(fontsize=8)
# 3 AC
for lab,mask,col in [('Central AC likely','Central likely','#ff7f0e'),('Room or light use','Room or light use','#fdae6b'),('No AC signal','No',grey)]:
    m=c.air_conditioning==mask; ax[0,2].scatter(Td,med_daily(m),s=7,color=col,label=f'{lab} ({m.sum():,})')
ax[0,2].set_title('Air conditioning: use climbs above about 60°F',fontsize=10.5); ax[0,2].set_xlabel('Daily average temperature (°F)'); ax[0,2].legend(fontsize=8)
# 4 Pool: mild summer vs mild spring profile for pool-possible vs others
ms=np.isin(days.month,[6,7,8,9])&(Td>=58)&(Td<=70); sp=np.isin(days.month,[4,5,10])&(Td>=50)&(Td<=66)
def prof(mask_c,mask_d):
    pos=allidx.get_indexer(c.index[mask_c]); out=np.zeros(24)
    X=np.stack([np.array(M[p]).reshape(365,24)[mask_d].mean(0) for p in pos[:300]]); return np.nanmedian(X,0)
pm=c.pool=='Possible'
ax[1,0].plot(prof(pm,ms),color='#17becf',lw=2,label='Possible pool: mild summer days'); ax[1,0].plot(prof(pm,sp),color='#17becf',lw=2,ls='--',label='Possible pool: mild spring days')
ax[1,0].plot(prof(~pm,ms),color=grey,lw=1.5,label='Others: mild summer days'); ax[1,0].plot(prof(~pm,sp),color=grey,lw=1.5,ls='--',label='Others: mild spring days')
ax[1,0].set_title(f'Pool (exploratory, {pm.sum()}): summer only lift on mild days',fontsize=10.5); ax[1,0].set_xlabel('Hour of day'); ax[1,0].set_ylabel('Median kWh per hour'); ax[1,0].legend(fontsize=7.5)
# 5 Solar
pos=allidx.get_indexer(c.index[c.solar!='No']); pos0=allidx.get_indexer(c.index[c.solar=='No'])
ax[1,1].plot(np.nanmedian(P[pos,1,0],0),color='#2ca02c',lw=2,label=f'Solar ({(c.solar!="No").sum()})'); ax[1,1].plot(np.nanmedian(P[pos0,1,0],0),color=grey,lw=1.5,label='All others')
ax[1,1].set_title('Solar: midday use drops to zero (exports not metered)',fontsize=10.5); ax[1,1].set_xlabel('Hour of day (summer weekdays)'); ax[1,1].legend(fontsize=8)
# 6 EV validation bars: labeled EV rate by tier
tiers=['High','Medium','Low','No']; rate=[v.lab_EV[c.ev==t].mean()*100 for t in tiers]
ax[1,2].bar(tiers,rate,color=[acc,'#ff9896','#fdd0a2',grey]); 
for i,r in enumerate(rate): ax[1,2].text(i,r+0.2,f'{r:.1f}%',ha='center',fontsize=9)
ax[1,2].set_title('Check: share of known EV customers by EV tier',fontsize=10.5); ax[1,2].set_ylabel('% of tier on the known EV list')
for a in ax.ravel(): a.grid(alpha=.3)
fig.suptitle('Part 1: load signatures used to classify technologies',fontsize=13); fig.tight_layout(); fig.savefig(f'{OUT}/04_technology_signatures.png',dpi=140); plt.close()
# segment x technology matrix
seg=pd.read_csv(f'{OUT}/customer_segments.csv',index_col=0).segment
t=pd.DataFrame({'Primary electric heat':c.electric_heat=='Primary','Supplemental electric heat':c.electric_heat=='Supplemental','Central AC':c.air_conditioning=='Central likely','EV (any tier)':c.ev!='No','EV high tier':c.ev=='High','Solar':c.solar!='No','Pool (possible)':c.pool=='Possible'}).join(seg)
mat=t.groupby('segment').mean()*100
order=['High use, heavy AC','Evening AC peakers','Steady mid users','Low use, light cooling','Electric heating homes','Seasonal and intermittent','Solar prosumers']; mat=mat.loc[order]
fig,ax=plt.subplots(figsize=(11,4.8)); im=ax.imshow(mat.values,cmap='Blues',aspect='auto',vmin=0,vmax=100)
ax.set_xticks(range(mat.shape[1])); ax.set_xticklabels(mat.columns,fontsize=9,rotation=15); ax.set_yticks(range(len(order))); ax.set_yticklabels(order,fontsize=9)
for i in range(mat.shape[0]):
    for j in range(mat.shape[1]): ax.text(j,i,f'{mat.values[i,j]:.0f}%',ha='center',va='center',fontsize=9,color='white' if mat.values[i,j]>55 else '#222')
ax.set_title('Share of each segment with each technology (Part 1 flags crossed with Part 2 segments)'); fig.tight_layout(); fig.savefig(f'{OUT}/05_segment_technology_matrix.png',dpi=140); plt.close()
c.join(seg).to_csv(f'{OUT}/customer_classification.csv')
mat.round(1).to_csv(f'{OUT}/segment_technology_matrix.csv'); print(mat.round(0).to_string())
