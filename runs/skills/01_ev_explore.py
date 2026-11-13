"""Explore EV charging signatures from the hourly matrix (shoulder months only, so HVAC is not the cause)."""
import numpy as np, pandas as pd
P='/Users/giocaballero/avangrid-hackathon/data/processed/'
F=pd.read_parquet(P+'features.parquet'); L=np.load(P+'load_present.npy', mmap_mode='r')
n=len(F); days=pd.date_range('2025-09-01',periods=365,freq='D'); mon=days.month.to_numpy()
sh = np.isin(mon,[3,4,5,6,9,10,11])
D3=np.asarray(L).reshape(n,365,24)[:,sh,:]
base=np.percentile(D3,20,axis=2,keepdims=True)
ex=D3-base
out={}
for thr in [4,5,6,7]:
    out[f'd_ex{thr}']=(ex.max(2)>=thr).sum(1)
two=(ex[:,:,1:]>=3)&(ex[:,:,:-1]>=3)
out['d_run2_3']=two.any(2).sum(1)
three=(ex[:,:,2:]>=3)&(ex[:,:,1:-1]>=3)&(ex[:,:,:-2]>=3)
out['d_run3_3']=three.any(2).sum(1)
# Level 1: 1.0-2.0 kW for >=5 consecutive hours, starting 17-02
l1=(ex>=1.0)&(ex<=2.2)
r5=l1[:,:,4:]&l1[:,:,3:-1]&l1[:,:,2:-2]&l1[:,:,1:-3]&l1[:,:,:-4]
out['d_l1run5']=r5.any(2).sum(1)
O=pd.DataFrame(out); O['lab_ev']=F.lab_ev.values; O['lab_pv']=F.lab_pv.values; O['lab_hp']=F.lab_hp.values
nsh=sh.sum(); print('shoulder days',nsh)
for c in out:
    for k in [5,10,20,40]:
        flag=O[c]>=k; rec=O.loc[O.lab_ev==1,c].ge(k).mean(); nf=flag.sum(); labf=(flag&(O.lab_ev==1)).sum()
        print(f'{c:10s} >= {k:3d}: flagged {nf:6d}  EV recall {rec:.2f}  labeled-in-flag {labf:4d}  implied precision(4x) {4*labf/max(nf,1):.2f}')
O.to_parquet('/Users/giocaballero/avangrid-hackathon/runs/skills/ev_feats.parquet')
