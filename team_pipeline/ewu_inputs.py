import numpy as np, pandas as pd
M=np.load('kwh.npy',mmap_mode='r'); f=pd.read_csv('features_all.csv',index_col=0)
c=pd.read_csv('classification.csv',index_col=0,keep_default_na=False)
Td=np.load('daily_temp.npy'); mild=np.where((Td>=45)&(Td<=68))[0]
# 1) EV charging start hours from High tier EV homes (mild days, rise to >= base+4.5)
ev=c.index[c.ev=='High']; starts=[]
for cid in ev:
    X=np.nan_to_num(np.array(M[cid-1])).reshape(365,24)[mild]
    base=np.percentile(X,20,axis=1,keepdims=True); hi=X>=base+4.5
    for d in range(hi.shape[0]):
        for h in range(24):
            if hi[d,h] and (h==0 or not hi[d,h-1]): starts.append(h)
st=pd.Series(starts).value_counts(normalize=True).sort_index(); np.save('ev_start_pmf.npy',st.reindex(range(24),fill_value=0).values)
print('EV start hour distribution (High tier, mild days):',(st*100).round(1).to_dict())
# 2) Heat pump increment: labeled heat pump homes that are primary electric heat vs homes with no electric heat but central AC
hp=c.index[(c.electric_heat=='Primary')&(f.loc[c.index,'lab_HP']==1)]
ref=c.index[(c.electric_heat=='No')&(c.air_conditioning=='Central likely')]
def med(ids):
    out=np.zeros(8760); X=np.array(M[np.array(ids)-1]); return np.nanmedian(X,0)
Mh=med(hp); Mr=med(ref[np.random.default_rng(0).choice(len(ref),600,replace=False)])
inc=np.clip(pd.Series(Mh-Mr).rolling(3,center=True,min_periods=1).mean().values,0,None)
np.save('hp_increment.npy',inc)
T=np.load('hourly_temp.npy'); print('HP homes',len(hp),' increment annual kWh',round(inc.sum()),' max kW',round(inc.max(),2),' mean kW when T<10F',round(inc[T<10].mean(),2),' when T>80F',round(inc[T>80].mean(),2))
print('ref annual',round(Mr.sum()),'hp annual',round(Mh.sum()))
