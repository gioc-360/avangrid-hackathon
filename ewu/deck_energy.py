"""Added energy on the same wires: how much more electricity the 2030 adopters use, as a share of today's use.

What: for each scenario, the yearly kWh of the new EV charging and heat pump load the battery plan adds to the
      3,000 synthetic transformers, divided by today's yearly kWh of the same homes; recorded as
      ewu.deck.<scenario>.added_energy_pct.
Why:  slide 13 says the plan sells more energy on the same wires; the number must come from the engine's own
      adoption draw, the same one that sets the overloads, not from a hand estimate.
How:  `.venv/bin/python -I ewu/deck_energy.py` (aggregates only; about 2 s).
"""
import sys
from pathlib import Path
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ewu import read_config, read_inputs  # noqa: E402
from ewu import deck  # noqa: E402


def added_energy(inputs, config):
    """{scenario: (added kWh, today's kWh, percent)} over every home on the synthetic transformers."""
    setup = deck.deck_setup(inputs, config)
    out = {}
    for scenario in deck.SCENARIOS:
        _, loads = deck.run_deck(inputs, config, scenario, setup, limits=[1.2])
        added = float(loads["ev"].sum() + loads["hp"].sum())
        today = float(loads["base"].sum())
        out[scenario] = (added, today, 100.0 * added / today)
    return out


def main():
    from analysis.facts import record
    config = read_config()
    for scenario, (added, today, pct) in added_energy(read_inputs(), config).items():
        record(f"ewu.deck.{scenario}.added_energy_pct", round(pct, 2), "% more kWh a year than today, same homes",
               "new EV charging plus heat pump kWh over today's kWh on the 3,000 synthetic transformers, battery plan draw")
        print(f"{scenario}: +{pct:.1f}% ({added / 1e6:.2f} GWh added on {today / 1e6:.2f} GWh)")


if __name__ == "__main__":
    main()
