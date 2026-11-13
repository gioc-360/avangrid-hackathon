# Avangrid AMI hackathon: end uses, segments, batteries

Hourly smart-meter data for 33,757 homes plus weather. The pipeline classifies equipment (EV Level 1/2, AC,
electric and heat-pump heat, water heaters, pools, hot tubs, solar and solar + battery), segments homes, and
ranks and sizes behind-the-meter batteries (Enphase IQ 10C). The repo also checks itself: one command answers
"are we still solving the problem they set?" and "does every number and quote trace to code or a source page?"

## Run it

```
make env                      # Python 3.12 venv from requirements.txt
make all                      # zips -> matrix -> features -> classes -> segments -> batteries -> readout (~4 min)
make check                    # problem coverage + source checks
make check DECK=deck.pptx     # also trace every number and quote on every slide
```

Data is not in the repo (event-confidential). Point `DATA=` at the folder holding the four zips.

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
| source | an outside citation's quote is not on its cited page (`checks/citations.yaml`, web copies in `sources/web/`) |
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

## Main limitations

Labels are positive-only and unverified (EV and heat-pump lists are ~25% samples). Hourly data hides
15-minute peaks, so the 3 kVA test is optimistic. No transformer map, so relief is system-level, not local.
All $ values are assumptions until replaced with NYSEG/RG&E tariffs and avoided-cost values.
