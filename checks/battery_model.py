"""Battery model: the second implementation of staggered charging, the fit score and battery dispatch.

What: setting() reads config/ewu.yaml; battery() gives one host's kW, kWh and floor; staggered_rows() places
      new EV charging in the stagger window; fit_scores() is the kW a battery cuts over the system top hours;
      dispatch() runs host batteries on many transformers through the year hour by hour.
Why:  checks/recompute_battery.py must not reuse ewu/shift.py, ewu/fitscore.py or ewu/dispatch.py, or a bug
      there would pass its own check. These rules are written again here from the plan and the config.
How:  plain numpy. Slots come from a pandas rank per transformer; a session's kW is min(power, kWh left).
      Hosts discharge in order (cumulative sums split the excess), then charge in order into the room left
      under the limit, storing kW x round-trip efficiency; with no export a host cuts at most its own load.
"""
import functools
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((ROOT / "config" / "ewu.yaml").read_text())
HOURS, TOL = 8760, 1e-9


def setting(dotted):
    """The `value` of one config input, named like 'battery.energy_kwh_per_unit'."""
    return functools.reduce(lambda node, part: node[part], dotted.split("."), CFG)["value"]


def battery(units):
    """(power kW, energy kWh, floor kWh) of one host with `units` IQ 10C units."""
    energy = units * setting("battery.energy_kwh_per_unit")
    return units * setting("battery.power_kw_two_units") / 2, energy, setting("battery.reserve_share") * energy


def staggered_rows(sessions, ev_homes, owner):
    """(home, hour, kW) of staggered charging: own slot in the window by rank on the transformer, half power, same kWh."""
    start, charger = setting("shift.stagger_start_hour"), setting("scenarios.loads.ev_l2_kw")
    window, power = (setting("shift.stagger_end_hour") - start) % 24, setting("shift.stagger_power_share") * charger
    table = pd.DataFrame({"home": np.asarray(ev_homes), "owner": owner[np.asarray(ev_homes)]}).sort_values(["owner", "home"])
    slot = pd.Series((table.groupby("owner").cumcount() % window).to_numpy(), index=table["home"].to_numpy())
    begin = np.asarray(sessions["start"])
    energy = (np.minimum(begin + np.asarray(sessions["hours"]), HOURS) - begin) * charger
    steps = np.ceil(energy / power - 1e-9).astype(np.int64)
    idx = np.repeat(np.arange(len(begin)), steps)
    step = np.arange(len(idx)) - np.repeat(np.cumsum(steps) - steps, steps)
    first = (begin // 24) * 24 + start + slot.reindex(sessions["home"]).to_numpy()
    kw = np.minimum(power, energy[idx] - step * power)
    return np.asarray(sessions["home"])[idx], (first[idx] + step) % HOURS, kw


def fit_scores(kw_top, top_days, units):
    """Mean kW a battery cuts over the top hours: min(load, power), each day scaled to fit the usable energy."""
    power, energy, floor = battery(units)
    cut = np.clip(kw_top, 0.0, power)
    starts = np.flatnonzero(np.r_[True, top_days[1:] != top_days[:-1]])
    scale = np.minimum(1.0, (energy - floor) / np.maximum(np.add.reduceat(cut, starts, axis=-1), 1e-12))
    return (cut * np.repeat(scale, np.diff(np.r_[starts, len(top_days)]), axis=-1)).mean(-1)


def dispatch(total, ceiling, host_kw, power, energy, floor, window):
    """Run all rows through the year. total (N, H), host_kw (N, S, H), power/energy/floor (N, S).
    Returns hours over all year, kWh over left in the window and whether pooled charge hit the floor there."""
    eff = setting("battery.round_trip_efficiency")
    soc = setting("battery.start_soc_share") * energy
    load_by_hour, host_by_hour = np.ascontiguousarray(total.T), np.ascontiguousarray(host_kw.transpose(2, 0, 1))
    hours_over, left, empty = np.zeros(len(total), np.int64), np.zeros(len(total)), np.zeros(len(total), bool)
    for h in range(total.shape[1]):
        load = load_by_hour[h]
        can = np.minimum(power, np.maximum(soc - floor, 0.0))
        can = can if setting("battery.export_to_neighbors") else np.minimum(can, np.maximum(host_by_hour[h], 0.0))
        out = np.clip(np.maximum(load - ceiling, 0.0)[:, None] - (np.cumsum(can, 1) - can), 0.0, can)
        soc, load = soc - out, load - out.sum(1)
        head = np.maximum(np.minimum(power, (energy - soc) / eff), 0.0)
        inn = np.clip(np.maximum(ceiling - load, 0.0)[:, None] - (np.cumsum(head, 1) - head), 0.0, head)
        soc, load = soc + inn * eff, load + inn.sum(1)
        over = load - ceiling
        hours_over += over > TOL
        if window[0] <= h < window[1]:
            left += np.maximum(over, 0.0)
            empty |= soc.sum(1) <= floor.sum(1) + 1e-6
    return hours_over, left, empty
