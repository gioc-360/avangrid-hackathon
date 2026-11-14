"""Deck recharge check: do the deck's battery sizes still hold once the batteries must recharge through the transformer?

What: dispatch() runs each battery-fixed transformer hour by hour for the year: discharge whatever is above the
      limit (up to the units' power and stored energy), recharge only from headroom below the limit at the
      round-trip efficiency, start full; still_over() counts transformers left above the limit in any hour;
      resize() adds a unit to each such transformer until it clears or passes units_max (then an upgrade);
      main() runs both scenarios at 1.20 and records ewu.deck.recharge.* facts.
Why:  the audit found the deck's sizing rule (day's peak excess / kW and day's excess kWh / kWh) ignores
      recharge, in the teammate's code and in ours. The deck profile keeps the spec's rule; this check says how
      many transformers it misses and gives the corrected count beside it, behind its own command.
How:  `bin/ewu recharge`. Usable kWh and kW per unit from profiles.deck, efficiency from
      battery.round_trip_efficiency. A day-sized battery that cannot refill overnight shows up as a miss.
"""
import numpy as np
from ewu import config_value, read_config, read_inputs
from ewu import deck

SCENARIOS = ("moderate", "high")


def dispatch(total_kw, ceiling_kw, units, config):
    """kW left above the limit, per transformer and hour, with batteries that recharge only from headroom."""
    power, energy = units * deck.deck_value("unit_kw", config), units * deck.deck_value("unit_kwh", config)
    rte = config_value("battery.round_trip_efficiency", config)
    charge, left = energy.astype(np.float64).copy(), np.zeros_like(total_kw)
    for hour in range(total_kw.shape[1]):
        excess = total_kw[:, hour] - ceiling_kw
        give = np.where(excess > 0, np.minimum(np.minimum(excess, power), charge), 0.0)
        charge -= give
        left[:, hour] = np.where(excess > 0, excess - give, 0.0)
        room = np.where(excess < 0, -excess, 0.0)
        charge += np.minimum(np.minimum(room, power), (energy - charge) / rte) * rte
    return left


def still_over(total_kw, ceiling_kw, units, config):
    left = dispatch(total_kw, ceiling_kw, units, config)
    return left.max(1) > 1e-6, left.max(1)


def resize(total_kw, ceiling_kw, units, config):
    """Units after adding one at a time where dispatch still misses; above units_max means an upgrade."""
    units, cap = units.copy(), deck.deck_value("units_max", config)
    todo = still_over(total_kw, ceiling_kw, units, config)[0]
    while todo.any():
        units[todo] += 1
        todo &= units <= cap
        if todo.any():
            rows = np.flatnonzero(todo)
            todo[rows] = still_over(total_kw[rows], ceiling_kw[rows], units[rows], config)[0]
    return units


def run_check(inputs, config, scenario, setup):
    cells, parts = deck.run_deck(inputs, config, scenario, setup, False, [1.2])
    cell = cells[1.2]
    st = cell["state"]
    rows = np.flatnonzero(st["fixed"])
    total = (parts["base"] + parts["ev"] + parts["hp"])[rows]
    miss, worst = still_over(total, st["ceiling"][rows], st["units"][rows], config)
    units = resize(total, st["ceiling"][rows], st["units"][rows], config)
    cap = deck.deck_value("units_max", config)
    fixed = int((units <= cap).sum())
    return {"fixed": len(rows), "still_over": int(miss.sum()), "worst_kw": float(worst.max()) if len(rows) else 0.0,
            "fixed_after": fixed, "fixed_after_pct": round(100.0 * fixed / cell["overloaded"], 2) if cell["overloaded"] else 0.0,
            "fixed_pct": cell["fixed_of_overloaded_pct"], "average_units_after": round(float(units[units <= cap].mean()), 2) if fixed else 0.0,
            "average_units": cell["average_units"]}


def main():
    from analysis.facts import record
    config, inputs = read_config(), read_inputs()
    setup = deck.deck_setup(inputs, config)
    print("Recharge check, battery plan at 1.20: batteries recharge only from headroom under the limit")
    for s in SCENARIOS:
        r = run_check(inputs, config, s, setup)
        for k, v in r.items():
            record(f"ewu.deck.recharge.{s}.{k}", v, "transformers" if k in ("fixed", "still_over", "fixed_after") else "",
                   "ewu/deck_recharge.py, battery plan at 1.20, hour-by-hour dispatch")
        print(f"  {s:<9} {r['still_over']} of {r['fixed']} battery-fixed transformers still go over (worst {r['worst_kw']:.2f} kW); "
              f"resized: fixed {r['fixed_pct']:.2f}% -> {r['fixed_after_pct']:.2f}%, units {r['average_units']:.2f} -> {r['average_units_after']:.2f}")


def add_command(commands):
    """`bin/ewu recharge`."""
    rec = commands.add_parser("recharge", help="battery plan: battery sizes checked with recharge through the transformer")
    rec.set_defaults(run=lambda args: main() or 0)
