import numpy as np, pandas as pd, json
rng=np.random.default_rng(11)
M=np.load('kwh.npy',mmap_mode='r'); c=pd.read_csv('classification.csv',index_col=0,keep_default_na=False)
pmf=np.load('ev_start_pmf.npy'); hpinc=np.load('hp_increment.npy')
ids=c.index.values; NT=3000; H=8
sizes=np.array([25,37.5,50,75,100,167]); OVER=1.2      # allowable hourly loading = 120% of nameplate (assumption)
UNIT_P,UNIT_E=3.84,8.064
evp=0.47; dur=3; kw=7.2                                   # 3.3 sessions per week, 3 h at 7.2 kW = ~3,700 kWh/yr
sel=np.array([rng.choice(len(ids),H,replace=False) for _ in range(NT)])
uniq=np.unique(sel); Xall={}
for a in range(0,len(uniq),2000):
    chunk=uniq[a:a+2000]; X=np.array(M[ids[chunk]-1]); mu=np.nanmean(X,1,keepdims=True); X=np.where(np.isnan(X),mu,X)
    for k,i in enumerate(chunk): Xall[i]=X[k].astype(np.float32)
isev=(c.ev.isin(['High','Medium'])).values; isheat=(c.electric_heat=='Primary').values
def ev_profile(managed):
    p=np.zeros(8760,np.float32); days=np.where(rng.random(365)<evp)[0]
    for d in days:
        h=rng.choice(24,p=pmf)
        if managed:
            h=23+rng.integers(0,5)              # smart: staggered start 11pm to 3am
            s=d*24+h; p[s:s+6]+=kw/2              # half power, twice as long, same energy
        else:
            s=d*24+h; p[s:s+dur]+=kw
    return p
def run(p_ev,p_hp,seed):
    global rng; rng=np.random.default_rng(seed); out=[]
    for t in range(NT):
        base=np.zeros(8760,np.float32); add_u=np.zeros(8760,np.float32); add_m=np.zeros(8760,np.float32); nev=nhp=0
        for i in sel[t]:
            base+=Xall[i]
            if not isev[i] and rng.random()<p_ev:
                st=rng.integers(1e9); r0=rng
                rng=np.random.default_rng(st); add_u+=ev_profile(False); rng=np.random.default_rng(st); add_m+=ev_profile(True); rng=r0; nev+=1
            if not isheat[i] and rng.random()<p_hp: add_u+=hpinc; add_m+=hpinc; nhp+=1
        rating=sizes[np.searchsorted(sizes,base.max()/0.85)] if base.max()/0.85<=sizes[-1] else sizes[-1]
        lim=OVER*rating
        Lu=base+add_u; Lm=base+add_m
        def need_units(L):
            e=np.clip(L-lim,0,None).reshape(365,24)
            if e.max()<=0: return 0
            u=max(np.ceil(e.max(1)/UNIT_P).max(), np.ceil(e.sum(1)/UNIT_E).max()); return int(u)
        hu=np.where(Lu>lim)[0]
        bo={}
        for ov in (1.0,1.1,1.2,1.4):
            l2=ov*rating; e=np.clip(Lu-l2,0,None).reshape(365,24)
            bo[f'u{int(ov*100)}']=0 if e.max()<=0 else int(max(np.ceil(e.max(1)/UNIT_P).max(), np.ceil(e.sum(1)/UNIT_E).max()))
            bo[f'o{int(ov*100)}']=bool(e.max()>0)
        out.append(dict(t=t,rating=rating,base_peak=float(base.max()),peak_u=float(Lu.max()),peak_m=float(Lm.max()),nev=nev,nhp=nhp,
            over_u=len(hu)>0, over_m=bool((Lm>lim).any()), units=need_units(Lm), hours_over=len(hu), **bo, om100=bool((Lm>1.0*rating).any()),
            winter=bool(len(hu) and np.isin(pd.DatetimeIndex(pd.date_range('2025-09-01',periods=8760,freq='h')[hu]).month,[11,12,1,2,3]).mean()>0.5)))
    return pd.DataFrame(out)
import sys
name=sys.argv[1]; pe,ph={'Moderate':(0.20,0.15),'High':(0.35,0.30)}[name]
d=run(pe,ph,5); d.to_csv(f'ewu_bo2_{name}.csv',index=False); print(name,'done',d[['o100','o110','o120','o140','om100','over_m']].mean().round(3).to_dict(),flush=True)
