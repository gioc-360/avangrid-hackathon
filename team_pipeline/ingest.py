import sys, zipfile, numpy as np, pandas as pd, os, time
zpath = sys.argv[1]; tag = sys.argv[2]; deadline = time.time() + float(sys.argv[3])
N, H = 35725, 8760
M = np.lib.format.open_memmap('kwh.npy', mode='r+')
base = np.datetime64('2025-09-01')
z = zipfile.ZipFile(zpath)
done = set(open('done.txt').read().split()) if os.path.exists('done.txt') else set()
for name in sorted(n for n in z.namelist() if n.endswith('.csv')):
    key = tag + ':' + name
    if key in done: continue
    if time.time() > deadline: print(tag, 'paused'); break
    d = pd.read_csv(z.open(name), usecols=['CUSTOMER_NUMBER','usage_date','hour_ending','hourly_kwh','is_complete_hour'])
    day = (pd.to_datetime(d.usage_date).values.astype('datetime64[D]') - base).astype(int)
    h = day*24 + d.hour_ending.values - 1
    c = d.CUSTOMER_NUMBER.values - 1
    ok = (h >= 0) & (h < H) & (c >= 0) & (c < N)
    M[c[ok], h[ok]] = d.hourly_kwh.values[ok].astype('float32')
    M.flush()
    with open('stats.txt','a') as f: f.write(f"{key} {len(d)} {int((~ok).sum())} {int((d.hourly_kwh<0).sum())} {int((d.is_complete_hour==0).sum())} {d.CUSTOMER_NUMBER.min()} {d.CUSTOMER_NUMBER.max()}\n")
    with open('done.txt','a') as f: f.write(key + '\n')
else:
    print(tag, 'COMPLETE')
