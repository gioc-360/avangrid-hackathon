import numpy as np, pandas as pd
w=pd.read_csv('weather_raw.csv'); w['ts']=pd.to_datetime(w.date.astype(str).str[:10]+' '+w.time.astype(str))
w=w.drop_duplicates('ts').set_index('ts').reindex(pd.date_range('2025-09-01','2026-08-31 23:00',freq='h'))
w[['temp','humidity','windspeed']]=w[['temp','humidity','windspeed']].interpolate(limit_direction='both')
T=w.temp.values.reshape(365,24).mean(1); np.save('daily_temp.npy',T)
np.save('hourly_temp.npy', w.temp.values.astype('float32'))
Z=np.load('feat_device.npz'); D=Z['daily'].astype(float)
# fill missing days with customer median
med=np.nanmedian(D,1,keepdims=True); D=np.where(np.isnan(D),med,D)
best=None
N=D.shape[0]; bestsse=np.full(N,np.inf); par=np.zeros((N,6))
for th in range(40,66,2):
    for tc in range(max(th,58),78,2):
        X=np.column_stack([np.ones(365),np.maximum(0,th-T),np.maximum(0,T-tc),np.maximum(0,15-T)])
        P=np.linalg.pinv(X)            # 4x365
        B=D@P.T                         # N x4
        r=D-B@X.T; sse=(r**2).sum(1)
        better=sse<bestsse
        bestsse[better]=sse[better]; par[better]=np.column_stack([B,np.full(N,th),np.full(N,tc)])[better]
sst=((D-D.mean(1,keepdims=True))**2).sum(1)
r2=1-bestsse/np.where(sst>0,sst,np.nan)
cols=['base_daily','heat_slope','cool_slope','cold_extra_slope','heat_bp','cool_bp']
np.savez('weather_feats.npz',par=par,r2=r2,cols=np.array(cols))
# simple correlations as robust backup
c_cold=np.array([np.corrcoef(D[i],np.maximum(0,55-T))[0,1] if D[i].std()>0 else np.nan for i in range(N)])
c_hot=np.array([np.corrcoef(D[i],np.maximum(0,T-65))[0,1] if D[i].std()>0 else np.nan for i in range(N)])
np.savez('weather_corr.npz',c_cold=c_cold,c_hot=c_hot)
print(pd.DataFrame(par,columns=cols).describe().round(2)); print('r2',np.nanpercentile(r2,[10,50,90]).round(2))
