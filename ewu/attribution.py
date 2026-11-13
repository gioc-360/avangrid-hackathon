"""Attribution: which load (base, EV or heat pump) causes each overload hour, and what EV shifting fixes.

What: fair_shares() splits the energy above the limit in each overload hour among base, EV and heat pump;
      attribute_overloads() counts overload hours by their lead cause, the shares of energy above the limit,
      the lead cause of each transformer's worst hour, how many overload hours fall while heat pumps run, and
      how many hours and transformers clear with no new EV load at all; run_attribution() reruns the M1
      stress test under unmanaged, timer and staggered EV charging at every sizing margin;
      record_attribution() writes the aggregates to facts.
Why:  the teammate's case says most overloads are heat pump nights and also that staggering EVs fixes most
      overloads. Both can only be true if EV load tips over hours the heat pump has already filled. Splitting
      each hour and rerunning with EV load moved settles it with numbers instead of argument.
How:  the energy above the limit in an hour is max(load - limit x rating, 0). Today's load goes first, since
      it is already on the wire: base gets only what it would put over the limit alone. EV and heat pump then
      split the rest by their added effect averaged over both orders of arrival (a two-load Shapley value),
      so the three shares add up to the hour's energy above the limit exactly. An hour's lead cause is the
      load with the largest share. Seeds are pooled before shares are taken, so shares sum to 100%.
"""
import sys
from pathlib import Path
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import time
import numpy as np
from ewu import config_value, read_config, read_inputs
from ewu import feeders as feeder_groups, shift, stress
from ewu.adoption import measure_ev_sessions

SOURCES = ("base", "ev", "hp")


def fair_shares(base, ev, hp, ceiling):
    """Split max(base + ev + hp - ceiling, 0) per hour: base first, then EV and heat pump share the rest fairly."""
    def above(kw):
        return np.maximum(kw - ceiling, 0.0)
    alone = above(base)
    ev_share = ((above(base + ev) - alone) + (above(base + ev + hp) - above(base + hp))) / 2
    hp_share = ((above(base + hp) - alone) + (above(base + ev + hp) - above(base + ev))) / 2
    return {"base": alone, "ev": ev_share, "hp": hp_share}


def attribute_overloads(base, ev, hp, ceiling):
    """Counts for one run: overload hours by lead cause, fair shares of kWh above the limit, worst hours."""
    total = base + ev + hp
    over = total > ceiling[:, None]
    t, h = np.nonzero(over)
    limit = ceiling[t]
    shares = fair_shares(base[t, h], ev[t, h], hp[t, h], limit)
    stacked = np.stack([shares[s] for s in SOURCES])
    lead = stacked.argmax(0)
    excess = np.where(over, total - ceiling[:, None], 0.0)
    overloaded = over.any(1)
    worst = excess.argmax(1)[overloaded]
    worst_t = np.flatnonzero(overloaded)
    worst_shares = fair_shares(base[worst_t, worst], ev[worst_t, worst], hp[worst_t, worst], ceiling[worst_t])
    worst_lead = np.stack([worst_shares[s] for s in SOURCES]).argmax(0)
    still_over = ((base + hp) > ceiling[:, None]).any(1)
    return {"hours_over": len(t), "transformers": len(ceiling), "overloaded": int(overloaded.sum()),
            "kwh_over_total": float(excess.sum()),
            **{f"hours_lead_{s}": int((lead == i).sum()) for i, s in enumerate(SOURCES)},
            **{f"kwh_over_{s}": float(shares[s].sum()) for s in SOURCES},
            **{f"worst_lead_{s}": int((worst_lead == i).sum()) for i, s in enumerate(SOURCES)},
            "overloaded_without_ev": int((overloaded & still_over).sum()),
            "hours_with_hp_running": int((hp[t, h] > 0).sum()),
            "hours_clear_without_ev": int((base[t, h] + hp[t, h] <= limit).sum())}


def run_attribution(inputs, config, seeds, scenarios=stress.SCENARIOS, groupings=feeder_groups.MODES):
    """Per grouping, seed, scenario and EV mode: overloaded flags at every margin, attribution at the base one."""
    k = config_value("transformer.homes_per_transformer", config)
    count = config_value("transformer.count", config)
    margins = config_value("transformer.sizing_margins", config)
    base_margin = config_value("transformer.base_margin", config)
    limit = config_value("transformer.overload_limit", config)
    sessions = measure_ev_sessions(inputs["load"], inputs["homes"]["is_ev_l2"], inputs["temp"], config)
    runs = []
    for grouping in groupings:
        for seed in seeds:
            groups = feeder_groups.build_transformers(inputs["homes"]["segment"].to_numpy(), k, count, grouping, seed)
            base = stress.base_loading(inputs["load"], groups)
            owner = stress.transformer_of_each_home(groups, len(inputs["homes"]))
            for scenario in scenarios:
                parts = stress.loading_parts(inputs, groups, scenario, seed, config, sessions, base)
                for mode in shift.EV_MODES:
                    ev = shift.ev_loading_by_mode(mode, parts, owner, groups.count, config)
                    total = base + ev + parts["hp"]
                    run = {"grouping": grouping, "seed": seed, "scenario": scenario, "mode": mode,
                           "ev_kwh": float(ev.sum()), "overloaded": {}}
                    for margin in margins:
                        ceiling = limit * feeder_groups.rate(base.max(1), margin)
                        run["overloaded"][margin] = (total > ceiling[:, None]).any(1)
                        if margin == base_margin:
                            run["attribution"] = attribute_overloads(base, ev, parts["hp"], ceiling)
                    runs.append(run)
    return runs


def percent_of(part, whole):
    return round(100.0 * part / whole, 2) if whole else 0.0


def summarize_runs(runs, config):
    """Seed-pooled shares per scenario, grouping and EV mode; overloaded, fixed and new shares per margin."""
    out = {}
    for run in runs:
        out.setdefault((run["scenario"], run["grouping"], run["mode"]), []).append(run)
    summary = {}
    for (scenario, grouping, mode), group in out.items():
        unmanaged = {r["seed"]: r for r in runs if (r["scenario"], r["grouping"], r["mode"]) ==
                     (scenario, grouping, "unmanaged")}
        cell = {"by_margin": {}, "ev_kwh": sum(r["ev_kwh"] for r in group)}
        for margin in config_value("transformer.sizing_margins", config):
            now = np.concatenate([r["overloaded"][margin] for r in group])
            before = np.concatenate([unmanaged[r["seed"]]["overloaded"][margin] for r in group])
            cell["by_margin"][margin] = {
                "overloaded_pct": round(float(np.mean([100.0 * r["overloaded"][margin].mean() for r in group])), 2),
                "fixed_pct": percent_of((before & ~now).sum(), before.sum()),
                "new_overloads_pct": percent_of((now & ~before).sum(), len(now))}
        a = {key: sum(r["attribution"][key] for r in group) for key in group[0]["attribution"]}
        cell["counts"] = a
        cell["attribution"] = {
            **{f"hours_lead_{s}_pct": percent_of(a[f"hours_lead_{s}"], a["hours_over"]) for s in SOURCES},
            **{f"kwh_over_{s}_pct": percent_of(a[f"kwh_over_{s}"], a["kwh_over_total"]) for s in SOURCES},
            **{f"worst_hour_{s}_led_pct": percent_of(a[f"worst_lead_{s}"], a["overloaded"]) for s in SOURCES},
            "overloaded_without_ev_pct": percent_of(a["overloaded_without_ev"], a["overloaded"]),
            "overloaded_without_ev_of_all_pct": percent_of(a["overloaded_without_ev"], a["transformers"]),
            "hours_with_hp_running_pct": percent_of(a["hours_with_hp_running"], a["hours_over"]),
            "hours_clear_without_ev_pct": percent_of(a["hours_clear_without_ev"], a["hours_over"]),
            "hours_over_per_transformer": round(a["hours_over"] / a["transformers"], 2)}
        summary[(scenario, grouping, mode)] = cell
    return summary


def record_attribution(summary, config, seconds):
    """Write every aggregate to facts/facts.json; the attribution keys sit at the base sizing margin."""
    from analysis.facts import record
    base_margin = config_value("transformer.base_margin", config)
    seeds = config_value("checks.seeds", config)
    for (scenario, grouping, mode), cell in summary.items():
        for margin, row in cell["by_margin"].items():
            key = f"ewu.shift.{scenario}.{grouping}.{stress.margin_label(margin)}.{mode}"
            record(f"{key}.overloaded_pct", row["overloaded_pct"], "% of transformers",
                   f"mean of {seeds} seeds, EV charging {mode}, rating = today's peak x {margin}")
            if mode != "unmanaged":
                record(f"{key}.fixed_pct", row["fixed_pct"], "% of transformers overloaded unmanaged",
                       "pooled seeds; overloaded unmanaged and not overloaded in this mode")
                record(f"{key}.new_overloads_pct", row["new_overloads_pct"], "% of all transformers",
                       "pooled seeds; overloaded in this mode and not unmanaged")
        key = f"ewu.attribution.{scenario}.{grouping}.{stress.margin_label(base_margin)}.{mode}"
        for name, value in cell["attribution"].items():
            unit = "hours per transformer per year" if name.startswith("hours_over") else "%"
            record(f"{key}.{name}", value, unit,
                   f"pooled {seeds} seeds; base first, then EV and heat pump split the energy above the limit")
    ref = lambda name: config_value(f"teammate_reference.{name}", config)
    for scenario in stress.SCENARIOS:
        record(f"ewu.findings.teammate.{scenario}.shift_fixed_share_pct",
               round(100 * ref(f"shift_fixed_pct_{scenario}") / ref(f"overloaded_pct_{scenario}"), 1),
               "% of overloaded transformers", "teammate fixed-by-staggering points over overloaded points")
    record("ewu.attribution.grid_seconds", round(seconds, 1), "s", "whole attribution and shift grid")


def main():
    config = read_config()
    started = time.time()
    runs = run_attribution(read_inputs(), config, range(config_value("checks.seeds", config)))
    summary = summarize_runs(runs, config)
    record_attribution(summary, config, time.time() - started)
    base_margin = config_value("transformer.base_margin", config)
    print(f"{'scenario':<9} {'grouping':<13} {'EV mode':<10} {'overloaded %':>12} {'fixed %':>8} "
          f"{'HP-led hrs %':>12} {'EV-led hrs %':>12} {'over w/o EV %':>13} {'worst HP-led %':>14}")
    for (scenario, grouping, mode), cell in sorted(summary.items()):
        row, a = cell["by_margin"][base_margin], cell["attribution"]
        print(f"{scenario:<9} {grouping:<13} {mode:<10} {row['overloaded_pct']:>12.2f} {row['fixed_pct']:>8.2f} "
              f"{a['hours_lead_hp_pct']:>12.2f} {a['hours_lead_ev_pct']:>12.2f} "
              f"{a['overloaded_without_ev_pct']:>13.2f} {a['worst_hour_hp_led_pct']:>14.2f}")


if __name__ == "__main__":
    main()
