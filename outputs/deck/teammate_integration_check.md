# Independent check: teammate arrays and the deck replica

Checked 2026-11-13, 14:53 to 15:05 ET, on commit 37839c7 (branch prototype). Read and run only; nothing in ewu/ was called by the recompute, and the teammate's folder was read in place, never written.

Verdict: pass. My own code, written from her ewu_sim_bo2.py and not from ewu/deck_replica.py, gives the moderate case at 120% exactly as the tool records it and as her result files report it. The arrays in data/processed are byte for byte hers. No customer-level file of hers is tracked, copied or in git history. make check, pytest and demo_check are green, with the two expected failures the integration step named.

## 1. Moderate case at 120%, recomputed three ways

My script (scratch, run with python -I) reads data/processed/load.npy, the two arrays in data/processed, and two columns of her customer_classification.csv held in memory. It follows her rules: groups from a generator seeded 11, adoption seeded 5 with one coin per eligible home, missing hours set to the home's mean, rating = smallest standard kVA at or above peak / 0.85 (capped at 167), units = max of daily peak excess / 3.84 kW and daily excess energy / 8.064 kWh, more than 4 units = upgrade, winter driven = more than half the hours over the limit in November to March. Unlike the tool, it draws each day's EV start hour one call at a time as her loop does, so the tool's vector draw is tested, not assumed.

| Measure | My recompute | Tool fact (ewu.deck_replica.moderate.limit_120) | Her ewu_bo_econ.json / ewu_bo2_econ.json | Her ewu_results.json | Match |
|---|---|---|---|---|---|
| Overloaded | 295 of 3,000 = 9.8333% | 295, 9.83% | 9.8 | 9.8 | exact |
| Fixed without upgrade | 290 = 98.3051% of overloaded | 290, 98.31% | 98.3 (bo2) | not reported | exact |
| Upgrades (more than 4 units) | 5 | 5 | 1.7% of overloaded (bo2), 0.2% of all (bo) | not reported | exact |
| Batteries on fixed transformers | 423 | 423 | 15686 across NYSEG | not reported | exact |
| Average units per fixed transformer | 1.4586 | 1.46 | 1.46 | not reported | exact |
| Winter driven, her definition | 72.8814% of overloaded | 72.88% | 72.9 (bo) | 72.9 | exact |
| New EV homes / new heat pump homes | 4,673 / 3,053 | 4,673 / 3,053 | not reported | not reported | exact |

Her NYSEG battery count, 15686, is the 423 scaled to NYSEG (teammate.audit.rerun.moderate.batteries_nyseg = 15686.25). Her per-transformer `units` column sizes for managed charging and does not give 1.46; the deck's 1.46 comes from her unmanaged u120 column, which is what both the tool and my script use, consistent with managed charging off in the spec.

## 2. Arrays

| File | sha256, data/processed | sha256, teammate folder | In config/ewu.yaml |
|---|---|---|---|
| ev_start_pmf.npy | `7fbff91f...49bd2` | same | ev_start_pmf_sha256, same |
| hp_increment.npy | `2a63625a...db5b4` | same | hp_increment_sha256, same |

Full digests were compared, not the shortened forms shown.

## 3. Customer-level files

| Test | Result |
|---|---|
| git ls-files for customer_classification, customer_segments, battery_candidates, classification.csv | none |
| Those names anywhere in git history, all branches | none |
| sha256 of her three CSVs against every file in the repo (outside .venv and .git) | 0 copies |
| Her CSV header or row pattern in tracked files (git grep) | none |
| Files with those names on disk in the repo | outputs/customer_segments.csv only: our own analysis/segment.py output (different columns), gitignored by outputs/*.csv |
| Her folder modified | no: every file's change time is the download time |

The replica reads customer_classification.csv in place from the configured folder (profiles.deck.teammate_folder), keeps two boolean columns in memory and writes nothing from it.

## 4. Suite

| Run | Result |
|---|---|
| make check | exit 0; brief, coverage and source all pass; recompute_battery 10 of 10 reproduce |
| pytest tests/ | all pass except 2 expected failures |
| Expected failures | high-case fixed (our tiers move her run below 94%) and moderate winter share (tiers plus the random draw); both carry measured causes in the test |
| checks/demo_check.py | 0 problems |

## 5. Notes, not defects

- The tool's replica draws all EV start hours of a home in one vector call; her code draws one per day. My one-at-a-time version gives the same totals on every field above, so the docstring claim in ewu/deck_replica.py holds on this run.
- Her bo2 upgrade figure is a share of overloaded transformers and her bo figure is a share of all transformers; both describe the same 5 upgrades.
- No doc typos were found that needed a fix in this step.
