"""Aggregates behind the readout charts -> outputs/report_data.json (no customer-level rows)."""
import os, json
import numpy as np, pandas as pd
from scipy.stats import beta

ROOT = os.path.expanduser("~/avangrid-hackathon/")
P = ROOT + "data/processed/"
F = pd.read_parquet(P + "bess.parquet")
L = np.load(P + "load_present.npy", mmap_mode="r")
w = pd.read_parquet(P + "weather.parquet"); temp = w["temp"].to_numpy()
sysl = np.load(P + "sysload.npy")
n = len(F)
out = {}

# 1 daily system peak and mean temperature
d = sysl.reshape(365, 24)
out["daily"] = {"date": [str(x.date()) for x in pd.date_range("2025-09-01", periods=365)],
                "peak_mw": np.round(d.max(1) / 1000, 2).tolist(),
                "temp_f": np.round(temp.reshape(365, 24).mean(1), 1).tolist()}

# 2 validation: recall on labeled homes with Jeffreys 95% CI, vs flag rate among unlabeled homes
val = []
for name, flag, lab in [("Solar PV", "is_solar", "lab_pv"), ("EV Level 2", "is_ev_l2", "lab_ev"),
                        ("EV Level 1", "is_ev_l1", "lab_ev"), ("Electric heat", "is_electric_heat", "lab_hp"),
                        ("Heat pump", "is_heat_pump", "lab_hp")]:
    y = F[lab] == 1; f = F[flag]
    k, m = int((f & y).sum()), int(y.sum())
    lo, hi = beta.ppf([0.025, 0.975], k + 0.5, m - k + 0.5)
    val.append({"cls": name, "recall": round(100 * k / m, 1), "lo": round(100 * lo, 1), "hi": round(100 * hi, 1),
                "base": round(100 * f[~y].mean(), 1), "k": k, "n": m})
out["validation"] = val

# 3 neutral-day hourly profiles: why the EV list and the meters disagree
tday = temp.reshape(365, 24).mean(1)
neutral = np.where((tday >= 55) & (tday <= 70))[0]
def prof(mask):
    idx = np.where(mask)[0]
    A = np.asarray(L[idx]).reshape(len(idx), 365, 24)[:, neutral, :]
    return np.round(A.mean((0, 1)), 3).tolist(), int(len(idx))
groups = {"Listed EV, charging seen": F.is_ev_l2 & (F.lab_ev == 1),
          "Listed EV, no charging seen": ~F.is_ev_l2 & (F.lab_ev == 1),
          "Not listed, charging seen": F.is_ev_l2 & (F.lab_ev == 0),
          "All other homes": ~F.is_ev_l2 & (F.lab_ev == 0)}
out["ev_profiles"] = {g: dict(zip(["kw", "n"], prof(m.to_numpy()))) for g, m in groups.items()}

# 4 temperature response: median daily kWh by 5F bin
daily = np.load(P + "daily.npy")
bins = np.arange(-5, 95, 5)
tb = np.digitize(tday, bins)
resp = {}
for g, m in {"Electric heat (flagged)": F.is_electric_heat, "Listed heat pump": F.lab_hp == 1,
             "Everyone else": ~F.is_electric_heat & (F.lab_hp == 0)}.items():
    D = daily[m.to_numpy()]
    resp[g] = [None if (tb == i).sum() == 0 else round(float(np.median(D[:, tb == i].mean(1))), 1) for i in range(1, len(bins))]
out["temp_response"] = {"bin_f": (bins[:-1] + 2.5).tolist(), "series": resp}

# 5 supply curve: MW as ranked candidates are added
order = np.load(P + "bess_order.npy")
cand = F.bess_tier.to_numpy()[order] != ""
o = order[cand]
cs = np.cumsum(F.relief_summer_2u.to_numpy()[o]) / 1000; cw = np.cumsum(F.relief_winter_2u.to_numpy()[o]) / 1000
pts = np.unique(np.linspace(0, len(o) - 1, 120).astype(int))
out["supply"] = {"homes": (pts + 1).tolist(), "summer_mw": np.round(cs[pts], 2).tolist(), "winter_mw": np.round(cw[pts], 2).tolist()}

json.dump(out, open(ROOT + "outputs/report_data.json", "w"))
print("ok", {k: len(v) for k, v in out.items()})
