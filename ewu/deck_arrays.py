"""Deck arrays: bring the teammate's two input arrays into data/processed, check them, record their provenance.

What: import_arrays() copies ev_start_pmf.npy and hp_increment.npy from the teammate's folder into
      data/processed (gitignored), checks each against its CSV twin and its shape rule (24 start-hour weights
      summing to 1; 8,760 hourly kW, none negative) and records sha256 and summary facts under
      ewu.deck.inputs.*; verify_array() runs on every load in ewu/deck.py and fails loudly when a file's
      sha256 is not the one config/ewu.yaml holds.
Why:  the team's final deck uses these two arrays (spec lines 9 and 10). They are given by the teammate, built
      from the hackathon meter data by her ewu_inputs.py; the tool must load exactly those bytes by default and
      say so, never a silently different file.
How:  the folder is untrusted input: files are only read (np.load with allow_pickle=False, pandas read_csv),
      never executed, and nothing is written there. The CSV twins are rounded (5 decimals for start hours,
      4 for kW), so every value must agree within half a unit of the last shown digit.
"""
import hashlib
import shutil
from pathlib import Path
import numpy as np
import pandas as pd
from ewu import PROCESSED, config_value, read_config

ARRAYS = {"ev_start_pmf": {"csv": "ev_start_pmf.csv", "column": "probability", "length": 24, "csv_digits": 5},
          "hp_increment": {"csv": "hp_increment.csv", "column": "hp_increment_kw", "length": 8760, "csv_digits": 4}}


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_array(name, values, twin):
    """Plain sentences for every rule the array breaks against its CSV twin and its shape rule."""
    spec, problems = ARRAYS[name], []
    if values.shape != (spec["length"],):
        problems.append(f"{name}: shape {values.shape}, not ({spec['length']},)")
        return problems
    if not np.isfinite(values).all() or values.min() < 0:
        problems.append(f"{name}: holds a negative or missing value")
    if name == "ev_start_pmf" and abs(values.sum() - 1.0) > 1e-9:
        problems.append(f"{name}: sums to {values.sum()}, not 1")
    if len(twin) != spec["length"]:
        problems.append(f"{name}: CSV twin has {len(twin)} rows, not {spec['length']}")
    elif np.abs(values - twin).max() > 0.5 * 10 ** -spec["csv_digits"] + 1e-12:
        problems.append(f"{name}: differs from its CSV twin by {np.abs(values - twin).max()}")
    return problems


def verify_array(name, path, config):
    """Fail loudly unless the file at path has the sha256 config/ewu.yaml holds for it."""
    want = config_value(f"profiles.deck.{name}_sha256", config)
    got = sha256_of(path)
    if got != want:
        raise ValueError(f"{path.name} sha256 {got[:12]} is not the teammate's {want[:12]} in config/ewu.yaml; "
                         f"rerun bin/ewu arrays or remove the file to use the derived array")
    return got


def import_arrays(folder, config):
    """Copy, check and record both arrays; returns {name: summary}. Raises before copying anything that fails."""
    folder, found, problems = Path(folder).expanduser(), {}, []
    for name, spec in ARRAYS.items():
        values = np.load(folder / f"{name}.npy", allow_pickle=False).astype(np.float64).ravel()
        twin = pd.read_csv(folder / spec["csv"])[spec["column"]].to_numpy(dtype=np.float64)
        problems += check_array(name, values, twin)
        found[name] = {"values": values, "twin_diff": float(np.abs(values - twin).max()) if len(twin) == len(values) else None}
    if problems:
        raise ValueError("; ".join(problems))
    from analysis.facts import record
    how = f"bin/ewu arrays; {config['profiles']['deck']['ev_start_pmf_file']['provenance']}"
    for name, item in found.items():
        target = PROCESSED / f"{name}.npy"
        shutil.copyfile(folder / f"{name}.npy", target)
        item["sha256"] = sha256_of(target)
        values = item["values"]
        record(f"ewu.deck.inputs.{name}.sha256", item["sha256"], "sha256 of data/processed file", how)
        record(f"ewu.deck.inputs.{name}.values", len(values), "values", how)
        record(f"ewu.deck.inputs.{name}.csv_twin_max_diff", item["twin_diff"], "largest difference to the CSV twin", how)
        if name == "ev_start_pmf":
            record(f"ewu.deck.inputs.{name}.sum", round(float(values.sum()), 6), "sum of 24 start-hour weights", how)
            record(f"ewu.deck.inputs.{name}.hour0_pct", float(values[0] * 100), "% of starts at midnight", how)
            record(f"ewu.deck.inputs.{name}.hours_15_22_pct", float(values[15:23].sum() * 100), "% of starts 15:00 to 22:00", how)
        else:
            record(f"ewu.deck.inputs.{name}.annual_kwh", float(values.sum()), "kWh one adopter adds per year", how)
            record(f"ewu.deck.inputs.{name}.max_kw", float(values.max()), "kW, highest hour", how)
    return found


def main(folder=None):
    config = read_config()
    folder = folder or config_value("profiles.deck.teammate_folder", config)
    found = import_arrays(folder, config)
    for name, item in found.items():
        print(f"{name:<14} {len(item['values']):>5} values, CSV twin within {item['twin_diff']:.1e}, sha256 {item['sha256'][:12]}, "
              f"copied to data/processed/{name}.npy")
    print("Provenance: given by the teammate (ewu_inputs.py, 2026-11-13), built from the hackathon meter data. "
          "Set profiles.deck.*_sha256 in config/ewu.yaml to these values once; every battery plan run then checks them.")
    return found


def add_command(commands):
    """`bin/ewu arrays [--folder PATH]`."""
    arr = commands.add_parser("arrays", help="copy and check the teammate's ev_start_pmf and hp_increment arrays (read only)")
    arr.add_argument("--folder", default=None, help="teammate's folder (default profiles.deck.teammate_folder)")
    arr.set_defaults(run=lambda args: main(args.folder) and 0)
