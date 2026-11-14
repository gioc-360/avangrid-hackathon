import numpy as np, pandas as pd
rng=np.random.default_rng(0)
d=pd.read_csv('features_all.csv',index_col=0); v=d[d.valid].copy()
def logit_fit(X,y,l2=1.0,it=3000,lr=0.1):
    w=np.zeros(X.shape[1]); b=0.0; sw=np.where(y==1,(y==0).sum()/max((y==1).sum(),1),1.0)  # balance classes
    for _ in range(it):
        p=1/(1+np.exp(-(X@w+b))); g=(p-y)*sw
        w-=lr*(X.T@g/len(y)+l2*w/len(y)); b-=lr*g.mean()
    return w,b
def prep(df,cols,ref=None):
    X=df[cols].astype(float).replace([np.inf,-np.inf],np.nan).fillna(0)
    for c in cols:
        if c.startswith('log_'): pass
    ref=ref if ref is not None else (X.median(),X.quantile(.9)-X.quantile(.1)+1e-6)
    return ((X-ref[0])/ref[1]).clip(-4,6).values, ref
def add_logs(df):
    for c in ['annual_kwh','ev_mild_3_2','ev_mild_45_2','ev_mild_55_2','l2_events','l1_nights','hrs_gt6','zero_hours']:
        df['log_'+c]=np.log1p(df[c].clip(lower=0))
    return df
v=add_logs(v)
def pu_model(name,label,cols,expected):
    y=v[label].values; X,ref=prep(v,cols)
    # 5-fold CV: hold out positives AND unlabeled
    folds=rng.integers(0,5,len(y)); g=np.zeros(len(y))
    for k in range(5):
        tr=folds!=k; w,b=logit_fit(X[tr],y[tr]); g[~tr]=1/(1+np.exp(-(X[~tr]@w+b)))
    # AUC labeled vs unlabeled (out of fold)
    r=pd.Series(g).rank().values; npos=y.sum(); auc=(r[y==1].sum()-npos*(npos+1)/2)/(npos*(len(y)-npos))
    w,b=logit_fit(X,y); score=1/(1+np.exp(-(X@w+b)))
    # calibrate: scale scores so implied total matches expected prevalence (labeled = ~25% sample)
    # choose threshold t such that count(score>=t) = expected; probability = rank based
    order=np.sort(score)[::-1]; t=order[min(expected,len(order))-1]
    # recall of out-of-fold scores on labeled at same quantile
    tq=np.sort(g)[::-1][min(expected,len(g))-1]; rec=(g[y==1]>=tq).mean()
    # implied precision: true positives flagged ~= recall*expected ; precision = that / expected
    prob=np.clip(score/np.quantile(score[y==1],0.5)*0.5,0,1)   # labeled median -> 0.5? keep simple: rescale
    coef=pd.Series(w,index=cols).sort_values(key=abs,ascending=False)
    print(f'== {name}: out-of-fold AUC {auc:.3f}; top {expected} flagged; recall of labeled in top {expected}: {rec:.2f}  -> est precision ~{rec:.2f}')
    print('   strongest features:',', '.join(f'{c} {coef[c]:+.2f}' for c in coef.index[:6]))
    return score,t,rec,auc
ev_cols=['log_ev_mild_3_2','log_ev_mild_45_2','log_ev_mild_55_2','ev_mild_night_share','mild_dailymax_p90','mild_rise_med','log_l2_events','l2_dur_med','log_l1_nights','night_share','log_annual_kwh','load_factor','heat_slope','cool_slope','log_zero_hours']
hp_cols=['heat_slope','corr_cold','cold_ratio','cool_slope','corr_hot','winter_summer_ratio','log_l1_nights','base_night_p05','load_factor','log_annual_kwh','weather_r2','heat_bp','cold_extra_slope','log_zero_hours']
E_ev=int(round(v.lab_EV.sum()/0.25)); E_hp=int(round(v.lab_HP.sum()/0.25))
ev_s,ev_t,ev_rec,ev_auc=pu_model('EV','lab_EV',ev_cols,E_ev)
hp_s,hp_t,hp_rec,hp_auc=pu_model('Heat pump','lab_HP',hp_cols,E_hp)
v['ev_score']=ev_s; v['hp_score']=hp_s; v['ev_thr']=ev_t; v['hp_thr']=hp_t
v.to_pickle('v_scored.pkl'); print('expected EV',E_ev,'HP',E_hp)
