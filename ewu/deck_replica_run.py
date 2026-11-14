"""Deck replica run: `bin/ewu screen --replica` (profile deck-replica), its ladder to the deck profile, its facts.

What: run_scenarios() runs ewu/deck_replica.py for moderate and high and prices each cell like the deck;
      compare_rows() counts transformers whose every field equals her own run's table (when the audit's scratch
      rerun exists); ladder() walks from her run to our deck profile one difference at a time; record() writes
      aggregates under ewu.deck_replica.*; main() prints deck target, replica and deck profile side by side.
Why:  every deck headline must be reproduced exactly by our code following hers, and every gap between her
      run and our deck profile must be put down to a named, measured difference, not to tuning.
How:  ladder steps, each adding one change to the one before: A her run (her tiers, her groups, mean fill,
      8.064 kWh); B our inventory tiers; C our deck groups (seed 5, our generator) and our filled load and
      8.06 kWh; D our deck engine with shares of eligible homes (our draw, the deck default); E shares of all
      grouped homes (the earlier reading). Steps A to C use her coin-flip adoption, D and E our fixed counts.
"""
import copy, time
from pathlib import Path
import numpy as np
import pandas as pd
from ewu import PROCESSED, FLAG_COLUMNS, config_value, read_config, read_inputs
from ewu import deck, deck_money, deck_replica

SCENARIOS = ("moderate", "high")
RERUN = Path("/private/tmp/claude-501/teammate_audit/run")
FIELDS = ("overloaded_pct", "fixed_of_overloaded_pct", "average_units", "winter_of_overloaded_pct", "winter_worst_hour_pct",
          "overloaded", "fixed", "upgrades", "batteries", "ev_homes", "hp_homes")
STEPS = {"a_her_run": "A: her tiers, her groups (seed 11), home-mean fill, 8.064 kWh", "b_our_tiers": "B: our inventory tiers",
         "c_our_groups": "C: + our groups (seed 5), our filled load, 8.06 kWh",
         "d_deck_eligible": "D: our battery plan, shares of eligible homes (default)",
         "e_deck_all_homes": "E: shares of all grouped homes (earlier reading)"}


def shares(scenario, config):
    return config_value(f"scenarios.{scenario}.ev_share", config), config_value(f"scenarios.{scenario}.hp_share", config)


def run_scenarios(setup, config, unit_kwh):
    """{scenario: (per-transformer frame, {limit: cell}, {limit: money})}."""
    out = {}
    for s in SCENARIOS:
        frame = deck_replica.run_replica(setup, config, *shares(s, config), unit_kwh)
        cells = deck_replica.cells_from(frame, config)
        out[s] = (frame, cells, {lim: deck_money.price_deck(c, config) for lim, c in cells.items()})
    return out


def compare_rows(frame, scenario):
    """Transformers whose rating, adopters, flags, units at every limit and winter flag equal her own run's table."""
    path = RERUN / f"ewu_bo2_{scenario.capitalize()}.csv"
    if not path.exists():
        return None
    her = pd.read_csv(path)
    same = (her.rating.to_numpy() == frame.rating.to_numpy()) & (her.nev.to_numpy() == frame.nev.to_numpy())
    same &= (her.nhp.to_numpy() == frame.nhp.to_numpy()) & (her.winter.to_numpy() == frame.winter_major.to_numpy())
    for tag in (100, 110, 120, 140):
        same &= (her[f"o{tag}"].to_numpy() == frame[f"o{tag}"].to_numpy()) & (her[f"u{tag}"].to_numpy() == frame[f"u{tag}"].to_numpy())
    return int(same.sum())


def deck_cells(config, base):
    """Step D or E: our deck engine at 1.20 with the adoption share base switched, nothing else."""
    changed = copy.deepcopy(config)
    changed["profiles"]["deck"]["adoption_share_base"]["value"] = base
    inputs = read_inputs()
    setup = deck.deck_setup(inputs, changed)
    return {s: deck.run_deck(inputs, changed, s, setup, False, [1.2])[0][1.2] for s in SCENARIOS}


def ladder(homes, config):
    """{step: {scenario: cell at 1.20}}, each step one change on top of the one before."""
    steps = {}
    for step, options, kwh in (("a_her_run", {}, deck_replica.replica_value("unit_kwh", config)),
                               ("b_our_tiers", {"tiers": "ours"}, deck_replica.replica_value("unit_kwh", config)),
                               ("c_our_groups", {"tiers": "ours", "groups": "ours", "fill": "ours"}, deck.deck_value("unit_kwh", config))):
        setup = deck_replica.replica_setup(homes, config, **options)
        steps[step] = {s: deck_replica.cells_from(deck_replica.run_replica(setup, config, *shares(s, config), kwh), config)[1.2]
                       for s in SCENARIOS}
    steps["d_deck_eligible"] = deck_cells(config, "eligible_homes")
    steps["e_deck_all_homes"] = deck_cells(config, "all_homes")
    return steps


def seed_spread(config):
    """{scenario: {field: (min, max, mean, sd)}} of the deck profile at 1.20 over seeds 1 to spread_seeds."""
    inputs, found = read_inputs(), {s: {k: [] for k in FIELDS[:5]} for s in SCENARIOS}
    for seed in range(1, deck_replica.replica_value("spread_seeds", config) + 1):
        setup = deck.deck_setup(inputs, config, seed)
        for s in SCENARIOS:
            cell = deck.run_deck(inputs, config, s, setup, False, [1.2])[0][1.2]
            for k in found[s]:
                found[s][k].append(cell[k])
    return {s: {k: (min(v), max(v), float(np.mean(v)), float(np.std(v, ddof=1))) for k, v in by.items()} for s, by in found.items()}


def record_replica(result, rows_equal, steps, spread, tiers, seconds, config):
    from analysis.facts import record, forget
    forget("ewu.deck_replica.")
    how = f"bin/ewu screen --replica: the teammate's ewu_sim_bo2.py rebuilt in ewu/deck_replica.py; tiers {tiers}"
    for s, (_, cells, money) in result.items():
        for lim, cell in cells.items():
            key = f"ewu.deck_replica.{s}.limit_{int(round(lim * 100))}"
            for name in FIELDS:
                record(f"{key}.{name}", cell[name], "", how)
            for column, value in money[lim]["nyseg_musd"].items():
                record(f"{key}.nyseg_{column}_musd", value, "$M across NYSEG", how)
            scale = deck_money.nyseg_scale(cell, config)[0]
            record(f"{key}.nyseg_gross_musd_raw", money[lim]["sample_usd"]["gross"] * scale / 1e6, "$M across NYSEG, unrounded", how)
        if rows_equal.get(s) is not None:
            record(f"ewu.deck_replica.{s}.rows_equal_her_run", rows_equal[s], "of 3,000 transformers, every field equal", how)
    for step, by in steps.items():
        for s, cell in by.items():
            for name in ("overloaded_pct", "fixed_of_overloaded_pct", "average_units", "winter_of_overloaded_pct",
                         "winter_worst_hour_pct", "hp_homes", "ev_homes"):
                record(f"ewu.deck_replica.ladder.{step}.{s}.{name}", cell[name], "", f"{STEPS[step]}; limit 1.20")
    for s, by in spread.items():
        for k, values in by.items():
            for stat, v in zip(("min", "max", "mean", "sd"), values):
                record(f"ewu.deck_replica.spread.{s}.{k}.{stat}", v, "", "battery plan at 1.20, seeds 1 to spread_seeds")
    record("ewu.deck_replica.seconds", round(seconds, 1), "s", how)


def print_replica(result, rows_equal, steps, tiers, config):
    print(f"EWU screen, replica profile: the teammate's ewu_sim_bo2.py followed exactly (groups seed "
          f"{deck_replica.replica_value('grouping_seed', config)}, adoption seed {deck_replica.replica_value('adoption_seed', config)}, home-mean fill, "
          f"167 kVA cap, {deck_replica.replica_value('unit_kwh', config)} kWh, her winter rule)")
    print("Tiers: " + ("the teammate's customer_classification.csv, read in place from her folder, never copied"
                       if tiers == "teammate" else "our inventory flags (Level 2 EV, electric heat)"))
    print("Arrays: ev_start_pmf and hp_increment from the teammate (sha256 checked)\n")
    rows = [("Overloaded, %", "overloaded_pct", "{:.2f}"), ("Fixed without an upgrade, %", "fixed_of_overloaded_pct", "{:.2f}"),
            ("Average units per fixed", "average_units", "{:.2f}"), ("Winter driven (her rule), %", "winter_of_overloaded_pct", "{:.2f}")]
    print(f"{'At 1.20':<30} {'moderate':>10} {'high':>10}")
    for label, name, fmt in rows:
        print(f"{label:<30} " + " ".join(f"{fmt.format(result[s][1][1.2][name]):>10}" for s in SCENARIOS))
    for column in deck_money.COLUMNS:
        print(f"{'NYSEG ' + column.replace('_', ' ') + ', $M':<30} " + " ".join(f"{result[s][2][1.2]['nyseg_musd'][column]:>10.1f}" for s in SCENARIOS))
    if rows_equal:
        print("\nTransformers equal to her own run, every field: " + ", ".join(f"{s} {n:,} of 3,000" for s, n in rows_equal.items()))
    print("\nLadder from her run to our battery plan, overloaded % / fixed % / units / winter % (moderate | high):")
    for step, by in steps.items():
        print(f"  {STEPS[step]:<62} " + " | ".join(
            f"{c['overloaded_pct']:.1f} / {c['fixed_of_overloaded_pct']:.1f} / {c['average_units']:.2f} / {c['winter_of_overloaded_pct']:.1f}"
            for c in by.values()))


def print_spread(spread):
    print("\nBattery plan over seeds 1 to 20, min to max (mean): " + "; ".join(
        f"{s} {k.replace('_of_overloaded', '').replace('_pct', ' %')} {v[0]:.2f} to {v[1]:.2f} ({v[2]:.2f})"
        for s, by in spread.items() for k, v in by.items() if k in ("fixed_of_overloaded_pct", "winter_of_overloaded_pct")))


def main(tiers="teammate"):
    config = read_config()
    started = time.time()
    homes = pd.read_parquet(PROCESSED / "segmented.parquet", columns=FLAG_COLUMNS)
    setup = deck_replica.replica_setup(homes, config, tiers=tiers)
    result = run_scenarios(setup, config, deck_replica.replica_value("unit_kwh", config))
    rows_equal = {s: compare_rows(result[s][0], s) for s in SCENARIOS} if tiers == "teammate" else {}
    rows_equal = {s: n for s, n in rows_equal.items() if n is not None}
    steps, spread = ladder(homes, config), seed_spread(config)
    seconds = time.time() - started
    if tiers == "teammate":
        record_replica(result, rows_equal, steps, spread, tiers, seconds, config)
    print_replica(result, rows_equal, steps, tiers, config)
    print_spread(spread)
    print(f"\n{seconds:.1f} s, aggregates only; {'facts recorded' if tiers == 'teammate' else 'what-if tiers: facts not recorded'}")
    return result, steps
