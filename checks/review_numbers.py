"""Review numbers: recompute 10 headline facts a second way and record match or mismatch in runs/review_round.json.

What: rebuilds 10 numbers from data/processed and config/ewu.yaml without importing ewu/ (the M8 number
      review): the usable-home count, the mean measured charging session, the overloaded share, the share
      over at least 3 hours, the heat pump and EV shares of overload hours, the two 3 kVA one-unit pass
      shares, the ladder's share of upgrading everything and the battery tie price. Each check stores the
      fact, the recomputed value, the tolerance and match true or false under "number_checks".
Why:  plan step M8 asks a reviewer to try to break 10 numbers by recomputing them its own way; a number that
      only its own code can reproduce has not been checked. Keeping the work in a script makes it repeatable.
How:  plain numpy on the meter matrix. Sessions are found as runs of hours at least the jump above the day's
      25th percentile (start on a weather-neutral day, held the minimum hours) via np.diff, not a backward
      scan. Transformers use other random streams (seeds 101 to 105) and are run twice: adopters of both
      devices off one shuffle (the recorded rule) and heat pump adopters drawn apart (the robustness facts);
      each is compared with its fact within the config seed tolerance. The 3 kVA test looks only at the
      charging hours of each day. The two money numbers are rebuilt from rounded facts, so they pass when the
      fact lies inside the interval those roundings allow. Prints aggregates only.
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA, OUT = ROOT / "data" / "processed", ROOT / "runs" / "review_round.json"
CFG = yaml.safe_load((ROOT / "config" / "ewu.yaml").read_text())
FACTS = json.loads((ROOT / "facts" / "facts.json").read_text())
SEEDS = (101, 102, 103, 104, 105)


def setting(dotted):
    node = CFG
    for part in dotted.split("."):
        node = node[part]
    return node["value"]


def fact(key):
    return FACTS[key]["value"]


def count_usable_homes():
    """Rows of the full load matrix with at least 90% of hours read (NaN marks a missing hour)."""
    full = np.load(DATA / "load.npy", mmap_mode="r")
    usable = 0
    for i in range(0, len(full), 4000):
        usable += int(((~np.isnan(np.asarray(full[i:i + 4000]))).mean(1) >= 0.9).sum())
    return usable


def find_sessions(load, ev_rows, temp):
    """(start hour of day, length) of every measured Level 2 session, and sessions per home per neutral day."""
    jump, held = setting("scenarios.loads.ev_session_jump_kw"), setting("scenarios.loads.ev_session_min_hours")
    day_mean = temp.reshape(-1, 24).mean(1)
    neutral = (day_mean >= setting("scenarios.loads.ev_neutral_day_low_f")) & (day_mean <= setting("scenarios.loads.ev_neutral_day_high_f"))
    starts, lengths = [], []
    for row in ev_rows:
        days = np.asarray(load[row], dtype=np.float32).reshape(365, 24)
        on = ((days - np.percentile(days, 25, axis=1, keepdims=True)) >= jump).ravel().astype(np.int8)
        edge = np.diff(np.concatenate([[0], on, [0]]))
        first, last = np.flatnonzero(edge == 1), np.flatnonzero(edge == -1)
        keep = ((last - first) >= held) & neutral[first // 24]
        starts.append(first[keep] % 24)
        lengths.append((last - first)[keep])
    starts, lengths = np.concatenate(starts), np.concatenate(lengths)
    return starts, lengths, len(starts) / (len(ev_rows) * int(neutral.sum()))


def simulate_one_seed(load, homes, temp, sessions, seed, one_order, scenario="moderate"):
    """Counts for one random draw: overloaded, over 3+ hours, overload hours, hours with a heat pump on, hours the
    EV share is strictly the largest. one_order: both devices go to the first eligible homes of one shuffle."""
    rng = np.random.default_rng(seed)
    k, count = setting("transformer.homes_per_transformer"), setting("transformer.count")
    groups = rng.permutation(len(homes))[: k * count].reshape(count, k)
    owner = np.full(len(homes), -1)
    owner[groups.ravel()] = np.repeat(np.arange(count), k)
    vacant = homes.is_other_inactive.to_numpy()
    picks, shuffled = {}, rng.permutation(groups.ravel())
    for share, has in (("ev_share", "is_ev_l2"), ("hp_share", "is_electric_heat")):
        pool = shuffled[~homes[has].to_numpy()[shuffled] & ~vacant[shuffled]]
        wanted = int(round(setting(f"scenarios.{scenario}.{share}") * groups.size))
        picks[share] = pool[:wanted] if one_order else rng.choice(pool, wanted, replace=False)
    base = np.zeros((count, 8760))
    for i in range(0, count, 500):
        base[i:i + 500] = np.asarray(load[groups[i:i + 500].ravel()], dtype=np.float64).reshape(-1, k, 8760).sum(1)
    start, length, rate = sessions
    car, day = np.nonzero(rng.random((len(picks["ev_share"]), 365)) < rate)
    pick = rng.integers(0, len(start), len(car))
    ev = np.zeros(count * 8760)
    for step in range(int(length.max())):
        live = length[pick] > step
        hour = day[live] * 24 + start[pick][live] + step
        ok = hour < 8760
        np.add.at(ev, owner[picks["ev_share"][car[live][ok]]] * 8760 + hour[ok], setting("scenarios.loads.ev_l2_kw"))
    ev = ev.reshape(count, 8760)
    hp_kw = setting("scenarios.loads.hp_kw_per_degf") * np.maximum(0, setting("scenarios.loads.hp_balance_temp_f") - temp)
    hp = np.bincount(owner[picks["hp_share"]], minlength=count)[:, None] * hp_kw[None, :]
    ceiling = (setting("transformer.overload_limit") * setting("transformer.base_margin") * base.max(1))[:, None]
    over = base + ev + hp > ceiling
    def above(x):
        return np.maximum(x - ceiling, 0)
    ev_part = (above(base + ev) - above(base) + above(base + ev + hp) - above(base + hp)) / 2
    hp_part = (above(base + hp) - above(base) + above(base + ev + hp) - above(base + ev)) / 2
    return {"overloaded": int(over.any(1).sum()), "three_hours": int((over.sum(1) >= 3).sum()), "hours": int(over.sum()),
            "hp_on": int((over & (hp > 0)).sum()), "ev_led": int((over & (ev_part > hp_part) & (ev_part > above(base))).sum())}


def one_unit_pass_share(load, rows, hours):
    """Share of homes whose new charger, run `hours` from the config start, one battery unit keeps within peak + 3."""
    start, kw = setting("robustness.headroom_ev_start_hour"), setting("scenarios.loads.ev_l2_kw")
    add = np.array([kw * min(1.0, hours - i) for i in range(int(np.ceil(hours)))])
    energy = setting("battery.energy_kwh_per_unit") * np.sqrt(setting("battery.round_trip_efficiency"))
    power = setting("battery.power_kw_two_units") / setting("battery.units_per_host_max")
    passed = 0
    for i in range(0, len(rows), 3000):
        days = np.asarray(load[rows[i:i + 3000]]).reshape(-1, 365, 24)
        cap = days.max((1, 2))[:, None, None] + setting("transformer.service_added_kva_max")
        excess = np.maximum(days[:, :, start:start + len(add)] + add - cap, 0)
        passed += int(((excess.sum(2) <= energy).all(1) & (excess.max(2) <= power).all(1)).sum())
    return round(100.0 * passed / len(rows), 1)


def money_interval():
    """Ladder share and equal-life tie price over every rounding of the pooled shares behind them (mid prices)."""
    r = setting("prices.discount_rate")
    def recovery_factor(years):
        return r / (1 - (1 + r) ** -years)
    life, blife = setting("prices.transformer_life_years"), setting("battery.life_years")
    up = setting("prices.upgrade_cost_usd") * recovery_factor(life)
    bat = np.mean([setting("prices.battery_unit_cost_low_usd"), setting("prices.battery_unit_cost_high_usd")]) * recovery_factor(blife)
    shift = setting("prices.managed_charging_enroll_usd") * recovery_factor(life) + setting("prices.managed_charging_usd_yr")
    cell = "ewu.sensitivity.moderate.random.margin_115."
    def span(name, half):
        return (fact(cell + name) - half, fact(cell + name) + half)
    flag, prot, left = span("flagged_pct", .005), span("protected_pct", .005), span("upgrade_left_pct", .005)
    per, epf = span("batteries_per_protected", .005), span("ev_homes_per_flagged", .005)
    def share(j):
        return 100 * (epf[j] * shift / up + (per[j] * prot[j] * bat + left[j] * up) / (flag[1 - j] * up))
    return (share(0), share(1)), (up / (per[1] * recovery_factor(blife)), up / (per[0] * recovery_factor(blife)))


def compare(key, mine, tol, how):
    """One comparison: the fact, what this script got, and whether they agree (an interval when tol is None)."""
    value = fact(key)
    if tol is None:
        ok, shown = mine[0] - 0.5 <= value <= mine[1] + 0.5, [round(float(x), 2) for x in mine]
    else:
        ok, shown = abs(value - mine) <= tol + 1e-9, round(float(mine), 2)
    print(f"{'MATCH' if ok else 'MISMATCH':<9} {key} = {value}; recomputed {shown}")
    return {"fact": key, "fact_value": value, "recomputed": shown, "how": how, "match": bool(ok),
            "tolerance": tol if tol is not None else "fact inside the interval the rounded inputs allow"}


def main():
    load = np.load(DATA / "load_present.npy", mmap_mode="r")
    homes = pd.read_parquet(DATA / "segmented.parquet")
    temp = pd.read_parquet(DATA / "weather.parquet")["temp"].to_numpy().astype(np.float64)
    sessions = find_sessions(load, np.flatnonzero(homes.is_ev_l2.to_numpy()), temp)
    whole, tol = len(SEEDS) * setting("transformer.count"), setting("checks.seed_tolerance_pts")
    sims = {}
    for one_order in (True, False):
        runs = [simulate_one_seed(load, homes, temp, sessions, s, one_order) for s in SEEDS]
        t = {key: sum(r[key] for r in runs) for key in runs[0]}
        sims[one_order] = {"overloaded_pct": 100 * t["overloaded"] / whole, "flagged_min_hours_pct": 100 * t["three_hours"] / whole,
                           "hours_with_hp_running_pct": 100 * t["hp_on"] / t["hours"],
                           "hours_ev_strictly_larger_pct": 100 * t["ev_led"] / t["hours"]}
    pool = np.flatnonzero(~homes.is_ev_l2.to_numpy() & ~(homes.is_other_inactive | homes.is_other_seasonal).to_numpy())
    mean_hours = round(float(sessions[1].mean()), 2)
    ladder, tie = money_interval()
    m, own = "ewu.attribution.moderate.random.margin_115.unmanaged.", "ewu.robustness.adoption_own_order.moderate.margin_115."
    recorded = {"overloaded_pct": "ewu.stress.moderate.random.margin_115.overloaded_pct",
                "flagged_min_hours_pct": "ewu.robustness.flag_hours.moderate.random.margin_115.flagged_min_hours_pct",
                "hours_with_hp_running_pct": m + "hours_with_hp_running_pct",
                "hours_ev_strictly_larger_pct": m + "hours_ev_strictly_larger_pct"}
    checks = [compare("data.customers_usable", count_usable_homes(), 0, "rows of load.npy with 90% of hours read, NaN scan"),
              compare("ewu.adoption.ev_session_mean_hours", mean_hours, 0.005, "runs found with np.diff on each Level 2 home")]
    for name, key in recorded.items():
        row = compare(key, sims[True][name], tol, "own simulation, seeds 101-105, both devices off one shuffle")
        unit = "" if name == "flagged_min_hours_pct" else "unmanaged."
        row["own_order"] = compare(own + unit + name, sims[False][name], tol, "own simulation, heat pump adopters drawn apart")
        row["match"] = row["match"] and row["own_order"]["match"]
        checks.append(row)
    for label, hours in (("charge_measured_mean", mean_hours), ("charge_assumed", setting("robustness.headroom_ev_hours_assumed"))):
        checks.append(compare(f"ewu.headroom.ev.{label}.pass_pct_one_unit", one_unit_pass_share(load, pool, hours), 0.05,
                              f"charging hours only, {hours} h charge"))
    checks.append(compare("ewu.economics.headline.ladder_share_pct.base", ladder, None, "annuity math on the rounded pooled shares, mid prices"))
    checks.append(compare("ewu.economics.battery_vs_upgrade.mid.tie_unit_usd_equal_life", tie, None,
                          "upgrade yearly cost over batteries per cleared times the battery annuity"))
    review = json.loads(OUT.read_text()) if OUT.exists() else {}
    review["number_checks"] = checks
    OUT.write_text(json.dumps(review, indent=2) + "\n")
    print(f"review_numbers: {sum(c['match'] for c in checks)} of {len(checks)} match")
    return 0 if all(c["match"] for c in checks) else 1

if __name__ == "__main__":
    sys.exit(main())
