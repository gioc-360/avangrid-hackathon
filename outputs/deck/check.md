# Independent check: engine plan, showcase, architecture and specs

Checked 2026-11-13, 12:36 to 12:50 ET, on commit 0178252 (branch prototype). The engine runs were made in a scratch copy of the repo (data symlinked), so they rewrote nothing here; pytest and make check ran in the repo itself, and facts/facts.json had the same md5 before and after.

Verdict: pass on the plan counts, the showcase privacy, the figures, pytest and make check. One must-fix: the code-size specs were measured before the plan files were committed, so the engine line and module counts are 14 to 17 percent low.

## 1. Plan counts against the screen

| Item | bin/ewu screen | transformer_actions.csv (recounted) | Match |
|---|---|---|---|
| Flag (over the limit, unmanaged) | 780 | over_limit true: 780 | exact |
| Shift | 615 | action shift: 615 | exact |
| Protect | 149 | action protect: 149 | exact |
| Upgrade | 18 | action upgrade: 18 | exact |
| Batteries | 213 | batteries_needed sum: 213 | exact |
| Ladder share of upgrade-all, mid | 51.79% | capital_plan.csv ladder mid: 51.79 | exact |

Run: moderate 2030, x1.15, random grouping, seed 0, 3,000 rows. Shift + Protect + Upgrade = 782, two more than Flag; those are the 2 transformers that staggering pushes over (the screen's 0.07%), shown as over_limit false with protect or upgrade, as the README says. The est_cost_usd column sums to $6,059,676 against $6,059,668 in capital_plan.csv (rounding). The rerun's CSVs, simulated homes and README were identical to the local ones.

## 2. Showcase privacy

My own snippet against data/processed/segmented.parquet and outputs/private/inventory.parquet:

| Test | Result |
|---|---|
| Every home_id in simulated_homes, battery_hosts, program_targets is SIM- plus 5 digits | yes, 24,000 unique |
| Any id string equal to a real CUSTOMER_NUMBER | 0 |
| Any (segment, annual kWh, peak kW) equal to a real home | 0 |
| Any (annual kWh, peak kW) pair equal to a real home, segment ignored | 2 of 24,000 (different segments) |
| Single annual kWh value equal to some real home's | 19,782 of 24,000 (expected: integers in the same range) |
| Homes per transformer | 8 on every transformer; 149 protected transformers carry hosts |
| README says simulated | yes, first line and every home-level table; each CSV starts with the simulated note |

Doc fix made: the README said the guard "redraws any value that happens to match one (47 values redrawn)". It keys on whole rows, and single values do coincide, so ewu/plan_readme_template.md and outputs/showcase/README.md now say which fields the guard compares and that 47 rows were redrawn.

## 3. Architecture and specs

Files: every path and module named in docs/ARCHITECTURE.md, docs/TECH_SPECS.md and both figures exists (analysis/ingest, features, classify, segment, bess; ewu/inventory, feeders, adoption, stress, shift, fitscore, dispatch, coldsnap, economics, sensitivity, screen, plan, plan_output; checks/trace_numbers, demo_check, recompute_battery; config/ewu.yaml; facts/facts.json). The only paths not on disk are outputs/private/plan (written only with --private, not run) and /usr/bin/time and .venv/bin/python (tools). No em dashes in either doc.

| Spec | Stated | Rerun here | Within 10% |
|---|---|---|---|
| Live screen time | 2.4 s | 2.3 s (engine's own clock; 3.05 s wall with start-up), load average about 9 | yes |
| Screen peak memory | 913,132,184 bytes | 909,396,632 bytes | yes |
| Load matrix | 33,757 x 8,760, float32, 1,182,845,280 bytes | same | exact |
| Battery candidates | 5,341 rows | 5,341 | exact |
| Inventory | 33,757 x 59, 8 program columns | same | exact |
| Tests collected | 132 | 132 passed | exact |
| make check | exit 0 in 21 s | exit 0 in 23.5 s (load average 10 to 15) | 12% slower, load |
| bin/ewu plan | 4.9 s | 2.7 s | faster; recorded under load |
| Engine code | 2,799 lines in 21 ewu modules | 3,262 lines in 24 tracked ewu modules | NO, 16.5% low |
| Tests code | 1,626 lines in 16 files | 1,750 lines in 17 files | 7.6%, but stale |
| Viewer page | 2,000,320 bytes | 2,000,335 (the other run is editing it) | yes |

Why the code counts are low: deck/engine_specs.py counts `git ls-files`, and it ran before ewu/plan.py (170), ewu/plan_output.py (147), ewu/showcase.py (146) and tests/test_plan.py were committed; 2,799 + 463 = 3,262. specs.code.deck.files also reads 0 while 3 deck scripts are now tracked.

Figures: architecture.png and tech_specs.png are 1920x1080, every label readable, nothing cut off; smallest SVG text is 24 px. In the pptx, slide 1 places the figure at 0.92 scale with the top 13.9% (its own title) cropped, so its smallest text lands near 22 px at 1920 wide; slide 2's table is 13 pt (26 px) and its footer 11 pt (22 px). Both slides render cleanly, no overflow; Downloads copy equals outputs/deck/EWU_engine_slides.pptx.

## 4. Tests

`pytest tests/` (the other run's uncommitted tests/test_labels.py left out): 132 passed in 178 s. `make check`: brief 31/31, coverage 31/31, source 26/26, battery recompute selftest and full run pass, exit 0. tests/test_plan.py and tests/test_house_rules.py pass again after the README fix (16 passed).

## Must-fix

1. docs/TECH_SPECS.md, outputs/deck/tech_specs.png, the pptx slide 2: engine code reads 2,799 lines in 21 modules and tests 1,626 in 16 files; the tracked tree is 3,262 in 24 and 1,750 in 17. Fix: `.venv/bin/python -I deck/engine_specs.py` (light run, no --heavy), then deck/engine_figures.py and deck/engine_slides.py, update the two rows in TECH_SPECS.md, and copy the pptx to Downloads under a new name (EWU_engine_slides_b.pptx), never over the existing one.

## Worth knowing, not blocking

- Guard key: two simulated homes share a real home's (annual kWh, peak kW) pair under a different segment. Keying the guard on the pair without segment would close it.
- SIM-00001's digits equal real customer number 1 (and so on); no values are carried over, but a reader stripping the prefix lands on a real id.
- The fact ewu.plan.showcase.redrawn has the unit "simulated values redrawn"; it counts rows.
