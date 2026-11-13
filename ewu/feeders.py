"""Feeders: which homes share a neighborhood transformer, and what each transformer is rated for.

What: build_transformers() makes synthetic groups of k homes (random, or same segment); load_map() reads a real
      meter-to-transformer map; rate() sets each rating from today's peak times a sizing margin.
Why:  no meter-to-transformer map exists in the hackathon data, so the stress test needs groups it can explain
      and a sizing rule it can vary. The real map plugs in through load_map() with no other change.
How:  Feeders holds two equal-length arrays, home row and transformer id, so groups may differ in size. Random
      mode shuffles every home and cuts groups of k; same-segment mode shuffles, then stable-sorts by segment
      before cutting, so most groups hold one segment. `count` groups are then drawn without replacement. A
      home appears once at most, and load_map() refuses a meter listed under two transformers.
"""
from typing import NamedTuple
import numpy as np
import pandas as pd

MODES = ("random", "same_segment")


class Feeders(NamedTuple):
    homes: np.ndarray          # row number in the load matrix, one entry per connected home
    transformer: np.ndarray    # transformer id 0..count-1 for the same entry
    count: int
    rating_kva: np.ndarray | None = None   # only when a real map supplies nameplate ratings


def build_transformers(segments, k, count, mode, seed):
    """Synthetic groups: `count` transformers of `k` homes each, no home in two of them."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, not {mode}")
    rng = np.random.default_rng((seed, 0))
    order = rng.permutation(len(segments))
    if mode == "same_segment":
        order = order[np.argsort(np.asarray(segments)[order], kind="stable")]
    full = len(order) // k
    groups = order[: full * k].reshape(full, k)
    count = min(count, full)
    chosen = groups[np.sort(rng.choice(full, size=count, replace=False))]
    return Feeders(chosen.ravel(), np.repeat(np.arange(count), k), count)


def load_map(csv_path, meter_ids):
    """Real groups from a CSV with columns meter_id, transformer_id, kva. Meters not in the data are dropped."""
    table = pd.read_csv(csv_path, dtype={"meter_id": str, "transformer_id": str})
    missing = {"meter_id", "transformer_id", "kva"} - set(table.columns)
    if missing:
        raise ValueError(f"map lacks columns {sorted(missing)}")
    twice = table.groupby("meter_id")["transformer_id"].nunique()
    if (twice > 1).any():
        raise ValueError(f"{int((twice > 1).sum())} meters are listed under two transformers")
    table = table.drop_duplicates("meter_id")
    row_of = pd.Series(np.arange(len(meter_ids)), index=pd.Index(meter_ids).astype(str))
    table = table[table.meter_id.isin(row_of.index)]
    ids, transformer = np.unique(table.transformer_id.to_numpy(), return_inverse=True)
    kva = table.groupby("transformer_id")["kva"].first().reindex(ids).to_numpy(dtype=float)
    return Feeders(row_of[table.meter_id].to_numpy(), transformer, len(ids), kva)


def rate(today_peak_kw, margin):
    """Rating in kW: today's group peak times the sizing margin (unity power factor, an assumption)."""
    return np.asarray(today_peak_kw, dtype=np.float64) * margin
