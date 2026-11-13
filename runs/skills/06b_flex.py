"""Demand flexibility without a battery: weather-driven load sitting in the system peak hours.
cooling load at summer peak = load in summer top-20 system hours - same-hour load on weather-neutral days (55-70 F)
heating load at winter peak = same, winter top-20. A 50% thermostat setback/cycling share is an ASSUMPTION."""
import json, numpy as np, pandas as pd
OUT='/Users/giocaballero/avangrid-hackathon/runs/skills/'; P='/Users/giocaballero/avangrid-hackathon/data/processed/'
L=np.load(P+'load_present.npy',mmap_mode='r'); C=pd.read_parquet(OUT+'classes.parquet'); B=pd.read_parquet(OUT+'battery.parquet')
n=len(C); hours=pd.date_range('2025-09-01',periods=8760,freq='h')
t=pd.read_parquet(P+'weather.parquet').temp.to_numpy(); tday=t.reshape(365,24).mean(1)
neutral=np.repeat((tday>=55)&(tday<=70),24); hod=hours.hour.to_numpy()
pk=json.load(open(P+'system_peaks.json')); A=np.asarray(L)
res={}
for s in ['summer','winter']:
    idx=np.array([hours.get_loc(pd.Timestamp(h)) for h in pk[f'top_{s}_hours']])
    base=np.stack([A[:,neutral&(hod==h)].mean(1) for h in hod[idx]],1)
    res[s]=np.clip(A[:,idx]-base,0,None).mean(1)
SH=0.5
print('weather-driven kW at system peak (mean over 20 top hours), all 25,653 homes:')
for s in res: print(f'  {s}: total {res[s].sum()/1000:.1f} MW; 50% flex share = {SH*res[s].sum()/1000:.1f} MW; median home {np.median(res[s]):.2f} kW')
for nm,m in [('central AC',C.ac_central),('electric heat',C.elec_heat),('T3 tier',B.tier.str.startswith('T3')),('T1 tier',B.tier.str.startswith('T1'))]:
    m=np.asarray(m); print(f'  {nm:14s} n={m.sum():5d}: summer flex {SH*res["summer"][m].sum()/1000:.2f} MW, winter flex {SH*res["winter"][m].sum()/1000:.2f} MW')
# NET line inputs (ASSUMPTIONS): installed cost per IQ 10C unit, life 15 y (warranty in brief)
for cost in [9000,13000]:
    for tier in ['T1 electrified peaker','T3 summer peaker (DR first)']:
        sub=B[B.tier==tier]; capex=(sub.units*cost).sum(); val=sub.value_total_usd.sum()
        print(f'cost ${cost}/unit {tier}: capex ${capex/1e6:.1f}M, value ${val/1e6:.2f}M/yr, simple payback {capex/val:.0f} y vs 15 y warranty')
pd.DataFrame({'CUSTOMER_NUMBER':C.CUSTOMER_NUMBER,'flex_summer_kw':res['summer'],'flex_winter_kw':res['winter']}).to_parquet(OUT+'flex.parquet')
