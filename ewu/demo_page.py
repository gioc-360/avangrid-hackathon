"""Demo page: the offline page judges click through one step at a time from its side panel, built only from
numbers the code already wrote.

What: collect_values() gathers every fact, private fact and config input the page may show, each under a
      prefixed key (fact:, private:, config:); steps_built() says which data group (summary, network, inventory,
      ladder, money) has what it needs; build_page() pours both into ewu/demo_template.html and writes
      outputs/demo/ewu_demo.html.
Why:  the live demo must work with no network and no server, and every number on it must trace to code. The
      page never computes a number of its own: it shows stored values, and each shown number carries its key,
      which checks/demo_check.py compares with the stored value. Deck v3 is final (Gio, 2026-11-13: "v3 is final
      numbers and app should reflect that"), so the page reads only the deck profile's facts (ewu.deck.*, the
      numbers v3 took), the 2,610 priority homes' peak cut v3 shows, the replica facts for one validation line,
      and the inventory; the cautious profile's facts (ewu.sensitivity, ewu.economics, ewu.coldsnap, ewu.network)
      stay in the CLI and docs.
How:  the values travel inside the page as one JSON block; the template's script draws the steps from them.
      The page shows no real home: Network draws the deck profile's synthetic transformers (8 homes summed
      each, ewu/deck_views.py) and Inventory draws a Composite home per segment (segment averages, public facts).
      The page stays gitignored. A step whose inputs are missing shows "not built" and the keys it lacks,
      instead of failing quietly.
"""
import json
from ewu import ROOT

TEMPLATE = ROOT / "ewu" / "demo_template.html"
PAGE = ROOT / "outputs" / "demo" / "ewu_demo.html"
FACT_PREFIXES = ("ewu.inventory.", "ewu.demo.", "ewu.deck.", "ewu.deck_replica.", "teammate.audit.rerun.fleet_priority.",
                 "teammate.audit.rerun.priority_homes", "data.customers_usable")
NOT_SHOWN = ("ewu.deck.managed.", "ewu.deck.network_managed.", "ewu.deck.recharge.")   # deck-profile runs v3 does not use
PRIVATE_PREFIXES = ("ewu.deck.network.t.",)
NEVER_SHOWN = ("soc_kwh", "ewu.demo.home_")   # one host's charge or one real home: retired by audit MUST_FIX 1
DECK = "fact:ewu.deck.{}.limit_120.{}"
NEEDS = {
    "summary": [DECK.format("moderate", "saving_vs_upgrade_all_pct"), DECK.format("high", "nyseg_avangrid_cost_musd"),
                "fact:teammate.audit.rerun.fleet_priority.peak_cut_mw", "fact:teammate.audit.rerun.priority_homes",
                "fact:ewu.deck_replica.moderate.limit_120.overloaded_pct"],
    "network": ["fact:ewu.deck.network.transformers_drawn", "fact:ewu.deck.network.moderate.upgrade.upgrade",
                "private:ewu.deck.network.t.state", "private:ewu.deck.network.t.feeder", "private:ewu.deck.network.t.base_kw",
                "private:ewu.deck.network.t.over_today"],
    "inventory": ["fact:ewu.inventory.homes", "fact:ewu.inventory.any_program_pct", "fact:ewu.demo.home_count",
                  "fact:ewu.demo.composite_0.flags", "fact:ewu.demo.composite_0.winter_day_kw"],
    "ladder": ["fact:ewu.deck.high.limit_140.fixed_units_3_4_pct", "fact:ewu.deck.moderate.limit_100.upgrade_of_overloaded_pct",
               "fact:ewu.deck.high.limit_110.winter_of_overloaded_pct", "fact:ewu.deck.moderate.limit_120.average_units"],
    "money": [DECK.format("moderate", "nyseg_gross_musd"), DECK.format("high", "nyseg_net_without_nyserda_musd"),
              "fact:ewu.deck.high.limit_140.saving_vs_upgrade_all_pct", "fact:ewu.deck.prices.upgrade_counted_usd"],
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
    values = {f"fact:{k}": v["value"] for k, v in facts.items()
              if k.startswith(FACT_PREFIXES) and not k.startswith(NOT_SHOWN) and not k.endswith(".seconds")}
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
