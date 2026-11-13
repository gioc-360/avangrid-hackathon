"""Teammate audit facts: the aggregates behind docs/TEAMMATE_AUDIT.md, from her files and our rerun of her code.

What: reads the teammate's downloaded folder as data (result JSONs, program_scenarios.csv, the arrays, the
      candidate list, her source text for its seeds) and the scratch outputs of checks/teammate_rerun.py, and
      records sums, shares and counts under teammate.audit.* in facts/facts.json. No customer row is written.
Why:  the audit says which deck headline her code reproduces and why the others differ; every number in it
      must trace to a fact (checks/trace_numbers.py), and the folder's customer-level files must not reach git.
How:  file.* = what her saved results say; rerun.* = her scripts run unchanged in scratch on our load matrix
      (identical layout to her kwh.npy); rebuild.* = her array recipe rerun; sens.* = her transformer run with
      the start-hour array her script as written gives; econ.* = the deck's money arithmetic recomputed from
      the rerun counts with the deck profile inputs in config/ewu.yaml.
"""
import argparse, json, re, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis.facts import record, forget, FACTS

FOLDER = Path.home() / "Downloads" / "_prototype"
WORK = Path("/private/tmp/claude-501/teammate_audit")
P = "teammate.audit."
SCEN = {"moderate": ("Moderate", "Moderate 2030 (20% EV, 15% HP)"), "high": ("High", "High 2030 (35% EV, 30% HP)")}


def note_fact(key, value, unit, method):
    record(P + key, value, unit, method)


def annuity(years, rate=0.07):
    return (1 - (1 + rate) ** -years) / rate


def transformer_view(frame, limit=120):
    """Shares, counts and money for one scenario's per-transformer rerun table at one limit."""
    over = frame[f"o{limit}"]
    fixed = over & (frame[f"u{limit}"] <= 4)
    upgrade = over & (frame[f"u{limit}"] > 4)
    units = int(frame.loc[fixed, f"u{limit}"].sum())
    scale, eq = 890000 / 8 / len(frame), annuity(15) / annuity(40)
    lease = 330 * annuity(15)
    money = {}
    for tag, f in (("eq", eq), ("full", 1.0)):
        up = upgrade.sum() * 15000 * f
        money[tag] = {"trad": over.sum() * 15000 * f * scale / 1e6, "gross": (units * 7000 + up) * scale / 1e6,
                      "net": (units * (7000 - lease - 2016) + up) * scale / 1e6,
                      "net_no_nyserda": (units * (7000 - lease) + up) * scale / 1e6}
    winter = (frame.winter & frame.over_u).sum() / max(frame.over_u.sum(), 1) * 100
    return {"overloaded_pct": over.mean() * 100, "overloaded": int(over.sum()), "fixed_pct": fixed.sum() / over.sum() * 100,
            "units": units, "mean_units": units / fixed.sum(), "upgrades": int(upgrade.sum()), "winter_pct": winter,
            "batteries_nyseg": units * scale, "money": money}


def fleet_cut(sysload_mw, homes, energy=16.128, power=7.68):
    """Her program.py fleet: each top-50 day shaved to a flat line by the pooled fleet; (peak cut, mean top-50 cut)."""
    days, top = sysload_mw.reshape(365, 24).copy(), np.argsort(-sysload_mw)[:50]
    for d in np.unique(top // 24):
        load, e_all, p_all = days[d].copy(), homes * energy / 1000, homes * power / 1000
        low, high = 0, load.max()
        for _ in range(50):
            mid = (low + high) / 2
            used = np.minimum(np.clip(load - mid, 0, None), p_all).sum()
            low, high = (mid, high) if used > e_all else (low, mid)
        days[d] = load - np.minimum(np.clip(load - high, 0, None), p_all)
    after = days.ravel()
    return sysload_mw.max() - after.max(), (sysload_mw[top] - after[top]).mean()


def her_files(folder):
    econ = json.load(open(folder / "ewu_bo2_econ.json"))
    res = json.load(open(folder / "ewu_results.json"))
    smart = json.load(open(folder / "ewu_econ.json"))
    for s, (cap, long) in SCEN.items():
        row = econ[f"{cap}_120_15000_eq"]
        for k in ("overloaded", "fixed", "mean_units", "trad_M", "gross_M", "net_M", "netnoNY_M"):
            note_fact(f"file.{s}.{k.lower()}", row[k], "as saved", f"ewu_bo2_econ.json {cap}_120_15000_eq.{k}")
        note_fact(f"file.{s}.trad_full_m", econ[f"{cap}_120_15000_full"]["trad_M"], "$M", "ewu_bo2_econ.json _full key")
        for k in ("overloaded", "winter_driven", "need_battery", "fixed_by_managed_EV"):
            note_fact(f"file.{s}.results_{k.lower()}", res[long][k], "% of transformers or of overloaded", f"ewu_results.json {k}")
        sm = smart[cap]
        note_fact(f"file.{s}.smart_extra", sm["fixed_by_smart_EV"] + sm["need_battery"] + sm["still_upgrade"] - sm["overloaded"],
            "transformers overloaded only under smart charging", "ewu_econ.json fixed + battery + upgrade - overloaded")
    prog = pd.read_csv(folder / "program_scenarios.csv")
    pri = prog.iloc[1]
    note_fact("file.program.priority_homes", int(re.search(r"\(([\d,]+)\)", pri.Scenario).group(1).replace(",", "")), "homes", "program_scenarios.csv row 2 name")
    note_fact("file.program.peak_cut_mw", pri["Peak cut MW"], "MW", "program_scenarios.csv Peak cut MW, priority row")
    note_fact("file.program.top50_cut_mw", prog.iloc[0]["Avg of top 50 original hours MW"] - pri["Avg of top 50 original hours MW"],
        "MW", "drop in the mean of the top 50 hours, priority row")
    note_fact("file.program.peak_today_mw", prog.iloc[0]["Peak MW"], "MW", "program_scenarios.csv today peak")
    cand = pd.read_csv(folder / "battery_candidates.csv", index_col=0, keep_default_na=False)
    prio = cand[cand.tier == "Priority"]
    note_fact("file.candidates.priority", len(prio), "homes", "battery_candidates.csv tier Priority")
    note_fact("file.candidates.priority_two_units", int((prio.units == 2).sum()), "homes", "priority rows with 2 units")
    note_fact("file.candidates.btm_mw", prio.red_top50.sum() / 1000, "MW", "sum of red_top50 over priority homes")
    note_fact("file.candidates.btm_kw_per_home", prio.red_top50.mean(), "kW", "mean red_top50 over priority homes")
    seg = pd.read_csv(folder / "segment_technology_reduction.csv")
    note_fact("file.thermostat_technical_mw", seg["Thermostat MW technical"].sum(), "MW", "segment_technology_reduction.csv sum")
    cls = pd.read_csv(folder / "customer_classification.csv", index_col=0, usecols=[0])
    note_fact("file.customers", len(cls), "customers", "rows of customer_classification.csv")
    note_fact("file.customers_10001_20000", int(((cls.index > 10000) & (cls.index <= 20000)).sum()), "customers", "ids in 10,001 to 20,000")
    pmf, hp = np.load(folder / "ev_start_pmf.npy"), np.load(folder / "hp_increment.npy")
    note_fact("file.pmf.hour0_pct", pmf[0] * 100, "% of starts", "ev_start_pmf.npy[0]")
    note_fact("file.pmf.hours_15_22_pct", pmf[15:23].sum() * 100, "% of starts", "ev_start_pmf.npy 15 to 22")
    temp = pd.read_parquet(Path(__file__).resolve().parent.parent / "data/processed/weather.parquet").temp.to_numpy()
    month = pd.date_range("2025-09-01", periods=8760, freq="h").month
    note_fact("file.hp.annual_kwh", hp.sum(), "kWh per adopter per year", "hp_increment.npy sum")
    note_fact("file.hp.max_kw", hp.max(), "kW", "hp_increment.npy max")
    note_fact("file.hp.below_10f_kw", hp[temp < 10].mean(), "kW", "mean over hours below 10 F")
    note_fact("file.hp.nov_mar_kwh", hp[np.isin(month, [11, 12, 1, 2, 3])].sum(), "kWh", "November to March")
    note_fact("file.hp.jun_aug_kwh", hp[np.isin(month, [6, 7, 8])].sum(), "kWh", "June to August")
    src = (folder / "ewu_sim_bo2.py").read_text()
    note_fact("code.grouping_seed", int(re.search(r"^rng=np.random.default_rng\((\d+)\)", src, re.M).group(1)), "seed", "ewu_sim_bo2.py:2")
    note_fact("code.unit_kwh", float(re.search(r"UNIT_P,UNIT_E=[\d.]+,([\d.]+)", src).group(1)), "kWh", "ewu_sim_bo2.py:7")
    note_fact("code.fleet_kwh", float(re.search(r"E=([\d.]+)", (folder / "code/program.py").read_text()).group(1)), "kWh", "program.py:4")
    block = re.search(r"\[1-(\d+), (\d+)-\d+\]", (folder / "code/config.yaml").read_text())
    note_fact("code.skipped_ids_from", int(block.group(1)) + 1, "customer id", "config.yaml:6")
    note_fact("code.adoption_seed", int(re.search(r"d=run\(pe,ph,(\d+)\)", src).group(1)), "seed", "ewu_sim_bo2.py:54")


def rerun(folder, work):
    run = work / "run"
    saved = json.load(open(folder / "ewu_results.json"))
    again = json.load(open(run / "ewu_results.json"))
    note_fact("rerun.results_fields_equal", sum(saved[s][k] == again[s][k] for s in saved for k in saved[s]), "fields", "ewu_results.json saved vs rerun")
    note_fact("rerun.results_fields", sum(len(v) for v in saved.values()), "fields", "ewu_results.json fields")
    econ = json.load(open(folder / "ewu_bo2_econ.json"))
    for s, (cap, _) in SCEN.items():
        frame = pd.read_csv(run / f"ewu_bo2_{cap}.csv")
        v = transformer_view(frame)
        for k in ("overloaded_pct", "overloaded", "fixed_pct", "units", "mean_units", "upgrades", "winter_pct", "batteries_nyseg"):
            note_fact(f"rerun.{s}.{k}", v[k], "", "her ewu_sim_bo2.py rerun, limit 1.20")
        for tag, m in v["money"].items():
            for k, x in m.items():
                note_fact(f"rerun.{s}.{tag}.{k}_musd", x, "$M across NYSEG", "deck money arithmetic on the rerun counts")
        row = econ[f"{cap}_120_15000_eq"]
        same = [round(v["money"]["eq"][a], 1) == row[b] for a, b in (("trad", "trad_M"), ("gross", "gross_M"), ("net", "net_M"), ("net_no_nyserda", "netnoNY_M"))]
        note_fact(f"rerun.{s}.money_fields_equal", sum(same), "of 4 money fields", "rerun vs ewu_bo2_econ.json at one decimal")
        note_fact(f"rerun.{s}.overloaded_pct_100", transformer_view(frame, 100)["overloaded_pct"], "%", "limit 1.00")
        note_fact(f"rerun.{s}.rating_capped", int((frame.base_peak / 0.85 > 167).sum()), "transformers", "peak / 0.85 above 167 kVA")
        managed = pd.read_csv(run / f"ewu_{cap}.csv")
        note_fact(f"rerun.{s}.managed_over_pct", managed.over_m.mean() * 100, "%", "ewu_sim.py managed rule, over limit")
        note_fact(f"rerun.{s}.managed_only", int((managed.over_m & ~managed.over_u).sum()), "transformers", "over only when managed")
        sens = transformer_view(pd.read_csv(work / "sens" / f"ewu_bo2_{cap}.csv"))
        for k in ("overloaded_pct", "fixed_pct", "mean_units", "winter_pct"):
            note_fact(f"sens.{s}.{k}", sens[k], "", "ewu_sim_bo2.py with the start-hour array her script as written gives")
        rc = json.load(open(run / "recharge.json"))[cap]
        note_fact(f"rerun.{s}.recharge_fixed", rc["fixed"], "transformers", "battery-fixed at 1.20")
        note_fact(f"rerun.{s}.recharge_still_over", rc["still_over"], "transformers", "above 1.20 once batteries recharge from headroom")
        note_fact(f"rerun.{s}.recharge_worst_kw", rc["worst_kw"], "kW", "largest hour left above the limit")
    sim = pd.read_csv(run / "battery_sim.csv", index_col=0)
    cls = pd.read_csv(run / "classification.csv", index_col=0, keep_default_na=False)
    sim = sim.loc[cls.index]
    prio = (sim.load_top50 >= 4) & (sim.red2_top50 >= 2.0)
    note_fact("rerun.priority_homes", int(prio.sum()), "homes", "battery_sim.py + rank.py thresholds")
    note_fact("rerun.btm_mw", sim.loc[prio, "red2_top50"].sum() / 1000, "MW", "sum of 2-unit cut over the top 50 hours")
    sysload = np.load(run / "system_load.npy") / 1000
    for homes, tag in ((int(prio.sum()), "priority"), (int(json.load(open(FACTS))["ewu.deck.peakcut.hosts"]["value"]), "our_hosts")):
        peak, mean = fleet_cut(sysload, homes)
        note_fact(f"rerun.fleet_{tag}.peak_cut_mw", peak, "MW", "her program.py fleet, peak minus new peak")
        note_fact(f"rerun.fleet_{tag}.top50_cut_mw", mean, "MW", "her program.py fleet, mean cut over the top 50 hours")
    ids = cls.index.to_numpy()
    rng = np.random.default_rng(11)
    sel = np.array([rng.choice(len(ids), 8, replace=False) for _ in range(3000)])
    homes, count = np.unique(sel, return_counts=True)
    note_fact("rerun.sample.distinct_homes", len(homes), "homes", "homes drawn into the 3,000 groups")
    note_fact("rerun.sample.repeated_homes", int((count > 1).sum()), "homes", "homes in two or more groups")
    load = np.load(run / "kwh.npy", mmap_mode="r")
    note_fact("rerun.sample.nan_pct", float(np.isnan(np.asarray(load[ids[homes] - 1])).mean() * 100), "% of hours", "missing hours filled with the home mean")
    built = work / "rebuild"
    note_fact("rebuild.hp_max_diff_kw", float(np.abs(np.load(built / "hp_increment.npy") - np.load(folder / "hp_increment.npy")).max()), "kW", "her recipe on our data vs her array")
    note_fact("rebuild.pmf_hour0_pct", float(np.load(built / "ev_start_pmf.npy")[0] * 100), "% of starts", "her recipe as written")
    diag = json.load(open(built / "pmf_diag.json"))
    note_fact("rebuild.pmf_continuous_hour0_pct", diag["continuous_hour0"] * 100, "% of starts", "sessions run across midnight")
    note_fact("rebuild.pmf_continuous_diff_pts", float(np.abs(np.load(built / "pmf_continuous.npy") - np.load(folder / "ev_start_pmf.npy")).max() * 100), "points", "max over 24 hours")
    note_fact("rebuild.hour0_carried_pct", diag["hour0_carried_from_23"] / diag["hour0_starts"] * 100, "% of hour-0 starts", "already charging at 23:00")
    note_fact("rebuild.ev_source_homes", diag["source_homes"], "homes", "High tier EV homes"); note_fact("rebuild.mild_days", diag["mild_days"], "days", "45 to 68 F")
    feats = pd.read_csv(built / "features_all.csv", index_col=0)
    note_fact("rebuild.hp_source_homes", int(((cls.electric_heat == "Primary") & (feats.loc[cls.index, "lab_HP"] == 1)).sum()), "homes", "labeled HP and primary electric heat")
    note_fact("rebuild.hp_reference_pool", int(((cls.electric_heat == "No") & (cls.air_conditioning == "Central likely")).sum()), "homes", "no electric heat, central AC")


def money_arithmetic():
    note_fact("econ.a15", annuity(15), "years", "annuity factor 15 years at 7%"); note_fact("econ.a40", annuity(40), "years", "40 years at 7%")
    note_fact("econ.upgrade_15_of_40_usd", 15000 * annuity(15) / annuity(40), "$", "15,000 x a15 / a40")
    note_fact("econ.nyseg_scale", 890000 / 8 / 3000, "NYSEG transformers per modeled transformer", "890,000 / 8 / 3,000")
    note_fact("econ.nyseg_transformers", 890000 / 8, "transformers", "890,000 / 8")
    note_fact("econ.lease_pv_usd", 330 * annuity(15), "$ per unit", "330 x a15")
    note_fact("econ.avangrid_unit_usd", 7000 - 330 * annuity(15) - 2016, "$ per unit", "7,000 - lease PV - 2,016")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", type=Path, default=FOLDER)
    ap.add_argument("--work", type=Path, default=WORK)
    a = ap.parse_args()
    forget(P)
    her_files(a.folder); rerun(a.folder, a.work); money_arithmetic()
    print("recorded", sum(k.startswith(P) for k in json.load(open(Path(__file__).resolve().parent.parent / "facts/facts.json"))), "facts")
