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
        if managed and 15<=h<=22: h=23
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
        out.append(dict(t=t,rating=rating,base_peak=float(base.max()),peak_u=float(Lu.max()),peak_m=float(Lm.max()),nev=nev,nhp=nhp,
            over_u=len(hu)>0, over_m=bool((Lm>lim).any()), units=need_units(Lm), hours_over=len(hu),
            winter=bool(len(hu) and np.isin(pd.DatetimeIndex(pd.date_range('2025-09-01',periods=8760,freq='h')[hu]).month,[11,12,1,2,3]).mean()>0.5)))
    return pd.DataFrame(out)
res={}
for name,(pe,ph) in {'Today':(0,0),'Moderate 2030 (20% EV, 15% HP)':(0.20,0.15),'High 2030 (35% EV, 30% HP)':(0.35,0.30)}.items():
    d=run(pe,ph,5); d.to_csv(f'ewu_{name.split()[0]}.csv',index=False)
    ov=d.over_u; fixed_ev=ov&~d.over_m; need_b=d.over_m&(d.units<=4); unres=d.over_m&(d.units>4)
    res[name]=dict(overloaded=round(ov.mean()*100,1), fixed_by_managed_EV=round(fixed_ev.mean()*100,1), need_battery=round(need_b.mean()*100,1),
        median_units=float(d.loc[need_b,'units'].median()) if need_b.any() else 0, unresolved=round(unres.mean()*100,1),
        winter_driven=round((d.winter&ov).sum()/max(ov.sum(),1)*100,1), avg_rating=round(d.rating.mean(),1))
    print(name,res[name],flush=True)
json.dump(res,open('ewu_results.json','w'),indent=1)
