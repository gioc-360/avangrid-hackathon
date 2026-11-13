# Overnight build plan: Electrify Without Upgrade (EWU) prototype

## Scoped (this section wins over everything below)

Scoped 2026-11-12 23:17 ET. One coder, one night, one goal: a live demo that runs offline, answers in under a minute
and survives code questions. The teammate builds the deck; this build hands over numbers and screens, never slides.

Decisions taken. D1: commit and push to branch `prototype` after each green milestone (this replaces "No git push"
in section 7). D2: our rebuild is the reference; differences from the teammate's numbers are reported, never tuned
away. D3: k = 8 homes per transformer, and only 8.

```
┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐
│ M0  INV    │──▶│ M1  M2     │──▶│ M3  M4     │──▶│ M5         │──▶│ M6  M7     │──▶│ J1 M8 J2   │
│ config,    │   │ stress,    │   │ cold snap, │   │ money,     │   │ CLI, demo  │   │ judges,    │
│ inventory  │   │ attribution│   │ fit score  │   │ range grid │   │ page, docs │   │ review     │
└────────────┘   └────────────┘   └────────────┘   └────────────┘   └────────────┘   └────────────┘
```

### S1. Layout fixed by this scope (so the exit checks are exact)
- `config/ewu.yaml`: every input as `{value, unit, source}` or `{value, unit, assumption: true}`. Blocks: `scenarios`,
  `transformer` (k, count, sizing margins, overload limit), `battery` (challenge page 3 spec), `shift`, `prices`,
  `demo`, `checks` (every test threshold), `teammate_reference` (numbers from runs/business_case_team_v2.txt with
  their line, used only for the D2 difference table).
- `ewu/`: adoption.py, feeders.py, stress.py, dispatch.py, fitscore.py, economics.py, inventory.py, demo_page.py,
  cli.py. `bin/ewu` is a two-line shell wrapper around `.venv/bin/python -I ewu/cli.py`. cli.py gains one
  subcommand per milestone: `inventory` in INV, `coldsnap` in M3, `sensitivity` in M5, `screen` and `demo` in M6.
- `tests/` with `conftest.py` that puts the repo root on the import path (needed under `-I`).
- `checks/config_check.py`, `checks/trace_numbers.py`, `checks/demo_check.py`, `checks/qa_refs.py`,
  `checks/judge_rounds_check.py`. Each has `--selftest` that plants one bad case and must catch it.
- Facts go under `ewu.*` in facts/facts.json. That file is in git, so it holds aggregates only. Per-home and
  per-transformer values shown on the demo page go through `record(..., private=True)`, which writes
  `outputs/private/facts_private.json`. One door for every number, and nothing per-home reaches git.
- Demo page: `outputs/demo/ewu_demo.html` (gitignored). Fallback screenshots: `outputs/private/demo_shots/`, not
  `docs/demo/`, because steps 1 and 3 show one home and one transformer. `docs/demo/cli_output.txt` holds aggregate
  terminal output only.

### S2. Milestones (ids, time box in ET, what is built, what the exit check proves)
| Id | Box | Build | The exit check proves |
|---|---|---|---|
| M0 | 23:20-23:50 | `caffeinate -dims &`; config/ewu.yaml; config_check.py; pytest in requirements.txt; tests/conftest.py; `record(private=True)`; Makefile targets `test` and `prototype` | every config value has a source or an assumption flag; a planted unsourced value is caught; new modules have a what/why/how docstring, stay under the line cap, hold no em dash |
| INV | 23:50-00:20 | inventory.py and `bin/ewu inventory`: one row per home with equipment flags, confidence, segment, eligible programs (rules in config), written to outputs/private/inventory.parquet; prints the aggregate table only | row count equals fact `data.customers_usable`; every home has a segment; each class count equals its `class.*.count` fact; every program rule is read from config; stdout holds no customer number |
| M1 | 00:20-01:20 | adoption.py, feeders.py, stress.py: 2030 scenarios, k = 8 groups, random and same-segment grouping, sizing = today's peak times each margin in config; `load_map(csv)` for a real map | loading equals base plus EV plus heat pump adds; no home sits in two transformers; overloaded share never rises as the margin rises; 5 seeds agree within the config tolerance; the overloaded share at every sizing margin is in facts |
| M2 | 01:20-02:10 | attribution of overload hours to base, EV and heat pump kW; EV timer mode and staggered mode; docs/FINDINGS.md answers the 73% versus 89% question and holds the D2 difference table | shares sum to 100%; shifting moves EV energy and loses none; timer and staggered results are in facts; every number in FINDINGS.md traces |
| M3 | 02:10-03:30 | dispatch.py and `bin/ewu coldsnap`: battery through Feb 7-8, hour by hour, charging only under the limit | state of charge stays between 0 and capacity; power stays within the challenge spec; energy balance holds within the config tolerance; zero batteries reproduces the M1 numbers; hours over, kWh over and share cleared are in facts. Then one agent that did not write the code recomputes 3 of those numbers its own way and logs match or mismatch; a mismatch reopens M3 once |
| M4 | 03:30-04:15 | fitscore.py: system top hours, kW cut per home in those hours, hosts chosen on flagged transformers, 1 or 2 units per host | Feb 7 and Jul 2 are in the top-hour set; fit-score hosts clear more flagged transformers per battery than random hosts on the same set |
| M5 | 04:15-05:10 | economics.py: ladder cost, equal-life comparison (battery life versus transformer life), deferral value, one labeled NYSEG scaling line; `bin/ewu sensitivity` runs the grid of 2 scenarios by 4 margins by 2 grouping modes | economics.py holds no typed price; equal lives and zero discount rate give the plain cost ratio; deferral value never exceeds the upgrade cost; all grid cells are in facts; the headline is stated as a range |
| M6 | 05:10-06:20 | cli.py gains `screen` (flag, shift, protect, upgrade split for one scenario and margin, optional `--map`) and `demo`; demo_page.py builds the 4-step offline page from cached results; `make prototype` rebuilds all of it from data/processed | `make prototype` runs clean; the page has no outside link or script; headless Chrome renders all 4 steps with no NaN or undefined; every number on the page binds to a fact key or a private fact; `bin/ewu screen` on the full data finishes under 60 s and the seconds are in facts |
| M7 | 06:20-06:50 | docs/DEMO_SCRIPT.md (3-minute click path: click, one sentence, objection answered); docs/CODE_QA.md (10 judge questions, each answered with file:line); README section "Run the EWU tool" with one diagram | every file:line resolves; every number in the three docs traces |
| J1 | 06:50-07:20 | docs/COMPANY_BRIEF.md (sourced lines only, unverified teammate claims listed apart); judge round 1 per section 6b, Talent Development judge held out; fix the top 3 gaps in wording and outputs | runs/judge_rounds.json holds round 1 for all 9 judges with per-criterion gaps to the A1 anchor; all tests and the demo check still pass after the fixes |
| M8 | 07:20-07:50 | one fresh agent tries to break 10 numbers by recomputing them; the code examiner asks 10 questions against CODE_QA.md; fix or label what breaks | runs/review_round.json holds 10 number checks and 10 answers; examiner pass is 9 of 10; tests and demo check still pass |
| J2 | 07:50-08:10 | judge round 2, scores only, no fixes | round 2 and the held-out judge's change are in judge_rounds.json and MORNING_REPORT.md |

Hard stop 08:15 ET: stop building, write the top of docs/MORNING_REPORT.md (section 8), commit, push.

### S3. Exact exit-check commands
Run from the repo root. Every command must exit 0. Every milestone also runs the gates line last.
```
cd /Users/giocaballero/avangrid-hackathon
GATES  make check && .venv/bin/python -I checks/compare.py
M0     .venv/bin/python -I checks/config_check.py --selftest && .venv/bin/python -I checks/config_check.py && .venv/bin/python -I -m pytest -q tests/test_config.py tests/test_house_rules.py
INV    bin/ewu inventory && .venv/bin/python -I -m pytest -q tests/test_inventory.py
M1     .venv/bin/python -I -m pytest -q tests/test_stress.py
M2     .venv/bin/python -I -m pytest -q tests/test_attribution.py && .venv/bin/python -I checks/trace_numbers.py --selftest && .venv/bin/python -I checks/trace_numbers.py docs/FINDINGS.md
M3     .venv/bin/python -I -m pytest -q tests/test_dispatch.py && bin/ewu coldsnap --date 2026-02-07
M4     .venv/bin/python -I -m pytest -q tests/test_fitscore.py
M5     .venv/bin/python -I -m pytest -q tests/test_economics.py && bin/ewu sensitivity && .venv/bin/python -I checks/trace_numbers.py docs/FINDINGS.md
M6     make prototype && .venv/bin/python -I -m pytest -q tests/ && .venv/bin/python -I checks/demo_check.py --selftest && .venv/bin/python -I checks/demo_check.py
M7     .venv/bin/python -I checks/qa_refs.py --selftest && .venv/bin/python -I checks/qa_refs.py docs/CODE_QA.md && .venv/bin/python -I checks/trace_numbers.py docs/DEMO_SCRIPT.md docs/CODE_QA.md docs/FINDINGS.md
J1     .venv/bin/python -I checks/judge_rounds_check.py --round 1 && .venv/bin/python -I -m pytest -q tests/ && .venv/bin/python -I checks/demo_check.py
M8     .venv/bin/python -I checks/judge_rounds_check.py --review && .venv/bin/python -I -m pytest -q tests/ && .venv/bin/python -I checks/demo_check.py
J2     .venv/bin/python -I checks/judge_rounds_check.py --round 2
```
`checks/demo_check.py` is one script that: confirms outputs/demo/ewu_demo.html exists and names no http or https
resource; dumps the page with headless Chrome ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
--headless) and finds all 4 steps filled; writes one screenshot per step to outputs/private/demo_shots/; confirms
every number on the page binds to a fact key or a private fact and equals it; times `bin/ewu screen --scenario
moderate --margin 1.15` on the full data, fails at 60 s or more, and records `ewu.cli.screen_seconds`.

### S4. Rules that hold for every milestone
- After a green exit check: `git add -A`, then `git diff --cached --name-only`; unstage any .npy, .parquet, .csv,
  anything under outputs/private/ or outputs/demo/, and any per-home file; commit with a plain description; then
  `git push -q origin prototype`. Then append one line under "## Log" in docs/MORNING_REPORT.md.
- A failing check is fixed and retried at most 2 times. On the third fail the milestone is logged FAIL and the build
  moves to the next milestone that does not depend on it. Thresholds in `checks:` are fixed tonight; a test is
  never loosened to pass.
- Tests, checks and CLI commands print aggregates only. Judge and review agents read aggregates only: CLI output,
  FINDINGS.md, DEMO_SCRIPT.md, facts.json. Steps 1 and 3 of the page are checked by script, not by an agent
  looking at a home's rows.
- Before `make prototype` and any other step over 60 s: read the Loggie call file named in section 6; if a
  recording is live, wait 10 minutes and read it again.
- The three unverified teammate claims in section 6b stay off the demo page and out of the demo script.
- Depends on: INV, M1 need M0. M2, M3 need M1. M4 needs M3. M5 needs M2, M3, M4. M6 needs INV and M1; a step
  whose milestone failed shows "not built" on the page. M7, J1, M8 need M6. J2 needs J1.

### S5. Cut outright (not built tonight)
- Ambient-temperature derate (objection 6 is answered by hours over and kWh over the limit).
- Adoption clustered by transformer. Same-segment grouping stays as the one clustered mode.
- k = 4 and k = 12 in the grid (D3).
- report_ewu.py and deck PNG figures. The demo page is the readout; the step screenshots serve the deck.
- docs/ARCHITECTURE.md. Its one diagram goes in the README.
- The one-pager for judges. Judges read the CLI output, FINDINGS.md and DEMO_SCRIPT.md.
- Independent verify after M5 and after M8. One stays, after M3; M8 covers the others.
- CODE_QA.md shrinks from 20 questions to 10, the number the examiner asks.

### S6. Cut order if behind (drop from the top; each cut is logged in MORNING_REPORT.md)
1. J2, the second judge round.
2. `load_map(csv)` test and `--map` flag. The data contract stays as three lines in the README.
3. Same-segment grouping mode. The grid shrinks to 2 scenarios by 4 margins.
4. The NYSEG scaling line in M5.
5. The D2 difference table in FINDINGS.md.
6. CODE_QA.md drops to 5 questions and the examiner pass becomes 4 of 5.
7. The home picker in step 1 becomes one fixed home.
8. M8.

Never cut: INV, the sizing range in M1, attribution in M2, the cold snap in M3, fit-score hosts in M4, equal-life
economics in M5, the 4-step offline page and the under-60-s `bin/ewu screen` in M6, the self-checks (config_check,
trace_numbers, demo_check, pytest), and J1. If one of these fails three times it is reported FAIL, never dropped
quietly.

## Original plan (kept for context; Scoped above wins where they differ)

Owner: autonomous build, night of 2026-11-12 to 11-13. Deck due 5pm ET 11-13 (teammate builds the deck).
Purpose: the live DEMO portion. The prototype must run on stage in under a minute and survive code questions.
Scoper: read this whole file, then tighten scope; do not widen it.

## 1. What we are building, in one sentence
A tool that takes hourly meter data (and, when Avangrid has it, a meter-to-transformer map), inventories each home's
equipment and segment (challenge Parts 1 and 2), finds which neighborhood transformers electrification will overload
by 2030, and gives each one the cheapest fix in order: Flag, Shift (staggered EV charging), Protect (home batteries on
the best-fit homes), Upgrade (challenge Part 3). The challenge's code deliverable is "a tool applied to hourly loads
that will estimate inventory of heating and cooling appliances, and identify customers eligible for utility programs,
BESS, etc.", so `ewu inventory` (per-home equipment, segment, program eligibility) ships alongside `ewu screen`.

## 2. Why this shape (rubric, so every module earns points)
| Rubric line | What the prototype must show | Module |
|---|---|---|
| Value 40%: utility relevance, actionability | Per-transformer action list a planner can use; CLI runs on a real map later | `ewu screen` |
| Value: battery opportunity assessment | Fit score on system top hours (incl. Feb 7, Jul 2) picks battery hosts | `fitscore.py` |
| Value: impact quantification | MW at system peak, transformers fixed, $ deferred, per scenario, with ranges | `economics.py` |
| Analytics 35%: classification, segmentation | Reuse existing pipeline (classify.py, segment.py) with accuracy table | existing |
| Analytics: rigor | Duration test on the Feb 7-8 cold snap, battery state of charge, sensitivity grid | `stress.py`, `dispatch.py` |
| Analytics: reproducibility, assumptions | `make prototype`, every number in facts.json, every assumption labeled in one config | `config/ewu.yaml` |
| Presentation 15% | One HTML readout + PNG figures sized for slides | `report_ewu.py` |
| Innovation 10% | Headroom framing; timer-rebound finding; transformer view from AMI alone | figures |

## 3. Judge objections the build must answer (from the 6-judge panel, avg 3.57 vs front-runner 4.14)
1. Battery never tested on a long cold night. -> Feb 7-8 duration test: hours and kWh above limit vs battery energy, SoC by hour.
2. Headline depends on transformer sizing. -> Sensitivity: rating = today's peak x {1.05, 1.15, 1.30, 1.50}; report a range.
3. Random homes ignore clustering. -> Grouping modes: random, clustered (same segment), and adoption clustered by transformer.
4. "73% heat-pump nights" vs "EV staggering fixes 89%" contradiction. -> Attribute each overload hour to base / EV / HP kW.
5. "Avoids" an upgrade. -> Equal-life economics: battery 15 yr vs upgrade 30+ yr; report deferral value, not avoidance.
6. Thermal limit is a single 120% crossing. -> Report hours over limit and energy over limit; optional simple
   ambient-temperature derate (label it simplified, not IEEE C57.91).
7. Unsourced numbers. -> Every price and adoption % lives in config/ewu.yaml with `source:` or `assumption: true`;
   the checker fails on any number in the readout that is not in facts.json or config.

## 4. Architecture (high-level functions; each file under ~200 lines, docstring says what, why, how)
```
load_present.npy + segmented.parquet (existing)
        |
adoption.py   assign_adoption(scenario, mode) -> ev_homes, hp_homes        # 2030 scenarios, random or clustered
              ev_profile(mode) -> kW by hour                                # from measured EV start times in the data
              hp_profile(temp) -> kW by hour                                # fit on electric-heat homes vs temperature
feeders.py    build_transformers(k=8, mode, seed) -> groups                 # synthetic until a real map exists
              load_map(csv) -> groups, ratings                              # contract: meter_id, transformer_id, kva
              rate(groups, margin) -> ratings
stress.py     loading(groups, adds, action) -> kW by transformer by hour
              overload_metrics(loading, rating) -> peak ratio, hours over, kWh over, worst window
              attribute(loading parts, overload hours) -> share base / EV / HP
dispatch.py   battery_fix(transformer, hosts, units) -> SoC by hour, cleared?  # multi-day, charges only under limit
fitscore.py   system_top_hours(sysload, named_dates) -> hours
              fit_score(homes, hours) -> kW cut per home in those hours      # picks battery hosts
economics.py  ladder(results, config) -> cost per action, equal-life NPV, deferral value, NYSEG scaling (labeled)
cli.py        ewu inventory   -> per home: equipment flags + confidence, segment, eligible programs (existing pipeline)
              ewu screen --scenario moderate --margin 1.15 --mode random [--map file.csv]
              ewu sensitivity    ewu coldsnap --date 2026-02-07
report_ewu.py one HTML + figures/ PNGs; aggregates only
```
Data contract for the real world: `--map` CSV with meter_id, transformer_id, kva. Without it, synthetic groups.
Scale story: work is per transformer, vectorized; measure seconds per 1,000 transformers and record it.

## 4b. Demo surface (what the judges see live)
- `ewu demo` opens one local HTML page (no server, works offline, no external scripts) built from cached results:
  1. Inventory: pick a home, see its load shape, equipment flags with confidence, segment, eligible programs.
  2. Screen: pick scenario (moderate/high) and transformer sizing (+5/15/30/50%), see the share overloaded and the
     Flag/Shift/Protect/Upgrade split update.
  3. Cold snap: one flagged transformer through Feb 7-8, hour by hour: load vs limit, battery state of charge.
  4. Money: equal-life cost of the ladder vs upgrading everything, with the range.
- `ewu screen ...` also runs live from the terminal on the full data in under 60 s (timed in M6) to prove it is real.
- Fallback if the laptop fails: docs/demo/ holds PNG screenshots of each step and the terminal output.
- Customer rows shown on screen stay on this machine; the page is never published or uploaded.

## 5. Milestones (each ends on a command that must pass; time boxes in ET)
| # | Box | Build | Exit check (must pass before next) |
|---|---|---|---|
| M0 | 23:00-23:30 | Snapshot repo (see decision D1). Create config/ewu.yaml with every input and its source or assumption flag. Port teammate numbers as targets. Write docs/COMPANY_BRIEF.md (sourced lines only). | `python -I checks/config_check.py` (every value has source or assumption) |
| M1 | 23:30-00:30 | adoption.py, feeders.py, stress.py; rebuild baseline stress test | pytest: overloads fall as margin rises; loading = base + adds exactly; 5 seeds within +-1.5 pts |
| M2 | 00:30-01:30 | Attribution + EV timer and staggered modes; resolve the 73% vs 89% question with numbers | pytest: attribution sums to 100%; facts recorded; written answer in docs/FINDINGS.md |
| M3 | 01:30-03:00 | dispatch.py + Feb 7-8 cold snap; SoC never <0 or >capacity; charges only under limit | pytest: energy balance within 0.1%; cold-snap table recorded |
| M4 | 03:00-04:00 | fitscore.py on system top hours (named dates in set); choose hosts on flagged transformers | pytest: Feb 7 and Jul 2 in top-hour set; targeted hosts beat random hosts |
| M5 | 04:00-05:00 | economics.py with equal-life NPV and deferral; sensitivity grid (margins x modes x scenarios) | every $ traces to config; grid written to facts |
| M6 | 05:00-06:00 | cli.py + report_ewu.py + demo page (section 4b); figures as a bonus for the deck | `make prototype` from clean runs end to end; readout has 0 untraced numbers; `ewu demo` page renders all 4 steps (headless screenshot check); live `ewu screen` under 60 s |
| M7 | 06:00-06:45 | docs/DEMO_SCRIPT.md (3-minute click path) + docs/ARCHITECTURE.md (one diagram) + docs/CODE_QA.md (20 likely judge questions, each answered with file:line) | every file:line in CODE_QA resolves; `make check` passes |
| J1 | after M6 | Judge battle test round 1 (section 6b) on the readout + one-pager; fix the top 3 gaps | scores recorded in runs/judge_rounds.json |
| M8 | 06:45-07:15 | Fresh-eyes review agent tries to break 10 numbers; fix or label | review report in docs/MORNING_REPORT.md |
| J2 | 07:15-07:45 | Judge round 2 on the fixed build + code examiner (section 6b) | round-2 scores and Q&A pass rate in MORNING_REPORT.md |

Cut order if behind: drop M7 polish first, then ambient derate, then clustered-adoption mode. Never drop M3 (cold snap)
or the sensitivity range; those are what the judges asked for.

## 6. How it runs unattended and checks itself
- Keep the Mac awake for the whole run: start with `caffeinate -dims` in the background.
- Driver: one orchestrating session works milestone by milestone. After each milestone: run its exit check;
  on fail, fix and retry at most 2 times; on a third fail, write the blocker to MORNING_REPORT.md, mark the milestone
  red, and continue with the next milestone that does not depend on it.
- Independent verify: after M3, M5 and M8, a separate agent that did not write the code reviews it against this plan
  and tries to refute three numbers by recomputing them its own way.
- Gates that already exist and must stay green: `make check` (31 requirements, 26 sources), `checks/compare.py`.
- New gates: `pytest -q tests/`, `checks/config_check.py`, readout number tracing extended to EWU facts.
- Before any step expected to run over 60 s: read ~/Library/Application Support/Loggie/hikyaku/calls/current.json;
  if a recording is live, wait and retry in 10 minutes.
- Heartbeat: append one line per milestone to docs/MORNING_REPORT.md (time, milestone, pass/fail, key number).

## 6b. Battle test: simulated judges (rubric + Avangrid company context)
- Panel: all 9 judge roles from runs/IDEATION_BRIEF.md (Load Research Director "Scott", Storage Policy, Customer
  Programs, Load Forecasting, Data Engineer, Reliability, Technology & Innovation, Regulatory NY, Talent Development).
- Each judge reads only: the rubric PDF, the challenge statement, the kickoff deck, Scott's office-hours transcript,
  docs/COMPANY_BRIEF.md, and the rendered outputs (readout HTML/PNGs, one-pager, CLI output). Not the source code,
  except the Data Engineer and the code examiner.
- docs/COMPANY_BRIEF.md (built in M0) holds only sourced Avangrid facts: runs/SOURCES_FACTS.md, kickoff deck,
  challenge, Scott. Each line cites its source. Unsourced teammate claims (Rate Decoupling Mechanism, capex 3.4x
  operating cash flow, Stillwater RFP) go in a separate "unverified" list judges are told not to trust.
- Scoring: 1-5 per rubric criterion, weighted 40/35/15/10, one bonus point per judge, head to head against the anchor
  A1 "System-Peak Battery Fit Score" (4.14) so rounds are comparable. Report per-criterion gaps, not just the total.
- Code examiner: one agent reads the repo cold, asks 10 questions a technical judge would ask, and checks each answer
  in docs/CODE_QA.md against the cited file:line. Pass = 9 of 10 answers correct and resolvable.
- Anti-overfitting: the Talent Development judge is held out; it never feeds fixes, only scores. If the 8 used judges
  rise and the held-out one does not, say so in the morning report.
- Stop rule: fix loop ends when the weighted average beats 4.14, or after 2 rounds, or if a round gains under 0.1
  (inside judge noise). Fixes may change outputs and wording; they may not change a number without rerunning its code.

## 7. Guardrails
- Hackathon data never leaves this machine: no uploads, no web calls with data, no customer rows in git or reports.
- Outputs with customer or transformer rows go to outputs/private/ (gitignored). Readout shows aggregates only.
- Do not edit the teammate's documents in Downloads. Do not touch the pptx deck.
- No em dashes in any prose. Numbers in prose come from facts.json only.
- No git push. Local commits only if D1 says yes.

## 8. Morning handoff (what Gio reads first, docs/MORNING_REPORT.md)
Top: 3 sentences, what works, what failed, what to say if asked about code. Then a table per milestone,
the headline numbers with ranges, the cold-snap verdict for batteries, judge scores by round (with the held-out judge
and the A1 anchor), the code examiner pass rate, and the slide-ready figure list. The deck itself is not built
overnight; the report says which figure goes on which slide.

## 9. Decisions for Gio before starting
- D1: allow local git commits on a branch `prototype` after each green milestone (recommended; no push). If no,
  the build takes a tar snapshot of the repo before M0 instead. Most of the pipeline is currently untracked.
- D2: if the teammate's simulation code arrives, reconcile to it or keep our rebuild as the reference? (recommended:
  keep ours as reference, report differences.)
- D3: transformer size k = 8 homes (teammate) as default, with 4 and 12 in the sensitivity grid.
