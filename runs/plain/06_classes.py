"""Part 1: final class flags + confidence tiers + label validation. Output out/classes.parquet, out/class_table.csv"""
import numpy as np, pandas as pd
P="/Users/giocaballero/avangrid-hackathon/data/processed/"; O="/Users/giocaballero/avangrid-hackathon/runs/plain/out/"
F=pd.read_parquet(O+"scored.parquet"); L=np.load(P+"load_present.npy",mmap_mode="r")
hours=pd.date_range("2025-09-01",periods=8760,freq="h"); hod=hours.hour.to_numpy(); mon=hours.month.to_numpy()
C=pd.DataFrame({"CUSTOMER_NUMBER":F.CUSTOMER_NUMBER})
# ---- solar
pv=(F.zero_mid_S>=0.05)&(F.zero_night_all<=0.02)&(F.zero_all<0.5)
C["pv"]=np.where(pv&(F.zero_mid_S>=0.2),"high",np.where(pv,"medium",np.where(F.lab_pv==1,"label-only","")))
# solar+battery: zeros that persist after dark (21-23h, May-Aug) in a PV home => battery serving evening load
idx=np.where(pv|(F.lab_pv==1))[0]; X=np.asarray(L[idx],np.float32)
dark=np.isin(mon,[5,6,7,8])&(hod>=21)
zd=(X[:,dark]==0).mean(1); C["zero_dark_S"]=0.0; C.loc[idx,"zero_dark_S"]=zd
C["pv_battery"]=np.where(C.zero_dark_S>=0.25,"medium",np.where(C.zero_dark_S>=0.08,"low",""))
# ---- EV
ev_hi=(F.l2_days_all>=20)&(F.l2_eve_share>=0.5)&(F.ev_hi5_days_shoulder>=5)
rank=(-F.score_ev).rank(method="first")
ev_med=(~ev_hi)&((rank<=560)|(F.l2_days_all>=10))
C["ev_l2"]=np.where(ev_hi,"high",np.where(ev_med,"medium",""))
heat=(F.heat_kwh_yr>=2000)&(F.cold_kw_lift>=1.0)
ev_l1=(C.ev_l2=="")&(F.ev_l1_nights_shoulder>=30)&(F.zero_night_all==0)
C["ev_l1"]=np.where(ev_l1,"low","")
# ---- AC
ac=(F.b_cool>=0.5)&(F.hot_kw_lift>=0.5)
C["ac"]=np.where(ac&(F.b_cool>=1.5)&(F.hot_kw_lift>=1.0),"high",np.where(ac,"medium",""))
# ---- electric heat
hp_rank=(-F.score_hp).rank(method="first")
res_like=heat&(F.heat_kwh_yr>=8000)&(F.winter_ratio>=2.5)&(F.b_cool<0.5)
hp_like=heat&~res_like&ac&(hp_rank<=2000)
C["elec_heat"]=np.where(heat&(F.heat_kwh_yr>=5000),"high",np.where(heat,"medium",""))
C["heat_type"]=np.where(res_like,"resistance-likely",np.where(hp_like,"heat-pump-likely",np.where(heat,"undetermined","")))
# ---- water heater, pool, hot tub
evany=C.ev_l2!=""
C["water_heater"]=np.where(((F.spike_morning+F.spike_night)>=30)&~evany,"low","")
pool=(F.pool_floor_delta_kw>=0.5)&(F.pool_delta_kwh_day>=8)
C["pool"]=np.where(pool&(F.pool_floor_delta_kw>=1.0),"high",np.where(pool,"medium",""))
C["hot_tub"]=np.where((F.spike_night>=30)&(F.spike_winter_share>=0.2)&~evany,"low","")
# ---- discovered segments
C["seasonal_home"]=np.where(((F.low_days>=60)|(F.min_month_share<0.15))&(F.annual_kwh>=500),"high","")
C["inactive"]=np.where(F.annual_kwh<500,"high","")
C["flat_24x7"]=np.where((F.load_factor>=0.45)&(F.base_kw>=1.5)&(F.annual_kwh>=15000),"medium","")
C.to_parquet(O+"classes.parquet")
rows=[]
for col,lab in [("pv","lab_pv"),("pv_battery",None),("ev_l2","lab_ev"),("ev_l1","lab_ev"),("ac",None),("elec_heat","lab_hp"),("heat_type","lab_hp"),("water_heater",None),("pool",None),("hot_tub",None),("seasonal_home",None),("inactive",None),("flat_24x7",None)]:
    for v in sorted(set(C[col])-{""}):
        m=C[col]==v; r={"class":col,"tier":v,"n":int(m.sum()),"share_%":round(100*m.mean(),2),
          "median_kwh":int(F.annual_kwh[m].median()),"median_peak_kw":round(F.peak_kw[m].median(),1),"median_sys_peak_kw":round(F.cs_kw[m].median(),2)}
        if lab: r["label_recall"]=round(m[F[lab]==1].mean(),3); r["labeled_in_flag"]=int((m&(F[lab]==1)).sum())
        rows.append(r)
T=pd.DataFrame(rows); T.to_csv(O+"class_table.csv",index=False); print(T.to_string())
anyev=C.ev_l2!=""; print("EV any L2 flag",anyev.sum(),"label recall",anyev[F.lab_ev==1].mean().round(3))
anypv=pv; print("PV flag",pv.sum(),"recall",pv[F.lab_pv==1].mean().round(3),"new (unlabeled) PV",(pv&(F.lab_pv==0)).sum())
print("PV labeled missed: their zero_mid_S median", F.zero_mid_S[(F.lab_pv==1)&~pv].median(), "zero_night_all median",F.zero_night_all[(F.lab_pv==1)&~pv].median(), "n",((F.lab_pv==1)&~pv).sum())
print("heat label recall",heat[F.lab_hp==1].mean().round(3),"; HP-like recall",hp_like[F.lab_hp==1].mean().round(3), "lift", (hp_like[F.lab_hp==1].mean()/hp_like[F.lab_hp==0].mean()).round(1))
print("labeled HP with AC signature", ac[F.lab_hp==1].mean().round(2),"vs all",ac.mean().round(2))
