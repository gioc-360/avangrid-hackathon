import numpy as np, pandas as pd
M=np.load('kwh.npy',mmap_mode='r'); df=pd.read_csv('features.csv',index_col=0)
idx=np.where(df.valid.values)[0]; S=np.zeros(8760)
for s in range(0,len(idx),3000): S+=np.nansum(M[idx[s:s+3000]],0)
np.save('system_load.npy',S)
ts=pd.date_range('2025-09-01',periods=8760,freq='h'); summ=np.where(ts.month.isin([6,7,8]))[0]; wint=np.where(ts.month.isin([12,1,2]))[0]
top_s=summ[np.argsort(-S[summ])[:100]]; top_w=wint[np.argsort(-S[wint])[:100]]
cp_s=np.zeros(len(df)); cp_w=np.zeros(len(df))
for a in range(0,len(df),3000):
    X=np.array(M[a:a+3000]); cp_s[a:a+3000]=np.nanmean(X[:,top_s],1); cp_w[a:a+3000]=np.nanmean(X[:,top_w],1)
df['coinc_summer_kw']=cp_s; df['coinc_winter_kw']=cp_w; df['coinc_ratio']=cp_s/df.mean_kw; df.to_csv('features.csv')
s=pd.Series(S/1000,index=ts); w=s[s.index.month.isin([12,1,2])]
print('valid',len(idx),'summer peak',round(s.max(),1),s.idxmax(),' winter peak',round(w.max(),1),w.idxmax())
t=s.nlargest(100); print('top100 months',t.index.month.value_counts().sort_index().to_dict())
top50=np.argsort(-S)[:50]; print('top50 days',len(np.unique(top50//24)))
