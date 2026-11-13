"""Economics tests (M5): no typed price, fair equal-life math, bounded deferral, every grid cell in facts.

What: ewu/economics.py holds no number that could be a price, and doubling every price in config doubles every
      cost; equal lives at a zero discount rate give the plain cost ratio, for one asset and for a whole ladder;
      an upgrade's present value over its own life is its price; deferral value is never negative, never above
      the upgrade cost and zero at a zero rate, in the formula and in the recorded facts; every one of the 16
      grid cells has its ladder and its money in facts; the grid agrees with M1, M2 and M4 where they overlap;
      a one-seed rerun keeps the ladder's books balanced; the headline is a range that FINDINGS.md states.
Why:  the plan's M5 exit check, plus the questions a finance judge would ask before trusting the cost line.
How:  ast scan of the module's numbers; hand-made counts and prices for the arithmetic; facts/facts.json for the
      recorded grid; one small rerun (seed 0, random grouping) for the ladder identities.
"""
import ast, copy, json
import pytest
from ewu import ROOT, config_value, read_config, read_inputs
from ewu import economics, sensitivity, stress
from ewu.feeders import MODES

CONFIG = read_config()
FACTS = {k: v["value"] for k, v in json.loads((ROOT / "facts/facts.json").read_text()).items()}
MARGINS = [stress.margin_label(m) for m in config_value("transformer.sizing_margins", CONFIG)]
CELLS = [f"{s}.{g}.{m}" for s in stress.SCENARIOS for g in MODES for m in MARGINS]
BASE = f"{config_value('demo.scenario', CONFIG)}.random.{stress.margin_label(config_value('transformer.base_margin', CONFIG))}"
HAND_COUNTS = {"flagged": 40, "protect_set": 9, "protected": 7, "batteries": 11, "upgrade_left": 2, "ev_homes_enrolled": 55}


def test_economics_types_no_price():
    """Only rounding digits, 0, 1, and the unit steps 100 (percent) and a million ($M) may appear as numbers."""
    tree = ast.parse((ROOT / "ewu/economics.py").read_text())
    numbers = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
               and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)}
    assert numbers <= {0, 1, 2, 100, 1e6}, numbers


def test_doubling_every_price_doubles_every_cost():
    doubled = copy.deepcopy(CONFIG)
    for name, item in doubled["prices"].items():
        if name.endswith("_usd") or name.endswith("_usd_yr"):
            item["value"] *= 2
    for case in economics.PRICE_CASES:
        one = economics.cost_the_ladder(HAND_COUNTS, economics.prices_for_case(case, CONFIG))
        two = economics.cost_the_ladder(HAND_COUNTS, economics.prices_for_case(case, doubled))
        for name in economics.STRATEGIES:
            assert two["yearly_usd"][name] == pytest.approx(2 * one["yearly_usd"][name])
            assert two["share_of_upgrade_all_pct"][name] == pytest.approx(one["share_of_upgrade_all_pct"][name], abs=0.01)


def test_equal_lives_at_zero_rate_give_the_plain_cost_ratio():
    for battery, upgrade, life in ((9000, 15000, 30), (13000, 10000, 15), (1, 3, 7)):
        ratio = economics.equal_life_annual_cost(battery, 0, life) / economics.equal_life_annual_cost(upgrade, 0, life)
        assert ratio == pytest.approx(battery / upgrade)
    prices = economics.prices_for_case("mid", CONFIG, rate=0)
    prices["battery_life"] = prices["transformer_life"]
    life, c = prices["transformer_life"], HAND_COUNTS
    plain_ladder = (c["ev_homes_enrolled"] * (prices["enroll_usd"] + prices["fee_usd_yr"] * life)
                    + c["batteries"] * prices["battery_unit_usd"] + c["upgrade_left"] * prices["upgrade_usd"])
    plain_all = c["flagged"] * prices["upgrade_usd"]
    got = economics.cost_the_ladder(c, prices)["share_of_upgrade_all_pct"]["ladder"]
    assert got == pytest.approx(round(100 * plain_ladder / plain_all, 2))


def test_an_upgrade_over_its_own_life_is_worth_its_price():
    for rate in (0, config_value("prices.discount_rate", CONFIG), 0.25):
        prices = economics.prices_for_case("mid", CONFIG, rate=rate)
        yearly = economics.equal_life_annual_cost(prices["upgrade_usd"], rate, prices["transformer_life"])
        assert economics.present_value_over_years(yearly, rate, prices["transformer_life"]) == pytest.approx(prices["upgrade_usd"])


def test_deferral_value_never_exceeds_the_upgrade_cost():
    upgrade = config_value("prices.upgrade_cost_usd", CONFIG)
    for rate in (0, 0.01, config_value("prices.discount_rate", CONFIG), 0.2, 1.0):
        for years in range(0, 61):
            value = economics.deferral_value(upgrade, rate, years)
            assert 0 <= value <= upgrade
    assert economics.deferral_value(upgrade, 0, config_value("battery.life_years", CONFIG)) == 0
    for case in economics.PRICE_CASES:
        recorded = FACTS[f"ewu.economics.battery_vs_upgrade.{case}.deferral_value_usd"]
        assert 0 < recorded <= economics.prices_for_case(case, CONFIG)["upgrade_usd"]


def test_every_grid_cell_is_in_facts():
    assert len(CELLS) == 16 and FACTS["ewu.sensitivity.cells"] == 16
    missing = []
    for cell in CELLS:
        for name in ("flagged_pct", "shift_fixed_pct", "protect_set_pct", "protected_pct", "upgrade_left_pct",
                     "batteries_per_protected", "ev_homes_per_flagged"):
            missing += [] if f"ewu.sensitivity.{cell}.{name}" in FACTS else [f"{cell}.{name}"]
        for case in economics.PRICE_CASES:
            for rate in ("discounted", "zero_rate"):
                for strategy in ("ladder", "shift_then_upgrade"):
                    key = f"ewu.economics.{cell}.{case}.{rate}.{strategy}_share_pct"
                    missing += [] if key in FACTS else [key]
            for strategy in economics.STRATEGIES:
                key = f"ewu.economics.{cell}.{case}.nyseg_{strategy}_musd"
                missing += [] if key in FACTS else [key]
    assert missing == []


def test_grid_agrees_with_earlier_milestones():
    for cell in CELLS:
        flagged = FACTS[f"ewu.sensitivity.{cell}.flagged_pct"]
        assert flagged == pytest.approx(FACTS[f"ewu.stress.{cell}.overloaded_pct"], abs=0.011)
        assert FACTS[f"ewu.sensitivity.{cell}.protect_set_pct"] == pytest.approx(
            FACTS[f"ewu.shift.{cell}.staggered.overloaded_pct"], abs=0.011)
        shares = [FACTS[f"ewu.sensitivity.{cell}.{n}"] for n in ("shift_fixed_pct", "protected_pct", "upgrade_left_pct")]
        assert sum(shares) >= flagged - 0.03
    for scenario in stress.SCENARIOS:
        cell = BASE.replace(BASE.split(".")[0], scenario, 1)
        assert FACTS[f"ewu.sensitivity.{cell}.protected_of_set_pct"] == FACTS[
            f"ewu.fitscore.{scenario}.staggered.{cell.split('.')[-1]}.fit_score.cheapest.cleared_pct"]


def test_overloads_never_rise_with_the_margin():
    for s in stress.SCENARIOS:
        for g in MODES:
            for name in ("flagged_pct", "protect_set_pct"):
                values = [FACTS[f"ewu.sensitivity.{s}.{g}.{m}.{name}"] for m in MARGINS]
                assert values == sorted(values, reverse=True), (s, g, name)


def test_nyseg_line_is_the_flagged_share_times_the_upgrade_price():
    scale = economics.nyseg_transformers(CONFIG)
    assert FACTS["ewu.economics.nyseg_transformers"] == round(scale)
    upgrade = config_value("prices.upgrade_cost_usd", CONFIG)
    expected = FACTS[f"ewu.sensitivity.{BASE}.flagged_pct"] / 100 * scale * upgrade / 1e6
    assert FACTS[f"ewu.economics.{BASE}.mid.nyseg_upgrade_all_musd"] == pytest.approx(expected, abs=0.1)


@pytest.fixture(scope="module")
def one_seed_ladder():
    return sensitivity.run_sensitivity(read_inputs(), CONFIG, [0], groupings=("random",))


def test_ladder_books_balance_on_a_rerun(one_seed_ladder):
    options = sensitivity.options_from_config(CONFIG)
    most = max(h * u for h, u in options)
    for (scenario, grouping, margin, seed), c in one_seed_ladder.items():
        assert c["flagged"] - c["shift_fixed"] + c["new_from_stagger"] == c["protect_set"]
        assert c["protected"] + c["upgrade_left"] == c["protect_set"]
        assert c["protected"] <= c["batteries"] <= most * c["protected"]
        assert c["flagged"] <= c["transformers"]


def test_headline_is_a_range_and_findings_state_it():
    findings = (ROOT / "docs/FINDINGS.md").read_text()
    for strategy in ("ladder", "shift_then_upgrade"):
        low, base, high = (FACTS[f"ewu.economics.headline.{strategy}_share_pct.{end}"] for end in ("low", "base", "high"))
        assert low <= base <= high and low < high
        assert f"from {low}% to {high}%" in findings
    assert f"{FACTS['ewu.economics.headline.ladder_share_pct.base']}%" in findings
