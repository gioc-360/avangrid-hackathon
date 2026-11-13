# What the data is really saying: Avangrid AMI hackathon (skills run)

All numbers are computed from 25,653 homes x 8,760 hours (1 Sep 2025 to 31 Aug 2026) unless the line says ASSUMPTION.

## 1. What the data is really saying

1. **Electric heat is the hidden winter load.** 2,873 homes (11.2%) use at least 3,000 kWh a year of weather-driven heating. The utility's heat-pump list implies only about 240 heat pumps in our data, and only 24 of the 60 listed heat pumps fall in this group, so about 2,780 electric-heat homes appear on no list. The winter-peaking segment that contains them is 24% of homes but carries **50.5% of load at the winter system peak**.
2. **About half of the EV list does not charge at Level 2 at home.** 69 of the 140 listed EV homes never show a block of 6 kWh or more on any mild day. The best rule finds 28% of listed EVs (95% CI 21-36%), and 431 homes that are not on the list show the same night-time Level 2 signature.
3. **Solar is the one class that load data identifies well.** Against the complete PV list, the rule scores **91.8% recall (CI 88-94%) and 88.4% precision**. It also finds 38 solar-shaped homes that are not on the list. Only 3 homes show an evening zero that would suggest a solar-plus-battery system.
4. **Weather drives the summer peak, so thermostats should come before batteries.** Weather-driven load is 31.4 MW of the 55.9 MW summer system peak (56%). A program that sheds half of that load (ASSUMPTION) would yield about 15.7 MW, more than the 11.9 MW that batteries in all 4,663 summer-peaker homes would deliver.
5. **A battery that cannot export is limited by the home's load.** At the median, a home draws only 1.97 kW at the summer peak and 1.13 kW at the winter peak. The second unit therefore adds 0.5 kW in summer and 0.09 kW in winter at the median. If export is allowed, 2 units deliver 3.63 kW at every home.
6. **The battery's real job is enabling electrification.** An unmanaged 7.2 kW Level 2 charger breaks the 3 kVA rule at 99.2% of homes that have no EV today, and 84% would still break it if charging moved overnight. One battery unit brings 57% of homes within the rule, and two units bring 100%.
7. **Capacity and time-of-use value alone do not pay for the batteries.** In tier T1 (840 homes, 2.7 MW of coincident relief), value is about $0.53M a year against $14-20M of capital, a 26-38 year payback against a 15-year warranty (all dollar inputs are ASSUMPTIONS). The business case has to come from avoided service and transformer upgrades, or from paying for export.

## 2. Part 1: Classification

**Method.** Each class has one physics rule, and each rule names the load shape it catches (`03_classify.py`). For EV and heat pump there is also a positive-unlabeled gradient-boosting model (5-fold, out-of-fold scores, 2 seeds).

**Validation.** Labels are positive-only, and the brief says they are a random 25% of positives. Under that assumption, P(labeled | flagged) = precision x 0.25, which gives:
- precision_hat = 4 x labeled_in_flag / flagged
- recall = labeled_in_flag / labeled_total, with a Jeffreys 95% interval

PV labels are the complete list, so PV precision is measured directly. For EV and heat pump, precision_hat counts only homes on the utility's list as true. It is a **lower bound**, because a real EV that is missing from the list counts as a false positive.

| Class | Rule (signature) | Flagged | Labeled recall (95% CI) | Precision_hat | Confidence |
|---|---|---|---|---|---|
| Solar PV | summer midday hours at exactly 0 >= 5%, and 5 points above summer-night zeros; winter evenings not zero | 328 (1.3%) | 0.92 (0.88-0.94) | **0.88 measured** | High |
| Solar + battery | PV, and summer 19-23 h at zero >= 30% | 3 | n/a | n/a | Low (n=3) |
| EV Level 2 | >= 8 of 119 weather-neutral days (55-70 F) with a >= 6 kWh block above the day's 20th percentile, and >= 60% of blocks starting 18:00-03:59 | 470 (1.8%) | 0.28 (0.21-0.36) | >= 0.33 | Medium |
| EV Level 2, High | rule AND in the model's top 560 | 254 | 0.25 (0.18-0.33) | >= 0.55 | High |
| EV Level 1 | >= 30 nights with a 1.0-2.2 kW lift held 5+ hours, no Level 2 blocks | 383 | 0.11 (0.07-0.18) | >= 0.17 | Low |
| EV model alone | top 560 by out-of-fold score (AUC 0.78) | 560 | 0.36 (0.29-0.45) | >= 0.36 | Medium |
| Electric heat (any) | heat_kWh_yr >= 3,000 and cold-hour lift >= 1.5 kW | 2,873 (11.2%) | 0.40 (0.28-0.53) | n/a, see finding 1 | High that heat is electric |
| Heat pump | electric heat, and (cold slope / mild slope >= 1.5, or cools with winter ratio < 2.5) | 1,572 | 0.30 (0.20-0.42) | >= 0.05 | Low (split) |
| Resistance heat | electric heat, not heat-pump-like | 1,301 | 0.10 of listed HPs land here | n/a | Low (split) |
| Central AC | hot-hour lift >= 1.5 kW and cooling slope >= 1 kWh/CDD | 8,287 (32%) | no labels | n/a | Medium |
| Room AC | hot-hour lift 0.5-1.5 kW | 9,627 (38%) | no labels | n/a | Low-Medium |
| Pool | June 15-Aug daytime floor +0.6 kW and +8 kWh/day vs spring/fall days at the same temperature | 1,633 (6.4%) | no labels | n/a | Medium |
| Hot tub | >= 30 isolated night spikes >= 2.5 kWh, >= 25% of them in winter | 189 | no labels | n/a | Low |
| Electric water heat | >= 40 morning spikes, base >= 15 kWh/day | 423 | no labels | n/a | Low |
| Seasonal home | lowest month < 15% of highest month | 2,455 (9.6%) | n/a | n/a | High (shape) |
| Dead or vacant meter | < 300 kWh/yr | 163 | n/a | n/a | High |
| Always-on base | load factor >= 0.5 and base >= 1.5 kW | 2 | n/a | n/a | High (n=2) |

**Heat-pump labels do not separate well from other homes.** The model's out-of-fold AUC is 0.69, but its top 240 contains only 2 listed heat pumps. 29 of the 60 listed heat pumps show less than 1,500 kWh a year of weather-driven heat. The list therefore looks mostly like supplemental mini-splits, not whole-home heating. Fig 2 shows the heat-pump and resistance curves nearly overlapping, so the split between them is reported as Low confidence.

**The first EV rule was revised.** It overlapped electric heat on 331 homes, because cold April and October days produced heating blocks. Restricting the count to weather-neutral days and requiring a night start raised list precision from 0.19 to 0.33 (`02b_ev_neutral.py`).

## 3. Part 2: Segmentation

**Method.** k-means on each home's 72-point shape: its 24-hour profile in winter, shoulder and summer, divided by its own mean load. Log annual kWh is added, standardized. Dead meters and spike outliers are dropped. k was chosen by silhouette on a 6,000-home sample. Silhouette falls steadily from **0.22 at k=3 to 0.13 at k=9**, so load shapes form a continuum and only 3 groups are well supported. Split-half stability is high (ARI 0.948). The classes from Part 1 are then laid over each segment as program tags.

| Segment | Homes | Median kWh/yr | Load at winter / summer system peak (kW) | Share of winter / summer system peak | Tags | Utility action |
|---|---|---|---|---|---|---|
| Summer-peaking (AC) | 11,935 (46.8%) | 7,463 | 1.19 / 2.75 | 39.3% / **62.7%** | 11% pool, 0 electric heat | Smart-thermostat DR; these homes form most of the T3 battery tier |
| Small, low-use | 7,385 (29.0%) | 3,098 | 0.51 / 0.91 | 10.2% / 13.4% | 11% seasonal | Leave out of DR; electrification-readiness outreach |
| Winter-peaking (electric heat) | 6,170 (24.2%) | 11,500 | 2.86 / 1.88 | **50.5%** / 23.9% | 46.5% electric heat, 18% seasonal | Winter peak planning; heat-pump conversion of resistance homes; battery tier T1 |

Labels are spread unevenly across segments (chi-square p < 1e-6 for all three), but the effect is small (Cramer's V 0.03-0.08). Segments describe load shape, not technology.

## 4. Part 3: Battery and demand flexibility

**Formulas (`06_battery.py`).**
- Usable AC energy per unit: E_ac = 10.08 x sqrt(0.894) = 9.53 kWh. Power P = 3.84 kW per unit.
- Coincident relief on an event day with system-top hours H_d: r_h = min(L_h, P, E_ac / |H_d|), averaged over the 20 top system hours in each season.
- Own-peak shave: the smallest threshold T such that, on every day, sum of max(L - T, 0) <= E_ac and max(L - T) <= P (found by binary search).
- Daily shift from 16:00 to 21:00: s_d = min(sum of min(L, P), E_ac).
- Sizing: a 2nd unit is added only if it adds at least 1 kW of coincident relief (22.9% of homes).
- Candidate gate: load at system peak >= 3 kW, persistence >= 0.5 (the home is in its own top 10% of hours in at least half of the 40 system-top hours), and not a seasonal home.

| Tier | Homes | % with 2 units | Median relief at system peak (kW) | Total relief (MW) | Median own-peak shave (kW) | Median shift (kWh/yr) | Median value ($/yr, ASSUMPTIONS) |
|---|---|---|---|---|---|---|---|
| T1 electrified peaker (EV Level 2 or electric heat) | 840 | 87 | 3.33 | 2.70 | 4.10 | 3,734 | 638 |
| T2 solar + storage | 310 | 21 | 1.37 | 0.52 | 3.48 | 1,809 | 284 |
| T3 summer peaker (DR first) | 4,663 | 64 | 2.84 | 11.89 | 3.37 | 2,542 | 478 |

- **Solar charging.** Solar homes have a median of 139 days with 3 or more midday zero hours. On those days, 1 unit could move a median 616 kWh a year of evening load onto stored solar. Export volume is not visible in the data, which shows export as 0.
- **Flexibility without a battery (`06b_flex.py`).** Shedding half of central-AC load would give 9.1 MW in summer. Shedding half of electric-heat load would give 4.9 MW in winter.
- **Prioritisation.**
  1. Thermostat and managed-charging DR for all segment-0 and T3 homes.
  2. Batteries for T1 homes where a feeder or service upgrade is pending.
  3. Batteries at T2 homes, paired with time-of-use rates.
  4. Export-enabled VPP mode, which more than doubles relief per battery.
- **[NET] line, ASSUMPTIONS.** T1 needs about 1,570 units. At $9,000-13,000 per unit installed, that is $14.1-20.4M of capital against $0.53M a year of value, a 26-38 year simple payback. A battery pays back only where it avoids a service or transformer upgrade, or where its export is paid for.

## 5. Charts

- `fig1_ev_profiles.png`: hourly load on weather-neutral days. Listed EV homes the rule flags show a night charging hump. The 101 listed homes it misses look like the average home. The 431 unlisted homes the rule flags look like the flagged listed EVs.
- `fig2_temp_response.png`: median daily kWh against daily mean temperature for four groups. Electric heat runs about 4x above other homes at 0 F. The heat-pump and resistance curves nearly coincide, and the utility's heat-pump list sits about halfway between electric-heat and other homes.
- `fig3_segments.png`: small multiples of the three segment centroids (kW) by season, with the other segments ghosted.
- `fig4_battery_relief_cdf.png`: distribution of per-home relief at the summer peak for 1 unit, 2 units, and 2 units with export. Relief is limited by each home's load.

## 6. Surprises, doubts, next checks

**Surprises**
- The utility's EV and heat-pump lists describe the load data poorly.
- 2,780 electric-heat homes appear on no list.
- Batteries are capped by home load, not by battery size.
- The winter system peak fell on 25 January from 11:00 to 18:00, a midday block that suggests a storm or holiday event and not an evening peak.

**Least sure of**
- The heat-pump vs resistance split.
- Hot tub and water heater, which have no labels and rest on a spike heuristic.
- All dollar values.
- Whether the 25% labels are a random sample (SCAR), since every precision_hat depends on it.
- Hourly averages, which hide 15-minute peaks. kVA headroom is therefore understated, and the enablement result is optimistic.

**Next checks**
- Validate the 431 unlisted EV homes and 38 unlisted solar homes against DMV registrations and interconnection records.
- Get gas-service flags to confirm the electric-heat homes.
- Map homes to transformers to measure real capacity headroom.
- Model 15-minute interval data.
- Recover the 10,072 homes the data defect dropped.
- Price the battery value against NYSEG and RG&E tariffs and avoided-cost studies.

## 7. Assumptions

1. The labels are a random 25% of true positives (the challenge statement's hint), which gives the factor of 4 in precision_hat. The EV list implies 560 EVs in our data and the heat-pump list implies 240.
2. Weather-neutral days are those with a daily mean of 55-70 F. Shoulder months are April, May, September and October.
3. Signature thresholds come from physical ratings, not from fitting to the labels:
   - Level 2 EV, 6 kWh block: from typical 6-7.7 kW chargers.
   - Level 1 EV, 1.0-2.2 kW: from 1.4-1.9 kW chargers.
   - Electric heat: 3,000 kWh/yr.
   - Pool pump: 0.6 kW floor.
   - Spike: 2.5 kWh.
4. Battery:
   - All 10.08 kWh is usable.
   - Losses are split evenly between charge and discharge (sqrt of round-trip efficiency).
   - No export unless stated.
   - Recharge happens within the same day.
   - kW is treated as kVA (power factor 1).
5. The 3 kVA rule is read as: new peak <= old peak + 3 kVA. The EV test uses a 7.2 kW charger running 2 hours a day.
6. Dollar inputs are unverified placeholders, not sourced. Check them against NYSEG and RG&E tariffs, NYISO ICAP prices and avoided-cost studies.
   - Avoided capacity: $100/kW-yr.
   - Peak/off-peak spread: $0.10/kWh.
   - Retail rate: $0.20/kWh.
   - Installed cost: $9,000-13,000 per unit.
7. Thermostat DR sheds 50% of weather-driven load at the peak.
8. Segment size weight: log kWh is scaled x3, giving size about as much weight as 9 shape dimensions.
9. Missing customers (10,072) are assumed to look like the 25,653 we have.

## 8. Which skill shaped which decision

- **hackathon**
  - Read the rubric first. Analytics & Modeling (35%) asks for classification accuracy and transparency, which led to a validation table per class. Business Value (40%) asks for impact quantification, which led to MW, kWh and $ per tier.
  - The skill's [NET] rule forced the capital-vs-value payback line that turned out to be finding 7.
- **stat-test**
  - Used the SCAR identity for precision with positive-only labels, Jeffreys intervals on recall, and out-of-fold AUC.
  - Picked k by silhouette, not by preference. The skill's rule was to take k=6 unless another k was clearly better. k=3 won by more than 0.02, so k=3 was used and the low silhouette is reported.
  - Tested split-half stability (ARI) and ran chi-square with Cramer's V for label enrichment by segment.
  - Ran the per-feature Mann-Whitney AUC check (`00`).
- **data-display**
  - Labels go directly on the lines, with no legends.
  - The other segments are ghosted behind each small multiple, and every axis carries its unit.
  - The Phase 5 integrity check caught a false title: "diminishing returns" on a nearly straight supply curve. That chart was replaced with the CDF in Fig 4.
  - The table test kept tier and validation numbers in tables, not charts.
