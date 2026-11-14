import numpy as np, pandas as pd
M=np.load('kwh.npy',mmap_mode='r'); N=M.shape[0]
Td=np.load('daily_temp.npy'); Th=np.load('hourly_temp.npy').reshape(365,24)
days=pd.date_range('2025-09-01',periods=365,freq='D'); mon=days.month.values
mild_summer=np.isin(mon,[6,7,8,9])&(Td>=58)&(Td<=70)
mild_spring=np.isin(mon,[4,5,10])&(Td>=50)&(Td<=66)
cols=['l2_events','l2_days','l2_rise_med','l2_dur_med','l2_start_night_share','l2_temp_corr','l1_nights','pool_day_lift','pool_night_lift','pool_flat_day','winter_night_base','spring_night_base','heat_peak_cold','heat_peak_mild']
out=np.full((N,len(cols)),np.nan,np.float32)
B=1200
for s in range(0,N,B):
    X=np.nan_to_num(np.array(M[s:s+B]),nan=0.0).reshape(-1,365,24); n=X.shape[0]
    F=X.reshape(n,-1)
    d=np.diff(F,axis=1,prepend=F[:,:1])
    up=d>=3.0
    # block: after rise at t, load stays >= pre+2.5 for k hours (1..8) then falls by >=2.5
    pre=np.roll(F,1,axis=1)
    ev_count=np.zeros(n); ev_days=np.zeros(n); rises=[[] for _ in range(n)]; durs=[[] for _ in range(n)]; night=np.zeros(n)
    dayhit=np.zeros((n,365),bool)
    ci,ti=np.nonzero(up)
    for c,t in zip(ci,ti):
        base=pre[c,t]; lvl=base+2.5; k=0
        while t+k+1<F.shape[1] and F[c,t+k+1]>=lvl and k<8: k+=1
        end=t+k+1
        if end<F.shape[1] and F[c,end]<=F[c,t+k]-2.5 and k<=7:
            ev_count[c]+=1; rises[c].append(F[c,t]-base); durs[c].append(k+1); dayhit[c,t//24]=True
            h=t%24
            if h>=18 or h<=3: night[c]+=1
    out[s:s+n,0]=ev_count; out[s:s+n,1]=dayhit.sum(1)
    out[s:s+n,2]=[np.median(r) if r else np.nan for r in rises]
    out[s:s+n,3]=[np.median(r) if r else np.nan for r in durs]
    out[s:s+n,4]=np.where(ev_count>0,night/np.maximum(ev_count,1),np.nan)
    tc=np.full(n,np.nan)
    for c in range(n):
        if dayhit[c].sum()>=10 and dayhit[c].sum()<=355: tc[c]=np.corrcoef(dayhit[c].astype(float),np.abs(Td-60))[0,1]
    out[s:s+n,5]=tc
    # L1: nights (20h..7h) with >=5 consecutive hours between base+0.9 and base+2.2, base = p10 of 2-5am across year
    base=np.percentile(X[:,:,2:5].reshape(n,-1),10,axis=1)[:,None,None]
    nightseq=np.concatenate([X[:,:-1,20:24],X[:,1:,0:7]],axis=2)  # 364 nights x 11 hours
    inb=(nightseq>=base+0.9)&(nightseq<=base+2.2)
    run=np.zeros(inb.shape[:2]); best=np.zeros(inb.shape[:2])
    for h in range(inb.shape[2]):
        run=np.where(inb[:,:,h],run+1,0); best=np.maximum(best,run)
    out[s:s+n,6]=(best>=5).sum(1)
    # pool: mild summer days vs mild spring days, daytime (9-17) p20 and night (0-5) p20
    def p(mask,hrs): 
        Y=X[:,mask][:,:,hrs].reshape(n,-1); return np.percentile(Y,20,axis=1) if Y.shape[1] else np.full(n,np.nan)
    out[s:s+n,7]=p(mild_summer,list(range(9,17)))-p(mild_spring,list(range(9,17)))
    out[s:s+n,8]=p(mild_summer,list(range(0,5)))-p(mild_spring,list(range(0,5)))
    ds=X[:,mild_summer][:,:,9:17]; out[s:s+n,9]=np.median(ds.std(2),1)  # pump = flat daytime
    wint=np.isin(mon,[12,1,2])
    out[s:s+n,10]=np.percentile(X[:,wint][:,:,1:5].reshape(n,-1),20,axis=1)
    out[s:s+n,11]=p(mild_spring,[1,2,3,4])
    cold=Td<15; mildw=(Td>=30)&(Td<=40)
    out[s:s+n,12]=X[:,cold].mean((1,2)); out[s:s+n,13]=X[:,mildw].mean((1,2))
    print(s,flush=True)
pd.DataFrame(out,columns=cols,index=np.arange(1,N+1)).to_csv('features2.csv')
print('saved; mild summer days',mild_summer.sum(),'mild spring',mild_spring.sum(),'cold days',(Td<15).sum())
