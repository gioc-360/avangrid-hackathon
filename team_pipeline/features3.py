import numpy as np, pandas as pd
M=np.load('kwh.npy',mmap_mode='r'); N=M.shape[0]
Td=np.load('daily_temp.npy'); mild=(Td>=45)&(Td<=68)
res={}
thr_list=[(3.0,2),(4.5,2),(5.5,2),(4.5,3)]
out=np.zeros((N,len(thr_list)+3),np.float32)
for s in range(0,N,1500):
    X=np.nan_to_num(np.array(M[s:s+1500]),nan=0.0).reshape(-1,365,24); n=X.shape[0]
    Xm=X[:,mild]                              # n, dm, 24
    base=np.percentile(Xm,20,axis=2,keepdims=True)
    for j,(thr,L) in enumerate(thr_list):
        hi=Xm>=base+thr; run=np.zeros(hi.shape[:2]); best=np.zeros(hi.shape[:2])
        for h in range(24):
            run=np.where(hi[:,:,h],run+1,0); best=np.maximum(best,run)
        out[s:s+n,j]=((best>=L)&(best<=8)).sum(1)   # days with a 2..8 hour block
    hi=Xm>=base+4.5; 
    # hour of block start distribution: share of high hours between 18 and 3
    hrs=np.arange(24); nightmask=(hrs>=18)|(hrs<=3)
    tot=hi.sum((1,2)); out[s:s+n,len(thr_list)]=np.where(tot>0,hi[:,:,nightmask].sum((1,2))/np.maximum(tot,1),np.nan)
    out[s:s+n,len(thr_list)+1]=np.percentile(Xm.max(2),90,axis=1)   # p90 of daily max on mild days
    out[s:s+n,len(thr_list)+2]=np.median(Xm.max(2)-base[:,:,0],axis=1)
cols=['ev_mild_3_2','ev_mild_45_2','ev_mild_55_2','ev_mild_45_3','ev_mild_night_share','mild_dailymax_p90','mild_rise_med']
pd.DataFrame(out,columns=cols,index=np.arange(1,N+1)).to_csv('features3.csv'); print('mild days',mild.sum())
