"""Export the model's aggregate inputs and outputs to results/, so a reader can check the model without the meter data.

What: writes results/ from the engine and the processed data: the system's hourly load (sum of 33,757 homes), the EV
      charging start-hour shares and the added heat pump load per home (both averaged over many homes), the segment
      tables, the battery plan's transformer action lists for both 2030 scenarios (3,000 synthetic transformers, 8-home
      sums, no home named), and the screen's results at every loading limit, read from facts/facts.json.
Why:  the challenge statement says the data "is for use during and as part of the Hackathon only. Under no circumstances
      should the data be shared or utilized outside of scope of this event." So no meter row, customer id or label
      list is published; every file here is a total, an average over many homes, or a synthetic-transformer result.
How:  .venv/bin/python -I analysis/export_results.py [SEGMENT_DIR]   (needs data/processed; SEGMENT_DIR holds the
      segment_summary.csv and segment_technology_matrix.csv of the classification run the deck uses). Fails if any
      written column looks like a customer or meter id.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results"
PROC = ROOT / "data" / "processed"
ID_WORDS = {"customer", "customers", "meter", "account", "premise", "id", "cust"}
SYNTHETIC_IDS = {"transformer_id", "feeder_id"}   # names of synthetic groups, not people
SEGMENT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Downloads" / "_prototype"


def write(df, name, note):
    bad = [c for c in df.columns if c not in SYNTHETIC_IDS and ID_WORDS & set(str(c).lower().replace(" ", "_").split("_"))]
    assert not bad, f"{name}: id-like columns {bad}"
    path = OUT / name
    with path.open("w") as fh:
        fh.write(f"# {note}\n")
        df.to_csv(fh, index=False)
    print(f"{name:42s} {len(df):>6,} rows")


def main():
    OUT.mkdir(exist_ok=True)
    hours = pd.read_parquet(PROC / "weather.parquet").index
    sysload = np.load(PROC / "sysload.npy")
    assert len(sysload) == len(hours) == 8760
    write(pd.DataFrame({"hour": hours, "system_load_mw": np.round(sysload / 1000, 3)}), "system_load_hourly.csv",
          "sum of all 33,757 usable homes' hourly kWh (MW), Sep 2025 to Aug 2026; data/processed/sysload.npy")
    pmf = np.load(PROC / "ev_start_pmf.npy")
    write(pd.DataFrame({"start_hour": range(24), "share_of_sessions": np.round(pmf, 5)}), "ev_charging_start_hour_shares.csv",
          "share of observed EV charging sessions starting in each hour (about 20,800 sessions, EV high tier homes); engine input")
    hp = np.load(PROC / "hp_increment.npy")
    write(pd.DataFrame({"hour": hours, "added_kw_per_heat_pump_home": np.round(hp, 4)}), "heat_pump_added_load_hourly.csv",
          "hourly kW one new heat pump adds (labeled heat pump homes minus similar AC homes, averaged); engine input")
    shutil.copy(PROC / "system_peaks.json", OUT / "system_peak_hours.json")
    for name in ("segment_summary.csv", "segment_technology_matrix.csv"):
        src = SEGMENT_DIR / name
        if src.exists():
            df = pd.read_csv(src).rename(columns={"Unnamed: 0": "segment", "Customers": "homes"})   # a count of homes, not ids
            write(df, name, f"segment aggregates from the team's classification and segmentation run ({name})")
        else:
            print(f"{name:42s} skipped: {src} not found")
    for scenario in ("high", "moderate"):        # moderate last, so the recorded plan facts are the moderate run's
        subprocess.run([str(ROOT / "bin/ewu"), "plan", "--scenario", scenario, "--limit", "1.2"], check=True,
                       stdout=subprocess.DEVNULL)
        for name in ("transformer_actions.csv", "capital_plan.csv"):
            df = pd.read_csv(ROOT / "outputs/plan/battery" / name, comment="#")
            write(df, f"{scenario}_2030_{name}", f"battery plan, {scenario} 2030, overloaded above 1.2 x rating; 3,000 synthetic "
                  "transformers of 8 real homes, summed, no home named; costs net of lease and NYSERDA, upgrade counted 15 of 40 years")
    facts = json.loads((ROOT / "facts/facts.json").read_text())
    rows = []
    for scenario in ("moderate", "high"):
        for limit in ("100", "110", "120", "140"):
            k = f"ewu.deck.{scenario}.limit_{limit}"
            g = lambda n: facts[f"{k}.{n}"]["value"]
            rows.append({"scenario": scenario, "overload_limit_pct": int(limit), "overloaded_pct": g("overloaded_pct"),
                         "fixed_by_batteries_pct": g("fixed_of_overloaded_pct"), "average_units": g("average_units"),
                         "gross_musd": g("nyseg_gross_musd"), "net_without_nyserda_musd": g("nyseg_net_without_nyserda_musd"),
                         "net_musd": g("nyseg_avangrid_cost_musd"), "upgrade_all_musd": g("nyseg_upgrade_all_musd"),
                         "saving_vs_upgrade_all_pct": g("saving_vs_upgrade_all_pct")})
    write(pd.DataFrame(rows), "screen_results_by_loading_limit.csv",
          "bin/ewu screen on the full meter data, from facts/facts.json; $M across NYSEG, present value, 15 years at 7%")


if __name__ == "__main__":
    main()
