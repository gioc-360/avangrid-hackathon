import numpy as np, pandas as pd
P="/Users/giocaballero/avangrid-hackathon/data/processed/"
F=pd.read_parquet(P+"features.parquet")
pd.set_option("display.width",220)
cols=[c for c in F.columns if c not in ("CUSTOMER_NUMBER",) and not c.startswith("kwh_m") and not c.startswith("lab_")]
out=pd.DataFrame({"all":F[cols].median()})
for l in ["lab_ev","lab_hp","lab_pv"]: out[l]=F.loc[F[l]==1,cols].median()
print(out.round(3).to_string())
# PV recall of zero midday rule
for t in [0.01,0.05,0.1,0.2]:
    r=(F.zero_mid_summer>t)
    print("zero_mid>",t,"flag",r.sum(),"PV recall",r[F.lab_pv==1].mean().round(3),"unlabeled flagged",(r&(F.lab_pv==0)).sum())
print(F.loc[F.lab_pv==1,"zero_mid_summer"].describe())
