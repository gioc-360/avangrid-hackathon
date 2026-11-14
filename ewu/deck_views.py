"""Deck views: `bin/ewu network` and `bin/ewu plan` under the deck profile, transformer by transformer.

What: deck_states() runs one deck scenario at one limit and keeps every synthetic transformer's state (within,
      protected by 1 to 4 units, upgrade); network_main() records the per-view counts; plan_table() writes the
      planner's action list and capital_rows() the three money columns plus upgrade-all, to outputs/plan/battery/.
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

OUT = ROOT / "outputs" / "plan" / "battery"
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


PRIVATE = ("state", "flag", "over_today", "units", "units_needed", "feeder", "limit_kw", "day", "peak_hour_of_day",
           "base_kw", "ev_kw", "hp_kw", "after_kw", "peak_base_kw", "peak_ev_kw", "peak_hp_kw", "peak_kw", "excess_kw")
INTS = ("state", "flag", "over_today", "units", "units_needed", "feeder", "day", "peak_hour_of_day")


def network_arrays(states, config):
    """Per synthetic transformer (8-home sums) for the page's Network view: state 0 within, 2 protected, 3 upgrade
    (the cautious codes, no 1 since the deck has no Shift step), units, and the worst 2030 day by hour. After is the
    load capped at the limit for a protected transformer: the battery sizing rule covers every day's excess."""
    setup, parts, st = states["setup"], states["parts"], states["cell"]["state"]
    base, ev, hp, ceiling = setup["base"], parts["ev"], parts["hp"], st["ceiling"]
    total, n = base + ev + hp, setup["groups"].count
    worst, rows = st["worst_hour"], np.arange(n)
    day = worst // 24
    after = np.where(st["fixed"][:, None], np.minimum(total, ceiling[:, None]), total)
    at = lambda series: np.round(series[rows, worst], 1)
    return {"state": np.select([states["action"] == 1, states["action"] == 2], [2, 3], 0), "flag": states["action"] > 0,
            "over_today": states["over_today"], "units": states["units"], "units_needed": np.where(st["over"], st["units"], 0),
            "feeder": network.feeder_of(n, config_value("network.feeders", config)), "limit_kw": np.round(ceiling, 1),
            "day": day, "peak_hour_of_day": worst % 24, "base_kw": network.day_rows(base, day), "ev_kw": network.day_rows(ev, day),
            "hp_kw": network.day_rows(hp, day), "after_kw": network.day_rows(after, day), "peak_base_kw": at(base),
            "peak_ev_kw": at(ev), "peak_hp_kw": at(hp), "peak_kw": at(total), "excess_kw": np.round(np.maximum(at(total) - ceiling, 0), 1)}


def record_network(states, counts, config, name):
    """Counts to facts under ewu.<name>.<scenario>.; per-transformer arrays to the private facts only, ewu.<name>.t."""
    from analysis.facts import forget, record
    scenario, limit = states["scenario"], states["limit"]
    how = (f"battery plan, {scenario} 2030, limit {limit} x standard kVA rating, seed {states['setup']['seed']}"
           f"{', managed charging (optional)' if states['cell']['managed'] else ''}; same run as bin/ewu screen")
    forget(f"ewu.{name}.{scenario}.")
    for view, words in counts.items():
        for word, n in words.items():
            record(f"ewu.{name}.{scenario}.{view}.{word}", n, "transformers", how)
    record(f"ewu.{name}.transformers_drawn", int(states["setup"]["groups"].count), "transformers", how)
    record(f"ewu.{name}.homes", int(len(states["setup"]["groups"].homes)), "homes", "homes in the drawn transformers")
    arrays = network_arrays(states, config)
    forget(f"ewu.{name}.t.", private=True)
    for field in PRIVATE:
        record(f"ewu.{name}.t.{field}", np.asarray(arrays[field]).astype(int if field in INTS else float).tolist(),
               "kW" if field.endswith("_kw") else "", "per synthetic transformer, 8 homes summed; " + how, private=True)


def network_main(scenario=None, limit=None, managed=None):
    config = read_config()
    scenario = scenario or config_value("demo.scenario", config)
    limit = float(config_value("profiles.deck.overload_limit", config) if limit is None else limit)
    started = time.time()
    states = deck_states(read_inputs(), config, scenario, limit, managed)
    counts = view_counts(states)
    official = limit == config_value("profiles.deck.overload_limit", config) and not states["cell"]["managed"]
    if official:
        record_network(states, counts, config, "deck.network")
        managed_states = deck_states(read_inputs(), config, scenario, limit, True)   # the optional scenario, for the page
        record_network(managed_states, view_counts(managed_states), config, "deck.network_managed")
    print(f"Network, battery plan: {states['setup']['groups'].count:,} synthetic transformers, {scenario} 2030, loading limit {limit:.2f}")
    for view, words in counts.items():
        print(f"  {SHOW.get(view, view):<8} " + ", ".join(f"{SHOW.get(w, w)} {n:,}" for w, n in words.items()))
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
    note = (f"battery plan, {scenario} 2030, limit {limit} x standard kVA rating; synthetic transformers, 8-home sums; "
            "costs are net cost (units net of lease and NYSERDA) or an upgrade counted 15 of 40 years")
    paths = [plan.write_csv(table, OUT / "transformer_actions.csv", note), plan.write_csv(capital, OUT / "capital_plan.csv", note)]
    counts = table.action.value_counts()
    if limit == config_value("profiles.deck.overload_limit", config) and not states["cell"]["managed"]:
        from analysis.facts import record
        for action in ACTIONS:
            record(f"ewu.deck.plan.{scenario}.actions.{action}", int(counts.get(action, 0)), "transformers", note)
        record(f"ewu.deck.plan.{scenario}.avangrid_cost_total_usd", int(table.avangrid_cost_usd.sum()), "$ for the sample", note)
    print(f"EWU plan, battery plan: {scenario} 2030, loading limit {limit:.2f}, {len(table):,} transformers")
    for action in ACTIONS:
        on = table.action == action
        print(f"{SHOW.get(action, action):<8} {int(on.sum()):>6,} transformers {int(table.units[on].sum()):>6,} units ${int(table.avangrid_cost_usd[on].sum()):>12,}")
    for path in paths:
        print(f"written  {path.relative_to(ROOT)}")
    print(f"{time.time() - started:.1f} s, transformer-level only, stays local")
    return table


# words the printouts show for the state and action identifiers (docs/TERMS.md)
SHOW = {"protect": "place", "protected": "fixed by batteries", "over": "overloaded", "within": "within limit"}
