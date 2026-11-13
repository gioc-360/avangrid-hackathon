"""Facts: the only door a number takes to reach a slide, a doc or the demo page.

What: record(key, value, unit, method) writes one fact with the script that made it; forget(prefix) drops
      every fact whose key starts with prefix, so a retired output leaves nothing stale. Aggregates go to
      facts/facts.json (in git). record(..., private=True) sends per-home and per-transformer values to
      outputs/private/facts_private.json, which is gitignored and never leaves this machine.
Why:  checks/check_all.py and the EWU checks trace every shown number back to code. One door for every
      number, and nothing per-home reaches git.
How:  read the JSON file, set the key with value, unit, calling script and method, write it back sorted.
"""
import json, inspect, os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "facts" / "facts.json"
PRIVATE_FACTS = ROOT / "outputs" / "private" / "facts_private.json"


def record(key, value, unit="", method="", private=False):
    path = PRIVATE_FACTS if private else FACTS
    path.parent.mkdir(parents=True, exist_ok=True)
    d = json.loads(path.read_text()) if path.exists() else {}
    caller = os.path.relpath(inspect.stack()[1].filename, ROOT)
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float):
        value = round(value, 4)
    d[key] = {"value": value, "unit": unit, "script": caller, "method": method}
    path.write_text(json.dumps(dict(sorted(d.items())), indent=1))


def forget(prefix, private=False):
    """Drop every fact whose key starts with prefix; return how many went."""
    path = PRIVATE_FACTS if private else FACTS
    if not path.exists():
        return 0
    d = json.loads(path.read_text())
    kept = {k: v for k, v in d.items() if not k.startswith(prefix)}
    if len(kept) != len(d):
        path.write_text(json.dumps(kept, indent=1))
    return len(d) - len(kept)
