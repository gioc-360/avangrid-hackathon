"""One feature row per customer from the dense load matrix + weather.

Every feature names the physical signature it is meant to catch, so a judge can
trace a classification back to a load shape. Runs in about a minute.
"""
import os, numpy as np, pandas as pd
P = os.path.expanduser("~/avangrid-hackathon/data/processed/")
D = "/Users/giocaballero/Downloads/00_Hackathon Materials/Data/"

present = np.load(P + "present.npy")
ids = np.where(present)[0] + 1
L = np.asarray(np.load(P + "load.npy", mmap_mode="r")[present], dtype=np.float32)
L = pd.DataFrame(L).ffill(axis=1).bfill(axis=1).to_numpy(np.float32)   # 2 DST gaps per customer
np.save(P + "load_present.npy", L)
n = len(ids)
w = pd.read_parquet(P + "weather.parquet")
temp = w["temp"].to_numpy()
hours = pd.date_range("2025-09-01", periods=8760, freq="h")
days = pd.date_range("2025-09-01", periods=365, freq="D")
hod = np.tile(np.arange(24), 365)
mon_d = days.month.to_numpy()
D3 = L.reshape(n, 365, 24)
daily = D3.sum(2)
tday = temp.reshape(365, 24).mean(1)
F = pd.DataFrame({"CUSTOMER_NUMBER": ids})

# size and shape
F["annual_kwh"] = daily.sum(1)
F["peak_kw"] = L.max(1)
F["p99_kw"] = np.percentile(L, 99, axis=1)
F["base_kw"] = np.percentile(L, 5, axis=1)
F["load_factor"] = L.mean(1) / np.maximum(F["peak_kw"], 1e-3)
pk = L.argmax(1)
F["peak_hour"] = hod[pk]; F["peak_month"] = hours.month.to_numpy()[pk]
for m in range(1, 13):
    F[f"kwh_m{m:02d}"] = daily[:, mon_d == m].sum(1)

# season ratios: winter and summer daily use vs mild shoulder months
sh = np.isin(mon_d, [4, 5, 10]); wi = np.isin(mon_d, [12, 1, 2]); su = np.isin(mon_d, [7, 8])
F["winter_ratio"] = daily[:, wi].mean(1) / np.maximum(daily[:, sh].mean(1), 0.1)
F["summer_ratio"] = daily[:, su].mean(1) / np.maximum(daily[:, sh].mean(1), 0.1)

# weather response: daily kWh = b0 + b_hmild*HDDmild + b_hcold*HDDcold + b_cdd*CDD + b_we*weekend
hdd = np.maximum(0, 60 - tday); cdd = np.maximum(0, tday - 65)
X = np.column_stack([np.ones(365), np.minimum(hdd, 25), np.maximum(0, hdd - 25), cdd,
                     (days.dayofweek >= 5).astype(float)])
B, *_ = np.linalg.lstsq(X, daily.T, rcond=None)
res = daily.T - X @ B
F["b_base"], F["b_heat_mild"], F["b_heat_cold"], F["b_cool"], F["b_weekend"] = B
F["weather_r2"] = 1 - res.var(0) / np.maximum(daily.T.var(0), 1e-6)
F["heat_kwh_yr"] = (X[:, 1:3] @ B[1:3]).clip(0).sum(0)          # weather-driven heating energy
F["cool_kwh_yr"] = (X[:, 3] * B[3][None, :].T).clip(0).sum(1) if False else np.outer(B[3], X[:, 3]).clip(0).sum(1)
F["heat_nonlin"] = B[2] / np.where(np.abs(B[1]) < 0.05, np.nan, B[1])   # COP drop / backup strips below 35F
# hourly cold response: kW at coldest 100 hours minus mild-night kW
cold_h = np.argsort(temp)[:100]
mild_night = np.where((temp > 50) & (temp < 62) & (hod < 6))[0]
F["cold_kw_lift"] = L[:, cold_h].mean(1) - L[:, mild_night].mean(1)
hot_h = np.argsort(temp)[-100:]
F["hot_kw_lift"] = L[:, hot_h].mean(1) - L[:, mild_night].mean(1)

# seasonal / vacant homes
med = np.median(daily, 1, keepdims=True)
F["low_days"] = (daily < 0.3 * np.maximum(med, 0.5)).sum(1)
mm = np.stack([daily[:, mon_d == m].mean(1) for m in range(1, 13)], 1)
F["month_cv"] = mm.std(1) / np.maximum(mm.mean(1), 0.1)
F["min_month_share"] = mm.min(1) / np.maximum(mm.max(1), 0.1)

# solar: hours at exactly zero (export netted to 0) at midday vs night
summer_mid = np.isin(hours.month, [5, 6, 7, 8]) & (hod >= 10) & (hod <= 14)
F["zero_mid_summer"] = (L[:, summer_mid] == 0).mean(1)
eve = (hod >= 18) & (hod <= 22)
F["zero_evening"] = (L[:, eve] == 0).mean(1)
F["zero_night"] = (L[:, hod <= 4] == 0).mean(1)

# EV: big steps and high blocks in mild months, when HVAC is not the cause
shm = np.isin(hours.month, [4, 5, 9, 10])
dL = np.diff(L, axis=1, prepend=L[:, :1])
up3 = (dL >= 3.0) & shm
F["ev_up3_shoulder"] = up3.sum(1)
F["ev_up3_night_share"] = (up3 & ((hod >= 18) | (hod <= 5))).sum(1) / np.maximum(up3.sum(1), 1)
hi = L >= (F["base_kw"].to_numpy()[:, None] + 5.0)
F["ev_hi5_shoulder"] = (hi & shm).sum(1)
F["ev_hi5_days_shoulder"] = ((hi & shm).reshape(n, 365, 24).any(2)).sum(1)
# Level 2 plateau: 2+ consecutive hours both >= base+5 kW in mild months (resistive water heaters rarely hold that)
pl2 = hi[:, 1:] & hi[:, :-1] & shm[1:]
F["ev_plateau2_shoulder"] = pl2.sum(1)
# Level 1: overnight lift of 1.0-2.5 kW held 4+ hours on mild nights
night = D3[:, :, 0:6]
lift = night - F["base_kw"].to_numpy()[:, None, None]
l1night = ((lift >= 1.0) & (lift <= 2.5)).sum(2) >= 4
F["ev_l1_nights_shoulder"] = l1night[:, np.isin(mon_d, [4, 5, 9, 10])].sum(1)
F["max_step_kw"] = np.percentile(np.where(up3, dL, np.nan), 90, axis=1) if False else np.nanmax(np.where(shm, dL, np.nan), axis=1)

# pool: same temperature, different season. Summer days 58-72F vs spring/fall days 58-72F
mild = (tday >= 58) & (tday <= 72)
pool_season = mild & (((mon_d == 6) & (days.day >= 15)) | np.isin(mon_d, [7, 8]))
off_season = mild & (np.isin(mon_d, [4, 5, 10]) | ((mon_d == 9) & (days.day >= 20)))
F["pool_delta_kwh_day"] = daily[:, pool_season].mean(1) - daily[:, off_season].mean(1)
day_min = D3[:, :, 9:17].min(2)   # pump keeps a daytime floor
F["pool_floor_delta_kw"] = day_min[:, pool_season].mean(1) - day_min[:, off_season].mean(1)

# hot tub / water heater: isolated 1-hour spikes (>= 2.5 kWh above both neighbours)
spike = (L[:, 1:-1] - np.maximum(L[:, :-2], L[:, 2:])) >= 2.5
spike = np.pad(spike, ((0, 0), (1, 1)))
F["spike_night"] = (spike & (hod <= 4)).sum(1)
F["spike_morning"] = (spike & (hod >= 5) & (hod <= 9)).sum(1)
F["spike_winter_share"] = (spike & np.isin(hours.month, [12, 1, 2])).sum(1) / np.maximum(spike.sum(1), 1)

# system coincident peak contribution
sysload = L.sum(0)
w_mask = np.isin(hours.month, [11, 12, 1, 2, 3]); s_mask = np.isin(hours.month, [6, 7, 8])
top_w = np.where(w_mask)[0][np.argsort(sysload[w_mask])[-20:]]
top_s = np.where(s_mask)[0][np.argsort(sysload[s_mask])[-20:]]
F["cp_winter_kw"] = L[:, top_w].mean(1); F["cp_summer_kw"] = L[:, top_s].mean(1)
F["cp_kw"] = np.maximum(F["cp_winter_kw"], F["cp_summer_kw"])
F["cp_ratio"] = F["cp_kw"] / np.maximum(L.mean(1), 0.05)       # >1: peaks when the system peaks
np.save(P + "sysload.npy", sysload)
pd.Series({"top_winter_hours": [str(hours[i]) for i in sorted(top_w)],
           "top_summer_hours": [str(hours[i]) for i in sorted(top_s)]}).to_json(P + "system_peaks.json")

# labels
x = pd.read_excel(D + "EV_Heat Pump_Solar PV Customers.xlsx", sheet_name=None)
for tab, col in [("EV Customers", "lab_ev"), ("HP Customers", "lab_hp"), ("PV Customers", "lab_pv")]:
    F[col] = F.CUSTOMER_NUMBER.isin(x[tab].CUSTOMER_NUMBER).astype(int)
F.to_parquet(P + "features.parquet")
np.save(P + "daily.npy", daily.astype(np.float32))
print(F.shape)
print(F.groupby("lab_ev")[["annual_kwh","peak_kw","ev_up3_shoulder","ev_plateau2_shoulder","ev_hi5_days_shoulder","ev_l1_nights_shoulder"]].median().T)
print(F.groupby("lab_hp")[["annual_kwh","winter_ratio","b_heat_mild","b_heat_cold","heat_nonlin","b_cool","cold_kw_lift"]].median().T)
print(F.groupby("lab_pv")[["annual_kwh","zero_mid_summer","zero_evening","zero_night"]].median().T)
print("system peaks", open(P+"system_peaks.json").read()[:400])
