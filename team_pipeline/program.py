import numpy as np, pandas as pd
v=pd.read_pickle('ranked.pkl'); S=np.load('system_load.npy')/1000; Sd=S.reshape(365,24)  # MW
top50=np.argsort(-S)[:50]; tdays=np.unique(top50//24)
def fleet(n,E=16.128,P=7.68,therm=0.0,ev=0.0):
    # staggered fleet: per top day, water-fill system load with fleet energy n*E (MWh) and power n*P (MW); flex reduces load first
    Snew=Sd.copy()
    flex=np.zeros(24); 
    for d in range(365):
        Snew[d]=Sd[d]
    Snew=Snew.ravel().copy(); Snew[top50]-=0  # placeholder
    S2=Sd.copy()
    for d in tdays:
        L=S2[d].copy()
        # flexibility at that day's top 6 hours (thermostat + EV), MW
        h6=np.argsort(-L)[:6]; L[h6]-= (therm+ev)
        Etot=n*E/1000; Ptot=n*P/1000; lo,hi=0,L.max()
        for _ in range(50):
            mid=(lo+hi)/2; e=np.minimum(np.clip(L-mid,0,None),Ptot).sum()
            lo,hi=(mid,hi) if e>Etot else (lo,mid)
        L=L-np.minimum(np.clip(L-hi,0,None),Ptot); S2[d]=L
    S2=S2.ravel(); return S2
P=v[v.tier=='Priority']; Sx=v[v.tier=='Secondary']
therm_all=v.thermostat_kw.sum()/1000; ev_all=v.ev_shift_top50.sum()/1000
scen={'Today':S.copy(),
      f'Batteries: priority ({len(P):,})':fleet(len(P)),
      f'Batteries: priority + secondary ({len(P)+len(Sx):,})':fleet(len(P)+len(Sx)),
      'Priority batteries + thermostats + EV charging':fleet(len(P),therm=therm_all*0.3,ev=ev_all*0.5)}
rows=[]
for k,s in scen.items():
    rows.append({'Scenario':k,'Peak MW':s.max(),'Avg of top 50 original hours MW':s[top50].mean(),'Peak cut MW':S.max()-s.max(),'Top 50 hours reduced':int((S[top50]-s[top50]>0.01).sum())})
t=pd.DataFrame(rows).round(2); print(t.to_string(index=False)); t.to_csv('program_scenarios.csv',index=False)
np.savez('scen.npz',**{f's{i}':s for i,s in enumerate(scen.values())})
print('thermostat potential MW (all central AC)',round(therm_all,2),' assume 30% enroll ->',round(therm_all*0.3,2),'; EV',round(ev_all,2),'assume 50% ->',round(ev_all*.5,2))
cr=(P.kwh_yr/60/0.894/7); print('priority overnight charge rate kW median',round(cr.median(),2),'max',round(cr.max(),2))
print('secondary sizing: 1u',(Sx.units==1).sum(),'2u',(Sx.units==2).sum(),' avg red1/red2 priority',round((P.red1_top50/P.red2_top50).mean(),2))
cut=S.max()-list(scen.values())[1].max()
print('capacity value priority fleet: peak cut %.2f MW -> $%.0fk to $%.0fk per year at $50 to $275 per kW-season'%(cut,cut*1000*50/1000,cut*1000*275/1000))
