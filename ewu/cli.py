"""EWU command line: one subcommand per milestone, run as `bin/ewu <subcommand>`.

What: `inventory` lists every home's equipment, segment and eligible programs (aggregate table on screen,
      rows in outputs/private); `screen` runs the battery plan (the deck profile in code: both scenarios,
      battery-only fix, money, peak cut; `--profile cautious --scenario moderate --margin 1.15` runs the earlier
      Flag, Shift, Place, Upgrade) live; `coldsnap --date 2026-02-07` tests battery duration through the cold
      snap; `sensitivity` prices the ladder over every scenario, margin and grouping; `tophours` measures the MW battery hosts cut in the system's top 20 and 50 hours; `robustness` reruns
      the heat pump slope variants, the flag durations and the 3 kVA test; `network` writes the screen's
      synthetic network for the page; `arrays` checks the teammate's two arrays; `case` writes the business
      case; `demo` builds the offline page. No printout or help names the deck (tests/test_no_deck_words.py).
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
          f"columns: med = median over flagged transformers, p90 = 90th percentile, run = longest stretch of hours over, "
          f"'Nh' = N host homes per flagged transformer\n")
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
    if args.replica or args.profile == "replica":
        from ewu import deck_replica_run
        deck_replica_run.main("teammate" if args.tiers == "team" else args.tiers)   # "teammate" stays the code value
        return 0
    if args.profile == "battery":
        from ewu import deck_screen
        deck_screen.main(args.limit, True if args.managed else None)
        return 0
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


def run_network_command(args):
    if args.profile == "battery":
        from ewu import deck_views
        deck_views.network_main(args.scenario, args.limit, True if args.managed else None)
        return 0
    from ewu import network
    network.main()
    return 0


def run_top_hours_command(args):
    from ewu import tophours
    tophours.main()
    return 0


def run_robustness_command(args):
    from ewu import headroom, robustness
    robustness.main()
    print()
    headroom.main()
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


PROFILE_NAMES = {"deck": "battery", "deck-replica": "replica"}   # shown names; the old typed names still work


def add_profile_options(command, replica=False):
    """--profile (battery by default, cautious = the earlier method), --limit and --managed for the battery plan."""
    command.add_argument("--profile", default=PROFILE_NAMES.get(config_value("profiles.default")), type=lambda t: PROFILE_NAMES.get(t, t),
                         choices=("battery", "cautious") + (("replica",) if replica else ()),
                         help="battery = the battery plan (default); cautious = the earlier Flag, Shift, Place, Upgrade")
    command.add_argument("--limit", type=float, default=config_value("profiles.deck.overload_limit"),
                         choices=config_value("profiles.deck.overload_limit_options"), help="battery: overloaded above this x rating")
    command.add_argument("--managed", action="store_true", help="battery: managed charging (optional)")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ewu", description="Electrify Without Upgrade prototype")
    commands = parser.add_subparsers(dest="command", required=True)
    inv = commands.add_parser("inventory", help="technology, segment and eligible programs for every home")
    inv.set_defaults(run=run_inventory_command)
    scr = commands.add_parser("screen", help="Flag, Shift, Place, Upgrade for one scenario and sizing, live")
    scr.add_argument("--scenario", default=config_value("demo.scenario"), choices=("moderate", "high"))
    scr.add_argument("--margin", type=float, default=config_value("demo.margin"), help="rating = today's peak x this")
    scr.add_argument("--grouping", default="random", choices=("random", "same_segment"))
    scr.add_argument("--map", help="CSV with meter_id, transformer_id, kva; replaces the synthetic transformers (cautious)")
    add_profile_options(scr, replica=True)
    scr.add_argument("--replica", action="store_true", help="profile replica: the team's model followed exactly")
    scr.add_argument("--tiers", default="team", choices=("team", "ours"), type=lambda s: s.replace("teammate", "team"), help="replica: whose EV and heat tiers")
    scr.set_defaults(run=run_screen_command)
    net = commands.add_parser("network", help="the live screen's synthetic network, transformer by transformer, for the page")
    net.add_argument("--scenario", default=None, choices=("moderate", "high"), help="battery: scenario (default demo.scenario)")
    add_profile_options(net)
    net.set_defaults(run=run_network_command)
    cold = commands.add_parser("coldsnap", help="battery duration test through the cold snap")
    cold.add_argument("--date", default=config_value("demo.cold_snap_start"), help="first day of the window")
    cold.set_defaults(run=run_coldsnap_command)
    grid = commands.add_parser("sensitivity", help="the steps and their cost over scenarios x sizing margins x groupings")
    grid.set_defaults(run=run_sensitivity_command)
    top = commands.add_parser("tophours", help="MW the fit-score batteries cut in the system's top 20 and 50 hours")
    top.set_defaults(run=run_top_hours_command)
    rob = commands.add_parser("robustness", help="heat pump slope variants, flag durations, 3 kVA test by charge length")
    rob.set_defaults(run=run_robustness_command)
    case = commands.add_parser("case", help="write docs/BUSINESS_CASE.md with every number filled from facts")
    case.set_defaults(run=run_case_command)
    demo = commands.add_parser("demo", help="build the offline demo page and open it")
    demo.add_argument("--no-open", action="store_true", help="build only")
    demo.set_defaults(run=run_demo_command)
    from ewu import plan_output, deck_arrays, deck_recharge   # plan: action lists; arrays: teammate's inputs; recharge: sizing
    for module in (plan_output, deck_arrays, deck_recharge):
        module.add_command(commands)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
