"""Demo page: the offline page judges click through one step at a time from its side panel, built only from
numbers the code already wrote.

What: collect_values() gathers every fact, private fact and config input the page may show, each under a
      prefixed key (fact:, private:, config:); steps_built() says which data group (inventory, screen, cold
      snap, money) has what it needs; build_page() pours both into ewu/demo_template.html and writes
      outputs/demo/ewu_demo.html.
Why:  the live demo must work with no network and no server, and every number on it must trace to code. The
      page never computes a number of its own: it shows stored values, and each shown number carries its key,
      which checks/demo_check.py compares with the stored value.
How:  the values travel inside the page as one JSON block; the template's script draws the steps from them.
      The page shows no real home: Inventory draws a Composite home per segment (segment averages,
      public facts), and Protect draws one 8-home transformer's cold snap load from
      outputs/private/facts_private.json with battery charge from the fleet facts, never a host's own charge.
      The page stays gitignored. A step whose inputs are missing shows "not built" and the keys it lacks,
      instead of failing quietly.
"""
import json
from ewu import ROOT

TEMPLATE = ROOT / "ewu" / "demo_template.html"
PAGE = ROOT / "outputs" / "demo" / "ewu_demo.html"
FACT_PREFIXES = ("ewu.inventory.", "ewu.demo.", "ewu.sensitivity.", "ewu.economics.", "ewu.coldsnap.")
PRIVATE_PREFIXES = ("ewu.coldsnap.example.",)
NEVER_SHOWN = ("soc_kwh", "ewu.demo.home_")   # one host's charge or one real home: retired by audit MUST_FIX 1
NEEDS = {
    "inventory": ["fact:ewu.inventory.homes", "fact:ewu.inventory.any_program_pct", "fact:ewu.demo.home_count",
                  "fact:ewu.demo.composite_0.flags", "fact:ewu.demo.composite_0.winter_day_kw"],
    "screen": ["fact:ewu.sensitivity.moderate.random.margin_115.flagged_pct",
               "fact:ewu.sensitivity.high.same_segment.margin_150.upgrade_left_pct",
               "fact:ewu.sensitivity.moderate.random.margin_115.new_from_stagger_pct"],
    "coldsnap": ["private:ewu.coldsnap.example.load_kw", "private:ewu.coldsnap.example.hosts_2.net_kw",
                 "fact:ewu.coldsnap.moderate.staggered.margin_115.hosts_2.soc_median_pct_by_hour",
                 "fact:ewu.coldsnap.moderate.staggered.margin_115.hosts_1.cleared_pct"],
    "money": ["fact:ewu.economics.headline.ladder_share_pct.base", "fact:ewu.sensitivity.cells",
              "fact:ewu.economics.battery_vs_upgrade.mid.tie_unit_usd_equal_life",
              "fact:ewu.economics.high.same_segment.margin_150.high.discounted.ladder_share_pct"],
}


def config_inputs(tree, prefix=""):
    """{dotted name: value} for every input in config/ewu.yaml."""
    out = {}
    for key, node in tree.items():
        if isinstance(node, dict) and "value" in node:
            out[f"{prefix}{key}"] = node["value"]
        elif isinstance(node, dict):
            out.update(config_inputs(node, f"{prefix}{key}."))
    return out


def read_json(path):
    return json.loads(path.read_text()) if path.exists() else {}


def collect_values(config, root=ROOT):
    """Every value the page may show, under fact:, private: or config: keys."""
    facts = read_json(root / "facts" / "facts.json")
    private = read_json(root / "outputs" / "private" / "facts_private.json")
    values = {f"fact:{k}": v["value"] for k, v in facts.items() if k.startswith(FACT_PREFIXES)}
    values |= {f"private:{k}": v["value"] for k, v in private.items()
               if k.startswith(PRIVATE_PREFIXES) and not any(word in k for word in NEVER_SHOWN)}
    values |= {f"config:{k}": v for k, v in config_inputs(config).items()}
    return values


def steps_built(values):
    """{step: True or False} and {step: missing keys}."""
    missing = {step: [k for k in keys if k not in values] for step, keys in NEEDS.items()}
    return {step: not lost for step, lost in missing.items()}, missing


def page_html(values):
    built, missing = steps_built(values)
    payload = json.dumps({"values": values, "built": built, "missing": missing}, separators=(",", ":"))
    return TEMPLATE.read_text().replace("/*DATA*/", payload.replace("</", "<\\/"))


def build_page(config):
    """Write outputs/demo/ewu_demo.html and return its path."""
    PAGE.parent.mkdir(parents=True, exist_ok=True)
    PAGE.write_text(page_html(collect_values(config)))
    return PAGE
