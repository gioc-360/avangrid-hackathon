# EWU engine architecture

The product is the engine: the ewu Python package and its bin/ewu command line. It reads Avangrid's hourly meter data, weather and prices, finds the transformers 2030 electrification overloads, picks the cheapest fix for each and writes action lists, all offline on one machine. The demo page only views what the engine already wrote, and a trust layer checks every number before anyone sees it.

Deck figure: outputs/deck/architecture.png (1920x1080, drawn from facts by deck/engine_figures.py). Measured specs: docs/TECH_SPECS.md.

```
┌────────────────────┐
│ Read inputs        │
└─────────┬──────────┘
          ▼
┌────────────────────┐   facts     ┌────────────────────┐
│ Profile every home │────────────▶│                    │
└─────────┬──────────┘             │                    │
          ▼                        │                    │
┌────────────────────┐   facts     │                    │
│ Add 2030 load      │────────────▶│ Check every number │
└─────────┬──────────┘             │                    │
          ▼                        │                    │
┌────────────────────┐   facts     │                    │
│ Run the steps      │────────────▶│                    │
└─────────┬──────────┘             │                    │
          ▼                        │                    │
┌────────────────────┐   facts     │                    │
│ Ship action lists  │────────────▶│                    │
└────────────────────┘             └────────────────────┘
Figure 1  EWU engine, one offline batch run
```

## The five steps

| Step | Code | Reads | Writes |
|---|---|---|---|
| Read inputs | analysis/ingest.py | hourly meter CSVs (zips or folders), weather workbook, organizers' EV, heat pump and solar customer lists, config/ewu.yaml, optional meter-to-transformer map (`--map`) | data/processed/load.npy, one row per customer, one column per hour |
| Profile every home | analysis/features.py, classify.py, segment.py, bess.py, ewu/inventory.py | load matrix and weather | load_present.npy (33,757 homes x 8,760 hours, 1.18 GB), technology flags, segment, battery tier, program eligibility per home |
| Add 2030 load | ewu/feeders.py, adoption.py, stress.py | homes, flags, weather, config scenarios | kW by transformer by hour in three parts (base, EV, heat pump) for 3,000 synthetic transformers of 8 homes, or the real map's groups |
| Run the steps | ewu/shift.py, fitscore.py, dispatch.py, coldsnap.py, economics.py, sensitivity.py, screen.py | the 2030 loading | each transformer's step: within limit, Flag, Shift (managed charging), Place (batteries in fit-score homes), Upgrade; priced on equal life |
| Ship action lists | ewu/plan.py, plan_output.py (`bin/ewu plan`), business_case.py, demo_page.py | the step states and prices | transformer_actions.csv, capital_plan.csv, battery_hosts.csv, program_targets.csv, docs/BUSINESS_CASE.md, outputs/demo/ewu_demo.html |

Side analyses run on the same loading: ewu/attribution.py (which load causes each overload hour), tophours.py (MW cut in the system's top hours), headroom.py (the service test for a new charger), robustness.py (soft inputs moved), network.py (the page's network view).

## Trust layer

| Check | What it proves |
|---|---|
| facts/facts.json via analysis/facts.py `record()` | every number has one home, written by the code that made it; per-home values go to the gitignored outputs/private |
| checks/trace_numbers.py | every number in a doc equals a fact or a config input |
| checks/demo_check.py | every number on the viewer page equals its stored value, and the page loads nothing from outside |
| checks/recompute_battery.py | separate code rebuilds the battery and cold snap facts and must land on the same values |
| checks/config_check.py | every config input is found at its cited source or is labeled an assumption |
| pytest tests/ | module behavior, house rules, privacy of outputs |
| `make check` | runs the problem-coverage check and the battery recompute in one command |

## What Avangrid's map changes

One flag. `bin/ewu screen --map map.csv` (columns meter_id, transformer_id, kva) swaps the synthetic transformers for real ones through ewu/feeders.py `load_map()`; nothing else in the engine changes, and groups of different sizes run as separate batches. Two limits today: ratings still follow today's peak times the sizing margin, because a kVA rating from the utility's records needs a power factor nobody has given us, and `bin/ewu plan` does not take `--map` yet.

## Privacy

Everything runs on one machine with no network calls. Real home-level rows stay in outputs/private (gitignored); `bin/ewu plan --private` is the only path that writes real home lists. The shareable home lists in outputs/showcase are simulated from segment statistics. The figures and slides in outputs/deck hold no customer data.

## Run it

```
make env        # .venv with requirements.txt
make data features model    # zips to load matrix, features, classes, segments
bin/ewu screen  # the steps live on the full data
bin/ewu plan    # action lists
make check      # trust layer
```
