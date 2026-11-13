import numpy as np, pandas as pd
P="/Users/giocaballero/avangrid-hackathon/data/processed/"
F=pd.read_parquet(P+"features.parquet"); w=pd.read_parquet(P+"weather.parquet")
pd.set_option("display.width",200); pd.set_option("display.max_columns",80)
print(F.describe(percentiles=[.05,.25,.5,.75,.95,.99]).T.round(3).to_string())
print(F[["lab_ev","lab_hp","lab_pv"]].sum(), (F.lab_ev&F.lab_pv).sum(), (F.lab_hp&F.lab_pv).sum(), (F.lab_ev&F.lab_hp).sum())
s=np.load(P+"sysload.npy"); print("sys peak MW", s.max()/1e3, s.argmax(), "mean", s.mean()/1e3)
print(w.describe())
