"""Screen: the live answer for one scenario and one sizing, Flag, Shift, Protect, Upgrade, in under a minute.

What: run_screen() loads the full meter data, groups homes into transformers (synthetic, or a real map with
      `--map`), adds the 2030 EVs and heat pumps and runs the ladder at one sizing margin: transformers over
      the limit with unmanaged charging (Flag), those staggered charging fixes (Shift), those fit-score
      batteries clear (Protect) and those left for an upgrade (Upgrade); price_screen() prices that split;
      record_screen() writes it to facts; print_screen() prints aggregates only.
Why:  the demo needs one command a judge can watch run on the real data, not a cached chart. It is the same
      code the sensitivity grid runs, cut to one cell and one seed so it answers in seconds.
How:  sensitivity.ladder_for_one_run() with the config's margins replaced by the one asked for. A real map
      may hold transformers with different numbers of homes; each group size runs as its own batch and the
      counts are added, so no other module changes. With a map the rating still follows today's peak times
      the margin; nameplate kVA would need a power factor nobody has given us yet.
"""
import copy
import numpy as np
from ewu import config_value
from ewu import adoption, economics, feeders as feeder_groups, sensitivity, stress


def config_for_margin(config, margin):
    """A copy of the config whose sizing margins hold only `margin`."""
    one = copy.deepcopy(config)
    one["transformer"]["sizing_margins"]["value"] = [float(margin)]
    return one


def groups_by_size(feeders):
    """Split a map's transformers into batches that all hold the same number of homes."""
    sizes = np.bincount(feeders.transformer, minlength=feeders.count)
    order = np.argsort(feeders.transformer, kind="stable")
    homes_sorted = feeders.homes[order]
    starts = np.concatenate([[0], np.cumsum(sizes)[:-1]])
    batches = []
    for size in np.unique(sizes[sizes > 0]):
        picked = np.flatnonzero(sizes == size)
        rows = np.concatenate([homes_sorted[starts[t]:starts[t] + size] for t in picked])
        batches.append(feeder_groups.Feeders(rows, np.repeat(np.arange(len(picked)), size), len(picked)))
    return batches


def run_screen(inputs, config, scenario, margin, grouping="random", seed=None, map_path=None):
    """Pooled ladder counts and shares for one scenario, margin and grouping (or a real map)."""
    one = config_for_margin(config, margin)
    seed = config_value("demo.screen_seed", config) if seed is None else seed
    sessions = adoption.measure_ev_sessions(inputs["load"], inputs["homes"]["is_ev_l2"], inputs["temp"], config)
    top, top_day = sensitivity.top_hours_and_days(config)
    if map_path:
        batches = groups_by_size(feeder_groups.load_map(map_path, inputs["homes"]["CUSTOMER_NUMBER"].astype(str)))
    else:
        k = config_value("transformer.homes_per_transformer", config)
        batches = [feeder_groups.build_transformers(inputs["homes"]["segment"].to_numpy(), k,
                                                    config_value("transformer.count", config), grouping, seed)]
    total = {}
    for groups in batches:
        base = stress.base_loading(inputs["load"], groups)
        parts = stress.loading_parts(inputs, groups, scenario, seed, one, sessions, base)
        counts = sensitivity.ladder_for_one_run(inputs, groups, base, parts, one, top, top_day)[float(margin)]
        for name, value in counts.items():
            total[name] = total.get(name, 0) + value
    cell = sensitivity.summarize_ladder({(scenario, grouping, float(margin), seed): total})
    return next(iter(cell.values())) | {"homes": int(sum(len(g.homes) for g in batches)),
                                        "map": bool(map_path), "seed": seed}


def price_screen(cell, config):
    """The ladder's equal-life cost as a share of upgrading every flagged transformer, per price case."""
    return {case: economics.cost_the_ladder(cell, economics.prices_for_case(case, config))["share_of_upgrade_all_pct"]
            for case in economics.PRICE_CASES}


def record_screen(cell, money, scenario, grouping, margin, seconds):
    """The live run's shares and cost to facts/facts.json (synthetic transformers only, never a map)."""
    from analysis.facts import record
    key = f"ewu.screen.{scenario}.{grouping}.{stress.margin_label(margin)}"
    how = f"one seed ({cell['seed']}), {cell['transformers']} synthetic transformers, rating = today's peak x {margin}"
    for name, value in cell["shares"].items():
        record(f"{key}.{name}", value, "% of all transformers" if name.endswith("_pct") and name != "protected_of_set_pct"
               else "% of transformers still over with staggered charging" if name == "protected_of_set_pct" else "ratio", how)
    for case, shares in money.items():
        record(f"{key}.{case}.ladder_share_pct", shares["ladder"], "% of upgrading every flagged transformer", how)
    for name in ("transformers", "homes", "flagged", "shift_fixed", "protected", "upgrade_left", "batteries"):
        record(f"{key}.{name}", cell[name], "homes" if name == "homes" else "batteries" if name == "batteries"
               else "transformers", how)
    record(f"{key}.seconds", round(seconds, 1), "s", "whole live screen, data load included")


def print_screen(cell, money, scenario, grouping, margin, seconds):
    s = cell["shares"]
    source = "real transformer map" if cell["map"] else f"{grouping} grouping, seed {cell['seed']}"
    print(f"EWU screen: {scenario} 2030, rating = today's peak x {margin:.2f}, {cell['transformers']:,} transformers "
          f"({source}), {cell['homes']:,} homes\n")
    rows = [("Flag", "over the limit, EV charging unmanaged", s["flagged_pct"], cell["flagged"]),
            ("Shift", "fixed by staggered EV charging", s["shift_fixed_pct"], cell["shift_fixed"]),
            ("Protect", "cleared by fit-score home batteries", s["protected_pct"], cell["protected"]),
            ("Upgrade", "left for a transformer upgrade", s["upgrade_left_pct"], cell["upgrade_left"])]
    print(f"{'step':<8} {'what':<40} {'% of transformers':>17} {'transformers':>12}")
    for step, what, pct, count in rows:
        print(f"{step:<8} {what:<40} {pct:>17.2f} {count:>12,}")
    print(f"\nStaggering newly overloads {s['new_from_stagger_pct']:.2f}% of transformers; they join Protect or Upgrade.")
    print(f"Batteries: {cell['batteries']:,} units, {s['batteries_per_protected']:.2f} per protected transformer.")
    print("Ladder cost as % of upgrading every flagged transformer (equal life): " +
          ", ".join(f"{case} prices {m['ladder']:.2f}%" for case, m in money.items()))
    print(f"\n{seconds:.1f} s, full meter data, aggregates only")

