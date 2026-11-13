"""Top hours: how many kW the fit-score battery hosts cut in the system's top 20 and top 50 hours of the year.

What: hour_sets() ranks the year's metered system hours and builds the sets Scott named: the annual top 20
      and top 50, the winter top hours from the M4 season rule, and the single peak hour of each named date
      (July 2, February 7). run_top_hours() takes the transformers M4 flags (still over the limit with
      staggered EV charging), places 1 host per transformer with 1 or 2 units, by fit score or at random,
      and measures the fleet's kW cut in every set. record_top_hours() pools seeds into facts.
Why:  Scott's stated objective is "how many of those top hours can your solution reduce". M4 showed fit-score
      hosts clear more transformers per battery; this answers his question in MW, checked against his two
      dates, and says plainly when a date is not in the annual top set.
How:  the cut uses ewu/fitscore.fit_score(): each host battery, dispatched for the system, cuts the smaller of
      its home's 2030 kW and its power, scaled down on any day where the cuts add to more than its usable
      energy, so a flat, long-loaded home scores lower than a peaky one. Hosts are the same ones M4 picks
      (fit score on the season top hours); random hosts on the same transformers are the control. The share
      is the fleet cut over the 2030 load (metered + staggered EV + heat pump) of all homes on the synthetic
      transformers in the same hours.
"""
import sys
from pathlib import Path
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import time
import numpy as np
import pandas as pd
from ewu import PROCESSED, config_value, read_config, read_inputs
from ewu import adoption, dispatch, feeders as feeder_groups, fitscore, shift, stress

POLICIES = ("fit_score", "random")
HOSTS = 1
DATES = ("summer_peak_date", "winter_peak_date")


def hour_sets(sysload, index, config):
    """{set name: sorted hour numbers}, plus the year's hour ranking (rank 1 = highest metered system hour)."""
    sysload = np.asarray(sysload)
    order = np.argsort(-sysload, kind="stable")
    sets = {f"top_{n}": np.sort(order[:n]) for n in config_value("battery.system_top_hour_counts", config)}
    season = fitscore.system_top_hours(sysload, index, config)
    sets["winter_top"] = season[np.isin(index[season].month, config_value("battery.winter_months", config))]
    days = index.normalize()
    for name in DATES:
        day = np.flatnonzero(days == pd.Timestamp(config_value(f"demo.{name}", config)))
        sets[name] = day[[int(np.argmax(sysload[day]))]]
    rank = np.empty(len(order), dtype=np.int64)
    rank[order] = np.arange(1, len(order) + 1)
    return sets, rank


def fleet_cut_kw(home_kw, hosts, hours, index, spec):
    """Mean kW the whole host fleet cuts over `hours` when every battery is dispatched for the system."""
    t = np.arange(len(hosts))[:, None]
    host_kw = home_kw[t, hosts][:, :, hours].astype(np.float64)
    return float(fitscore.fit_score(host_kw, np.asarray(index[hours].normalize().asi8), spec).sum())


def run_top_hours(inputs, config, seeds, scenarios=stress.SCENARIOS):
    """Per scenario and seed: batteries placed, fleet kW cut per set and policy, and the homes' 2030 kW per set."""
    index = pd.read_parquet(PROCESSED / "weather.parquet").index
    sysload = np.load(PROCESSED / "sysload.npy")
    sets, rank = hour_sets(sysload, index, config)
    season = fitscore.system_top_hours(sysload, index, config)
    season_day = np.asarray(index[season].normalize().asi8)
    k, count = config_value("transformer.homes_per_transformer", config), config_value("transformer.count", config)
    sessions = adoption.measure_ev_sessions(inputs["load"], inputs["homes"]["is_ev_l2"], inputs["temp"], config)
    runs = {}
    for seed in seeds:
        groups = feeder_groups.build_transformers(inputs["homes"]["segment"].to_numpy(), k, count, fitscore.GROUPING, seed)
        base = stress.base_loading(inputs["load"], groups)
        owner = stress.transformer_of_each_home(groups, len(inputs["homes"]))
        for i, scenario in enumerate(scenarios):
            parts = stress.loading_parts(inputs, groups, scenario, seed, config, sessions, base)
            setup = fitscore.flagged_setup(inputs, groups, base, parts, config)
            home_kw = setup["home_kw"]
            system_2030 = (base + shift.ev_loading_by_mode(fitscore.EV_MODE, parts, owner, groups.count, config)
                           + parts["hp"]).sum(0)
            random_key = np.random.default_rng((seed, 4, i)).random(home_kw.shape[:2])
            cell = {"flagged": len(home_kw), "load_kw": {s: float(system_2030[h].mean()) for s, h in sets.items()},
                    "cut_kw": {}}
            for units in config_value("battery.units_per_host_options", config):
                spec = dispatch.battery_spec(units, config)
                scores = fitscore.fit_score(home_kw[:, :, season], season_day, spec)
                for policy in POLICIES:
                    hosts = fitscore.choose_hosts(policy, scores, home_kw, setup["worst_hour"], HOSTS, random_key)
                    for name, hours in sets.items():
                        cell["cut_kw"][(policy, units, name)] = fleet_cut_kw(home_kw, hosts, hours, index, spec)
            runs[(scenario, seed)] = cell
    return runs, sets, rank, index


def summarize_top_hours(runs):
    """Seed means per scenario: batteries, fleet MW, kW per battery and % of the homes' 2030 load, per set."""
    out = {}
    for scenario in sorted({s for s, _ in runs}):
        group = [c for (s, _), c in sorted(runs.items()) if s == scenario]
        flagged = float(np.mean([c["flagged"] for c in group]))
        cell = {"flagged_per_seed": round(flagged, 1), "seeds": len(group), "cut": {}}
        for key in group[0]["cut_kw"]:
            policy, units, name = key
            cut = float(np.mean([c["cut_kw"][key] for c in group]))
            load = float(np.mean([c["load_kw"][name] for c in group]))
            batteries = flagged * HOSTS * units
            cell["cut"][key] = {"fleet_mw": round(cut / 1000, 3), "batteries": round(batteries, 1),
                                "kw_per_battery": round(cut / batteries, 2) if batteries else 0.0,
                                "share_of_load_pct": round(100 * cut / load, 3) if load else 0.0}
        out[scenario] = cell
    return out


def record_top_hours(summary, sets, rank, index, config, seconds):
    """Aggregates only, to facts/facts.json: the hour sets, the named dates' rank, and every fleet cut."""
    from analysis.facts import record
    for name, hours in sets.items():
        record(f"ewu.tophours.sets.{name}.hours", len(hours), "hours", "metered system load of the whole sample")
        record(f"ewu.tophours.sets.{name}.days", len({d.date() for d in index[hours]}), "days", "days holding those hours")
        for date in DATES:
            on = int((index[hours].normalize() == pd.Timestamp(config_value(f"demo.{date}", config))).sum())
            record(f"ewu.tophours.sets.{name}.hours_on_{date}", on, "hours", f"hours of the set on {config_value(f'demo.{date}', config)}")
    for date in DATES:
        record(f"ewu.tophours.{date}.rank", int(rank[sets[date][0]]), "rank among 8,760 hours",
               "the date's highest metered system hour; rank 1 = highest of the year")
    margin = stress.margin_label(config_value("transformer.base_margin", config))
    for scenario, cell in summary.items():
        key = f"ewu.tophours.{scenario}.{fitscore.EV_MODE}.{margin}"
        how = (f"pooled {cell['seeds']} seeds, {HOSTS} host per transformer still over the limit with staggered "
               "charging, battery dispatched for the system on these hours")
        record(f"{key}.flagged_per_seed", cell["flagged_per_seed"], "transformers", how)
        for (policy, units, name), v in cell["cut"].items():
            for field, unit in (("fleet_mw", "MW, mean over the set"), ("batteries", "batteries per seed"),
                                ("kw_per_battery", "kW per battery, mean over the set"),
                                ("share_of_load_pct", "% of the 2030 load of all homes on the 3,000 transformers")):
                record(f"{key}.{policy}.units_{units}.{name}.{field}", v[field], unit, how)
    record("ewu.tophours.seconds", round(seconds, 1), "s", "whole top-hours run")


def print_top_hours(summary, sets, rank, index, config):
    """Aggregate table: one line per scenario, set, policy and unit count."""
    for date in DATES:
        stamp = index[sets[date][0]]
        print(f"{config_value(f'demo.{date}', config)} peak hour {stamp:%H}:00 ranks {rank[sets[date][0]]} of 8,760; "
              + ", ".join(f"{n} holds {int((index[h].normalize() == stamp.normalize()).sum())} of its hours"
                          for n, h in sets.items() if n.startswith("top_") or n == "winter_top"))
    print(f"\n{'scenario':<9} {'hour set':<17} {'hosts':<10} {'units':>5} {'batteries':>9} {'fleet MW':>9} "
          f"{'kW/battery':>10} {'% of load':>9}")
    for scenario, cell in summary.items():
        for (policy, units, name), v in sorted(cell["cut"].items(), key=lambda kv: (kv[0][2], kv[0][1], kv[0][0])):
            print(f"{scenario:<9} {name:<17} {policy:<10} {units:>5} {v['batteries']:>9.1f} {v['fleet_mw']:>9.3f} "
                  f"{v['kw_per_battery']:>10.2f} {v['share_of_load_pct']:>9.3f}")


def main():
    config = read_config()
    started = time.time()
    runs, sets, rank, index = run_top_hours(read_inputs(), config, range(config_value("checks.seeds", config)))
    summary = summarize_top_hours(runs)
    record_top_hours(summary, sets, rank, index, config, time.time() - started)
    print_top_hours(summary, sets, rank, index, config)
    print(f"\nfacts recorded; {time.time() - started:.1f} s, aggregates only")


if __name__ == "__main__":
    main()
