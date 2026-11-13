# Morning report: EWU prototype build

The top summary (section 8 of docs/PROTOTYPE_PLAN.md) is written at the hard stop. Until then, read the log.

## Log
- 2026-11-12 23:17 ET | SCOPE | PASS | 12 milestones with exit checks, 8 ordered cuts; plan section "Scoped" is the build contract
- 2026-11-12 23:25 ET | M0 | PASS | config_check: 73 inputs, 71 with a verified source, 32 flagged as assumptions, 0 problems; selftest caught 7 of 7 planted cases; 17 tests pass; gates green
- 2026-11-12 23:32 ET | M1 | PASS | baseline stress on 3,000 synthetic transformers x 5 seeds: overloaded at today's peak x 1.15 is 26.18% moderate, 54.77% high (random grouping; teammate 9.8%, 29.8%); range 3.74% to 71.71% over margins and modes; widest seed gap 1.37 pts vs 1.5 allowed; 7 stress tests pass; gates green
- 2026-11-12 23:46 ET | M2 | PASS | moderate 2030 at peak x 1.15: heat pumps run in 90.52% of overload hours but lead only 4.57%; staggering fixes 78.56% of overloaded transformers (26.18% to 5.65%), timer nets 24.28%; heat-pump-only floor 1.97% moderate, 11.73% high; 9 attribution tests pass; every number in FINDINGS.md traced, 0 untraced; gates green
- 2026-11-12 23:57 ET | M3 | PASS | Feb 7-8 cold snap, moderate 2030 staggered at peak x 1.15: 2.70% of transformers over the limit in the window, median 3.0 h and 3.02 kWh over; one host (2 units, 20.16 kWh) clears 89.88%, two hosts 92.84%; high staggered 13.66% flagged, one host clears 75.11%; 10 dispatch tests pass; gates green; independent 3-number recompute still to run (no agent spawn from this session)
- 2026-11-13 00:08 ET | M4 | PASS | 40 system top hours on 9 days incl. Feb 7 and Jul 2; on transformers still overloaded with staggered charging (5.65% moderate, 22.35% high), 1 fit-score host with 1 unit clears 66.75 per 100 batteries vs 43.75 random (high 52.03 vs 37.62), fit beats random in all 8 host/unit cells; M3 worst-hour rule clears slightly more (69.46) but its hosts cut less at system peak (1.72 vs 1.89 kW); 8 fit score tests, 51 total pass; gates green
