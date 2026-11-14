import numpy as np, pandas as pd
S=np.load('system_load.npy')/1000; ts=pd.date_range('2025-09-01',periods=8760,freq='h'); Sd=S.reshape(365,24)
T=np.load('hourly_temp.npy')
top50=np.argsort(-S)[:50]
# event days: top 60 days by daily max
ev_days=np.sort(np.argsort(-Sd.max(1))[:60])
# window: best 3 consecutive hours (start 12..19) per event day
win=np.zeros((365,),int)
for d in range(365):
    sums=[Sd[d,h:h+3].sum() for h in range(12,20)]; win[d]=12+int(np.argmax(sums))
covered=sum(1 for h in top50 if (h//24 in ev_days) and win[h//24]<=h%24<win[h//24]+3)
days=pd.date_range('2025-09-01',periods=365,freq='D')
print('top 50 hours: months',pd.Series(ts[top50].month).value_counts().sort_index().to_dict(),' hours',pd.Series(ts[top50].hour).value_counts().sort_index().to_dict())
print('top 50 hours covered by 60 event-day 3h windows:',covered)
print('event days by month',pd.Series(days[ev_days].month).value_counts().sort_index().to_dict())
print('window start hours',pd.Series(win[ev_days]).value_counts().sort_index().to_dict())
print('winter event days', [str(days[d].date()) for d in ev_days if days[d].month in (12,1,2)])
print('50th hour MW',round(S[top50].min(),1),' peak',round(S.max(),1))
np.savez('events.npz',top50=top50,ev_days=ev_days,win=win)
