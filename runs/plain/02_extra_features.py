"""Extra per-customer features computed from the hourly matrix (chunked). Output: runs/plain/out/extra.parquet, profiles.npy"""
import numpy as np, pandas as pd, os
P="/Users/giocaballero/avangrid-hackathon/data/processed/"; O="/Users/giocaballero/avangrid-hackathon/runs/plain/out/"
os.makedirs(O,exist_ok=True)
L=np.load(P+"load_present.npy",mmap_mode="r"); n=L.shape[0]
w=pd.read_parquet(P+"weather.parquet"); temp=w.temp.to_numpy()
hours=pd.date_range("2025-09-01",periods=8760,freq="h"); hod=hours.hour.to_numpy(); mon=hours.month.to_numpy(); dow=hours.dayofweek.to_numpy()
seas={"win":np.isin(mon,[12,1,2]),"sum":np.isin(mon,[6,7,8]),"shl":np.isin(mon,[3,4,5,9,10,11])}
sys=np.load(P+"sysload.npy")
# system peak sets: top 100 hours in summer (Jun-Aug) and winter (Dec-Feb)
top_s=np.where(seas["sum"])[0][np.argsort(sys[seas["sum"]])[-100:]]
top_w=np.where(seas["win"])[0][np.argsort(sys[seas["win"]])[-100:]]
np.save(O+"top_s.npy",top_s); np.save(O+"top_w.npy",top_w)
prof=np.zeros((n,3,24),np.float32); rows=[]
midS=np.isin(mon,[5,6,7,8])&(hod>=10)&(hod<=14); nightA=(hod<=4)
eveS=np.isin(mon,[5,6,7,8])&(hod>=19)&(hod<=22)
midW=np.isin(mon,[11,12,1,2])&(hod>=10)&(hod<=14)
for a in range(0,n,2000):
    X=np.asarray(L[a:a+2000],dtype=np.float32); m=X.shape[0]
    for k,(s,mask) in enumerate(seas.items()):
        prof[a:a+m,k]=X[:,mask].reshape(m,-1,24).mean(1)
    D=X.reshape(m,365,24)
    dpk=D.max(2)
    r=pd.DataFrame({
      "zero_mid_S":(X[:,midS]==0).mean(1),"zero_mid_W":(X[:,midW]==0).mean(1),
      "zero_night_all":(X[:,nightA]==0).mean(1),"zero_eve_S":(X[:,eveS]==0).mean(1),
      "zero_all":(X==0).mean(1),
      # midday dip: summer 10-14 mean vs summer 7-9 & 17-19 mean (solar homes self-consume at noon)
      "mid_dip_S":X[:,midS].mean(1)/np.maximum(X[:,np.isin(mon,[5,6,7,8])&(np.isin(hod,[7,8,17,18,19]))].mean(1),1e-3),
      "cs_kw":X[:,top_s].mean(1),"cw_kw":X[:,top_w].mean(1),
      "cs_kw_p90":np.percentile(X[:,top_s],90,axis=1),
      "days_pk_ge10":(dpk>=10).sum(1),"days_pk_ge7":(dpk>=7).sum(1),
      "dpk_p95":np.percentile(dpk,95,axis=1),
      # L2 EV all-year: days with >=2 consecutive hours >= 6.0 kW above that day's 25th pct hour, starting 16-02h
      })
    q=np.percentile(D,25,axis=2,keepdims=True)
    hi=(D-q)>=6.0
    run2=hi[:,:,1:]&hi[:,:,:-1]
    r["l2_days_all"]=run2.any(2).sum(1)
    # evening/night start share of those runs
    start_h=np.arange(1,24)
    eve_run=run2[:,:,(start_h>=17)|(start_h<=3)].any(2)
    r["l2_eve_share"]=eve_run.sum(1)/np.maximum(r["l2_days_all"].to_numpy(),1)
    # L1 EV: nights with 1.2-2.0 kW constant above base held 4+ hours, all year non-winter
    rows.append(r); print(a,flush=True)
E=pd.concat(rows,ignore_index=True)
E.to_parquet(O+"extra.parquet"); np.save(O+"profiles.npy",prof)
print(E.describe().T.round(3).to_string())
