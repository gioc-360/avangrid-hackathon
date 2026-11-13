"""Part 2: segmentation on load SHAPE (not size), then size, peak and class tags laid over each segment.
Shape vector: mean 24-h profile in winter (Dec-Feb), shoulder (Apr-May, Oct), summer (Jun-Aug), each divided by the
customer's annual mean hourly kW -> 72 numbers, scale-free. Plus log annual kWh (standardised) so the cluster also knows size.
k chosen by silhouette on a 6,000-customer sample (stat-test: cluster analysis -> standardise, drop outliers, validate k)."""
import numpy as np, pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
OUT='/Users/giocaballero/avangrid-hackathon/runs/skills/'
P='/Users/giocaballero/avangrid-hackathon/data/processed/'
F=pd.read_parquet(P+'features.parquet'); L=np.load(P+'load_present.npy', mmap_mode='r')
C=pd.read_parquet(OUT+'classes.parquet')
n=len(F); days=pd.date_range('2025-09-01',periods=365,freq='D'); mon=days.month.to_numpy()
D3=np.asarray(L).reshape(n,365,24)
seas={'winter':[12,1,2],'shoulder':[4,5,10],'summer':[6,7,8]}
prof=np.concatenate([D3[:,np.isin(mon,m),:].mean(1) for m in seas.values()],axis=1)   # n x 72, kW
np.save(OUT+'profiles72.npy',prof)
mean_kw=np.maximum(L.mean(1) if False else D3.mean((1,2)),1e-3)
shape=prof/mean_kw[:,None]
keep=(~C.dead_meter.values)&(shape.max(1)<15)          # drop dead meters and extreme spiky outliers
la=np.log10(np.maximum(F.annual_kwh.values,1)); z=(la-la[keep].mean())/la[keep].std()
Xs=np.column_stack([shape, 3*z[:,None]])               # size weighted like ~9 shape dims (assumption: equal say for size and shape)
rng=np.random.default_rng(0); idx=rng.choice(np.where(keep)[0],6000,replace=False)
sil={}
for k in range(3,10):
    km=KMeans(k,n_init=5,random_state=0).fit(Xs[idx]); sil[k]=silhouette_score(Xs[idx],km.labels_)
print('silhouette by k',{k:round(v,3) for k,v in sil.items()})
K=max(sil,key=sil.get) if max(sil.values())-sil.get(6,0)>0.02 else 6     # prefer 6 unless another k is clearly better
km=KMeans(K,n_init=10,random_state=0).fit(Xs[keep])
seg=np.full(n,-1); seg[keep]=km.labels_
# stability: re-fit on two random halves, adjusted Rand on overlap
from sklearn.metrics import adjusted_rand_score
h=rng.permutation(np.where(keep)[0]); a,b=h[:len(h)//2],h[len(h)//2:]
ka=KMeans(K,n_init=5,random_state=1).fit(Xs[a]); kb=KMeans(K,n_init=5,random_state=2).fit(Xs[b])
print('stability ARI (half-A model vs half-B model, scored on all kept):',round(adjusted_rand_score(ka.predict(Xs[keep]),kb.predict(Xs[keep])),3))
S=pd.DataFrame({'seg':seg}); S=pd.concat([S,C.drop(columns=['annual_kwh','peak_kw','cp_kw','cp_winter_kw','cp_summer_kw']),
        F[['annual_kwh','peak_kw','cp_kw','cp_winter_kw','cp_summer_kw','winter_ratio','summer_ratio','load_factor','peak_hour','min_month_share']]],axis=1)
g=S[S.seg>=0].groupby('seg')
tab=pd.DataFrame({'n':g.size(),'share_pct':(100*g.size()/keep.sum()).round(1),
  'med_kwh':g.annual_kwh.median().round(0),'med_peak_kw':g.peak_kw.median().round(2),
  'med_cp_winter_kw':g.cp_winter_kw.median().round(2),'med_cp_summer_kw':g.cp_summer_kw.median().round(2),
  'winter_ratio':g.winter_ratio.median().round(2),'summer_ratio':g.summer_ratio.median().round(2),'load_factor':g.load_factor.median().round(3),
  'share_of_winter_cp_pct':(100*g.cp_winter_kw.sum()/S.cp_winter_kw[S.seg>=0].sum()).round(1),
  'share_of_summer_cp_pct':(100*g.cp_summer_kw.sum()/S.cp_summer_kw[S.seg>=0].sum()).round(1),
  'pct_elec_heat':(100*g.elec_heat.mean()).round(1),'pct_ev':(100*(g.ev_l2.mean())).round(1),'pct_solar':(100*g.solar.mean()).round(1),
  'pct_pool':(100*g.pool.mean()).round(1),'pct_seasonal':(100*g.seasonal_home.mean()).round(1),
  'lab_hp':g.lab_hp.sum(),'lab_ev':g.lab_ev.sum(),'lab_pv':g.lab_pv.sum()})
pd.set_option('display.width',250); print(tab.to_string())
# label enrichment test (chi-square): are HP/EV/PV labels spread evenly over segments?
from scipy.stats import chi2_contingency
for lab in ['lab_hp','lab_ev','lab_pv']:
    ct=pd.crosstab(S.seg[S.seg>=0],S[lab][S.seg>=0]); chi,p,dof,_=chi2_contingency(ct)
    V=np.sqrt(chi/(ct.values.sum()*(min(ct.shape)-1))); print(f'{lab}: chi2({dof})={chi:.1f}, p={p:.2g}, Cramer V={V:.3f}')
tab.to_csv(OUT+'segments.csv'); S[['seg']].assign(CUSTOMER_NUMBER=F.CUSTOMER_NUMBER).to_parquet(OUT+'segments.parquet')
np.save(OUT+'seg_centroid_kw.npy',np.stack([prof[seg==s].mean(0) for s in range(K)]))
