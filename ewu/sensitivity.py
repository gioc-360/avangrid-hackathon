"""Sensitivity: the Flag, Shift, Protect, Upgrade ladder in every cell of the grid, ready for the money step.

What: ladder_for_one_run() takes one seed's transformers in one scenario and, at every sizing margin, counts
      the transformers overloaded with unmanaged EV charging (Flag), those staggered charging fixes (Shift),
      those fit-score batteries clear (Protect), those left for an upgrade (Upgrade), the batteries used and
      the EV homes enrolled in staggered charging; run_sensitivity() does that for 2 scenarios x 2 grouping
      modes x the config's seeds, which covers 2 x 4 x 2 = 16 cells; summarize_ladder() pools the seeds;
      record_ladder() writes every cell's shares to facts. ewu/economics.py prices the pooled counts.
Why:  judges asked how much the answer moves with transformer sizing and with clustered neighbors (plan
      objections 2 and 3), and the money only means something next to the range of outcomes behind it.
How:  the same transformers, adoption and EV sessions as M1 to M4 (same seeds). Flag uses M1's rule (any hour
      above the limit, unmanaged). Shift is M2's staggered charging; a transformer still over with it goes to
      Protect, where each of 1 or 2 hosts with 1 or 2 units is placed by fit score (M4) and dispatched all
      year (M3); the option with the fewest batteries that clears it wins. A transformer no option clears is
      an Upgrade. Overloaded sets nest as the margin rises, so homes are loaded once at the smallest margin
      and every margin's Protect set is dispatched in one batch with its own ceilings.
"""
import sys
from pathlib import Path
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
import pandas as pd
from ewu import PROCESSED, config_value
from ewu import adoption, dispatch, feeders as feeder_groups, fitscore, stress
from ewu.coldsnap import percent_of

COUNTS = ("transformers", "flagged", "shift_fixed", "protect_set", "new_from_stagger", "protected",
          "batteries", "upgrade_left", "ev_homes_enrolled")


def top_hours_and_days(config):
    """The M4 system top hours and the day each falls on, for fit scores."""
    index = pd.read_parquet(PROCESSED / "weather.parquet").index
    top = fitscore.system_top_hours(np.load(PROCESSED / "sysload.npy"), index, config)
    return top, np.asarray(index[top].normalize().asi8)


def options_from_config(config):
    """Every (hosts, units) pair the plan allows on one flagged transformer."""
    return [(hosts, units) for hosts in config_value("battery.coldsnap_hosts_per_transformer", config)
            for units in config_value("battery.units_per_host_options", config)]


def batteries_that_clear(setup, rows_by_margin, ceilings_by_margin, top, top_day, config):
    """Per margin: the fewest batteries that clear each Protect transformer (0 = none clears), fit-score hosts."""
    rows = np.concatenate(rows_by_margin)
    ceiling = np.concatenate(ceilings_by_margin)
    edges = np.cumsum([0] + [len(r) for r in rows_by_margin])
    placed = [{} for _ in rows_by_margin]
    for hosts, units in options_from_config(config):
        spec = dispatch.battery_spec(units, config)
        scores = fitscore.fit_score(setup["home_kw"][:, :, top], top_day, spec)
        picks = fitscore.choose_hosts("fit_score", scores, None, None, hosts, None)[rows]
        host_kw = setup["home_kw"][rows[:, None], picks].transpose(1, 0, 2)
        cleared = dispatch.run_batteries(setup["total"][rows], ceiling, host_kw, spec)["hours_over"] == 0
        for i in range(len(rows_by_margin)):
            placed[i][(hosts, units)] = cleared[edges[i]:edges[i + 1]]
    return [fitscore.cheapest_clear(p, options_from_config(config)) if len(r) else np.zeros(0, dtype=np.int64)
            for p, r in zip(placed, rows_by_margin)]


def ladder_for_one_run(inputs, groups, base, parts, config, top, top_day):
    """{margin: counts} for one seed, scenario and grouping."""
    margins = sorted(config_value("transformer.sizing_margins", config))
    limit = config_value("transformer.overload_limit", config)
    owner = stress.transformer_of_each_home(groups, len(inputs["homes"]))
    unmanaged = base + parts["ev"] + parts["hp"]
    setup = fitscore.flagged_setup(inputs, groups, base, parts, config, margin=margins[0])
    ev_per_transformer = np.bincount(owner[parts["ev_homes"]], minlength=groups.count)
    rows_by_margin, ceilings_by_margin, flags = [], [], []
    for margin in margins:
        ceiling = limit * feeder_groups.rate(base.max(1), margin)
        flag = (unmanaged > ceiling[:, None]).any(1)
        above = setup["total"] - ceiling[setup["flagged"]][:, None]
        rows = np.flatnonzero((above > dispatch.OVER_TOLERANCE_KW).any(1))
        rows_by_margin.append(rows)
        ceilings_by_margin.append(ceiling[setup["flagged"][rows]])
        flags.append(flag)
    needs = batteries_that_clear(setup, rows_by_margin, ceilings_by_margin, top, top_day, config)
    out = {}
    for margin, rows, flag, need in zip(margins, rows_by_margin, flags, needs):
        protect = np.zeros(groups.count, dtype=bool)
        protect[setup["flagged"][rows]] = True
        out[margin] = {"transformers": groups.count, "flagged": int(flag.sum()),
                       "shift_fixed": int((flag & ~protect).sum()), "protect_set": int(protect.sum()),
                       "new_from_stagger": int((protect & ~flag).sum()), "protected": int((need > 0).sum()),
                       "batteries": int(need.sum()), "upgrade_left": int((need == 0).sum()),
                       "ev_homes_enrolled": int(ev_per_transformer[flag | protect].sum())}
    return out


def run_sensitivity(inputs, config, seeds, scenarios=stress.SCENARIOS, groupings=feeder_groups.MODES):
    """{(scenario, grouping, margin, seed): counts} over the whole grid."""
    k, count = config_value("transformer.homes_per_transformer", config), config_value("transformer.count", config)
    sessions = adoption.measure_ev_sessions(inputs["load"], inputs["homes"]["is_ev_l2"], inputs["temp"], config)
    top, top_day = top_hours_and_days(config)
    runs = {}
    for grouping in groupings:
        for seed in seeds:
            groups = feeder_groups.build_transformers(inputs["homes"]["segment"].to_numpy(), k, count, grouping, seed)
            base = stress.base_loading(inputs["load"], groups)
            for scenario in scenarios:
                parts = stress.loading_parts(inputs, groups, scenario, seed, config, sessions, base)
                for margin, counts in ladder_for_one_run(inputs, groups, base, parts, config, top, top_day).items():
                    runs[(scenario, grouping, margin, seed)] = counts
    return runs


def summarize_ladder(runs):
    """Seed-pooled counts per (scenario, grouping, margin), plus the ladder as shares of all transformers."""
    pooled = {}
    for (scenario, grouping, margin, _), counts in runs.items():
        cell = pooled.setdefault((scenario, grouping, margin), {name: 0 for name in COUNTS} | {"seeds": 0})
        for name in COUNTS:
            cell[name] += counts[name]
        cell["seeds"] += 1
    for cell in pooled.values():
        whole = cell["transformers"]
        cell["shares"] = {
            "flagged_pct": percent_of(cell["flagged"], whole), "shift_fixed_pct": percent_of(cell["shift_fixed"], whole),
            "protect_set_pct": percent_of(cell["protect_set"], whole),
            "protected_pct": percent_of(cell["protected"], whole), "upgrade_left_pct": percent_of(cell["upgrade_left"], whole),
            "protected_of_set_pct": percent_of(cell["protected"], cell["protect_set"]),
            "batteries_per_protected": round(cell["batteries"] / cell["protected"], 2) if cell["protected"] else 0.0,
            "ev_homes_per_flagged": round(cell["ev_homes_enrolled"] / cell["flagged"], 2) if cell["flagged"] else 0.0}
    return pooled


def record_ladder(pooled):
    """Every cell's ladder shares to facts/facts.json (aggregates only)."""
    from analysis.facts import record
    units = {"batteries_per_protected": "batteries per protected transformer",
             "ev_homes_per_flagged": "EV homes enrolled per flagged transformer",
             "protected_of_set_pct": "% of transformers still over with staggered charging"}
    for (scenario, grouping, margin), cell in pooled.items():
        key = f"ewu.sensitivity.{scenario}.{grouping}.{stress.margin_label(margin)}"
        how = (f"pooled {cell['seeds']} seeds, {cell['transformers']} transformer runs, rating = today's peak x {margin}; "
               "flag unmanaged, shift staggered, protect with fit-score hosts, fewest batteries that clear")
        for name, value in cell["shares"].items():
            record(f"{key}.{name}", value, units.get(name, "% of all transformers"), how)
    record("ewu.sensitivity.cells", len(pooled), "grid cells", "scenarios x sizing margins x grouping modes")
