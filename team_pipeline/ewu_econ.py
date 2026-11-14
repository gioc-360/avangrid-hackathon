import numpy as np, pandas as pd, json
af=lambda n,r=0.07:(1-(1+r)**-n)/r; A10,A15=af(10),af(15)
UPG=15000                     # Eversource overhead transformer upgrade $10,000 to $20,000 (mid)
UNIT=7000                     # one Enphase unit, half of ~$14,000 for two
LEASE=27.5*12                 # half of $55 a month for two units
NYSERDA=200*10.08             # $200 per kWh up to, per unit
CAPV=60*1.68                  # ~$60 per kW-year rest of state capacity x 1.68 kW per unit at system peak
EVC=150+86*A10                # OptimizEV style incentive per EV home
DEL=0.09138; EVKWH=3700; HPKWH=8760
out={}
for tag,f in [('Moderate','ewu_smart_Moderate.csv'),('High','ewu_smart_High.csv')]:
    d=pd.read_csv(f); n=len(d)
    ov=d.over_u; fix_ev=ov&~d.over_m; need_b=d.over_m&(d.units<=4); unres=d.over_m&(d.units>4)
    trad=ov.sum()*UPG
    ev_cost=(d.loc[ov,'nev'].sum())*EVC
    units=d.loc[need_b,'units'].sum()
    batt_gross=units*UNIT; batt_net_util=units*(UNIT-LEASE*A15-NYSERDA); batt_net_noNY=units*(UNIT-LEASE*A15)
    upg=unres.sum()*UPG
    ewu=ev_cost+batt_net_util+upg; ewu_noNY=ev_cost+batt_net_noNY+upg
    cap_cust=units*CAPV*A15
    scale_sample=33757/8/n; scale_nyseg=890000/8/n
    r=dict(transformers=n, overloaded=int(ov.sum()), fixed_by_smart_EV=int(fix_ev.sum()), need_battery=int(need_b.sum()), battery_units=int(units),
        mean_units=round(units/max(need_b.sum(),1),2), still_upgrade=int(unres.sum()),
        traditional_cost_per_overloaded=UPG, ewu_cost_per_overloaded=round(ewu/max(ov.sum(),1)), ewu_cost_noNY_per_overloaded=round(ewu_noNY/max(ov.sum(),1)),
        saving_pct=round(100*(1-ewu/trad),1), saving_pct_noNY=round(100*(1-ewu_noNY/trad),1),
        NYSEG_traditional_M=round(trad*scale_nyseg/1e6,1), NYSEG_ewu_M=round(ewu*scale_nyseg/1e6,1), NYSEG_ewu_noNY_M=round(ewu_noNY*scale_nyseg/1e6,1),
        NYSEG_batteries=int(units*scale_nyseg), NYSEG_capacity_value_to_customers_M=round(cap_cust*scale_nyseg/1e6,1))
    out[tag]=r; print(tag, json.dumps(r,indent=0))
# electrification sales on the sample
c=pd.read_csv('classification.csv',index_col=0,keep_default_na=False); N=len(c)
for tag,pe,ph in [('Moderate',0.20,0.15),('High',0.35,0.30)]:
    nev=pe*(N-(c.ev.isin(['High','Medium'])).sum()); nhp=ph*(N-(c.electric_heat=='Primary').sum())
    gwh=(nev*EVKWH+nhp*HPKWH)/1e6; base=pd.read_csv('features.csv',index_col=0).query('valid').annual_kwh.sum()/1e6
    print(tag,'EV homes',int(nev),'HP homes',int(nhp),'added GWh',round(gwh,1),'base GWh',round(base,1),'growth %',round(100*gwh/base,1),'delivery revenue $M/yr',round(gwh*1e6*DEL/1e6,2), ' NYSEG scaled $M/yr',round(gwh*1e6*DEL/1e6*890000/N,1))
json.dump(out,open('ewu_econ.json','w'),indent=1)
