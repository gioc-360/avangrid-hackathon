import numpy as np, pandas as pd
v=pd.read_pickle('ranked.pkl')
_sc=pd.read_csv('program_scenarios.csv'); fleet_kw_per_batt=_sc['Peak cut MW'].iloc[1]*1000/(v.tier=='Priority').sum()   # staggered fleet: peak cut per priority battery
TH_ENR, EV_ENR = 0.30, 0.50
v['therm_elig']=v.air_conditioning=='Central likely'
v['ev_elig']=v.ev.isin(['High','Medium'])
v['batt']=v.tier=='Priority'
g=v.groupby('segment')
t=pd.DataFrame({
 'Customers':g.size(),
 'Load at top 50 hrs MW':g.load_top50.sum()/1000,
 'Thermostat eligible':g.therm_elig.sum(),
 'Thermostat kW per home':g.apply(lambda x: x.loc[x.therm_elig,'thermostat_kw'].mean()),
 'Thermostat MW technical':g.thermostat_kw.sum()/1000,
 'EV eligible':g.ev_elig.sum(),
 'EV kW per home':g.apply(lambda x: x.loc[x.ev_elig,'ev_shift_top50'].mean()),
 'EV MW technical':g.ev_shift_top50.sum()/1000,
 'Batteries (priority)':g.batt.sum(),
 'Battery kW per home (behind meter)':g.apply(lambda x: x.loc[x.batt,'red_top50'].mean()),
 'Battery MW (fleet)':g.batt.sum()*fleet_kw_per_batt/1000,
})
t['Thermostat MW at 30%']=t['Thermostat MW technical']*TH_ENR
t['EV MW at 50%']=t['EV MW technical']*EV_ENR
t['Total MW (program)']=t['Thermostat MW at 30%']+t['EV MW at 50%']+t['Battery MW (fleet)']
t['Share of segment top-hour load cut %']=100*t['Total MW (program)']/t['Load at top 50 hrs MW']
t['Share of total cut %']=100*t['Total MW (program)']/t['Total MW (program)'].sum()
t=t.sort_values('Total MW (program)',ascending=False)
pd.set_option('display.width',250)
print(t.round(2).T.to_string())
tot=t[['Thermostat MW technical','Thermostat MW at 30%','EV MW technical','EV MW at 50%','Battery MW (fleet)','Total MW (program)','Load at top 50 hrs MW']].sum().round(2); print(tot.to_dict())
print('fleet kW per battery',round(fleet_kw_per_batt,2))
t.round(3).to_csv('segment_technology_reduction.csv')
