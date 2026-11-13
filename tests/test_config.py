"""Config tests: config/ewu.yaml is complete, sourced and internally consistent.

What: runs the config checker on the real file and on planted bad inputs, then checks the values agree with
      each other (margins in order, the demo margin is one of them, two batteries are twice one).
Why:  every later milestone reads its numbers from this file; a wrong or unsourced input there spreads
      into every result and slide.
How:  imports checks/config_check.py and calls its functions directly on dicts.
"""
import copy
from pathlib import Path
import yaml
from checks import config_check

ROOT = Path(__file__).resolve().parent.parent
SCOPE_BLOCKS = ("scenarios", "transformer", "battery", "shift", "prices", "demo", "checks", "teammate_reference")


def load_config():
    return yaml.safe_load((ROOT / "config" / "ewu.yaml").read_text())


def value_of(config, dotted):
    node = config
    for part in dotted.split("."):
        node = node[part]
    return node["value"]


def test_every_input_has_a_verified_source_or_an_assumption_flag():
    problems, counts = config_check.find_problems(load_config(), config_check.SourceReader())
    assert problems == []
    assert counts["inputs"] > 0


def test_config_has_every_block_the_scope_names():
    assert set(SCOPE_BLOCKS) <= set(load_config())
    assert set(SCOPE_BLOCKS) == set(config_check.REQUIRED_BLOCKS)


def test_a_planted_unsourced_value_is_caught():
    config = copy.deepcopy(load_config())
    config["prices"]["planted_price"] = {"value": 123, "unit": "$"}
    problems, _ = config_check.find_problems(config, config_check.SourceReader())
    assert any("planted_price" in p for p in problems)


def test_a_planted_wrong_source_line_is_caught():
    config = copy.deepcopy(load_config())
    config["teammate_reference"]["overloaded_pct_moderate"]["value"] = 9.9
    problems, _ = config_check.find_problems(config, config_check.SourceReader())
    assert any("overloaded_pct_moderate" in p for p in problems)


def test_selftest_catches_every_planted_case():
    assert config_check.run_selftest(config_check.SourceReader())


def test_numbers_are_found_with_commas_and_as_percents():
    assert config_check.number_found(2100, "about 2,100 batteries")
    assert config_check.number_found(0.2, "Moderate 2030 (20% EV, 15% HP)")
    assert not config_check.number_found(0.3, "Moderate 2030 (20% EV, 15% HP)")


def test_sizing_margins_rise_and_hold_the_defaults():
    config = load_config()
    margins = value_of(config, "transformer.sizing_margins")
    assert margins == sorted(margins)
    assert value_of(config, "transformer.base_margin") in margins
    assert value_of(config, "demo.margin") in margins
    assert value_of(config, "transformer.overload_limit") > 1


def test_two_batteries_hold_twice_one_battery():
    config = load_config()
    assert abs(value_of(config, "battery.energy_kwh_two_units") - 2 * value_of(config, "battery.energy_kwh_per_unit")) < 1e-9
    assert 0 < value_of(config, "battery.round_trip_efficiency") <= 1


def test_high_scenario_adds_more_than_moderate():
    config = load_config()
    for share in ("ev_share", "hp_share"):
        assert value_of(config, f"scenarios.high.{share}") > value_of(config, f"scenarios.moderate.{share}")
    assert value_of(config, "demo.scenario") in config["scenarios"]


def test_check_thresholds_are_positive():
    for name, entry in config_check.walk_inputs(load_config()["checks"]):
        assert entry["value"] > 0, name
