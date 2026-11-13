import numpy as np, pandas as pd
O="/Users/giocaballero/avangrid-hackathon/runs/plain/out/"
F=pd.read_parquet(O+"scored.parquet")
def tab(name,mask,lab):
    m=mask.to_numpy(); y=F[lab].to_numpy()==1
    print(f"{name:55s} flagged {m.sum():6d} | labeled hit {m[y].sum():3d}/{y.sum()} = {m[y].mean():.2f} | unlabeled rate {m[~y].mean():.4f}")
for t in [5,10,20,40,80]:
    tab(f"l2_days_all>={t}",F.l2_days_all>=t,"lab_ev")
for t in [10,20,40]:
    tab(f"l2_days_all>={t} & eve_share>=0.5",(F.l2_days_all>=t)&(F.l2_eve_share>=0.5),"lab_ev")
for t in [5,10,20]:
    tab(f"ev_plateau2_shoulder>={t}",F.ev_plateau2_shoulder>=t,"lab_ev")
for t in [10,20,30]:
    tab(f"ev_l1_nights_shoulder>={t}",F.ev_l1_nights_shoulder>=t,"lab_ev")
print()
for h,c in [(1000,0.8),(1500,1.0),(2000,1.0),(3000,1.5),(5000,2)]:
    tab(f"heat_kwh_yr>={h} & cold_kw_lift>={c}",(F.heat_kwh_yr>=h)&(F.cold_kw_lift>=c),"lab_hp")
for t in [0.5,1.0,1.5]:
    tab(f"b_heat_cold>={t}",F.b_heat_cold>=t,"lab_hp")
tab("heat_nonlin>1.5 & heat_kwh>=1000",(F.heat_nonlin>1.5)&(F.heat_kwh_yr>=1000),"lab_hp")
print(F.loc[F.lab_ev==1,["annual_kwh","l2_days_all","l2_eve_share","ev_plateau2_shoulder","ev_l1_nights_shoulder","peak_kw","zero_mid_S"]].describe().round(2).to_string())
print(F.loc[F.lab_hp==1,["annual_kwh","heat_kwh_yr","cold_kw_lift","b_heat_mild","b_heat_cold","b_cool","winter_ratio","cw_kw"]].describe().round(2).to_string())
