# Deck audit notes: where the app and deck v3 meet

Gio's rule (2026-11-13): "in the app it shouldn't refer anything explicitly in deck like (not in v3); just note me
here or note it in a markdown for final auditing checks". This file holds those notes. The page, every `bin/ewu`
printout and every help text now name no deck and no version; `tests/test_no_deck_words.py` fails the build if one
comes back. Every comparison below sits here, for the final audit before submission.

Deck v3 means `D4G Cornell 2_Final Submission_v3.pptx`. The independent check of 107 claim pairs (0 mismatches)
is in `outputs/deck/app_v3_check.md` (local, gitignored). Numbers below come from `facts/facts.json` and
`config/ewu.yaml`, by key.

```
deck v3 slides ──▶ teammate spec 2026-11-13 ──▶ config profiles.deck ──▶ bin/ewu screen ──▶ facts ewu.deck.*
                   (runs/teammate_deck_spec...)                                                  │
teammate rerun ──▶ facts teammate.audit.rerun.* ────────────────────────────────────────────────┼──▶ page
replica ─────────▶ facts ewu.deck_replica.* (Summary dropdown, Validation) ─────────────────────┘
```

## Naming: what the viewer reads, what the code keeps

| Viewer sees | Code keeps | Where |
|---|---|---|
| "battery plan" (`bin/ewu screen`, `network`, `plan`, `recharge` headers; page dropdowns) | profile `deck`, module names `ewu/deck*.py`, fact keys `ewu.deck.*`, config `profiles.deck.*` | printouts, page |
| `--profile battery`, `--profile replica` | old `--profile deck` and `deck-replica` still accepted as hidden aliases; `profiles.default: deck` in config | `ewu/cli.py` PROFILE_NAMES |
| "Synthetic network" tag alone | unchanged | Network view |
| "Managed charging (optional)" (CLI `--managed` help; network fact method) | `profiles.deck.managed_charging` | not on the page |
| Plan files in `outputs/plan/battery/` | earlier runs left in `outputs/plan/deck/` (not deleted) | `ewu/deck_views.py` OUT |
| A number's hover title is its fact key, for example `fact:ewu.deck.moderate.limit_120.overloaded_pct` | kept on purpose: "hover a number for its key" is the page's traceability promise | every view |
| The URL hash `#step=deck` for Summary | kept: `video/v3_plan.py` and the film's takes open `step=deck`; the hash is not visible in the kiosk film | Summary |

Open for Gio: the hover keys and the hash still contain the word "deck" for anyone who hovers or reads the address
bar in a normal browser window. Renaming them means renaming fact keys and re-filming nothing, but touching every
check that reads `ewu.deck.*`. Not done.

## Where the app and the deck connect or differ

| Number or rule | Deck v3 (slide) | App (view) | Status and why |
|---|---|---|---|
| Loading limit options | 110%, 120%, 140% only (slides 28, 29; A13) | 100%, 110%, 120%, 140% buttons on Overview, Flag, Place, Upgrade, Money | differ. The teammate's spec keeps 100% as a sensitivity (`profiles.deck.overload_limit_options`). The page used to label it "not in deck v3"; it now shows it plain, and the dropdown calls it "a stricter extra check" beside "the battery plan reports 120% and tests 110% and 140%". Config `profiles.deck.limits_tested` (was `limits_in_deck_v3`) holds the three the deck shows. At 100% the page shows numbers on no slide, for example High 60.03% overloaded and a 50.33% saving (`ewu.deck.high.limit_100.*`), and 2.1 battery units each, which clashes with the deck's "1 or 2 units". Gio's call: keep, or drop 1.00 from the options. |
| Reported limit | 120% (A13, slide 12) | 120% default (`profiles.deck.overload_limit`) | match |
| Summer peak cut | 8.8 MW from 2,610 priority homes (slides 2, 10, 15) | 8.80 MW from 2,610 (Summary; `bin/ewu screen` last line) from `teammate.audit.rerun.fleet_priority.peak_cut_mw` 8.8025 and `teammate.audit.rerun.priority_homes` 2,610: the teammate's ranking rerun on our data, 2 units each, export allowed | match. The model's own hosts give a different figure: `ewu.deck.peakcut.hosts` 2,733 homes, 9.05 MW export allowed (`export_peak_drop_mw`), 7.11 MW behind the meter. Neither the page nor the screen printout shows the 2,733-home run any more; its facts stay for the docs. |
| Mean cut over the top 50 hours | not on a slide we found | `bin/ewu screen` prints 6.16 MW (`teammate.audit.rerun.fleet_priority.top50_cut_mw`) beside the peak cut | app only; printout, not page |
| Replica | the teammate's run is the deck's source (A13) | Summary dropdown, Validation: our replica equals her saved results on 3,000 of 3,000 transformers per scenario (`ewu.deck_replica.*.rows_equal_her_run`) | match. Our engine (the battery plan) differs from her model by small amounts at 120%: overloaded 9.73 vs 9.83 (moderate), 29.87 vs 29.83 (high); fixed 98.29 vs 98.31, 91.63 vs 93.52; winter nights 79.79 vs 72.88, 89.96 vs 89.16. Causes are measured in `bin/ewu screen --replica` (the ladder A to E) and `tests/test_deck_alignment.py` (2 xfail). The deck took our engine's numbers, so the page's headline numbers equal the deck's. |
| Money basis | present value, 15 years at 7%, upgrade $15,000 counted for 15 of its 40 years, lease $330 a unit a year, NYSERDA $2,016 a unit, $7,000 a unit (slides 11, 26 to 29) | same inputs (`profiles.deck.*`), counted upgrade $10,248 (`ewu.deck.prices.upgrade_counted_usd`, factors 9.108 and 13.332), lease worth $3,006 (`lease_pv_usd`), NYSEG 890,000 customers / 8 = 111,250 transformers | match. The page now says "Money basis" and "one basis on every view" where it said "v3's basis" and "same basis on every slide". |
| Net cost and Upgrade all at 120% | $34.3M / $143.8M and $111.0M / $340.5M (A13; slide 2 rounds $34M, $144M) | same (Summary, Money) | match |
| Saving | 58% to 69% (slides 2, 11, 15); 69.1% and 57.8% (A13) | 69.06 / 57.78 (`saving_vs_upgrade_all_pct`) | match |
| Steps | Flag, Place, Dispatch, Upgrade (slide 12) | "three of the battery plan's four steps"; the page sizes batteries and never runs Dispatch | the page says it does not dispatch; deck shows four |
| Bar of slide 12 | fixed with 1 or 2 units, 3 or 4, upgrade, as % of all transformers | same bands (Overview, Place, Upgrade) | match |
| Network view | tool slide A17 | always Moderate 2030 at 120%, labeled | match; the page no longer says "the network deck v3 shows on its tool slide" |
| Cold snap test | none | Place dropdown: "the battery plan runs no separate cold snap test" | wording only |
| EV charging | unmanaged | Flag dropdown: "EV charging unmanaged" | match; managed charging is CLI only (`--managed`) |
| Gross cost above Upgrade all | slide 29 footnote: "before those offsets the battery path costs more than upgrading in every row" | Money dropdown says gross is below Upgrade all at Moderate 140% | deck side error, from `outputs/deck/app_v3_check.md` item 6: Moderate 140% gross $25.3M against Upgrade all $27.7M. For the teammates. |

## Terms

The app uses the deck's words (`docs/TERMS.md`, checked by `checks/terms_check.py`) without naming the deck.
Terms the app uses that the deck does not: "synthetic network" (the Network tag), "home type" (the engine's six
groups, not the deck's seven segments), "managed charging", "the teammate's EV start-hour shares and heat pump
curve", "the teammate's model". New here: "battery plan" as the name of the default method on screen. TERMS.md
lists "battery path" as the canonical term for the plan priced against Upgrade all; "battery plan" is the
method's name, and no banned pattern matches it. Gio's call whether the two should be one word.

## Not changed, for the audit

- `docs/BUSINESS_CASE.md` (from `ewu/business_case_template.md`), `docs/TERMS.md`, `docs/FINDINGS.md` and
  `docs/TEAMMATE_AUDIT.md` still compare with deck v3 by name: they are team documents, not the app.
- `deck/frontend_guide.py` captions: the Summary and Money captions now say "the battery plan"; the guide's
  intro still speaks to the teammates who build the deck.
- Code comments and docstrings keep their deck citations (slide numbers), since they are provenance.

## Narration claims to audit

Filled by the edit step: each spoken claim in the voiced film, the number it states, its fact key, and the deck
slide that carries it.

| Film time | Line | Spoken claim | Fact key | Deck slide | Status |
|---|---|---|---|---|---|
| 1:55.1 | pay (Money view) | "A third-party company owns and installs the batteries." | none: the model prices units, it has no owner | to find (business model slide) | not shown by the model; audit against the deck |
| 1:58.9 | pay | "Host homes pay a monthly lease for backup power." | none for "monthly"; the money basis counts lease $330 a unit a year (`profiles.deck.*`, slides 11, 26 to 29 per the money basis row above) | 11, 26 to 29 | not shown by the model: the model has a yearly lease paid against the cost, not a monthly payment by host homes; audit the wording |
| 2:02.4 | pay | "NYSERDA's incentive covers part of the cost." (her script's words; the recording sounds like "Nicea...", whisper heard "NYSEG's"; the caption says NYSERDA's, Gio 11-13) | NYSERDA $2,016 a unit in the money basis; the Money view shows Net cost without NYSERDA $67.4M (`ewu.deck.moderate.limit_120.nyseg_net_without_nyserda_musd`) | 11, 26 to 29 | the incentive amount is a model input; the spoken name is unclear in the audio, so the caption carries it |
| 2:05.6 | pay | "NYSEG recovers the remaining $34 million through electric rates, the same way it would for transformer upgrades." | $34 million is the net cost, `ewu.deck.moderate.limit_120.nyseg_avangrid_cost_musd`; rate recovery: none | to find | the number is a model output; recovery through rates is not modeled; audit against the deck |

Film times are in `outputs/video/v4film/EWU_demo_final.mp4` (2:56.3); the edit decision list beside it maps each to
her recording.
