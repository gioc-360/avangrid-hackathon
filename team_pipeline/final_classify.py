import numpy as np, pandas as pd
exec(open('classify.py').read().split("ev_cols=")[0])   # reuse helpers (logit_fit, prep, add_logs, v)
v=pd.read_pickle('v_scored.pkl')
out=pd.DataFrame(index=v.index)
# ---- Electric heating
prim=(v.heat_slope>=0.5)&(v.corr_cold>=0.5); supp=(~prim)&(v.heat_slope>=0.15)&(v.corr_cold>=0.3)
out['electric_heat']=np.where(prim,'Primary',np.where(supp,'Supplemental','No'))
out['electric_heat_conf']=v.corr_cold.clip(0,1).round(2)
# heat pump vs resistance among primary electric heat (PU within group)
g=v[prim].copy(); g=add_logs(g)
cols=['heat_slope','cold_ratio','cool_slope','corr_hot','winter_summer_ratio','log_annual_kwh','load_factor','heat_bp','cold_extra_slope','base_night_p05']
X,ref=prep(g,cols); y=g.lab_HP.values
rng=np.random.default_rng(1); folds=rng.integers(0,5,len(y)); oof=np.zeros(len(y))
for k in range(5):
    tr=folds!=k; w,b=logit_fit(X[tr],y[tr],l2=5.0); oof[~tr]=1/(1+np.exp(-(X[~tr]@w+b)))
r=pd.Series(oof).rank().values; npos=y.sum(); auc_hp=(r[y==1].sum()-npos*(npos+1)/2)/(npos*(len(y)-npos))
w,b=logit_fit(X,y,l2=5.0); hs=1/(1+np.exp(-(X@w+b)))
exp_hp_in_prim=int(round(npos/0.25)); thr=np.sort(hs)[::-1][exp_hp_in_prim-1]
out['heat_type']=''; out.loc[g.index,'heat_type']=np.where(hs>=thr,'Heat pump likely','Resistance likely')
out['heat_pump_score']=np.nan; out.loc[g.index,'heat_pump_score']=hs.round(3)
tq=np.sort(oof)[::-1][exp_hp_in_prim-1]; rec_hp=(oof[y==1]>=tq).mean()
print(f'HP within primary electric heat: n={len(g)}, labeled={npos}, OOF AUC {auc_hp:.2f}, flagged {exp_hp_in_prim}, labeled recall {rec_hp:.2f}')
print('  HP coefs:',', '.join(f'{c} {x:+.2f}' for c,x in sorted(zip(cols,w),key=lambda t:-abs(t[1]))[:5]))
# ---- AC
central=(v.cool_slope>=1.0)&(v.weather_r2>=0.3); room=(~central)&(v.cool_slope>=0.3)
out['air_conditioning']=np.where(central,'Central likely',np.where(room,'Room or light use','No'))
out['ac_conf']=(v.cool_slope/1.5).clip(0,1).mul(v.weather_r2.clip(0,1)**0.5).round(2)
# ---- EV tiers
rank=v.ev_score.rank(ascending=False)
out['ev_score']=v.ev_score.round(3)
E_EV=int(round(v.lab_EV.sum()/0.25)); hi_n=int(round(E_EV*200/544)); lo_n=int(round(E_EV*1000/544))
out['ev']=np.where(rank<=hi_n,'High',np.where(rank<=E_EV,'Medium',np.where(rank<=lo_n,'Low','No')))
print('EV tiers: High',hi_n,'Medium to',E_EV,'Low to',lo_n)
l2=(v.ev_mild_45_2>=5)|((v.l2_events>=10)&(v.l2_rise_med>=4.5))
out['ev_level']=np.where(out.ev=='No','',np.where(l2,'Level 2','Level 1 or mixed'))
# ---- Solar and solar + battery
solar=((v.zero_hours>200)&(v.solar_dip_summer<0.7))|(v.lab_PV==1)
out['solar']=np.where(v.lab_PV==1,'Known (list)',np.where(solar,'Detected','No'))
sb=(v.lab_PV==1)&(v.zero_hours<100)&(v.solar_dip_summer<0.6)
out['solar_battery']=np.where(sb,'Possible','')
# ---- Pool and hot tub (exploratory)
pool=(v.pool_day_lift>=0.7)&(v.pool_flat_day<=0.6)&(v.summer_base_lift>=0.3)
out['pool']=np.where(pool,'Possible','')
tub=(v.winter_night_base-v.spring_night_base>=0.5)&(v.heat_slope<0.3)&(v.spring_night_base>=0.4)
out['hot_tub']=np.where(tub,'Possible','')
for c in ['electric_heat','heat_type','air_conditioning','ev','ev_level','solar','solar_battery','pool','hot_tub']:
    vc=out[c].value_counts(); print(c, vc.to_dict())
# validation vs labels
print('EV labeled by tier', pd.crosstab(out.ev, v.lab_EV).to_dict())
print('HP labeled by electric_heat', pd.crosstab(out.electric_heat, v.lab_HP).to_dict())
print('PV labeled detected by rule', int((solar&(v.zero_hours>200)&(v.lab_PV==1)).sum()), 'of', int(v.lab_PV.sum()))
out.replace('None','No').to_csv('classification.csv'); print('saved',len(out))
