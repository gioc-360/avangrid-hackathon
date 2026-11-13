"""Fit score: which homes on a flagged transformer should host a battery, judged on the system's top hours.

What: system_top_hours() picks the highest metered system hours per season (Feb 7 and Jul 2 fall in the set);
      fit_score() is the kW a battery in each home could cut in those hours; run_fitscore() flags every
      transformer still over the limit with staggered EV charging, puts 1 or 2 hosts with 1 or 2 units each on
      it, chosen by fit score, at random, or by the M3 rule (largest draw in the transformer's worst hour), and
      dispatches all year; summarize_fitscore() and record_fitscore() pool seeds into facts.
Why:  the rubric pays for a battery opportunity assessment. A battery that helps the system peak and also
      clears a local overload pays twice; the test is whether fit-score hosts clear more flagged transformers
      per battery than random hosts on the same transformers with the same battery count.
How:  a home's 2030 kW in each top hour is metered + new heat pump + new EV (staggered). The battery cut per
      hour is the smaller of the home's kW and the battery's power (no export), scaled down on any day where
      the cuts add to more than the usable energy. The score is the mean cut over the top hours. Clearing
      uses ewu/dispatch.py: a transformer is cleared when no hour of the year stays above the limit.
"""
import sys
from pathlib import Path
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import time
import numpy as np
import pandas as pd
from ewu import PROCESSED, config_value, read_config, read_inputs
from ewu import adoption, dispatch, feeders as feeder_groups, shift, stress
from ewu.coldsnap import percent_of

POLICIES = ("fit_score", "random", "worst_hour")
EV_MODE = "staggered"
GROUPING = "random"


def system_top_hours(sysload, index, config):
    """Sorted hour numbers: the `top_hours_per_season` highest system hours in winter months and in summer months."""
    count = config_value("battery.top_hours_per_season", config)
    picked = []
    for season in ("winter_months", "summer_months"):
        months = np.flatnonzero(np.isin(index.month, config_value(f"battery.{season}", config)))
        picked.append(months[np.argsort(-np.asarray(sysload)[months], kind="stable")[:count]])
    return np.sort(np.concatenate(picked))


def fit_score(home_kw_top, top_day, spec):
    """kW a battery cuts in each home, averaged over the top hours: power- and load-limited, energy per day capped."""
    cut = np.minimum(np.maximum(np.asarray(home_kw_top, dtype=np.float64), 0.0), spec["power_kw"])
    usable = spec["energy_kwh"] - spec["floor_kwh"]
    _, day = np.unique(top_day, return_inverse=True)
    for d in range(day.max() + 1):
        on = day == d
        total = cut[..., on].sum(-1, keepdims=True)
        cut[..., on] *= np.minimum(1.0, usable / np.maximum(total, 1e-12))
    return cut.mean(-1)


def choose_hosts(policy, scores, home_kw, worst_hour, count, random_key):
    """Per flagged transformer, the positions (0..k-1) of its `count` host homes under one policy.

    random_key (T, k) is drawn once per seed and scenario, so random hosts nest (the 1-host pick is in the
    2-host pick) and are the same homes whatever the unit count, as fit-score hosts are."""
    if policy == "fit_score":
        return np.argsort(-scores, axis=1, kind="stable")[:, :count]
    if policy == "random":
        return np.argsort(random_key, axis=1, kind="stable")[:, :count]
    if policy == "worst_hour":
        local = np.broadcast_to(np.arange(scores.shape[1]), scores.shape)
        return dispatch.pick_hosts(home_kw, local, worst_hour, count)
    raise ValueError(f"policy must be one of {POLICIES}, not {policy}")


def flagged_setup(inputs, groups, base, parts, config, margin=None):
    """Transformers over the limit with staggered EV charging (base margin unless given), homes' kW, worst hour."""
    owner = stress.transformer_of_each_home(groups, len(inputs["homes"]))
    ceiling = config_value("transformer.overload_limit", config) * feeder_groups.rate(
        base.max(1), margin or config_value("transformer.base_margin", config))
    total = base + shift.ev_loading_by_mode(EV_MODE, parts, owner, groups.count, config) + parts["hp"]
    above = np.maximum(total - ceiling[:, None], 0.0)
    flagged = np.flatnonzero((above > dispatch.OVER_TOLERANCE_KW).any(1))
    homes = groups.homes.reshape(groups.count, -1)[flagged]
    home_kw = dispatch.own_loading(inputs, parts, homes.ravel(), owner, EV_MODE, config).astype(np.float32)
    return {"total": total[flagged], "ceiling": ceiling[flagged], "homes": homes, "transformers": groups.count,
            "flagged": flagged, "home_kw": home_kw.reshape(len(flagged), homes.shape[1], home_kw.shape[-1]), "worst_hour": above[flagged].argmax(1)}


def place_and_dispatch(setup, top, top_day, seed, scenario_index, config):
    """For every policy, host count and unit count: which flagged transformers clear, and the hosts' fit scores."""
    home_kw = setup["home_kw"]
    random_key = np.random.default_rng((seed, 4, scenario_index)).random(home_kw.shape[:2])
    out = {}
    for units in config_value("battery.units_per_host_options", config):
        spec = dispatch.battery_spec(units, config)
        scores = fit_score(home_kw[:, :, top], top_day, spec)
        for policy in POLICIES:
            for count in config_value("battery.coldsnap_hosts_per_transformer", config):
                hosts = choose_hosts(policy, scores, home_kw, setup["worst_hour"], count, random_key)
                t = np.arange(len(hosts))[:, None]
                host_kw = home_kw[t, hosts].transpose(1, 0, 2).astype(np.float64)
                result = dispatch.run_batteries(setup["total"], setup["ceiling"], host_kw, spec)
                out[(policy, count, units)] = {"cleared": result["hours_over"] == 0, "hosts": hosts,
                                               "host_fit_kw": scores[t, hosts].ravel()}
    return out


def run_fitscore(inputs, config, seeds, scenarios=stress.SCENARIOS):
    """Every seed x scenario: the flagged set and the placement results. {(scenario, seed): run}."""
    index = pd.read_parquet(PROCESSED / "weather.parquet").index
    top = system_top_hours(np.load(PROCESSED / "sysload.npy"), index, config)
    top_day = np.asarray(index[top].normalize().asi8)
    k, count = config_value("transformer.homes_per_transformer", config), config_value("transformer.count", config)
    sessions = adoption.measure_ev_sessions(inputs["load"], inputs["homes"]["is_ev_l2"], inputs["temp"], config)
    runs = {}
    for seed in seeds:
        groups = feeder_groups.build_transformers(inputs["homes"]["segment"].to_numpy(), k, count, GROUPING, seed)
        base = stress.base_loading(inputs["load"], groups)
        for i, scenario in enumerate(scenarios):
            parts = stress.loading_parts(inputs, groups, scenario, seed, config, sessions, base)
            setup = flagged_setup(inputs, groups, base, parts, config)
            runs[(scenario, seed)] = {"flagged": len(setup["homes"]), "transformers": setup["transformers"],
                                      "placed": place_and_dispatch(setup, top, top_day, seed, i, config)}
    return runs, index[top]


def cheapest_clear(placed, options):
    """Per transformer, the fewest batteries (hosts x units) that clear it, or 0 when no option does."""
    need = np.zeros(len(next(iter(placed.values()))), dtype=np.int64)
    for hosts, units in sorted(options, key=lambda o: (o[0] * o[1], o[0])):
        hit = placed[(hosts, units)] & (need == 0)
        need[hit] = hosts * units
    return need


def summarize_fitscore(runs):
    """Seed-pooled cleared share, cleared per 100 batteries and host fit kW per scenario, policy, hosts and units."""
    out = {}
    for scenario in sorted({s for s, _ in runs}):
        group = [r for (s, _), r in sorted(runs.items()) if s == scenario]
        flagged = sum(r["flagged"] for r in group)
        cell = {"flagged_per_seed": round(flagged / len(group), 1), "seeds": len(group),
                "flagged_pct": round(100.0 * flagged / sum(r["transformers"] for r in group), 2), "policies": {}}
        for policy in POLICIES:
            block, options = {}, []
            for (p, hosts, units) in group[0]["placed"]:
                if p != policy:
                    continue
                options.append((hosts, units))
                cleared = sum(int(r["placed"][(p, hosts, units)]["cleared"].sum()) for r in group)
                fit = np.concatenate([r["placed"][(p, hosts, units)]["host_fit_kw"] for r in group])
                block[f"hosts_{hosts}.units_{units}"] = {
                    "cleared_pct": percent_of(cleared, flagged),
                    "cleared_per_100_batteries": percent_of(cleared, flagged * hosts * units),
                    "host_fit_kw_median": round(float(np.median(fit)), 2) if len(fit) else 0.0}
            need = np.concatenate([cheapest_clear({o: r["placed"][(policy, *o)]["cleared"] for o in options}, options)
                                   for r in group])
            block["cheapest"] = {"cleared_pct": percent_of((need > 0).sum(), flagged),
                                 "batteries_per_cleared": round(float(need[need > 0].mean()), 2) if (need > 0).any() else 0.0}
            cell["policies"][policy] = block
        out[scenario] = cell
    return out


def record_fitscore(summary, top_stamps, config, seconds):
    """Aggregates only, to facts/facts.json."""
    from analysis.facts import record
    margin = stress.margin_label(config_value("transformer.base_margin", config))
    dates = sorted({str(ts.date()) for ts in top_stamps})
    record("ewu.fitscore.top_hours.count", len(top_stamps), "hours", "winter plus summer top system hours, metered load")
    record("ewu.fitscore.top_hours.dates", dates, "date", "days holding at least one top hour")
    for scenario, cell in summary.items():
        key = f"ewu.fitscore.{scenario}.{EV_MODE}.{margin}"
        how = f"pooled {cell['seeds']} seeds, {GROUPING} grouping, flagged = any hour over the limit, {EV_MODE} EV charging"
        record(f"{key}.flagged_pct", cell["flagged_pct"], "% of transformers", how)
        record(f"{key}.flagged_per_seed", cell["flagged_per_seed"], "transformers", how)
        for policy, block in cell["policies"].items():
            for option, values in block.items():
                for name, value in values.items():
                    unit = "kW" if name.endswith("kw_median") else "batteries" if name == "batteries_per_cleared" \
                        else "transformers cleared per 100 batteries" if "per_100" in name else "% of flagged transformers"
                    record(f"{key}.{policy}.{option}.{name}", value, unit, how + "; cleared = no hour over all year")
    record("ewu.fitscore.seconds", round(seconds, 1), "s", "whole fit score run")


def main():
    config = read_config()
    started = time.time()
    runs, stamps = run_fitscore(read_inputs(), config, range(config_value("checks.seeds", config)))
    summary = summarize_fitscore(runs)
    record_fitscore(summary, stamps, config, time.time() - started)
    print(f"Top system hours: {len(stamps)} on {len({ts.date() for ts in stamps})} days")
    print(f"{'scenario':<9} {'policy':<11} {'option':<17} {'cleared %':>9} {'per 100 batt':>12} {'host fit kW':>11}")
    for scenario, cell in summary.items():
        for policy, block in cell["policies"].items():
            for option, v in block.items():
                if option != "cheapest":
                    print(f"{scenario:<9} {policy:<11} {option:<17} {v['cleared_pct']:>9.2f} "
                          f"{v['cleared_per_100_batteries']:>12.2f} {v['host_fit_kw_median']:>11.2f}")
            c = block["cheapest"]
            print(f"{scenario:<9} {policy:<11} {'cheapest':<17} {c['cleared_pct']:>9.2f}  batteries per cleared {c['batteries_per_cleared']}")
    print(f"{time.time() - started:.1f} s")


if __name__ == "__main__":
    main()
