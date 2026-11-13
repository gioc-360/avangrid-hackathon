# Audit: the EWU prototype before the video

Read-only audit, 2026-11-13, branch prototype at 20a365f plus uncommitted work from other agents (Makefile,
tests/test_house_rules.py, docs/BUSINESS_CASE.md, checks/recompute_battery.py and others). Battery numbers are out
of scope here (another agent reruns them). Every non-battery headline number tested reproduces with independent
code. The real problems are privacy (the demo page and two tracked figures hold single real homes) and two
unlabeled placeholders. Two stale code references and the missing media ignore rules were fixed in the working
tree by another agent while this audit ran.

## Checks

| Check | Result | Verbatim failures |
|---|---|---|
| `make check` | PASS, exit 0 | brief 31/31, coverage 31/31, source 26/26 |
| `pytest -q tests/` | PASS, 103 passed in 430.92 s | none (see qa_refs: it would now fail, the edits landed mid-run) |
| `checks/demo_check.py` | PASS | 16 rendered states, 1072 bound numbers checked, live screen 9.1 s (limit 60 s), 0 problems |
| `checks/trace_numbers.py docs/*.md` | FAIL, exit 1 | see below |
| `checks/qa_refs.py docs/CODE_QA.md` | FAIL at 06:50, PASS at 06:56 after another agent updated the refs | see below |

trace_numbers (BUSINESS_CASE 162 traced, CODE_QA 54, DEMO_SCRIPT 32, FINDINGS 447, all 0 untraced):
```
FAIL  docs/COMPANY_BRIEF.md:15  2,548,000  traces to no fact or config input
FAIL  docs/COMPANY_BRIEF.md:15  3,099,000  traces to no fact or config input
FAIL  docs/COMPANY_BRIEF.md:15  4,157,000  traces to no fact or config input
FAIL  docs/MORNING_REPORT.md:92      1,072  traces to no fact or config input
FAIL  docs/PROTOTYPE_PLAN.md:147      3.57  traces to no fact or config input
```
These three docs are internal and not in `make check`; keep them out of the video and deck.

qa_refs:
```
FAIL  Q13. Where does customer data go?: `tests/test_house_rules.py:81 def test_private_outputs_are_ignored_by_git` anchor 'def test_private_outputs_are_ignored_by_git' is not on those lines
FAIL  Q15. Random groups change with the seed. How stable are the results?: `Makefile:33 prototype:` anchor 'prototype:' is not on those lines
qa_refs: docs/CODE_QA.md: 15 questions, 72 references resolve, 2 problems
```
Cause: the uncommitted battery-recompute edits added lines to Makefile (now `prototype:` at 35) and
tests/test_house_rules.py (now line 82). tests/test_qa_refs.py runs the same check, so `make test` goes red once
those edits stay.

Side effect: demo_check rewrites tracked files on every run (facts.json `ewu.cli.screen_seconds` and
`ewu.screen.moderate.random.margin_115.seconds`, docs/demo/cli_output.txt timing line). This audit restored the two
values and the line to HEAD afterwards, so it leaves no edit behind. Whoever commits after a demo_check run will
carry new timings; both versions trace.

## Numbers tested

Independent rerun: scratch script rebuilt base, EV, staggered EV and heat pump loading with its own loops (only the
seeded draws for groups, adopters and sessions were reused so seeds match), then all metrics, 5 seeds, moderate,
random grouping, rating = today's peak x 1.15.

| # | Number | Verdict | Evidence |
|---|---|---|---|
| 1 | 26.18% flagged, moderate (live seed 0: 26.00%) | HOLDS. Rerun 26.18% pooled; seed 0 26.0, seeds 26.0 / 26.67 / 25.5 / 27.23 / 25.5. Mean of seed shares, equal seed sizes, so pooling is fair. Load has 0 NaN, 0 negatives; weather is local time (coldest hour of day 6, warmest 16), so no UTC shift | ewu/stress.py:74-80, ewu/stress.py:105, docs/BUSINESS_CASE.md:6 |
| 2 | 78.56% of flagged fixed by staggering; 20.57% of all fixed; 26.18% to 5.65% | HOLDS. Rerun 78.56%, 20.57%, 5.65%. But the rung table does not add up: 20.57 + 5.23 + 0.42 = 26.22, not 26.18, because 0.04% of transformers are newly overloaded by staggering and sit in Protect and Upgrade. Not an error; add one clause | ewu/sensitivity.py:85-88, docs/BUSINESS_CASE.md:83-86, docs/DEMO_SCRIPT.md:25 |
| 3 | 16.41% over at least 3 hours; 37.31% of flags under 3 hours | HOLDS. Rerun 16.41% and 37.31%; 26.18 x (1 - 0.3731) = 16.41 | ewu/robustness.py:103-112, docs/BUSINESS_CASE.md:18,22-23 |
| 4 | Heat pumps run in 90.52% of overload hours | HOLDS. Rerun 90.52% | ewu/attribution.py:70, docs/BUSINESS_CASE.md:31 |
| 5 | 95.38% of overload hours stay under with no new EV; 76.0% need both loads | HOLDS. Rerun 95.38% and 76.0%. Base can never cross alone (limit = 1.2 x 1.15 x base peak), so base share is always 0 and ties only fall between EV and heat pump, as documented | ewu/attribution.py:61,71, docs/BUSINESS_CASE.md:32-33 |
| 6 | 1.97% of transformers overload from heat pumps alone | HOLDS. Rerun 1.97% (flagged and base + heat pump over in some hour) | ewu/attribution.py:60,69, docs/BUSINESS_CASE.md:49 |
| 7 | Shift then upgrade 43.47% of upgrade-all | HOLDS by hand: flagged 3,927 and still-over 847.5 of 15,000 runs; upgrade $15,000 x CRF(7%, 30) = $1,209/yr; shift = 2.7 x 3,927 enrolled x ($150 x CRF + $86) = $1.04M/yr; (1.04M + 847.5 x 1,209) / (3,927 x 1,209) = 43.5%. Caveat: rung 2 says "EV homes on flagged transformers", but the model staggers and prices only new 2030 EVs; existing EVs (2.07% of homes) stay unmanaged in the base | ewu/economics.py:63-78, ewu/sensitivity.py:89, docs/BUSINESS_CASE.md:8-9,84 |
| 8 | NYSEG $436.9M upgrade-all, $226.8M ladder, $189.9M shift then upgrade | HOLDS: 890,000 / 8 = 111,250 transformers x 26.18% x $15,000 = $436.9M; x 51.92% = $226.8M; x 43.47% = $189.9M. Labeled assumption in the doc | ewu/economics.py:99-102,138, docs/BUSINESS_CASE.md:101-103 |
| 9 | 69.07% of 33,757 homes qualify for a program | HOLDS (rerun 69.07%), but 65.65 points of it is "has AC, so smart-thermostat DR" (is_ac 69.06% of homes). A judge will call it padded; say the AC share out loud or lead with the narrower programs | ewu/inventory.py:52-53, config/ewu.yaml:153, docs/DEMO_SCRIPT.md:23 |
| 10 | Same-segment grouping 32.65% flagged, 1.55% upgrade | HOLDS (facts match; same code path as #1, not rerun separately) | ewu/feeders.py:32-33, docs/DEMO_SCRIPT.md:27 |

Probed and found clean: kW vs kWh (hourly kWh = mean kW; EV 7.2 kW for whole hours; energy conserved when shifted),
seed pooling, double counting in the ladder (shift_fixed excludes the Protect set), the 0-hour index (hour 0 =
2025-09-01 00:00 to 01:00 in both load and weather). One quirk, low impact: 22.6% of the 20,940 measured sessions
start 00:00 to 05:59, and staggered and timer modes move them to 23:00 of that same calendar day, about a day
later, not to that night (ewu/shift.py:50,79).

## Unsourced claims

Business case claims that are not computed numbers, checked against sources/ and config sources:

| Where | Claim | Status |
|---|---|---|
| docs/BUSINESS_CASE.md:24 | "$15,000 (mid)" per upgrade | Config labels it an assumption (teammate midpoint, Eversource page not verified, config/ewu.yaml:90-91); the doc does not say placeholder. MUST_FIX 3 |
| docs/BUSINESS_CASE.md:95 | "7% rate" | Config: placeholder, no source (config/ewu.yaml:114-115); doc does not say so. MUST_FIX 3 |
| docs/BUSINESS_CASE.md:21 | Flag = any hour above 1.2 x rating | Teammate threshold, assumption in config (config/ewu.yaml:48-49); doc calls the duration an ask but not the 1.2 |
| docs/BUSINESS_CASE.md:36-37 | Timer backfires "because cars start together on the coldest nights" | Mechanism not measured; the numbers show the backfire, not the cause. Cut "on the coldest nights" or measure it |
| docs/BUSINESS_CASE.md:101 | 890,000 NYSEG customers | Sourced, labeled assumption; config basis says "2018 count" but the quote is "As of December 2016" (docs/COMPANY_BRIEF.md:16). All customer classes, not homes |
| docs/BUSINESS_CASE.md:84 | Rung 2 defaults "EV homes" to staggered charging | Program design, not modeled for existing EVs (see #7) |
| docs/BUSINESS_CASE.md:51 | A home may add about 3 kVA without a service study | Sourced, pdf:challenge:3 |
| docs/BUSINESS_CASE.md:97 | Lease payments, NYSERDA incentive, capacity value left out | Labeled "none verified" |
| docs/BUSINESS_CASE.md:111-112 | New York non-wires benefit-cost test | Framed as an ask, not a claim |

Everything else in the doc is a computed number (traced, 162 of 162) or a labeled method.

## Privacy

| Where | What it exposes | In the video? |
|---|---|---|
| outputs/demo/ewu_demo.html step 1 (ewu/inventory.py:73 pick_demo_homes, ewu/demo_page.py:20-23) | Six real homes, the median-kWh home of each segment: monthly kWh, summer and winter day kW curves, peak kW, flags, probabilities | Must not be recorded as is. MUST_FIX 1 |
| outputs/demo/ewu_demo.html cold snap step (ewu/coldsnap.py:165-167) | One example transformer (8 real homes, allowed as an aggregate) and the host battery's state of charge, which follows one host home's own load | Use fleet SOC facts instead. MUST_FIX 1 |
| runs/plain/fig6_dispatch_example.png, tracked and on origin/prototype | One real home's 24-hour load on 2026-07-02 | MUST_FIX 2 |
| runs/plain/fig2_signatures.png, tracked and on origin/prototype | Six real homes' full-year hourly heatmaps | MUST_FIX 2 |
| outputs/bess_candidates.csv, customer_classes.csv, customer_segments.csv | One row per CUSTOMER_NUMBER, in outputs/ root not outputs/private/ | Gitignored, not tracked; never open on screen while recording |
| outputs/private/demo_shots/step1.png to step4.png | Screenshots of the page with the real homes | Gitignored; do not reuse for the video |
| outputs/video/, outputs/*.mp4, *.wav, *.m4a, *.pptx | Not yet created; ignored as of 06:56 ET (.gitignore:25-30, uncommitted) | Commit the rule |
| facts/facts.json, docs/demo/cli_output.txt, outputs/readout.txt, outputs/comparison.json | Aggregates only; no customer number, no per-home key | Clean |
| `git ls-files` data check | No csv, parquet, npy or zip tracked; tracked json are facts and judge runs; tracked png are the 11 bench figures under runs/plain and runs/skills (the 9 others are aggregates) | Clean except the two above |

## Open questions a utility exec will ask that the tool cannot answer yet

1. "What happens on my real transformers?" Groups are 8 random homes; real secondaries vary in size, nameplate
   kVA and geography, and adoption clusters by street. `--map` exists but has never run on a real map.
2. "Will customers actually stay enrolled, and what does it cost us?" Shift assumes every new EV home on a flagged
   transformer follows the stagger, with no opt-out, at teammate prices ($150 once, $86 a year) never verified.
3. "Which transformers fail first, and in what year?" One 2030 snapshot; no adoption path by year, so no capital
   schedule or deferral timing.
4. "Is a one-hour 120% overload even a failure?" No thermal loss-of-life model, no ambient derate, no 15-minute
   peaks; the flag is a threshold count, and the 3-hour rule already cuts it from 26.18% to 16.41%.
5. "Can we own a battery in a customer's home and earn on it, and at what installed price?" Regulatory treatment
   and the real installed price are asks; at placeholder prices the battery loses to the upgrade.

## MUST_FIX

Resolved in the working tree during this audit by another agent, not yet committed: the two stale CODE_QA
references (docs/CODE_QA.md:168 now `tests/test_house_rules.py:82`, :189 now `Makefile:35`; qa_refs rerun at
06:56 ET: 74 references resolve, 0 problems) and the media rules (.gitignore:25-30 now ignore `outputs/video/` and
mp4, wav, m4a, pptx under outputs; `git check-ignore` confirms). Commit both with the edits that moved the lines.

1. FIXED 2026-11-13. Step 1: six real homes (the median-kWh home of each segment, private facts
   ewu.demo.home_0 to home_5) -> six Composite homes, public facts ewu.demo.composite_0 to composite_5, each the
   average of every home in its segment (105 to 15,335 homes; e.g. EV home 533 homes, 17,134 kWh a year, average
   highest hour 12.74 kW; baseline 15,335 homes, 4,647 kWh), labeled "Composite ... not a real customer" on the
   page. Cold snap: host charge line (private ewu.coldsnap.example.hosts_N.soc_kwh) -> fleet median and bottom-tenth
   charge (ewu.coldsnap.moderate.staggered.margin_115.hosts_N.soc_median_pct_by_hour, soc_p10_pct_by_hour); the
   example transformer keeps its summed load before and after batteries. soc_kwh is no longer written and old
   ewu.demo.* private rows are dropped (analysis/facts.py forget()). Tests: tests/test_inventory.py
   test_composite_homes_are_segment_averages_never_one_home, test_demo_page_carries_no_single_home_and_no_host_charge.
   Original finding: ewu/inventory.py:73 and ewu/demo_page.py:20-27: the demo page shows six real homes and one host's battery
   charge. Fix for the video: replace the picker homes with a per-segment "Composite" typical home built from
   segment means and labeled "Composite"; on the cold snap step show the 8-home transformer load and the fleet
   charge facts (`ewu.coldsnap.moderate.staggered.margin_115.hosts_2.soc_median_pct_by_hour`, `soc_p10_pct_by_hour`)
   instead of one host's kWh. Until then, do not record step 1's home view or the cold snap charge line.
2. FIXED 2026-11-13 for git going forward: both files untracked (git rm --cached, still on disk), .gitignore adds
   runs/**/*.png, tracked runs png 11 -> 9; test tests/test_house_rules.py
   test_single_home_figures_are_not_tracked_and_new_run_figures_are_ignored. NOT fixed: both stay in the private
   remote's history; rewriting it is Gio's call. Original finding:
   runs/plain/fig6_dispatch_example.png and runs/plain/fig2_signatures.png are single real homes, tracked and pushed
   to origin/prototype (private GitHub repo). Fix: `git rm --cached` both, add `runs/**/*.png` to .gitignore,
   commit, push; tell Gio the files stay in the private remote's history (rewriting it is his call). Never use them
   in the video or deck.
3. FIXED 2026-11-13: "$15,000 (mid)" -> "$15,000 (mid placeholder)" and "7% rate" -> "7% rate, a placeholder";
   numbers unchanged, trace_numbers on docs/BUSINESS_CASE.md 162 traced, 0 untraced; test
   tests/test_business_case.py test_every_assumed_price_is_labeled_where_it_is_cited. Original finding:
   docs/BUSINESS_CASE.md:24 "$15,000 (mid)" and docs/BUSINESS_CASE.md:95 "7% rate" are not labeled as placeholder
   and assumption. Fix in ewu/business_case_template.md: "$15,000 (mid placeholder)" and "7% rate, a placeholder";
   rerun `bin/ewu case` and `checks/trace_numbers.py docs/BUSINESS_CASE.md`.

Should fix, not errors: add "includes 0.04% newly overloaded by staggering" under the rung table
(docs/BUSINESS_CASE.md:86 and the narration at docs/DEMO_SCRIPT.md:25); say that 65.65 of the 69.07% is
smart-thermostat eligibility (docs/DEMO_SCRIPT.md:23); drop or measure "on the coldest nights"
(docs/BUSINESS_CASE.md:37); fix the 890,000 basis year in config/ewu.yaml:117. This audit file itself holds
working numbers (18 untraced by trace_numbers), so leave it out of any `trace_numbers docs/*.md` gate.
