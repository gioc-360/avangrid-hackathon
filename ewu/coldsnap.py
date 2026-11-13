"""Cold snap: the Feb 7-8 duration test for home batteries on every transformer the cold snap overloads.

What: window_hours() turns a start date into the cold snap's hour range; flag_and_dispatch() flags transformers over
      the limit inside the window, puts 1 or 2 battery hosts on each and dispatches them all year;
      run_coldsnap() does that for every seed, scenario and EV mode (unmanaged, staggered); summarize_coldsnap()
      pools seeds; record_coldsnap() writes the aggregates to facts and one example transformer to the private
      facts file. ewu/cli.py prints the aggregates.
Why:  plan objection 1: the battery was never tested on a long cold night. Hours over, kWh over, the longest
      run of hours over and the state of charge by hour across both nights answer it with numbers.
How:  2030 loading is the M1 loading (random grouping, base sizing margin) with EV charging unmanaged or
      staggered; a transformer is flagged if any window hour is above `overload_limit` x rating. Hosts are
      the homes drawing most in its worst window hour, each with `units_per_host_max` units. The battery runs
      from the first hour of the year so the state of charge entering Feb 7 is earned, not assumed. A
      transformer is cleared when no window hour is left above the limit.
"""
import numpy as np
import pandas as pd
from ewu import PROCESSED, config_value
from ewu import adoption, dispatch, feeders as feeder_groups, shift, stress

COLD_MODES = ("unmanaged", "staggered")
GROUPING = "random"


def window_hours(start_date, config):
    """Hour range [first, last) of the cold snap starting at `start_date`, as long as the config's Feb 7-8."""
    index = pd.read_parquet(PROCESSED / "weather.parquet").index
    days = (pd.Timestamp(config_value("demo.cold_snap_end", config)) -
            pd.Timestamp(config_value("demo.cold_snap_start", config))).days + 1
    first = index.get_loc(pd.Timestamp(start_date))
    return first, first + days * 24, index[first:first + days * 24]


def flag_and_dispatch(inputs, groups, base, parts, mode, window, config):
    """Flag, pick hosts and dispatch batteries for one seed, scenario and EV mode. Per-transformer arrays."""
    owner = stress.transformer_of_each_home(groups, len(inputs["homes"]))
    ceiling = config_value("transformer.overload_limit", config) * feeder_groups.rate(
        base.max(1), config_value("transformer.base_margin", config))
    total = base + shift.ev_loading_by_mode(mode, parts, owner, groups.count, config) + parts["hp"]
    first, last = window[:2]
    above = np.maximum(total[:, first:last] - ceiling[:, None], 0.0)
    flagged = np.flatnonzero((above > dispatch.OVER_TOLERANCE_KW).any(1))
    homes = groups.homes.reshape(groups.count, -1)[flagged]
    home_kw = dispatch.own_loading(inputs, parts, homes.ravel(), owner, mode, config, (first, last))
    host_counts = config_value("battery.coldsnap_hosts_per_transformer", config)
    hosts = dispatch.pick_hosts(home_kw.reshape(len(flagged), homes.shape[1], -1), homes,
                                above[flagged].argmax(1), max(host_counts))
    host_kw = dispatch.own_loading(inputs, parts, hosts.T.ravel(), owner, mode, config)
    host_kw = host_kw.reshape(hosts.shape[1], len(flagged), -1)
    spec = dispatch.battery_spec(config_value("battery.units_per_host_max", config), config)
    over = above[flagged] > dispatch.OVER_TOLERANCE_KW
    run = {"transformers": groups.count, "flagged": len(flagged), "hours_over": over.sum(1),
           "kwh_over": above[flagged].sum(1), "longest_run": adoption.run_lengths(over).max(1, initial=0),
           "over_by_hour": over, "load_kw": total[flagged, first:last], "ceiling_kw": ceiling[flagged],
           "spec": spec, "hosts": {}}
    for count in host_counts:
        result = dispatch.run_batteries(total[flagged], ceiling[flagged], host_kw[:count], spec, (first, last))
        left = np.maximum(result["net_kw"] - ceiling[flagged, None], 0.0)
        pooled = result["soc_kwh"].sum(0)
        run["hosts"][count] = {"result": result, "left_kwh": left.sum(1),
                               "left_by_hour": left > dispatch.OVER_TOLERANCE_KW,
                               "soc_share": pooled / (count * spec["energy_kwh"]),
                               "ran_empty": (pooled <= count * spec["floor_kwh"] + 1e-6).any(1)}
    return run


def run_coldsnap(inputs, config, start_date, seeds, scenarios=stress.SCENARIOS):
    """Every seed x scenario x EV mode through the cold snap window: {(scenario, mode, seed): run}."""
    k = config_value("transformer.homes_per_transformer", config)
    count = config_value("transformer.count", config)
    window = window_hours(start_date, config)
    sessions = adoption.measure_ev_sessions(inputs["load"], inputs["homes"]["is_ev_l2"], inputs["temp"], config)
    runs = {}
    for seed in seeds:
        groups = feeder_groups.build_transformers(inputs["homes"]["segment"].to_numpy(), k, count, GROUPING, seed)
        base = stress.base_loading(inputs["load"], groups)
        for scenario in scenarios:
            parts = stress.loading_parts(inputs, groups, scenario, seed, config, sessions, base)
            for mode in COLD_MODES:
                runs[(scenario, mode, seed)] = flag_and_dispatch(inputs, groups, base, parts, mode, window, config)
    return runs, window


def percent_of(part, whole):
    return round(100.0 * float(part) / float(whole), 2) if whole else 0.0


def summarize_coldsnap(runs):
    """Seed-pooled aggregates per scenario and EV mode, with one block per host count."""
    keys = sorted({(s, m) for s, m, _ in runs})
    out = {}
    for scenario, mode in keys:
        group = [r for (s, m, _), r in sorted(runs.items()) if (s, m) == (scenario, mode)]
        cat = lambda name: np.concatenate([r[name] for r in group])
        kwh, hours, longest = cat("kwh_over"), cat("hours_over"), cat("longest_run")
        flagged = len(kwh)
        median = lambda a: round(float(np.median(a)), 2) if len(a) else 0.0
        cell = {"flagged_pct": round(float(np.mean([100.0 * r["flagged"] / r["transformers"] for r in group])), 2),
                "flagged_per_seed": round(flagged / len(group), 1), "seeds": len(group),
                "hours_over_median": median(hours), "hours_over_max": int(hours.max(initial=0)),
                "kwh_over_median": median(kwh), "kwh_over_p90": round(float(np.percentile(kwh, 90)), 2) if flagged else 0.0,
                "longest_run_median": median(longest), "longest_run_max": int(longest.max(initial=0)),
                "over_pct_by_hour": [percent_of(v, flagged) for v in np.concatenate([r["over_by_hour"] for r in group]).sum(0)],
                "hosts": {}}
        for count in group[0]["hosts"]:
            blocks = [r["hosts"][count] for r in group]
            spec = group[0]["spec"]
            usable = count * (spec["energy_kwh"] - spec["floor_kwh"])
            left = np.concatenate([b["left_kwh"] for b in blocks])
            soc = np.concatenate([b["soc_share"] for b in blocks])
            cell["hosts"][count] = {
                "cleared_pct": percent_of((left <= dispatch.OVER_TOLERANCE_KW).sum(), flagged),
                "kwh_over_left_pct": percent_of(left.sum(), kwh.sum()),
                "energy_fits_pct": percent_of((kwh <= usable).sum(), flagged),
                "ran_empty_pct": percent_of(np.concatenate([b["ran_empty"] for b in blocks]).sum(), flagged),
                "usable_kwh": round(usable, 2),
                "over_pct_by_hour": [percent_of(v, flagged) for v in np.concatenate([b["left_by_hour"] for b in blocks]).sum(0)],
                "soc_median_pct_by_hour": [round(100 * float(v), 1) for v in np.median(soc, axis=0)] if flagged else [],
                "soc_p10_pct_by_hour": [round(100 * float(v), 1) for v in np.percentile(soc, 10, axis=0)] if flagged else []}
        out[(scenario, mode)] = cell
    return out


def record_coldsnap(summary, runs, window, config, seconds):
    """Aggregates to facts/facts.json; one example transformer, hour by hour, to the private facts file."""
    from analysis.facts import record
    margin = stress.margin_label(config_value("transformer.base_margin", config))
    seeds = next(iter(summary.values()))["seeds"]
    how = f"pooled {seeds} seeds, {GROUPING} grouping, Feb 7-8 window, battery dispatched all year"
    for (scenario, mode), cell in summary.items():
        key = f"ewu.coldsnap.{scenario}.{mode}.{margin}"
        for name in ("flagged_pct", "flagged_per_seed", "hours_over_median", "hours_over_max", "kwh_over_median",
                     "kwh_over_p90", "longest_run_median", "longest_run_max", "over_pct_by_hour"):
            unit = "% of transformers" if name == "flagged_pct" else "kWh" if "kwh" in name else \
                "% of flagged transformers" if "pct" in name else "transformers" if "per_seed" in name else "hours"
            record(f"{key}.{name}", cell[name], unit, how + "; no battery")
        for count, block in cell["hosts"].items():
            for name, value in block.items():
                unit = "kWh" if name == "usable_kwh" else "% of kWh over" if name == "kwh_over_left_pct" else \
                    "% state of charge" if name.startswith("soc") else "% of flagged transformers"
                record(f"{key}.hosts_{count}.{name}", value, unit, how + f"; {count} host(s) per transformer")
    record("ewu.coldsnap.window_hours", int(window[1] - window[0]), "hours", "Feb 7 00:00 to Feb 8 23:00")
    record("ewu.coldsnap.window_min_temp_f", float(window_temps(window).min()), "F", "hourly weather in the window")
    record("ewu.coldsnap.seconds", round(seconds, 1), "s", "whole cold snap run")
    record_example(runs, window, config, record)


def window_temps(window):
    return pd.read_parquet(PROCESSED / "weather.parquet")["temp"].to_numpy()[window[0]:window[1]]


def record_example(runs, window, config, record):
    """The demo transformer: the flagged one with the median kWh over, seed 0, demo scenario, staggered."""
    run = runs[(config_value("demo.scenario", config), "staggered", 0)]
    if not run["flagged"]:
        return
    t = int(np.argsort(run["kwh_over"])[run["flagged"] // 2])
    two = lambda a: [round(float(v), 2) for v in a]
    record("ewu.coldsnap.example.hour", [str(ts) for ts in window[2]], "timestamp", "window hours", private=True)
    record("ewu.coldsnap.example.load_kw", two(run["load_kw"][t]), "kW", "no battery", private=True)
    record("ewu.coldsnap.example.limit_kw", round(float(run["ceiling_kw"][t]), 2), "kW", "limit x rating", private=True)
    record("ewu.coldsnap.example.kwh_over", round(float(run["kwh_over"][t]), 2), "kWh", "window", private=True)
    for count, block in run["hosts"].items():
        result = block["result"]
        record(f"ewu.coldsnap.example.hosts_{count}.net_kw", two(result["net_kw"][t]), "kW", "after batteries",
               private=True)
        record(f"ewu.coldsnap.example.hosts_{count}.soc_kwh", two(result["soc_kwh"][:, t].sum(0)), "kWh",
               "pooled hosts", private=True)
        record(f"ewu.coldsnap.example.hosts_{count}.capacity_kwh", count * run["spec"]["energy_kwh"], "kWh", "",
               private=True)
