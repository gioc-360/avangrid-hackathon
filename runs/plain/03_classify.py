"""Part 1 classification. PU learning (Elkan-Noto) for EV and HP; physical rules for the rest. Output out/classes.parquet"""
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold
P="/Users/giocaballero/avangrid-hackathon/data/processed/"; O="/Users/giocaballero/avangrid-hackathon/runs/plain/out/"
F=pd.read_parquet(P+"features.parquet"); E=pd.read_parquet(O+"extra.parquet"); F=pd.concat([F,E],axis=1)
feat=[c for c in F.columns if c not in("CUSTOMER_NUMBER","lab_ev","lab_hp","lab_pv","peak_month") and not c.startswith("kwh_m")]
X=F[feat].to_numpy(np.float32)
def pu(lab,seed=0,reps=3):
    y=F[lab].to_numpy(); oof=np.zeros(len(y)); 
    for r in range(reps):
        skf=StratifiedKFold(5,shuffle=True,random_state=seed+r)
        for tr,te in skf.split(X,y):
            m=HistGradientBoostingClassifier(max_iter=200,learning_rate=0.05,max_leaf_nodes=15,min_samples_leaf=40,
                 l2_regularization=1.0,class_weight={0:1,1:20},random_state=r)
            m.fit(X[tr],y[tr]); oof[te]+=m.predict_proba(X[te])[:,1]/reps
    return oof,y
res={}
for lab,hint in [("lab_ev",0.25),("lab_hp",0.25)]:
    s,y=pu(lab); F[lab.replace("lab","score")]=s
    rank=(-s).argsort().argsort()  # 0 = highest
    implied=int(round(y.sum()/hint))
    print(f"\n{lab}: labeled present {y.sum()}, implied population at 25% sampling = {implied}")
    for N in [100,250,implied,1000,2000,5000]:
        rec=(rank[y==1]<N).mean(); print(f"  top {N:5d}: held-out recall of labeled positives {rec:.3f} -> est. true positives in list {rec*implied:.0f}, est. precision {rec*implied/N:.2f}")
    # AUC unlabeled vs labeled (lower bound of true AUC under PU)
    from sklearn.metrics import roc_auc_score; print("  OOF AUC labeled-vs-unlabeled", round(roc_auc_score(y,s),3))
    res[lab]=implied
F.to_parquet(O+"scored.parquet")
