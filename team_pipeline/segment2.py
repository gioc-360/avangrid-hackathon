
import numpy as np, pandas as pd
rng=np.random.default_rng(7)
df=pd.read_csv('features.csv',index_col=0); v=df[df.valid].copy()
solar=((v.zero_hours>200)&(v.solar_dip_summer<0.7))|(v.lab_PV==1)
seasonal=(~solar)&((v.min_month_ratio<0.3)|(v.zero_hours>200))
v['rule']=np.where(solar,'S',np.where(seasonal,'V',''))
r=v[v.rule==''].copy()
feat=pd.DataFrame({
 'size':np.log(r.annual_kwh.clip(300)),'heat':np.log1p(r.heat_slope.clip(0,5)*10),'cool':np.log1p(r.cool_slope.clip(0,8)),
 'evening':r.evening_share,'night':r.night_share,'midday':r.midday_share,'lf':r.load_factor,
 'coinc':np.log(r.coinc_ratio.clip(0.2,8)),'season':np.log(r.winter_summer_ratio.clip(0.2,8)),'bigload':np.log1p(r.hrs_gt6)},index=r.index)
Z=(feat-feat.median())/(feat.quantile(.9)-feat.quantile(.1)); Z=Z.clip(-3,3).fillna(0); X=Z.values
def kmeans(X,k,it=80,n_init=6):
    best=None
    for t in range(n_init):
        C=X[rng.choice(len(X),1)]
        for _ in range(k-1):
            d=((X[:,None]-C[None])**2).sum(2).min(1); C=np.vstack([C,X[rng.choice(len(X),p=d/d.sum())]])
        for _ in range(it):
            lab=((X[:,None]-C[None])**2).sum(2).argmin(1)
            C=np.array([X[lab==j].mean(0) if (lab==j).any() else C[j] for j in range(k)])
        inert=((X-C[lab])**2).sum()
        if best is None or inert<best[0]: best=(inert,lab,C)
    return best
def sil(X,lab,n=3000):
    i=rng.choice(len(X),n,replace=False); Xs=X[i]; L=lab[i]
    D=np.sqrt(((Xs[:,None]-Xs[None])**2).sum(2)); sc=[]
    for a in range(n):
        same=L==L[a]; same[a]=False
        aa=D[a,same].mean(); bb=min(D[a,L==j].mean() for j in set(L) if j!=L[a]); sc.append((bb-aa)/max(aa,bb))
    return np.mean(sc)
out={}
for k in [3,4,5]:
    inert,lab,C=kmeans(X,k); out[k]=(lab,C); print('k',k,'sil',round(sil(X,lab),3),np.bincount(lab).tolist())
pd.set_option('display.width',250)
for k in [4,5]:
    v['seg']=v.rule
    v.loc[r.index,'seg']=[str(x) for x in out[k][0]]
    g=v.groupby('seg')
    t=pd.DataFrame({'n':g.size(),'share%':g.size()/len(v)*100,'kWh/yr':g.annual_kwh.median(),'pmax':g.pmax.median(),'heat_sl':g.heat_slope.median(),'cool_sl':g.cool_slope.median(),'W/S':g.winter_summer_ratio.median(),
      'eve%':g.evening_share.median()*100,'night%':g.night_share.median()*100,'mid%':g.midday_share.median()*100,'LF':g.load_factor.median(),'coincS':g.coinc_summer_kw.median(),'coincW':g.coinc_winter_kw.median(),'hrs>6':g.hrs_gt6.median(),
      'EV%':g.lab_EV.mean()*100,'HP%':g.lab_HP.mean()*100,'PV%':g.lab_PV.mean()*100,'sysPkS%':g.coinc_summer_kw.sum()/v.coinc_summer_kw.sum()*100,'sysPkW%':g.coinc_winter_kw.sum()/v.coinc_winter_kw.sum()*100})
    print('k=',k); print(t.round(2).to_string()); 
    v[['seg']].to_csv(f'seg_k{k}.csv')
    pd.DataFrame(out[k][1],columns=feat.columns).round(2).to_csv(f'centroids_k{k}.csv')
