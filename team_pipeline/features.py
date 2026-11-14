import numpy as np, pandas as pd
M = np.load('kwh.npy', mmap_mode='r'); N, H = M.shape
days = pd.date_range('2025-09-01', periods=365, freq='D')
month = days.month.values; dow = days.dayofweek.values
season = np.where(np.isin(month,[12,1,2]),0, np.where(np.isin(month,[6,7,8]),1,2))  # 0 winter 1 summer 2 shoulder
hod = np.arange(24)
F = {}; daily = np.full((N,365),np.nan,np.float32); prof = np.full((N,3,2,24),np.nan,np.float32)
monthly_base = np.full((N,12),np.nan,np.float32); monthly_mean=np.full((N,12),np.nan,np.float32)
cols = ['n_valid','mean_kw','base_night_p05','p95','pmax','night_share','evening_share','midday_share',
        'jumps3','blocks3','blocks5','hrs_gt6','min_kw','cv','solar_dip_summer','solar_dip_winter','zero_hours']
out = np.full((N,len(cols)),np.nan,np.float32)
for s in range(0,N,1500):
    X = np.array(M[s:s+1500]).reshape(-1,365,24)   # cust, day, hour
    n = X.shape[0]
    valid = ~np.isnan(X)
    out[s:s+n,0] = valid.sum((1,2))
    D = np.nanmean(X,2)*24; daily[s:s+n]=D
    for si in range(3):
        for w in range(2):
            m = (season==si)&((dow>=5)==w)
            prof[s:s+n,si,w] = np.nanmean(X[:,m],1)
    for mi in range(12):
        m = month==mi+1
        monthly_mean[s:s+n,mi]=np.nanmean(X[:,m])if False else np.nanmean(X[:,m].reshape(n,-1),1)
        monthly_base[s:s+n,mi]=np.nanpercentile(X[:,m][:,:,0:5].reshape(n,-1),10,axis=1)
    flat = X.reshape(n,-1)
    tot = np.nansum(flat,1)
    out[s:s+n,1] = np.nanmean(flat,1)
    out[s:s+n,2] = np.nanpercentile(X[:,:,0:5].reshape(n,-1),5,axis=1)
    out[s:s+n,3] = np.nanpercentile(flat,95,axis=1)
    out[s:s+n,4] = np.nanmax(flat,1)
    out[s:s+n,5] = np.nansum(X[:,:,[23,0,1,2,3,4,5]],(1,2))/tot
    out[s:s+n,6] = np.nansum(X[:,:,16:21],(1,2))/tot
    out[s:s+n,7] = np.nansum(X[:,:,10:15],(1,2))/tot
    d = np.diff(flat,axis=1)
    out[s:s+n,8] = (d>3).sum(1)
    # block: rise >thr then fall < -thr within 1..6 hours
    for col,thr in [(9,3.0),(10,5.0)]:
        up = d>thr; dn = d< -thr
        cnt = np.zeros(n)
        dn_any = np.zeros_like(up)
        for k in range(1,7):
            dn_any[:, :-k] |= dn[:, k:]
        out[s:s+n,col] = (up & dn_any).sum(1)
    out[s:s+n,11] = (flat>6).sum(1)
    out[s:s+n,12] = np.nanmin(flat,1)
    out[s:s+n,13] = np.nanstd(flat,1)/np.nanmean(flat,1)
    for col,ss in [(14,1),(15,0)]:
        p = prof[s:s+n,ss].mean(1)  # avg weekday/weekend
        out[s:s+n,col] = p[:,10:15].mean(1)/((p[:,6:9].mean(1)+p[:,17:20].mean(1))/2)
    out[s:s+n,16] = (flat<=0.01).sum(1)
    print(s, flush=True)
np.savez_compressed('feat_device.npz', out=out, cols=np.array(cols), daily=daily, prof=prof, monthly_base=monthly_base, monthly_mean=monthly_mean)
print('saved')
