"""Robustness: how far the heat pump answer and the flagged share move when a soft input moves.

What: run_slope_variants() reruns the attribution and shift grid (random grouping, both scenarios) with the
      heat pump slope scaled by each multiplier in `robustness.hp_slope_multipliers`; count_hours_over()
      measures how many hours a year each transformer spends over the limit with EV charging unmanaged;
      summarize_flag_duration() turns those hours into the flagged share at one hour and at
      `robustness.flag_min_hours`, plus the share of flagged transformers over for fewer hours than that;
      run_adoption_variant() reruns attribution, shift and hours over with heat pump adopters drawn off their
      own random order instead of the EV order; record_robustness() writes all of it under ewu.robustness.*.
Why:  the M8 review found two soft spots. The heat pump slope (0.05 kW per F) is a median difference between
      groups of homes, not a heat pump model, and the answer "EVs decide whether, heat pumps decide when"
      depends on it. And a flag is any single hour over, so a transformer over for one hour a year is priced
      as a full upgrade. The number review then found EV and heat pump adopters share one random order, which
      stacks both loads on the same homes. All three are stated as ranges instead of left for a judge to find.
How:  the slope variants reuse ewu.attribution end to end on a copy of the config with only the slope
      changed, so a multiplier of 1.0 must reproduce the recorded M2 facts (a test checks it). Hours over
      reuse ewu.stress loading and ratings on the same seeds, so the one-hour share equals the M1 fact.
"""
import sys
from pathlib import Path
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import copy
import time
import numpy as np
from ewu import config_value, read_config, read_inputs
from ewu import attribution, adoption, feeders as feeder_groups, stress

SLOPE_KEY = ("scenarios", "loads", "hp_kw_per_degf")
ORDER_KEY = ("scenarios", "loads", "adopters_share_one_order")
SHOWN = ("hours_lead_hp_pct", "hours_with_hp_running_pct", "worst_hour_hp_led_pct", "overloaded_without_ev_of_all_pct",
         "hours_both_needed_pct", "hours_ev_strictly_larger_pct", "hours_clear_without_ev_pct")


def slope_label(multiplier):
    return f"hp_slope_x{int(round(multiplier * 100))}"


def config_with(config, path, change):
    """A copy of the config with one input's value passed through `change`; nothing else changes."""
    changed = copy.deepcopy(config)
    node = changed
    for part in path:
        node = node[part]
    node["value"] = change(node["value"])
    return changed


def config_with_slope(config, multiplier):
    return config_with(config, SLOPE_KEY, lambda value: value * multiplier)


def run_adoption_variant(inputs, config, seeds):
    """Heat pump adopters off their own order: attribution summary, hours over by scenario, and the overlap."""
    own = config_with(config, ORDER_KEY, lambda value: False)
    summary = attribution.summarize_runs(attribution.run_attribution(inputs, own, seeds, groupings=("random",)), own)
    hours = {s: count_hours_over(inputs, own, seeds, s) for s in stress.SCENARIOS}
    return summary, hours, {"one_order": heat_pump_homes_with_new_ev(inputs, config, seeds),
                            "own_order": heat_pump_homes_with_new_ev(inputs, own, seeds)}


def heat_pump_homes_with_new_ev(inputs, config, seeds):
    """{scenario: % of new heat pump homes that also get a new EV}, pooled over seeds."""
    k, count, out = config_value("transformer.homes_per_transformer", config), config_value("transformer.count", config), {}
    for scenario in stress.SCENARIOS:
        both = total = 0
        for seed in seeds:
            groups = feeder_groups.build_transformers(inputs["homes"]["segment"].to_numpy(), k, count, "random", seed)
            ev, hp = adoption.pick_adopters(groups.homes, inputs["homes"], scenario, seed, config)
            both, total = both + len(np.intersect1d(ev, hp)), total + len(hp)
        out[scenario] = round(100.0 * both / total, 2)
    return out


def run_slope_variants(inputs, config, seeds):
    """Per multiplier: the attribution summary for random grouping, both scenarios, every EV mode."""
    out = {}
    for multiplier in config_value("robustness.hp_slope_multipliers", config):
        scaled = config_with_slope(config, multiplier)
        runs = attribution.run_attribution(inputs, scaled, seeds, groupings=("random",))
        out[multiplier] = attribution.summarize_runs(runs, scaled)
    return out


def count_hours_over(inputs, config, seeds, scenario):
    """Hours over the limit for every transformer, unmanaged EV charging, random grouping: {margin: array}."""
    k = config_value("transformer.homes_per_transformer", config)
    count = config_value("transformer.count", config)
    limit = config_value("transformer.overload_limit", config)
    sessions = adoption.measure_ev_sessions(inputs["load"], inputs["homes"]["is_ev_l2"], inputs["temp"], config)
    hours = {m: [] for m in config_value("transformer.sizing_margins", config)}
    for seed in seeds:
        groups = feeder_groups.build_transformers(inputs["homes"]["segment"].to_numpy(), k, count, "random", seed)
        base = stress.base_loading(inputs["load"], groups)
        parts = stress.loading_parts(inputs, groups, scenario, seed, config, sessions, base)
        total = parts["base"] + parts["ev"] + parts["hp"]
        for margin in hours:
            ceiling = limit * feeder_groups.rate(base.max(1), margin)
            hours[margin].append((total > ceiling[:, None]).sum(1))
    return hours


def summarize_flag_duration(hours_by_seed, min_hours):
    """Flagged share at one hour and at min_hours (mean of seeds), and the flagged share under min_hours."""
    one = [100.0 * float((h >= 1).mean()) for h in hours_by_seed]
    rule = [100.0 * float((h >= min_hours).mean()) for h in hours_by_seed]
    pooled = np.concatenate(hours_by_seed)
    flagged = pooled >= 1
    short = (pooled[flagged] < min_hours).mean() if flagged.any() else 0.0
    return {"flagged_pct": round(float(np.mean(one)), 2), "flagged_min_hours_pct": round(float(np.mean(rule)), 2),
            "short_of_flagged_pct": round(100.0 * float(short), 2),
            "median_hours_of_flagged": float(np.median(pooled[flagged])) if flagged.any() else 0.0}


def record_robustness(variants, durations, config, seconds):
    """Write the slope variants and flag durations to facts/facts.json (aggregates only)."""
    from analysis.facts import record
    base_margin = stress.margin_label(config_value("transformer.base_margin", config))
    slope = config_value("scenarios.loads.hp_kw_per_degf", config)
    balance = config_value("scenarios.loads.hp_balance_temp_f", config)
    for multiplier, summary in variants.items():
        key = f"ewu.robustness.{slope_label(multiplier)}"
        record(f"{key}.kw_per_degf", round(slope * multiplier, 3), "kW per F below the balance point",
               f"config slope x {multiplier}")
        record(f"{key}.kw_at_0f", round(slope * multiplier * balance, 2), "kW per heat pump at 0 F", "")
        for scenario in stress.SCENARIOS:
            how = f"pooled seeds, random grouping, heat pump slope x {multiplier}, rating = today's peak x base margin"
            for mode in ("unmanaged", "staggered"):
                row = summary[(scenario, "random", mode)]["by_margin"][config_value("transformer.base_margin", config)]
                record(f"{key}.{scenario}.{base_margin}.{mode}.overloaded_pct", row["overloaded_pct"],
                       "% of transformers", how)
            staggered = summary[(scenario, "random", "staggered")]["by_margin"]
            record(f"{key}.{scenario}.{base_margin}.staggered.fixed_pct",
                   staggered[config_value("transformer.base_margin", config)]["fixed_pct"],
                   "% of transformers overloaded unmanaged", how)
            shares = summary[(scenario, "random", "unmanaged")]["attribution"]
            for name in SHOWN:
                record(f"{key}.{scenario}.{base_margin}.unmanaged.{name}", shares[name], "%", how)
    min_hours = config_value("robustness.flag_min_hours", config)
    for (scenario, margin), cell in durations.items():
        key = f"ewu.robustness.flag_hours.{scenario}.random.{stress.margin_label(margin)}"
        how = f"mean of seeds, EV charging unmanaged, rating = today's peak x {margin}"
        record(f"{key}.flagged_pct", cell["flagged_pct"], "% of transformers over at least 1 hour a year", how)
        record(f"{key}.flagged_min_hours_pct", cell["flagged_min_hours_pct"],
               f"% of transformers over at least {min_hours} hours a year", how)
        record(f"{key}.short_of_flagged_pct", cell["short_of_flagged_pct"],
               f"% of flagged transformers over fewer than {min_hours} hours a year", "pooled seeds")
        record(f"{key}.median_hours_of_flagged", cell["median_hours_of_flagged"], "hours a year", "pooled seeds")
    record("ewu.robustness.seconds", round(seconds, 1), "s", "slope variants, flag durations, adoption order")


def record_adoption_variant(one, own, config):
    """Both adoption orders side by side at the base margin: one = (summary, durations, overlap) per order."""
    from analysis.facts import record
    base = config_value("transformer.base_margin", config)
    for label, (summary, durations, overlap) in (("one_order", one), ("own_order", own)):
        for scenario in stress.SCENARIOS:
            key = f"ewu.robustness.adoption_{label}.{scenario}.{stress.margin_label(base)}"
            how = f"pooled seeds, random grouping, heat pump adopters {label.replace('_', ' ')}"
            record(f"{key}.hp_homes_with_new_ev_pct", overlap[scenario], "% of new heat pump homes", how)
            record(f"{key}.unmanaged.overloaded_pct", summary[(scenario, "random", "unmanaged")]["by_margin"][base]["overloaded_pct"],
                   "% of transformers", how)
            record(f"{key}.staggered.fixed_pct", summary[(scenario, "random", "staggered")]["by_margin"][base]["fixed_pct"],
                   "% of transformers overloaded unmanaged", how)
            record(f"{key}.flagged_min_hours_pct", durations[(scenario, base)]["flagged_min_hours_pct"],
                   f"% of transformers over at least {config_value('robustness.flag_min_hours', config)} hours a year", how)
            for name in SHOWN:
                record(f"{key}.unmanaged.{name}", summary[(scenario, "random", "unmanaged")]["attribution"][name], "%", how)


def main():
    config = read_config()
    inputs = read_inputs()
    seeds = range(config_value("checks.seeds", config))
    started = time.time()
    variants = run_slope_variants(inputs, config, seeds)
    min_hours = config_value("robustness.flag_min_hours", config)
    def durations_of(hours):
        return {(s, m): summarize_flag_duration(h, min_hours) for s, by in hours.items() for m, h in by.items()}
    durations = durations_of({s: count_hours_over(inputs, config, seeds, s) for s in stress.SCENARIOS})
    own_summary, own_hours, overlap = run_adoption_variant(inputs, config, seeds)
    own_durations = durations_of(own_hours)
    record_adoption_variant((variants[1.0], durations, overlap["one_order"]),
                            (own_summary, own_durations, overlap["own_order"]), config)
    record_robustness(variants, durations, config, time.time() - started)
    base = config_value("transformer.base_margin", config)
    print(f"{'heat pump slope':<16} {'scenario':<9} {'flagged %':>9} {'stagger fixes %':>15} {'HP-led hrs %':>12}")
    for multiplier, summary in variants.items():
        for scenario in stress.SCENARIOS:
            flag, fixed = summary[(scenario, "random", "unmanaged")], summary[(scenario, "random", "staggered")]
            print(f"{'x ' + str(multiplier):<16} {scenario:<9} {flag['by_margin'][base]['overloaded_pct']:>9.2f} "
                  f"{fixed['by_margin'][base]['fixed_pct']:>15.2f} {flag['attribution']['hours_lead_hp_pct']:>12.2f}")
    print(f"\n{'scenario':<9} {'margin':>6} {'flagged %':>9} {f'>= {min_hours} h %':>9} {'short of flagged %':>18}")
    for (scenario, margin), cell in durations.items():
        print(f"{scenario:<9} {margin:>6.2f} {cell['flagged_pct']:>9.2f} {cell['flagged_min_hours_pct']:>9.2f} "
              f"{cell['short_of_flagged_pct']:>18.2f}")


if __name__ == "__main__":
    main()
