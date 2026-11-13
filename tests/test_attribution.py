"""Attribution tests (M2): overload hours split cleanly, EV shifting moves energy without losing any, facts match.

What: the base-first fair split adds up to the energy above the limit in every hour; lead-cause, energy and
      worst-hour shares sum to 100% in every cell; timer and staggered charging deliver exactly the EV energy
      unmanaged charging does, home by home; staggered EVs on one transformer start in different slots;
      unmanaged results equal the M1 baseline facts; timer and staggered results are in facts and equal a rerun.
Why:  the answer to "does staggering fix heat pump night overloads" rests on these numbers, so the split must
      add up, the shift must be a pure move of energy, and what FINDINGS.md quotes must be what the code makes.
How:  runs ewu.attribution.run_attribution once for the module (all seeds, scenarios, groupings, EV modes),
      plus small planted cases with answers worked out by hand.
"""
import json
import numpy as np
import pytest
from ewu import ROOT, config_value, read_config, read_inputs
from ewu import attribution, feeders, shift, stress
from ewu.adoption import HOURS, measure_ev_sessions

CONFIG = read_config()
SEEDS = range(config_value("checks.seeds", CONFIG))
TOLERANCE = config_value("checks.attribution_sum_tolerance_pts", CONFIG)
BASE_MARGIN = config_value("transformer.base_margin", CONFIG)


@pytest.fixture(scope="module")
def inputs():
    return read_inputs()


@pytest.fixture(scope="module")
def summary(inputs):
    return attribution.summarize_runs(attribution.run_attribution(inputs, CONFIG, SEEDS), CONFIG)


@pytest.fixture(scope="module")
def one_run(inputs):
    k, count = config_value("transformer.homes_per_transformer", CONFIG), config_value("transformer.count", CONFIG)
    groups = feeders.build_transformers(inputs["homes"]["segment"].to_numpy(), k, count, "random", 0)
    sessions = measure_ev_sessions(inputs["load"], inputs["homes"]["is_ev_l2"], inputs["temp"], CONFIG)
    parts = stress.loading_parts(inputs, groups, "high", 0, CONFIG, sessions)
    return groups, parts, stress.transformer_of_each_home(groups, len(inputs["homes"]))


def test_fair_split_adds_up_to_the_energy_above_the_limit():
    base, ev, hp = np.array([40.0, 46.0, 30.0]), np.array([7.2, 0.0, 7.2]), np.array([3.0, 2.0, 0.0])
    ceiling = np.array([45.0, 45.0, 45.0])
    shares = attribution.fair_shares(base, ev, hp, ceiling)
    total = sum(shares[s] for s in attribution.SOURCES)
    assert np.allclose(total, np.maximum(base + ev + hp - ceiling, 0.0))
    assert shares["ev"][0] == pytest.approx(3.7) and shares["hp"][0] == pytest.approx(1.5)
    assert shares["base"][1] == pytest.approx(1.0) and shares["hp"][1] == pytest.approx(2.0)
    assert total[2] == 0.0


def test_shares_sum_to_100_pct_in_every_cell(summary):
    for key, cell in summary.items():
        n = cell["counts"]
        for family, whole in (("hours_lead_{}", n["hours_over"]), ("kwh_over_{}", n["kwh_over_total"]),
                              ("worst_lead_{}", n["overloaded"])):
            got = 100.0 * sum(n[family.format(s)] for s in attribution.SOURCES) / whole
            assert abs(got - 100.0) <= TOLERANCE, (key, family, got)
        assert n["hours_over"] > 0 and n["overloaded"] > 0


def test_shifting_moves_ev_energy_and_loses_none(one_run):
    groups, parts, owner = one_run
    unmanaged = shift.ev_loading_by_mode("unmanaged", parts, owner, groups.count, CONFIG)
    for mode in ("timer", "staggered"):
        moved = shift.ev_loading_by_mode(mode, parts, owner, groups.count, CONFIG)
        tolerance = config_value("checks.energy_balance_tolerance_pct", CONFIG) / 100
        assert moved.sum() == pytest.approx(unmanaged.sum(), rel=min(tolerance, 1e-9))
        assert np.allclose(moved.sum(1), unmanaged.sum(1), rtol=1e-9)
        assert (moved >= 0).all()


def test_each_home_gets_the_same_energy_at_no_more_than_the_mode_power(one_run):
    _, parts, _ = one_run
    sessions, kw = parts["ev_sessions"], config_value("scenarios.loads.ev_l2_kw", CONFIG)
    energy = shift.delivered_hours(sessions) * kw
    power = config_value("shift.stagger_power_share", CONFIG) * kw
    home, hour, row_kw = shift.spread_energy(sessions["home"], sessions["start"], energy, power)
    assert (row_kw <= power + 1e-9).all() and (row_kw > 0).all() and ((hour >= 0) & (hour < HOURS)).all()
    per_home = np.bincount(home, weights=row_kw)
    assert np.allclose(per_home, np.bincount(sessions["home"], weights=energy, minlength=len(per_home)))


def test_timer_starts_every_session_at_the_timer_hour(one_run):
    groups, parts, owner = one_run
    timer = shift.ev_loading_by_mode("timer", parts, owner, groups.count, CONFIG)
    start = config_value("shift.timer_start_hour", CONFIG)
    by_hour = timer.sum(0).reshape(-1, 24).sum(0)
    assert by_hour.argmax() == start
    assert by_hour[(start - 1) % 24] < by_hour[start]


def test_staggered_evs_on_one_transformer_start_in_different_slots(one_run):
    _, parts, owner = one_run
    window = (config_value("shift.stagger_end_hour", CONFIG) - config_value("shift.stagger_start_hour", CONFIG)) % 24
    slots = shift.stagger_slots(parts["ev_homes"], owner, window)
    by_transformer = {}
    for home, slot in slots.items():
        by_transformer.setdefault(owner[home], []).append(slot)
    for found in by_transformer.values():
        assert len(set(found)) == min(len(found), window)


def test_overloads_without_any_ev_are_the_same_in_every_mode(summary):
    for scenario in stress.SCENARIOS:
        for grouping in feeders.MODES:
            floors = {summary[(scenario, grouping, m)]["attribution"]["overloaded_without_ev_of_all_pct"]
                      for m in shift.EV_MODES}
            assert len(floors) == 1, (scenario, grouping, floors)


def test_unmanaged_mode_reproduces_the_m1_baseline(summary):
    facts = json.loads((ROOT / "facts" / "facts.json").read_text())
    for scenario in stress.SCENARIOS:
        for grouping in feeders.MODES:
            for margin, row in summary[(scenario, grouping, "unmanaged")]["by_margin"].items():
                key = f"ewu.stress.{scenario}.{grouping}.{stress.margin_label(margin)}.overloaded_pct"
                assert row["overloaded_pct"] == facts[key]["value"], key


def test_timer_and_staggered_results_are_in_facts(summary):
    facts = json.loads((ROOT / "facts" / "facts.json").read_text())
    for (scenario, grouping, mode), cell in summary.items():
        for margin, row in cell["by_margin"].items():
            key = f"ewu.shift.{scenario}.{grouping}.{stress.margin_label(margin)}.{mode}"
            names = ("overloaded_pct",) if mode == "unmanaged" else ("overloaded_pct", "fixed_pct", "new_overloads_pct")
            for name in names:
                assert facts[f"{key}.{name}"]["value"] == row[name], f"{key}.{name}"
        key = f"ewu.attribution.{scenario}.{grouping}.{stress.margin_label(BASE_MARGIN)}.{mode}"
        for name, value in cell["attribution"].items():
            assert facts[f"{key}.{name}"]["value"] == value, f"{key}.{name}"
