"""Peak cut: MW a fleet of priority home batteries takes off the system's top hours, with and without export.

What: priority_homes() picks the homes the earlier 7.0 MW rule picks (mean load and behind-the-meter cut in
      the system's top hours above two thresholds); behind_meter_cut() is what their batteries cut when each
      may cover only its own home; export_cut() is what the same fleet cuts when it may export, dispatched as
      one staggered fleet that flattens the system load day by day; run_peak_cut() returns both.
Why:  the final deck reports the staggered fleet with export (export confirmed in office hours, per the
      teammate) as the default peak cut and behind the meter as the conservative case. Both must come from
      this code on our data, not be typed in.
How:  top hours = the year's `peak_hours` highest metered system hours. Each priority home holds units_per_host
      units of unit_kw and unit_kwh. Behind the meter, each home cuts min(own load, power) in each top hour,
      scaled down on any day where the cuts add to more than its usable energy (ewu/fitscore.fit_score).
      With export, the fleet's power and energy pool: each day holding a top hour is shaved to the flat line
      that uses at most the fleet's energy, never more than its power in any hour (bisection on the line).
      Both report the mean MW cut over the top hours, plus the cut in the single highest hour.
"""
import numpy as np
import pandas as pd
from ewu import PROCESSED
from ewu import fitscore
from ewu.deck import deck_value


def fleet_spec(config):
    units = deck_value("units_per_host", config)
    return {"power_kw": units * deck_value("unit_kw", config), "energy_kwh": units * deck_value("unit_kwh", config),
            "floor_kwh": 0.0}


def top_hours(sysload, config):
    return np.sort(np.argsort(-np.asarray(sysload), kind="stable")[:deck_value("peak_hours", config)])


def priority_homes(load, hours, day, spec, config):
    """(rows, per-home cut kW): homes whose mean top-hour load and behind-the-meter cut clear the thresholds."""
    kw = np.asarray(load[:, hours], dtype=np.float64)
    cut = fitscore.fit_score(kw, day, spec)
    keep = (kw.mean(1) >= deck_value("priority_load_kw", config)) & (cut >= deck_value("priority_cut_kw", config))
    return np.flatnonzero(keep), cut[keep]


def flat_line_cut(day_kw, power_kw, energy_kwh):
    """Per hour of one day: the cut that shaves the day to a flat line using at most energy_kwh and power_kw."""
    low, high = float(day_kw.max()) - power_kw, float(day_kw.max())
    for _ in range(60):
        line = (low + high) / 2
        used = np.minimum(np.maximum(day_kw - line, 0.0), power_kw).sum()
        low, high = (line, high) if used > energy_kwh else (low, line)
    return np.minimum(np.maximum(day_kw - high, 0.0), power_kw)


def export_cut(sysload, hours, homes, spec):
    """kW cut in each top hour when the whole fleet pools power and energy and may export."""
    days = np.unique(hours // 24)
    cut = np.zeros(len(sysload))
    for d in days:
        span = slice(d * 24, d * 24 + 24)
        cut[span] = flat_line_cut(np.asarray(sysload[span], dtype=np.float64), homes * spec["power_kw"],
                                  homes * spec["energy_kwh"])
    return cut[hours]


def run_peak_cut(inputs, config):
    """Behind-the-meter and export fleet cuts over the top hours, MW, with the hosts and hours behind them."""
    sysload = np.load(PROCESSED / "sysload.npy")
    index = pd.read_parquet(PROCESSED / "weather.parquet").index
    hours = top_hours(sysload, config)
    day = np.asarray(index[hours].normalize().asi8)
    spec = fleet_spec(config)
    rows, home_cut = priority_homes(inputs["load"], hours, day, spec, config)
    behind = fitscore.fit_score(np.asarray(inputs["load"][rows][:, hours], dtype=np.float64)[None], day, spec)
    behind_by_hour = np.minimum(np.maximum(np.asarray(inputs["load"][rows][:, hours], dtype=np.float64), 0.0),
                                spec["power_kw"]).sum(0)
    exported = export_cut(sysload, hours, len(rows), spec)
    peak = int(np.argmax(sysload[hours]))
    return {"hosts": len(rows), "units": len(rows) * deck_value("units_per_host", config), "hours": len(hours),
            "days": len(np.unique(day)), "behind_meter_mw": round(float(behind.sum()) / 1000, 2),
            "export_mw": round(float(exported.mean()) / 1000, 2),
            "export_peak_hour_mw": round(float(exported[peak]) / 1000, 2),
            "behind_meter_power_cap_mw": round(float(behind_by_hour.mean()) / 1000, 2),
            "top_hours_load_mw": round(float(sysload[hours].mean()) / 1000, 2)}
