"""Per-customer kW vs outdoor temperature curve (all hours, 10F bins). Output out/tcurve.npy [n x 10]"""
import numpy as np, pandas as pd
P="/Users/giocaballero/avangrid-hackathon/data/processed/"; O="/Users/giocaballero/avangrid-hackathon/runs/plain/out/"
L=np.load(P+"load_present.npy",mmap_mode="r"); t=pd.read_parquet(P+"weather.parquet").temp.to_numpy()
edges=[-99,0,10,20,30,40,50,60,70,80,99]; b=np.digitize(t,edges[1:-1])
B=np.zeros((8760,10),np.float32); B[np.arange(8760),b]=1; B/=B.sum(0,keepdims=True)
print("hours per bin",np.bincount(b,minlength=10))
out=np.vstack([np.asarray(L[a:a+4000],np.float32)@B for a in range(0,L.shape[0],4000)])
np.save(O+"tcurve.npy",out)
F=pd.read_parquet(O+"scored.parquet")
lab=["<0","0-10","10-20","20-30","30-40","40-50","50-60","60-70","70-80","80+"]
heat=(F.heat_kwh_yr>=2000)&(F.cold_kw_lift>=1.0)
for name,m in [("all",np.ones(len(F),bool)),("labeled HP",F.lab_hp==1),("labeled HP w/ heat",(F.lab_hp==1)&heat),("unlabeled elec-heat",(F.lab_hp==0)&heat),("labeled EV",F.lab_ev==1),("labeled PV",F.lab_pv==1)]:
    print(f"{name:22s}",np.round(np.median(out[np.asarray(m)],0),2))
