"""Part 1: which homes have which equipment, with evidence and confidence.

Each class is one physical rule on features.parquet (features.py says what each
feature catches). EV and heat pump also get a positive-unlabeled model whose
out-of-fold score is the confidence. Validation uses the organizers' note that
the EV and HP lists are a random ~25% of likely owners:
    implied owners in a flagged group = labeled hits / 0.25
    precision lower bound            = 4 * labeled hits / flagged
Rules were cross-checked by two independent analyst passes; where they chose
different thresholds, both are recorded as a sensitivity range.
Writes outputs/customer_classes.csv and facts/facts.json.
"""
import os, sys
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from facts import record

ROOT = os.path.expanduser("~/avangrid-hackathon/")
P = ROOT + "data/processed/"
os.makedirs(ROOT + "outputs", exist_ok=True)
F = pd.read_parquet(P + "features.parquet")
L = np.load(P + "load_present.npy", mmap_mode="r")
w = pd.read_parquet(P + "weather.parquet")
n = len(F)
SAMPLE = 0.25
hours = pd.date_range("2025-09-01", periods=8760, freq="h")
tday = w["temp"].to_numpy().reshape(365, 24).mean(1)

# ---------- extra EV evidence on weather-neutral days (55-70 F mean): HVAC is quiet, so a block is a charger
neutral = np.where((tday >= 55) & (tday <= 70))[0]
D3 = np.asarray(L).reshape(n, 365, 24)[:, neutral, :]
p25 = np.percentile(D3, 25, axis=2, keepdims=True)
blk = (D3 - p25) >= 5.0                                      # Level 2 = 6-7.7 kW chargers
two = blk[:, :, 1:] & blk[:, :, :-1]                         # held 2+ hours
start_hr = np.argmax(two, axis=2)
has = two.any(2)
night_start = has & ((start_hr >= 16) | (start_hr <= 3))
F["ev_l2_days"] = has.sum(1)
F["ev_l2_night_share"] = night_start.sum(1) / np.maximum(has.sum(1), 1)
lift = D3[:, :, 0:6] - F["base_kw"].to_numpy()[:, None, None]
F["ev_l1_nights"] = (((lift >= 1.0) & (lift <= 2.5)).sum(2) >= 4).sum(1)
del D3, blk, two

# solar + battery: zeros that continue after dark in summer
summer_eve = np.isin(hours.month, [5, 6, 7, 8]) & np.isin(hours.hour, [20, 21, 22])
F["zero_summer_eve"] = (np.asarray(L[:, summer_eve]) == 0).mean(1)

lab_ev, lab_hp, lab_pv = F.lab_ev == 1, F.lab_hp == 1, F.lab_pv == 1

# ---------- positive-unlabeled models (confidence scores)
WEATHER = ["b_heat_mild", "b_heat_cold", "b_cool", "weather_r2", "heat_kwh_yr", "cool_kwh_yr",
           "heat_nonlin", "cold_kw_lift", "hot_kw_lift"]
BASE = ["annual_kwh", "peak_kw", "p99_kw", "base_kw", "load_factor", "peak_hour", "peak_month",
        "winter_ratio", "summer_ratio", "month_cv", "min_month_share", "low_days",
        "ev_up3_shoulder", "ev_up3_night_share", "ev_hi5_shoulder", "ev_hi5_days_shoulder",
        "ev_plateau2_shoulder", "ev_l1_nights_shoulder", "max_step_kw", "spike_night",
        "spike_morning", "spike_winter_share", "ev_l2_days", "ev_l2_night_share", "ev_l1_nights",
        "zero_mid_summer", "pool_delta_kwh_day", "pool_floor_delta_kw"]

def pu_scores(y, cols, seeds=(0, 1)):
    X = F[cols].to_numpy(np.float32)
    s = np.zeros(n)
    for seed in seeds:
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=seed).split(X, y):
            m = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=15,
                                               class_weight="balanced", random_state=seed)
            m.fit(X[tr], y[tr])
            s[te] += m.predict_proba(X[te])[:, 1] / len(seeds)
    return s

for name, y in [("ev", lab_ev.to_numpy()), ("heat_pump", lab_hp.to_numpy())]:
    s_all = pu_scores(y, BASE + WEATHER)
    s_now = pu_scores(y, BASE)
    auc_all, auc_now = roc_auc_score(y, s_all), roc_auc_score(y, s_now)
    F[f"score_{name}"] = s_all
    # labeled-vs-unlabeled AUC understates true AUC (hidden positives sit in the unlabeled pool)
    record(f"class.{name}.pu_auc", round(auc_all, 3), "AUC", "out-of-fold, labeled vs unlabeled, 5-fold x 2 seeds")
    record(f"class.weather_gain.{name}_auc_without_weather", round(auc_now, 3), "AUC", "same model, weather-response features removed")
    record(f"class.weather_gain.{name}_auc_points", round(100 * (auc_all - auc_now), 1), "AUC points", "with minus without weather")
    # calibrate to a probability: P(owner) ~ P(labeled | x) / c, c = mean score on labeled (Elkan-Noto)
    c = s_all[y == 1].mean()
    F[f"p_{name}"] = np.clip(s_all / c, 0, 1)

# ---------- rules
def flag(name, mask, method, conf, labels=None):
    mask = np.asarray(mask)
    F[f"is_{name}"] = mask
    record(f"class.{name}.count", int(mask.sum()), "homes", method)
    record(f"class.{name}.share_pct", round(100 * mask.mean(), 1), "% of homes", "")
    record(f"class.{name}.method", method, "", "")
    record(f"class.{name}.confidence", conf, "", "")
    if labels is not None:
        hits = int((mask & labels).sum())
        record(f"class.{name}.labeled_hits", hits, "labeled homes", "")
        record(f"class.{name}.recall_pct", round(100 * hits / labels.sum(), 1), "% of labeled", "")

inactive = F.annual_kwh < 300
seasonal = (F.min_month_share < 0.15) & ~inactive
solar = (F.zero_mid_summer >= 0.05) & (F.zero_night <= 0.02) & ~inactive
flag("solar", solar, "summer 10-14h meter reads exactly 0 in >=5% of hours (export nets to zero), nights do not", "high", lab_pv)
record("class.solar.recall_heldout", round(100 * (solar & lab_pv).sum() / lab_pv.sum(), 1), "% of known PV", "PV list is complete, so this is true recall")
record("class.solar.precision_pct", round(100 * (solar & lab_pv).sum() / solar.sum(), 1), "%", "PV list is complete, so this is true precision")
record("class.solar.undisclosed", int((solar & ~lab_pv).sum()), "homes", "solar-shaped homes not on the 'all known PV' list")
flag("solar_battery", solar & (F.zero_summer_eve >= 0.25), "solar home whose zeros continue to 20-23h in summer (a battery covering the evening)", "low (tiny n)")

ev_l2 = (F.ev_l2_days >= 8) & (F.ev_l2_night_share >= 0.5) & ~inactive
flag("ev_l2", ev_l2, ">=8 weather-neutral days with a 2+ hour block >=5 kW above the day's 25th percentile, most starting 16:00-03:59", "high", lab_ev)
ev_l1 = (F.ev_l1_nights >= 30) & ~ev_l2 & ~inactive
flag("ev_l1", ev_l1, ">=30 weather-neutral nights with a 1.0-2.5 kW lift held 4+ hours, no Level 2 blocks", "low: dehumidifiers and well pumps look alike", lab_ev)
ev_any = ev_l2 | ev_l1
hits = int((ev_l2 & lab_ev).sum())
record("class.ev.recall_heldout", round(100 * hits / lab_ev.sum(), 1), "% of labeled EVs", "share of listed EV homes showing home Level 2 charging")
record("class.ev.implied_total", int(round(lab_ev.sum() / SAMPLE)), "homes", "labeled EVs present / 0.25 sample rate")
record("class.ev.l2_listed_owners_found", int(round(hits / SAMPLE)), "homes", "labeled L2 hits / 0.25")
record("class.ev.l2_unlisted", int(ev_l2.sum() - round(hits / SAMPLE)), "homes", "L2 flags minus implied listed owners: chargers the utility does not know about")
record("class.ev.l2_precision_floor_pct", round(100 * min(1, hits / SAMPLE / ev_l2.sum()), 1), "%", "lower bound: counts only listed owners as true")
record("class.ev.labeled_no_home_l2_pct", round(100 * (lab_ev & (F.ev_l2_days == 0)).sum() / lab_ev.sum(), 1), "% of labeled EVs", "zero Level 2 days at home")

heat_t = [(2000, 1.0), (3000, 1.5)]                       # plain run, skills run
cnts = [int(((F.heat_kwh_yr >= a) & (F.cold_kw_lift >= b) & ~inactive).sum()) for a, b in heat_t]
eheat = (F.heat_kwh_yr >= 3000) & (F.cold_kw_lift >= 1.5) & ~inactive
flag("electric_heat", eheat, ">=3,000 kWh/yr of weather-driven heating (daily-kWh vs HDD regression) and >=1.5 kW more at the 100 coldest hours than mild nights", "high that heat is electric", lab_hp)
record("class.electric_heat.sensitivity_low", min(cnts), "homes", "thresholds 3,000 kWh & 1.5 kW")
record("class.electric_heat.sensitivity_high", max(cnts), "homes", "thresholds 2,000 kWh & 1.0 kW")
ac_any = (F.b_cool >= 0.5) & (F.hot_kw_lift >= 0.5)
central = (F.b_cool >= 1.0) & (F.hot_kw_lift >= 1.5)
flag("ac", ac_any, "cooling slope >=0.5 kWh per cooling degree-day and >=0.5 kW lift at the 100 hottest hours", "high")
flag("ac_central", central, "cooling slope >=1 kWh/CDD and >=1.5 kW hot-hour lift", "medium")
hp_like = eheat & ac_any & (F.p_heat_pump >= np.quantile(F.p_heat_pump[eheat], 0.5))
flag("heat_pump", hp_like, "electric heat AND a cooling signature (heat pumps heat and cool) AND top half of the heat-pump model score", "low: listed heat pump homes and resistance homes share one kW-vs-temperature curve", lab_hp)
record("class.heat_pump.recall_heldout", round(100 * (hp_like & lab_hp).sum() / lab_hp.sum(), 1), "% of labeled HPs", "")
record("class.heat_pump.labeled_little_heat_pct", round(100 * (lab_hp & (F.heat_kwh_yr < 1500)).sum() / lab_hp.sum(), 1), "% of labeled HPs", "<1,500 kWh/yr weather-driven heat: supplemental mini-splits, not whole-home heat")
flag("resistance_heat", eheat & ~hp_like, "electric heat without the heat-pump evidence", "low (the remainder of electric heat)")
flag("pool", (F.pool_delta_kwh_day >= 8) & (F.pool_floor_delta_kw >= 0.6) & ~seasonal,
     "on days of equal mild temperature, summer uses >=8 kWh/day more than spring/fall and the 9-17h floor rises >=0.6 kW (a pump on a timer)", "medium")
flag("hot_tub", (F.spike_night >= 30) & (F.spike_winter_share >= 0.25) & ~ev_any,
     ">=30 isolated 1-hour spikes >=2.5 kWh between 0-4h, a quarter or more in winter (heater cycling)", "low, no labels")
flag("water_heater", (F.spike_morning >= 40) & ~ev_any,
     ">=40 isolated 1-hour morning spikes >=2.5 kWh (a 4.5 kW element after showers)", "low, no labels")
flag("other_seasonal", seasonal, "lowest month <15% of highest month (camps, snowbirds, part-year homes)", "high (shape)")
flag("other_inactive", inactive, "<300 kWh in the whole year", "high")
flag("other_flat_large", (F.load_factor >= 0.45) & (F.base_kw >= 1.5) & (F.annual_kwh >= 15000),
     "flat 24x7 load >=1.5 kW base, >=15,000 kWh/yr (business, grow room or crypto miner)", "medium")

cols = ["CUSTOMER_NUMBER"] + [c for c in F.columns if c.startswith(("is_", "p_"))] + ["lab_ev", "lab_hp", "lab_pv"]
F[cols].round(3).to_csv(ROOT + "outputs/customer_classes.csv", index=False)
F.to_parquet(P + "classified.parquet")
print(F[[c for c in F.columns if c.startswith("is_")]].sum().to_string())
