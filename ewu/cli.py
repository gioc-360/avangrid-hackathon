"""EWU command line: one subcommand per milestone, run as `bin/ewu <subcommand>`.

What: `inventory` lists every home's equipment, segment and eligible programs (aggregate table on screen,
      rows in outputs/private); `screen --scenario moderate --margin 1.15` runs Flag, Shift, Protect, Upgrade
      live on the full data; `coldsnap --date 2026-02-07` runs the battery duration test through the cold
      snap; `sensitivity` runs and prices the ladder over every scenario, sizing margin and grouping mode;
      `tophours` measures the MW battery hosts cut in the system's top 20 and 50 hours; `case` writes
      the one-page business case from facts; `demo` builds the offline 4-step page and opens it.
Why:  judges and the demo need one short command per question, and every command must print aggregates only,
      never a customer or a single transformer.
How:  argparse subcommands; each calls one module's run, summarize and record functions and ewu/printouts.py
      or the module's own printer. Cold snap facts are written only for the config's date, and screen facts
      only for synthetic transformers, so a what-if run never overwrites the record.
"""
import sys
from pathlib import Path
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import argparse
import subprocess
import time
import pandas as pd
from ewu import config_value, read_config, read_inputs, printouts


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
    printouts.print_coldsnap_table(summary, hosts)
    show = (config_value("demo.scenario", config), "staggered")
    print(f"\nHour by hour, {show[0]} 2030, staggered EV charging, share of flagged transformers:")
    printouts.print_coldsnap_hours(summary[show], window, coldsnap.window_temps(window), hosts)
    print(f"\n{'facts recorded' if official else 'what-if date: facts not recorded'}; {seconds:.1f} s")
    return 0


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
    printouts.print_sensitivity(pooled, priced, config)
    print(f"\nfacts recorded; {seconds:.1f} s")
    return 0


def run_inventory_command(args):
    from ewu import inventory
    config = read_config()
    homes = inventory.build_inventory(config)
    inventory.PRIVATE_TABLE.parent.mkdir(parents=True, exist_ok=True)
    homes.to_parquet(inventory.PRIVATE_TABLE, index=False)
    summary = inventory.summarize_inventory(homes, config)
    inventory.record_inventory(summary, homes, read_inputs()["load"], config)
    inventory.print_inventory(summary)
    return 0


def run_screen_command(args):
    from ewu import screen
    config = read_config()
    started = time.time()
    cell = screen.run_screen(read_inputs(), config, args.scenario, args.margin, args.grouping, map_path=args.map)
    money = screen.price_screen(cell, config)
    seconds = time.time() - started
    if not args.map:
        screen.record_screen(cell, money, args.scenario, args.grouping, args.margin, seconds)
    screen.print_screen(cell, money, args.scenario, args.grouping, args.margin, seconds)
    return 0


def run_top_hours_command(args):
    from ewu import tophours
    tophours.main()
    return 0


def run_case_command(args):
    from ewu import business_case
    business_case.main()
    return 0


def run_demo_command(args):
    from ewu import demo_page
    path = demo_page.build_page(read_config())
    print(f"Demo page built from cached results: {path.relative_to(path.parents[2])} (offline, stays on this machine)")
    if not args.no_open:
        subprocess.run(["open", str(path)], check=False)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ewu", description="Electrify Without Upgrade prototype")
    commands = parser.add_subparsers(dest="command", required=True)
    inv = commands.add_parser("inventory", help="equipment, segment and eligible programs for every home")
    inv.set_defaults(run=run_inventory_command)
    scr = commands.add_parser("screen", help="Flag, Shift, Protect, Upgrade for one scenario and sizing, live")
    scr.add_argument("--scenario", default=config_value("demo.scenario"), choices=("moderate", "high"))
    scr.add_argument("--margin", type=float, default=config_value("demo.margin"), help="rating = today's peak x this")
    scr.add_argument("--grouping", default="random", choices=("random", "same_segment"))
    scr.add_argument("--map", help="CSV with meter_id, transformer_id, kva; replaces the synthetic groups")
    scr.set_defaults(run=run_screen_command)
    cold = commands.add_parser("coldsnap", help="battery duration test through the cold snap")
    cold.add_argument("--date", default=config_value("demo.cold_snap_start"), help="first day of the window")
    cold.set_defaults(run=run_coldsnap_command)
    grid = commands.add_parser("sensitivity", help="ladder and its cost over scenarios x sizing margins x groupings")
    grid.set_defaults(run=run_sensitivity_command)
    top = commands.add_parser("tophours", help="MW the fit-score batteries cut in the system's top 20 and 50 hours")
    top.set_defaults(run=run_top_hours_command)
    case = commands.add_parser("case", help="write docs/BUSINESS_CASE.md with every number filled from facts")
    case.set_defaults(run=run_case_command)
    demo = commands.add_parser("demo", help="build the offline 4-step demo page and open it")
    demo.add_argument("--no-open", action="store_true", help="build only")
    demo.set_defaults(run=run_demo_command)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
