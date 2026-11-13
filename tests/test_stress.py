"""Stress tests (M1): the baseline transformer stress test adds up, groups homes cleanly and behaves with sizing.

What: loading equals base plus EV plus heat pump adds, recomputed a second way; no home sits in two
      transformers; the overloaded share never rises as the sizing margin rises; 5 seeds agree within the
      config tolerance; the overloaded share at every sizing margin is in facts/facts.json and equals a rerun.
Why:  every later number (attribution, shifting, batteries, money) is measured against this baseline, so it
      has to be right before anything is built on it.
How:  runs ewu.stress.run_grid once for the whole module (all seeds, scenarios, modes, margins), then checks
      each property. The second-way loading check walks a few transformers home by home, session by session.
"""
import json
import numpy as np
import pytest
from ewu import ROOT, config_value, read_config, read_inputs
from ewu import adoption, feeders, stress

CONFIG = read_config()
MARGINS = config_value("transformer.sizing_margins", CONFIG)
SEEDS = range(config_value("checks.seeds", CONFIG))


@pytest.fixture(scope="module")
def inputs():
    return read_inputs()


@pytest.fixture(scope="module")
def grid(inputs):
    rows, sessions = stress.run_grid(inputs, CONFIG, SEEDS)
    return rows, stress.summarize_grid(rows), sessions


@pytest.fixture(scope="module")
def one_run(inputs, grid):
    k, count = config_value("transformer.homes_per_transformer", CONFIG), config_value("transformer.count", CONFIG)
    groups = feeders.build_transformers(inputs["homes"]["segment"].to_numpy(), k, count, "random", 0)
    return groups, stress.loading_parts(inputs, groups, "moderate", 0, CONFIG, grid[2])


def test_loading_equals_base_plus_ev_plus_heat_pump_adds(inputs, one_run):
    groups, parts = one_run
    kw = config_value("scenarios.loads.ev_l2_kw", CONFIG)
    slope = config_value("scenarios.loads.hp_kw_per_degf", CONFIG)
    balance = config_value("scenarios.loads.hp_balance_temp_f", CONFIG)
    heat_pump = slope * np.maximum(0.0, balance - inputs["temp"])
    sessions = parts["ev_sessions"]
    for t in (0, 1, 7, groups.count // 2, groups.count - 1):
        homes = groups.homes[groups.transformer == t]
        base = np.asarray(inputs["load"][np.sort(homes)], dtype=np.float64).sum(0)
        ev = np.zeros(adoption.HOURS)
        for i in np.where(np.isin(sessions["home"], homes))[0]:
            start = sessions["start"][i]
            ev[start:min(start + sessions["hours"][i], adoption.HOURS)] += kw
        hp = np.isin(homes, parts["hp_homes"]).sum() * heat_pump
        assert np.allclose(parts["base"][t], base, atol=1e-6)
        assert np.allclose(parts["ev"][t], ev, atol=1e-6)
        assert np.allclose(parts["hp"][t], hp, atol=1e-4)
    charged = np.minimum(sessions["start"] + sessions["hours"], adoption.HOURS) - sessions["start"]
    assert parts["ev"].sum() == pytest.approx(charged.sum() * kw, rel=1e-9)
    assert parts["hp"].sum() == pytest.approx(len(parts["hp_homes"]) * heat_pump.sum(), rel=1e-5)


def test_adopters_do_not_have_the_device_today(inputs, one_run):
    groups, parts = one_run
    homes = inputs["homes"]
    for device, has_today, picked in (("ev_share", "is_ev_l2", parts["ev_homes"]),
                                      ("hp_share", "is_electric_heat", parts["hp_homes"])):
        assert not homes[has_today].to_numpy()[picked].any()
        assert not homes["is_other_inactive"].to_numpy()[picked].any()
        assert np.isin(picked, groups.homes).all()
        assert len(picked) == round(config_value(f"scenarios.moderate.{device}", CONFIG) * len(groups.homes))
    high_ev, high_hp = adoption.pick_adopters(groups.homes, homes, "high", 0, CONFIG)
    assert np.isin(parts["ev_homes"], high_ev).all() and np.isin(parts["hp_homes"], high_hp).all()


def test_no_home_sits_in_two_transformers(inputs, tmp_path):
    k, count = config_value("transformer.homes_per_transformer", CONFIG), config_value("transformer.count", CONFIG)
    for mode in feeders.MODES:
        for seed in SEEDS:
            groups = feeders.build_transformers(inputs["homes"]["segment"].to_numpy(), k, count, mode, seed)
            assert len(np.unique(groups.homes)) == len(groups.homes) == k * count
            assert (np.bincount(groups.transformer) == k).all() and groups.count == count
    ids = inputs["homes"]["CUSTOMER_NUMBER"].astype(str).to_numpy()
    good = tmp_path / "map.csv"
    good.write_text("meter_id,transformer_id,kva\n" + "".join(f"{m},T{i // 3},25\n" for i, m in enumerate(ids[:9])))
    real = feeders.load_map(good, ids)
    assert real.count == 3 and len(np.unique(real.homes)) == 9 and (real.rating_kva == 25).all()
    bad = tmp_path / "bad.csv"
    bad.write_text(good.read_text() + f"{ids[0]},T9,50\n")
    with pytest.raises(ValueError, match="two transformers"):
        feeders.load_map(bad, ids)


def test_overloaded_share_never_rises_as_margin_rises(grid):
    rows, summary, _ = grid
    order = sorted(MARGINS)
    for scenario in stress.SCENARIOS:
        for mode in feeders.MODES:
            means = [summary[(scenario, mode, m)]["overloaded_pct"] for m in order]
            assert means == sorted(means, reverse=True), (scenario, mode, means)
            for seed in SEEDS:
                one = [next(r["overloaded_pct"] for r in rows if (r["scenario"], r["mode"], r["seed"], r["margin"])
                            == (scenario, mode, seed, m)) for m in order]
                assert one == sorted(one, reverse=True)


def test_overload_metrics_catch_a_planted_overload():
    total = np.full((2, 24), 10.0)
    total[1, 5] = 13.0
    m = stress.overload_metrics(total, np.array([10.0, 10.0]), 1.2)
    assert m["overloaded"].tolist() == [False, True] and m["hours_over"][1] == 1
    assert m["kwh_over"][1] == pytest.approx(1.0)


def test_five_seeds_agree_within_tolerance(grid):
    _, summary, _ = grid
    tolerance = config_value("checks.seed_tolerance_pts", CONFIG)
    assert all(cell["seeds"] == len(SEEDS) for cell in summary.values())
    gaps = {key: cell["seed_gap_pts"] for key, cell in summary.items() if cell["seed_gap_pts"] > tolerance}
    assert gaps == {}


def test_overloaded_share_at_every_margin_is_in_facts(grid):
    _, summary, _ = grid
    facts = json.loads((ROOT / "facts" / "facts.json").read_text())
    for scenario in stress.SCENARIOS:
        for mode in feeders.MODES:
            for margin in MARGINS:
                key = f"ewu.stress.{scenario}.{mode}.{stress.margin_label(margin)}.overloaded_pct"
                assert key in facts, key
                assert facts[key]["value"] == summary[(scenario, mode, margin)]["overloaded_pct"], key
