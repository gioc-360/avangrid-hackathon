"""Part 2: segments a program manager can act on, and the system insights behind them.

Segments are assigned in priority order from the Part 1 classes (a home lands in the
first segment it matches). Why rules and not clusters: k-means on normalized seasonal
day shapes gives low silhouette (recorded below), so load shapes form a continuum;
both analyst runs found the same thing independently.
Peak share = segment's summed kW over the season's top-100 system hours / system total.
"""
import os, sys, time
import numpy as np, pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from facts import record

t0 = time.time()
ROOT = os.path.expanduser("~/avangrid-hackathon/")
P = ROOT + "data/processed/"
F = pd.read_parquet(P + "classified.parquet")
L = np.load(P + "load_present.npy", mmap_mode="r")
w = pd.read_parquet(P + "weather.parquet")
sysl = np.load(P + "sysload.npy")
hours = pd.date_range("2025-09-01", periods=8760, freq="h")
temp = w["temp"].to_numpy()
n = len(F)

summer = np.isin(hours.month, [6, 7, 8]); winter = np.isin(hours.month, [11, 12, 1, 2, 3])
top_s = np.where(summer)[0][np.argsort(sysl[summer])[-100:]]
top_w = np.where(winter)[0][np.argsort(sysl[winter])[-100:]]
kw_s = np.asarray(L[:, top_s]).mean(1); kw_w = np.asarray(L[:, top_w]).mean(1)
F["cp_summer_kw"], F["cp_winter_kw"] = kw_s, kw_w
q75 = np.quantile(kw_s, 0.75)

SEGMENTS = [  # name, rule, action
    ("inactive", F.is_other_inactive, "Field check the meter; drop from forecasts"),
    ("seasonal", F.is_other_seasonal, "Forecast as its own class; skip for batteries and DR"),
    ("solar", F.is_solar, "Offer solar + storage: charge from midday surplus, discharge into the evening peak"),
    ("dual_electrified", F.is_ev_l2 & F.is_electric_heat, "First battery and service-upgrade watch list"),
    ("ev_home", F.is_ev_l2, "Managed charging and an EV time-of-use rate"),
    ("electric_heat", F.is_electric_heat, "Winter DR, weatherization, resistance-to-heat-pump conversion"),
    ("summer_peaker", (kw_s >= q75) & (F.is_ac | F.is_pool), "Smart-thermostat DR, pool-pump timers, battery tier for grid relief"),
    ("emerging", (F.annual_kwh >= F.annual_kwh.median()) & F.is_ac, "Market heat pumps: they already own cooling, a heat pump replaces it"),
    ("baseline", pd.Series(True, index=F.index), "Mass-market, low-cost channels only"),
]
seg = np.full(n, "", dtype=object)
for name, rule, _ in SEGMENTS:
    seg[(seg == "") & np.asarray(rule)] = name
F["segment"] = seg
for name, _, action in SEGMENTS:
    m = seg == name
    record(f"seg.{name}.count", int(m.sum()), "homes", "")
    record(f"seg.{name}.share_pct", round(100 * m.mean(), 1), "% of homes", "")
    record(f"seg.{name}.median_kwh", int(np.median(F.annual_kwh[m])), "kWh/yr", "")
    record(f"seg.{name}.summer_peak_share_pct", round(100 * kw_s[m].sum() / kw_s.sum(), 1), "% of summer top-100h load", "")
    record(f"seg.{name}.winter_peak_share_pct", round(100 * kw_w[m].sum() / kw_w.sum(), 1), "% of winter top-100h load", "")
    record(f"seg.{name}.action", action, "", "")

# clustering evidence: is there natural structure?
rng = np.random.default_rng(0)
idx = np.sort(rng.choice(np.where(~F.is_other_inactive)[0], 6000, replace=False))
A = np.asarray(L[idx])
prof = []
for mask in (winter, np.isin(hours.month, [4, 5, 9, 10]), summer):
    d = A[:, mask].reshape(len(idx), -1, 24).mean(1)
    prof.append(d / np.maximum(d.mean(1, keepdims=True), 1e-3))
X = np.hstack(prof + [np.log1p(F.annual_kwh.to_numpy()[idx])[:, None] * 3])
X = (X - X.mean(0)) / (X.std(0) + 1e-9)
for k in (3, 6):
    lab = KMeans(k, n_init=5, random_state=0).fit_predict(X)
    record(f"insight.kmeans_silhouette_k{k}", round(float(silhouette_score(X, lab)), 3), "silhouette",
           "normalized 24h x 3-season shapes + log size; <0.25 means no strong natural clusters")

# system insights
pk = int(np.argmax(sysl))
record("insight.system_peak_mw", round(sysl.max() / 1000, 1), "MW", "sum of all usable homes, annual max hour")
record("insight.system_peak_temp_f", float(temp[pk]), "F", "")
record("insight.system_peak_when", str(hours[pk]), "", "")
wpk = top_w[np.argmax(sysl[top_w])]
record("insight.winter_peak_mw", round(sysl[wpk] / 1000, 1), "MW", "")
record("insight.winter_peak_temp_f", float(temp[wpk]), "F", "")
record("insight.winter_peak_when", str(hours[wpk]), "", "")
gap = (sysl.max() - sysl[wpk]) / 1000
record("insight.summer_minus_winter_mw", round(gap, 1), "MW", "")

# when does electrified heat flip the system to winter peaking?
# added kW per converted home at the winter peak hour = electric-heat homes' median lift there over other homes
eh = F.is_electric_heat.to_numpy()
add_kw = float(np.median(np.asarray(L[eh, wpk])) - np.median(np.asarray(L[~eh & ~F.is_other_inactive.to_numpy(), wpk])))
flip = gap * 1000 / add_kw
record("insight.heat_conversion_added_kw_at_winter_peak", round(add_kw, 2), "kW per home", "median electric-heat home minus median other home at the winter peak hour")
record("insight.homes_to_flip_winter_peaking", int(round(flip, -1)), "homes", "summer-winter gap / added kW per conversion")
record("insight.share_to_flip_winter_peaking_pct", round(100 * flip / n, 1), "% of homes", "")
record("insight.electric_heat_winter_peak_share_pct", round(100 * kw_w[eh].sum() / kw_w.sum(), 1), "% of winter top-100h load", "")
record("insight.electric_heat_home_share_pct", round(100 * eh.mean(), 1), "% of homes", "")
record("insight.seasonal_winter_peak_share_pct", round(100 * kw_w[F.is_other_seasonal.to_numpy()].sum() / kw_w.sum(), 1), "% of winter top-100h load", "")

F.to_parquet(P + "segmented.parquet")
F[["CUSTOMER_NUMBER", "segment", "cp_summer_kw", "cp_winter_kw"]].round(3).to_csv(ROOT + "outputs/customer_segments.csv", index=False)
record("scale.segment_seconds", round(time.time() - t0, 1), "s", "")
print(pd.Series(seg).value_counts().to_string())
