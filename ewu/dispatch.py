"""Dispatch: home batteries on a flagged transformer, hour by hour, carrying state of charge night to night.

What: battery_spec() reads one host's energy, power, efficiency and floor from config; own_loading() is each
      home's own kW (metered, plus its new heat pump, plus its new EV under a charging mode); pick_hosts()
      takes the homes drawing most in a transformer's worst hour; run_batteries() dispatches every host's
      battery through a run of hours and returns load after batteries, state of charge, charge and discharge.
Why:  judges asked whether a battery survives a long cold night (plan objection 1). A single peak hour hides
      the question; carrying state of charge hour after hour shows whether the energy above the limit fits,
      and whether the battery refills before the next night.
How:  each hour, hosts discharge in turn to bring the transformer down to `overload_limit` x rating, each
      limited by its power, its stored energy above the reserve floor and, with no export, its own home's load.
      Then hosts charge in turn, only into room left under that same limit, at no more than their power.
      Charging stores kW x round-trip efficiency, so losses are booked once, on the way in. With no hosts the
      load passes through untouched, which is how this reproduces the M1 stress numbers exactly.
"""
import numpy as np
from ewu import config_value
from ewu.adoption import HOURS, heat_pump_kw
from ewu.shift import ev_rows_by_mode

OVER_TOLERANCE_KW = 1e-9   # float noise only: an hour shaved exactly to the limit counts as not over


def battery_spec(units, config):
    """One host with `units` IQ 10C units: kWh, continuous kW, round-trip efficiency, floor kWh, start kWh."""
    energy = units * config_value("battery.energy_kwh_per_unit", config)
    two = config_value("battery.power_kw_two_units", config)
    return {"energy_kwh": energy, "power_kw": units * two / 2,
            "efficiency": config_value("battery.round_trip_efficiency", config),
            "floor_kwh": config_value("battery.reserve_share", config) * energy,
            "start_kwh": config_value("battery.start_soc_share", config) * energy,
            "export": bool(config_value("battery.export_to_neighbors", config))}


def own_loading(inputs, parts, rows, owner, mode, config, hours=(0, HOURS)):
    """Each listed home's own kW in hours [first, last): metered + its new heat pump + its new EV in this mode."""
    first, last = hours
    rows = np.asarray(rows)
    width = last - first
    out = np.asarray(inputs["load"][rows], dtype=np.float64)[:, first:last]
    hp_kw = heat_pump_kw(inputs["temp"], config).astype(np.float64)[first:last]
    out += np.isin(rows, parts["hp_homes"])[:, None] * hp_kw[None, :]
    home, hour, kw = ev_rows_by_mode(mode, parts, owner, config)
    position = np.full(len(owner), -1, dtype=np.int64)
    position[rows] = np.arange(len(rows))
    keep = (position[home] >= 0) & (hour >= first) & (hour < last)
    cell = position[home[keep]] * width + (hour[keep] - first)
    out += np.bincount(cell, weights=kw[keep], minlength=len(rows) * width).reshape(len(rows), width)
    return out


def pick_hosts(home_kw, homes_by_transformer, worst_hour, count):
    """Per transformer, the `count` homes with the highest own kW in its worst hour (row numbers, best first)."""
    at_worst = np.take_along_axis(home_kw, worst_hour[:, None, None], axis=2)[:, :, 0]
    order = np.argsort(-at_worst, axis=1, kind="stable")[:, :count]
    return np.take_along_axis(homes_by_transformer, order, axis=1)


def run_batteries(total_kw, ceiling_kw, host_kw, spec, keep=(0, 0)):
    """Dispatch H host batteries on T transformers through N hours.

    total_kw (T, N) transformer load before batteries; ceiling_kw (T,) the overload line; host_kw (H, T, N)
    each host's own load, H may be 0. Returns year sums per transformer, per-host extremes, and the hours in
    `keep` stored in full: net load (T, w), state of charge, charge and discharge (H, T, w).
    """
    total_kw = np.asarray(total_kw, dtype=np.float64)
    hosts, (count, hours) = len(host_kw), total_kw.shape
    soc = np.full((hosts, count), spec["start_kwh"])
    width = keep[1] - keep[0]
    kept = {"net_kw": np.zeros((count, width)), "soc_kwh": np.zeros((hosts, count, width)),
            "charge_kw": np.zeros((hosts, count, width)), "discharge_kw": np.zeros((hosts, count, width))}
    sums = {"hours_over": np.zeros(count, dtype=np.int64), "kwh_over": np.zeros(count),
            "charged_kwh": np.zeros((hosts, count)), "discharged_kwh": np.zeros((hosts, count)),
            "soc_min_kwh": soc.copy(), "soc_max_kwh": soc.copy(),
            "charge_max_kw": np.zeros((hosts, count)), "discharge_max_kw": np.zeros((hosts, count))}
    start_soc = soc.copy()
    for h in range(hours):
        load = total_kw[:, h].copy()
        out = np.zeros((hosts, count))
        inn = np.zeros((hosts, count))
        for i in range(hosts):
            limit = np.minimum(spec["power_kw"], np.maximum(soc[i] - spec["floor_kwh"], 0.0))
            if not spec["export"]:
                limit = np.minimum(limit, np.maximum(host_kw[i][:, h], 0.0))
            out[i] = np.minimum(np.maximum(load - ceiling_kw, 0.0), limit)
            soc[i] -= out[i]
            load -= out[i]
        for i in range(hosts):
            room = np.maximum(ceiling_kw - load, 0.0)
            inn[i] = np.minimum(np.minimum(room, spec["power_kw"]), (spec["energy_kwh"] - soc[i]) / spec["efficiency"])
            inn[i] = np.maximum(inn[i], 0.0)
            soc[i] += inn[i] * spec["efficiency"]
            load += inn[i]
        above = np.maximum(load - ceiling_kw, 0.0)
        sums["hours_over"] += above > OVER_TOLERANCE_KW
        sums["kwh_over"] += above
        sums["charged_kwh"] += inn
        sums["discharged_kwh"] += out
        np.minimum(sums["soc_min_kwh"], soc, out=sums["soc_min_kwh"])
        np.maximum(sums["soc_max_kwh"], soc, out=sums["soc_max_kwh"])
        np.maximum(sums["charge_max_kw"], inn, out=sums["charge_max_kw"])
        np.maximum(sums["discharge_max_kw"], out, out=sums["discharge_max_kw"])
        if keep[0] <= h < keep[1]:
            j = h - keep[0]
            kept["net_kw"][:, j] = load
            kept["soc_kwh"][:, :, j], kept["charge_kw"][:, :, j], kept["discharge_kw"][:, :, j] = soc, inn, out
    return {**sums, **kept, "start_soc_kwh": start_soc, "end_soc_kwh": soc}
