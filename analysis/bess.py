"""Part 3: who should get a battery or a flexibility program, what size, and what it is worth.

Unit (from the challenge): one IQ Battery 10C = 10.08 kWh, 3.84 kW. The program setup is 2 of them
(20.16 kWh, 7.68 kW). Round trip 89.4%, losses split evenly, so delivered energy per full
discharge E_d = kWh * sqrt(0.894). No export (meter shows export as 0, and the program is BTM).

Event days: each season's 10 highest system days; window = that day's 4 contiguous highest system hours.
  relief_h = min(L_h, P) scaled so sum over the window <= E_d           (a battery cannot discharge past the home)
  coincident relief = mean relief over all event hours, per season
Own peak shave: smallest T with, every day, sum(L-T)+ <= E_d and max(L)-T <= P (binary search).
Load shift: per day min(E_d, sum over 16-21h of min(L, P)), summed over the year.
Enablement (3 kVA rule read as new peak <= old peak + 3 kW at unity power factor):
  EV: unmanaged 7.2 kW Level 2 charging 18-20h daily.  HP: kW added = k * max(0, 60F - T),
  k fitted from electric-heat homes vs others. Battery dispatched to hold old peak + 3.
Every $ input is an ASSUMPTION recorded under assumption.* and must be replaced by tariff values.
"""
import os, sys, time
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from facts import record

t0 = time.time()
ROOT = os.path.expanduser("~/avangrid-hackathon/")
P = ROOT + "data/processed/"
F = pd.read_parquet(P + "segmented.parquet")
L = np.asarray(np.load(P + "load_present.npy", mmap_mode="r"))
w = pd.read_parquet(P + "weather.parquet"); temp = w["temp"].to_numpy()
sysl = np.load(P + "sysload.npy")
hours = pd.date_range("2025-09-01", periods=8760, freq="h")
n = len(F)
RTE = 0.894
SIZES = {"one_unit": (10.08, 3.84), "two_units": (20.16, 7.68)}

# assumptions, recorded so the deck can only use them with their label
CAP_VALUE = 100.0      # $/kW-yr avoided distribution + generation capacity
SPREAD_ON, SPREAD_OFF = 0.30, 0.18   # $/kWh on-peak 16-21h vs off-peak
UNIT_COST = (9000, 13000)            # $ installed per IQ 10C
record("assumption.capacity_value_usd_kw_yr", CAP_VALUE, "$/kW-yr", "ASSUMPTION: replace with NY avoided T&D + ICAP values")
record("assumption.tou_on_peak_usd_kwh", SPREAD_ON, "$/kWh", "ASSUMPTION: replace with NYSEG/RG&E TOU tariff")
record("assumption.tou_off_peak_usd_kwh", SPREAD_OFF, "$/kWh", "ASSUMPTION")
record("assumption.unit_cost_low_usd", UNIT_COST[0], "$ per IQ 10C installed", "ASSUMPTION")
record("assumption.unit_cost_high_usd", UNIT_COST[1], "$ per IQ 10C installed", "ASSUMPTION")

# ---------- event windows
day_sys = sysl.reshape(365, 24)
days = pd.date_range("2025-09-01", periods=365)
def windows(months):
    cand = np.where(np.isin(days.month, months))[0]
    top = cand[np.argsort(day_sys[cand].max(1))[-10:]]
    hrs = []
    for d in top:
        roll = np.convolve(day_sys[d], np.ones(4), "valid")
        s = int(np.argmax(roll)); hrs.append(d * 24 + np.arange(s, s + 4))
    return np.array(hrs)                                  # 10 x 4 hour indices
EV = {"summer": windows([6, 7, 8]), "winter": windows([12, 1, 2])}
for s, hw in EV.items():
    record(f"bess.event_window_{s}_hours", f"{hours[hw[0,0]].hour}:00-{hours[hw[0,-1]].hour + 1}:00 on the top day", "", "")

def coincident(kwh, kw):
    e = kwh * np.sqrt(RTE)
    out = {}
    for s, hw in EV.items():
        Lw = L[:, hw]                                     # n x 10 x 4
        r = np.minimum(Lw, kw)
        tot = r.sum(2, keepdims=True)
        r = r * np.minimum(1, e / np.maximum(tot, 1e-9))
        out[s] = r.mean((1, 2))
    return out

def shave_threshold(kwh, kw, rows):
    e = kwh * np.sqrt(RTE)
    D = L[rows].reshape(len(rows), 365, 24)
    lo, hi = np.zeros(len(rows)), D.max((1, 2))
    for _ in range(22):
        T = (lo + hi) / 2
        ex = np.maximum(D - T[:, None, None], 0)
        ok = (ex.sum(2) <= e).all(1) & (ex.max(2) <= kw).all(1)
        hi = np.where(ok, T, hi); lo = np.where(ok, lo, T)
    return hi

def daily_shift(kwh, kw, rows):
    e = kwh * np.sqrt(RTE)
    D = L[rows].reshape(len(rows), 365, 24)[:, :, 16:21]
    return np.minimum(np.minimum(D, kw).sum(2), e).sum(1)

rel = {k: coincident(*v) for k, v in SIZES.items()}
F["relief_summer_2u"], F["relief_winter_2u"] = rel["two_units"]["summer"], rel["two_units"]["winter"]
F["relief_summer_1u"], F["relief_winter_1u"] = rel["one_unit"]["summer"], rel["one_unit"]["winter"]

# ---------- candidates and ranking
ev_load = {s: L[:, hw].mean((1, 2)) for s, hw in EV.items()}
persist = {s: (L[:, hw].mean(2) >= 2.0).mean(1) for s, hw in EV.items()}   # share of event days the home is loaded
excluded = F.is_other_inactive | F.is_other_seasonal
# "persistent peak demand" (challenge assumption): loaded >= 3.5 kW on average in a season's event hours,
# and >= 2 kW on >= 9 of its 10 event days
cand = (((ev_load["summer"] >= 3.5) & (persist["summer"] >= 0.9)) |
        ((ev_load["winter"] >= 3.5) & (persist["winter"] >= 0.9))) & ~excluded
electrified = F.is_ev_l2 | F.is_electric_heat
tier = np.select([cand & electrified, cand & F.is_solar, cand], ["T1_electrified_peaker", "T2_solar_storage", "T3_grid_peaker"], "")
F["bess_tier"] = tier
best2 = np.maximum(F.relief_summer_2u, F.relief_winter_2u)
best1 = np.maximum(F.relief_summer_1u, F.relief_winter_1u)
F["bess_units"] = np.where(best1 >= 0.85 * best2, 1, 2) * (tier != "")
F["bess_score"] = best2 * np.maximum(persist["summer"], persist["winter"]) + 0.5 * electrified   # kW x persistence, tie-break to electrified
c = np.where(tier != "")[0]
record("bess.candidates.count", int(len(c)), "homes", "event-window load >=3.5 kW and loaded on >=9 of 10 event days, not seasonal/inactive")
# supply curve: MW as ranked homes are added (program setup at every home)
order = np.argsort(-F.bess_score.to_numpy())
for k in (500, 1000, 2000):
    top = order[:k]
    record(f"bess.supply_curve.top{k}_summer_mw", round(F.relief_summer_2u.to_numpy()[top].sum() / 1000, 2), "MW", f"best {k} homes by score")
    record(f"bess.supply_curve.top{k}_winter_mw", round(F.relief_winter_2u.to_numpy()[top].sum() / 1000, 2), "MW", "")
np.save(P + "bess_order.npy", order)
record("bess.candidates.share_pct", round(100 * len(c) / n, 1), "% of homes", "")
record("bess.ranking.method", "score = best-season coincident relief (kW, program setup) x event-day persistence + 0.5 if EV or electric heat", "", "")
record("bess.size.one_unit", int((F.bess_units == 1).sum()), "homes", "one IQ 10C already gives >=85% of the setup's coincident relief")
record("bess.size.two_units", int((F.bess_units == 2).sum()), "homes", "")
record("bess.size.median_second_unit_gain_kw", round(float(np.median((best2 - best1)[c])), 2), "kW", "")
for t in ["T1_electrified_peaker", "T2_solar_storage", "T3_grid_peaker"]:
    m = tier == t
    record(f"bess.tier.{t}.count", int(m.sum()), "homes", "")
    record(f"bess.tier.{t}.summer_mw", round(F.relief_summer_2u[m].sum() / 1000, 2), "MW", "")
    record(f"bess.tier.{t}.winter_mw", round(F.relief_winter_2u[m].sum() / 1000, 2), "MW", "")

# sized relief (each home gets its own size)
size_kw_s = np.where(F.bess_units == 2, F.relief_summer_2u, F.relief_summer_1u)
size_kw_w = np.where(F.bess_units == 2, F.relief_winter_2u, F.relief_winter_1u)
cap_s, cap_w = size_kw_s[c].sum() / 1000, size_kw_w[c].sum() / 1000
record("bess.capacity_relief_mw", round(cap_s, 2), "MW", "summer event hours, every candidate at its own size")
record("bess.capacity_relief_winter_mw", round(cap_w, 2), "MW", "winter event hours")
sys_s = sysl[EV["summer"]].mean() / 1000; sys_w = sysl[EV["winter"]].mean() / 1000
record("bess.capacity_relief_pct_of_event_load", round(100 * cap_s / sys_s, 1), "% of summer event-hour system load", "")
record("bess.relief_per_home_kw", round(float(np.median(np.maximum(size_kw_s, size_kw_w)[c])), 2), "kW", "median candidate, best season")

# own-peak reduction and load shift for candidates
T2 = shave_threshold(20.16, 7.68, c); T1u = shave_threshold(10.08, 3.84, c)
pk = L[c].max(1)
shave = np.where(F.bess_units.to_numpy()[c] == 2, pk - T2, pk - T1u)
record("bess.peak_reduction_kw", round(float(np.median(shave)), 2), "kW", "median candidate: annual peak cut while holding every day (perfect foresight)")
record("bess.peak_reduction_pct", round(float(np.median(shave / pk) * 100), 1), "% of own annual peak", "")
sh2, sh1 = daily_shift(20.16, 7.68, c), daily_shift(10.08, 3.84, c)
shift = np.where(F.bess_units.to_numpy()[c] == 2, sh2, sh1)
record("bess.load_shift_mwh_yr", round(float(shift.sum() / 1000), 0), "MWh/yr", "16-21h energy moved to off-peak, all candidates")
record("bess.load_shift_kwh_per_home", int(np.median(shift)), "kWh/yr", "median candidate")

# value and the net line
units = F.bess_units.to_numpy()[c]
cap_val = np.maximum(size_kw_s, size_kw_w)[c] * CAP_VALUE
bill = shift * (SPREAD_ON - SPREAD_OFF / RTE)
record("bess.bill_savings_usd_yr", int(round(bill.sum(), -3)), "$/yr", "TOU arbitrage on shifted kWh (ASSUMED rates)")
record("bess.bill_savings_per_home_usd_yr", int(np.median(bill)), "$/yr", "median candidate (ASSUMED rates)")
record("bess.capacity_value_usd_yr", int(round(cap_val.sum(), -3)), "$/yr", "relief x ASSUMED $/kW-yr")
capex = (units.sum() * UNIT_COST[0], units.sum() * UNIT_COST[1])
annual = bill.sum() + cap_val.sum()
record("bess.units_total", int(units.sum()), "IQ 10C units", "")
record("bess.capex_low_usd_m", round(capex[0] / 1e6, 1), "$M", "ASSUMED unit cost")
record("bess.capex_high_usd_m", round(capex[1] / 1e6, 1), "$M", "")
record("bess.simple_payback_low_yr", round(capex[0] / annual, 0), "years", "capex / (bill + capacity value); warranty is 15 years")
record("bess.simple_payback_high_yr", round(capex[1] / annual, 0), "years", "")

# solar charging
sol = F.is_solar.to_numpy()
mid = (hours.hour >= 10) & (hours.hour <= 14)
zero_days = ((L[sol][:, mid] == 0).reshape(sol.sum(), 365, 5).sum(2) >= 3).sum(1)
record("bess.solar_charge_share", round(float(np.median(zero_days)) / 365, 3), "share of days", "median solar home: days with >=3 midday export hours (surplus to charge from)")
record("bess.solar_charge_days", int(np.median(zero_days)), "days/yr", "")

# ---------- electrification enablement under the 3 kVA rule
hod = hours.hour.to_numpy()
ev_add = np.where((hod >= 18) & (hod <= 19), 7.2, 0.0)
eh = F.is_electric_heat.to_numpy()
cold = np.argsort(temp)[:200]
k_hp = float((np.median(L[eh][:, cold].mean(1)) - np.median(L[~eh][:, cold].mean(1))) / np.mean(np.maximum(0, 60 - temp[cold])))
hp_add = k_hp * np.maximum(0, 60 - temp)
record("bess.headroom_rule.hp_kw_per_degf", round(k_hp, 3), "kW per F below 60F", "electric-heat minus other homes at the 200 coldest hours")
record("bess.headroom_rule.hp_kw_at_0f", round(k_hp * 60, 2), "kW", "")

def passes(add, rows, kwh, kw):
    """True if new peak <= old peak + 3 kW, with the battery (kwh, kw) holding that cap; kwh=0 means no battery."""
    base = L[rows]
    cap = base.max(1) + 3.0
    new = (base + add[None, :]).reshape(len(rows), 365, 24)
    ex = np.maximum(new - cap[:, None, None], 0)
    if kwh == 0:
        return (ex.max((1, 2)) <= 1e-6)
    e = kwh * np.sqrt(RTE)
    return (ex.sum(2) <= e).all(1) & (ex.max(2) <= kw).all(1)

res = {}
for name, add, pool in [("ev", ev_add, ~F.is_ev_l2.to_numpy()), ("hp", hp_add, ~eh)]:
    rows = np.where(pool & ~excluded.to_numpy())[0]
    out = {}
    for chunk in np.array_split(rows, 8):
        for lab, (kwh, kw) in {"none": (0, 0), "one_unit": SIZES["one_unit"], "two_units": SIZES["two_units"]}.items():
            out.setdefault(lab, []).append(passes(add, chunk, kwh, kw))
    out = {k: np.concatenate(v) for k, v in out.items()}
    for lab, ok in out.items():
        record(f"bess.headroom_rule.{name}_pass_pct_{lab}", round(100 * ok.mean(), 1), "% of homes without it today", "")
    res[name] = out
    record(f"bess.electrification_enabled.{name}_homes", int((~out["none"] & out["two_units"]).sum()), "homes",
           "fail the 3 kVA rule alone, pass with the program battery")
record("bess.electrification_enabled.count", int((~res["ev"]["none"] & res["ev"]["two_units"]).sum()), "homes", "Level 2 EV enabled without a service study")

# flexibility without a battery: AC thermostat setback and pool timers at the summer event hours
hw = EV["summer"]
mild = np.where(np.isin(hours.month, [5, 9]) & (temp >= 60) & (temp <= 68))[0]
ac = F.is_ac.to_numpy()
ac_kw = np.maximum(L[ac][:, hw].mean((1, 2)) - L[ac][:, mild].reshape(ac.sum(), -1).mean(1), 0)
record("flex.ac_weather_load_mw", round(ac_kw.sum() / 1000, 1), "MW", "AC homes' event-hour load above mild-day load")
record("assumption.thermostat_shed_pct", 33, "%", "ASSUMPTION: share of cooling load a setback event sheds")
record("flex.reduction_kw", round(float(np.median(ac_kw) * 0.33), 2), "kW per AC home", "median home x 33% shed")
record("flex.thermostat_mw", round(ac_kw.sum() * 0.33 / 1000, 1), "MW", "")

F.to_parquet(P + "bess.parquet")
cols = ["CUSTOMER_NUMBER", "segment", "bess_tier", "bess_units", "bess_score", "relief_summer_2u", "relief_winter_2u"]
F.loc[F.bess_tier != "", cols].sort_values("bess_score", ascending=False).round(3).to_csv(ROOT + "outputs/bess_candidates.csv", index=False)
record("scale.bess_seconds", round(time.time() - t0, 1), "s", "")
print(pd.Series(tier[tier != ""]).value_counts().to_string())
