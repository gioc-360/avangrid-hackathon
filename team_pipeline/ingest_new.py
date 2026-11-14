import sys, glob, os, numpy as np, pandas as pd, time
k=int(sys.argv[1]); deadline=time.time()+150
files=sorted(glob.glob(os.path.expanduser('~/mnt/New Data/*.csv')))[k::4]
M=np.lib.format.open_memmap('kwh.npy',mode='r+'); base=np.datetime64('2025-09-01')
done=set(open('done_new.txt').read().split()) if os.path.exists('done_new.txt') else set()
for f in files:
    key=os.path.basename(f)
    if key in done: continue
    if time.time()>deadline: print('paused'); break
    d=pd.read_csv(f,usecols=['CUSTOMER_NUMBER','usage_date','hour_ending','hourly_kwh','is_complete_hour'])
    day=(pd.to_datetime(d.usage_date).values.astype('datetime64[D]')-base).astype(int)
    h=day*24+d.hour_ending.values-1; c=d.CUSTOMER_NUMBER.values-1
    ok=(h>=0)&(h<8760)&(c>=10000)&(c<20000)
    M[c[ok],h[ok]]=d.hourly_kwh.values[ok].astype('float32'); M.flush()
    with open('stats_new.txt','a') as fh: fh.write(f"{key} {len(d)} {int((~ok).sum())} {int((d.hourly_kwh<0).sum())} {int((d.is_complete_hour==0).sum())} {d.CUSTOMER_NUMBER.min()} {d.CUSTOMER_NUMBER.max()} {d.CUSTOMER_NUMBER.nunique()}\n")
    with open('done_new.txt','a') as fh: fh.write(key+'\n')
