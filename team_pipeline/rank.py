import numpy as np, pandas as pd
b=pd.read_csv('battery_sim.csv',index_col=0); f=pd.read_csv('features.csv',index_col=0)
cls=pd.read_csv('classification.csv',index_col=0,keep_default_na=False)
seg=pd.read_csv('seg_k5.csv',index_col=0).seg.astype(str)
names={'4':'High use, heavy AC','0':'Evening AC peakers','3':'Steady mid users','1':'Low use, light cooling','2':'Electric heating homes','V':'Seasonal and intermittent','S':'Solar prosumers'}
v=b.loc[cls.index].join(cls).join(f[['mean_kw','annual_kwh']]); v['segment']=seg.map(names)
v['coinc_ratio']=v.load_top50/v.mean_kw.clip(lower=0.05)
v['elec']=(v.ev.isin(['High','Medium'])|(v.electric_heat=='Primary')).astype(int)
pr=lambda s: s.rank(pct=True)
v['score']=(100*(0.40*pr(v.red2_top50)+0.30*pr(v.load_top50)+0.15*pr(v.coinc_ratio)+0.15*v.elec)).round(1)
print('red2 pct',v.red2_top50.quantile([.5,.75,.9,.95]).round(2).to_dict(),' load_top50 pct',v.load_top50.quantile([.5,.75,.9,.95]).round(2).to_dict())
for thr in [1.5,1.8,2.0]:
    for lt in [3,4]:
        c=(v.red2_top50>=thr)&(v.load_top50>=lt); print(f'red2>={thr} & load_top50>={lt}: {c.sum()}')
v['tier']=np.where((v.load_top50>=4)&(v.red2_top50>=2.0),'Priority',np.where((v.load_top50>=3)&(v.red2_top50>=1.5),'Secondary','Not a battery candidate'))
v['units']=np.where(v.red1_top50>=0.85*v.red2_top50,1,2)
v['red_top50']=np.where(v.units==1,v.red1_top50,v.red2_top50); v['kwh_yr']=np.where(v.units==1,v.kwh1_yr,v.kwh2_yr)
v['loss_cost_usd']=(v.kwh_yr*(1/0.894-1)*0.2315).round(2)
v['thermostat_kw']=np.where(v.air_conditioning=='Central likely',0.25*v.ac_kw_top50,0)   # ASSUMED 25% of AC load
v.to_pickle('ranked.pkl')
P=v[v.tier=='Priority']; Sx=v[v.tier=='Secondary']
print('\nPRIORITY',len(P),'units: 1u',(P.units==1).sum(),'2u',(P.units==2).sum())
print(' avg load at top50 %.2f kW, avg reduction %.2f kW (%.0f%%)'%(P.load_top50.mean(),P.red_top50.mean(),100*P.red_top50.sum()/P.load_top50.sum()))
print(' BTM reduction at top 50 hours total MW %.2f ; kWh shifted per yr total %.0f MWh ; avg loss cost $%.0f/yr'%(P.red_top50.sum()/1000,P.kwh_yr.sum()/1000,P.loss_cost_usd.mean()))
print(' by segment', P.segment.value_counts().to_dict())
print(' electrified already',P.elec.sum(),' not yet (electrification enablement)',(1-P.elec).sum(), ' solar',(P.solar!='No').sum())
print('SECONDARY',len(Sx),' MW %.2f'%(Sx.red2_top50.sum()/1000))
print('Thermostat potential (central AC, 25%% of AC load at top hours): all %.2f MW ; priority %.2f MW'%(v.thermostat_kw.sum()/1000,P.thermostat_kw.sum()/1000))
print('EV managed charging at top hours: %.3f MW from %d EV customers'%(v.ev_shift_top50.sum()/1000,(v.ev.isin(["High","Medium"])).sum()))
print('Charging creates new personal peak on >=1 event day (priority):',(P.charge_new_peak>0).mean().round(2))
# system view: top 50 hour reduction from priority batteries (BTM) - compute hourly
