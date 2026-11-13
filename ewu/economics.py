"""Economics: what the Flag, Shift, Protect, Upgrade ladder costs next to upgrading every flagged transformer.

What: capital_recovery_factor() and equal_life_annual_cost() put a 15-year battery and a 30-year transformer on
      one yearly footing; present_value_over_years() turns a yearly cost back into money today over the
      transformer's life; deferral_value() is what pushing an upgrade back by the battery's life is worth;
      prices_for_case() reads every price from config/ewu.yaml for the low, mid or high case; cost_the_ladder()
      prices one grid cell's pooled counts; battery_against_upgrade() compares one cleared transformer's
      batteries with its upgrade; nyseg_transformers() is the one labeled scaling line.
Why:  judges said a battery does not "avoid" an upgrade, it lives half as long (plan objection 5). Equal-life
      cost and deferral value are the two fair ways to compare them, and the range across the grid and the
      price cases is the honest headline. This file types no price: every dollar comes from config.
How:  equal-life annual cost = capital x r / (1 - (1 + r)^-life), or capital / life at r = 0, so a battery is
      replaced at the end of its life at the same price. Present value over the transformer life multiplies
      that by the annuity factor, so an upgrade's present value is exactly its price. Deferral value =
      upgrade x (1 - (1 + r)^-years), which is 0 at r = 0 and never above the upgrade's price. Shift costs the
      one-time enrollment, spread over the transformer life, plus the yearly fee for every enrolled EV home.
      The mid price case takes the teammate's midpoint upgrade and the middle of the battery range.
"""
import numpy as np
from ewu import config_value

PRICE_CASES = ("low", "mid", "high")
STRATEGIES = ("upgrade_all", "shift_then_upgrade", "ladder")


def capital_recovery_factor(rate, years):
    """Share of a capital cost paid each year so that `years` equal payments repay it at `rate`."""
    if rate == 0:
        return 1 / years
    return rate / (1 - (1 + rate) ** -years)


def equal_life_annual_cost(capital, rate, life_years):
    """Yearly cost of owning `capital` forever, replaced every `life_years` at the same price."""
    return capital * capital_recovery_factor(rate, life_years)


def present_value_over_years(yearly, rate, years):
    """Money today that equals `yearly` paid at the end of each of `years` years."""
    return yearly / capital_recovery_factor(rate, years)


def deferral_value(upgrade_cost, rate, years):
    """What pushing an upgrade back by `years` is worth today: never negative, never above the upgrade cost."""
    return upgrade_cost * (1 - (1 + rate) ** -max(years, 0))


def prices_for_case(case, config, rate=None):
    """Every price and life one cost calculation needs, read from config for the low, mid or high case."""
    battery = [config_value(f"prices.battery_unit_cost_{end}_usd", config) for end in ("low", "high")]
    upgrade = {"low": config_value("prices.upgrade_cost_low_usd", config),
               "mid": config_value("prices.upgrade_cost_usd", config),
               "high": config_value("prices.upgrade_cost_high_usd", config)}
    return {"upgrade_usd": upgrade[case],
            "battery_unit_usd": {"low": battery[0], "mid": float(np.mean(battery)), "high": battery[-1]}[case],
            "enroll_usd": config_value("prices.managed_charging_enroll_usd", config),
            "fee_usd_yr": config_value("prices.managed_charging_usd_yr", config),
            "battery_life": config_value("battery.life_years", config),
            "transformer_life": config_value("prices.transformer_life_years", config),
            "rate": config_value("prices.discount_rate", config) if rate is None else rate}


def cost_the_ladder(counts, prices):
    """Equal-life yearly cost of each strategy for one cell's pooled counts, and its present value over the
    transformer life. Strategies: upgrade every flagged transformer; shift, then upgrade what is still over;
    shift, protect with batteries, upgrade what batteries leave (the ladder)."""
    rate, life = prices["rate"], prices["transformer_life"]
    upgrade_yr = equal_life_annual_cost(prices["upgrade_usd"], rate, life)
    battery_yr = equal_life_annual_cost(prices["battery_unit_usd"], rate, prices["battery_life"])
    shift_yr = counts["ev_homes_enrolled"] * (equal_life_annual_cost(prices["enroll_usd"], rate, life) + prices["fee_usd_yr"])
    yearly = {"upgrade_all": counts["flagged"] * upgrade_yr,
              "shift_then_upgrade": shift_yr + counts["protect_set"] * upgrade_yr,
              "ladder": shift_yr + counts["batteries"] * battery_yr + counts["upgrade_left"] * upgrade_yr}
    parts = {"shift": shift_yr, "protect": counts["batteries"] * battery_yr, "upgrade": counts["upgrade_left"] * upgrade_yr}
    present = {name: present_value_over_years(v, rate, life) for name, v in yearly.items()}
    whole = yearly["upgrade_all"]
    return {"yearly_usd": yearly, "present_usd": present, "ladder_parts_yearly_usd": parts,
            "share_of_upgrade_all_pct": {name: round(100 * v / whole, 2) if whole else 0.0 for name, v in yearly.items()}}


def battery_against_upgrade(counts, prices):
    """For one cleared transformer: batteries' equal-life yearly cost against the upgrade's, the unit price at
    which they tie, and the deferral framing (what a battery-life delay of the upgrade is worth)."""
    if not counts["protected"]:
        return {}
    per = counts["batteries"] / counts["protected"]
    rate, life, battery_life = prices["rate"], prices["transformer_life"], prices["battery_life"]
    upgrade_yr = equal_life_annual_cost(prices["upgrade_usd"], rate, life)
    defer = deferral_value(prices["upgrade_usd"], rate, battery_life)
    return {"batteries_per_cleared": round(per, 2),
            "battery_capital_usd": round(per * prices["battery_unit_usd"]),
            "battery_yearly_usd": round(equal_life_annual_cost(per * prices["battery_unit_usd"], rate, battery_life)),
            "upgrade_yearly_usd": round(upgrade_yr),
            "tie_unit_usd_equal_life": round(upgrade_yr / (per * capital_recovery_factor(rate, battery_life))),
            "deferral_value_usd": round(defer),
            "tie_unit_usd_deferral": round(defer / per)}


def nyseg_transformers(config):
    """Labeled scaling line: NYSEG electric customers over homes per transformer, as if every customer were a
    home like our sample (the teammate's assumption, flagged in config)."""
    return config_value("prices.nyseg_electric_customers", config) / config_value("transformer.homes_per_transformer", config)


def price_every_cell(pooled, config):
    """{(scenario, grouping, margin): {(case, rate name): costs}} at the config rate and at zero."""
    rates = {"discounted": config_value("prices.discount_rate", config), "zero_rate": 0}
    return {cell: {(case, name): cost_the_ladder(counts, prices_for_case(case, config, rate))
                   for case in PRICE_CASES for name, rate in rates.items()}
            for cell, counts in pooled.items()}


def headline_range(priced, base_cell, strategy="ladder"):
    """A strategy's cost as a share of upgrading every flagged transformer: the base cell at mid prices, and
    the lowest and highest over every grid cell and price case, at the config discount rate."""
    shares = [costs[(case, "discounted")]["share_of_upgrade_all_pct"][strategy]
              for costs in priced.values() for case in PRICE_CASES]
    return {"base": priced[base_cell][("mid", "discounted")]["share_of_upgrade_all_pct"][strategy],
            "low": min(shares), "high": max(shares)}


def record_economics(pooled, priced, config):
    """Every cell's money at the config rate and at zero, the base-cell battery comparison, the headline range
    and the NYSEG scaling line, to facts/facts.json."""
    from analysis.facts import record
    from ewu.stress import margin_label
    base_cell = (config_value("demo.scenario", config), "random", config_value("transformer.base_margin", config))
    scale = nyseg_transformers(config)
    for cell, by_case in priced.items():
        key = f"ewu.economics.{cell[0]}.{cell[1]}.{margin_label(cell[2])}"
        for (case, rate_name), costs in by_case.items():
            how = f"{case} prices, {rate_name.replace('_', ' ')}, equal-life yearly cost; pooled seeds"
            for name, share in costs["share_of_upgrade_all_pct"].items():
                if name != "upgrade_all":
                    record(f"{key}.{case}.{rate_name}.{name}_share_pct", share, "% of upgrading every flagged transformer", how)
            if rate_name == "discounted":
                for name, present in costs["present_usd"].items():
                    musd = round(present / pooled[cell]["transformers"] * scale / 1e6, 1)
                    record(f"{key}.{case}.nyseg_{name}_musd", musd, "$M present value over the transformer life",
                           f"scaled to {scale:.0f} NYSEG transformers (customers / homes per transformer, assumption)")
    ladder = priced[base_cell]
    for case in PRICE_CASES:
        for name, value in battery_against_upgrade(pooled[base_cell], prices_for_case(case, config)).items():
            unit = "batteries" if name == "batteries_per_cleared" else "$ per year" if "yearly" in name else "$"
            record(f"ewu.economics.battery_vs_upgrade.{case}.{name}", value, unit,
                   f"base cell {base_cell}, per transformer batteries clear, config discount rate")
    for strategy in STRATEGIES[1:]:
        for end, share in headline_range(priced, base_cell, strategy).items():
            record(f"ewu.economics.headline.{strategy}_share_pct.{end}", share, "% of upgrading every flagged transformer",
                   "base cell at mid prices; low and high over every grid cell and price case, config discount rate")
    mid = ladder[("mid", "discounted")]["present_usd"]
    saved = (mid["upgrade_all"] - mid["ladder"]) / pooled[base_cell]["transformers"] * scale / 1e6
    record("ewu.economics.headline.nyseg_saved_musd", round(saved, 1), "$M present value",
           "base cell, mid prices, scaled to NYSEG (labeled assumption)")
    record("ewu.economics.nyseg_transformers", round(scale), "transformers", "NYSEG customers / homes per transformer")
