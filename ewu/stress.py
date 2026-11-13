"""Stress: how many neighborhood transformers the 2030 scenarios overload, at every sizing margin.

What: loading_parts() builds kW by transformer by hour as three parts (base, EV, heat pump); overload_metrics()
      turns loading and a rating into peak ratio, hours over, kWh over and an overloaded flag; run_grid() runs
      every scenario, grouping mode, seed and margin; record_baseline() writes the aggregate results to facts.
Why:  this is the baseline every later step (attribution, shifting, batteries, money) is measured against, and
      judges asked how much the headline moves with transformer sizing. Keeping the three parts apart lets M2
      say which load causes each overload hour without rerunning anything.
How:  base = sum of the grouped homes' metered kW (sparse sum over chunks of rows); EV = each session's hours
      at `ev_l2_kw`, binned by transformer and hour; heat pump = new heat pumps on the transformer times
      heat_pump_kw(). Rating = today's group peak times the margin; overloaded = any hour above
      `overload_limit` times the rating. Run as a script, it records every cell and prints aggregates only.
"""
import sys
from pathlib import Path
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import time
import numpy as np
from scipy import sparse
from ewu import config_value, read_config, read_inputs
from ewu import adoption, feeders as feeder_groups

HOURS = adoption.HOURS
SCENARIOS = ("moderate", "high")


def transformer_of_each_home(feeders, home_count):
    """Array over every home row: its transformer id, or -1 when it is not in any group."""
    owner = np.full(home_count, -1, dtype=np.int64)
    owner[feeders.homes] = feeders.transformer
    return owner


def base_loading(load, feeders, chunk_rows=4000):
    """Today's metered kW summed by transformer, one row per transformer, one column per hour."""
    out = np.zeros((feeders.count, HOURS), dtype=np.float64)
    order = np.argsort(feeders.homes)
    for part in np.array_split(order, max(1, len(order) // chunk_rows)):
        rows = np.asarray(load[feeders.homes[part]], dtype=np.float64)
        pick = sparse.csr_matrix((np.ones(len(part)), (feeders.transformer[part], np.arange(len(part)))),
                                 shape=(feeders.count, len(part)))
        out += pick @ rows
    return out


def ev_loading(ev_sessions, owner, count, charger_kw):
    """kW that new EV charging adds, by transformer and hour."""
    home, hour = adoption.session_hours(ev_sessions)
    cell = owner[home] * HOURS + hour
    return (np.bincount(cell, minlength=count * HOURS) * charger_kw).reshape(count, HOURS)


def heat_pump_loading(hp_homes, owner, count, kw_per_heat_pump):
    """kW that new heat pumps add, by transformer and hour."""
    per_transformer = np.bincount(owner[hp_homes], minlength=count)
    return per_transformer[:, None] * kw_per_heat_pump[None, :].astype(np.float64)


def loading_parts(inputs, feeders, scenario, seed, config, sessions, base=None):
    """Base, EV and heat pump kW by transformer and hour, plus who adopted what. Total = the sum of the three."""
    owner = transformer_of_each_home(feeders, len(inputs["homes"]))
    ev_homes, hp_homes = adoption.pick_adopters(feeders.homes, inputs["homes"], scenario, seed, config)
    ev_sessions = adoption.draw_ev_sessions(ev_homes, sessions, seed, SCENARIOS.index(scenario))
    charger_kw = config_value("scenarios.loads.ev_l2_kw", config)
    return {
        "base": base_loading(inputs["load"], feeders) if base is None else base,
        "ev": ev_loading(ev_sessions, owner, feeders.count, charger_kw),
        "hp": heat_pump_loading(hp_homes, owner, feeders.count, adoption.heat_pump_kw(inputs["temp"], config)),
        "ev_homes": ev_homes, "hp_homes": hp_homes, "ev_sessions": ev_sessions,
    }


def overload_metrics(total_kw, rating_kw, limit):
    """Per transformer: peak as a multiple of rating, hours and kWh above limit x rating, and overloaded or not."""
    ceiling = (limit * np.asarray(rating_kw))[:, None]
    above = np.maximum(total_kw - ceiling, 0.0)
    hours_over = (above > 0).sum(1)
    return {"peak_ratio": total_kw.max(1) / np.asarray(rating_kw), "hours_over": hours_over,
            "kwh_over": above.sum(1), "overloaded": hours_over > 0}


def run_grid(inputs, config, seeds, scenarios=SCENARIOS, modes=feeder_groups.MODES):
    """Every scenario x mode x seed x margin: one row of aggregate results each."""
    k = config_value("transformer.homes_per_transformer", config)
    count = config_value("transformer.count", config)
    margins = config_value("transformer.sizing_margins", config)
    limit = config_value("transformer.overload_limit", config)
    sessions = adoption.measure_ev_sessions(inputs["load"], inputs["homes"]["is_ev_l2"], inputs["temp"], config)
    rows = []
    for mode in modes:
        for seed in seeds:
            feeders = feeder_groups.build_transformers(inputs["homes"]["segment"].to_numpy(), k, count, mode, seed)
            base = base_loading(inputs["load"], feeders)
            today_peak = base.max(1)
            for scenario in scenarios:
                parts = loading_parts(inputs, feeders, scenario, seed, config, sessions, base)
                total = parts["base"] + parts["ev"] + parts["hp"]
                for margin in margins:
                    m = overload_metrics(total, feeder_groups.rate(today_peak, margin), limit)
                    hit = m["overloaded"]
                    rows.append({"scenario": scenario, "mode": mode, "seed": seed, "margin": margin,
                                 "transformers": feeders.count, "homes": len(feeders.homes),
                                 "ev_homes": len(parts["ev_homes"]), "hp_homes": len(parts["hp_homes"]),
                                 "overloaded_pct": 100.0 * hit.mean(),
                                 "median_hours_over": float(np.median(m["hours_over"][hit])) if hit.any() else 0.0,
                                 "median_kwh_over": float(np.median(m["kwh_over"][hit])) if hit.any() else 0.0})
    return rows, sessions


def margin_label(margin):
    return f"margin_{int(round(margin * 100))}"


def summarize_grid(rows):
    """Mean over seeds for each scenario, mode and margin, and the largest gap between one seed and that mean."""
    cells = {}
    for r in rows:
        cells.setdefault((r["scenario"], r["mode"], r["margin"]), []).append(r)
    out = {}
    for (scenario, mode, margin), group in cells.items():
        shares = np.array([r["overloaded_pct"] for r in group])
        out[(scenario, mode, margin)] = {
            "overloaded_pct": round(float(shares.mean()), 2),
            "seed_gap_pts": round(float(np.abs(shares - shares.mean()).max()), 2),
            "median_hours_over": round(float(np.mean([r["median_hours_over"] for r in group])), 1),
            "median_kwh_over": round(float(np.mean([r["median_kwh_over"] for r in group])), 1),
            "ev_homes": int(np.mean([r["ev_homes"] for r in group])), "hp_homes": int(np.mean([r["hp_homes"] for r in group])),
            "seeds": len(group), "transformers": group[0]["transformers"], "homes": group[0]["homes"]}
    return out


def record_baseline(summary, sessions, seconds):
    """Write every grid cell and the measured EV session numbers to facts/facts.json (aggregates only)."""
    from analysis.facts import record
    for (scenario, mode, margin), cell in summary.items():
        key = f"ewu.stress.{scenario}.{mode}.{margin_label(margin)}"
        how = f"mean of {cell['seeds']} seeds, {cell['transformers']} synthetic transformers, rating = today's peak x {margin}"
        record(f"{key}.overloaded_pct", cell["overloaded_pct"], "% of transformers", how)
        record(f"{key}.seed_gap_pts", cell["seed_gap_pts"], "percentage points", "largest gap between one seed and the mean")
        record(f"{key}.median_hours_over", cell["median_hours_over"], "hours per year", "median overloaded transformer")
        record(f"{key}.median_kwh_over", cell["median_kwh_over"], "kWh per year", "median overloaded transformer")
    first = next(iter(summary.values()))
    record("ewu.stress.transformers", first["transformers"], "synthetic transformers", "per seed")
    record("ewu.stress.homes_grouped", first["homes"], "homes", "per seed, none in two transformers")
    for scenario in SCENARIOS:
        cell = next(c for (s, _, _), c in summary.items() if s == scenario)
        record(f"ewu.adoption.{scenario}.ev_homes_added", cell["ev_homes"], "homes per seed", "share x grouped homes")
        record(f"ewu.adoption.{scenario}.hp_homes_added", cell["hp_homes"], "homes per seed", "share x grouped homes")
    record("ewu.adoption.ev_sessions_measured", len(sessions["start_hour"]), "sessions", "Level 2 homes, weather-neutral days")
    record("ewu.adoption.ev_homes_measured", sessions["homes"], "homes", "flagged Level 2 homes")
    record("ewu.adoption.ev_sessions_per_home_day", round(sessions["per_home_day"], 3), "sessions per home per day", "")
    record("ewu.adoption.ev_session_mean_hours", round(float(sessions["length_hours"].mean()), 2), "hours", "")
    evening = (sessions["start_hour"] >= 16) & (sessions["start_hour"] <= 22)
    record("ewu.adoption.ev_start_16_to_22_pct", round(100 * float(evening.mean()), 1), "% of sessions", "start 16:00-22:59")
    record("ewu.stress.grid_seconds", round(seconds, 1), "s", "whole baseline grid")


def main():
    config = read_config()
    started = time.time()
    rows, sessions = run_grid(read_inputs(), config, range(config_value("checks.seeds", config)))
    summary = summarize_grid(rows)
    record_baseline(summary, sessions, time.time() - started)
    print(f"{'scenario':<9} {'grouping':<13} {'margin':>6} {'overloaded %':>12} {'seed gap':>8}")
    for (scenario, mode, margin), cell in sorted(summary.items()):
        print(f"{scenario:<9} {mode:<13} {margin:>6.2f} {cell['overloaded_pct']:>12.2f} {cell['seed_gap_pts']:>8.2f}")


if __name__ == "__main__":
    main()
