"""Build deck/v3/fact_map.yaml: for every number in outputs/deck/v3/numbers.csv, where v3 gets it from.

What: one entry per number id (text, table, notes, chart category, series name, title) and one per chart series
      (covering its points unless a point has its own entry). Status is one of
        mapped         a fact key in facts/facts.json, a config value (cfg:path), or an expression over them
        pending        the key our engine should write does not exist yet (expected name given); apply.py skips
                       it until the key exists, then applies it and says so
        keep           not a model number: data counts, market data, equipment specs, labels, years, rubric
        teammate-only  her classification, segmentation and battery-ranking work, which our engine does not compute
        no-source      a model number nothing in the repo computes; flagged for a person to decide
Why:  v3 must make every model number come from our engine (Gio, 2026-11-13: "just use our calculations"); the map
      is the reviewable record of which number comes from where, and apply.py refuses to guess.
How:  rules below, most specific first (explicit ids), then per-slide defaults. Money in the deck is on the deck's
      own basis (the upgrade at its full $15,000; batteries net of lease PV and NYSERDA), rebuilt from our engine's
      counts with the same formula the audit verified (docs/TEAMMATE_AUDIT.md section 1), so it moves when the
      counts move. One switch, aliases.peak_source, picks whose fleet supplies the peak cut and host count.
    .venv/bin/python -I deck/v3/build_fact_map.py outputs/deck/v3/numbers.csv deck/v3/fact_map.yaml
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
FACTS = json.loads((ROOT / "facts/facts.json").read_text())


def S(s, L=120):
    return f"ewu.deck.{s}.limit_{L}"


SC = {"m": "moderate", "h": "high"}
COMMON = {"nyt": "ewu.deck.nyseg_transformers", "n": "cfg:profiles.deck.transformer_count"}
PRICE = {"unit": "cfg:profiles.deck.battery_unit_usd", "lease": "ewu.deck.prices.lease_pv_usd",
         "nyserda": "cfg:profiles.deck.nyserda_usd_unit"}


def money(s, col, L=120, U="cfg:profiles.deck.upgrade_usd"):
    """NYSEG $M on the deck's basis from our counts. U = $ per upgrade (full price, as the deck shows it)."""
    k = dict(COMMON, **PRICE, over=f"{S(s, L)}.overloaded", bat=f"{S(s, L)}.batteries", upg=f"{S(s, L)}.upgrades")
    u = "U"
    if isinstance(U, str):
        k["U"] = U
    else:
        u = str(U)
    sc = "nyt / n / 1e6"
    cols = {
        "upall": f"over * {u} * {sc}",
        "net": f"(bat * (unit - lease - nyserda) + upg * {u}) * {sc}",
        "netnony": f"(bat * (unit - lease) + upg * {u}) * {sc}",
        "gross": f"(bat * unit + upg * {u}) * {sc}",
    }
    if col in cols:
        return k, cols[col]
    if col == "saving_pct":
        return k, f"100 * (1 - ({cols['net']}) / ({cols['upall']}))"
    if col == "less_capital":
        return k, f"({cols['upall']}) - ({cols['net']})"
    raise KeyError(col)


def m(key=None, fmt="{:,.0f}", keys=None, expr=None, note=None):
    e = {"status": "mapped"}
    if key:
        e["key"] = key
    if keys:
        e["keys"] = keys
        e["expr"] = expr
    e["fmt"] = fmt
    if note:
        e["note"] = note
    return e


def money_entry(s, col, fmt, L=120, U="cfg:profiles.deck.upgrade_usd", note=None):
    keys, expr = money(SC[s], col, L, U)
    return m(keys=keys, expr=expr, fmt=fmt, note=note)


def pending(expected, keys, expr, fmt, note):
    return {"status": "pending", "expected_key": expected, "keys": keys, "expr": expr, "fmt": fmt, "note": note}


def keep(note):
    return {"status": "keep", "note": note}


def mate(note):
    return {"status": "teammate-only", "note": note}


def nosrc(note, suggested=None):
    e = {"status": "no-source", "note": note}
    if suggested:
        e["suggested_key"] = suggested
    return e


PCT0, PCT1, MW1, USDM0, USDM1 = "{:.0f}%", "{:.1f}%", "{:.1f} MW", "${:,.0f}M", "${:,.1f}M"
FIX = lambda s: m(f"{S(SC[s])}.fixed_of_overloaded_pct", PCT0)
OVER0 = lambda s: m(f"{S(SC[s])}.overloaded_pct", PCT0)
WINTER = lambda s: m(f"{S(SC[s])}.winter_of_overloaded_pct", PCT0,
                     note="majority-of-over-hours rule (profiles.deck.winter_rule), the teammate's definition")
SAVE0 = lambda s: money_entry(s, "saving_pct", PCT0, note="1 - net / upgrade-all, deck basis (upgrade at full $15,000)")
UPALL0 = lambda s: money_entry(s, "upall", USDM0)
NET0 = lambda s: money_entry(s, "net", USDM0)
PEAK = m(keys={"mw": "@peak_mw"}, expr="mw", fmt=MW1, note="export fleet, drop in the single highest hour (aliases.peak_source)")
PEAK_PCT = m(keys={"mw": "@peak_mw", "sys": "insight.system_peak_mw"}, expr="100 * mw / sys", fmt=PCT0,
             note="peak cut / today's system peak")
HOSTS = m(keys={"h": "@hosts"}, expr="h", fmt="{:,.0f}", note="priority homes with 2 units (aliases.peak_source)")
UNITS = {"h": "@hosts", "per": "cfg:profiles.deck.units_per_host"}
FLEET = dict(UNITS, mw="@peak_mw", unit="cfg:profiles.deck.battery_unit_usd", lease="ewu.deck.prices.lease_pv_usd",
             nyserda="cfg:profiles.deck.nyserda_usd_unit", f="ewu.deck.prices.factor")
CAP_USD_KW_YR = 60   # the deck's market capacity value (A15: NYISO rest of state); a market input, not a model number
COST, LEASE, NYS = "h * per * unit / 1e6", "h * per * lease / 1e6", "h * per * nyserda / 1e6"
CAP = f"mw * 1000 * {CAP_USD_KW_YR} * f / 1e6"
FLEET_NOTE = "peak-only fleet economics rebuilt from host count, peak cut and the deck prices (A11 arithmetic)"

# Explicit entries, by number id from numbers.csv.
E = {
    # 2 Executive summary
    "s02/3/p0/m1": SAVE0("h"), "s02/3/p0/m2": SAVE0("m"),
    "s02/7/p0/m0": OVER0("m"), "s02/7/p0/m1": OVER0("h"),
    "s02/9/p0/m0": m("insight.system_peak_mw", MW1),
    "s02/9/p0/m1": pending("insight.system_mean_mw", {"x": "insight.system_mean_mw"}, "x", MW1,
                           "average combined load; no fact holds it yet (load factor = mean / peak)"),
    "s02/9/p0/m2": pending("insight.system_mean_mw", {"x": "insight.system_mean_mw", "p": "insight.system_peak_mw"},
                           "100 * x / p", PCT0, "load factor"),
    "s02/9/p1/m0": m("cfg:profiles.deck.peak_hours", "{:.0f}"),
    "s02/9/p1/m1": m("ewu.deck.peakcut.days", "{:.0f}"),
    "s02/9/p2/m0": WINTER("m"), "s02/9/p2/m1": WINTER("h"),
    "s02/9/p2/m2": UPALL0("m"), "s02/9/p2/m3": UPALL0("h"),
    "s02/17/p0/m0": PEAK, "s02/18/p0/m0": PEAK_PCT, "s02/18/p0/m1": HOSTS,
    "s02/19/p0/m0": FIX("h"), "s02/19/p0/m1": FIX("m"),
    "s02/19/p1/m0": NET0("m"), "s02/19/p1/m1": UPALL0("m"), "s02/19/p1/m3": NET0("h"), "s02/19/p1/m4": UPALL0("h"),
    # 3 Approach
    "s03/9/p0/m0": keep("meters promised (data.customers_promised)"), "s03/9/p0/m1": keep("hours in a year"),
    "s03/9/p0/m2": keep("labeled homes with data (181 + 86 + 395), data count"),
    "s03/10/p0/m0": keep("usable homes (data.customers_usable)"),
    # 8 When the grid peaks
    "s08/3/p0/m0": m("cfg:profiles.deck.peak_hours", "{:.0f}"), "s08/3/p0/m1": m("ewu.deck.peakcut.days", "{:.0f}"),
    "s08/6/p0/m0": m("insight.system_peak_mw", MW1),
    "s08/7/p0/m0": keep("date of the summer peak; check against insight.system_peak_when (2026-07-02 17:00)"),
    "s08/7/p0/m2": keep("hour of the summer peak; check against insight.system_peak_when"),
    "s08/7/p0/m3": m("insight.system_peak_temp_f", "{:.0f}°F"),
    "s08/8/p0/m0": m("insight.winter_peak_mw", MW1),
    "s08/9/p0/m0": keep("date of the winter peak; check against insight.winter_peak_when (2026-01-25 17:00)"),
    "s08/9/p0/m2": keep("hour of the winter peak; check against insight.winter_peak_when"),
    "s08/9/p0/m3": m("insight.winter_peak_temp_f", "{:.0f}°F"),
    "s08/10/p0/m0": pending("insight.system_mean_mw", {"x": "insight.system_mean_mw", "p": "insight.system_peak_mw"},
                            "100 * x / p", PCT0, "load factor"),
    "s08/11/p0/m0": pending("insight.system_mean_mw", {"x": "insight.system_mean_mw"}, "x", MW1, "average combined load"),
    "s08/11/p0/m1": m("insight.system_peak_mw", MW1),
    # 9 Battery homes
    "s09/3/p0/m0": HOSTS,
    # 10 Operational benefits
    "s10/3/p0/m0": HOSTS, "s10/3/p0/m1": PEAK, "s10/3/p0/m2": PEAK_PCT,
    "s10/3/p0/m3": mate("44 of the top 50 hours lowered: her program.py fleet run; our engine does not count it"),
    "s10/3/p0/m4": m("cfg:profiles.deck.peak_hours", "{:.0f}"),
    "s10/6/p0/m0": PEAK, "s10/7/p0/m0": PEAK_PCT, "s10/7/p0/m1": HOSTS,
    # 11 Business value test
    "s11/7/p0/m0": m(keys=FLEET, expr=f"({LEASE} + {CAP} + {NYS}) / ({COST})", fmt="{:.2f}", note=FLEET_NOTE),
    "s11/8/p0/m0": m(keys=FLEET, expr=f"({LEASE} + {CAP}) / ({COST})", fmt="{:.2f}", note=FLEET_NOTE),
    "s11/10/p0/m0": m(keys=FLEET, expr=COST, fmt=USDM1, note=FLEET_NOTE), "s11/10/p0/m1": HOSTS,
    "s11/10/p0/m2": m("cfg:profiles.deck.units_per_host", "{:.0f}"),
    "s11/11/p0/m0": m("cfg:profiles.deck.years", "{:.0f}"),
    "s11/11/p0/m1": m("cfg:profiles.deck.discount_rate", "{:.0%}"),
    "s11/12/p0/m0": m(keys=FLEET, expr=LEASE, fmt=USDM1, note=FLEET_NOTE),
    "s11/12/p0/m1": m(keys=FLEET, expr=CAP, fmt=USDM1, note=FLEET_NOTE + f"; capacity ${CAP_USD_KW_YR}/kW-yr"),
    "s11/12/p0/m2": m(keys=FLEET, expr=NYS, fmt=USDM1, note=FLEET_NOTE),
    "s11/12/p0/m3": m(keys=FLEET, expr=f"{LEASE} + {CAP} + {NYS}", fmt=USDM0, note=FLEET_NOTE),
    "s11/14/p0/m0": m(keys=FLEET, expr=f"({COST} - {LEASE} - {NYS}) * 1e6 / (mw * 1000 * f)", fmt="${:,.0f}",
                      note="break-even capacity value, $ per kW a year"),
    "s11/14/p0/m1": keep("market capacity value, about $60 per kW a year (A15)"),
    "s11/19/p0/m0": m(keys=dict(PRICE, am=f"{S('moderate')}.average_units", ah=f"{S('high')}.average_units"),
                      expr="round((am + ah) / 2 * (unit - lease - nyserda), -3)", fmt="${:,.0f}",
                      note="net cost per battery-fixed transformer: mean units of both scenarios x $ per unit, to the nearest $1,000"),
    "s11/20/p0/m0": m("cfg:profiles.deck.upgrade_usd", "${:,.0f}"),
    "s11/22/p0/m0": m(f"{S('moderate')}.average_units", "{:.1f}"), "s11/22/p0/m1": m(f"{S('high')}.average_units", "{:.1f}"),
    "s11/24/p0/m0": m("cfg:profiles.deck.battery_unit_usd", "${:,.0f}"),
    "s11/24/p0/m1": m(keys={"lease": "ewu.deck.prices.lease_pv_usd"}, expr="round(lease, -3)", fmt="${:,.0f}",
                      note="lease present value per unit, to the nearest $1,000"),
    "s11/24/p0/m2": m("cfg:profiles.deck.years", "{:.0f}"),
    "s11/24/p0/m3": m("cfg:profiles.deck.nyserda_usd_unit", "${:,.0f}"),
    "s11/24/p0/m4": m(keys=PRICE, expr="unit - lease - nyserda", fmt="${:,.0f}"),
    "s11/28/p0/m0": SAVE0("h"), "s11/28/p0/m1": SAVE0("m"),
    "s11/notes/p0/m0": keep("market capacity value"), "s11/notes/p0/m1": m("cfg:profiles.deck.upgrade_usd", "${:,.0f}"),
    # 12 Recommendation
    "s12/20/p0/m0": m(keys={"f": f"{S('moderate')}.fixed_of_overloaded_pct"}, expr="100 - f", fmt=PCT0,
                      note="overloads batteries cannot fix"),
    "s12/20/p0/m1": m(keys={"f": f"{S('high')}.fixed_of_overloaded_pct"}, expr="100 - f", fmt=PCT0),
    "s12/21/chart/cat0/m0": m(f"{S('moderate')}.overloaded_pct", PCT1),
    "s12/21/chart/cat1/m0": m(f"{S('high')}.overloaded_pct", PCT1),
    "s12/24/p0/m1": m("cfg:scenarios.moderate.ev_share", "{:.0%}"), "s12/24/p0/m2": m("cfg:scenarios.moderate.hp_share", "{:.0%}"),
    "s12/24/p0/m3": m("cfg:scenarios.high.ev_share", "{:.0%}"), "s12/24/p0/m4": m("cfg:scenarios.high.hp_share", "{:.0%}"),
    "s12/24/p0/m5": WINTER("m"), "s12/24/p0/m6": WINTER("h"),
    "s12/24/p0/m7": money_entry("h", "netnony", USDM0),
    "s12/notes/p0/m0": m("cfg:profiles.deck.transformer_count", "{:,.0f}"),
    "s12/notes/p0/m1": m("cfg:profiles.deck.homes_per_transformer", "{:.0f}"),
    "s12/notes/p0/m2": m("cfg:profiles.deck.overload_limit", "{:.0%}"),
    # 13 Value and implementation
    "s13/7/p1/m0": m(keys={"y": "cfg:profiles.deck.lease_usd_unit_yr", "per": "cfg:profiles.deck.units_per_host"},
                     expr="y * per / 12", fmt="${:,.0f}", note="lease per month for 2 units"),
    "s13/10/p0/m0": money_entry("m", "less_capital", USDM0), "s13/10/p0/m1": money_entry("h", "less_capital", USDM0),
    "s13/13/p0/m0": m(keys=UNITS | {"mw": "@peak_mw"}, expr="mw * 1000 / (h * per)", fmt="{:.1f} kW",
                      note="peak cut per unit"),
    "s13/13/p0/m1": m(keys=UNITS | {"mw": "@peak_mw", "nb": f"{S('moderate')}.nyseg_batteries"},
                      expr="mw / (h * per) * nb", fmt="{:,.0f}", note="kW per unit x NYSEG batteries, moderate"),
    "s13/13/p0/m2": m(keys=UNITS | {"mw": "@peak_mw", "nb": f"{S('high')}.nyseg_batteries"},
                      expr="mw / (h * per) * nb", fmt="{:,.0f} MW", note="kW per unit x NYSEG batteries, high"),
    "s13/13/p2/m0": nosrc("more energy sold, moderate: added EV and heat pump kWh over today's kWh of the sampled homes",
                          f"{S('moderate')}.added_energy_pct"),
    "s13/13/p2/m1": nosrc("more energy sold, high", f"{S('high')}.added_energy_pct"),
    # 15 Thank you
    "s15/5/p0/m0": PEAK, "s15/7/p0/m0": FIX("h"), "s15/7/p0/m1": FIX("m"),
    "s15/9/p0/m0": SAVE0("h"), "s15/9/p0/m1": SAVE0("m"),
    # A9 tiers text, A10 stress-test sizing
    "s25/5/p0/m0": HOSTS,
    "s26/4/p4/m0": m("cfg:profiles.deck.unit_kw", "{:.2f} kW"), "s26/4/p4/m1": m("cfg:profiles.deck.unit_kwh", "{:.2f} kWh"),
    # A11 fleet economics
    "s27/28/r1c1/p0/m0": HOSTS, "s27/28/r1c1/p0/m1": m("cfg:profiles.deck.units_per_host", "{:.0f}"),
    "s27/28/r1c1/p0/m2": m(keys=UNITS, expr="h * per", fmt="{:,.0f}"),
    "s27/28/r2c1/p0/m0": m(keys=FLEET, expr=COST, fmt=USDM1, note=FLEET_NOTE),
    "s27/28/r2c1/p0/m1": m("cfg:profiles.deck.battery_unit_usd", "${:,.0f}"),
    "s27/28/r3c1/p0/m0": m(keys=UNITS | {"y": "cfg:profiles.deck.lease_usd_unit_yr"}, expr="h * per * y / 1e6", fmt="${:.2f}M"),
    "s27/28/r3c1/p0/m1": m(keys=FLEET, expr=LEASE, fmt=USDM1, note=FLEET_NOTE),
    "s27/28/r3c1/p0/m2": m("cfg:profiles.deck.years", "{:.0f}"), "s27/28/r3c1/p0/m3": m("cfg:profiles.deck.discount_rate", "{:.0%}"),
    "s27/28/r4c1/p0/m0": PEAK,
    "s27/28/r4c1/p0/m2": m(keys={"mw": "@peak_mw"}, expr=f"mw * 1000 * {CAP_USD_KW_YR} / 1e6", fmt="${:.2f}M"),
    "s27/28/r4c1/p0/m3": m(keys=FLEET, expr=CAP, fmt=USDM1, note=FLEET_NOTE),
    "s27/28/r5c1/p0/m0": m("cfg:profiles.deck.nyserda_usd_unit", "${:,.0f}"),
    "s27/28/r5c1/p0/m1": m(keys=FLEET, expr=NYS, fmt=USDM1, note=FLEET_NOTE),
    "s27/28/r6c1/p0/m0": m(keys=FLEET, expr=f"({LEASE} + {CAP} + {NYS}) / ({COST})", fmt="{:.2f}"),
    "s27/28/r6c1/p0/m1": m(keys=FLEET, expr=f"({LEASE} + {CAP}) / ({COST})", fmt="{:.2f}"),
    "s27/28/r6c2/p0/m0": m("cfg:profiles.deck.years", "{:.0f}"), "s27/28/r6c2/p0/m1": m("cfg:profiles.deck.discount_rate", "{:.0%}"),
    "s27/28/r7c1/p0/m0": m(keys=FLEET, expr=f"({COST} - {LEASE} - {NYS}) * 1e6 / (mw * 1000 * f)", fmt="${:,.0f}"),
    "s27/28/r7c1/p0/m1": m(keys=FLEET, expr=f"({COST} - {LEASE}) * 1e6 / (mw * 1000 * f)", fmt="${:,.0f}"),
    # A12 stress test method
    "s28/29/r1c1/p0/m0": m("cfg:profiles.deck.transformer_count", "{:,.0f}"),
    "s28/29/r1c1/p0/m1": m("cfg:profiles.deck.homes_per_transformer", "{:.0f}"),
    "s28/29/r2c1/p0/m6": m("cfg:profiles.deck.peak_to_rating_divisor", "{:.2f}"),
    "s28/29/r3c1/p0/m0": m("cfg:profiles.deck.overload_limit", "{:.0%}"),
    "s28/29/r4c1/p0/m0": m("cfg:profiles.deck.ev_kw", "{:.1f} kW"),
    "s28/29/r4c1/p0/m2": m(keys={"d": "cfg:profiles.deck.ev_day_share"}, expr="d * 7", fmt="{:.1f}", note="sessions a week"),
    "s28/29/r4c1/p0/m3": m("cfg:profiles.deck.ev_hours", "{:.0f}"),
    "s28/29/r4c1/p0/m4": mate("20,800 observed sessions behind her EV start-hour array (ev_start_pmf); the audit rebuilds it from 266 homes x 145 mild days"),
    "s28/29/r5c1/p0/m0": m(keys={"k": "ewu.deck.inputs.hp_increment.annual_kwh"}, expr="round(k, -2)", fmt="{:,.0f} kWh"),
    "s28/29/r5c1/p0/m1": m("teammate.audit.file.hp.below_10f_kw", "{:.1f} kW",
                           note="mean of the heat pump curve below 10°F (her array, measured by our audit)"),
    "s28/29/r6c1/p0/m0": m("cfg:scenarios.moderate.ev_share", "{:.0%}"), "s28/29/r6c1/p0/m1": m("cfg:scenarios.moderate.hp_share", "{:.0%}"),
    "s28/29/r6c1/p0/m2": m("cfg:scenarios.high.ev_share", "{:.0%}"), "s28/29/r6c1/p0/m3": m("cfg:scenarios.high.hp_share", "{:.0%}"),
    "s28/29/r7c1/p0/m0": m("cfg:profiles.deck.unit_kw", "{:.2f} kW"), "s28/29/r7c1/p0/m1": m("cfg:profiles.deck.unit_kwh", "{:.2f} kWh"),
    "s28/29/r7c1/p0/m2": m("cfg:profiles.deck.units_max", "{:.0f}"),
    "s28/29/r8c1/p0/m0": m("cfg:profiles.deck.upgrade_usd", "${:,.0f}"),
    "s28/29/r9c1/p0/m0": m("cfg:prices.nyseg_electric_customers", "{:,.0f}"),
    "s28/29/r9c1/p0/m1": m("cfg:profiles.deck.homes_per_transformer", "{:.0f}"),
    "s28/29/r9c1/p0/m2": m("cfg:profiles.deck.transformer_count", "{:,.0f}"),
    "s29/5/p0/m0": m("cfg:profiles.deck.years", "{:.0f}"), "s29/5/p0/m1": m("cfg:profiles.deck.discount_rate", "{:.0%}"),
    "s29/5/p0/m2": m("cfg:profiles.deck.lease_usd_unit_yr", "${:,.0f}"), "s29/5/p0/m3": m("cfg:profiles.deck.nyserda_usd_unit", "${:,.0f}"),
}

# A13 sensitivity table: rows (scenario, limit, upgrade $), columns 3 to 9.
A13 = [("m", 110, 15000), ("m", 120, 10000), ("m", 120, 15000), ("m", 120, 20000), ("m", 140, 15000),
       ("h", 110, 15000), ("h", 120, 10000), ("h", 120, 15000), ("h", 120, 20000), ("h", 140, 15000)]
for r, (s, L, U) in enumerate(A13, 1):
    p = f"s29/30/r{r}c"
    E[p + "3/p0/m0"] = m(f"{S(SC[s], L)}.overloaded_pct", PCT1)
    E[p + "4/p0/m0"] = m(f"{S(SC[s], L)}.fixed_of_overloaded_pct", PCT0)
    E[p + "5/p0/m0"] = money_entry(s, "upall", USDM1, L, U)
    E[p + "6/p0/m0"] = money_entry(s, "net", USDM1, L, U)
    E[p + "7/p0/m0"] = money_entry(s, "netnony", USDM1, L, U)
    E[p + "8/p0/m0"] = money_entry(s, "gross", USDM1, L, U)
    E[p + "9/p0/m0"] = money_entry(s, "saving_pct", PCT1, L, U)

# Chart entries. Series ids cover every point unless a point id is listed.
for i, s in enumerate("mh"):
    E[f"s12/22/chart/ser0/pt{i}"] = money_entry(s, "upall", "{:.1f}")
    E[f"s12/22/chart/ser1/pt{i}"] = money_entry(s, "net", "{:.1f}")
    E[f"s12/21/chart/ser2/pt{i}"] = m(keys={"u": f"{S(SC[s])}.upgrades", "n": COMMON["n"]}, expr="100 * u / n",
                                      fmt="{:.1f}", note="still needs an upgrade, % of all transformers")
    for j, band in ((0, "1_2"), (1, "3_4")):
        key = f"{S(SC[s])}.fixed_units_{band}"
        E[f"s12/21/chart/ser{j}/pt{i}"] = pending(key, {"x": key, "n": COMMON["n"]}, "100 * x / n", "{:.1f}",
                                                  f"transformers fixed by {band.replace('_', ' or ')} units; the screen counts units per transformer but records no split")

SERIES = {
    "s04/5/chart/ser0": mate("homes flagged per technology (her classification)"),
    "s05/10/chart/ser0": mate("segment daily kWh by temperature"), "s05/10/chart/ser1": mate("segment daily kWh by temperature"),
    "s08/5/chart/ser0": keep("daily peak of the metered combined load: data, not model; its maximum is insight.system_peak_mw"),
    "s10/5/chart/ser0": keep("today's metered load, July 1 to 4"),
    "s10/5/chart/ser1": mate("her fleet dispatch time series (program.py); our engine records no hourly series"),
    "s10/5/chart/ser2": mate("her fleet dispatch time series with secondary homes"),
    "s10/14/chart/ser0": mate("priority homes by her segment"),
    "s25/6/chart/ser0": mate("priority homes by her segment"), "s25/6/chart/ser1": mate("secondary homes by her segment"),
}

TEAMMATE_SLIDES = {3: "approach metrics of her pipeline (classifier, k-means, runtime)", 4: "her classification",
                   5: "her classification method", 6: "her segmentation", 7: "her segments and her priority list by segment",
                   9: "her battery simulation and ranking", 10: "her fleet run", 19: "her classification",
                   20: "her classification figure", 21: "her segmentation", 22: "her segment statistics",
                   23: "her segment by technology", 24: "her battery dispatch method", 25: "her prioritization",
                   26: "her sizing check"}
KEEP_SLIDES = {1: "title", 14: "scalability text", 16: "appendix index", 17: "data preparation counts", 18: "feature dictionary",
               30: "ownership and program design", 31: "market data and public sources", 32: "limitations", 33: "tool description"}


def default(row):
    sid, kind, num, text, unit = int(row["slide"]), row["kind"], row["number"], row["text"], row["unit"]
    if kind == "picture":
        return {"status": "picture", "note": "baked into an image; cannot be edited in place", "shows": text,
                "numbers_in_image": num}
    if unit in ("year", "label"):
        return keep("year or label")
    if (kind == "text" and text.strip() == num and len(num) == 1) or re.search(r"\b(PART|Part) " + re.escape(num) + r"\b", text):
        return keep("step or part number")
    if num == "33,757":
        return keep("usable homes, a data count (data.customers_usable)")
    if "Cornell 2" in text and num == "2":
        return keep("team name")
    if "3 or 4 batteries" in text:
        return keep("chart legend: unit band")
    if sid == 8 and num in ("60", "6"):
        return mate("her battery simulation's event days and hours (battery_sim.py); our peak cut uses the top 50 hours")
    if "Pilot" in text or "lease batteries to about" in text:
        return keep("pilot size, a proposal")
    if "IQ 10C" in text and num == "10":
        return keep("equipment model name")
    if kind == "chart_category":
        return keep("chart axis label (date or hour)")
    if sid in TEAMMATE_SLIDES:
        return mate(TEAMMATE_SLIDES[sid])
    if sid in KEEP_SLIDES:
        return keep(KEEP_SLIDES[sid])
    if re.search(r"\b1 or 2\b|2 units?\b|2 Enphase|2 x IQ|2 unit\b", text) and num in ("1", "2"):
        return keep("units per home, a program rule")
    if sid == 28:
        return keep("method input, rubric or public value")
    if sid == 29 and kind == "table":
        return keep("scenario label (limit, upgrade cost)")
    if sid == 29:
        return keep("upgrade prices named in the footer claim; the claim itself is checked under claims")
    if sid == 27:
        return keep("market data or price basis")
    return nosrc("no rule placed this number; decide by hand")


def build(csv_path):
    rows = list(csv.DictReader(open(csv_path)))
    entries, seen_series = {}, set()
    for r in rows:
        rid = r["id"]
        if r["kind"] == "chart_value":
            ser = rid.rsplit("/", 1)[0]
            if rid in E:
                spec = E[rid]
            elif ser in seen_series:
                continue
            else:
                seen_series.add(ser)
                spec = SERIES.get(ser) or (mate(TEAMMATE_SLIDES[int(r["slide"])]) if int(r["slide"]) in TEAMMATE_SLIDES
                                          else nosrc("chart series with no rule"))
                rid = ser
                old = f"series '{r['text'].split(' @ ')[0]}', {sum(1 for x in rows if x['id'].startswith(ser + '/'))} points"
                entries[rid] = dict(slide=int(r["slide"]), kind="chart_series", old=old, **spec)
                continue
        elif r["kind"] == "chart_category" and rid not in E:
            cats = rid.split("/cat")[0] + "/categories"
            if cats not in entries:
                n = sum(1 for x in rows if x["id"].startswith(cats.replace("/categories", "/cat")))
                entries[cats] = dict(slide=int(r["slide"]), kind="chart_categories", old=f"{n} numbers in category labels",
                                     text=r["text"][:160], **keep("chart axis labels (dates, hours, names)"))
            continue
        else:
            spec = E.get(rid) or default(r)
        entries[rid] = dict(slide=int(r["slide"]), kind=r["kind"], old=r["number"], text=r["text"][:160], **spec)
    missing = sorted(set(E) - set(entries))
    if missing:
        sys.exit(f"explicit ids not in the inventory (deck changed?): {missing}")
    return entries


ALIASES = {"peak_source": {
    "selected": "teammate_rerun",
    "why": ("teammate_rerun keeps Part 3 coherent: the 2,610 priority homes, her per-segment counts (slides 7, 10, A9), "
            "the scatter legend (slide 9) and the July fleet chart (slide 10) all describe her ranking, and our audit's "
            "rerun of her code on our load matrix gives the peak cut for exactly those homes. 'ours' takes our engine's "
            "own hosts (same 4 kW and 2 kW thresholds, our simulation) and peak drop; then those teammate-only numbers "
            "no longer add up to the host count and need a caption or new charts."),
    "teammate_rerun": {"peak_mw": "teammate.audit.rerun.fleet_priority.peak_cut_mw", "hosts": "teammate.audit.rerun.priority_homes"},
    "ours": {"peak_mw": "ewu.deck.peakcut.export_peak_drop_mw", "hosts": "ewu.deck.peakcut.hosts"},
}}

CLAIMS = [
    {"where": "s29/5 A13 footer", "says": "battery path cheaper before offsets at $15,000 or more per upgrade",
     "keys": None, "expr": "gross('m', 120, 15000) < upall('m', 120, 15000) and gross('h', 120, 15000) < upall('h', 120, 15000)"},
    {"where": "s29/5 A13 footer", "says": "costlier before offsets in the high case at $10,000",
     "keys": None, "expr": "gross('h', 120, 10000) > upall('h', 120, 10000)"},
    {"where": "s11 verdict", "says": "peak-only fleet does not pay on its own (benefit to cost below 1)",
     "keys": FLEET, "expr": f"({LEASE} + {CAP} + {NYS}) / ({COST}) < 1"},
    {"where": "s12 title, s2", "says": "1 or 2 batteries fix most overloaded transformers",
     "keys": {"fm": f"{S('moderate')}.fixed_of_overloaded_pct", "fh": f"{S('high')}.fixed_of_overloaded_pct"},
     "expr": "fm > 50 and fh > 50"},
    {"where": "s7 vs s2", "says": "winter nights drive most future overloads",
     "keys": {"wm": f"{S('moderate')}.winter_of_overloaded_pct", "wh": f"{S('high')}.winter_of_overloaded_pct"},
     "expr": "wm > 50 and wh > 50"},
]

if __name__ == "__main__":
    entries = build(sys.argv[1])
    out = Path(sys.argv[2])
    doc = {"about": ("Where each number of the D4G deck comes from in v3. Built by deck/v3/build_fact_map.py from "
                     "outputs/deck/v3/numbers.csv; read by deck/v3/apply.py. Keys: facts/facts.json; cfg:path = "
                     "config/ewu.yaml value; @name = aliases.peak_source.<selected>.name. Money is on the deck's basis "
                     "(upgrade at its full price), rebuilt from our counts."),
           "aliases": ALIASES, "claims": CLAIMS, "entries": entries}
    class NoAlias(yaml.SafeDumper):
        def ignore_aliases(self, data):
            return True
    out.write_text(yaml.dump(doc, Dumper=NoAlias, sort_keys=False, allow_unicode=True, width=140))
    c = Counter(e["status"] for e in entries.values())
    print(f"{len(entries)} entries to {out}: " + ", ".join(f"{k} {v}" for k, v in sorted(c.items())))
    absent = sorted({k for e in entries.values() if e["status"] in ("mapped", "pending")
                     for k in list((e.get("keys") or {}).values()) + [e.get("key")]
                     if k and not k.startswith(("cfg:", "@")) and k not in FACTS})
    print("keys not in facts.json now:", absent)
