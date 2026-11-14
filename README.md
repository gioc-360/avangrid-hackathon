# Electrify Without Upgrade: Avangrid AMI hackathon (Team D4G Cornell 2)

**What:** a planning engine that reads hourly smart-meter data for 33,757 homes and finds the neighborhood
transformers that 2030 EVs and heat pumps will overload, then prices the cheapest fix for each: 1 to 4 leased home
batteries, or an upgrade only where batteries cannot fix it. **Why:** a battery fleet for the summer peak alone does
not pay (benefit to cost 0.85), but a battery placed where it avoids a transformer upgrade does: in the engine's
run, batteries fix 92% to 98% of overloaded transformers at 58% to 69% lower net cost than upgrading every one
(present value, 15 years), and 50% to 73% across loading limits from 100% to 140%. **How:** `bin/ewu screen` reruns
the whole transformer test on the full meter data in about 2 seconds; every number it prints is recorded in
`facts/facts.json`. Transformers are synthetic (3,000 of them, 8 real homes each), because the data has no
meter-to-transformer map; `bin/ewu screen --map` takes a real one.

```
┌────────────────┐   ┌────────────────┐   ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
│ analysis/,     │──▶│ ewu/           │──▶│ facts/         │──▶│ results/       │   │ checks/ tests/ │
│ team_pipeline/ │   │ the engine:    │   │ facts.json:    │   │ aggregate      │   │ every input    │
│ features,      │   │ flag, place,   │   │ every number,  │   │ inputs and     │   │ sourced, every │
│ classes        │   │ upgrade, price │   │ unit, method   │   │ outputs        │   │ number traced  │
└────────────────┘   └────────────────┘   └────────────────┘   └────────────────┘   └────────────────┘
                     inputs: config/ewu.yaml (each with a source or an assumption flag)
```

## The data

The meter data is not in this repo and cannot be. The challenge statement says the data "is for use during and as
part of the Hackathon only. Under no circumstances should the data be shared or utilized outside of scope of this
event." No meter row, customer id or label list is published here. Avangrid's judges already hold the four zips,
the weather file and the label spreadsheet: point `DATA=` at that folder and `make all` rebuilds every result.

What a reader can check without the meter data is in `results/` (written by `analysis/export_results.py`, which
fails if any column looks like a customer or meter id):

| File | What it is |
|---|---|
| `screen_results_by_loading_limit.csv` | overloaded, fixed by batteries, units, gross cost, net cost and Upgrade all, saving, for both 2030 scenarios at limits 100% to 140% |
| `moderate_2030_transformer_actions.csv`, `high_2030_transformer_actions.csv` | all 3,000 synthetic transformers: homes, new EVs and heat pumps, today's peak, rating, worst 2030 hour, action, battery units, cost |
| `moderate_2030_capital_plan.csv`, `high_2030_capital_plan.csv` | the plan priced: gross, net cost without NYSERDA, net cost, Upgrade all |
| `system_load_hourly.csv`, `system_peak_hours.json` | the hourly sum of all 33,757 homes (MW) and its top summer and winter hours |
| `ev_charging_start_hour_shares.csv` | when observed EV charging sessions start (engine input) |
| `heat_pump_added_load_hourly.csv` | the hourly kW one new heat pump adds (engine input) |
| `segment_summary.csv`, `segment_technology_matrix.csv` | the seven segments: size, load shape, weather slopes, peak shares, technology mix |

Every input the engine uses is in `config/ewu.yaml` with its source line or an `assumption` flag
(`checks/config_check.py` fails on a missing one), and every number it computes is in `facts/facts.json` with its
unit, script and method.

## Run it

```
make env                      # Python 3.12 venv from requirements.txt
make all                      # zips -> matrix -> features -> classes -> home types -> batteries -> readout (~4 min)
make prototype                # rebuild every engine output from data/processed
make test                     # tests (about 4 min)
make check                    # problem coverage, source checks, battery recompute, terms
.venv/bin/python -I analysis/export_results.py    # refresh results/
```

Run the engine as `bin/ewu` (`python -I -m ewu` does not work, because `-I` keeps the repo off the import path):

```
bin/ewu --help                                     # list the commands
bin/ewu inventory                                  # Parts 1 and 2: technology, home type, eligible programs per home
bin/ewu screen --scenario moderate --margin 1.15   # Flag, Shift, Place, Upgrade on the full data, live
bin/ewu screen --map meters.csv                    # same, on a real map: meter_id, transformer_id, kva
bin/ewu plan --scenario high --limit 1.2           # transformer action list and capital plan
bin/ewu coldsnap --date 2026-02-07                 # battery hour by hour through the Feb 7-8 cold snap
bin/ewu tophours                                   # MW the battery hosts cut in the system's top 20 and 50 hours
bin/ewu sensitivity                                # every scenario x sizing margin x grouping, priced
bin/ewu robustness                                 # heat pump slope x 1.5 and x 2, flag duration, 3 kVA by charge length
bin/ewu demo                                       # the offline planner dashboard (outputs/demo/ewu_demo.html)
```

## How the engine works

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ meter data   │──▶│ FLAG         │──▶│ PLACE        │──▶│ UPGRADE      │──▶│ PRICE        │
│ + map (opt.) │   │ any hour over│   │ 1 to 4 units │   │ only above 4 │   │ both paths,  │
│ 8 homes each │   │ 1.2 x rating │   │ per worst day│   │ units        │   │ 15 yr at 7%  │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

| Step | Code | What it does |
|---|---|---|
| Ingest | `analysis/ingest.py` | zips to a 33,757 x 8,760 matrix (float32, about 20 s, nothing unzipped to disk) |
| Features | `analysis/features.py` | about 60 features per home; each names the load shape it catches |
| Part 1 | `analysis/classify.py` | rule plus positive-unlabeled model per technology, validated on the label lists |
| Part 2 | `analysis/segment.py` | segments, their peak shares and the winter-flip point |
| Part 3 | `analysis/bess.py` | battery relief, sizing, 3 kVA enablement and value per home |
| Network | `ewu/feeders.py`, `ewu/deck.py` | 3,000 synthetic transformers of 8 real homes, rated at the smallest standard kVA at or above today's peak / 0.85 |
| 2030 load | `ewu/deck.py`, `ewu/adoption.py` | new EV charging (7.2 kW, start hours from observed sessions) and heat pump load per scenario |
| Fix | `ewu/deck.py` | units per transformer = the larger of peak excess / 3.84 kW and excess kWh / 8.06 kWh, worst day; above 4 units, upgrade |
| Money | `ewu/deck_money.py` | $7,000 a unit less lease ($3,006) and NYSERDA ($2,016); an upgrade counted for 15 of its 40 years ($10,248) |
| Added energy | `ewu/deck_energy.py` | 23.5% to 44.8% more kWh on the same wires |

The modules named `deck*.py` hold the battery plan, the profile the team chose as final; the earlier, stricter
profile stays available as `--profile cautious`. The reasoning is in `docs/FINDINGS.md`, the one-page case in
`docs/BUSINESS_CASE.md`, likely code questions with file:line answers in `docs/CODE_QA.md`.

Classes, segments and the 2,610-home battery ranking in the team's final numbers (16,833 central AC homes, seven
segments) come from Kayin Bejide's pipeline in `team_pipeline/` (its README maps every script); its aggregate tables
are `results/segment_*.csv`, and two of its outputs feed the engine through `data/processed`. `analysis/` is the team's first, independent pass at Parts 1 to 3 (readout in
`outputs/readout.txt`); its rules differ (for example 10,961 central AC homes), so its counts are not the final ones.

## The checks (`make check`)

| Check | Fails when |
|---|---|
| brief | a requirement's quote is not on the cited page of the organizers' PDFs (`checks/requirements.yaml`) |
| coverage | a challenge requirement has no computed fact or file behind it |
| source | an outside citation's quote is not on its cited page (`checks/citations.yaml`) |
| config | an engine input has neither a verified source line nor an assumption flag (`checks/config_check.py`, run by `make test`) |
| battery | a second, independent battery model disagrees with the engine (`checks/recompute_battery.py`) |
| terms | the dashboard, the CLI or the docs use two words for one idea (`checks/terms_check.py`) |

The organizers' PDFs, full-text copies of the cited web articles and the teammate's model, which `config/ewu.yaml` cites
line by line are kept outside the repo (event confidentiality and copyright), so `make check` runs on the team's
machines; `checks/citations.yaml` keeps every URL and quote.

## Known data defects

The original `2026 Avangrid Hackathon Data_10001_20000.zip` contains customers 1-10,000 again. The Makefile skips it
and reads the corrected folder `2026 Avangrid Hackathon Data_10001_20000_v2` instead (set `V2=` to its path).
That folder holds 8,585 of the 10,000 promised IDs (`data.source.10001_20000.missing_in_range`).
Homes missing more than 10% of hours are left out, not gap-filled: 33,757 usable of 34,238 with any data.

## Main limitations

Labels are positive-only and unverified (EV and heat-pump lists are ~25% samples). Hourly data hides
15-minute peaks, so the 3 kVA test is optimistic. No transformer map, so the engine groups 8 real homes per
synthetic transformer; a real map replaces them. Battery, lease, NYSERDA and upgrade prices are assumptions until
replaced with NYSEG and RG&E tariffs and avoided-cost values; before the lease and NYSERDA, the battery path costs
more than upgrading in 7 of the 8 rows of `results/screen_results_by_loading_limit.csv` (its gross column).
