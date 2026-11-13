"""Network tests: the page's network is the live screen's own network, transformer by transformer.

What: the per-state counts from ewu/network.py equal `bin/ewu screen` for the demo seed; every flagged
      transformer has exactly one final state and no unflagged one is fixed; every ladder step accounts for
      every transformer; feeders are equal blocks by id; the stored facts equal a fresh run; the page carries
      the network and builds with nothing loaded from outside.
Why:  the Network view is the demo moment. If its recolored nodes and counts drifted from the screen command,
      the page would show one answer and the terminal another.
How:  one run of each on the full data for the config's demo case; the page is built in memory, never written.
"""
import json
import numpy as np
import pytest
from checks import demo_check
from ewu import ROOT, config_value, read_config, read_inputs
from ewu import demo_page, network, screen

CONFIG = read_config()


@pytest.fixture(scope="module")
def runs():
    inputs = read_inputs()
    scenario, margin = config_value("demo.scenario", CONFIG), config_value("demo.margin", CONFIG)
    return network.run_network(inputs, CONFIG), screen.run_screen(inputs, CONFIG, scenario, margin)


def test_state_counts_equal_the_screen_for_the_demo_seed(runs):
    net, cell = runs
    final = net["counts"]["upgrade"]
    assert net["seed"] == cell["seed"] == config_value("demo.screen_seed", CONFIG)
    assert net["transformers"] == cell["transformers"] and net["homes"] == cell["homes"]
    assert net["counts"]["flag"]["over"] == cell["flagged"]
    assert final["shifted"] == cell["shift_fixed"]
    assert final["protected"] == cell["protected"]
    assert final["upgrade"] == cell["upgrade_left"]
    assert net["counts"]["shift"]["over"] == cell["protect_set"]


def test_every_flagged_transformer_has_exactly_one_final_state(runs):
    net, _ = runs
    state, flag = net["state"], net["flag"]
    assert set(np.unique(state)) <= {0, 1, 2, 3} and len(state) == net["transformers"]
    assert np.isin(state[flag], [1, 2, 3]).all()
    assert (state[~flag] != 1).all()
    assert ((net["batteries"] > 0) == (state == 2)).all()


def test_every_ladder_step_accounts_for_every_transformer(runs):
    net, _ = runs
    for view in network.VIEWS:
        words = network.looks(view, net["state"], net["flag"], net["over_today"])
        assert len(words) == net["transformers"]
        assert sum(net["counts"][view].values()) == net["transformers"]


def test_feeders_are_equal_blocks_by_id():
    feeder = network.feeder_of(3000, 6)
    assert np.bincount(feeder).tolist() == [500] * 6
    assert (np.diff(feeder) >= 0).all()


def test_stored_facts_equal_a_fresh_run(runs):
    net, _ = runs
    facts = json.loads((ROOT / "facts" / "facts.json").read_text())
    for view, counts in net["counts"].items():
        for word, n in counts.items():
            assert facts.get(f"ewu.network.{view}.{word}", {}).get("value", 0) == n, (view, word)


def test_the_page_carries_the_network_and_builds_offline():
    values = demo_page.collect_values(CONFIG)
    built, missing = demo_page.steps_built(values)
    assert built["network"], missing["network"]
    html = demo_page.page_html(values)
    assert not demo_check.OUTSIDE.search(html)
    assert '"network":true' in html and "private:ewu.deck.network.t.state" in html
    assert not any("meter" in k or "customer" in k for k in values if k.startswith("private:ewu.deck.network."))


def test_the_page_draws_the_deck_network_only():
    """Deck v3 is final: one setup, the deck profile; no cautious or managed-charging network on the page."""
    values = demo_page.collect_values(CONFIG)
    assert all("ewu.deck.network." in k for k in demo_page.NEEDS["network"])
    state = values["private:ewu.deck.network.t.state"]
    scenario = CONFIG["demo"]["scenario"]["value"]
    assert len(state) == values["fact:ewu.deck.network.transformers_drawn"]
    for code, word in ((0, "within"), (2, "protected"), (3, "upgrade")):
        assert state.count(code) == values[f"fact:ewu.deck.network.{scenario}.upgrade.{word}"], word
    assert not any(k.startswith(("private:ewu.network.", "fact:ewu.network.", "private:ewu.deck.network_managed.",
                                 "fact:ewu.deck.network_managed.")) for k in values)
    template = demo_page.TEMPLATE.read_text()
    assert 'const S = { step: "deck"' in template
    assert "Cautious" not in template and "Managed charging (optional)" not in template


def test_the_deck_network_counts_equal_the_deck_screen():
    """The page's network for the demo scenario has the deck screen's counts at the deck limit (bin/ewu screen)."""
    facts = {k: v["value"] for k, v in json.loads((ROOT / "facts" / "facts.json").read_text()).items()}
    scenario = config_value("demo.scenario", CONFIG)
    net, cell = f"ewu.deck.network.{scenario}.", f"ewu.deck.{scenario}.limit_{round(100 * config_value('profiles.deck.overload_limit', CONFIG))}."
    assert facts[net + "flag.over"] == facts[cell + "overloaded"]
    assert facts[net + "upgrade.protected"] == facts[cell + "fixed"]
    assert facts[net + "upgrade.upgrade"] == facts[cell + "upgrades"]
    assert facts["ewu.deck.network.transformers_drawn"] == config_value("profiles.deck.transformer_count", CONFIG)
