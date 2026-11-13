# Analyst brief (identical for every analyst)

## The job
Avangrid hackathon (judged on a PowerPoint by Avangrid load research, energy storage policy, customer programs,
load forecasting, reliability and NY regulatory staff). Read the challenge and rubric first:
- `pdftotext -layout "/Users/giocaballero/Downloads/00_Hackathon Materials/Challenge Statement.pdf" -`
- `pdftotext -layout "/Users/giocaballero/Downloads/00_Hackathon Materials/Scoring Rubric.pdf" -`

Your question: **what is this data really saying?** Answer the challenge's three parts with numbers you computed:
1. Classification: which customers likely have Level 1 / Level 2 EV charging, AC, resistance heat, heat pumps,
   electric water heat, pools, hot tubs, solar (+ battery), and anything else you discover. Evidence + confidence per class.
2. Segmentation: segments from load behaviour, their size, and what the utility should do with each.
3. BTM battery + demand flexibility: who are candidates, what size (the unit is 2x Enphase IQ 10C: 20.16 kWh total,
   7.68 kW continuous, 89.4% round trip; 1 or 2 units allowed), peak reduction, load shifting, capacity relief,
   bill savings, electrification enablement (a 200 A service should not exceed ~3 kVA of added load without study).

## Data (already processed; do NOT modify anything under data/processed)
Python: `~/avangrid-hackathon/.venv/bin/python -I` (numpy, pandas, polars, duckdb, scikit-learn, scipy, matplotlib).
Folder: `~/avangrid-hackathon/data/processed/`
- `load_present.npy` float32 [25,653 customers x 8,760 hours], kWh per hour; row i = `present_ids[i]` (see features.parquet
  CUSTOMER_NUMBER, same order). Hour 0 = 2025-09-01 00:00-01:00 local. Load is delivered energy only: never negative;
  solar export shows as 0.
- `daily.npy` float32 [25,653 x 365] daily kWh, same row order.
- `weather.parquet` 8,760 rows: temp (F), humidity (%), windspeed (mph), hourly, same hour index. Range -5F to 92F.
- `features.parquet` 25,653 rows x 58 cols, one per customer; definitions and rationale in
  `~/avangrid-hackathon/analysis/features.py` (read it). Includes labels lab_ev, lab_hp, lab_pv.
- `sysload.npy` summed hourly load of all customers; `system_peaks.json` top-20 winter and summer system hours.

Labels: EV list = random ~25% sample of likely-EV homes (200 given, 140 present in our data); HP list = ~25% sample
(100 given, 60 present); PV list = all known solar (434 given, 316 present). Labels are positive-only and not physically
verified: unlabeled does not mean negative.

Data defect (already confirmed): the file named customers 10,001-20,000 actually re-ships customers 1-10,000, so
10,072 customer IDs (almost all of 10,001-20,000) have no data. We have 25,653 of 35,725. Weather station location
is not given; temperatures suggest upstate NY / New England.

## Rules
- Write all scripts, charts (PNG) and notes into YOUR folder only (given below). Reproducible: scripts, not REPL-only.
- The data is confidential to the event: never send it or derived customer-level results to any external service
  or other model (no web uploads, no Gemini, no Codex). Web search for public facts (e.g., rates) is fine.
- Any number you did not compute from the data (rates, $/kW, adoption rates) is an ASSUMPTION: label it and say where
  it came from. Never present a guess as a finding.
- Validate classifiers against the labels (e.g., held-out recall on labeled positives, implied population vs the
  "25% sample" hint). Say how confident you are and why.
- Keep compute sane: the full matrix is 0.9 GB in RAM; vectorise with numpy.

## Output: `REPORT.md` in your folder (max ~2,000 words) containing
1. "What the data is really saying": the 5-7 most important findings, each one sentence with its number.
2. Part 1, 2, 3 results with tables of counts, confidence, and method (formulas).
3. Charts you made (file names + one line each on what it shows).
4. What surprised you, what you are least sure of, what you would check next.
5. A list of every assumption.
