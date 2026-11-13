"""Teammate rerun: run copies of the teammate's prototype scripts in a scratch folder on our load matrix.

What: copies the four scripts behind the deck's transformer and battery numbers (ewu_sim_bo2.py, ewu_sim.py,
      battery_sim.py, ewu_inputs.py) and her inputs (classification, the two arrays) from the downloaded folder
      into a scratch folder, links our data/processed/load.npy as her kwh.npy (same layout: row = customer id
      minus 1, NaN where missing), writes the temperature and label files her inputs script reads, and runs
      each copy with python -I. Then three audit runs of our own: the arrays rebuilt by her recipe, the
      transformer run again with the start-hour array her script as written produces, and a recharge check.
Why:  docs/TEAMMATE_AUDIT.md must say whether her code, as written, gives the deck's numbers. The folder is
      untrusted input, so nothing runs inside it and nothing is written to it; the customer-level files stay
      in the scratch folder, outside git.
How:  scratch = /private/tmp/claude-501/teammate_audit (run/, rebuild/, sens/). Recharge check: her
      ewu_sim_bo2.py text up to `import sys`, with one line added that keeps each transformer's load, then each
      battery-fixed transformer at the 1.20 limit is dispatched hour by hour (discharge above the limit,
      recharge only from headroom below it, 89.4% round trip, start full) and any hour left above is counted.
      checks/teammate_audit.py turns the outputs into facts.
"""
import argparse, json, shutil, subprocess, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
FOLDER = Path.home() / "Downloads" / "_prototype"
WORK = Path("/private/tmp/claude-501/teammate_audit")
PY = [sys.executable, "-I"]


def fresh_dir(path, folder):
    """A scratch dir holding her classification, our load matrix as kwh.npy and the given arrays."""
    path.mkdir(parents=True, exist_ok=True)
    shutil.copy(folder / "customer_classification.csv", path / "classification.csv")
    link = path / "kwh.npy"
    if not link.exists():
        link.symlink_to(PROCESSED / "load.npy")
    return path


def write_weather_and_labels(path):
    """daily_temp.npy, hourly_temp.npy (her weather_fit.py recipe) and features_all.csv (lab_HP, lab_EV)."""
    temp = pd.read_parquet(PROCESSED / "weather.parquet").temp.to_numpy()
    np.save(path / "daily_temp.npy", temp.reshape(365, 24).mean(1))
    np.save(path / "hourly_temp.npy", temp.astype("float32"))
    ids = np.flatnonzero(np.load(PROCESSED / "present.npy")) + 1
    feats = pd.read_parquet(PROCESSED / "features.parquet")
    labels = pd.DataFrame({"lab_HP": feats.lab_hp.to_numpy().astype(int), "lab_EV": feats.lab_ev.to_numpy().astype(int)},
                          index=pd.Index(ids, name="customer"))
    labels.to_csv(path / "features_all.csv")


def run_copy(script, cwd, *args):
    subprocess.run(PY + [str(script), *args], cwd=cwd, check=True, capture_output=True, text=True)


def start_pmf_diagnostic(path):
    """Hour-0 share of her EV start recipe as written (resets at midnight) and with sessions run across midnight."""
    load = np.load(path / "kwh.npy", mmap_mode="r")
    cls = pd.read_csv(path / "classification.csv", index_col=0, keep_default_na=False)
    mild = np.load(path / "daily_temp.npy")
    mild = (mild >= 45) & (mild <= 68)
    starts, carried, at_zero = [], 0, 0
    for cid in cls.index[cls.ev == "High"]:
        day = np.nan_to_num(np.array(load[cid - 1])).reshape(365, 24)
        high = (day >= np.percentile(day, 20, axis=1, keepdims=True) + 4.5)
        flat = high.ravel()
        begin = np.flatnonzero(flat & ~np.r_[False, flat[:-1]])
        starts += list(begin[mild[begin // 24]] % 24)
        for d in np.flatnonzero(mild):
            if high[d, 0]:
                at_zero += 1
                carried += int(d > 0 and high[d - 1, 23])
    pmf = pd.Series(starts).value_counts(normalize=True).reindex(range(24), fill_value=0).to_numpy()
    np.save(path / "pmf_continuous.npy", pmf)
    return {"continuous_hour0": float(pmf[0]), "continuous_15_22": float(pmf[15:23].sum()),
            "hour0_starts": at_zero, "hour0_carried_from_23": carried, "mild_days": int(mild.sum()),
            "source_homes": int((cls.ev == "High").sum())}


def recharge_check(name, script):
    """Battery-fixed transformers at the 1.20 limit still above it once batteries recharge from headroom."""
    src = Path(script).read_text().split("import sys")[0]
    hook = "        hu=np.where(Lu>lim)[0]\n"
    assert src.count(hook) == 1, "her transformer loop changed; recharge check needs its hook line"
    src = src.replace(hook, hook + "        KEEP.append((Lu.astype(np.float32),float(lim)))\n")
    space = {"KEEP": []}
    exec(compile(src, "ewu_sim_bo2_copy", "exec"), space)
    share = {"Moderate": (0.20, 0.15), "High": (0.35, 0.30)}[name]
    out = space["run"](*share, 5)
    rows = np.flatnonzero((out.o120 & (out.u120 <= 4)).to_numpy())
    load = np.stack([space["KEEP"][i][0] for i in rows]).astype(np.float64)
    limit = np.array([space["KEEP"][i][1] for i in rows])
    units = out.u120.to_numpy()[rows].astype(float)
    power, energy, rte = 3.84 * units, 8.064 * units, 0.894
    charge, short, worst = energy.copy(), np.zeros(len(rows)), np.zeros(len(rows))
    for hour in range(load.shape[1]):
        excess = load[:, hour] - limit
        give = np.where(excess > 0, np.minimum(np.minimum(excess, power), charge), 0.0)
        charge -= give
        left = np.where(excess > 0, excess - give, 0.0)
        short += left
        worst = np.maximum(worst, left)
        room = np.where(excess < 0, -excess, 0.0)
        charge += np.minimum(np.minimum(room, power), (energy - charge) / rte) * rte
    fail = short > 1e-6
    return {"fixed": int(len(rows)), "still_over": int(fail.sum()), "worst_kw": float(worst.max())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", type=Path, default=FOLDER)
    ap.add_argument("--work", type=Path, default=WORK)
    ap.add_argument("--recharge", help="internal: run the recharge check for one scenario in the current dir")
    a = ap.parse_args()
    if a.recharge:
        print(json.dumps(recharge_check(a.recharge, "ewu_sim_bo2.py")))
        return
    folder, work = a.folder, a.work
    run = fresh_dir(work / "run", folder)
    for name in ("ev_start_pmf.npy", "hp_increment.npy"):
        shutil.copy(folder / name, run / name)
    for src in (folder / "ewu_sim_bo2.py", folder / "code/ewu_sim.py", folder / "code/battery_sim.py"):
        shutil.copy(src, run / src.name)
    write_weather_and_labels(run)
    np.save(run / "system_load.npy", np.load(PROCESSED / "sysload.npy"))
    jobs = [subprocess.Popen(PY + [n, *x], cwd=run, stdout=subprocess.DEVNULL)
            for n, x in (("ewu_sim_bo2.py", ["Moderate"]), ("ewu_sim_bo2.py", ["High"]), ("ewu_sim.py", []))]
    run_copy("battery_sim.py", run)
    rebuild = fresh_dir(work / "rebuild", folder)
    shutil.copy(folder / "code/ewu_inputs.py", rebuild / "ewu_inputs.py")
    write_weather_and_labels(rebuild)
    subprocess.run(PY + ["ewu_inputs.py"], cwd=rebuild, capture_output=True)   # her last print line fails on NaN
    (rebuild / "pmf_diag.json").write_text(json.dumps(start_pmf_diagnostic(rebuild)))
    sens = fresh_dir(work / "sens", folder)
    shutil.copy(rebuild / "ev_start_pmf.npy", sens / "ev_start_pmf.npy")
    shutil.copy(folder / "hp_increment.npy", sens / "hp_increment.npy")
    shutil.copy(folder / "ewu_sim_bo2.py", sens / "ewu_sim_bo2.py")
    jobs += [subprocess.Popen(PY + ["ewu_sim_bo2.py", n], cwd=sens, stdout=subprocess.DEVNULL) for n in ("Moderate", "High")]
    result = {}
    for name in ("Moderate", "High"):
        done = subprocess.run(PY + [str(Path(__file__).resolve()), "--recharge", name], cwd=run, check=True,
                              capture_output=True, text=True)
        result[name] = json.loads(done.stdout.strip().splitlines()[-1])
    (run / "recharge.json").write_text(json.dumps(result))
    assert all(j.wait() == 0 for j in jobs)
    print("rerun done in", work)


if __name__ == "__main__":
    main()
