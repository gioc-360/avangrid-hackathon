"""Robustness tests (M8 fixes): the slope variants, flag durations and 3 kVA rerun agree with the recorded runs.

What: a heat pump slope of 1.0 times reproduces the M2 facts; a heavier heat pump never lets staggering fix
      more or the heat pump lead fewer overload hours; the one-hour flagged share equals the M1 fact at every
      margin and scenario, and a longer minimum never flags more; the 2-hour 3 kVA run reproduces the
      existing bess.py facts, and the measured-length charge never passes more homes; the charge profile
      delivers exactly its length times the charger kW; the duration summary is right on a planted case.
Why:  these numbers now sit in FINDINGS.md and the business case next to the headline, so each must be what
      the code makes, and each variant must differ from the recorded run only in the input it changes.
How:  read facts/facts.json written by ewu/robustness.py and ewu/headroom.py, plus small cases worked by hand.
"""
import json
import numpy as np
import pytest
from ewu import ROOT, config_value, read_config, headroom, robustness, stress

CONFIG = read_config()
FACTS = {k: v["value"] for k, v in json.loads((ROOT / "facts/facts.json").read_text()).items()}
BASE = stress.margin_label(config_value("transformer.base_margin", CONFIG))
MULTIPLIERS = config_value("robustness.hp_slope_multipliers", CONFIG)
SIZES = ("none", "one_unit", "two_units")


def slope_fact(multiplier, scenario, rest):
    return FACTS[f"ewu.robustness.{robustness.slope_label(multiplier)}.{scenario}.{BASE}.{rest}"]


@pytest.mark.parametrize("scenario", stress.SCENARIOS)
def test_slope_of_one_reproduces_the_recorded_attribution(scenario):
    assert slope_fact(1.0, scenario, "staggered.fixed_pct") == FACTS[f"ewu.shift.{scenario}.random.{BASE}.staggered.fixed_pct"]
    assert slope_fact(1.0, scenario, "unmanaged.overloaded_pct") == FACTS[f"ewu.stress.{scenario}.random.{BASE}.overloaded_pct"]
    for name in robustness.SHOWN:
        assert slope_fact(1.0, scenario, f"unmanaged.{name}") == \
            FACTS[f"ewu.attribution.{scenario}.random.{BASE}.unmanaged.{name}"]


@pytest.mark.parametrize("scenario", stress.SCENARIOS)
def test_heavier_heat_pump_weakens_staggering(scenario):
    fixed = [slope_fact(m, scenario, "staggered.fixed_pct") for m in sorted(MULTIPLIERS)]
    led = [slope_fact(m, scenario, "unmanaged.hours_lead_hp_pct") for m in sorted(MULTIPLIERS)]
    assert fixed == sorted(fixed, reverse=True) and led == sorted(led)


@pytest.mark.parametrize("scenario", stress.SCENARIOS)
def test_one_hour_flag_equals_the_baseline_and_longer_rules_flag_less(scenario):
    for margin in config_value("transformer.sizing_margins", CONFIG):
        label = stress.margin_label(margin)
        key = f"ewu.robustness.flag_hours.{scenario}.random.{label}"
        assert FACTS[f"{key}.flagged_pct"] == FACTS[f"ewu.stress.{scenario}.random.{label}.overloaded_pct"]
        assert FACTS[f"{key}.flagged_min_hours_pct"] <= FACTS[f"{key}.flagged_pct"]
        assert 0 <= FACTS[f"{key}.short_of_flagged_pct"] <= 100


@pytest.mark.parametrize("scenario", stress.SCENARIOS)
def test_adoption_variants_one_order_is_the_recorded_run_and_apart_overlaps_less(scenario):
    one, own = (f"ewu.robustness.adoption_{label}.{scenario}.{BASE}." for label in ("one_order", "own_order"))
    assert FACTS[one + "unmanaged.overloaded_pct"] == FACTS[f"ewu.stress.{scenario}.random.{BASE}.overloaded_pct"]
    assert FACTS[one + "staggered.fixed_pct"] == FACTS[f"ewu.shift.{scenario}.random.{BASE}.staggered.fixed_pct"]
    for name in robustness.SHOWN:
        assert FACTS[one + f"unmanaged.{name}"] == FACTS[f"ewu.attribution.{scenario}.random.{BASE}.unmanaged.{name}"]
    assert FACTS[own + "hp_homes_with_new_ev_pct"] < FACTS[one + "hp_homes_with_new_ev_pct"]


def test_duration_summary_on_a_planted_case():
    seeds = [np.array([0, 1, 2, 3, 5]), np.array([0, 0, 1, 4, 0])]
    cell = robustness.summarize_flag_duration(seeds, 3)
    assert cell["flagged_pct"] == 60.0              # 4 of 5, then 2 of 5
    assert cell["flagged_min_hours_pct"] == 30.0    # 2 of 5, then 1 of 5
    assert cell["short_of_flagged_pct"] == 50.0     # 1, 2 and 1 of the 6 flagged are under 3 hours
    assert cell["median_hours_of_flagged"] == 2.5


def test_assumed_charge_reproduces_the_existing_headroom_facts():
    for size in SIZES:
        assert FACTS[f"ewu.headroom.ev.charge_assumed.pass_pct_{size}"] == FACTS[f"bess.headroom_rule.ev_pass_pct_{size}"]


def test_measured_charge_length_is_the_measured_mean_and_passes_no_more_homes():
    assert FACTS["ewu.headroom.ev.measured_mean_hours"] == FACTS["ewu.adoption.ev_session_mean_hours"]
    assert FACTS["ewu.headroom.ev.measured_mean_hours"] > config_value("robustness.headroom_ev_hours_assumed", CONFIG)
    for size in SIZES:
        assert FACTS[f"ewu.headroom.ev.charge_measured_mean.pass_pct_{size}"] <= \
            FACTS[f"ewu.headroom.ev.charge_assumed.pass_pct_{size}"]


def test_charge_profile_delivers_its_length_in_kwh():
    kw = headroom.charge_profile(18, 3.78, 7.2)
    assert kw.sum() == pytest.approx(3.78 * 7.2)
    assert list(np.flatnonzero(kw)) == [18, 19, 20, 21] and kw[21] == pytest.approx(0.78 * 7.2)
    assert headroom.charge_profile(23, 2, 7.2)[[23, 0]].tolist() == [7.2, 7.2]


def test_a_battery_holds_the_cap_only_within_its_energy_and_power():
    base = np.zeros((1, 8760), dtype=np.float32)
    add = headroom.charge_profile(18, 2, 5.0)        # 2 kW over a 3 kW cap for 2 hours: 4 kWh a day
    assert not headroom.passes_service_limit(base, add, 3.0, 0.0, 0.0)[0]
    assert headroom.passes_service_limit(base, add, 3.0, 4.0, 2.0)[0]
    assert not headroom.passes_service_limit(base, add, 3.0, 3.9, 2.0)[0]
    assert not headroom.passes_service_limit(base, add, 3.0, 4.0, 1.9)[0]
