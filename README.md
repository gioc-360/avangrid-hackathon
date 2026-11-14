# Electrify Without Upgrade: Avangrid AMI hackathon (Team D4G Cornell 2)

**What:** a planning engine that reads hourly smart-meter data for 33,757 homes and finds the neighborhood
transformers that 2030 EVs and heat pumps will overload, then prices the cheapest fix for each: 1 to 4 leased home
batteries, or an upgrade only where batteries cannot fix it. **Why:** a battery fleet for the summer peak alone does
not pay (benefit to cost 0.85), but a battery placed where it avoids a transformer upgrade does: in the engine's
run, batteries fix 92% to 98% of overloaded transformers at 58% to 69% lower net cost than upgrading every one
(present value, 15 years). **How:** `bin/ewu screen` reruns the whole transformer test on the full meter data in
about 2 seconds; every number it prints is recorded in `facts/facts.json`, and every transformer and money number
in the final deck traces there. Transformers are synthetic (8 real homes each, 3,000 of them), because the data has
no meter-to-transformer map; `bin/ewu screen --map` takes a real one.


Hourly smart-meter data for 33,757 homes plus weather. The pipeline classifies technology (EV Level 1/2, AC,
electric and heat-pump heat, water heaters, pools, hot tubs, solar and solar + battery), sorts homes into home types, and
ranks and sizes behind-the-meter batteries (Enphase IQ 10C). The repo also checks itself: one command answers
"are we still solving the problem they set?" and "does every number and quote trace to code or a source page?"

## Run it

```
make env                      # Python 3.12 venv from requirements.txt
make all                      # zips -> matrix -> features -> classes -> home types -> batteries -> readout (~4 min)
make check                    # problem coverage + source checks + battery recompute (about 70 s)
make check DECK=deck.pptx     # also trace every number and quote on every slide
```

Data is not in the repo (event-confidential). Point `DATA=` at the folder holding the four zips.

Also kept outside the repo: the organizers' PDFs and full-text copies of the web articles the citations quote
(copyright and event confidentiality; `checks/citations.yaml` keeps each URL and quote), a teammate's code that
`config/ewu.yaml` cites line by line, and the demo video's production code. `make check` reads those local copies,
so it runs on the team's machines, not on a fresh clone.

## Run the EWU tool

Electrify Without Upgrade (EWU) finds the neighborhood transformers that 2030 EVs and heat pumps will
overload and gives each the cheapest fix. It runs offline on the processed meter data; every command
prints aggregates only. Run it as `bin/ewu` (`python -I -m ewu` does not work, because `-I` keeps the repo
off the import path).

```
bin/ewu --help                                     # list the commands
bin/ewu inventory                                  # Parts 1 and 2: technology, home type, eligible programs per home
bin/ewu screen --scenario moderate --margin 1.15   # Flag, Shift, Place, Upgrade on the full data, live
bin/ewu screen --map meters.csv                    # same, on a real map: meter_id, transformer_id, kva
bin/ewu network                                    # the screen's synthetic network, transformer by transformer, for the page
bin/ewu coldsnap --date 2026-02-07                 # battery hour by hour through the Feb 7-8 cold snap
bin/ewu tophours                                   # MW the battery hosts cut in the system's top 20 and 50 hours
bin/ewu sensitivity                                # every scenario x sizing margin x grouping, priced
bin/ewu robustness                                 # heat pump slope x 1.5 and x 2, flag duration, 3 kVA by charge length
bin/ewu case                                       # docs/BUSINESS_CASE.md, every number filled from facts
bin/ewu demo                                       # the offline demo page, the deck's numbers; opens on Summary
make prototype                                     # rebuild all of the above from data/processed
```

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ meter data   │──▶│ FLAG         │──▶│ SHIFT        │──▶│ PLACE        │──▶│ UPGRADE      │
│ + map (opt.) │   │ stress.py    │   │ shift.py     │   │ fitscore.py  │   │ economics.py │
│ inventory.py │   │ any hour over│   │ managed EV   │   │ dispatch.py  │   │ what is left │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
                          every number ──▶ analysis/facts.py record() ──▶ facts/facts.json
```

Inputs live in `config/ewu.yaml`, each with a source or an assumption flag (`checks/config_check.py`). The
one-page case is `docs/BUSINESS_CASE.md` and the reasoning is `docs/FINDINGS.md`; `checks/trace_numbers.py`
traces every number in both. Tests: `make test`. Demo page check: `.venv/bin/python -I checks/demo_check.py`.
The demo page shows the deck's numbers, all from the engine's battery plan profile (the cautious profile stays in the
CLI, `--profile cautious`). It opens on Summary, one column per scenario; Network then draws one substation, 6
illustrative feeders and every synthetic transformer of the deck profile, recolored by Today, 2030: Flag,
+ Place batteries, + Upgrade; click a transformer for its 8 homes summed on its worst 2030 day. Overview, Flag,
Place, Upgrade and Money switch scenario and loading limit. The page uses the deck's terms, one per idea
(docs/TERMS.md, checked by `checks/terms_check.py` in `make check`). Each view keeps its assumptions in one closed
"How this is computed".
The three-minute click path for the live demo is `docs/DEMO_SCRIPT.md`; likely code questions, each answered with
file:line, are in `docs/CODE_QA.md`, and `checks/qa_refs.py` fails if any cited line no longer holds its code.

## How the pieces fit

| Step | Script | Output |
|---|---|---|
| Ingest | `analysis/ingest.py` | `data/processed/load.npy`: customers x 8,760 hours, float32, ~20 s, nothing unzipped to disk |
| Features | `analysis/features.py` | one row per home; each feature names the load shape it catches |
| Part 1 | `analysis/classify.py` | `outputs/customer_classes.csv`, rule + positive-unlabeled model per class |
| Part 2 | `analysis/segment.py` | `outputs/customer_segments.csv`, peak shares, winter-flip point |
| Part 3 | `analysis/bess.py` | `outputs/bess_candidates.csv`, relief, sizing, 3 kVA enablement, value |
| Readout | `analysis/report.py` | `outputs/readout.html`: prose filled from facts, charts from aggregates |

Every number a slide may use is written by `analysis/facts.py: record()` into `facts/facts.json` with its unit,
script and method. Dollar inputs live under `assumption.*` and the checker fails any slide that uses them
without saying so.

## The checks (`checks/check_all.py`)

| Check | Fails when |
|---|---|
| brief | a requirement's quote is not on the cited page of the organizers' PDFs (`checks/requirements.yaml`) |
| coverage | a requirement has no computed fact or file behind it |
| source | an outside citation's quote is not on its cited page (`checks/citations.yaml`; web copies kept outside the repo) |
| quotes | a quoted phrase on a slide is under 3 words or not found on any cited page |
| numbers | a number on a slide matches no computed fact and no cited number |
| assumed | a number rests on an assumption and the slide does not say so |
| scope | the deck drifts onto topics the challenge never asked (outages) |

`checks/compare.py` holds the plain-vs-skills analyst comparison (`runs/`) to the same rule: every quoted
analyst claim must be word for word in that analyst's report.

## Known data defects

The original `2026 Avangrid Hackathon Data_10001_20000.zip` contains customers 1-10,000 again. The Makefile skips it
and reads the corrected folder `2026 Avangrid Hackathon Data_10001_20000_v2` instead (set `V2=` to its path).
That folder holds 8,585 of the 10,000 promised IDs (`data.source.10001_20000.missing_in_range`).
Homes missing more than 10% of hours are left out, not gap-filled: 33,757 usable of 34,238 with any data.

## Where the deck's numbers come from

| Deck slides | Made by | Check |
|---|---|---|
| Transformers, batteries, money (slides 2, 10 to 15, A11 to A13, A18) | `ewu/` engine, `bin/ewu screen` | `facts/facts.json`, `make check DECK=` |
| Added energy on the same wires (slide 13) | `ewu/deck_energy.py` | `ewu.deck.*.added_energy_pct` |
| Classes and segments (slides 4 to 6, A1 to A7) | a teammate's classification and segmentation run; its saved outputs feed the engine through `data/processed` | counts checked against those outputs |
| The v4 deck itself | `deck/make_v4.py` (text and chart values from facts) and `deck/add_demo_video.py` | each edit asserts its old text |

`analysis/` is the team's first, independent pass at Parts 1 to 3 (readout in `outputs/readout.txt`). Its rules
differ from the teammate's run that the deck uses (for example 10,961 central AC homes against the deck's 16,833),
so its counts are not the deck's.

## Main limitations

Labels are positive-only and unverified (EV and heat-pump lists are ~25% samples). Hourly data hides
15-minute peaks, so the 3 kVA test is optimistic. No transformer map, so the engine groups 8 real homes per synthetic transformer; a real map replaces them.
All $ values are assumptions until replaced with NYSEG/RG&E tariffs and avoided-cost values.
