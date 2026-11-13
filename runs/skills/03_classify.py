"""Part 1: customer classification.
Two layers: (a) physics rules, one per end use, each naming the load signature it catches;
(b) positive-unlabeled gradient boosting for EV and HP, validated out-of-fold against the labels.
SCAR identity (labels are a random 25% of true positives, per the challenge statement):
   P(labeled | flagged) = precision * 0.25  ->  precision_hat = 4 * labeled_in_flag / flagged
   recall_hat = labeled_in_flag / labeled_total
Writes classes.parquet (one row per customer) and prints validation tables."""
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
from scipy.stats import beta
OUT='/Users/giocaballero/avangrid-hackathon/runs/skills/'
P='/Users/giocaballero/avangrid-hackathon/data/processed/'
F=pd.read_parquet(P+'features.parquet'); L=np.load(P+'load_present.npy')
n=len(F); hours=pd.date_range('2025-09-01',periods=8760,freq='h'); hod=hours.hour.to_numpy(); mo=hours.month.to_numpy()
days=pd.date_range('2025-09-01',periods=365,freq='D'); mon=days.month.to_numpy()
D3=L.reshape(n,365,24)

# ---------- extra features from the hourly matrix ----------
sh4=np.isin(mon,[4,5,9,10])                      # mildest months: no heat, little AC
S=D3[:,sh4,:]; base=np.percentile(S,20,axis=2,keepdims=True); ex=S-base
F['ev_d6']=(ex.max(2)>=6).sum(1)                 # days with an hour >= 6 kWh above the day's floor (L2 at 6-7.7 kW)
run2=(ex[:,:,1:]>=3)&(ex[:,:,:-1]>=3); F['ev_run2']=run2.any(2).sum(1)
st=np.argmax(ex>=6,axis=2); has=(ex.max(2)>=6)
F['ev_d6_night_share']=((has)&((st>=18)|(st<=4))).sum(1)/np.maximum(has.sum(1),1)
l1=(ex>=1.0)&(ex<=2.2)
r5=l1[:,:,4:]&l1[:,:,3:-1]&l1[:,:,2:-2]&l1[:,:,1:-3]&l1[:,:,:-4]
F['ev_l1run5']=r5.any(2).sum(1)                  # nights with a 1-2.2 kW lift held 5+ hours (Level 1 at 1.4-1.9 kW)
del S, ex
summ=np.isin(mo,[5,6,7,8]); wint=np.isin(mo,[12,1,2])
F['zero_eve_summer']=(L[:,summ&(hod>=19)&(hod<=23)]==0).mean(1)
F['zero_night_summer']=(L[:,summ&(hod<=4)]==0).mean(1)
F['zero_mid_winter']=(L[:,wint&(hod>=10)&(hod<=14)]==0).mean(1)
F['zero_eve_winter']=(L[:,wint&(hod>=17)&(hod<=22)]==0).mean(1)
F['evening_share']=L[:,(hod>=16)&(hod<=20)].sum(1)/np.maximum(L.sum(1),1e-3)

# ---------- (a) physics rules ----------
C=pd.DataFrame({'CUSTOMER_NUMBER':F.CUSTOMER_NUMBER})
C['dead_meter']=F.annual_kwh<300                                    # < 300 kWh/yr: meter on, nobody home
alive=~C.dead_meter
C['solar']=alive&(F.zero_mid_summer>=0.05)&(F.zero_mid_summer-F.zero_night_summer>=0.05)&(F.zero_eve_winter<0.5)
C['solar_battery']=C.solar&(F.zero_eve_summer>=0.3)                # evening also netted to zero in summer -> storage
E=pd.read_parquet(OUT+'ev_neutral.parquet')                         # from 05_ev_check.py: weather-neutral days only
F['ev_d6_neutral']=E.ev_d6_neutral.values; F['ev_night_share']=E.ev_night_share.values
# L2: >= 8 of 119 weather-neutral days (55-70 F) with a >=6 kWh block, and >= 60% of those blocks start 18:00-03:59
C['ev_l2']=alive&(F.ev_d6_neutral>=8)&(F.ev_night_share>=0.6)
C['ev_l1']=alive&~C.ev_l2&(F.ev_l1run5>=30)&(F.ev_d6<3)
C['elec_heat']=alive&(F.heat_kwh_yr>=3000)&(F.cold_kw_lift>=1.5)
# HP vs resistance: a heat pump's COP falls in deep cold (slope steepens) and it also cools.
hp_like=(F.heat_nonlin>=1.5)|((F.b_cool>=1.0)&(F.winter_ratio<2.5))
C['heat_pump']=C.elec_heat&hp_like
C['resistance_heat']=C.elec_heat&~hp_like
C['ac_central']=alive&(F.hot_kw_lift>=1.5)&(F.b_cool>=1.0)
C['ac_room']=alive&~C.ac_central&(F.hot_kw_lift>=0.5)&(F.b_cool>=0.4)
C['pool']=alive&(F.pool_floor_delta_kw>=0.6)&(F.pool_delta_kwh_day>=8)
C['hot_tub']=alive&~C.ev_l2&(F.spike_night>=30)&(F.spike_winter_share>=0.25)
C['elec_water_heat']=alive&~C.ev_l2&(F.spike_morning>=40)&(F.b_base>=15)
C['seasonal_home']=alive&(F.min_month_share<0.15)
C['always_on_base']=alive&(F.load_factor>=0.5)&(F.base_kw>=1.5)    # crypto rig, grow light, well pump or small business

# ---------- (b) PU gradient boosting for EV and HP ----------
feat=[c for c in F.columns if c not in ('CUSTOMER_NUMBER','lab_ev','lab_hp','lab_pv')]
X=F[feat].to_numpy(np.float32)
def pu(lab, seed=0):
    y=F[lab].to_numpy(); oof=np.zeros(n)
    for tr,te in StratifiedKFold(5,shuffle=True,random_state=seed).split(X,y):
        m=HistGradientBoostingClassifier(max_iter=200,learning_rate=0.05,max_leaf_nodes=15,l2_regularization=1.0,
                                         class_weight='balanced',random_state=seed).fit(X[tr],y[tr])
        oof[te]=m.predict_proba(X[te])[:,1]
    return oof
rows=[]
def scar(name, flag, lab, c=0.25):
    flag=np.asarray(flag); y=F[lab].to_numpy(); k=int((flag&(y==1)).sum()); N=int(flag.sum()); npos=int(y.sum())
    lo,hi=beta.ppf([0.025,0.975],[k+0.5]*2,[npos-k+0.5]*2)              # Jeffreys interval on recall
    prec=min(1,k/c/max(N,1)) if c else np.nan
    rows.append(dict(cls=name,flagged=N,labeled_in_flag=k,labeled_total=npos,recall=k/npos,recall_lo=lo,recall_hi=hi,
                     precision_hat=prec, implied_true_total=(N*prec/(k/npos)) if k else np.nan))
for lab,name,expected in [('lab_ev','EV',4*F.lab_ev.sum()),('lab_hp','HP',4*F.lab_hp.sum())]:
    oof=np.mean([pu(lab,s) for s in range(2)],axis=0)
    auc=roc_auc_score(F[lab],oof)
    C[f'p_{name}']=oof
    top=np.zeros(n,bool); top[np.argsort(-oof)[:expected]]=True
    C[f'{name}_model_top']=top
    print(f'{name}: OOF AUC labeled-vs-unlabeled {auc:.3f}; top-{expected} (= 4 x labels, the implied population)')
    scar(f'{name} model top-{expected}', top, lab)
    # confidence = within-flag rank -> High / Medium / Low tertiles of OOF score inside the implied population
C['ev_confidence']=np.where(C.EV_model_top&C.ev_l2,'High',np.where(C.ev_l2|C.EV_model_top,'Medium','None'))
C['hp_confidence']=np.where(C.HP_model_top&C.heat_pump,'High',np.where(C.heat_pump|C.HP_model_top,'Medium','None'))

scar('EV L2 rule (neutral-day blocks, night start)', C.ev_l2, 'lab_ev')
scar('EV L1 rule', C.ev_l1, 'lab_ev')
scar('EV any rule', C.ev_l2|C.ev_l1, 'lab_ev')
scar('EV High (rule & model)', C.ev_confidence=='High', 'lab_ev')
scar('Electric heat rule', C.elec_heat, 'lab_hp')
scar('Heat pump rule', C.heat_pump, 'lab_hp')
scar('Resistance rule (should hold few HP)', C.resistance_heat, 'lab_hp')
scar('HP High (rule & model)', C.hp_confidence=='High', 'lab_hp')
# PV labels are ALL known solar (c = 1): precision measurable directly
scar('Solar rule (c=1, all PV labeled)', C.solar, 'lab_pv', c=1.0)
V=pd.DataFrame(rows); pd.set_option('display.width',220)
print(V.round(3).to_string(index=False)); V.to_csv(OUT+'validation.csv',index=False)

# label-free consistency checks
print('\nPV labels with solar_battery flag:', int((C.solar_battery&(F.lab_pv==1)).sum()), ' unlabeled solar-shaped homes:', int((C.solar&(F.lab_pv==0)).sum()))
print('labeled HP with heat_kwh_yr<1500 (weather-driven heat barely visible):', int(((F.lab_hp==1)&(F.heat_kwh_yr<1500)).sum()),'of',int(F.lab_hp.sum()))
print('labeled EV with zero days >=6 kWh block in mild months:', int(((F.lab_ev==1)&(F.ev_d6==0)).sum()),'of',int(F.lab_ev.sum()))
cls=['dead_meter','solar','solar_battery','ev_l2','ev_l1','elec_heat','heat_pump','resistance_heat','ac_central','ac_room','pool','hot_tub','elec_water_heat','seasonal_home','always_on_base']
cnt=pd.DataFrame({'count':C[cls].sum(),'share_pct':(100*C[cls].mean()).round(2),
                  'median_annual_kwh':[F.annual_kwh[C[c]].median() for c in cls],
                  'median_peak_kw':[F.peak_kw[C[c]].median() for c in cls],
                  'median_cp_kw':[F.cp_kw[C[c]].median() for c in cls]})
print(cnt.round(1).to_string()); cnt.to_csv(OUT+'class_counts.csv')
C=pd.concat([C,F[['annual_kwh','peak_kw','cp_kw','cp_winter_kw','cp_summer_kw','lab_ev','lab_hp','lab_pv','ev_d6','ev_l1run5',
                  'heat_kwh_yr','evening_share','zero_eve_summer']]],axis=1)
C.to_parquet(OUT+'classes.parquet')
