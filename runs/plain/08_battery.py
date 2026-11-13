"""Part 3: BTM battery simulation for every customer, 1 unit (20.16 kWh / 7.68 kW) and 2 units, RTE 89.4%.
 (a) coincident relief at the 100 top summer + 100 top winter system hours (load-following, no export)
 (b) own-peak shaving: min annual peak T s.t. every day energy above T <= E, peak-T <= P, and the day's charging
     headroom below T (capped at P) x RTE covers the discharge (daily energy balance, no export)
 (c) daily on-peak shifting 16-21h (load following, no export) -> kWh shifted
 (d) electrification enablement: add L2 EV (7.2 kW x 2 h at 18-20h daily) or a heat pump (data-derived kW(T)) and
     test whether the battery holds incremental peak <= 3 kVA (kW, PF=1)
Output out/battery.parquet"""
import numpy as np, pandas as pd
P_="/Users/giocaballero/avangrid-hackathon/data/processed/"; O="/Users/giocaballero/avangrid-hackathon/runs/plain/out/"
L=np.load(P_+"load_present.npy",mmap_mode="r"); n=L.shape[0]
F=pd.read_parquet(O+"scored.parquet"); C=pd.read_parquet(O+"classes.parquet")
temp=pd.read_parquet(P_+"weather.parquet").temp.to_numpy()
hours=pd.date_range("2025-09-01",periods=8760,freq="h"); hod=hours.hour.to_numpy(); mon=hours.month.to_numpy()
sys=np.load(P_+"sysload.npy")
for nm,mk in [("summer",np.isin(mon,[6,7,8])),("winter",np.isin(mon,[12,1,2]))]:
    print(nm,"system mean MW by hour",np.round(sys[mk].reshape(-1,24).mean(0)/1e3,1))
top_s=np.load(O+"top_s.npy"); top_w=np.load(O+"top_w.npy")
print("top100 summer hours by hod",np.bincount(hod[top_s],minlength=24)); print("top100 winter by hod",np.bincount(hod[top_w],minlength=24))
print("event days summer",len(np.unique(top_s//24)),"winter",len(np.unique(top_w//24)))
UNITS={1:(20.16,7.68),2:(40.32,15.36)}; RTE=0.894
# heat-pump add profile from labeled HP homes that show heating: their kW(T) minus their own 60-70F level
tc=np.load(O+"tcurve.npy"); heatm=((F.heat_kwh_yr>=2000)&(F.cold_kw_lift>=1.0)&(F.lab_hp==1)).to_numpy()
hp_bin=np.clip(np.median(tc[heatm]-tc[heatm][:,[7]],0),0,None); print("HP add kW by 10F bin (<0..80+)",hp_bin.round(2),"from n=",heatm.sum())
edges=[0,10,20,30,40,50,60,70,80]; hp_add=hp_bin[np.digitize(temp,edges)].astype(np.float32)
# individual (non-diversified) scaling: labeled cohort P75/median of cold_kw_lift
ev_add=np.zeros(8760,np.float32); ev_add[(hod==18)|(hod==19)]=7.2
def shave(X,E,P,iters=28):
    pk=X.max(1); lo=np.maximum(pk-P,0); hi=pk.copy(); D=X.reshape(len(X),365,24)
    for _ in range(iters):
        T=(lo+hi)/2; over=np.maximum(D-T[:,None,None],0).sum(2)
        room=np.minimum(np.maximum(T[:,None,None]-D,0),P).sum(2)   # charging headroom below T, same day
        ok=((over<=E)&(over<=RTE*room+1e-6)).all(1)
        hi=np.where(ok,T,hi); lo=np.where(ok,lo,T)
    return hi
def cp(X,top,E,P):
    red=np.zeros((len(X),len(top)),np.float32); d=top//24
    for day in np.unique(d):
        j=np.where(d==day)[0]; r=np.minimum(X[:,top[j]],P); s=r.sum(1,keepdims=True)
        red[:,j]=r*np.minimum(1,E/np.maximum(s,1e-6))
    return red.mean(1)
win=(hod>=16)&(hod<=20)
out=[]
for a in range(0,n,1500):
    X=np.asarray(L[a:a+1500],np.float32); m=len(X); pk=X.max(1); r={}
    D=X.reshape(m,365,24)
    for u,(E,P) in UNITS.items():
        r[f"cpS_u{u}"]=cp(X,top_s,E,P); r[f"cpW_u{u}"]=cp(X,top_w,E,P)
        T=shave(X,E,P); r[f"peak_after_u{u}"]=T
        # recharge check: headroom below T (capped at P) must refill the day's discharge / RTE
        over=np.maximum(D-T[:,None,None],0).sum(2); room=np.minimum(np.maximum(T[:,None,None]-D,0),P).sum(2)
        r[f"recharge_fail_days_u{u}"]=(room<over/RTE-1e-6).sum(1)
        w=np.minimum(X[:,win],P).reshape(m,365,5).sum(2); r[f"shift_kwh_u{u}"]=np.minimum(w,E).sum(1)
        for nm,add in [("ev",ev_add),("hp",hp_add)]:
            Y=X+add[None,:]; T2=shave(Y,E,P); r[f"{nm}_newpk_u{u}"]=T2
    r["ev_newpk_u0"]=(X+ev_add).max(1); r["hp_newpk_u0"]=(X+hp_add).max(1); r["peak"]=pk
    out.append(pd.DataFrame(r)); print(a,flush=True)
B=pd.concat(out,ignore_index=True); B.insert(0,"CUSTOMER_NUMBER",F.CUSTOMER_NUMBER.values)
B.to_parquet(O+"battery.parquet"); print(B.describe().T.round(2).to_string())
