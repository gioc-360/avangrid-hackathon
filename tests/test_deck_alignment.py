"""Deck alignment: the deck profile and the deck-replica profile against the teammate's final-deck targets.

What: runs the deck screen once on the full data with the teammate's two arrays and compares overloaded
      share, fixed without an upgrade, average units, winter driven share, NYSEG money and both peak cuts with
      profiles.deck.targets inside profiles.deck.tolerances; runs the replica of her code and requires it to
      equal her saved results exactly; unit tests pin the rating rule, the sizing rule and the money arithmetic.
Why:  the final deck uses these numbers; the tool must reproduce them by default or say plainly where and why
      it does not. A target we miss is reported, never tuned away: its test is marked xfail with the cause
      measured by the ladder and the seed spread in `bin/ewu screen --replica` (ewu.deck_replica.* facts).
How:  pytest; module fixtures run ewu/deck_screen.run_deck_screen() (about 3 s) and the replica for both
      scenarios (about 3 s; skipped when the teammate's folder, which holds her tiers, is not on this machine).
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from ewu import FLAG_COLUMNS, PROCESSED, ROOT, config_value, read_config, read_inputs
from ewu import deck, deck_money, deck_replica, deck_replica_run, deck_screen

CONFIG = read_config()
LIMIT = float(config_value("profiles.deck.overload_limit", CONFIG))
SCENARIOS = ("moderate", "high")
FOLDER = Path(config_value("profiles.deck.teammate_folder", CONFIG)).expanduser()
TIERS = ("our inventory tiers: the ladder step from her tiers to ours (A to B) moves her own run from 93.5% to 91.5% "
         "fixed in the high case, and over seeds 1 to 20 the deck profile's high case spans 90.7% to 93.2% (mean 91.8%), "
         "below 94% minus 2 points")
DRAW = ("sampling and tiers: the ladder moves her run's 72.9% to 76.3% with our tiers (A to B) and to 79.8% with our "
        "fixed-count adopter draw (C to D); over seeds 1 to 20 the deck profile's moderate case spans 72.1% to 81.0% "
        "(mean 78.0%), so 73% sits inside the range but our seed 5 does not reach it")


def target(name):
    return config_value(f"profiles.deck.targets.{name}", CONFIG)


def tolerance(name):
    return config_value(f"profiles.deck.tolerances.{name}", CONFIG)


@pytest.fixture(scope="module")
def result():
    return deck_screen.run_deck_screen(read_inputs(), CONFIG, managed=False)


def cell(result, i):
    return result["cells"][(SCENARIOS[i], LIMIT)]


@pytest.mark.parametrize("i", [0, 1])
def test_overloaded_share_matches_the_deck(result, i):
    assert abs(cell(result, i)["overloaded_pct"] - target("overloaded_pct")[i]) <= tolerance("overloaded_pts")


@pytest.mark.parametrize("i", [0, pytest.param(1, marks=pytest.mark.xfail(reason="high 91.6% against 94%: " + TIERS, strict=True))])
def test_fixed_without_upgrade_matches_the_deck(result, i):
    assert abs(cell(result, i)["fixed_of_overloaded_pct"] - target("fixed_without_upgrade_pct")[i]) <= tolerance("fixed_pts")


@pytest.mark.parametrize("i", [0, 1])
def test_average_units_match_the_deck(result, i):
    assert abs(cell(result, i)["average_units"] - target("average_units")[i]) <= tolerance("average_units")


@pytest.mark.parametrize("i", [pytest.param(0, marks=pytest.mark.xfail(reason="moderate 79.8% against 73%: " + DRAW, strict=True)), 1])
def test_winter_driven_share_matches_the_deck(result, i):
    assert abs(cell(result, i)["winter_of_overloaded_pct"] - target("winter_share_pct")[i]) <= tolerance("winter_pts")


@pytest.mark.parametrize("column,name", [("avangrid_cost", "avangrid_cost_musd"), ("gross", "gross_musd"),
                                         ("upgrade_all", "upgrade_all_musd")])
@pytest.mark.parametrize("i", [0, 1])
def test_nyseg_money_matches_the_deck(result, i, column, name):
    ours = result["money"][(SCENARIOS[i], LIMIT)]["nyseg_musd"][column]
    assert abs(ours - target(name)[i]) <= tolerance("money_share") * target(name)[i]


def test_behind_the_meter_peak_cut_matches_the_deck(result):
    assert abs(result["peak"]["behind_meter_mw"] - target("peak_cut_behind_meter_mw")) <= tolerance("peak_mw")


def test_export_fleet_peak_cut_matches_the_deck(result):
    """The deck's 8.8 MW is the teammate's program.py peak drop (profiles.deck.peak_cut_metric), measured the same way."""
    assert config_value("profiles.deck.peak_cut_metric", CONFIG) == "peak_drop"
    assert abs(result["peak"]["export_peak_drop_mw"] - target("peak_cut_export_mw")) <= tolerance("peak_mw")


def test_deck_profile_loads_the_teammates_arrays(result):
    assert result["setup"]["origins"] == {"ev_start_pmf": "teammate", "hp_increment": "teammate"}


def test_a_changed_array_fails_loudly(tmp_path):
    bad = tmp_path / "hp_increment.npy"
    np.save(bad, np.zeros(deck.HOURS))
    from ewu.deck_arrays import verify_array
    with pytest.raises(ValueError, match="sha256"):
        verify_array("hp_increment", bad, CONFIG)


@pytest.fixture(scope="module")
def replica():
    if not (FOLDER / config_value("profiles.deck_replica.classification_file", CONFIG)).exists():
        pytest.skip("the teammate's folder (her tiers) is not on this machine")
    homes = pd.read_parquet(PROCESSED / "segmented.parquet", columns=FLAG_COLUMNS)
    setup = deck_replica.replica_setup(homes, CONFIG)
    return deck_replica_run.run_scenarios(setup, CONFIG, config_value("profiles.deck_replica.unit_kwh", CONFIG))


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_replica_equals_her_saved_results(replica, scenario):
    """Her ewu_bo2_econ.json and ewu_results.json values (teammate.audit.file.* facts) at the decimals she saved."""
    saved = {k[len(f"teammate.audit.file.{scenario}."):]: v["value"] for k, v in
             json.loads((ROOT / "facts/facts.json").read_text()).items() if k.startswith(f"teammate.audit.file.{scenario}.")}
    _, cells, money = replica[scenario]
    cell, musd = cells[LIMIT], money[LIMIT]["nyseg_musd"]
    assert round(cell["overloaded_pct"], 1) == saved["overloaded"] and round(cell["fixed_of_overloaded_pct"], 1) == saved["fixed"]
    assert round(cell["average_units"], 2) == saved["mean_units"]
    assert round(cell["winter_of_overloaded_pct"], 1) == saved["results_winter_driven"]
    assert (musd["avangrid_cost"], musd["upgrade_all"], musd["gross"], musd["net_without_nyserda"]) == \
        (saved["net_m"], saved["trad_m"], saved["gross_m"], saved["netnony_m"])


def test_cautious_profile_still_exists_and_deck_is_the_default():
    assert config_value("profiles.default", CONFIG) == "deck"
    assert config_value("transformer.base_margin", CONFIG) == 1.15
    assert config_value("profiles.deck.managed_charging", CONFIG) is False


def test_rating_is_the_smallest_standard_size_at_or_above_peak_over_085():
    rating, above = deck.standard_rating(np.array([10.0, 21.25, 21.26, 140.0, 300.0]), CONFIG)
    assert rating.tolist() == [25.0, 25.0, 37.5, 167.0, 501.0] and above == 1


def test_units_are_the_larger_of_power_and_energy_need_per_day():
    total = np.zeros((2, deck.HOURS))
    total[0, 18:21] = [13.0, 13.0, 13.0]          # 3 kW over for 3 hours: 1 unit by power, 2 by energy (9 kWh)
    total[1, 18] = 18.0                           # 8 kW over for 1 hour: 3 units by power, 1 by energy
    assert deck.battery_units(total, np.array([10.0, 10.0]), CONFIG).tolist() == [2, 3]


def test_money_formula_reproduces_the_deck_on_the_teammates_own_counts():
    over = target("overloaded_pct")[0] / 100 * 3000
    fixed = over * target("fixed_without_upgrade_pct")[0] / 100
    implied = {"transformers": 3000, "overloaded": over, "upgrades": over - fixed,
               "batteries": fixed * target("average_units")[0]}
    money = deck_money.price_deck(implied, CONFIG)["nyseg_musd"]
    for column, name in (("avangrid_cost", "avangrid_cost_musd"), ("upgrade_all", "upgrade_all_musd"), ("gross", "gross_musd")):
        assert abs(money[column] - target(name)[0]) <= 1.0     # the targets are rounded shares, so within $1M
    assert round(deck_money.deck_prices(CONFIG)["upgrade_counted_usd"], -1) == 10250


@pytest.mark.parametrize("i", [0, 1])
def test_unit_bands_add_up_to_fixed(result, i):
    """Slide 12's stacked bar: fixed by 1 or 2 units + fixed by 3 or 4 units = fixed; with upgrades = overloaded."""
    c = cell(result, i)
    assert c["fixed_units_1_2"] + c["fixed_units_3_4"] == c["fixed"]
    assert c["fixed"] + c["upgrades"] == c["overloaded"]


@pytest.mark.parametrize("limit", config_value("profiles.deck.overload_limit_options", CONFIG))
@pytest.mark.parametrize("scenario", SCENARIOS)
def test_recorded_money_and_shares_are_deck_v3s(scenario, limit):
    """The battery plan's money: recorded costs and savings equal the formula recomputed from recorded counts and prices."""
    facts = {k: v["value"] for k, v in json.loads((ROOT / "facts/facts.json").read_text()).items()}
    f = lambda name: facts[f"ewu.deck.{scenario}.{deck_screen.limit_label(limit)}.{name}"]
    deck_cfg = lambda name: config_value(f"profiles.deck.{name}", CONFIG)
    u = deck_cfg("upgrade_usd") * facts["ewu.deck.prices.factor"] / facts["ewu.deck.prices.life_factor"]
    scale = facts["ewu.deck.nyseg_transformers"] / deck_cfg("transformer_count") / 1e6
    net = (f("batteries") * (deck_cfg("battery_unit_usd") - facts["ewu.deck.prices.lease_pv_usd"] - deck_cfg("nyserda_usd_unit"))
           + f("upgrades") * u) * scale
    upall = f("overloaded") * u * scale
    assert abs(f("nyseg_avangrid_cost_musd") - net) <= 0.06 and abs(f("nyseg_upgrade_all_musd") - upall) <= 0.06
    assert abs(f("saving_vs_upgrade_all_pct") - 100 * (1 - net / upall)) <= 0.02
    assert abs(f("fixed_units_1_2_pct") + f("fixed_units_3_4_pct") + f("upgrades_pct") - f("overloaded_pct")) <= 0.03


def test_the_page_carries_deck_profile_numbers_only():
    """Gio, 2026-11-13: "v3 is final numbers and app should reflect that.. no more of the old numbers"."""
    from ewu import demo_page
    values = demo_page.collect_values(CONFIG)
    cautious = ("ewu.sensitivity.", "ewu.economics.", "ewu.coldsnap.", "ewu.network.", "ewu.screen.", "ewu.deck.managed.",
                "ewu.deck.network_managed.", "ewu.deck.recharge.")
    assert [k for k in values if k.split(":", 1)[1].startswith(cautious)] == []
    assert not [k for k in values if k.startswith("config:") and k[7:].startswith(("transformer.", "battery.", "shift."))
                and k[7:] in demo_page.TEMPLATE.read_text()]
    saving = sorted(values[f"fact:ewu.deck.{s}.limit_120.saving_vs_upgrade_all_pct"] for s in SCENARIOS)
    assert [round(x) for x in saving] == [58, 69] and round(values["fact:teammate.audit.rerun.fleet_priority.peak_cut_mw"], 1) == 8.8
