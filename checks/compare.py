"""Verify every analyst quote in comparison.yaml is word-for-word in that analyst's report,
attach the pipeline's values from facts.json, and write outputs/comparison.json."""
import json, re, sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
def norm(s): return re.sub(r"\s+", " ", s.replace("*", "")).strip().lower()

cmp = yaml.safe_load((ROOT / "checks/comparison.yaml").read_text())
facts = json.loads((ROOT / "facts/facts.json").read_text())
texts = {k: norm((ROOT / v).read_text()) for k, v in cmp["reports"].items()}
out, fails = [], 0
for r in cmp["rows"]:
    row = dict(r)
    for who in cmp["reports"]:
        ok = norm(r[who]) in texts[who]
        row[f"{who}_verified"] = ok
        fails += not ok
        if not ok:
            print(f"FAIL quote not in {who} report: {r['finding']}: {r[who][:70]}")
    row["pipeline"] = {}
    for k in r["facts"]:
        if k not in facts:
            print(f"FAIL fact missing: {k}"); fails += 1
        else:
            row["pipeline"][k] = facts[k]
    out.append(row)
(ROOT / "outputs").mkdir(exist_ok=True)
(ROOT / "outputs/comparison.json").write_text(json.dumps(out, indent=1))
agree = sum(r["verdict"] == "agree" for r in cmp["rows"])
print(f"{len(out)} findings, {agree} agree, {len(out) - agree} differ; quote/fact failures: {fails}")
sys.exit(1 if fails else 0)
