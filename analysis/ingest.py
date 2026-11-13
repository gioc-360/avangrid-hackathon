"""Stream the AMI sources into one dense float32 matrix: load[customer-1, hour].

Sources are zips of CSVs or folders of CSVs (the corrected 10,001-20,000 upload is a folder).
Why: ~300M CSV rows become a 1.25 GB array that every later step reads in seconds.
Nothing is unzipped to disk. hour 0 = 2025-09-01 hour-ending 1. Missing hours stay NaN.
Usage: ingest.py SOURCE [SOURCE ...]
"""
import sys, zipfile, io, os, re, time
from concurrent.futures import ProcessPoolExecutor
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from facts import record

N_CUST, N_HOUR = 35725, 8760
OUT = os.path.expanduser("~/avangrid-hackathon/data/processed")
START = pl.date(2025, 9, 1)
COLS = ["CUSTOMER_NUMBER", "usage_date", "hour_ending", "hourly_kwh", "is_complete_hour"]

def members(src):
    if os.path.isdir(src):
        return [(src, f) for f in sorted(os.listdir(src)) if f.endswith(".csv")]
    with zipfile.ZipFile(src) as z:
        return [(src, n) for n in z.namelist() if n.endswith(".csv")]

def do_file(task):
    src, name = task
    if os.path.isdir(src):
        df = pl.read_csv(os.path.join(src, name), columns=COLS, schema_overrides={"usage_date": pl.Date})
    else:
        with zipfile.ZipFile(src) as z:
            df = pl.read_csv(io.BytesIO(z.read(name)), columns=COLS, schema_overrides={"usage_date": pl.Date})
    df = df.with_columns(((pl.col("usage_date") - START).dt.total_days() * 24 + pl.col("hour_ending") - 1).alias("h"))
    st = dict(rows=df.height, out_of_range=0, dup=0, negative=int((df["hourly_kwh"] < 0).sum()))
    bad = (df["h"] < 0) | (df["h"] >= N_HOUR)
    st["out_of_range"] = int(bad.sum()); df = df.filter(~bad)
    g = df.group_by(["CUSTOMER_NUMBER", "h"]).agg(pl.col("hourly_kwh").sum(), pl.col("is_complete_hour").min())
    st["dup"] = df.height - g.height
    mm = np.lib.format.open_memmap(f"{OUT}/load.npy", mode="r+")
    c = g["CUSTOMER_NUMBER"].to_numpy() - 1; h = g["h"].to_numpy()
    mm[c, h] = g["hourly_kwh"].to_numpy().astype(np.float32); mm.flush()
    inc = np.bincount(g.filter(pl.col("is_complete_hour") == 0)["CUSTOMER_NUMBER"].to_numpy() - 1, minlength=N_CUST)
    return src, st, np.unique(c + 1), inc

if __name__ == "__main__":
    srcs = sys.argv[1:]
    t0 = time.time()
    tasks = [t for s in srcs for t in members(s)]
    mm = np.lib.format.open_memmap(f"{OUT}/load.npy", mode="w+", dtype=np.float32, shape=(N_CUST, N_HOUR))
    mm[:] = np.nan; mm.flush(); del mm
    inc_total = np.zeros(N_CUST, np.int64)
    per = {s: dict(rows=0, out_of_range=0, dup=0, negative=0, files=0, cust=set()) for s in srcs}
    with ProcessPoolExecutor(8) as ex:
        for src, st, custs, inc in ex.map(do_file, tasks):
            p = per[src]; p["files"] += 1; p["cust"].update(custs.tolist()); inc_total += inc
            for k in st: p[k] += st[k]
    for src, p in per.items():
        name = os.path.basename(src.rstrip("/"))
        lo, hi = [int(x) for x in re.search(r"_(\d+)_(\d+)", name).groups()]
        cust = p.pop("cust")
        inside = sum(lo <= c <= hi for c in cust)
        print(name, {k: v for k, v in p.items()}, "customers", len(cust), f"{min(cust)}-{max(cust)}", "in range", inside, flush=True)
        record(f"data.zip.{lo}_{hi}.customers_in_named_range", inside, "customers",
               f"customers in {name} whose ID lies in the range its name promises")
        record(f"data.source.{lo}_{hi}.name", name, "", "file or folder ingested for this customer range")
        record(f"data.source.{lo}_{hi}.missing_in_range", (hi - lo + 1) - inside, "customers", "IDs in the promised range with no rows")
    np.save(f"{OUT}/incomplete_hours.npy", inc_total.astype(np.int32))
    mm = np.load(f"{OUT}/load.npy", mmap_mode="r")
    share = np.isfinite(mm).mean(1)
    present = share > 0
    usable = share >= 0.9          # a home missing more than 10% of hours is left out, not gap-filled
    np.save(f"{OUT}/present.npy", usable)
    print("NaN share:", float(np.isnan(mm).mean()), "usable", int(usable.sum()))
    record("data.customers_usable", int(usable.sum()), "customers", "homes with at least 90% of hours present; all later steps use these")
    record("data.customers_partial_excluded", int((present & ~usable).sum()), "customers", "homes with some data but under 90% of hours")
    record("data.customers_promised", N_CUST, "customers", "Data Dictionary customer count")
    record("data.customers_present", int(present.sum()), "customers", "rows of load.npy with any reading")
    record("data.customers_missing", int((~present).sum()), "customers", "IDs with no reading in any source")
    record("data.rows_read", int(np.isfinite(mm).sum()), "hourly readings", "non-missing cells")
    record("scale.ingest_seconds", round(time.time() - t0, 1), "s", f"{len(tasks)} CSVs from {len(srcs)} sources in parallel, nothing unzipped to disk")
    record("scale.matrix_gb", round(mm.nbytes / 1e9, 2), "GB", "float32 customers x 8760 hours")
