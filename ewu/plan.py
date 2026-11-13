"""Plan: the engine's action lists, the files a planner and a programs team would actually work from.

What: run_plan() runs the same code path as `bin/ewu screen` for one scenario and sizing and keeps every
      synthetic transformer's state; transformer_table() turns it into one row per transformer (loads, limit,
      driver, action, batteries, placeholder cost, priority); host_table() names each protected transformer's
      fit-score battery hosts; program_rows() lists each home on an actioned transformer with the programs it
      can join; capital_table() prices the three options. write_plan() writes them: transformer level to
      outputs/plan/, real home lists only with --private (outputs/private/plan/), and with --showcase a full
      simulated set (ewu/showcase.py) to outputs/showcase/.
Why:  the product is the engine, not the page. A planner needs a ranked list of transformers and what to do at
      each; a programs team needs the homes to call. The counts must equal the screen a judge watches.
How:  screen.screen_setup and screen.batch_loading, then sensitivity.ladder_states_for_one_run, so no model
      code is rewritten. Feeders follow ewu/network.py's illustrative split. Costs are present values over the
      transformer life at mid placeholder prices (ewu/economics.py), so the column sums to the ladder's total.
"""
import time
from pathlib import Path
import numpy as np
import pandas as pd
from ewu import PROCESSED, ROOT, config_value, read_config, read_inputs
from ewu import attribution, dispatch, economics, fitscore, network, screen, sensitivity, stress

ACTIONS = ("none", "shift", "protect", "upgrade")
OUT, PRIVATE, SHOWCASE = ROOT / "outputs" / "plan", ROOT / "outputs" / "private" / "plan", ROOT / "outputs" / "showcase"
PROGRAMS = {"battery host": ("is_host", "best battery fit on a transformer to protect"),
            "managed charging": ("eligible_managed_charging", "Level 2 EV on an over-limit transformer"),
            "winter demand response": ("eligible_winter_demand_response", "electric heat on an over-limit transformer"),
            "heat pump conversion": ("eligible_heat_pump_conversion", "resistance heat on an over-limit transformer"),
            "smart thermostat": ("eligible_smart_thermostat", "air conditioning on an over-limit transformer")}


def run_plan(inputs, config, scenario, margin, grouping="random", seed=None):
    """Per-transformer ladder states for one scenario and sizing, from the screen's own setup."""
    run = screen.screen_setup(inputs, config, scenario, margin, grouping, seed)
    groups = run["batches"][0]
    base, parts = screen.batch_loading(inputs, run, groups, scenario)
    st = sensitivity.ladder_states_for_one_run(inputs, groups, base, parts, run["config"], run["top"],
                                               run["top_day"])[float(margin)]
    owner = stress.transformer_of_each_home(groups, len(inputs["homes"]))
    return {"run": run, "groups": groups, "base": base, "parts": parts, "st": st, "margin": float(margin),
            "scenario": scenario, "grouping": grouping, "ev_new": np.bincount(owner[parts["ev_homes"]], minlength=groups.count),
            "hp_new": np.bincount(owner[parts["hp_homes"]], minlength=groups.count)}


def ladder_counts(plan):
    """The screen's counts, rebuilt from the per-transformer states (tests hold them equal to bin/ewu screen)."""
    st, n = plan["st"], plan["groups"].count
    flag, protect, need = st["flag"], st["protect"], st["need"]
    return {"transformers": n, "flagged": int(flag.sum()), "shift_fixed": int((flag & ~protect).sum()),
            "protect_set": int(protect.sum()), "new_from_stagger": int((protect & ~flag).sum()),
            "protected": int((need > 0).sum()), "batteries": int(need.sum()), "upgrade_left": int((need == 0).sum()),
            "ev_homes_enrolled": int(plan["ev_new"][flag | protect].sum())}


def main_driver(base, ev, hp, ceiling):
    """At each transformer's worst 2030 hour: the load that leads the overload (fair shares), 'both' when neither
    new load alone crosses the limit; under the limit, the larger new load, or 'base' when none is added."""
    t, h = np.arange(len(ceiling)), (base + ev + hp).argmax(1)
    b, e, p = base[t, h], ev[t, h], hp[t, h]
    shares = attribution.fair_shares(b, e, p, ceiling)
    lead = np.array(["base", "EV", "heat pump"])[np.stack([shares[s] for s in attribution.SOURCES]).argmax(0)]
    over = b + e + p > ceiling
    both = over & (b + e <= ceiling) & (b + p <= ceiling)
    quiet = np.where(e > p, "EV", np.where(p > 0, "heat pump", "base"))
    return np.where(over, np.where(both, "both", lead), quiet), h


def unit_prices(config, case="mid"):
    """Present value over the transformer life of one upgrade, one battery and one enrolled EV home."""
    p = economics.prices_for_case(case, config)
    r, life = p["rate"], p["transformer_life"]
    pv = lambda yearly: economics.present_value_over_years(yearly, r, life)
    return {"upgrade": pv(economics.equal_life_annual_cost(p["upgrade_usd"], r, life)),
            "battery": pv(economics.equal_life_annual_cost(p["battery_unit_usd"], r, p["battery_life"])),
            "enroll": pv(economics.equal_life_annual_cost(p["enroll_usd"], r, life) + p["fee_usd_yr"])}


def transformer_table(plan, config):
    """One row per synthetic transformer: 8-home sums only, so it names no home."""
    st, base, parts, n = plan["st"], plan["base"], plan["parts"], plan["groups"].count
    unmanaged = base + parts["ev"] + parts["hp"]
    ceiling = st["ceiling"]
    driver, worst = main_driver(base, parts["ev"], parts["hp"], ceiling)
    state = network.final_state(st["flag"], st["protect"], st["batteries"])
    hosts, units = np.zeros(n, dtype=int), np.zeros(n, dtype=int)
    ids = st["setup"]["flagged"][st["rows"]]
    hosts[ids], units[ids] = network.chosen_option(st["placed"], st["need"], config)
    price = unit_prices(config)
    enrolled = np.where(st["flag"] | st["protect"], plan["ev_new"], 0)
    cost = np.select([state == 1, state == 2, state == 3],
                     [enrolled * price["enroll"], enrolled * price["enroll"] + st["batteries"] * price["battery"],
                      enrolled * price["enroll"] + price["upgrade"]], 0.0)
    stamps = pd.read_parquet(PROCESSED / "weather.parquet").index
    table = pd.DataFrame({
        "transformer_id": [f"T-{i + 1:04d}" for i in range(n)],
        "feeder_id": [f"F{f + 1}" for f in network.feeder_of(n, config_value("network.feeders", config))],
        "homes": np.bincount(plan["groups"].transformer, minlength=n), "new_evs_2030": plan["ev_new"],
        "new_heat_pumps_2030": plan["hp_new"], "today_peak_kw": base.max(1).round(2),
        "rating_kw": (ceiling / config_value("transformer.overload_limit", config)).round(2),
        "limit_kw": ceiling.round(2), "worst_2030_kw": unmanaged.max(1).round(2),
        "worst_2030_hour": stamps[worst].strftime("%Y-%m-%d %H:00"), "over_limit": st["flag"],
        "hours_over": (unmanaged > ceiling[:, None]).sum(1), "main_driver": driver,
        "action": np.array(ACTIONS)[state], "battery_hosts": hosts, "units_per_host": units,
        "batteries_needed": st["batteries"], "est_cost_usd": cost.round(0).astype(int)})
    severity = -state - unmanaged.max(1) / ceiling / 1000   # upgrade, protect, shift, none; worst ratio first in each
    table["priority"] = pd.Series(severity).rank(method="first").astype(int).to_numpy()
    return table.sort_values("priority").reset_index(drop=True)


def host_table(plan, inputs, config):
    """Real fit-score hosts per protected transformer: rank, customer number, fit and kW cut in the top hours."""
    st, top, top_day = plan["st"], plan["run"]["top"], plan["run"]["top_day"]
    setup, rows = st["setup"], st["rows"]
    hosts, units = network.chosen_option(st["placed"], st["need"], config)
    out = []
    for h, u in sorted({(int(a), int(b)) for a, b in zip(hosts, units) if a}):
        pick = rows[(hosts == h) & (units == u)]
        spec = dispatch.battery_spec(u, config)
        scores = fitscore.fit_score(setup["home_kw"][:, :, top], top_day, spec)
        chosen = fitscore.choose_hosts("fit_score", scores, None, None, h, None)[pick]
        for rank in range(h):
            cut = scores[pick, chosen[:, rank]]
            out.append(pd.DataFrame({"transformer_id": [f"T-{t + 1:04d}" for t in setup["flagged"][pick]],
                                     "rank": rank + 1, "home_row": setup["homes"][pick, chosen[:, rank]],
                                     "fit_score": (cut / spec["power_kw"]).round(3), "kw_cut_top_hours": cut.round(2),
                                     "units": u}))
    table = pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["transformer_id", "rank", "home_row"])
    table.insert(2, "home_id", inputs["homes"]["CUSTOMER_NUMBER"].to_numpy()[table["home_row"].astype(int)].astype(str))
    return table.drop(columns="home_row").sort_values(["transformer_id", "rank"]).reset_index(drop=True)


def program_rows(homes, hosts, transformers):
    """Homes on transformers with an action, the programs each can join and why; works on real or simulated homes."""
    acted = transformers[transformers.action != "none"].set_index("transformer_id")
    homes = homes[homes.transformer_id.isin(acted.index)].copy()
    homes["is_host"] = homes.home_id.isin(set(hosts.home_id))
    names = [name for name, (flag, _) in PROGRAMS.items() if flag in homes]
    picked = np.stack([homes[PROGRAMS[name][0]].to_numpy(bool) for name in names], 1)
    homes = homes[picked.any(1)]
    picked = picked[picked.any(1)]
    first = picked.argmax(1)
    return pd.DataFrame({"home_id": homes.home_id.to_numpy(), "transformer_id": homes.transformer_id.to_numpy(),
                         "segment": homes.segment.to_numpy(),
                         "programs": ["; ".join(n for n, on in zip(names, row) if on) for row in picked],
                         "reason": [PROGRAMS[names[i]][1] for i in first],
                         "priority": acted.loc[homes.transformer_id, "priority"].to_numpy()}
                        ).sort_values(["priority", "home_id"]).reset_index(drop=True)


def capital_table(counts, config):
    """One row per option, present value over the transformer life and share of upgrading every flag, per price case."""
    what = {"upgrade_all": "upgrade every flagged transformer",
            "shift_then_upgrade": "managed charging, then upgrade what is still over",
            "ladder": "managed charging, home batteries, upgrade what is left"}
    upgraded = {"upgrade_all": counts["flagged"], "shift_then_upgrade": counts["protect_set"], "ladder": counts["upgrade_left"]}
    priced = {case: economics.cost_the_ladder(counts, economics.prices_for_case(case, config)) for case in economics.PRICE_CASES}
    rows = [{"option": o, "what": what[o], "transformers_upgraded": upgraded[o],
             "batteries": counts["batteries"] if o == "ladder" else 0,
             "ev_homes_enrolled": 0 if o == "upgrade_all" else counts["ev_homes_enrolled"],
             **{f"pv_usd_{c}": round(priced[c]["present_usd"][o]) for c in priced},
             **{f"share_of_upgrade_all_pct_{c}": priced[c]["share_of_upgrade_all_pct"][o] for c in priced},
             "prices": "placeholder"} for o in economics.STRATEGIES]
    return pd.DataFrame(rows)


def write_csv(table, path, note):
    """A CSV whose first line is a '#' note saying what the file is (read with pandas comment='#')."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {note}\n" + table.to_csv(index=False))
    return path
