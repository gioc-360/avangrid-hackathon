"""EWU command line: one subcommand per milestone, run as `bin/ewu <subcommand>`.

What: `coldsnap --date 2026-02-07` runs the battery duration test through the cold snap and prints the
      aggregate table and the hour-by-hour state of charge across both nights; `sensitivity` runs the ladder
      over every scenario, sizing margin and grouping mode, prices it and prints the grid and the headline
      range. Later milestones add `inventory`, `screen` and `demo` here.
Why:  judges and the demo need one short command per question, and every command must print aggregates only,
      never a customer or a single transformer.
How:  argparse subcommands; each calls one module's run, summarize and record functions. Facts are written
      only when the run matches the config's cold snap date, so a what-if date never overwrites the record.
"""
import sys
from pathlib import Path
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import argparse
import time
import pandas as pd
from ewu import config_value, read_config, read_inputs


def print_coldsnap_table(summary, hosts):
    """One row per scenario and EV mode: how much is over the limit, and what 1 or 2 hosts clear."""
    head = f"{'scenario':<9} {'EV mode':<10} {'flagged %':>9} {'med hrs':>7} {'med kWh':>7} {'p90 kWh':>7} {'med run':>7}"
    for count in hosts:
        head += f" {f'clear {count}h %':>11} {f'kWh left {count}h %':>14} {f'empty {count}h %':>11}"
    print(head)
    for (scenario, mode), cell in sorted(summary.items()):
        line = (f"{scenario:<9} {mode:<10} {cell['flagged_pct']:>9.2f} {cell['hours_over_median']:>7.1f} "
                f"{cell['kwh_over_median']:>7.1f} {cell['kwh_over_p90']:>7.1f} {cell['longest_run_median']:>7.1f}")
        for count in hosts:
            b = cell["hosts"][count]
            line += f" {b['cleared_pct']:>11.2f} {b['kwh_over_left_pct']:>14.2f} {b['ran_empty_pct']:>11.2f}"
        print(line)


def print_coldsnap_hours(cell, window, temps, hosts):
    """Hour by hour across both nights: share of flagged transformers still over, median and low-tail charge."""
    head = f"{'hour':<16} {'temp F':>6} {'over, none %':>12}"
    for count in hosts:
        head += f" {f'over, {count}h %':>11} {f'med SoC {count}h %':>14} {f'p10 SoC {count}h %':>14}"
    print(head)
    for j, stamp in enumerate(window[2]):
        line = f"{pd.Timestamp(stamp):%a %m-%d %H:00} {temps[j]:>6.1f} {cell['over_pct_by_hour'][j]:>12.2f}"
        for count in hosts:
            b = cell["hosts"][count]
            line += f" {b['over_pct_by_hour'][j]:>11.2f} {b['soc_median_pct_by_hour'][j]:>14.1f} {b['soc_p10_pct_by_hour'][j]:>14.1f}"
        print(line)


def run_coldsnap_command(args):
    from ewu import coldsnap
    config = read_config()
    started = time.time()
    seeds = range(config_value("checks.seeds", config))
    runs, window = coldsnap.run_coldsnap(read_inputs(), config, args.date, seeds)
    summary = coldsnap.summarize_coldsnap(runs)
    seconds = time.time() - started
    hosts = config_value("battery.coldsnap_hosts_per_transformer", config)
    official = pd.Timestamp(args.date) == pd.Timestamp(config_value("demo.cold_snap_start", config))
    if official:
        coldsnap.record_coldsnap(summary, runs, window, config, seconds)
    spec = next(iter(runs.values()))["spec"]
    print(f"Cold snap from {args.date}, {window[1] - window[0]} hours, {len(seeds)} seeds, "
          f"{config_value('transformer.count', config)} synthetic transformers per seed, rating = today's peak x "
          f"{config_value('transformer.base_margin', config)}, limit {config_value('transformer.overload_limit', config)} x rating")
    print(f"Each host: {spec['energy_kwh']:.2f} kWh, {spec['power_kw']:.2f} kW, round trip {spec['efficiency']}; "
          f"columns 'Nh' = N host homes per flagged transformer\n")
    print_coldsnap_table(summary, hosts)
    show = (config_value("demo.scenario", config), "staggered")
    print(f"\nHour by hour, {show[0]} 2030, staggered EV charging, share of flagged transformers:")
    print_coldsnap_hours(summary[show], window, coldsnap.window_temps(window), hosts)
    print(f"\n{'facts recorded' if official else 'what-if date: facts not recorded'}; {seconds:.1f} s")
    return 0


def print_sensitivity(pooled, priced, config):
    """One row per grid cell: the ladder as shares of all transformers, then its cost against upgrading all."""
    from ewu import economics
    from ewu.stress import margin_label
    print(f"{'scenario':<9} {'grouping':<13} {'margin':>6} {'flag %':>7} {'shift %':>7} {'protect %':>9} "
          f"{'upgrade %':>9} {'batt/prot':>9} {'ladder cost % of upgrade-all: mid':>34} {'low':>6} {'high':>6} {'0% rate':>7}")
    for cell in sorted(pooled):
        s, costs = pooled[cell]["shares"], priced[cell]
        share = {case: costs[(case, "discounted")]["share_of_upgrade_all_pct"]["ladder"] for case in economics.PRICE_CASES}
        print(f"{cell[0]:<9} {cell[1]:<13} {cell[2]:>6.2f} {s['flagged_pct']:>7.2f} {s['shift_fixed_pct']:>7.2f} "
              f"{s['protected_pct']:>9.2f} {s['upgrade_left_pct']:>9.2f} {s['batteries_per_protected']:>9.2f} "
              f"{share['mid']:>34.2f} {share['low']:>6.2f} {share['high']:>6.2f} "
              f"{costs[('mid', 'zero_rate')]['share_of_upgrade_all_pct']['ladder']:>7.2f}")
    base = (config_value("demo.scenario", config), "random", config_value("transformer.base_margin", config))
    head = economics.headline_range(priced, base)
    print(f"\nHeadline: the ladder costs {head['base']:.2f}% of upgrading every flagged transformer "
          f"({base[0]}, {base[1]} grouping, {margin_label(base[2])}, mid prices), "
          f"range {head['low']:.2f}% to {head['high']:.2f}% over all {len(pooled)} cells and price cases")
    alone = economics.headline_range(priced, base, "shift_then_upgrade")
    print(f"Shift, then upgrade (no batteries): {alone['base']:.2f}%, range {alone['low']:.2f}% to {alone['high']:.2f}%")
    for case in economics.PRICE_CASES:
        b = economics.battery_against_upgrade(pooled[base], economics.prices_for_case(case, config))
        print(f"Battery vs upgrade, {case} prices, per cleared transformer: {b['batteries_per_cleared']} batteries, "
              f"${b['battery_yearly_usd']:,}/yr vs upgrade ${b['upgrade_yearly_usd']:,}/yr; tie at "
              f"${b['tie_unit_usd_equal_life']:,} per unit (equal life), ${b['tie_unit_usd_deferral']:,} (deferral)")
    mid = priced[base][("mid", "discounted")]["present_usd"]
    scale = economics.nyseg_transformers(config) / pooled[base]["transformers"] / 1e6
    print(f"Scaled to NYSEG (labeled assumption: {economics.nyseg_transformers(config):,.0f} transformers like ours), "
          f"present value: upgrade all ${mid['upgrade_all'] * scale:,.1f}M, ladder ${mid['ladder'] * scale:,.1f}M")


def run_sensitivity_command(args):
    from ewu import economics, sensitivity
    from analysis.facts import record
    config = read_config()
    started = time.time()
    runs = sensitivity.run_sensitivity(read_inputs(), config, range(config_value("checks.seeds", config)))
    pooled = sensitivity.summarize_ladder(runs)
    priced = economics.price_every_cell(pooled, config)
    sensitivity.record_ladder(pooled)
    economics.record_economics(pooled, priced, config)
    seconds = time.time() - started
    record("ewu.sensitivity.seconds", round(seconds, 1), "s", "whole sensitivity grid and pricing")
    print(f"Sensitivity grid: {len(pooled)} cells, {config_value('checks.seeds', config)} seeds, "
          f"{config_value('transformer.count', config)} synthetic transformers per seed; shares are % of all transformers; "
          f"discount rate {config_value('prices.discount_rate', config)}\n")
    print_sensitivity(pooled, priced, config)
    print(f"\nfacts recorded; {seconds:.1f} s")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ewu", description="Electrify Without Upgrade prototype")
    commands = parser.add_subparsers(dest="command", required=True)
    cold = commands.add_parser("coldsnap", help="battery duration test through the cold snap")
    cold.add_argument("--date", default=config_value("demo.cold_snap_start"), help="first day of the window")
    cold.set_defaults(run=run_coldsnap_command)
    grid = commands.add_parser("sensitivity", help="ladder and its cost over scenarios x sizing margins x groupings")
    grid.set_defaults(run=run_sensitivity_command)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
