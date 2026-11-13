"""Part 2: k-means on normalized seasonal daily shapes (3 seasons x 24 h) + size; describe clusters. Output out/segments.parquet"""
import numpy as np, pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
O="/Users/giocaballero/avangrid-hackathon/runs/plain/out/"
F=pd.read_parquet(O+"scored.parquet"); C=pd.read_parquet(O+"classes.parquet"); prof=np.load(O+"profiles.npy")
act=(F.annual_kwh>=500).to_numpy()   # inactive meters excluded from clustering
mean_kw=(F.annual_kwh/8760).to_numpy()
Z=(prof.reshape(len(F),-1)/np.maximum(mean_kw,1e-3)[:,None])   # shape, relative to own average
Z=np.clip(Z,0,8)
Zs=np.column_stack([Z,2.0*np.log10(np.maximum(F.annual_kwh,1))])  # size enters with modest weight
Za=Zs[act]
rng=np.random.default_rng(0); samp=rng.choice(len(Za),5000,replace=False)
for k in range(4,11):
    km=KMeans(k,n_init=5,random_state=0).fit(Za)
    print(k,"silhouette(5k sample)",round(silhouette_score(Za[samp],km.labels_[samp]),3),"inertia",int(km.inertia_))

# ---- final: k=6 shapes (descriptive), rule segments (decision)
K=6; km=KMeans(K,n_init=10,random_state=0).fit(Za)
F["shape_cluster"]=-1; F.loc[act,"shape_cluster"]=km.labels_
ev=C.ev_l2!=""; eh=C.elec_heat!=""; pv=C.pv.isin(["high","medium"])
seg=np.select([~act, C.seasonal_home!="", pv, ev&eh, ev, eh,
               (F.cs_kw>=F.cs_kw.quantile(.75))&((C.ac!="")|(C.pool!="")),
               (F.annual_kwh>=F.annual_kwh.median())&(C.ac!="")],
              ["0 Inactive","1 Seasonal/part-year","2 Solar PV","3 Dual electrified (EV+heat)","4 EV home","5 Electric-heat home",
               "6 Summer peak contributor","7 Emerging electrification candidate"],"8 Low-use / baseline")
F["segment"]=seg
sysS=F.cs_kw.sum(); sysW=F.cw_kw.sum()
g=F.groupby("segment").agg(n=("annual_kwh","size"),median_kwh=("annual_kwh","median"),total_GWh=("annual_kwh",lambda s:s.sum()/1e6),
   median_peak_kw=("peak_kw","median"),summer_cp_kw=("cs_kw","mean"),winter_cp_kw=("cw_kw","mean"),
   S_share=("cs_kw",lambda s:s.sum()/sysS*100),W_share=("cw_kw",lambda s:s.sum()/sysW*100),
   winter_ratio=("winter_ratio","median"),days_pk_ge7=("days_pk_ge7","median"))
g["cust_share"]=g.n/len(F)*100
print(g.round(2).to_string())
print("system summer top-100 mean MW",round(sysS/1e3,2),"winter top-100 mean MW",round(sysW/1e3,2))
# cluster description
ct=pd.crosstab(F.shape_cluster,F.segment); print(ct.to_string())
d=F.groupby("shape_cluster").agg(n=("annual_kwh","size"),kwh=("annual_kwh","median"),wr=("winter_ratio","median"),sr=("summer_ratio","median"),
   pkh=("peak_hour","median"),lf=("load_factor","median"),cs=("cs_kw","mean"),cw=("cw_kw","mean"))
print(d.round(2).to_string())
F[["CUSTOMER_NUMBER","segment","shape_cluster"]].to_parquet(O+"segments.parquet"); g.to_csv(O+"segment_table.csv")
np.save(O+"centroids.npy",km.cluster_centers_)
