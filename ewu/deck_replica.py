"""Deck replica: the teammate's transformer run (ewu_sim_bo2.py) rebuilt in our code, step for step.

What: run_replica() follows her code exactly where it differs from the spec: groups drawn by a generator
      seeded 11, adoption and EV days by one seeded 5 with a coin flip per eligible home, missing hours filled
      with the home's mean, ratings capped at 167 kVA, units sized with 8.064 kWh, winter driven = more than
      half the hours over 1.20 x rating in November to March. Each choice is a switch, so a ladder can walk
      from her run to our deck profile one difference at a time and measure what each one moves.
Why:  the final deck's numbers come from her code; the tool must reproduce them exactly, or show with numbers
      which difference makes each gap, instead of tuning constants.
How:  the same random calls in the same order as her lines 9 and 25 to 34 (a vector draw of a seeded
      generator equals the same draws one at a time), the same float32 sums, the same comparisons. Tiers
      come from our inventory or from her customer_classification.csv, read in place (two boolean columns
      kept in memory, nothing copied or written). Groups can also be our deck profile's own groups.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from ewu import PROCESSED, config_value
from ewu import feeders as feeder_groups

SIZES_KEY, HOURS = "profiles.deck.standard_sizes_kva", 8760


def replica_value(name, config):
    return config_value(f"profiles.deck_replica.{name}", config)


def deck_param(name, config):
    return config_value(f"profiles.deck.{name}", config)


def eligibility(homes, config, tiers):
    """(has_ev, has_heat) per home: her tiers read in place from her folder, or our inventory flags."""
    if tiers == "ours":
        return homes["is_ev_l2"].to_numpy(), homes["is_electric_heat"].to_numpy()
    path = Path(deck_param("teammate_folder", config)).expanduser() / replica_value("classification_file", config)
    first = pd.read_csv(path, nrows=0).columns[0]
    cls = pd.read_csv(path, index_col=0, keep_default_na=False, usecols=[first, "ev", "electric_heat"])
    if not np.array_equal(cls.index.to_numpy(), homes["CUSTOMER_NUMBER"].to_numpy()):
        raise ValueError(f"{path.name} rows are not our {len(homes):,} homes in order; the replica cannot use its tiers")
    return cls["ev"].isin(replica_value("ev_tiers", config)).to_numpy(), (cls["electric_heat"] == replica_value("heat_tier", config)).to_numpy()


def draw_groups(homes, config, groups):
    """3,000 x 8 home positions: her generator seeded 11 (repeats allowed across groups) or our deck groups."""
    count, k = deck_param("transformer_count", config), deck_param("homes_per_transformer", config)
    if groups == "teammate":
        rng = np.random.default_rng(replica_value("grouping_seed", config))
        return np.array([rng.choice(len(homes), k, replace=False) for _ in range(count)])
    built = feeder_groups.build_transformers(homes["segment"].to_numpy(), k, count, "random", deck_param("seed", config))
    return built.homes.reshape(built.count, k)


def home_loads(sel, homes, fill):
    """{position: float32 load}: raw meter rows with missing hours set to the home's mean (hers) or our filled rows."""
    uniq, out = np.unique(sel), {}
    ids = homes["CUSTOMER_NUMBER"].to_numpy()
    raw = np.load(PROCESSED / ("load.npy" if fill == "home_mean" else "load_present.npy"), mmap_mode="r")
    for a in range(0, len(uniq), 2000):
        chunk = uniq[a:a + 2000]
        if fill == "home_mean":
            x = np.array(raw[ids[chunk] - 1])
            mu = np.nanmean(x, 1, keepdims=True)
            x = np.where(np.isnan(x), mu, x)
        else:
            x = np.array(raw[chunk])
        for j, i in enumerate(chunk):
            out[i] = x[j].astype(np.float32)
    return out


def ev_profile(seed, pmf, config):
    """Her ev_profile(False): a generator seeded per home, charge days at ev_day_share, a start hour per day."""
    rng = np.random.default_rng(seed)
    p = np.zeros(HOURS, np.float32)
    days = np.where(rng.random(365) < deck_param("ev_day_share", config))[0]
    start = days * 24 + rng.choice(24, size=len(days), p=pmf)
    for k in range(deck_param("ev_hours", config)):
        hour = start + k
        np.add.at(p, hour[hour < HOURS], deck_param("ev_kw", config))
    return p


def run_replica(setup, config, p_ev, p_hp, unit_kwh):
    """One scenario: per transformer rating, adopters, over flag and units at each limit, both winter rules."""
    sizes = np.array(config_value(SIZES_KEY, config))
    unit_kw, cap, divisor = deck_param("unit_kw", config), replica_value("rating_cap", config), deck_param("peak_to_rating_divisor", config)
    month = pd.date_range("2025-09-01", periods=HOURS, freq="h").month.to_numpy()
    winter_month = np.isin(month, deck_param("winter_months", config))
    rng = np.random.default_rng(replica_value("adoption_seed", config))
    has_ev, has_heat, loads, pmf, hp = setup["has_ev"], setup["has_heat"], setup["loads"], setup["pmf"], setup["hp"]
    rows = []
    for group in setup["sel"]:
        base, add, nev, nhp = np.zeros(HOURS, np.float32), np.zeros(HOURS, np.float32), 0, 0
        for i in group:
            base += loads[i]
            if not has_ev[i] and rng.random() < p_ev:
                add += ev_profile(rng.integers(1e9), pmf, config)
                nev += 1
            if not has_heat[i] and rng.random() < p_hp:
                add += hp
                nhp += 1
        need = base.max() / divisor
        rating = sizes[np.searchsorted(sizes, need)] if need <= cap else sizes[-1]
        total = base + add
        over_hours = np.where(total > replica_value("winter_limit", config) * rating)[0]
        row = {"rating": rating, "nev": nev, "nhp": nhp, "winter_major": bool(len(over_hours) and winter_month[over_hours].mean() > 0.5),
               "winter_worst": bool(winter_month[int(total.argmax())])}
        for limit in deck_param("overload_limit_options", config):
            e = np.clip(total - limit * rating, 0, None).reshape(365, 24)
            tag = int(round(limit * 100))
            row[f"o{tag}"] = bool(e.max() > 0)
            row[f"u{tag}"] = 0 if e.max() <= 0 else int(max(np.ceil(e.max(1) / unit_kw).max(), np.ceil(e.sum(1) / unit_kwh).max()))
        rows.append(row)
    return pd.DataFrame(rows)


def cells_from(frame, config):
    """{limit: cell} with the deck cell's field names, from one scenario's per-transformer table."""
    cells, units_max = {}, deck_param("units_max", config)
    for limit in deck_param("overload_limit_options", config):
        tag = int(round(limit * 100))
        over, units = frame[f"o{tag}"].to_numpy(), frame[f"u{tag}"].to_numpy()
        fixed = over & (units <= units_max)
        n, share = int(over.sum()), lambda part, whole: round(100.0 * part / whole, 2) if whole else 0.0
        cells[float(limit)] = {
            "transformers": len(frame), "overloaded": n, "overloaded_pct": share(n, len(frame)), "fixed": int(fixed.sum()),
            "fixed_of_overloaded_pct": share(int(fixed.sum()), n), "upgrades": int((over & ~fixed).sum()),
            "batteries": int(units[fixed].sum()), "average_units": round(float(units[fixed].mean()), 2) if fixed.any() else 0.0,
            "winter_of_overloaded_pct": share(int((over & frame.winter_major).sum()), n),
            "winter_majority_hours_pct": share(int((over & frame.winter_major).sum()), n),
            "winter_worst_hour_pct": share(int((over & frame.winter_worst).sum()), n),
            "ev_homes": int(frame.nev.sum()), "hp_homes": int(frame.nhp.sum())}
    return cells


def replica_setup(homes, config, tiers="teammate", groups="teammate", fill="home_mean"):
    """Everything both scenarios share: eligibility, groups, home loads and the two arrays (exact bytes)."""
    has_ev, has_heat = eligibility(homes, config, tiers)
    sel = draw_groups(homes, config, groups)
    from ewu.deck_arrays import verify_array
    arrays = {name: PROCESSED / deck_param(f"{name}_file", config) for name in ("ev_start_pmf", "hp_increment")}
    for name, path in arrays.items():
        verify_array(name, path, config)
    return {"has_ev": has_ev, "has_heat": has_heat, "sel": sel, "loads": home_loads(sel, homes, fill),
            "pmf": np.load(arrays["ev_start_pmf"]), "hp": np.load(arrays["hp_increment"]),
            "options": {"tiers": tiers, "groups": groups, "fill": fill}}
