"""Deck alignment: the deck profile's own results against the teammate's final-deck targets, at a 120% limit.

What: runs the deck screen once on the full data and compares overloaded share, fixed without an upgrade,
      average units, winter driven share, NYSEG money and both peak cuts with profiles.deck.targets, inside
      profiles.deck.tolerances; unit tests pin the rating rule, the sizing rule and the money arithmetic.
Why:  the final deck uses these numbers; the tool must reproduce them by default or say plainly where and why
      it does not. A target we miss is reported, never tuned away: its test is marked xfail with the cause.
How:  pytest; a module fixture runs ewu/deck_screen.run_deck_screen() once (about 3 s). The money arithmetic is
      also checked on the teammate's own implied counts, so a formula slip cannot hide behind simulation noise.
"""
import numpy as np
import pytest
from ewu import config_value, read_config, read_inputs
from ewu import deck, deck_money, deck_screen

CONFIG = read_config()
LIMIT = float(config_value("profiles.deck.overload_limit", CONFIG))
SCENARIOS = ("moderate", "high")
MISSING_ARRAYS = ("most likely the heat pump array and the definition: the teammate's hp_increment.npy is not on this "
                  "machine, ours is derived (0.05 kW per F below 60 F); a heavier heat pump (x1.5) lifts winter share to "
                  "81% and 90% but overloaded to 14% and 41%, and counting any winter hour over gives 82% and 93%")


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


@pytest.mark.parametrize("i", [0, 1])
def test_fixed_without_upgrade_matches_the_deck(result, i):
    assert abs(cell(result, i)["fixed_of_overloaded_pct"] - target("fixed_without_upgrade_pct")[i]) <= tolerance("fixed_pts")


@pytest.mark.parametrize("i", [0, 1])
def test_average_units_match_the_deck(result, i):
    assert abs(cell(result, i)["average_units"] - target("average_units")[i]) <= tolerance("average_units")


@pytest.mark.xfail(reason="winter share 65.7% and 79.9% against 73% and 89%: " + MISSING_ARRAYS, strict=False)
@pytest.mark.parametrize("i", [0, 1])
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


@pytest.mark.xfail(reason="our pooled export fleet, 8.06 kWh usable per unit, shaved day by day, averages 6.4 MW over the "
                   "top 50 hours (9.05 MW in the highest hour); 8.8 MW equals 2,612 homes x 20.16 kWh nameplate spread "
                   "evenly over a 6-hour window, a different energy and averaging rule", strict=False)
def test_export_fleet_peak_cut_matches_the_deck(result):
    assert abs(result["peak"]["export_mw"] - target("peak_cut_export_mw")) <= tolerance("peak_mw")


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
