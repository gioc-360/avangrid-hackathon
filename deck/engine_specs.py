"""Engine specs: measure the EWU engine's size, speed and memory on this machine and record each number as a fact.

What: record_code_size() counts lines in every tracked Python file and sums them by layer; record_versions()
      reads the venv's Python and package versions; record_tests() counts the tests pytest collects;
      record_cli() counts the bin/ewu subcommands; record_matrix() times a full read of the processed load
      matrix and reads its shape and bytes; record_screen_memory() runs `bin/ewu screen` under
      /usr/bin/time -l with its facts write switched off and keeps its wall time and peak memory;
      record_make_check() times `make check`. Every value goes to facts/facts.json under specs.*.
Why:  docs/TECH_SPECS.md, the specs figure and the engine slides show these numbers, and the build rule is
      that no number is typed from memory. A spec a judge can rerun is a spec; a guessed one is not.
How:  plain subprocess calls and wc-style line counts. The screen run is the real CLI (ewu/cli.py main) with
      ewu.screen.record_screen replaced by a no-op, so measuring it never rewrites the screen facts. Heavy runs
      (screen and make check) only run with --heavy. Timings carry the machine's load average when measured.
"""
import argparse
import importlib.metadata
import os
import re
import subprocess
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import numpy as np
from analysis.facts import record

PY = str(ROOT / ".venv" / "bin" / "python")
PACKAGES = ("numpy", "pandas", "polars", "pyarrow", "scipy", "scikit-learn", "PyYAML", "matplotlib",
            "openpyxl", "python-pptx", "pytest")
LAYERS = {"analysis": "analysis/", "engine": "ewu/", "checks": "checks/", "tests": "tests/", "deck": "deck/"}
SCREEN_NO_RECORD = ("import sys; sys.path.insert(0, {root!r}); from ewu import cli, screen; "
                    "screen.record_screen = lambda *a, **k: None; sys.exit(cli.main(['screen']))")


def run_text(args, **kwargs):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, **kwargs)


def tracked_lines():
    """Lines per tracked Python file (working tree content), keyed by repo path."""
    paths = run_text(["git", "ls-files", "*.py"]).stdout.split()
    return {p: len((ROOT / p).read_text().splitlines()) for p in paths if (ROOT / p).exists()}


def record_code_size():
    lines = tracked_lines()
    for name, prefix in LAYERS.items():
        mine = {p: n for p, n in lines.items() if p.startswith(prefix)}
        record(f"specs.code.{name}.files", len(mine), "Python files", f"tracked files under {prefix}")
        record(f"specs.code.{name}.lines", sum(mine.values()), "lines", f"wc -l of tracked files under {prefix}")
    for path, count in lines.items():
        if path.startswith(("analysis/", "ewu/", "checks/")):
            key = path.replace("/", ".").removesuffix(".py")
            record(f"specs.lines.{key}", count, "lines", f"wc -l {path}")
    engine_cap = max(n for p, n in lines.items() if p.startswith("ewu/"))
    record("specs.code.engine.largest_module_lines", engine_cap, "lines", "longest tracked ewu module")


def record_versions():
    version = run_text([PY, "--version"]).stdout.split()[-1]
    record("specs.python_version", version, "", ".venv/bin/python --version")
    for name in PACKAGES:
        record(f"specs.package.{name}", importlib.metadata.version(name), "", "version installed in .venv")


def record_tests():
    tail = run_text([PY, "-I", "-m", "pytest", "--collect-only", "-q", "tests/"]).stdout.strip().splitlines()[-1]
    record("specs.tests_collected", int(re.search(r"(\d+) tests? collected", tail).group(1)), "tests",
           "pytest --collect-only -q tests/ | tail -1")
    scripts = [p for p in run_text(["git", "ls-files", "checks/*.py"]).stdout.split() if "battery_model" not in p]
    record("specs.check_scripts", len(scripts), "scripts", "tracked checks/*.py, less the battery_model helper")


def record_cli():
    usage = run_text([str(ROOT / "bin" / "ewu"), "--help"]).stdout
    commands = re.search(r"\{([a-z,]+)\}", usage).group(1).split(",")
    record("specs.cli_commands", len(commands), "subcommands", "bin/ewu --help")
    record("specs.cli_command_names", commands, "", "bin/ewu --help")


def record_matrix():
    path = ROOT / "data" / "processed" / "load_present.npy"
    started = time.time()
    matrix = np.load(path)
    float(matrix.sum())
    seconds = time.time() - started
    record("specs.matrix.homes", int(matrix.shape[0]), "homes", "rows of data/processed/load_present.npy")
    record("specs.matrix.hours", int(matrix.shape[1]), "hours", "columns of data/processed/load_present.npy")
    record("specs.matrix.dtype", str(matrix.dtype), "", "numpy dtype of the load matrix")
    record("specs.matrix.bytes", int(matrix.nbytes), "bytes", "homes x hours x 4 bytes in memory")
    record("specs.matrix.file_bytes", path.stat().st_size, "bytes", "load_present.npy on disk, header included")
    record("specs.matrix.gb", round(matrix.nbytes / 1e9, 2), "GB", "homes x hours x 4 bytes / 1e9")
    record("specs.matrix.full_load_seconds", round(seconds, 2), "s", "np.load of the whole matrix plus one sum, warm disk cache")


def record_machine():
    ram = int(run_text(["sysctl", "-n", "hw.memsize"]).stdout)
    record("specs.machine.cpu", run_text(["sysctl", "-n", "machdep.cpu.brand_string"]).stdout.strip(), "", "sysctl")
    record("specs.machine.cores", int(run_text(["sysctl", "-n", "hw.ncpu"]).stdout), "cores", "sysctl hw.ncpu")
    record("specs.machine.ram_gb", round(ram / 2**30), "GB", "sysctl hw.memsize / 2^30")
    model = re.search(r"Model Name: (.+)", run_text(["system_profiler", "SPHardwareDataType"]).stdout).group(1)
    record("specs.machine.model", model.strip(), "", "system_profiler SPHardwareDataType")


def record_outputs():
    import pandas as pd
    table = pd.read_parquet(ROOT / "outputs" / "private" / "inventory.parquet")
    record("specs.output.inventory.rows", len(table), "homes", "rows of outputs/private/inventory.parquet")
    record("specs.output.inventory.columns", table.shape[1], "columns", "columns of outputs/private/inventory.parquet")
    record("specs.output.inventory.program_columns", sum(c.startswith("eligible_") for c in table.columns), "programs",
           "eligible_* columns, one per program in config/ewu.yaml")
    hosts = pd.read_csv(ROOT / "outputs" / "bess_candidates.csv")
    record("specs.output.bess_candidates.rows", len(hosts), "homes", "rows of outputs/bess_candidates.csv")
    record("specs.output.demo_page_bytes", (ROOT / "outputs" / "demo" / "ewu_demo.html").stat().st_size, "bytes",
           "outputs/demo/ewu_demo.html, one offline file")


def load_average():
    return round(os.getloadavg()[0], 1)


def record_screen_memory():
    code = SCREEN_NO_RECORD.format(root=str(ROOT))
    done = run_text(["/usr/bin/time", "-l", PY, "-I", "-c", code])
    footprint = int(re.search(r"(\d+)\s+peak memory footprint", done.stderr).group(1))
    resident = int(re.search(r"(\d+)\s+maximum resident set size", done.stderr).group(1))
    seconds = float(re.search(r"([\d.]+) s, full meter data", done.stdout).group(1))
    note = f"bin/ewu screen defaults, facts write off, load average {load_average()}"
    record("specs.screen.peak_footprint_bytes", footprint, "bytes", f"/usr/bin/time -l peak memory footprint; {note}")
    record("specs.screen.peak_footprint_gb", round(footprint / 1e9, 2), "GB", f"peak memory footprint / 1e9; {note}")
    record("specs.screen.max_resident_bytes", resident, "bytes", f"max resident set, memory-mapped matrix pages included; {note}")
    record("specs.screen.max_resident_gb", round(resident / 1e9, 2), "GB", f"max resident set / 1e9; {note}")
    record("specs.screen.measured_seconds", seconds, "s", f"time the CLI printed; {note}")
    record("specs.screen.load_average", load_average(), "runnable processes", "1-minute load average right after the run")
    return done.returncode


def record_make_check():
    started = time.time()
    done = run_text(["make", "check"])
    record("specs.make_check.seconds", round(time.time() - started), "s", f"wall clock of make check, load average {load_average()}")
    record("specs.make_check.exit_code", done.returncode, "", "make check exit code")
    return done.returncode


def main(argv=None):
    parser = argparse.ArgumentParser(description="measure the engine's specs into facts/facts.json (specs.*)")
    parser.add_argument("--heavy", action="store_true", help="also run bin/ewu screen under time -l and make check")
    args = parser.parse_args(argv)
    record_code_size()
    record_versions()
    record_tests()
    record_cli()
    record_matrix()
    record_machine()
    record_outputs()
    codes = [record_screen_memory(), record_make_check()] if args.heavy else []
    print(f"specs recorded; heavy runs {'exit ' + str(codes) if codes else 'skipped'}")
    return max(codes, default=0)


if __name__ == "__main__":
    sys.exit(main())
