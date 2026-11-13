"""Demo audit: the page-reading half of checks/demo_check.py, which renders, reads and judges one demo page state.

What: RenderedPage reads the DOM Chrome dumps after the page's script runs: bound numbers (key, index, text), free
      text, and per view its bound count, chart marks and any "not built" marker; audit_raw() judges the page file
      (nothing loaded from outside, stored values equal to the source); audit_dom() judges one rendered state
      (every view filled, no NaN, every shown number bound to its key and equal to it at the shown precision, the
      Network view's drawn states equal to the deck network facts); run_chrome() renders a page headless.
Why:  split from demo_check.py to keep both under the house line cap; demo_check.py drives the states and the
      live screen, this module says whether each state is right.
How:  html.parser on the dumped DOM; numbers outside bound elements are found as checks/trace_numbers.py does;
      Chrome runs with its own empty profile, so the page never leaves this machine.
"""
import json, re, subprocess, sys
from html.parser import HTMLParser
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from checks import trace_numbers
from ewu import config_value, read_config
from ewu.demo_page import config_inputs, read_json

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUTSIDE, BROKEN = re.compile(r"https?://|<link\b|@import|\bsrc\s*=|url\(", re.I), re.compile(r"\b(NaN|undefined|Infinity)\b")
STEPS = ("deck", "network", "overview", "inventory", "flag", "protect", "upgrade", "money")   # the side panel, in order
NET_VIEWS, MARKS = ("today", "flag", "protect", "upgrade"), ("polyline", "rect", "path", "circle", "line")


def net_facts():
    """Count-fact prefix the Network view reads: the deck profile's network for the demo scenario."""
    return f"fact:ewu.deck.network.{config_value('demo.scenario')}."


class RenderedPage(HTMLParser):
    """Bound numbers (key, index, text), free text, and per step: bound count, chart marks, 'not built'."""

    def __init__(self):
        super().__init__()
        self.bound, self.free, self.skip, self.open = [], [], 0, None
        self.section, self.steps, self.looks = None, {s: {"bound": 0, "marks": 0, "not_built": False} for s in STEPS}, {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style", "title"):
            self.skip += 1
        if tag == "section" and a.get("id") in self.steps:
            self.section = a["id"]
        if self.section and tag in MARKS:
            self.steps[self.section]["marks"] += 1
        if self.section == "network" and tag == "g" and "data-look" in a:
            self.looks[a["data-look"]] = self.looks.get(a["data-look"], 0) + 1
        if self.section and "notbuilt" in (a.get("class") or ""):
            self.steps[self.section]["not_built"] = True
        if "data-key" in a:
            self.open = [a["data-key"], int(a["data-index"]) if a.get("data-index") else None, ""]

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag):
        if tag in ("script", "style", "title"):
            self.skip -= 1
        if tag == "section":
            self.section = None
        if self.open and tag == "span":
            self.bound.append(tuple(self.open))
            if self.section:
                self.steps[self.section]["bound"] += 1
            self.open = None

    def handle_data(self, data):
        if not self.skip and self.open:
            self.open[2] += data
        elif not self.skip:
            self.free.append(data)


def read_sources(root=ROOT):
    facts, private = (read_json(root / p) for p in ("facts/facts.json", "outputs/private/facts_private.json"))
    return ({f"fact:{k}": v["value"] for k, v in facts.items()} | {f"private:{k}": v["value"] for k, v in private.items()}
            | {f"config:{k}": v for k, v in config_inputs(read_config()).items()})


def shown_equals(text, value):
    """True when `text` is `value` (or value x 100) rounded to the digits shown."""
    raw = text.replace(",", "").replace("$", "").strip()
    if not re.fullmatch(r"-?\d+(\.\d+)?", raw) or isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    shown, digits = float(raw), len(raw.split(".")[1]) if "." in raw else 0
    return any(abs(v - shown) <= 0.5 * 10 ** -digits + 1e-9 for v in (value, value * 100))


def audit_raw(raw, sources):
    """Problems in the page file itself: outside resources, and stored values that no longer match the source."""
    block = re.search(r'<script type="application/json" id="data">(.*?)</script>', raw, re.S)
    values = json.loads(block.group(1).replace("<\\/", "</"))["values"] if block else {}
    problems = [f"loads from outside: '{m.group(0)}'" for m in OUTSIDE.finditer(raw)] + ([] if block else ["no data block"])
    problems += [f"stale value {k}: page {v} vs source {sources.get(k)}" for k, v in values.items() if sources.get(k) != v]
    return problems


def audit_dom(dom, sources, net_view=None):
    """Problems in one rendered state: unfilled views, broken or unbound numbers, Network states unequal to facts."""
    page = RenderedPage()
    page.feed(dom)
    prefix = net_facts()
    stored = {k.rsplit(".", 1)[1]: v for k, v in sources.items() if net_view and k.startswith(f"{prefix}{net_view}.") and v}
    problems = [] if page.looks == stored else [f"network {net_view}: drawn {page.looks} vs facts {stored}"]
    problems += [f"{s}: not built" if v["not_built"] else f"{s}: not filled ({v['bound']} numbers, {v['marks']} chart marks)"
                for s, v in page.steps.items() if v["not_built"] or not v["bound"] or not v["marks"]]
    text = "\n".join(page.free) + "\n" + "\n".join(t for _, _, t in page.bound)
    problems += [f"shows '{m.group(0)}'" for m in BROKEN.finditer(text)]
    problems += [f"unbound number {shown}" for _, shown, _, _ in trace_numbers.claimed_numbers("\n".join(page.free))]
    for key, index, shown in page.bound:
        value = sources.get(key)
        value = value[index] if index is not None and isinstance(value, list) and index < len(value) else value
        if not shown_equals(shown, value):
            problems.append(f"{key}{'' if index is None else f'[{index}]'} shows '{shown.strip()}', source holds {value}")
    return problems, len(page.bound)


def run_chrome(url, profile, *extra):
    args = [CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--disable-sync",
            "--disable-extensions", "--disable-background-networking", "--disable-component-update", "--hide-scrollbars",
            f"--user-data-dir={profile}", "--virtual-time-budget=3000", *extra, url]
    return subprocess.run(args, capture_output=True, text=True, timeout=90).stdout
