"""The only way a number reaches the deck: a script calls record(), which writes facts/facts.json.

Each fact carries its value, unit, the script that made it and a one-line method, so
checks/check_all.py can trace any number on a slide back to code.
"""
import json, inspect, os
from pathlib import Path
FACTS = Path(__file__).resolve().parent.parent / "facts" / "facts.json"

def record(key, value, unit="", method=""):
    FACTS.parent.mkdir(exist_ok=True)
    d = json.loads(FACTS.read_text()) if FACTS.exists() else {}
    caller = os.path.relpath(inspect.stack()[1].filename, FACTS.parent.parent)
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float):
        value = round(value, 4)
    d[key] = {"value": value, "unit": unit, "script": caller, "method": method}
    FACTS.write_text(json.dumps(dict(sorted(d.items())), indent=1))
