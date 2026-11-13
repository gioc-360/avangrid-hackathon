"""Screen and demo tests (M6): the live command agrees with the grid, a real map plugs in, the page checks itself.

What: the live screen's split adds up (Shift + Protect + Upgrade = Flag + newly overloaded); its counts equal
      the sensitivity grid's for the same seed, scenario and margin; a real meter-to-transformer map with
      transformers of different sizes runs through the same ladder; load_map() refuses a meter under two
      transformers; a page missing a step's facts says "not built"; demo_check's self-test catches every
      planted fault.
Why:  the live command is what a judge watches, so it must be the same code and the same answer as the
      cached grid the page shows, and the map path is how Avangrid would run it for real.
How:  one seed on the full data; a map CSV written to a temporary folder from real meter ids (it never
      leaves the machine and is deleted after the test).
"""
import numpy as np
import pandas as pd
import pytest
from checks import demo_check
from ewu import config_value, read_config, read_inputs
from ewu import adoption, demo_page, feeders as feeder_groups, screen, sensitivity, stress

CONFIG = read_config()
SCENARIO, MARGIN = config_value("demo.scenario", CONFIG), config_value("demo.margin", CONFIG)


@pytest.fixture(scope="module")
def inputs():
    return read_inputs()


@pytest.fixture(scope="module")
def live(inputs):
    return screen.run_screen(inputs, CONFIG, SCENARIO, MARGIN)


def test_the_split_adds_up(live):
    assert live["shift_fixed"] + live["protected"] + live["upgrade_left"] == live["flagged"] + live["new_from_stagger"]
    assert live["protect_set"] == live["protected"] + live["upgrade_left"]
    assert live["transformers"] == config_value("transformer.count", CONFIG)


def test_live_screen_equals_the_grid_for_the_same_seed(inputs, live):
    seed = config_value("demo.screen_seed", CONFIG)
    k, count = config_value("transformer.homes_per_transformer", CONFIG), config_value("transformer.count", CONFIG)
    groups = feeder_groups.build_transformers(inputs["homes"]["segment"].to_numpy(), k, count, "random", seed)
    sessions = adoption.measure_ev_sessions(inputs["load"], inputs["homes"]["is_ev_l2"], inputs["temp"], CONFIG)
    base = stress.base_loading(inputs["load"], groups)
    parts = stress.loading_parts(inputs, groups, SCENARIO, seed, CONFIG, sessions, base)
    top, top_day = sensitivity.top_hours_and_days(CONFIG)
    grid = sensitivity.ladder_for_one_run(inputs, groups, base, parts, CONFIG, top, top_day)[MARGIN]
    assert {name: live[name] for name in grid} == grid


def test_groups_by_size_keeps_every_home_once():
    homes = np.arange(20)
    transformer = np.array([0] * 8 + [1] * 6 + [2] * 6)
    batches = screen.groups_by_size(feeder_groups.Feeders(homes, transformer, 3))
    assert sorted(len(b.homes) // b.count for b in batches) == [6, 8]
    assert sorted(np.concatenate([b.homes for b in batches]).tolist()) == homes.tolist()


def test_a_real_map_with_uneven_transformers_runs(inputs, tmp_path):
    rng = np.random.default_rng(7)
    rows = rng.choice(np.flatnonzero(~inputs["homes"]["is_other_inactive"].to_numpy()), 360, replace=False)
    ids = inputs["homes"]["CUSTOMER_NUMBER"].to_numpy()[rows]
    owner = np.concatenate([np.repeat(np.arange(30), 8), np.repeat(np.arange(30, 50), 6)])
    path = tmp_path / "map.csv"
    pd.DataFrame({"meter_id": ids, "transformer_id": [f"T{t}" for t in owner], "kva": 25}).to_csv(path, index=False)
    cell = screen.run_screen(inputs, CONFIG, SCENARIO, MARGIN, map_path=path)
    assert cell["map"] and cell["transformers"] == 50 and cell["homes"] == 360
    assert cell["shift_fixed"] + cell["protected"] + cell["upgrade_left"] == cell["flagged"] + cell["new_from_stagger"]


def test_load_map_refuses_a_meter_under_two_transformers(tmp_path):
    path = tmp_path / "map.csv"
    pd.DataFrame({"meter_id": ["a", "a"], "transformer_id": ["T1", "T2"], "kva": [25, 25]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="two transformers"):
        feeder_groups.load_map(path, ["a"])


def test_a_step_without_its_facts_shows_not_built():
    values = demo_page.collect_values(CONFIG)
    built, _ = demo_page.steps_built(values)
    assert all(built.values())
    lost = {k: v for k, v in values.items() if not k.startswith("private:ewu.coldsnap.")}
    built, missing = demo_page.steps_built(lost)
    assert not built["coldsnap"] and built["money"] and missing["coldsnap"]
    assert '"coldsnap":false' in demo_page.page_html(lost)


def test_demo_check_catches_every_planted_fault():
    assert demo_check.run_selftest()
