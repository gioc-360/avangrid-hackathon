"""Fit score tests (M4): the top-hour set holds the named peak days, and fit-score hosts beat random hosts.

What: Feb 7 and Jul 2 (the dates Scott named) sit in the system top-hour set, and every picked hour is at
      least as high as every unpicked hour of its season; fit_score() gives the exact cut on hand-made homes
      and never exceeds the battery's power or the home's own load; hosts are distinct homes of their own
      transformer and fit-score hosts carry the highest fit kW on it; the flagged set matches the M2
      staggered overload share; fit-score hosts clear more flagged transformers per battery than random
      hosts on the same set with the same battery count, in every scenario, host count and unit count; and
      the recorded facts equal a rerun.
Why:  the plan's M4 exit check, plus the checks a judge would ask before trusting "pick hosts by fit score".
How:  hand cases for the arithmetic; one full run over the config's seeds for the rest, compared with the
      seed-pooled summary and with facts/facts.json.
"""
import json
import numpy as np
import pandas as pd
import pytest
from ewu import PROCESSED, ROOT, config_value, read_config, read_inputs
from ewu import dispatch, fitscore, stress

CONFIG = read_config()
SEEDS = range(config_value("checks.seeds", CONFIG))
MARGIN = stress.margin_label(config_value("transformer.base_margin", CONFIG))
FACTS = json.loads((ROOT / "facts/facts.json").read_text())


@pytest.fixture(scope="module")
def top_hours():
    index = pd.read_parquet(PROCESSED / "weather.parquet").index
    sysload = np.load(PROCESSED / "sysload.npy")
    return index, sysload, fitscore.system_top_hours(sysload, index, CONFIG)


@pytest.fixture(scope="module")
def full_run():
    runs, stamps = fitscore.run_fitscore(read_inputs(), CONFIG, SEEDS)
    return runs, stamps, fitscore.summarize_fitscore(runs)


def test_named_peak_days_are_in_the_top_hour_set(top_hours):
    index, _, top = top_hours
    days = {str(d.date()) for d in index[top]}
    for name in ("demo.winter_peak_date", "demo.summer_peak_date"):
        assert config_value(name, CONFIG) in days


def test_top_hours_are_the_highest_of_each_season(top_hours):
    index, sysload, top = top_hours
    count = config_value("battery.top_hours_per_season", CONFIG)
    assert len(top) == 2 * count and len(set(top)) == len(top)
    for season in ("battery.winter_months", "battery.summer_months"):
        months = np.isin(index.month, config_value(season, CONFIG))
        picked = np.zeros(len(index), bool)
        picked[top] = True
        assert (picked & months).sum() == count
        assert sysload[picked & months].min() >= sysload[~picked & months].max()


def test_fit_score_on_hand_made_homes():
    spec = dispatch.battery_spec(2, CONFIG)
    usable = spec["energy_kwh"] - spec["floor_kwh"]
    day = np.array([0, 0, 0, 0, 1, 1])
    homes = np.array([[10.0] * 6, [1.0] * 6, [0.0, 0, 0, 0, 10, -2]])
    got = fitscore.fit_score(homes, day, spec)
    power = spec["power_kw"]
    first_day = min(4 * power, usable) / 4
    assert got[0] == pytest.approx((4 * first_day + 2 * power) / 6)
    assert got[1] == pytest.approx(1.0)
    assert got[2] == pytest.approx(power / 6)


def test_fit_score_stays_within_power_and_own_load():
    rng = np.random.default_rng(7)
    homes = rng.gamma(2.0, 2.0, size=(50, 8, 40))
    day = np.repeat(np.arange(10), 4)
    for units in config_value("battery.units_per_host_options", CONFIG):
        spec = dispatch.battery_spec(units, CONFIG)
        got = fitscore.fit_score(homes, day, spec)
        assert (got >= 0).all() and (got <= spec["power_kw"] + 1e-9).all()
        assert (got <= homes.mean(-1) + 1e-9).all()


def test_hosts_are_distinct_homes_and_fit_hosts_score_highest(full_run):
    runs, _, _ = full_run
    k = config_value("transformer.homes_per_transformer", CONFIG)
    for run in runs.values():
        for (policy, count, units), block in run["placed"].items():
            hosts = block["hosts"]
            assert hosts.shape == (run["flagged"], count) and hosts.min() >= 0 and hosts.max() < k
            assert all(len(set(row)) == count for row in hosts.tolist())
            best = run["placed"][("fit_score", count, units)]["host_fit_kw"].reshape(-1, count).sum(1)
            assert (block["host_fit_kw"].reshape(-1, count).sum(1) <= best + 1e-9).all()


def test_flagged_set_matches_the_staggered_overload_share(full_run):
    _, _, summary = full_run
    for scenario, cell in summary.items():
        m2 = FACTS[f"ewu.shift.{scenario}.random.{MARGIN}.staggered.overloaded_pct"]["value"]
        assert cell["flagged_pct"] == pytest.approx(m2, abs=0.01)


def test_fit_score_hosts_clear_more_per_battery_than_random_hosts(full_run):
    _, _, summary = full_run
    for scenario, cell in summary.items():
        fit, rand = cell["policies"]["fit_score"], cell["policies"]["random"]
        for option in fit:
            if option == "cheapest":
                assert fit[option]["batteries_per_cleared"] < rand[option]["batteries_per_cleared"]
            else:
                assert fit[option]["cleared_per_100_batteries"] > rand[option]["cleared_per_100_batteries"], \
                    (scenario, option)
                assert fit[option]["host_fit_kw_median"] > rand[option]["host_fit_kw_median"]


def test_recorded_facts_equal_a_rerun(full_run):
    _, stamps, summary = full_run
    assert FACTS["ewu.fitscore.top_hours.count"]["value"] == len(stamps)
    for scenario, cell in summary.items():
        key = f"ewu.fitscore.{scenario}.{fitscore.EV_MODE}.{MARGIN}"
        assert FACTS[f"{key}.flagged_pct"]["value"] == cell["flagged_pct"]
        for policy, block in cell["policies"].items():
            for option, values in block.items():
                for name, value in values.items():
                    assert FACTS[f"{key}.{policy}.{option}.{name}"]["value"] == value, (key, policy, option, name)
