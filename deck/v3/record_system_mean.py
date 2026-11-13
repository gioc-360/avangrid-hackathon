"""Record the system's mean load and load factor (slides 2 and 8: 30.8 MW, 39%) from the same summed load as the peak.

What: insight.system_mean_mw and insight.system_load_factor_pct from data/processed/sysload.npy.
Why:  analysis/segment.py now writes both, but rerunning it rewrites every segment fact; this writes only these two.
How:  .venv/bin/python -I deck/v3/record_system_mean.py
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from analysis.facts import record  # noqa: E402

sysl = np.load(ROOT / "data/processed/sysload.npy")
record("insight.system_mean_mw", round(float(sysl.mean()) / 1000, 1), "MW", "sum of all usable homes, mean of the 8,760 hours")
record("insight.system_load_factor_pct", round(100 * float(sysl.mean() / sysl.max()), 1), "%", "mean / annual max hour of the summed load")
print(round(float(sysl.mean()) / 1000, 1), "MW mean;", round(100 * float(sysl.mean() / sysl.max()), 1), "% load factor")
