# Morning report: EWU prototype build

The prototype works: every build milestone passed, the live screen runs in seconds, and judge scores rose in round two. What failed: judges still read the old teammate one-pager, every hardest question attacked its numbers, and round two's per-judge scores were not saved. On code, say every number is written by code, and a check fails the build if one is typed by hand.

Do first: make sure the deck carries the numbers in docs/BUSINESS_CASE.md, not runs/business_case_team_v2.txt.

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Flag         │──▶│ Shift        │──▶│ Protect      │──▶│ Upgrade      │
│ 26.18% over  │   │ 20.57% fixed │   │ 5.23% clear  │   │ 0.42% left   │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
  moderate 2030, transformers rated at today's group peak x 1.15, share of all transformers
```

## Milestones

| Id | Result | What it means |
|---|---|---|
| SCOPE | PASS | Plan section "Scoped" is the build contract |
| M0 | PASS | Every config input sourced or flagged as an assumption; planted bad inputs caught |
| INV | PASS | Built inside M6; inventory of 33,757 homes, 69.07% eligible for a program; no log line of its own |
| M1 | PASS | Baseline stress on synthetic transformers, 5 seeds, every sizing margin |
| M2 | PASS | Overload hours split into base, EV and heat pump; timer and staggered charging |
| M3 | PASS | Battery dispatch hour by hour through Feb 7-8 |
| M3 recompute | NOT RUN | The independent rerun of cold snap and battery counts never happened; the M8 review did not cover them |
| M4 | PASS | Fit-score hosts beat random hosts in every cell |
| M5 | PASS | Equal-life economics, 16 grid cells, headline as a range |
| M6 | PASS | Live `bin/ewu screen`, offline 4-step page, every shown number bound to a fact |
| M7 | PASS | Demo script and code questions, every file and line reference resolves |
| J1 | PASS | Judge round 1 recorded; generated business case and top-hours command added |
| M8 | PASS | Failed once (record missing), passed on retry; 10 number checks match |
| J2 | FAIL | Averages and hardest questions saved, but per-judge scores were not, so `judge_rounds_check.py --round 2` fails |

## Headline numbers (moderate 2030, rating = today's group peak x 1.15, unless stated)

| Claim | Number | Range |
|---|---|---|
| Transformers over the limit, EV charging unmanaged | 26.18% | 3.74% to 42.84% over sizing margins; high case 54.77% (14.38% to 71.71%) |
| Same, counting only 3 or more hours over a year | 16.41% | 37.31% of flags are under 3 hours |
| Fixed by staggered EV charging | 78.56% of flagged | high 59.43%; heat pump slope x 1.5 gives 60.7%, x 2 gives 46.1% |
| Heat pump the larger cause | 4.57% of overload hours | both loads needed 76.0%; slope x 1.5 gives 26.67% |
| Overload from heat pumps alone, no EV fix reaches | 1.97% of transformers | high 11.73% |
| Full ladder cost, share of upgrading every flag | 51.92% | 30.8% to 151.19% over cells and price cases |
| Shift then upgrade, no batteries | 43.47% | 28.72% to 102.97%; cheaper than the ladder at placeholder prices |
| Battery price where Protect pays | below $7,730 a unit | placeholder $9,000 to $13,000; $6,715 on a deferral basis |
| Fit-score battery, kW cut in system top 20 hours | 1.71 kW | random hosts 1.17 kW |
| NYSEG scaling (labeled assumption) | $436.9M upgrade-all | ladder $226.8M, shift then upgrade $189.9M |

## Cold snap verdict for batteries

Batteries hold the cold snap but do not pay at placeholder prices. On Feb 7-8 with staggered charging, 2.70% of transformers go over the limit, for a median 3.0 hours and 3.02 kWh. One host home with two units (20.16 kWh) clears 89.88% of them and two hosts clear 92.84%; 9.63% of one-host batteries hit empty. In the high case 13.66% go over, one host clears 75.11%, two hosts 84.09%, and 23.38% of one-host batteries run empty. So Protect is a targeted rung for the cold snap, heat-pump-only transformers and the 3 kVA rule, worth funding where the installed price lands below the tie.

## Judge scores by round

| Round | Used judges, average | Held-out judge | A1 anchor | Used gap to anchor |
|---|---|---|---|---|
| 1 | 3.24 | 3.2 | 4.14 | -0.9 |
| 2 | 3.4 | 3.45 | 4.14 | -0.74 |

Round 2 moved the used judges up 0.16 and the held-out judge up 0.25. Code examiner: 9 of 10 in the latest run; runs/review_round.json records 7 of 10 on first read and 10 of 10 after the M8 fixes.

## The 3 hardest judge questions, with answers

**"Your one-pager says 9.8% and $27M; your tool says 26% and $226.8M against $436.9M. Which numbers do you stand behind?"**
Say: "The tool's. At today's peak x 1.15, 26.18% of transformers flag in the moderate case, pooled over five seeds; the live run is one seed and shows 26.00%. We give it as a range, 3.74% to 42.84%, because ratings stay a guess until we get your meter-to-transformer map. The 9.8% came from an earlier simulation and is retired; FINDINGS lists every difference."

**"If batteries lose to the upgrade at your own prices, why fund them instead of managed charging and upgrading the rest?"**
Say: "It is a managed-charging program first. Shifting then upgrading costs 43.47% of upgrading every flag, the full ladder 51.92%, so shifting is the money. Batteries go only where shifting cannot reach: transformers that overload from heat pumps alone, homes that need room under the 3 kVA rule, and the cold snap, where one host clears 89.88%. We put them on fit-score hosts, which cut 1.71 kW each in your top 20 hours against 1.17 kW for random hosts, and only below $7,730 a unit installed."

**"Under which New York mechanism does Avangrid earn anything on the capital a home battery avoids?"**
Say: "We do not know, so we took the return-on-avoided-capital claim out. How a leased home battery that defers a transformer is treated under New York's non-wires benefit-cost test is our third ask to you. The program does not depend on it: the shift rung saves money with no battery at all."

Also ready: if asked why one hour over counts as an overload, say a rule of 3 or more hours flags 16.41% instead of 26.18%, and Avangrid's own duration rule is an ask.

## How to run the demo

```
bin/ewu demo                                       # build and open the offline page, no network
bin/ewu screen --scenario moderate --margin 1.15   # the live run on the full meter data
bin/ewu case                                       # rewrite docs/BUSINESS_CASE.md from facts
```
Follow docs/DEMO_SCRIPT.md row by row. If the terminal hangs, show docs/demo/cli_output.txt. The page shows one real home and one transformer, so keep it on this laptop. `make prototype` rebuilds everything from data/processed.

## Log
- 2026-11-12 23:17 ET | SCOPE | PASS | 12 milestones with exit checks, 8 ordered cuts; plan section "Scoped" is the build contract
- 2026-11-12 23:25 ET | M0 | PASS | config_check: 73 inputs, 71 with a verified source, 32 flagged as assumptions, 0 problems; selftest caught 7 of 7 planted cases; 17 tests pass; gates green
- 2026-11-12 23:32 ET | M1 | PASS | baseline stress on 3,000 synthetic transformers x 5 seeds: overloaded at today's peak x 1.15 is 26.18% moderate, 54.77% high (random grouping; teammate 9.8%, 29.8%); range 3.74% to 71.71% over margins and modes; widest seed gap 1.37 pts vs 1.5 allowed; 7 stress tests pass; gates green
- 2026-11-12 23:46 ET | M2 | PASS | moderate 2030 at peak x 1.15: heat pumps run in 90.52% of overload hours but lead only 4.57%; staggering fixes 78.56% of overloaded transformers (26.18% to 5.65%), timer nets 24.28%; heat-pump-only floor 1.97% moderate, 11.73% high; 9 attribution tests pass; every number in FINDINGS.md traced, 0 untraced; gates green
- 2026-11-12 23:57 ET | M3 | PASS | Feb 7-8 cold snap, moderate 2030 staggered at peak x 1.15: 2.70% of transformers over the limit in the window, median 3.0 h and 3.02 kWh over; one host (2 units, 20.16 kWh) clears 89.88%, two hosts 92.84%; high staggered 13.66% flagged, one host clears 75.11%; 10 dispatch tests pass; gates green; independent 3-number recompute still to run (no agent spawn from this session)
- 2026-11-13 00:08 ET | M4 | PASS | 40 system top hours on 9 days incl. Feb 7 and Jul 2; on transformers still overloaded with staggered charging (5.65% moderate, 22.35% high), 1 fit-score host with 1 unit clears 66.75 per 100 batteries vs 43.75 random (high 52.03 vs 37.62), fit beats random in all 8 host/unit cells; M3 worst-hour rule clears slightly more (69.46) but its hosts cut less at system peak (1.72 vs 1.89 kW); 8 fit score tests, 51 total pass; gates green
- 2026-11-13 00:21 ET | M5 | PASS | 16 grid cells priced at equal life (battery 15 yr, transformer 30 yr, 7%): moderate at peak x 1.15 the ladder costs 51.92% of upgrading every flagged transformer, range 30.8% to 151.19% over cells and price cases; shift-then-upgrade 43.47% (28.72% to 102.97%); batteries cost more than the upgrade they defer at placeholder prices ($1,720/yr vs $1,209/yr mid), tie at $7,730 per unit; NYSEG scaling $436.9M upgrade-all vs $226.8M ladder (present value); 11 economics tests, 62 total pass; gates green
- 2026-11-13 00:41 ET | M6 | PASS | live bin/ewu screen on the full data in 3.3 s (limit 60 s): moderate at peak x 1.15, seed 0, flag 26.00%, shift 20.50%, protect 4.97% with 213 batteries, upgrade 0.60%; make prototype clean; offline 4-step page renders in 16 states with 1,072 numbers each bound to a fact, 0 problems, 4 step screenshots in outputs/private/demo_shots; INV built here too (33,757 homes, 69.07% eligible for a program); report_ewu.py cut per plan S5; 76 tests pass; gates green
- 2026-11-13 01:17 ET | J1 | PASS | round 1 (9 judges, Talent Development held out): average 3.23 vs A1 anchor 4.14 (8 used judges 3.24, held-out 3.2); gaps value -1.56, analytics -0.38, presentation -1.11, innovation 0.08; 3 fixes: docs/BUSINESS_CASE.md generated from facts (119 numbers traced, 0 untraced), bin/ewu tophours (fit-score hosts cut 1.71 kW per battery in the top 20 system hours vs 1.17 random, moderate; Jul 2 holds 8 of the top 20, Feb 7's peak hour ranks 123 so the annual top 50 are all summer), README 'Run the EWU tool' and plain-vs-skills table removed from the readout; 86 tests pass; demo check 0 problems after rebuilding the page for two re-recorded run timings; gates green
- 2026-11-13 01:29 ET | M7 | PASS | docs/DEMO_SCRIPT.md (12-row three-minute click path, each row a click, one sentence and the objection it answers), docs/CODE_QA.md (15 questions, scope minimum 10 in config checks.qa_questions), checks/qa_refs.py: 71 file:line references resolve with their anchor text, selftest caught 7 of 7 planted faults; numbers traced: DEMO_SCRIPT 32, CODE_QA 44, FINDINGS 330, 0 untraced; docs/ARCHITECTURE.md not built (cut in plan S5, its diagram is the README one); 88 tests pass; gates green
- 2026-11-13 02:01 ET | fix-M8 | FAIL | exit check fails only because runs/review_round.json (10 number checks, 10 examiner answers) was never written; the 4 review findings are fixed and recomputed: heat pump slope x1.5 staggering fixes 60.7% (x2 46.1%) vs 78.56%, heat pump leads 26.67% (x2 50.29%) of overload hours; flag at 3+ hours 16.41% vs 26.18% (37.31% of flags under 3 h); 3 kVA one unit 40.6% with the measured 3.78 h charge vs 57.2% with the assumed 2 h; battery counts behind the 51.92% ladder labeled not independently rerun; 99 tests pass, demo check 0 problems, make check and compare green; not committed
- 2026-11-13 02:46 ET | fix-M8 | PASS | review recorded in runs/review_round.json: 10 of 10 number checks match after fixes (first pass 7 of 10), examiner 10 of 10 after fixes (first read 7 of 10); EV-led 95.43% was argmax ties: EV strictly larger 19.42%, both loads needed 76.0%, heat pump 4.57% of overload hours; EV and heat pump adopters share one order (97.91% of new heat pump homes also get an EV), drawn apart 25.28% overload and staggering fixes 83.83% vs 78.56%; slope, flag-duration and 3 kVA fixes kept; battery counts still not independently rerun; 103 tests pass, demo check 0 problems, gates green
- 2026-11-13 02:57 ET | MORNING | PASS | report top written for Gio; judge round 2 used judges 3.4 (round 1 3.24), held-out 3.45 (round 1 3.2), anchor 4.14; code examiner 9 of 10; J2 check FAIL: per-judge scores were not saved, only averages and the 9 hardest questions; M3 independent battery recompute still not run
