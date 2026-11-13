"""EWU package: shared paths and the one reader for config/ewu.yaml.

What: ROOT, the processed-data folder, config_value() and read_inputs(), used by every ewu module.
Why:  every number the prototype uses must come from config/ewu.yaml or the measured data, through one door,
      so a module never types an input of its own.
How:  yaml.safe_load once per call, then walk the dotted key to its `value`; the data loader opens the load
      matrix memory-mapped so only the rows a run needs are read.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
CONFIG = ROOT / "config" / "ewu.yaml"
FLAG_COLUMNS = ["CUSTOMER_NUMBER", "segment", "is_ev_l2", "is_electric_heat", "is_other_inactive"]


def read_config():
    return yaml.safe_load(CONFIG.read_text())


def config_value(dotted, config=None):
    """Return the `value` of one config input, named like 'transformer.overload_limit'."""
    node = config if config is not None else read_config()
    for part in dotted.split("."):
        node = node[part]
    return node["value"]


def read_inputs():
    """Hourly load (homes x 8760 kW, memory-mapped), the flags each home needs, and hourly temperature (F)."""
    return {
        "load": np.load(PROCESSED / "load_present.npy", mmap_mode="r"),
        "homes": pd.read_parquet(PROCESSED / "segmented.parquet", columns=FLAG_COLUMNS),
        "temp": pd.read_parquet(PROCESSED / "weather.parquet")["temp"].to_numpy(),
    }
