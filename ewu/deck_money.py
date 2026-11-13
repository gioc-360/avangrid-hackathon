"""Deck money: the final deck's three cost columns and the upgrade-all comparison, scaled to NYSEG.

What: present_value_factor() is the annuity factor; deck_prices() reads every deck price from config and
      derives the counted upgrade cost; price_deck() turns one deck cell's counts into gross, net without
      NYSERDA and Avangrid cost (net of lease and NYSERDA) next to upgrading every overloaded transformer,
      in $ per sample and $M across NYSEG, and the saving against upgrading (deck v3's 58% to 69%).
Why:  the final deck reports these three columns at a 120% limit and a $15,000 upgrade; the tool must print
      the same columns from its own counts so every deck number traces to code.
How:  15 years at 7%: factor (1 - 1.07^-15) / 0.07 = 9.108. A $15,000 upgrade lives 40 years (factor 13.332),
      so 15 of its years count as 15,000 x 9.108 / 13.332. Gross = units x unit price + upgrades x counted
      upgrade; net without NYSERDA subtracts the lease's present value per unit; Avangrid cost also subtracts
      NYSERDA per unit. NYSEG scaling is the teammate's: NYSEG electric customers / 8 homes per transformer
      (prices.nyseg_electric_customers, an assumption flagged in config), times our share of transformers.
"""
from ewu import config_value
from ewu.deck import deck_value

COLUMNS = ("gross", "net_without_nyserda", "avangrid_cost", "upgrade_all")


def present_value_factor(rate, years):
    """Money today per $1 a year for `years` years at `rate`."""
    return years if rate == 0 else (1 - (1 + rate) ** -years) / rate


def deck_prices(config, upgrade_usd=None):
    """Every deck price, the two factors and the upgrade cost counted over the battery's years."""
    rate, years = deck_value("discount_rate", config), deck_value("years", config)
    factor = present_value_factor(rate, years)
    life_factor = present_value_factor(rate, deck_value("upgrade_life_years", config))
    upgrade = deck_value("upgrade_usd", config) if upgrade_usd is None else upgrade_usd
    return {"unit_usd": deck_value("battery_unit_usd", config), "lease_pv_usd": deck_value("lease_usd_unit_yr", config) * factor,
            "nyserda_usd": deck_value("nyserda_usd_unit", config), "factor": round(factor, 3),
            "life_factor": round(life_factor, 3), "upgrade_usd": upgrade, "upgrade_counted_usd": upgrade * factor / life_factor}


def nyseg_scale(cell, config):
    """NYSEG transformers per sample transformer: customers / homes per transformer / transformers simulated."""
    transformers = config_value("prices.nyseg_electric_customers", config) / deck_value("homes_per_transformer", config)
    return transformers / cell["transformers"], transformers


def price_deck(cell, config, upgrade_usd=None):
    """Gross, net without NYSERDA, Avangrid cost and upgrade-all, in $ for the sample and $M across NYSEG."""
    p = deck_prices(config, upgrade_usd)
    units, upgrades = cell["batteries"], cell["upgrades"]
    gross = units * p["unit_usd"] + upgrades * p["upgrade_counted_usd"]
    net = gross - units * p["lease_pv_usd"]
    sample = {"gross": gross, "net_without_nyserda": net, "avangrid_cost": net - units * p["nyserda_usd"],
              "upgrade_all": cell["overloaded"] * p["upgrade_counted_usd"]}
    scale, transformers = nyseg_scale(cell, config)
    return {"sample_usd": sample, "nyseg_musd": {k: round(v * scale / 1e6, 1) for k, v in sample.items()},
            "nyseg_batteries": round(units * scale), "nyseg_transformers": round(transformers), "prices": p,
            "avangrid_share_of_upgrade_all_pct": round(100 * sample["avangrid_cost"] / sample["upgrade_all"], 1)
            if sample["upgrade_all"] else 0.0,
            "saving_vs_upgrade_all_pct": round(100 * (1 - sample["avangrid_cost"] / sample["upgrade_all"]), 2)
            if sample["upgrade_all"] else 0.0}
