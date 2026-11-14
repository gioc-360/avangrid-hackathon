# Team pipeline: classification, segmentation and the battery ranking (Kayin Bejide)

This folder is Kayin Bejide's analysis code, added with her permission, exactly as she ran it. It produces the
team's final Part 1 and Part 2 numbers (for example 16,833 central AC homes, 1,331 homes with EV charging, the seven
segments) and the Part 3 ranking of 2,610 priority homes. Its aggregate outputs are in `../results/segment_*.csv`,
and two of its outputs feed the engine in `../ewu/`: `ev_start_pmf.npy` and `hp_increment.npy` (written by
`ewu_inputs.py`, checked by sha256 in `../config/ewu.yaml`).

```
┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐
│ ingest     │──▶│ features   │──▶│ classify   │──▶│ segment    │──▶│ battery    │
│ meter zips │   │ weather    │   │ PU logistic│   │ rules +    │   │ simulate,  │
│ to matrix  │   │ fits, load │   │ per device │   │ k-means    │   │ threshold, │
│            │   │ shapes     │   │            │   │            │   │ rank       │
└────────────┘   └────────────┘   └────────────┘   └────────────┘   └────────────┘
```

| Step | Scripts | Reads | Writes |
|---|---|---|---|
| Ingest | `run.sh`, `ingest.py`, `ingest_new.py` | the meter zips | fills the customer x hour matrix `kwh.npy` in place |
| Weather | `weather_fit.py` | `weather_raw.csv` | `daily_temp.npy`, `hourly_temp.npy` |
| Features | `features.py`, `features2.py`, `features3.py`, `assemble.py`, `prep_sys.py` | `kwh.npy`, temperatures | `feat_device.npz`, `features.csv`, `system_load.npy` |
| Classify | `classify.py`, then `final_classify.py` | `features_all.csv` | `v_scored.pkl`, `classification.csv` |
| Segment | `segment2.py`, `charts.py`, `class_charts.py` | `features.csv` | segment labels, `customer_segments.csv`, segment tables, figures |
| Battery | `events.py`, `battery_sim.py`, `rank.py`, `program.py`, `seg_tech.py`, `p3_charts.py` | `kwh.npy`, `classification.csv`, `system_load.npy` | `battery_sim.csv`, `ranked.pkl`, `program_scenarios.csv` |
| 2030 transformers | `ewu_inputs.py`, `ewu_sim.py`, `ewu_sim_bo.py`, `ewu_sim_bo2.py`, `ewu_sim_smart.py`, `ewu_econ.py` | `kwh.npy`, `classification.csv` | `ev_start_pmf.npy`, `hp_increment.npy`, scenario results |

Settings and their status (confirmed by Avangrid, assumed by the team, or open) are in `config.yaml`.

**What a reader should know**
- The scripts run from one working folder and read the meter data from a local path (see `run.sh`); the data itself
  is not in this repo (see `../README.md`).
- Three inputs are not written by any script here and were made in an interactive session: the empty `kwh.npy`
  file that `ingest.py` fills, `weather_raw.csv` (the weather sheet as a CSV), and `features_all.csv` (the merged
  feature table that `classify.py` reads).
  The final counts were checked against her saved outputs, not rerun end to end from this folder.
- The transformer scripts (`ewu_sim*.py`) are her version of the 2030 test. The repo's engine (`../ewu/`) reruns the
  same method on the full data and is the source of every transformer and money number in the final results.
