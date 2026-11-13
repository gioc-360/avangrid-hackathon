import numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
P_="/Users/giocaballero/avangrid-hackathon/data/processed/"; O="/Users/giocaballero/avangrid-hackathon/runs/plain/out/"; G="/Users/giocaballero/avangrid-hackathon/runs/plain/"
F=pd.read_parquet(O+"scored.parquet"); R=pd.read_parquet(O+"customer_results.parquet"); L=np.load(P_+"load_present.npy",mmap_mode="r")
tc=np.load(O+"tcurve.npy"); prof=np.load(O+"profiles.npy"); top_s=np.load(O+"top_s.npy")
plt.rcParams.update({"font.size":9,"axes.spines.top":False,"axes.spines.right":False})
# 1 label validation
rows=[("PV flag",R.pv.isin(["high","medium"]),"lab_pv"),("EV L2 high",R.ev_l2=="high","lab_ev"),("EV L2 any",R.ev_l2!="","lab_ev"),
      ("EV L1 (low)",R.ev_l1!="","lab_ev"),("Electric heat",R.elec_heat!="","lab_hp"),("HP-likely",R.heat_type=="heat-pump-likely","lab_hp")]
fig,ax=plt.subplots(figsize=(7,3.2)); y=np.arange(len(rows))
lab=[100*m[F[l]==1].mean() for _,m,l in rows]; un=[100*m[F[l]==0].mean() for _,m,l in rows]
ax.barh(y+0.2,lab,0.4,label="share of labeled positives flagged (recall, %)",color="#2b6cb0"); ax.barh(y-0.2,un,0.4,label="share of unlabeled flagged (%)",color="#a0aec0")
for i,(a,b) in enumerate(zip(lab,un)): ax.text(a+1,i+0.2,f"{a:.0f}%",va="center"); ax.text(b+1,i-0.2,f"{b:.1f}%",va="center")
ax.set_yticks(y,[r[0] for r in rows]); ax.invert_yaxis(); ax.set_xlabel("% of customers"); ax.legend(frameon=False,loc="lower right"); ax.set_title("Classifier recall on labeled customers vs flag rate in everyone else")
fig.tight_layout(); fig.savefig(G+"fig1_label_validation.png",dpi=150); plt.close()
# 2 signature heatmaps
ex={}
def pick(m,key): i=np.where(m)[0]; return i[np.argsort(F[key].values[i])[len(i)//2]]
ex["Solar PV (zeros at midday)"]=pick((R.pv=="high").values,"zero_mid_S")
ex["EV Level 2 (evening blocks)"]=pick((R.ev_l2=="high").values,"l2_days_all")
ex["Electric heat (winter, cold)"]=pick((R.elec_heat=="high").values,"heat_kwh_yr")
ex["Pool (summer daytime floor)"]=pick((R.pool=="high").values,"pool_floor_delta_kw")
ex["Seasonal / part-year"]=pick((R.seasonal_home!="").values,"low_days")
ex["AC, high (summer afternoons)"]=pick(((R.ac=="high")&(R.segment=="6 Summer peak contributor")).values,"b_cool")
fig,axs=plt.subplots(2,3,figsize=(11,6))
for ax,(t,i) in zip(axs.flat,ex.items()):
    M=np.asarray(L[i]).reshape(365,24).T; im=ax.imshow(M,aspect="auto",cmap="magma",vmax=np.percentile(M,99.5),origin="lower")
    ax.set_title(t); ax.set_ylabel("hour of day"); ax.set_xticks([0,92,182,273,364],["Sep","Dec","Mar","Jun","Aug"]); fig.colorbar(im,ax=ax,label="kWh/h")
fig.suptitle("One typical high-confidence home per class: hourly load, day of year (x) by hour (y)"); fig.tight_layout(); fig.savefig(G+"fig2_signatures.png",dpi=140); plt.close()
# 3 segments vs peak share
g=pd.read_csv(O+"segment_table.csv",index_col=0)
fig,ax=plt.subplots(figsize=(8,4)); y=np.arange(len(g))
ax.barh(y-0.27,g.cust_share,0.27,label="% of customers",color="#a0aec0"); ax.barh(y,g.S_share,0.27,label="% of summer system peak",color="#dd6b20"); ax.barh(y+0.27,g.W_share,0.27,label="% of winter system peak",color="#2b6cb0")
ax.set_yticks(y,g.index); ax.invert_yaxis(); ax.set_xlabel("% (peak = mean of top-100 system hours)"); ax.legend(frameon=False); ax.set_title("Segment share of customers vs share of system peak")
fig.tight_layout(); fig.savefig(G+"fig3_segment_peak_share.png",dpi=150); plt.close()
# 4 temperature response
lbl=[-5,5,15,25,35,45,55,65,75,85]; fig,ax=plt.subplots(figsize=(7,4))
for name,m,c in [("all customers",np.ones(len(F),bool),"k"),("electric heat (flag)",(R.elec_heat!="").values,"#2b6cb0"),("labeled heat pump",F.lab_hp.values==1,"#38a169"),
                 ("EV L2 (flag)",(R.ev_l2!="").values,"#805ad5"),("solar PV (flag)",R.pv.isin(["high","medium"]).values,"#d69e2e"),("pool (flag)",(R.pool!="").values,"#e53e3e")]:
    ax.plot(lbl,np.median(tc[m],0),marker="o",label=f"{name} (n={m.sum():,})",color=c)
ax.set_xlabel("outdoor temperature, 10F bin centre (F)"); ax.set_ylabel("median kW (kWh/h)"); ax.legend(frameon=False,fontsize=8); ax.set_title("Load vs outdoor temperature by class")
fig.tight_layout(); fig.savefig(G+"fig4_temp_response.png",dpi=150); plt.close()
# 5 supply curve
el=~R.segment.isin(["0 Inactive","1 Seasonal/part-year"]); r=R[el].sort_values("cp_u1",ascending=False)
fig,ax=plt.subplots(figsize=(7,4)); N=np.arange(1,len(r)+1)
ax.plot(N,r.cpS_u1.cumsum()/1e3,label="summer: mean of top-100 system hours",color="#dd6b20"); ax.plot(N,r.cpW_u1.cumsum()/1e3,label="winter: mean of top-100 system hours",color="#2b6cb0")
ax.axvline(1958,ls=":",color="gray"); ax.text(2100,1,"tier A (1,958 homes)",color="gray")
ax.set_xscale("log"); ax.set_xlabel("homes with one 20.16 kWh / 7.68 kW unit, ranked by coincident kW"); ax.set_ylabel("coincident relief (MW)"); ax.legend(frameon=False); ax.set_title("Battery supply curve: MW of system-peak relief vs homes enrolled")
fig.tight_layout(); fig.savefig(G+"fig5_battery_supply_curve.png",dpi=150); plt.close()
# 6 dispatch example: tier A1 median home on system summer peak day
cand=np.where((R.tier.str.startswith("A")&(R.cpS_u1>R.cpW_u1)).values)[0]; i=cand[np.argsort(R.cpS_u1.values[cand])[len(cand)//2]]
d=np.load(P_+"sysload.npy").argmax()//24; x=np.asarray(L[i]).reshape(365,24)[d].astype(float)
tops=top_s[top_s//24==d]%24; after=x.copy(); r_=np.minimum(x[tops],7.68); r_*=min(1,20.16/r_.sum()); after[tops]-=r_
need=r_.sum()/0.894; ch=[h for h in range(0,7)]; after[ch]+=need/len(ch)
fig,ax=plt.subplots(figsize=(7,3.5)); ax.step(range(24),x,where="mid",label="home load (meter)",color="k"); ax.step(range(24),after,where="mid",label="with battery: charge 0-6h, discharge in system-peak hours",color="#dd6b20")
ax.axvspan(tops.min()-0.5,tops.max()+0.5,color="#fbd38d",alpha=0.4,label="system top-100 hours this day")
ax.set_xlabel("hour of day"); ax.set_ylabel("kW"); ax.legend(frameon=False,fontsize=8); ax.set_title(f"Median summer tier-A home on the system peak day ({pd.Timestamp('2025-09-01')+pd.Timedelta(days=int(d)):%Y-%m-%d})")
fig.tight_layout(); fig.savefig(G+"fig6_dispatch_example.png",dpi=150); plt.close()
# 7 kmeans centroids
cen=np.load(O+"centroids.npy")[:,:72].reshape(-1,3,24); fig,axs=plt.subplots(1,6,figsize=(14,2.8),sharey=True)
cnt=R.shape_cluster.value_counts()
for k,ax in enumerate(axs):
    for s,c,nm in [(0,"#2b6cb0","winter"),(1,"#dd6b20","summer"),(2,"#718096","shoulder")]: ax.plot(cen[k,s],color=c,label=nm)
    ax.set_title(f"shape {k} (n={cnt.get(k,0):,})"); ax.set_xticks([0,6,12,18,23])
axs[0].set_ylabel("kW / own annual mean kW"); axs[0].legend(frameon=False,fontsize=7); fig.suptitle("k-means (k=6) daily load shapes by season; silhouette 0.13 = shapes form a continuum")
fig.tight_layout(); fig.savefig(G+"fig7_kmeans_shapes.png",dpi=140); plt.close()
print("ok")
