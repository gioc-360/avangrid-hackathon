import numpy as np, pandas as pd, matplotlib, os; matplotlib.use('Agg'); import matplotlib.pyplot as plt
OUT=os.path.expanduser('~/mnt/00_Hackathon Materials/_prototype'); v=pd.read_pickle('ranked.pkl'); sc=np.load('scen.npz')
S=sc['s0']; B=sc['s1']; B2=sc['s2']; BF=sc['s3']; ts=pd.date_range('2025-09-01',periods=8760,freq='h'); M=np.load('kwh.npy',mmap_mode='r')
# 1 heat wave
i0=ts.get_loc(pd.Timestamp('2026-07-01 00:00')); sl=slice(i0,i0+96); x=ts[sl]
fig,ax=plt.subplots(figsize=(12,4.6))
ax.plot(x,S[sl],color='#444',lw=2,label='Today'); ax.plot(x,B[sl],color='#1f77b4',lw=2,label=f'With {(v.tier=="Priority").sum():,} priority batteries (staggered)')
ax.plot(x,BF[sl],color='#2ca02c',lw=1.8,ls='--',label='Batteries + thermostats + EV managed charging')
ax.axhline(S.max(),color='#d62728',lw=.8,ls=':'); ax.text(x[2],S.max()+.4,f'Today\'s peak {S.max():.1f} MW',color='#d62728',fontsize=9)
ax.axhline(B.max(),color='#1f77b4',lw=.8,ls=':'); ax.text(x[2],B.max()+.4,f'New peak {B.max():.1f} MW (cut {S.max()-B.max():.1f} MW, {100*(S.max()-B.max())/S.max():.0f}%)',color='#1f77b4',fontsize=9)
ax.set_ylabel(f'Combined load of {len(v):,} customers (MW)'); ax.set_title('July 1 to 4 heat wave: batteries flatten the top hours (top 50 hours fall on only 10 days)')
ax.legend(fontsize=9,loc='lower right'); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(f'{OUT}/06_heatwave_peak_reduction.png',dpi=140); plt.close()
# 2 prioritization scatter
smp=v.sample(6000,random_state=1); col={'Priority':'#d62728','Secondary':'#ff9896','Not a battery candidate':'#c7c7c7'}
fig,ax=plt.subplots(figsize=(8.5,5.6))
for t in ['Not a battery candidate','Secondary','Priority']:
    s=smp[smp.tier==t]; ax.scatter(s.load_top50,s.red2_top50,s=6,color=col[t],label=f'{t} ({(v.tier==t).sum():,})',alpha=.8)
ax.axvline(4,color='#d62728',lw=1,ls='--'); ax.axhline(2.0,color='#d62728',lw=1,ls='--'); ax.axvline(3,color='#ff9896',lw=1,ls=':')
ax.text(4.1,0.15,'Priority: ≥ 4 kW at top hours\nand battery cuts ≥ 2 kW',fontsize=8.5,color='#d62728')
ax.set_xlim(0,12); ax.set_xlabel('Customer load during the top 50 system hours (average kW)'); ax.set_ylabel('Battery reduction at top 50 hours (kW, 2 units, behind the meter)')
ax.set_title('Threshold method: who gets a battery'); ax.legend(fontsize=8.5,loc='lower right'); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(f'{OUT}/07_battery_threshold.png',dpi=140); plt.close()
# 3 candidates by segment
order=['High use, heavy AC','Electric heating homes','Steady mid users','Evening AC peakers','Seasonal and intermittent','Solar prosumers','Low use, light cooling']
ct=pd.crosstab(v.segment,v.tier).reindex(order).fillna(0); share=(ct.get('Priority',0)/ct.sum(1)*100)
fig,ax=plt.subplots(figsize=(10,4.4)); y=np.arange(len(order))
ax.barh(y,ct['Priority'],color='#d62728',label='Priority'); ax.barh(y,ct['Secondary'],left=ct['Priority'],color='#ff9896',label='Secondary')
for i,s in enumerate(order): ax.text(ct.loc[s,['Priority','Secondary']].sum()+20,i,f'{share[s]:.0f}% of segment is priority',va='center',fontsize=8.5)
ax.set_yticks(y); ax.set_yticklabels(order); ax.invert_yaxis(); ax.set_xlabel('Customers'); ax.set_title('Battery candidates by segment: heavy AC homes dominate'); ax.legend(fontsize=9); ax.set_xlim(0,ct[['Priority','Secondary']].sum(1).max()*1.35)
ax.grid(axis='x',alpha=.3); fig.tight_layout(); fig.savefig(f'{OUT}/08_candidates_by_segment.png',dpi=140); plt.close()
# 4 example customer on July 2: before/after behind the meter (water-fill over day's top 6 system hours)
Sd=S.reshape(365,24); d=ts.get_loc(pd.Timestamp('2026-07-02'))//24; h6=np.sort(np.argsort(-Sd[d])[:6])
P=v[v.tier=='Priority']; cid=P.iloc[(P.red2_top50-P.red2_top50.median()).abs().argsort().iloc[0]].name
L=np.nan_to_num(np.array(M[cid-1]).reshape(365,24)[d]); E,Pw=16.128,7.68
lo,hi=0,L.max()
for _ in range(50):
    mid=(lo+hi)/2; e=np.minimum(np.clip(L[h6]-mid,0,None),Pw).sum(); lo,hi=(mid,hi) if e>E else (lo,mid)
after=L.copy(); after[h6]=L[h6]-np.minimum(np.clip(L[h6]-hi,0,None),Pw)
chg=(L[h6]-after[h6]).sum()/0.894/7; night=L.copy(); night[0:7]+=chg
fig,ax=plt.subplots(figsize=(9,4.4)); hrs=np.arange(24)
ax.bar(hrs,L,color='#c7c7c7',label='Home load today'); ax.bar(hrs,after,color='#1f77b4',label='With battery')
ax.bar(hrs[0:7],[chg]*7,bottom=L[0:7],color='#2ca02c',alpha=.6,label=f'Slow overnight charging ({chg:.1f} kW)')
for h in h6: ax.axvspan(h-.5,h+.5,color='#ffdd99',alpha=.35,zorder=0)
ax.set_xticks(range(0,24,2)); ax.set_xlabel('Hour of day (shaded = system top 6 hours, July 2)'); ax.set_ylabel('kWh per hour')
ax.set_title(f'Example priority customer (heavy AC), July 2: load in the system top 6 hours cut from {L[h6].mean():.1f} to {after[h6].mean():.1f} kW'); ax.legend(fontsize=8.5); ax.grid(axis='y',alpha=.3)
fig.tight_layout(); fig.savefig(f'{OUT}/09_example_customer_day.png',dpi=140); plt.close()
keep=['segment','tier','score','units','load_top50','red_top50','kwh_yr','loss_cost_usd','thermostat_kw','ev_shift_top50','electric_heat','air_conditioning','ev','solar']
v[v.tier!='Not a battery candidate'][keep].sort_values('score',ascending=False).round(3).to_csv(f'{OUT}/battery_candidates.csv')
print('example',cid)
