"""EV block features on weather-neutral days only (daily mean 55-70 F), so heating and cooling cannot fake a charger.
Run before 03_classify.py. Found because the first EV rule overlapped electric heat on 331 homes (cold April/October days)."""
import numpy as np, pandas as pd
OUT='/Users/giocaballero/avangrid-hackathon/runs/skills/'; P='/Users/giocaballero/avangrid-hackathon/data/processed/'
F=pd.read_parquet(P+'features.parquet'); L=np.load(P+'load_present.npy', mmap_mode='r'); n=len(F)
t=pd.read_parquet(P+'weather.parquet').temp.to_numpy().reshape(365,24).mean(1)
neutral=(t>=55)&(t<=70); print('neutral days',neutral.sum())
D=np.asarray(L).reshape(n,365,24)[:,neutral,:]; ex=D-np.percentile(D,20,axis=2,keepdims=True)
has=ex.max(2)>=6; st=np.argmax(ex>=6,axis=2); dur=(ex>=3).sum(2).astype(float)
E=pd.DataFrame({'CUSTOMER_NUMBER':F.CUSTOMER_NUMBER,'ev_d6_neutral':has.sum(1),
   'ev_night_share':(has&((st>=18)|(st<=3))).sum(1)/np.maximum(has.sum(1),1),
   'ev_med_block_hours':np.nanmedian(np.where(has,dur,np.nan),axis=1)})
for k in [5,8,10,15]:
  for s in [0.0,0.6,0.8]:
    f=(E.ev_d6_neutral>=k)&(E.ev_night_share>=s); lab=int((f&(F.lab_ev==1)).sum())
    print(f'd6>={k} night>={s}: flagged {int(f.sum())} labeled {lab} recall {lab/F.lab_ev.sum():.2f} precision_hat {min(1,4*lab/max(f.sum(),1)):.2f}')
E.to_parquet(OUT+'ev_neutral.parquet')
