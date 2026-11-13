"""Part 3: candidates, sizing, value, enablement. Dollar values are ILLUSTRATIVE ASSUMPTIONS (see REPORT)."""
import numpy as np, pandas as pd
P_="/Users/giocaballero/avangrid-hackathon/data/processed/"; O="/Users/giocaballero/avangrid-hackathon/runs/plain/out/"
F=pd.read_parquet(O+"scored.parquet"); C=pd.read_parquet(O+"classes.parquet"); B=pd.read_parquet(O+"battery.parquet"); S=pd.read_parquet(O+"segments.parquet")
prof=np.load(O+"profiles.npy"); top_s=np.load(O+"top_s.npy"); top_w=np.load(O+"top_w.npy")
CAP=100.0; P_ON=0.30; P_OFF=0.18; RTE=0.894   # ASSUMPTIONS: $/kW-yr avoided capacity; TOU $/kWh on/off-peak
eligible=~S.segment.isin(["0 Inactive","1 Seasonal/part-year"])
B["cp_u1"]=np.maximum(B.cpS_u1,B.cpW_u1); B["cp_u2"]=np.maximum(B.cpS_u2,B.cpW_u2)
B["own_red_u1"]=B.peak-B.peak_after_u1; B["own_red_u2"]=B.peak-B.peak_after_u2
for u in (1,2): B[f"usd_u{u}"]=B[f"cp_u{u}"]*CAP+B[f"shift_kwh_u{u}"]*(P_ON-P_OFF/RTE)
# electrification enablement (incremental kW vs current annual peak; 3 kVA ~ 3 kW at PF 1)
for nm in ["ev","hp"]:
    inc0=B[f"{nm}_newpk_u0"]-B.peak; inc1=B[f"{nm}_newpk_u1"]-B.peak; inc2=B[f"{nm}_newpk_u2"]-B.peak
    B[f"{nm}_enable"]=np.select([inc0<=3,inc1<=3,inc2<=3],["no battery needed","1 unit","2 units"],"needs study even with battery")
    has=(C.ev_l2!="") if nm=="ev" else (C.elec_heat!="")
    print(f"\n{nm.upper()} addition, customers without it today (eligible):")
    print(B.loc[eligible&~has,f"{nm}_enable"].value_counts().to_string())
    print(" median incremental kW: none",round(inc0[eligible&~has].median(),2),"1 unit",round(inc1[eligible&~has].median(),2),"2 units",round(inc2[eligible&~has].median(),2))
# candidate tiers
persist=F.days_pk_ge7>=10
A=eligible&(B.cp_u1>=2.5)&persist
EVb=eligible&(C.ev_l2!="")
HEb=eligible&(C.elec_heat=="high")
PVb=eligible&C.pv.isin(["high","medium"])
tier=np.select([A&(EVb|HEb),A,PVb,EVb|HEb],["A1 grid-relief + electrified","A2 grid-relief","B solar+storage","C electrified, lower coincidence"],"")
B["tier"]=tier
B["size"]=np.where((B.cp_u2-B.cp_u1>=1.5)|((B.ev_enable=="2 units")&EVb),2,1)
B["cp_sel"]=np.where(B["size"]==2,B.cp_u2,B.cp_u1); B["cpS_sel"]=np.where(B["size"]==2,B.cpS_u2,B.cpS_u1); B["cpW_sel"]=np.where(B["size"]==2,B.cpW_u2,B.cpW_u1)
B["own_sel"]=np.where(B["size"]==2,B.own_red_u2,B.own_red_u1); B["shift_sel"]=np.where(B["size"]==2,B.shift_kwh_u2,B.shift_kwh_u1)
B["usd_sel"]=np.where(B["size"]==2,B.usd_u2,B.usd_u1)
c=B[B.tier!=""]
T=c.groupby("tier").agg(n=("peak","size"),two_units=("size",lambda s:(s==2).sum()),peak_kw=("peak","median"),own_peak_cut_kw=("own_sel","median"),
  summer_cp_kw=("cpS_sel","mean"),winter_cp_kw=("cpW_sel","mean"),summer_MW=("cpS_sel",lambda s:s.sum()/1e3),winter_MW=("cpW_sel",lambda s:s.sum()/1e3),
  shift_MWh=("shift_sel",lambda s:s.sum()/1e3),usd_per_home=("usd_sel","median"))
print("\n",T.round(2).to_string()); T.to_csv(O+"battery_tiers.csv")
# supply curve: rank all eligible by summer coincident kW per unit, cumulative MW for first N
r=B[eligible].sort_values("cp_u1",ascending=False)
for N in [100,250,500,1000,2500,5000]:
    print(f"top {N:5d} by coincident kW: summer {r.cpS_u1.iloc[:N].sum()/1e3:.2f} MW, winter {r.cpW_u1.iloc[:N].sum()/1e3:.2f} MW, mean cp {r.cp_u1.iloc[:N].mean():.2f} kW/home")
print("system top-100 mean: summer 48.35 MW, winter 38.27 MW; system annual peak",round(np.load(P_+'sysload.npy').max()/1e3,2),"MW")
# PV: days a battery could charge from solar surplus (>=3 zero hours 10-15h, Apr-Sep)
L=np.load(P_+"load_present.npy",mmap_mode="r"); idx=np.where(PVb)[0]; X=np.asarray(L[idx],np.float32).reshape(len(idx),365,24)
days=pd.date_range("2025-09-01",periods=365,freq="D"); sm=np.isin(days.month,[4,5,6,7,8,9])
zd=((X[:,:,10:16]==0).sum(2)>=3); print("PV homes",len(idx),"median days/yr with >=3 zero midday hours",np.median(zd.sum(1)),"(Apr-Sep share",round(np.median(zd[:,sm].sum(1)/zd.sum(1).clip(1)),2),")")
# demand flexibility without battery: AC + pool at the summer peak
hs=pd.date_range("2025-09-01",periods=8760,freq="h").hour.to_numpy()[top_s]
shoulder_at=np.stack([prof[:,2,h] for h in hs],1).mean(1)
ac_kw=np.clip(F.cs_kw.values-shoulder_at,0,None); acm=(C.ac!="").values&eligible.values
pool_kw=np.where((C.pool!="").values&eligible.values,F.pool_floor_delta_kw.clip(0).values,0)
print(f"\nAC homes {acm.sum()}: weather-driven kW at summer peak mean {ac_kw[acm].mean():.2f}, total {ac_kw[acm].sum()/1e3:.1f} MW; 33% thermostat setback -> {0.33*ac_kw[acm].sum()/1e3:.1f} MW")
print(f"Pool homes {(pool_kw>0).sum()}: pump kW shiftable total {pool_kw.sum()/1e3:.2f} MW")
evm=(C.ev_l2!="").values&eligible.values; ev_peak=np.clip(F.cw_kw.values-np.stack([prof[:,2,h] for h in pd.date_range("2025-09-01",periods=8760,freq="h").hour.to_numpy()[top_w]],1).mean(1),0,None)
print(f"EV homes {evm.sum()}: load above own shoulder profile at summer peak {np.clip(F.cs_kw.values-shoulder_at,0,None)[evm].sum()/1e3:.2f} MW, winter {ev_peak[evm].sum()/1e3:.2f} MW")
B.merge(S,on="CUSTOMER_NUMBER").merge(C,on="CUSTOMER_NUMBER").to_parquet(O+"customer_results.parquet")
