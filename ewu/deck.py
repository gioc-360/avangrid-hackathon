"""Deck profile: the final deck's transformer screen and battery-only fix, built from the teammate's spec.

What: standard_rating() sizes each synthetic transformer to a standard kVA; ev_start_pmf() and hp_increment()
      load the teammate's arrays from data/processed (sha256 checked against config), or derive our own and say so; pick_adopters() draws new
      EV and heat pump homes; ev_loading() adds 3-hour 7.2 kW charges; battery_units() sizes 1 to 4 IQ 10C
      units per overloaded transformer; run_deck() runs one scenario at every overload limit option.
Why:  the team decided the final deck's method (runs/teammate_deck_spec_2026-11-13.txt). The tool must
      reproduce it by default, while the earlier method stays available as the `cautious` profile.
How:  rating = smallest size in profiles.deck.standard_sizes_kva at or above today's group peak / 0.85 (kW as
      kVA, power factor 1); a group needing more than the largest size gets as many of it as it needs, counted.
      Overloaded = any hour above limit x rating. Units = max over days of ceil(day's peak excess / unit_kw) and
      ceil(day's excess kWh / unit_kwh), at least units_min; above units_max = upgrade. Winter driven
      (profiles.deck.winter_rule) = more than half the hours over the limit fall in winter_months (the
      teammate's rule), or the worst hour does (ours); both are reported. With managed charging on,
      each new EV charge moves into the shift block's staggered window at its power share, same energy.
"""
import numpy as np
import pandas as pd
from ewu import PROCESSED, config_value
from ewu import adoption, feeders as feeder_groups, stress

HOURS = adoption.HOURS
SCENARIOS = stress.SCENARIOS


def deck_value(name, config):
    return config_value(f"profiles.deck.{name}", config)


def standard_rating(today_peak_kw, config):
    """(rating in kW, groups above the largest size): smallest standard size at or above peak / divisor."""
    sizes = np.asarray(deck_value("standard_sizes_kva", config), dtype=np.float64)
    pf = deck_value("power_factor", config)
    need_kva = np.asarray(today_peak_kw, dtype=np.float64) / deck_value("peak_to_rating_divisor", config) / pf
    slot = np.searchsorted(sizes, need_kva - 1e-9)
    above = slot >= len(sizes)
    kva = np.where(above, np.ceil(need_kva / sizes[-1]) * sizes[-1], sizes[np.minimum(slot, len(sizes) - 1)])
    return kva * pf, int(above.sum())


def array_source(name, config):
    """(path, 'teammate') when the teammate's file sits in data/processed and its sha256 is the one in config
    (ewu/deck_arrays.verify_array fails loudly otherwise), else (derived path, 'derived')."""
    path = PROCESSED / deck_value(name, config)
    if not path.exists():
        return path.with_name(f"{path.stem}_derived.npy"), "derived"
    from ewu.deck_arrays import verify_array
    verify_array(name.removesuffix("_file"), path, config)
    return path, "teammate"


def array_label(origin):
    """How a printout names an array's origin."""
    return ("the team's ewu_inputs.py (data/processed, sha256 checked; 2026-11-13, built from the meter data)"
            if origin == "teammate" else "derived from our data (the team's file is absent)")


def ev_start_pmf(inputs, config):
    """24 start-hour probabilities: the teammate's ev_start_pmf.npy, else the start hours of our measured
    Level 2 sessions (DERIVED), written to data/processed/ev_start_pmf_derived.npy."""
    path, origin = array_source("ev_start_pmf_file", config)
    if origin == "teammate":
        pmf = np.load(path).astype(np.float64).ravel()
    else:
        sessions = adoption.measure_ev_sessions(inputs["load"], inputs["homes"]["is_ev_l2"], inputs["temp"], config)
        pmf = np.bincount(sessions["start_hour"], minlength=24).astype(np.float64)
        np.save(path, pmf / pmf.sum())
    if pmf.shape != (24,) or pmf.min() < 0 or pmf.sum() <= 0:
        raise ValueError(f"{path.name} must hold 24 non-negative start-hour weights, not shape {pmf.shape}")
    return pmf / pmf.sum(), origin


def hp_increment(inputs, config):
    """kW one new heat pump adds in each of 8,760 hours: the teammate's hp_increment.npy, else our measured
    electric-heat temperature slope (DERIVED), written to data/processed/hp_increment_derived.npy."""
    path, origin = array_source("hp_increment_file", config)
    if origin == "teammate":
        kw = np.load(path).astype(np.float64).ravel()
    else:
        kw = adoption.heat_pump_kw(inputs["temp"], config).astype(np.float64)
        np.save(path, kw)
    if kw.shape != (HOURS,):
        raise ValueError(f"{path.name} must hold {HOURS} hourly kW values, not shape {kw.shape}")
    return kw, origin


def pick_adopters(group_homes, homes, scenario, seed, config):
    """(ev_homes, hp_homes): grouped, occupied homes without the device today, one order per device and seed,
    so high adopters include moderate ones; the share applies to eligible homes or to all grouped homes
    (profiles.deck.adoption_share_base)."""
    grouped = np.asarray(group_homes)
    vacant = homes["is_other_inactive"].to_numpy()
    picks = []
    for i, (device, flags) in enumerate((("ev_share", "ev_excluded_flags"), ("hp_share", "hp_excluded_flags"))):
        order = grouped[np.random.default_rng((seed, 1, i)).permutation(len(grouped))]
        has = np.zeros(len(homes), dtype=bool)
        for flag in deck_value(flags, config):
            has |= homes[flag].to_numpy()
        eligible = order[~has[order] & ~vacant[order]]
        pool = len(eligible) if deck_value("adoption_share_base", config) == "eligible_homes" else len(grouped)
        wanted = int(round(config_value(f"scenarios.{scenario}.{device}", config) * pool))
        if wanted > len(eligible):
            raise ValueError(f"{scenario} wants {wanted} {device} adopters but only {len(eligible)} homes can add one")
        picks.append(np.sort(eligible[:wanted]))
    return picks[0], picks[1]


def ev_loading(ev_homes, owner, count, pmf, seed, scenario, config, managed=False):
    """kW new EV charging adds by transformer and hour: each home charges on ev_day_share of days, ev_hours at
    ev_kw, from a start hour drawn from the pmf; managed moves the charge into the staggered window."""
    rng = np.random.default_rng((seed, 2, SCENARIOS.index(scenario)))
    kw, hours = deck_value("ev_kw", config), deck_value("ev_hours", config)
    home_pos, day = np.nonzero(rng.random((len(ev_homes), HOURS // 24)) < deck_value("ev_day_share", config))
    start = day * 24 + rng.choice(24, size=len(day), p=pmf)
    if managed:
        first, last = config_value("shift.stagger_start_hour", config), config_value("shift.stagger_end_hour", config)
        window = [(first + i) % 24 for i in range((last - first) % 24)]
        share = config_value("shift.stagger_power_share", config)
        pick = np.array(window)[rng.integers(0, len(window), len(day))]
        start = day * 24 + pick + 24 * (pick < first)
        kw, hours = kw * share, int(round(hours / share))
    cell = owner[np.asarray(ev_homes)[home_pos]] * HOURS
    out = np.zeros(count * HOURS)
    for k in range(hours):
        hour = start + k
        keep = hour < HOURS
        out += np.bincount(cell[keep] + hour[keep], minlength=count * HOURS)
    return (out * kw).reshape(count, HOURS)


def battery_units(total_kw, ceiling_kw, config):
    """Per transformer: max over days of ceil(peak excess / unit_kw) and ceil(excess kWh / unit_kwh), >= units_min."""
    excess = np.maximum(total_kw - np.asarray(ceiling_kw)[:, None], 0.0).reshape(len(total_kw), HOURS // 24, 24)
    by_power = np.ceil(excess.max(2) / deck_value("unit_kw", config) - 1e-9)
    by_energy = np.ceil(excess.sum(2) / deck_value("unit_kwh", config) - 1e-9)
    return np.maximum(np.maximum(by_power, by_energy).max(1), deck_value("units_min", config)).astype(np.int64)


def percent_of(part, whole):
    return round(100.0 * part / whole, 2) if whole else 0.0


def deck_setup(inputs, config, seed=None):
    """Transformers, today's base load, standard ratings and the two arrays (shared by every scenario)."""
    seed = deck_value("seed", config) if seed is None else seed
    groups = feeder_groups.build_transformers(inputs["homes"]["segment"].to_numpy(), deck_value("homes_per_transformer", config),
                                              deck_value("transformer_count", config), "random", seed)
    base = stress.base_loading(inputs["load"], groups)
    rating, above = standard_rating(base.max(1), config)
    pmf, pmf_origin = ev_start_pmf(inputs, config)
    hp_kw, hp_origin = hp_increment(inputs, config)
    month = pd.read_parquet(PROCESSED / "weather.parquet").index.month.to_numpy()
    return {"seed": seed, "groups": groups, "base": base, "rating": rating, "above_largest": above, "pmf": pmf,
            "hp_kw": hp_kw, "origins": {"ev_start_pmf": pmf_origin, "hp_increment": hp_origin}, "month": month,
            "owner": stress.transformer_of_each_home(groups, len(inputs["homes"]))}


def run_deck(inputs, config, scenario, setup=None, managed=None, limits=None):
    """{limit: cell} for one scenario: overloaded, fixed by 1 to 4 units, upgrades, units, winter driven share."""
    setup = setup or deck_setup(inputs, config)
    managed = deck_value("managed_charging", config) if managed is None else managed
    groups, owner = setup["groups"], setup["owner"]
    ev_homes, hp_homes = pick_adopters(groups.homes, inputs["homes"], scenario, setup["seed"], config)
    ev = ev_loading(ev_homes, owner, groups.count, setup["pmf"], setup["seed"], scenario, config, managed)
    hp = np.bincount(owner[hp_homes], minlength=groups.count)[:, None] * setup["hp_kw"][None, :]
    total = setup["base"] + ev + hp
    worst = total.argmax(1)
    winter_month = np.isin(setup["month"], deck_value("winter_months", config))
    winter_worst = winter_month[worst]
    cells = {}
    for limit in limits or deck_value("overload_limit_options", config):
        ceiling = limit * setup["rating"]
        above = total > ceiling[:, None]
        over = above.any(1)
        winter_major = 2 * (above & winter_month[None, :]).sum(1) > above.sum(1)
        winter = winter_major if deck_value("winter_rule", config) == "majority_of_over_hours" else winter_worst
        units = np.zeros(groups.count, dtype=np.int64)
        units[over] = battery_units(total[over], ceiling[over], config)
        fixed = over & (units <= deck_value("units_max", config))
        n_over = int(over.sum())
        cells[float(limit)] = {
            "transformers": groups.count, "overloaded": n_over, "overloaded_pct": percent_of(n_over, groups.count),
            "fixed": int(fixed.sum()), "fixed_of_overloaded_pct": percent_of(int(fixed.sum()), n_over),
            "upgrades": int((over & ~fixed).sum()), "batteries": int(units[fixed].sum()),
            "average_units": round(float(units[fixed].mean()), 2) if fixed.any() else 0.0,
            "fixed_units_1_2": int((fixed & (units <= 2)).sum()), "fixed_units_3_4": int((fixed & (units >= 3)).sum()),
            "winter_of_overloaded_pct": percent_of(int((over & winter).sum()), n_over),
            "winter_worst_hour_pct": percent_of(int((over & winter_worst).sum()), n_over),
            "winter_majority_hours_pct": percent_of(int((over & winter_major).sum()), n_over),
            "ev_homes": len(ev_homes), "hp_homes": len(hp_homes), "managed": bool(managed),
            "state": {"over": over, "fixed": fixed, "units": units, "ceiling": ceiling, "worst_hour": worst}}
    return cells, {"base": setup["base"], "ev": ev, "hp": hp, "ev_homes": ev_homes, "hp_homes": hp_homes}
