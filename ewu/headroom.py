"""Headroom: the 3 kVA service test for a new Level 2 charger, with the charge as long as measured sessions.

What: charge_profile() is the kW a new charger adds at each hour of the day; passes_service_limit() says,
      per home, whether its new peak stays within today's peak plus `transformer.service_added_kva_max`,
      with no battery or with a battery holding that cap day by day; run_headroom() tests every home without
      an EV today under the existing 2-hour charge and under a charge as long as the measured mean session;
      record_headroom() writes the pass shares to facts under ewu.headroom.*.
Why:  the existing rule in analysis/bess.py charges for two hours from 18:00, which set the one-unit pass
      share in facts (bess.headroom_rule.ev_pass_pct_one_unit). Measured sessions run much longer, so a
      one-unit battery must cover far more energy. The review asked for the measured length or a labeled
      assumption; this does both, and the 2-hour run must reproduce the existing facts, so the two tests
      differ only in charge length.
How:  same arithmetic as analysis/bess.py: a home passes with no battery when no hour tops the cap; with a
      battery when, every day, the energy above the cap fits in the battery's delivered energy (capacity x
      the square root of round-trip efficiency) and no hour's excess tops its power. The measured length
      comes from ewu.adoption.measure_ev_sessions; the last hour of the charge carries the part-hour.
"""
import sys
from pathlib import Path
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import time
import numpy as np
import pandas as pd
from ewu import PROCESSED, config_value, read_config, read_inputs
from ewu.adoption import HOURS, measure_ev_sessions

DAYS = HOURS // 24


def charge_profile(start_hour, hours, charger_kw):
    """kW one new charger adds at each hour of the day: full power, then the part of the last hour."""
    kw = np.zeros(24)
    for i in range(int(np.ceil(hours - 1e-9))):
        kw[(start_hour + i) % 24] = charger_kw * min(1.0, hours - i)
    return kw


def battery_sizes(config):
    """(label, delivered-energy kWh, kW) for no battery, one unit and two units, from the challenge spec."""
    units = config_value("battery.units_per_host_max", config)
    root = np.sqrt(config_value("battery.round_trip_efficiency", config))
    two_kwh = config_value("battery.energy_kwh_two_units", config)
    two_kw = config_value("battery.power_kw_two_units", config)
    one_kwh = config_value("battery.energy_kwh_per_unit", config)
    return [("none", 0.0, 0.0), ("one_unit", one_kwh * root, two_kw / units), ("two_units", two_kwh * root, two_kw)]


def passes_service_limit(base_rows, add_day, cap_kw, delivered_kwh, battery_kw):
    """Per home: True when today's load plus the new charge stays within today's peak + cap_kw."""
    base = np.asarray(base_rows)   # the meter data's own float32, as in bess.py, so results match home for home
    cap = base.max(1) + cap_kw
    new = base.reshape(len(base), DAYS, 24) + add_day[None, None, :]
    excess = np.maximum(new - cap[:, None, None], 0.0)
    if delivered_kwh == 0:
        return excess.max((1, 2)) <= 1e-6
    return (excess.sum(2) <= delivered_kwh).all(1) & (excess.max(2) <= battery_kw).all(1)


def homes_without_ev():
    """Row numbers of homes with no Level 2 EV today that are neither vacant nor seasonal (the bess.py pool)."""
    flags = pd.read_parquet(PROCESSED / "segmented.parquet", columns=["is_ev_l2", "is_other_inactive", "is_other_seasonal"])
    return np.flatnonzero(~flags.is_ev_l2.to_numpy() & ~(flags.is_other_inactive | flags.is_other_seasonal).to_numpy())


def run_headroom(inputs, config, chunk_rows=3000):
    """Pass shares for every charge length and battery size, and the measured mean session length."""
    sessions = measure_ev_sessions(inputs["load"], inputs["homes"]["is_ev_l2"], inputs["temp"], config)
    measured = round(float(sessions["length_hours"].mean()), 2)
    start = config_value("robustness.headroom_ev_start_hour", config)
    charger = config_value("scenarios.loads.ev_l2_kw", config)
    cap = config_value("transformer.service_added_kva_max", config)
    lengths = {"charge_assumed": config_value("robustness.headroom_ev_hours_assumed", config),
               "charge_measured_mean": measured}
    rows = homes_without_ev()
    passed = {(name, size): 0 for name in lengths for size, _, _ in battery_sizes(config)}
    for part in np.array_split(rows, max(1, len(rows) // chunk_rows)):
        base = np.asarray(inputs["load"][part])
        for name, hours in lengths.items():
            add = charge_profile(start, hours, charger)
            for size, kwh, kw in battery_sizes(config):
                passed[(name, size)] += int(passes_service_limit(base, add, cap, kwh, kw).sum())
    shares = {key: round(100.0 * n / len(rows), 1) for key, n in passed.items()}
    return {"shares": shares, "lengths": lengths, "homes": len(rows)}


def record_headroom(result, seconds):
    from analysis.facts import record
    lengths = result["lengths"]
    record("ewu.headroom.ev.measured_mean_hours", lengths["charge_measured_mean"], "hours",
           "mean measured Level 2 session, used as the charge length")
    record("ewu.headroom.ev.homes_tested", result["homes"], "homes", "no EV today, not vacant or seasonal")
    for (name, size), share in result["shares"].items():
        record(f"ewu.headroom.ev.{name}.pass_pct_{size}", share, "% of homes without an EV today",
               f"new peak within today's peak + 3 kVA (read as kW); charge {lengths[name]} h at full power")
    record("ewu.headroom.seconds", round(seconds, 1), "s", "")


def main():
    config = read_config()
    started = time.time()
    result = run_headroom(read_inputs(), config)
    record_headroom(result, time.time() - started)
    print(f"3 kVA test on {result['homes']:,} homes without an EV today; share that pass (%):")
    print(f"{'charge':<34} {'no battery':>10} {'one unit':>9} {'two units':>9}")
    for name, hours in result["lengths"].items():
        row = [result["shares"][(name, s)] for s in ("none", "one_unit", "two_units")]
        print(f"{name + f' ({hours} h)':<34} {row[0]:>10.1f} {row[1]:>9.1f} {row[2]:>9.1f}")


if __name__ == "__main__":
    main()
