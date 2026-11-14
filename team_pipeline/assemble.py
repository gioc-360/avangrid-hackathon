import numpy as np, pandas as pd
Z=np.load('feat_device.npz'); W=np.load('weather_feats.npz'); C=np.load('weather_corr.npz')
df=pd.DataFrame(Z['out'],columns=Z['cols']); df.index=np.arange(1,len(df)+1); df.index.name='customer'
for i,c in enumerate(W['cols']): df[str(c)]=W['par'][:,i]
df['weather_r2']=W['r2']; df['corr_cold']=C['c_cold']; df['corr_hot']=C['c_hot']
df['annual_kwh']=df.mean_kw*8760
df['load_factor']=df.mean_kw/df.pmax
mb=Z['monthly_base']; mm=Z['monthly_mean']   # months index 0=Jan
summer=[5,6,7]; spring=[3,4]; winter=[11,0,1]
df['summer_base_lift']=np.nanmean(mb[:,summer],1)-np.nanmean(mb[:,[3,4,9]],1)
df['winter_summer_ratio']=np.nanmean(mm[:,winter],1)/np.nanmean(mm[:,summer],1)
df['min_month_ratio']=np.nanmin(mm,1)/np.nanmean(mm,1)   # vacancy / seasonal home
for s in ['EV','HP','PV']:
    df['lab_'+s]=df.index.isin(pd.read_csv(s+'_labels.csv').CUSTOMER_NUMBER).astype(int)
df['valid']=(df.n_valid>=0.9*8760)
df.to_csv('features.csv')
v=df[df.valid]
print('valid customers',len(v),'labels in valid: EV',v.lab_EV.sum(),'HP',v.lab_HP.sum(),'PV',v.lab_PV.sum())
cols=['annual_kwh','pmax','p95','load_factor','base_night_p05','night_share','evening_share','midday_share','blocks3','blocks5','hrs_gt6','heat_slope','cool_slope','cold_extra_slope','heat_bp','weather_r2','corr_cold','corr_hot','solar_dip_summer','solar_dip_winter','zero_hours','min_kw','summer_base_lift','winter_summer_ratio','min_month_ratio','cv']
rows=[]
for c in cols:
    r={'feature':c,'all_med':v[c].median()}
    for s in ['EV','HP','PV']:
        a=v.loc[v['lab_'+s]==1,c]; b=v.loc[v['lab_'+s]==0,c]
        r[s+'_med']=a.median()
        # rank AUC
        ranks=pd.concat([a,b]).rank(); au=(ranks.iloc[:len(a)].sum()-len(a)*(len(a)+1)/2)/(len(a)*len(b))
        r[s+'_auc']=au
    rows.append(r)
pd.set_option('display.width',200)
print(pd.DataFrame(rows).round(3).to_string(index=False))
