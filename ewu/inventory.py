"""Inventory: one row per home with its equipment, how sure we are, its segment and the programs it can join.

What: build_inventory() reads the classified and segmented homes and returns one row per home: every
      equipment flag, a confidence word per flag, the EV and heat pump owner probabilities, the segment and
      one column per program saying eligible or not; summarize_inventory() turns that into counts;
      record_inventory() writes the counts and one Composite home per demo segment to facts;
      print_inventory() prints the aggregate table. Rows go to outputs/private/inventory.parquet.
Why:  the challenge asks for "a tool applied to hourly loads that will estimate inventory of heating and
      cooling appliances, and identify customers eligible for utility programs, BESS, etc." This is that
      tool's front door, and every later step (screen, batteries, money) works from the same homes.
How:  flags and probabilities come from analysis/classify.py, segment and battery tier from analysis/segment.py
      and analysis/bess.py (no new modelling here). Each flag's confidence word is the one classify.py
      recorded for its class. A home is eligible for a program when it has every flag in the program's rule
      in config/ewu.yaml and none of the excluded flags. The demo shows no real home: for each segment named
      in config it shows a Composite home, the average of every home in that segment (mean load by hour,
      mean kWh by month, share of homes with each device and in each program), so the page and the video
      carry segment aggregates only and nothing per home leaves the private table.
"""
import json
import numpy as np
import pandas as pd
from ewu import PROCESSED, ROOT, config_value

PRIVATE_TABLE = ROOT / "outputs" / "private" / "inventory.parquet"
CLASSES = ("ac", "ac_central", "electric_heat", "heat_pump", "resistance_heat", "ev_l2", "ev_l1", "solar",
           "solar_battery", "pool", "hot_tub", "water_heater", "other_seasonal", "other_inactive", "other_flat_large")
PROBABILITIES = {"ev_l2": "p_ev", "heat_pump": "p_heat_pump"}


def read_class_facts():
    """{class: {count, confidence}} as analysis/classify.py recorded them."""
    facts = json.loads((ROOT / "facts" / "facts.json").read_text())
    return {name: {"count": facts[f"class.{name}.count"]["value"], "confidence": facts[f"class.{name}.confidence"]["value"]}
            for name in CLASSES}


def program_rules(config):
    """{program: [flags it needs]} and the flags that rule a home out, all read from config."""
    rules = {name: entry["value"] for name, entry in config["programs"]["rules"].items()}
    return rules, config_value("programs.excluded_flags", config)


def build_inventory(config):
    """One row per home: flags, confidence words, probabilities, segment and program eligibility."""
    columns = ["CUSTOMER_NUMBER", "segment", "annual_kwh", "peak_kw", "bess_tier", "bess_units",
               *PROBABILITIES.values(), *[f"is_{c}" for c in CLASSES]] + [f"kwh_m{m:02d}" for m in range(1, 13)]
    homes = pd.read_parquet(PROCESSED / "bess.parquet", columns=columns)
    homes["is_bess_candidate"] = homes["bess_tier"].fillna("") != ""
    words = read_class_facts()
    for name in CLASSES:
        homes[f"confidence_{name}"] = np.where(homes[f"is_{name}"], str(words[name]["confidence"]), "")
    rules, excluded = program_rules(config)
    ruled_out = homes[excluded].any(axis=1)
    for program, needs in rules.items():
        homes[f"eligible_{program}"] = homes[needs].all(axis=1) & ~ruled_out
    return homes


def summarize_inventory(homes, config):
    """Counts and shares by equipment class, segment and program (aggregates only)."""
    whole = len(homes)
    share = lambda n: round(100.0 * n / whole, 2)
    rules, _ = program_rules(config)
    words = read_class_facts()
    return {"homes": whole,
            "classes": {c: {"count": int(homes[f"is_{c}"].sum()), "share_pct": share(homes[f"is_{c}"].sum()),
                            "confidence": words[c]["confidence"]} for c in CLASSES},
            "segments": {s: {"count": int(n), "share_pct": share(n)} for s, n in homes["segment"].value_counts().items()},
            "programs": {p: {"count": int(homes[f"eligible_{p}"].sum()), "share_pct": share(homes[f"eligible_{p}"].sum())}
                         for p in rules},
            "any_program": share(homes[[f"eligible_{p}" for p in rules]].any(axis=1).sum()),
            "unassigned_segment": int((homes["segment"].fillna("") == "").sum())}


def segment_mean_load(load, rows, chunk=2000):
    """Mean kW by hour of the year over the given homes, read in chunks so the memory-mapped matrix stays on disk."""
    total = np.zeros(load.shape[1], dtype=np.float64)
    for first in range(0, len(rows), chunk):
        total += np.asarray(load[rows[first:first + chunk]], dtype=np.float64).sum(0)
    return total / len(rows)


def day_shape(load_row, months, index):
    """Mean kW by hour of day over the given months."""
    on = np.isin(index.month, months)
    return np.asarray(load_row, dtype=np.float64)[on].reshape(-1, 24).mean(0)


def composite_homes(homes, load, config, index):
    """Per configured segment, the Composite home: averages over every home in the segment, never one home."""
    rules, _ = program_rules(config)
    words = read_class_facts()
    two = lambda a: [round(float(x), 2) for x in a]
    out = []
    for segment in config_value("demo.picker_segments", config):
        rows = np.flatnonzero(homes["segment"].to_numpy() == segment)
        group = homes.iloc[rows]
        share = lambda column: round(100.0 * float(group[column].mean()), 2)
        flags = sorted((c for c in CLASSES if group[f"is_{c}"].any()), key=lambda c: -group[f"is_{c}"].mean())
        programs = sorted((p for p in rules if group[f"eligible_{p}"].any()), key=lambda p: -group[f"eligible_{p}"].mean())
        mean_load = segment_mean_load(load, rows)
        home = {"segment": segment, "homes": len(rows), "annual_kwh": int(round(group["annual_kwh"].mean())),
                "peak_kw": round(float(group["peak_kw"].mean()), 2),
                "monthly_kwh": two(group[[f"kwh_m{m:02d}" for m in range(1, 13)]].mean()),
                "flags": flags, "flag_share_pct": [share(f"is_{c}") for c in flags],
                "confidence": [str(words[c]["confidence"]) for c in flags],
                "programs": programs, "program_share_pct": [share(f"eligible_{p}") for p in programs]}
        home |= {column: round(float(group[column].mean()), 2) for column in PROBABILITIES.values()}
        for season in ("winter", "summer"):
            shape = day_shape(mean_load, config_value(f"battery.{season}_months", config), index)
            home[f"{season}_day_kw"], home[f"{season}_day_peak_kw"] = two(shape), round(float(shape.max()), 2)
        out.append(home)
    return out


UNITS = {"segment": "segment", "homes": "homes averaged", "annual_kwh": "kWh, segment mean",
         "peak_kw": "kW, segment mean of each home's highest hour", "monthly_kwh": "kWh by month, segment mean",
         "flags": "equipment found in the segment", "flag_share_pct": "% of segment homes with each device",
         "confidence": "confidence word per device class", "programs": "programs any segment home qualifies for",
         "program_share_pct": "% of segment homes eligible", "p_ev": "probability, segment mean",
         "p_heat_pump": "probability, segment mean", "winter_day_kw": "kW by hour of day, segment mean load",
         "summer_day_kw": "kW by hour of day, segment mean load", "winter_day_peak_kw": "kW, top of the mean day",
         "summer_day_peak_kw": "kW, top of the mean day"}


def record_inventory(summary, homes, load, config):
    """Counts and the Composite homes to facts/facts.json; old single-home demo rows leave the private file."""
    from analysis.facts import forget, record
    record("ewu.inventory.homes", summary["homes"], "homes", "one row per usable home")
    for c, v in summary["classes"].items():
        record(f"ewu.inventory.class.{c}.count", v["count"], "homes", "flag from analysis/classify.py")
        record(f"ewu.inventory.class.{c}.share_pct", v["share_pct"], "% of homes", "")
    for s, v in summary["segments"].items():
        record(f"ewu.inventory.segment.{s}.count", v["count"], "homes", "segment from analysis/segment.py")
        record(f"ewu.inventory.segment.{s}.share_pct", v["share_pct"], "% of homes", "")
    for p, v in summary["programs"].items():
        record(f"ewu.inventory.program.{p}.count", v["count"], "homes", "every flag in the config rule, none excluded")
        record(f"ewu.inventory.program.{p}.share_pct", v["share_pct"], "% of homes", "")
    record("ewu.inventory.any_program_pct", summary["any_program"], "% of homes", "eligible for at least one program")
    forget("ewu.demo.", private=True)
    forget("ewu.demo.composite_")
    index = pd.read_parquet(PROCESSED / "weather.parquet").index
    for i, home in enumerate(composite_homes(homes, load, config, index)):
        for name, value in home.items():
            record(f"ewu.demo.composite_{i}.{name}", value, UNITS[name], "Composite home: average of every home in the segment")
    record("ewu.demo.home_count", len(config_value("demo.picker_segments", config)), "Composite homes", "one per picker segment")


def print_inventory(summary):
    print(f"Inventory: {summary['homes']:,} homes, one row each in outputs/private/inventory.parquet\n")
    print(f"{'equipment':<18} {'homes':>7} {'% homes':>8}  confidence")
    for c, v in summary["classes"].items():
        print(f"{c:<18} {v['count']:>7,} {v['share_pct']:>8.2f}  {v['confidence']}")
    print(f"\n{'segment':<18} {'homes':>7} {'% homes':>8}")
    for s, v in summary["segments"].items():
        print(f"{s:<18} {v['count']:>7,} {v['share_pct']:>8.2f}")
    print(f"\n{'program':<24} {'eligible':>8} {'% homes':>8}")
    for p, v in summary["programs"].items():
        print(f"{p:<24} {v['count']:>8,} {v['share_pct']:>8.2f}")
    print(f"\nEligible for at least one program: {summary['any_program']:.2f}% of homes")
