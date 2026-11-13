"""Look at labeled HP and PV distributions before setting rule thresholds."""
import numpy as np, pandas as pd
P='/Users/giocaballero/avangrid-hackathon/data/processed/'
F=pd.read_parquet(P+'features.parquet'); L=np.load(P+'load_present.npy', mmap_mode='r')
n=len(F); hours=pd.date_range('2025-09-01',periods=8760,freq='h'); hod=hours.hour.to_numpy(); mo=hours.month.to_numpy()
q=[.1,.25,.5,.75,.9]
for c in ['heat_kwh_yr','winter_ratio','heat_nonlin','b_heat_mild','b_heat_cold','cold_kw_lift','b_cool','hot_kw_lift','cool_kwh_yr']:
    print(c, 'HP', np.round(F.loc[F.lab_hp==1,c].quantile(q).values,2), 'ALL', np.round(F[c].quantile(q).values,2))
for t in [1500,2500,3000,4000,6000]:
    f=F.heat_kwh_yr>=t; print('heat>=',t,'flag',f.sum(),'HP recall',f[F.lab_hp==1].mean().round(2))
# PV
for t in [0.01,0.03,0.05,0.1,0.2]:
    f=F.zero_mid_summer>=t; print('zero_mid>=',t,'flag',f.sum(),'PV recall',f[F.lab_pv==1].mean().round(3),'precision',F.lab_pv[f].mean().round(3))
Ls=np.asarray(L)
sum_eve=np.isin(mo,[5,6,7,8])&(hod>=19)&(hod<=23)
zeve=(Ls[:,sum_eve]==0).mean(1)
win_mid=np.isin(mo,[12,1,2])&(hod>=10)&(hod<=14)
zwin=(Ls[:,win_mid]==0).mean(1)
F['zero_eve_summer']=zeve; F['zero_mid_winter']=zwin
pv=F.zero_mid_summer>=0.05
print(pd.crosstab(pv, F.lab_pv))
print('PV zero_eve_summer dist', np.round(np.quantile(zeve[pv],[.5,.75,.9,.95,.99]),3), '>=0.2:',(zeve[pv]>=0.2).sum(), '>=0.5:',(zeve[pv]>=0.5).sum())
print('allzero year', (F.annual_kwh==0).sum(), ' annual<300', (F.annual_kwh<300).sum())
print(F.loc[pv&(F.lab_pv==0),['annual_kwh','zero_mid_summer','zero_night','zero_eve_summer','zero_mid_winter','low_days']].describe().round(2))
