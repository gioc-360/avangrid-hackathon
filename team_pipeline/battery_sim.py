import numpy as np, pandas as pd
M=np.load('kwh.npy',mmap_mode='r'); N=M.shape[0]
S=np.load('system_load.npy'); Sd=S.reshape(365,24)
top50=np.argsort(-S)[:50]; ev_days=np.sort(np.argsort(-Sd.max(1))[:60])
K=6; RTE=0.894; RES=0.2
units={1:(10.08*(1-RES),3.84),2:(20.16*(1-RES),7.68)}
# hours used on each event day: that day's top K system hours
Hd={d:np.sort(np.argsort(-Sd[d])[:K]) for d in ev_days}
top50_days=np.unique(top50//24)
for d in top50_days:
    if d not in Hd: Hd[d]=np.sort(np.argsort(-Sd[d])[:K])
days_all=np.array(sorted(Hd)); hrs=np.array([d*24+Hd[d] for d in days_all])  # (nd,K) absolute hours
is_top50=np.isin(hrs,top50)
in60=np.isin(days_all,ev_days)
def waterfill(L,E,P):
    # L: (n,nd,K) loads; reduce r<=min(P,L), sum_k r <= E, flatten from top
    cap=np.minimum(L,P); lo=np.zeros(L.shape[:2]); hi=L.max(2)
    for _ in range(40):
        mid=(lo+hi)/2; r=np.clip(L-mid[...,None],0,None); r=np.minimum(r,cap); e=r.sum(2)
        lo=np.where(e>E,mid,lo); hi=np.where(e>E,hi,mid)
    r=np.minimum(np.clip(L-hi[...,None],0,None),cap); return r
cols=['load_top50','red1_top50','red2_top50','kwh2_yr','kwh1_yr','charge_new_peak','ev_shift_top50','ac_kw_top50','pmax99']
out=np.zeros((N,len(cols)),np.float32)
days=pd.date_range('2025-09-01',periods=365,freq='D'); Td=np.load('daily_temp.npy')
mild_s=np.where(np.isin(days.month,[6,7,8])&(Td>=60)&(Td<=68))[0]
cls=pd.read_csv('classification.csv',index_col=0,keep_default_na=False)
evflag=np.zeros(N,bool); evflag[cls.index[cls.ev.isin(['High','Medium'])]-1]=True
for s in range(0,N,2000):
    X=np.nan_to_num(np.array(M[s:s+2000]),nan=0.0); n=X.shape[0]; X3=X.reshape(n,365,24)
    L=X[:,hrs]                                  # n, nd, K
    out[s:s+n,0]=X[:,top50].mean(1)
    for u,col,colk in [(1,1,4),(2,2,3)]:
        E,P=units[u]; r=waterfill(L,E,P)
        out[s:s+n,col]=(r*is_top50).sum((1,2))/50
        out[s:s+n,colk]=r[:,in60].sum((1,2))
        if u==2:
            # overnight charge before each event day: energy/RTE over 7 hours (0-7h)
            chg=r.sum(2)/RTE/7                       # n, nd
            night=X3[:,days_all][:,:,0:7].max(2)      # same-day early hours as proxy
            p99=np.percentile(X,99,axis=1); out[s:s+n,8]=p99
            out[s:s+n,5]=((night+chg)>p99[:,None]).sum(1)
    # AC component at top hours: load minus same-hour median on mild summer days
    base_h=np.median(X3[:,mild_s],axis=1)            # n,24
    out[s:s+n,7]=np.clip(X[:,top50]-base_h[:,top50%24],0,None).mean(1)
    # EV shiftable: during top hours, load above day's p20 by >=4.5 kW counts (capped 7.2)
    dmin=np.percentile(X3[:,top50//24],20,axis=2)    # n,50
    exc=X[:,top50]-dmin; ev=np.where(exc>=4.5,np.minimum(exc,7.2),0)
    out[s:s+n,6]=np.where(evflag[s:s+n],ev.mean(1),0)
    print(s,flush=True)
df=pd.DataFrame(out,columns=cols,index=np.arange(1,N+1)); df.to_csv('battery_sim.csv'); print(df.describe().round(2).T)
