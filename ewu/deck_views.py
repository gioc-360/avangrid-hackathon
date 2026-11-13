"""Deck views: `bin/ewu network` and `bin/ewu plan` under the deck profile, transformer by transformer.

What: deck_states() runs one deck scenario at one limit and keeps every synthetic transformer's state (within,
      protected by 1 to 4 units, upgrade); network_main() records the per-view counts; plan_table() writes the
      planner's action list and capital_rows() the three money columns plus upgrade-all, to outputs/plan/deck/.
Why:  the deck profile is the default, so the network and plan commands must give the deck's own transformer
      states and counts, equal to `bin/ewu screen`; the earlier ladder stays under --profile cautious.
How:  the same setup and run as ewu/deck_screen.py (ewu/deck.py), so counts equal the screen by construction.
      There is no Shift step in the deck's battery-only fix order. A transformer's cost is the Avangrid cost of
      its units (unit price less lease and NYSERDA present values) or one upgrade counted 15 of 40 years.
      Main driver is ewu/plan.main_driver at the worst hour. The CSVs hold 8-home sums only and stay local.
"""
import time
import numpy as np
import pandas as pd
from ewu import PROCESSED, ROOT, config_value, read_config, read_inputs
from ewu import deck, deck_money, network, plan

OUT = ROOT / "outputs" / "plan" / "deck"
ACTIONS = ("none", "protect", "upgrade")


def deck_states(inputs, config, scenario, limit, managed=None):
    """Per-transformer arrays and the cell for one scenario and limit, from the screen's own run."""
    setup = deck.deck_setup(inputs, config)
    cells, parts = deck.run_deck(inputs, config, scenario, setup, managed, [limit])
    cell = cells[float(limit)]
    st = cell["state"]
    action = np.where(st["fixed"], 1, np.where(st["over"], 2, 0))
    return {"setup": setup, "cell": cell, "parts": parts, "action": action, "units": np.where(st["fixed"], st["units"], 0),
            "over_today": (setup["base"] > st["ceiling"][:, None]).any(1), "scenario": scenario, "limit": float(limit)}


def view_counts(states):
    """{view: {word: transformers}}: today, 2030 with no action, after batteries, after upgrades."""
    a, today = states["action"], states["over_today"]
    words = {"today": np.where(today, "over", "within"), "flag": np.where(a > 0, "over", "within"),
             "protect": np.select([a == 1, a == 2], ["protected", "over"], "within"),
             "upgrade": np.select([a == 1, a == 2], ["protected", "upgrade"], "within")}
    return {view: {"within": 0} | {str(w): int(n) for w, n in zip(*np.unique(w_, return_counts=True))}
            for view, w_ in words.items()}


def network_main(scenario=None, limit=None, managed=None):
    config = read_config()
    scenario = scenario or config_value("demo.scenario", config)
    limit = float(config_value("profiles.deck.overload_limit", config) if limit is None else limit)
    started = time.time()
    states = deck_states(read_inputs(), config, scenario, limit, managed)
    counts = view_counts(states)
    official = limit == config_value("profiles.deck.overload_limit", config) and not states["cell"]["managed"]
    if official:
        from analysis.facts import record
        how = f"deck profile, {scenario} 2030, limit {limit} x standard kVA rating, seed {states['setup']['seed']}; same run as bin/ewu screen"
        for view, words in counts.items():
            for word, n in words.items():
                record(f"ewu.deck.network.{scenario}.{view}.{word}", n, "transformers", how)
    print(f"Network, deck profile: {states['setup']['groups'].count:,} synthetic transformers, {scenario} 2030, limit {limit:.2f}")
    for view, words in counts.items():
        print(f"  {view:<8} " + ", ".join(f"{w} {n:,}" for w, n in words.items()))
    print(f"{time.time() - started:.1f} s, aggregates only; {'facts recorded' if official else 'what-if: facts not recorded'}")
    return counts


def plan_table(states, config):
    """One row per synthetic transformer: 8-home sums only."""
    setup, parts, st = states["setup"], states["parts"], states["cell"]["state"]
    base, ev, hp, ceiling = setup["base"], parts["ev"], parts["hp"], st["ceiling"]
    total = base + ev + hp
    n, owner = setup["groups"].count, setup["owner"]
    driver, worst = plan.main_driver(base, ev, hp, ceiling)
    p = deck_money.deck_prices(config)
    per_unit = p["unit_usd"] - p["lease_pv_usd"] - p["nyserda_usd"]
    cost = np.select([states["action"] == 1, states["action"] == 2], [states["units"] * per_unit, p["upgrade_counted_usd"]], 0.0)
    stamps = pd.read_parquet(PROCESSED / "weather.parquet").index
    table = pd.DataFrame({
        "transformer_id": [f"T-{i + 1:04d}" for i in range(n)],
        "feeder_id": [f"F{f + 1}" for f in network.feeder_of(n, config_value("network.feeders", config))],
        "homes": np.bincount(setup["groups"].transformer, minlength=n),
        "new_evs_2030": np.bincount(owner[parts["ev_homes"]], minlength=n),
        "new_heat_pumps_2030": np.bincount(owner[parts["hp_homes"]], minlength=n),
        "today_peak_kw": base.max(1).round(2), "rating_kva": setup["rating"], "limit_kw": ceiling.round(2),
        "worst_2030_kw": total.max(1).round(2), "worst_2030_hour": stamps[worst].strftime("%Y-%m-%d %H:00"),
        "over_limit": st["over"], "hours_over": (total > ceiling[:, None]).sum(1), "main_driver": driver,
        "action": np.array(ACTIONS)[states["action"]], "units": states["units"], "avangrid_cost_usd": cost.round(0).astype(int)})
    severity = -states["action"] - total.max(1) / ceiling / 1000
    table["priority"] = pd.Series(severity).rank(method="first").astype(int).to_numpy()
    return table.sort_values("priority").reset_index(drop=True)


def capital_rows(states, config):
    money = deck_money.price_deck(states["cell"], config)
    return pd.DataFrame([{"column": c, "sample_usd": round(money["sample_usd"][c]), "nyseg_musd": money["nyseg_musd"][c]}
                         for c in deck_money.COLUMNS])


def plan_main(scenario=None, limit=None, managed=None):
    config = read_config()
    scenario = scenario or config_value("demo.scenario", config)
    limit = float(config_value("profiles.deck.overload_limit", config) if limit is None else limit)
    started = time.time()
    states = deck_states(read_inputs(), config, scenario, limit, managed)
    table, capital = plan_table(states, config), capital_rows(states, config)
    note = (f"deck profile, {scenario} 2030, limit {limit} x standard kVA rating; synthetic transformers, 8-home sums; "
            "costs are Avangrid cost (units net of lease and NYSERDA) or an upgrade counted 15 of 40 years")
    paths = [plan.write_csv(table, OUT / "transformer_actions.csv", note), plan.write_csv(capital, OUT / "capital_plan.csv", note)]
    counts = table.action.value_counts()
    if limit == config_value("profiles.deck.overload_limit", config) and not states["cell"]["managed"]:
        from analysis.facts import record
        for action in ACTIONS:
            record(f"ewu.deck.plan.{scenario}.actions.{action}", int(counts.get(action, 0)), "transformers", note)
        record(f"ewu.deck.plan.{scenario}.avangrid_cost_total_usd", int(table.avangrid_cost_usd.sum()), "$ for the sample", note)
    print(f"EWU plan, deck profile: {scenario} 2030, limit {limit:.2f}, {len(table):,} transformers")
    for action in ACTIONS:
        on = table.action == action
        print(f"{action:<8} {int(on.sum()):>6,} transformers {int(table.units[on].sum()):>6,} units ${int(table.avangrid_cost_usd[on].sum()):>12,}")
    for path in paths:
        print(f"written  {path.relative_to(ROOT)}")
    print(f"{time.time() - started:.1f} s, transformer-level only, stays local")
    return table
