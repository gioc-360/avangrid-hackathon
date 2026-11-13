"""Dispatch tests (M3): home batteries obey physics and the challenge spec, and the cold snap numbers are recorded.

What: state of charge stays between the reserve floor and capacity; charge and discharge stay within the
      challenge's continuous power; energy balances hour by hour and over the year within the config
      tolerance; batteries charge only under the limit, discharge only above it and never export; zero
      batteries reproduce the M1 numbers; a hand-made night gives the exact expected state of charge; the cold
      snap window is Feb 7-8; hours over, kWh over and share cleared are in facts and equal a rerun.
Why:  a battery result a judge cannot break is the answer to plan objection 1; every check here is one a
      judge could ask for.
How:  runs the dispatch for a full year on the 60 transformers with the most kWh over the limit (moderate
      2030, staggered EV charging, seed 0) with every hour kept, then checks each property on the stored
      arrays, recomputed independently of the dispatch loop.
"""
import json
import numpy as np
import pytest
from ewu import ROOT, config_value, read_config, read_inputs
from ewu import adoption, coldsnap, dispatch, feeders, shift, stress

CONFIG = read_config()
SEEDS = range(config_value("checks.seeds", CONFIG))
LIMIT = config_value("transformer.overload_limit", CONFIG)
BASE_MARGIN = config_value("transformer.base_margin", CONFIG)
UNITS = config_value("battery.units_per_host_max", CONFIG)
TOLERANCE = config_value("checks.energy_balance_tolerance_pct", CONFIG) / 100
EPS = 1e-9


@pytest.fixture(scope="module")
def inputs():
    return read_inputs()


@pytest.fixture(scope="module")
def sessions(inputs):
    return adoption.measure_ev_sessions(inputs["load"], inputs["homes"]["is_ev_l2"], inputs["temp"], CONFIG)


def seed_setup(inputs, sessions, seed, scenario="moderate"):
    k, count = config_value("transformer.homes_per_transformer", CONFIG), config_value("transformer.count", CONFIG)
    groups = feeders.build_transformers(inputs["homes"]["segment"].to_numpy(), k, count, "random", seed)
    base = stress.base_loading(inputs["load"], groups)
    return groups, base, stress.loading_parts(inputs, groups, scenario, seed, CONFIG, sessions, base)


@pytest.fixture(scope="module")
def full_year(inputs, sessions):
    groups, base, parts = seed_setup(inputs, sessions, 0)
    owner = stress.transformer_of_each_home(groups, len(inputs["homes"]))
    total = base + shift.ev_loading_by_mode("staggered", parts, owner, groups.count, CONFIG) + parts["hp"]
    ceiling = LIMIT * feeders.rate(base.max(1), BASE_MARGIN)
    excess = np.maximum(total - ceiling[:, None], 0.0)
    worst = np.argsort(-excess.sum(1))[:60]
    homes = groups.homes.reshape(groups.count, -1)[worst]
    home_kw = dispatch.own_loading(inputs, parts, homes.ravel(), owner, "staggered", CONFIG)
    hosts = dispatch.pick_hosts(home_kw.reshape(len(worst), homes.shape[1], -1), homes, excess[worst].argmax(1), 2)
    host_kw = dispatch.own_loading(inputs, parts, hosts.T.ravel(), owner, "staggered", CONFIG).reshape(2, len(worst), -1)
    spec = dispatch.battery_spec(UNITS, CONFIG)
    result = dispatch.run_batteries(total[worst], ceiling[worst], host_kw, spec, (0, adoption.HOURS))
    return {"total": total[worst], "ceiling": ceiling[worst], "host_kw": host_kw, "hosts": hosts,
            "homes": homes, "spec": spec, "result": result}


def test_state_of_charge_stays_between_floor_and_capacity(full_year):
    r, spec = full_year["result"], full_year["spec"]
    assert r["discharged_kwh"].sum() > 0, "the planted worst transformers must make the batteries work"
    for soc in (r["soc_kwh"], r["soc_min_kwh"], r["soc_max_kwh"]):
        assert soc.min() >= spec["floor_kwh"] - EPS and soc.max() <= spec["energy_kwh"] + EPS


def test_power_stays_within_the_challenge_spec(full_year):
    r, spec = full_year["result"], full_year["spec"]
    assert spec["power_kw"] == pytest.approx(UNITS / 2 * config_value("battery.power_kw_two_units", CONFIG))
    assert spec["energy_kwh"] == pytest.approx(UNITS / 2 * config_value("battery.energy_kwh_two_units", CONFIG))
    assert r["charge_kw"].min() >= 0 and r["discharge_kw"].min() >= 0
    assert r["charge_kw"].max() <= spec["power_kw"] + EPS and r["discharge_kw"].max() <= spec["power_kw"] + EPS


def test_energy_balance_holds_hour_by_hour_and_over_the_year(full_year):
    r, spec = full_year["result"], full_year["spec"]
    previous = np.concatenate([r["start_soc_kwh"][:, :, None], r["soc_kwh"][:, :, :-1]], axis=2)
    step = r["charge_kw"] * spec["efficiency"] - r["discharge_kw"]
    assert np.abs(r["soc_kwh"] - previous - step).max() <= EPS * 100
    stored = r["charge_kw"].sum(2) * spec["efficiency"] - r["discharge_kw"].sum(2)
    moved = r["charge_kw"].sum(2) + r["discharge_kw"].sum(2)
    assert (np.abs(stored - (r["end_soc_kwh"] - r["start_soc_kwh"])) <= TOLERANCE * np.maximum(moved, 1.0)).all()
    grid = full_year["total"] + r["charge_kw"].sum(0) - r["discharge_kw"].sum(0)
    assert np.abs(r["net_kw"] - grid).max() <= EPS * 100


def test_batteries_charge_only_under_the_limit_and_discharge_only_above(full_year):
    r, ceiling = full_year["result"], full_year["ceiling"][None, :, None]
    total = full_year["total"][None]
    charging = r["charge_kw"] > 0
    assert (r["net_kw"][None].repeat(2, 0)[charging] <= np.broadcast_to(ceiling, charging.shape)[charging] + EPS).all()
    assert not (charging & (total >= ceiling)).any()
    assert not ((r["discharge_kw"] > 0) & (total <= ceiling)).any()


def test_no_battery_discharges_more_than_its_own_home_draws(full_year):
    assert config_value("battery.export_to_neighbors", CONFIG) is False
    r = full_year["result"]
    assert (r["discharge_kw"] <= np.maximum(full_year["host_kw"], 0.0) + EPS).all()


def test_hosts_belong_to_their_transformer_and_are_distinct(full_year):
    hosts, homes = full_year["hosts"], full_year["homes"]
    assert all(set(h) <= set(g) and len(set(h)) == len(h) for h, g in zip(hosts, homes))


def test_a_hand_made_night_gives_the_expected_state_of_charge():
    spec = dispatch.battery_spec(1, CONFIG)
    energy, power, eff = spec["energy_kwh"], spec["power_kw"], spec["efficiency"]
    total = np.array([[8.0, 8.0, 12.0, 12.0, 12.0, 15.0, 9.0, 9.0]])
    host = np.full((1, 1, 8), 100.0)
    r = dispatch.run_batteries(total, np.array([10.0]), host, spec, (0, 8))
    after_three = energy - 6.0
    expected = [energy, energy, energy - 2, energy - 4, after_three, after_three - power,
                after_three - power + eff, after_three - power + 2 * eff]
    assert r["soc_kwh"][0, 0] == pytest.approx(expected)
    assert r["hours_over"][0] == 1 and r["kwh_over"][0] == pytest.approx(5.0 - power)
    capped = dispatch.run_batteries(total, np.array([10.0]), np.full((1, 1, 8), 1.0), spec, (0, 8))
    assert capped["discharge_kw"].max() == pytest.approx(1.0)


def test_zero_batteries_reproduce_the_m1_numbers(inputs, sessions):
    facts = json.loads((ROOT / "facts" / "facts.json").read_text())
    margins = config_value("transformer.sizing_margins", CONFIG)
    shares = {m: [] for m in margins}
    no_battery = dispatch.battery_spec(UNITS, CONFIG)
    for seed in SEEDS:
        groups, base, parts = seed_setup(inputs, sessions, seed)
        total = base + parts["ev"] + parts["hp"]
        for margin in margins:
            rating = feeders.rate(base.max(1), margin)
            m1 = stress.overload_metrics(total, rating, LIMIT)
            r = dispatch.run_batteries(total, LIMIT * rating, np.zeros((0,) + total.shape), no_battery)
            assert (r["hours_over"] == m1["hours_over"]).all()
            assert np.allclose(r["kwh_over"], m1["kwh_over"], rtol=1e-9, atol=1e-9)
            shares[margin].append(100.0 * (r["hours_over"] > 0).mean())
    for margin in margins:
        key = f"ewu.stress.moderate.random.{stress.margin_label(margin)}.overloaded_pct"
        assert round(float(np.mean(shares[margin])), 2) == facts[key]["value"], key


def test_cold_snap_window_is_feb_7_to_8():
    first, last, stamps = coldsnap.window_hours(config_value("demo.cold_snap_start", CONFIG), CONFIG)
    assert last - first == 48 and len(stamps) == 48
    assert str(stamps[0].date()) == config_value("demo.cold_snap_start", CONFIG)
    assert str(stamps[-1].date()) == config_value("demo.cold_snap_end", CONFIG) and stamps[-1].hour == 23


def test_hours_over_kwh_over_and_share_cleared_are_in_facts(inputs):
    runs, _ = coldsnap.run_coldsnap(inputs, CONFIG, config_value("demo.cold_snap_start", CONFIG), SEEDS)
    summary = coldsnap.summarize_coldsnap(runs)
    facts = json.loads((ROOT / "facts" / "facts.json").read_text())
    margin = stress.margin_label(BASE_MARGIN)
    for (scenario, mode), cell in summary.items():
        key = f"ewu.coldsnap.{scenario}.{mode}.{margin}"
        for name in ("flagged_pct", "hours_over_median", "kwh_over_median", "longest_run_median"):
            assert facts[f"{key}.{name}"]["value"] == cell[name], f"{key}.{name}"
        for count, block in cell["hosts"].items():
            for name in ("cleared_pct", "kwh_over_left_pct", "ran_empty_pct"):
                assert facts[f"{key}.hosts_{count}.{name}"]["value"] == block[name], f"{key}.hosts_{count}.{name}"
            assert 0.0 <= block["cleared_pct"] <= 100.0
    assert set(summary) == {(s, m) for s in stress.SCENARIOS for m in coldsnap.COLD_MODES}
