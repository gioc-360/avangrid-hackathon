"""Deck screen: `bin/ewu screen` under the deck profile, both scenarios, every overload limit, money and peak cut.

What: run_deck_screen() runs ewu/deck.py for moderate and high 2030 at every overload limit option, prices each
      cell (ewu/deck_money.py) and measures the peak cut (ewu/peakcut.py); record_deck_screen() writes the
      aggregates to facts under ewu.deck; print_deck_screen() prints the deck's table, aggregates only.
Why:  the final deck's numbers must come from one command a judge can watch run, side by side with the
      teammate's targets, and every one must reach a doc only through facts.
How:  one shared setup (transformers, ratings, arrays) for both scenarios, so moderate and high run on the same
      homes. Managed charging is the optional scenario: with --managed its facts go under ewu.deck.managed so
      the default record is never overwritten. The arrays' origin (teammate or derived) is recorded and printed.
"""
import time
from ewu import config_value, read_config, read_inputs
from ewu import deck, deck_money, peakcut

FIELDS = {"overloaded_pct": "% of transformers", "fixed_of_overloaded_pct": "% of overloaded transformers",
          "average_units": "IQ 10C units per battery-fixed transformer", "winter_of_overloaded_pct": "% of overloaded transformers",
          "winter_worst_hour_pct": "% of overloaded transformers", "winter_majority_hours_pct": "% of overloaded transformers",
          "overloaded": "transformers", "fixed": "transformers", "upgrades": "transformers", "batteries": "IQ 10C units",
          "ev_homes": "homes", "hp_homes": "homes",
          "fixed_units_1_2": "transformers fixed by 1 or 2 IQ 10C units", "fixed_units_3_4": "transformers fixed by 3 or 4 IQ 10C units"}


SHARES = {"fixed_units_1_2_pct": ("fixed_units_1_2", "transformers"), "fixed_units_3_4_pct": ("fixed_units_3_4", "transformers"),
          "upgrades_pct": ("upgrades", "transformers"), "upgrade_of_overloaded_pct": ("upgrades", "overloaded")}
# the money columns in deck v3's words (docs/TERMS.md); the keys stay the fact names
INPUT_WORDS = {"ev_start_pmf": "EV start-hour shares", "hp_increment": "heat pump curve"}
MONEY_WORDS = {"gross": "gross cost", "net_without_nyserda": "net cost without NYSERDA", "avangrid_cost": "net cost",
               "upgrade_all": "Upgrade all"}


def band_shares(cell):
    """Slide 12's bars as % of all transformers (fixed by 1 or 2 units, by 3 or 4, upgrade) and upgrades as % of overloaded."""
    return {name: deck.percent_of(cell[part], cell[whole]) for name, (part, whole) in SHARES.items()}


def limit_label(limit):
    return f"limit_{int(round(limit * 100))}"


def run_deck_screen(inputs, config, managed=None):
    """{'cells': {(scenario, limit): cell}, 'money': {...}, 'peak': {...}, 'setup': ...} for the deck profile."""
    setup = deck.deck_setup(inputs, config)
    cells, money = {}, {}
    for scenario in deck.SCENARIOS:
        by_limit, _ = deck.run_deck(inputs, config, scenario, setup, managed)
        for limit, cell in by_limit.items():
            cells[(scenario, limit)] = cell
            money[(scenario, limit)] = deck_money.price_deck(cell, config)
    return {"cells": cells, "money": money, "peak": peakcut.run_peak_cut(inputs, config), "setup": setup,
            "managed": deck.deck_value("managed_charging", config) if managed is None else managed}


def record_deck_screen(result, seconds):
    """Aggregates only to facts/facts.json."""
    from analysis.facts import record
    setup, root = result["setup"], "ewu.deck.managed" if result["managed"] else "ewu.deck"
    how = (f"battery plan, seed {setup['seed']}, {setup['groups'].count} synthetic transformers, standard kVA rating; "
           f"ev_start_pmf {setup['origins']['ev_start_pmf']}, hp_increment {setup['origins']['hp_increment']}")
    for (scenario, limit), cell in result["cells"].items():
        key = f"{root}.{scenario}.{limit_label(limit)}"
        for name, unit in FIELDS.items():
            record(f"{key}.{name}", cell[name], unit, how)
        for name, value in band_shares(cell).items():
            record(f"{key}.{name}", value, f"% of {SHARES[name][1]}", how)
        m = result["money"][(scenario, limit)]
        for column, value in m["nyseg_musd"].items():
            record(f"{key}.nyseg_{column}_musd", value, "$M across NYSEG", "15 years at 7%, upgrade counted 15 of 40 years; " + how)
        record(f"{key}.nyseg_batteries", m["nyseg_batteries"], "IQ 10C units across NYSEG", how)
        record(f"{key}.avangrid_share_of_upgrade_all_pct", m["avangrid_share_of_upgrade_all_pct"], "% of upgrading every overloaded transformer", how)
        record(f"{key}.saving_vs_upgrade_all_pct", m["saving_vs_upgrade_all_pct"], "% less than upgrading every overloaded transformer",
               "1 - Avangrid cost / upgrade-all, present value basis; " + how)
    if result["managed"]:
        return
    prices = next(iter(result["money"].values()))
    for name in ("factor", "life_factor", "upgrade_counted_usd", "lease_pv_usd"):
        record(f"ewu.deck.prices.{name}", round(prices["prices"][name], 3), "$" if name.endswith("usd") else "present value factor", "ewu/deck_money.py")
    record("ewu.deck.nyseg_transformers", prices["nyseg_transformers"], "transformers", "NYSEG electric customers / 8 homes per transformer")
    record("ewu.deck.rating.above_largest", setup["above_largest"], "transformers", "groups needing more than 167 kVA; given multiple units")
    for size in sorted(set(setup["rating"].tolist())):
        record(f"ewu.deck.rating.kva_{str(size).replace('.', '_')}", int((setup["rating"] == size).sum()), "transformers", how)
    for name, origin in setup["origins"].items():
        record(f"ewu.deck.arrays.{name}", origin, "", "teammate = their file in data/processed; derived = built from our data")
    for name, value in result["peak"].items():
        record(f"ewu.deck.peakcut.{name}", value, "MW" if name.endswith("_mw") else name, "ewu/peakcut.py, top hours of the metered system load")
    record("ewu.deck.seconds", round(seconds, 1), "s", "whole battery plan screen, data load included")


def peak_cut_line(config):
    """Deck v3's summer peak cut: the teammate's priority homes, her ranking rerun on our data (checks/teammate_audit.py)."""
    import json
    from analysis.facts import FACTS
    facts = json.loads(FACTS.read_text()) if FACTS.exists() else {}
    keys = ("teammate.audit.rerun.priority_homes", "teammate.audit.rerun.fleet_priority.peak_cut_mw",
            "teammate.audit.rerun.fleet_priority.top50_cut_mw")
    if any(k not in facts for k in keys):
        return "Summer peak cut: not recorded yet; run checks/teammate_audit.py"
    homes, peak, top = (facts[k]["value"] for k in keys)
    return (f"Summer peak cut, {homes:,} priority homes x {config_value('profiles.deck.units_per_host', config)} units, "
            f"the teammate's ranking rerun on our data: export allowed {peak:.2f} MW off the yearly peak "
            f"(mean over the top {config_value('profiles.deck.peak_hours', config)} hours {top:.2f} MW)")


def print_deck_screen(result, config, limit, seconds):
    setup = result["setup"]
    print(f"EWU screen, battery plan: {setup['groups'].count:,} synthetic transformers, 8 random homes, seed {setup['seed']}, "
          f"standard kVA rating, overloaded above {limit:.2f} x rating; managed charging {'on' if result['managed'] else 'off'}")
    origins = set(setup["origins"].values())
    print("The teammate's EV start-hour shares and heat pump curve: " + (deck.array_label(origins.pop()) if len(origins) == 1 else
          "; ".join(f"{INPUT_WORDS.get(name, name)} {deck.array_label(origin)}" for name, origin in setup["origins"].items())) + "\n")
    rows = [("Overloaded, % of transformers", "overloaded_pct", "{:.1f}"), ("Fixed by batteries, %", "fixed_of_overloaded_pct", "{:.1f}"),
            ("Average units per fixed", "average_units", "{:.2f}"), ("Winter nights, % of overloaded", "winter_of_overloaded_pct", "{:.1f}")]
    print(f"{'':<34} {'moderate':>10} {'high':>10}")
    for label, name, fmt in rows:
        print(f"{label:<34} " + " ".join(f"{fmt.format(result['cells'][(s, limit)][name]):>10}" for s in deck.SCENARIOS))
    for column in deck_money.COLUMNS:
        print(f"{'NYSEG ' + MONEY_WORDS[column] + ', $M':<34} "
              + " ".join(f"{result['money'][(s, limit)]['nyseg_musd'][column]:>10.1f}" for s in deck.SCENARIOS))
    print("\nOverloaded % by loading limit: " + "; ".join(
        f"{lim:.2f}: "
        + "/".join(f"{result['cells'][(s, lim)]['overloaded_pct']:.1f}" for s in deck.SCENARIOS)
        for lim in config_value("profiles.deck.overload_limit_options", config)))
    print(peak_cut_line(config))
    print(f"\n{seconds:.1f} s, full meter data, aggregates only")


def main(limit=None, managed=None):
    config = read_config()
    limit = float(config_value("profiles.deck.overload_limit", config) if limit is None else limit)
    started = time.time()
    result = run_deck_screen(read_inputs(), config, managed)
    seconds = time.time() - started
    record_deck_screen(result, seconds)
    print_deck_screen(result, config, limit, seconds)
    return result
