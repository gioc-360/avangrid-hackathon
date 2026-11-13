# EWU engine tech specs

The engine is plain Python 3.12 on a laptop: it holds a year of meter data for 33,757 homes in a 1.18 GB matrix, screens 3,000 transformers in 2.4 s with 0.91 GB of peak memory, and passes 132 tests and make check in 21 s. Avangrid deploys it as a scheduled batch job on its own data platform, with no cloud and no customer data leaving, and their transformer map is one flag.

Every number here was measured by deck/engine_specs.py on this machine and written to facts/facts.json under specs.*, or was recorded by the engine itself under the key named. Rerun: `.venv/bin/python -I deck/engine_specs.py --heavy`, then deck/engine_figures.py (outputs/deck/tech_specs.png) and `python3 -I deck/engine_slides.py`. Timings were taken while other jobs ran on the machine; the load average is recorded beside each.

## At a glance

| Spec | Measured | Fact key |
|---|---|---|
| Language | Python 3.12.0 | specs.python_version |
| Key packages | numpy 2.5.4, pandas 3.1.1, polars 2.1.0, pyarrow 26.0.1, scipy 1.18.1, scikit-learn 1.9.1, PyYAML 6.0.3, openpyxl 3.1.5, matplotlib 3.11.2, python-pptx 1.0.2, pytest 9.2.0 | specs.package.* |
| Engine code | 3,262 lines in 24 ewu modules, none over 200 | specs.code.engine.* |
| Pipeline code | 1,013 lines in 8 analysis modules | specs.code.analysis.* |
| Checks and tests | 1,539 lines in 10 check files; 1,750 lines in test files | specs.code.checks.*, specs.code.tests.* |
| Tests | 132 collected by pytest | specs.tests_collected |
| Check scripts | 9 (checks/*.py, less the battery_model helper) | specs.check_scripts |
| make check | exit 0 in 21 s | specs.make_check.* |
| CLI | bin/ewu, 10 commands | specs.cli_commands |
| Machine | MacBook Pro, Apple M2 Max, 12 cores, 64 GB | specs.machine.* |

## Data sizes

| Item | Size | Fact key |
|---|---|---|
| Hourly readings ingested | 298,032,553 | data.rows_read |
| Customer ids promised by the data dictionary | 35,725 | data.customers_promised |
| Homes used (at least 90% of hours present) | 33,757 | data.customers_usable |
| Raw matrix data/processed/load.npy, every promised id | 1.25 GB | scale.matrix_gb |
| Working matrix load_present.npy | 33,757 homes x 8,760 hours, float32, 1,182,845,280 bytes (1.18 GB); 1,182,845,408 bytes on disk | specs.matrix.* |
| Full read of the working matrix | 0.18 s (warm disk cache); the engine memory-maps it instead | specs.matrix.full_load_seconds |
| Per-home inventory outputs/private/inventory.parquet | 33,757 rows x 59 columns, 8 program columns | specs.output.inventory.* |
| Battery candidate list outputs/bess_candidates.csv | 5,341 homes | specs.output.bess_candidates.rows |
| Viewer page outputs/demo/ewu_demo.html | 2,000,320 bytes, one offline file | specs.output.demo_page_bytes |

## Runtimes

| Run | Seconds | Fact key |
|---|---|---|
| Ingest the zips into the matrix | 16.8 | scale.ingest_seconds |
| Segment homes | 1.7 | scale.segment_seconds |
| Battery sizing (analysis/bess.py) | 25.7 | scale.bess_seconds |
| Stress grid, every scenario, grouping, seed and margin | 19.2 | ewu.stress.grid_seconds |
| Attribution and shift grid | 139.8 | ewu.attribution.grid_seconds |
| Fit score | 40.8 | ewu.fitscore.seconds |
| Cold snap test `bin/ewu coldsnap` | 61.9 | ewu.coldsnap.seconds |
| Top hours `bin/ewu tophours` | 44.1 | ewu.tophours.seconds |
| Sensitivity grid and pricing `bin/ewu sensitivity` | 173.2 | ewu.sensitivity.seconds |
| Robustness `bin/ewu robustness` | 420.1 | ewu.robustness.seconds |
| Charger headroom test | 32.1 | ewu.headroom.seconds |
| Live screen `bin/ewu screen`, measured here (load average 5.7) | 2.4 | specs.screen.measured_seconds |
| Live screen as the engine last recorded it | 2.3 | ewu.screen.moderate.random.margin_115.seconds |
| Action lists `bin/ewu plan` | 4.9 | ewu.plan.seconds |
| `make check` | 21 | specs.make_check.seconds |

The screen limit is 60 s (config checks.screen_seconds_max).

## Memory

`/usr/bin/time -l bin/ewu screen` (defaults, facts write switched off so the measurement rewrites nothing): peak memory footprint 913,132,184 bytes (0.91 GB), the process's own memory; maximum resident set 3,500,032,000 bytes (3.5 GB), which also counts the file pages of the memory-mapped matrix the run touches. Keys specs.screen.peak_footprint_* and specs.screen.max_resident_*.

## Command line

`bin/ewu --help` lists 10 subcommands: inventory, screen, network, coldsnap, sensitivity, tophours, robustness, case, demo, plan.

| Command | What it does |
|---|---|
| `inventory` | equipment, segment and eligible programs for every home |
| `screen [--scenario] [--margin] [--grouping] [--map CSV]` | Flag, Shift, Protect, Upgrade for one scenario and sizing, live |
| `network` | the screen's synthetic network, transformer by transformer, for the page |
| `coldsnap [--date]` | battery duration test through the cold snap |
| `sensitivity` | the ladder and its cost over scenarios, sizing margins and groupings |
| `tophours` | MW the fit-score batteries cut in the system's top 20 and 50 hours |
| `robustness` | heat pump slope variants, flag durations, the 3 kVA test by charge length |
| `case` | writes docs/BUSINESS_CASE.md with every number filled from facts |
| `demo [--no-open]` | builds the offline viewer page |
| `plan [--scenario] [--margin] [--grouping] [--seed] [--private] [--showcase]` | action lists: transformers and capital plan; real home lists only with `--private`, simulated ones with `--showcase` |

## Input data contract

| Input | Format | Columns and units | Rules |
|---|---|---|---|
| Hourly meter data | CSVs in zips or folders, read by analysis/ingest.py | CUSTOMER_NUMBER (integer id), usage_date (date), hour_ending (hour of the day), hourly_kwh (kWh in the hour, read as average kW), is_complete_hour (0 or 1) | hour 0 is 2025-09-01 hour ending 1; rows outside the year are dropped; duplicate rows for one customer and hour are summed; missing hours stay empty; homes with under 90% of hours are left out, the rest have gaps filled from neighboring hours |
| Weather | workbook Weather Data_Avangrid_Hackathon .xlsx, one sheet, stored as data/processed/weather.parquet | date, time, temp (F), humidity (%), windspeed | one row per hour of the same year |
| Customer labels | workbook EV_Heat Pump_Solar PV Customers.xlsx, tabs EV Customers, HP Customers, PV Customers | CUSTOMER_NUMBER | validation only: the organizers' partial lists of owners |
| Transformer map (optional) | CSV passed with `bin/ewu screen --map` | meter_id (text, the CUSTOMER_NUMBER), transformer_id (text), kva (number) | a meter under two transformers is refused; meters not in the data are dropped; groups may differ in size; rating still follows today's peak x the sizing margin |
| Settings | config/ewu.yaml | each input is {value, unit, source} or {value, unit, assumption: true, basis} | checks/config_check.py opens every source; sections: scenarios, transformer, battery, shift, prices, demo, network, programs, robustness, checks |

## Output data contract

The action lists come from `bin/ewu plan` (ewu/plan.py, ewu/plan_output.py). Column meanings, units and sources are in outputs/showcase/README.md, which the command writes. Every CSV starts with one `#` line saying what it is.

| File | Level | Columns |
|---|---|---|
| outputs/plan/transformer_actions.csv, 3,000 rows | transformer (8-home sums, no home named) | transformer_id, feeder_id, homes, new_evs_2030, new_heat_pumps_2030, today_peak_kw, rating_kw, limit_kw, worst_2030_kw, worst_2030_hour, over_limit, hours_over, main_driver, action, battery_hosts, units_per_host, batteries_needed, est_cost_usd, priority |
| outputs/plan/capital_plan.csv | whole sample, placeholder prices | option, what, transformers_upgraded, batteries, ev_homes_enrolled, pv_usd_low, pv_usd_mid, pv_usd_high, share_of_upgrade_all_pct_low, share_of_upgrade_all_pct_mid, share_of_upgrade_all_pct_high, prices |
| battery_hosts.csv (real: outputs/private/plan with `--private`; simulated: outputs/showcase) | home | transformer_id, rank, home_id, fit_score, kw_cut_top_hours, units |
| program_targets.csv (same two places) | home | home_id, transformer_id, segment, programs, reason, priority |
| outputs/private/inventory.parquet (`bin/ewu inventory`) | home, private | CUSTOMER_NUMBER, segment, annual_kwh, peak_kw, battery tier and units, p_ev, p_heat_pump, one is_* flag and one confidence_* word per equipment class, monthly kWh, one eligible_* column per program |
| facts/facts.json | aggregate | key: {value, unit, script, method}; per-home and per-transformer values go to the gitignored outputs/private/facts_private.json |
| docs/BUSINESS_CASE.md, outputs/demo/ewu_demo.html | aggregate | the business case and the viewer, both filled only from facts |

## Deployment path

A scheduled batch job on Avangrid's own data platform; the cadence is our proposal, for example after each month's meter data lands:

1. `make env` once: a Python 3.12 virtual environment from requirements.txt.
2. `make data features model`: zips to the matrix, features, classes, segments and battery sizing.
3. `bin/ewu plan --private`: the transformer and home action lists, written inside their platform.
4. `make check` and `pytest tests/`: the job fails loudly if any number stops tracing.

It runs offline: no web service, no cloud, no customer data leaves the machine it runs on. What changes with their transformer map is one flag, `--map map.csv`, which `bin/ewu screen` takes today through ewu/feeders.py `load_map()`. Two gaps before production: `bin/ewu plan` does not take `--map` yet, and weather.parquet is built by a step that is not in the repo (no tracked script writes it).
