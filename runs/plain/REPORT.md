# What 25,653 homes' hourly meters say (plain analyst run)

Run the scripts in order with `.venv/bin/python -I runs/plain/NN_*.py`. Intermediate files land in `out/`.

## 1. What the data is really saying

1. **Air conditioning sets the system peak, which comes in summer.** The top 100 summer hours average 48.4 MW, against 38.3 MW in winter. The annual peak was 59.4 MW on 2026-07-02. The 18.5% of homes in the "summer peak contributor" segment supply 34.6% of the summer peak.
2. **Electric heat drives the winter peak and future growth.** 11.1% of homes (the electric-heat segment) supply 25.7% of the winter peak. Across all homes, 16.2% (4,143) show a clear electric-heating response to cold.
3. **Most homes on the EV list show no Level 2 charging at home.** Only 41 of 140 labeled EV homes (29%) show the high-confidence L2 signature, and the median labeled EV home has zero L2 days. The list marks "likely EV owners", not "home L2 chargers". Load data alone can find at most about 39% of them.
4. **About 290 homes charge like EV owners but are not on the utility's list.** 455 homes show unmistakable L2 charging. The list accounts for only about 164 of them (41 labeled hits ÷ the 25% sampling rate).
5. **Solar is easy to find, but almost no solar home has a battery.** Detection catches 288 of 316 labeled PV homes (91%) and finds 50 unlisted ones. Only 1 home shows meter zeros that last after dark, which is the battery signature.
6. **About 1 in 10 meters (2,493) is seasonal or part-year.** These homes have 2 or more months near zero, yet hold 12.5% of the winter peak. They distort per-customer forecasts and should be left out of battery and demand response (DR) targeting.
7. **One battery unit (20.16 kWh, 7.68 kW) at 1,958 "tier A" homes (7.6% of customers) gives 5.6 MW of summer and 5.9 MW of winter relief at system-peak hours.** That is 11 to 15% of the top-100-hour peak. The same unit keeps an unmanaged Level 2 EV within the 3 kVA rule at 99.5% of homes. A typical heat pump needs no battery at all to stay under 3 kVA in 86% of homes without electric heat, because their annual peak already comes from summer AC.

## 2. Part 1: classification

Each class is flagged from a physical signature in the 8,760-hour load matrix plus weather. Feature definitions are in `analysis/features.py` and `02_extra_features.py`; thresholds are in `06_classes.py`.

For EV and heat pump (HP), `03_classify.py` also trains a positive-unlabeled model. It is gradient boosting of labeled against unlabeled homes, scored out-of-fold (5 folds, 3 repeats).

Each classifier is validated by its recall on labeled homes against the flag rate among all other homes (`fig1`).

| Class | Rule (key formula) | Flagged (n, % of 25,653) | Label recall | Confidence and why |
|---|---|---|---|---|
| Solar PV | summer 10-14h share of hours at exactly 0 ≥ 5%, night (0-4h) zeros ≤ 2%, meter not mostly zero | 338 (1.3%); 291 high (≥20% midday zeros) | 288/316 = 91% | High: exported solar shows as exact zeros only at midday. 50 unlabeled hits are new PV. 28 labeled PV homes never hit 0 (small systems, or not installed) |
| Solar + battery | PV home with ≥25% zero hours at 21-23h (May-Aug) | 1 | n/a | Low: a battery would extend the zeros past dark, and almost no one shows this |
| EV Level 2 | ≥20 days with 2+ consecutive hours ≥ 6 kW above the day's 25th-percentile hour; ≥50% of them start 17-03h; ≥5 such days in mild months | 455 high + 539 medium (top 560 on the model score, or ≥10 such days) = 994 (3.9%) | high 29%; any 39% (base rate 3.7%) | High for the 455, whose charging blocks are unmistakable (`fig2`). Medium for the rest. Model: AUC 0.79, recall in its top 560 is 33% |
| EV Level 1 | ≥30 mild-month nights with a 1.0-2.5 kW lift held 4+ h, no L2 | 1,114 (4.3%) | 11% (2.5x base rate) | Low: dehumidifiers, well pumps and heat tape look the same |
| Air conditioning | b_cool ≥ 0.5 kWh/CDD-day and hot-hour lift ≥ 0.5 kW | 17,556 (68%); 9,312 high (≥1.5 and ≥1.0) | none | High: cooling slope from the weather regression below |
| Electric heat (any) | heat_kWh_yr ≥ 2,000 and cold-hour lift ≥ 1.0 kW | 4,143 (16.2%); 1,969 high (≥5,000 kWh) | 45% (2.8x base) | Medium: the signal is clear, but 55% of labeled HP homes show little electric heat (likely supplemental mini-splits) |
| Heat pump vs resistance | HP-likely: electric heat + AC signature + HP model rank ≤ 2,000. Resistance-likely: ≥8,000 kWh of heat, winter/shoulder ratio ≥ 2.5, no cooling | HP-likely 887; resistance-likely 238; undetermined 3,018 | HP-likely 10% | Low: labeled HP homes and other electric-heat homes have the same kW-vs-temperature shape (`fig4`). HP model: AUC 0.70, recall in its top 240 is 5% |
| Electric water heater | ≥30 isolated 1-hour spikes ≥2.5 kWh (0-9h), not EV | 928 (3.6%) | none | Low |
| Pool | daily kWh on mild days Jun 15-Aug minus spring/fall days at the same temperature ≥ 8 kWh, and daytime (9-17h) floor up ≥ 0.5 kW | 2,148 (8.4%); 501 with ≥1.0 kW floor | none | Medium at best: comparing the same temperature in different seasons isolates the pump, but summer occupancy also raises the floor |
| Hot tub | ≥30 isolated night spikes, ≥20% of them in winter, not EV | 182 (0.7%) | none | Low |
| Seasonal / part-year | ≥60 days below 30% of the home's own median, or smallest month < 15% of largest | 2,493 (9.7%) | none | Medium: also catches move-in and move-out vacancies |
| Inactive meter | < 500 kWh/yr | 229 (0.9%) | none | High |
| Flat 24x7 large load | load factor ≥ 0.45, base ≥ 1.5 kW, ≥15,000 kWh/yr | 5 | none | Medium: possibly a business, grow operation or crypto mining |

The weather model is fit per customer over 365 days:

`kWh_day = b0 + b1·min(HDD60,25) + b2·max(HDD60−25,0) + b3·CDD65 + b4·weekend`

heat_kWh_yr is the sum of the positive part of (b1·HDDmild + b2·HDDcold) over the year.

The "25% sample" hint lets us check coverage. It implies about 560 likely-EV homes and 240 HP homes in our data. The flags recover about 164 and 108 of them (41 and 27 label hits ÷ 0.25). Load data alone therefore finds about 30 to 45% of the utility's lists.

## 3. Part 2: segmentation

The segments do not overlap: a home goes to the first one in the table that it matches. Peak share is the segment's summed kW over the season's top 100 system hours, divided by the system total (`07_segment.py`, `fig3`).

| Segment | n | % cust | Median kWh/yr | % summer peak | % winter peak | What to do |
|---|---|---|---|---|---|---|
| 0 Inactive | 229 | 0.9 | 155 | 0.0 | 0.0 | Field check; exclude from forecasts |
| 1 Seasonal / part-year | 2,493 | 9.7 | 5,542 | 5.5 | 12.5 | Forecast separately; skip battery and DR |
| 2 Solar PV | 265 | 1.0 | 7,222 | 0.7 | 1.4 | Offer solar plus storage (charge from surplus) |
| 3 Dual electrified (EV + heat) | 245 | 1.0 | 22,041 | 1.9 | 3.6 | First battery candidates; watch for service upgrades |
| 4 EV home | 575 | 2.2 | 14,048 | 4.9 | 3.7 | Enroll in managed charging; offer TOU |
| 5 Electric-heat home | 2,857 | 11.1 | 13,065 | 12.6 | 25.7 | Winter DR, weatherization, cold-climate HP upgrades |
| 6 Summer peak contributor (top-quartile summer peak-hour kW, with AC or pool) | 4,754 | 18.5 | 9,935 | 34.6 | 19.8 | Thermostat DR, pool-pump timing, battery tier A |
| 7 Emerging electrification candidate (above-median use, AC, no EV or electric heat yet) | 3,081 | 12.0 | 8,219 | 12.9 | 11.7 | Market heat pumps (they already own AC) |
| 8 Low-use / baseline | 11,154 | 43.5 | 4,270 | 26.9 | 21.7 | Reach through low-cost mass-market channels |

**Clustering check.** K-means was run on normalized day shapes (24 hours x 3 seasons = 72 points, plus log of size). Silhouette is 0.15 at k=4 and falls to 0.10 at k=10. Load shapes form a continuum rather than natural clusters, so segments built from physical flags are more defensible than clusters. The k=6 shapes in `fig7` still line up with the rule segments. For example, shape 2 (n=2,067, winter/shoulder ratio 2.95) is the electric-heat and seasonal shape.

**Flexibility at the summer peak without a battery** (`09_part3.py`):
- **AC:** homes with AC carry 24.2 MW of weather-driven load, measured as kW at peak hours minus the same hours on shoulder days. A 33% thermostat setback (an assumption) would remove about 8.0 MW.
- **Pool pumps:** 1.65 MW could be moved out of the peak.
- **EVs:** EV homes run 1.6 MW in summer and 1.2 MW in winter above their own shoulder-season profile.

## 4. Part 3: battery and flexibility

`08_battery.py` simulates every customer, hour by hour, with 1 unit (20.16 kWh, 7.68 kW) and with 2 units. Round-trip efficiency is 89.4%, there is no export, and the battery only follows the home's own load. Four quantities are computed:

- **Relief at system peak.** On each event day the battery covers `r_h = min(L_h, P)·min(1, E / Σ_day min(L_h, P))` in that day's top-100 system hours. The kW figure is the mean of r over the 100 hours.
- **Own-peak shaving.** This is the smallest annual threshold T that the battery can hold every day. On each day, `Σ(L−T)+ ≤ E` and `max L − T ≤ P`. The battery must also refill below T the same day: `Σ min((T−L)+, P)·0.894 ≥ Σ(L−T)+`. Days where the battery could not refill average 0.04 per customer, which is search tolerance.
- **Load shift.** Energy moved out of 16-20h: `Σ_days min(E, Σ_16-20h min(L,P))`.
- **Enablement.** Two new loads are added to each home. One is an unmanaged L2 EV (7.2 kW, 18-20h daily). The other is a heat pump whose kW-vs-temperature curve comes from the 27 labeled HP homes that show heating. Its median added load is 3.6 kW below 0F and 1.9 kW at 20-30F. The test is whether the battery keeps `new peak − current peak ≤ 3 kW` (3 kVA at power factor 1).

**Ranking and sizing.**
- **Tier A:** at least 2.5 kW of relief deliverable at system-peak hours, and the home's own daily peak reaches ≥ 7 kW on ≥ 10 days, so the need recurs. Inactive and seasonal homes are excluded.
- **A1 vs A2:** A1 homes also have an EV or high electric heat; A2 homes do not.
- **Size:** 2 units only if the second unit adds ≥ 1.5 kW at system peak, or the EV case needs it.
- **Value per home:** `kW_cp·$100/kW-yr + kWh_shift·($0.30 − $0.18/0.894)`. Both prices are illustrative.

| Tier | Homes | 2-unit | Own peak cut (median kW) | Summer MW | Winter MW | Shifted MWh/yr | Illustrative $/home-yr |
|---|---|---|---|---|---|---|---|
| A1 grid relief + electrified | 1,144 | 277 | 5.0 | 3.04 | 3.93 | 5,688 | 782 |
| A2 grid relief | 814 | 133 | 4.8 | 2.51 | 1.93 | 3,593 | 725 |
| B solar + storage | 229 | 0 | 3.7 | 0.25 | 0.31 | 440 | 325 |
| C electrified, lower coincidence | 804 | 1 | 3.6 | 1.37 | 1.75 | 2,357 | 524 |

**Supply curve** (`fig5`). The best 500 homes give 1.24 MW in summer and 1.78 MW in winter, about 3.7 kW each. 5,000 homes give 12.7 MW and 10.6 MW.

**Why one unit runs out of energy.** On the peak day the top-100 hours span 11:00 to 23:00, 13 hours in all. Spread across them, 20 kWh averages only about 1.5 to 2 kW (`fig6`).

**Electrification enablement**, for eligible homes that do not have the technology today:
- **Level 2 EV.** Unmanaged charging adds a median 6.7 kW and breaks the 3 kVA limit at 99.5% of homes. With 1 unit, 21,915 of 22,035 homes stay within 3 kVA (median net increase −0.9 kW).
- **Heat pump.** 17,006 homes (86%) need no battery, 2,624 (13%) fit with 1 unit, and 140 need a service study even with a battery.
- **Solar charging.** The 265 PV-segment homes have a median 137 days a year with at least 3 zero midday hours, which is surplus that could charge a battery. 73% of those days fall in April to September.

## 5. Charts
- `fig1_label_validation.png`: each classifier's recall on labeled homes against its flag rate among everyone else.
- `fig2_signatures.png`: day-by-hour heatmaps of one typical home per class (PV, L2 EV, electric heat, pool, seasonal, AC). Local only, not in git: it draws single real homes, so never use it in the video or deck.
- `fig3_segment_peak_share.png`: each segment's share of customers against its share of the summer and winter peak.
- `fig4_temp_response.png`: median kW against outdoor temperature by class. HP and electric-heat curves have the same shape.
- `fig5_battery_supply_curve.png`: cumulative MW of system-peak relief as homes are added in rank order.
- `fig6_dispatch_example.png`: the median summer tier-A home on the system peak day, before and after the battery. Local only, not in git: it draws single real homes, so never use it in the video or deck.
- `fig7_kmeans_shapes.png`: the six seasonal day-shape centroids from k-means.

## 6. Surprises, doubts, next checks

Surprises:
- **The labels are weak ground truth.** 61% of labeled EV homes show no home-charging signature, and 55% of labeled HP homes show little electric heat. That caps how good any supervised model can be.
- **Almost no solar home has a battery.** A BTM battery fleet would be new storage, not a replacement for existing storage.

Least sure:
- The heat pump vs resistance split (model AUC 0.70).
- Pools, because summer occupancy looks similar.
- Water heaters and hot tubs, which have no labels and low confidence.
- All dollar values, which rest on assumed prices.
- Own-peak shaving, which assumes perfect knowledge of each day's load in advance. Real dispatch would cut less.

Next checks:
- Get the rate and tariff data, and the feeder and transformer map so relief can be located.
- Check the 290 unlisted L2 homes against DMV or charger-rebate lists.
- Field-verify 50 sampled pool, HP and seasonal flags.
- Re-run the heat-pump addition with the 75th-percentile home instead of the median.
- Compare a targeted 4-hour event window with the 13-hour top-100 window.

## 7. Assumptions
1. The EV and HP labels are a random 25% sample of the utility's likely-EV and likely-HP lists (from the challenge text). Unlabeled does not mean negative.
2. Midday meter zeros in homes that are occupied mean exported solar (from the brief).
3. Battery: the brief defines the "unit" as 2x IQ 10C, which is 20.16 kWh, 7.68 kW continuous and 89.4% round-trip efficiency, with 1 or 2 units allowed. My own assumptions are that 100% of nameplate capacity is usable, that there is no export to the grid, and that the battery cycles daily with perfect knowledge of the day's load.
4. 3 kVA is treated as 3 kW (power factor 1, my assumption). The rule is applied to the increase in metered peak.
5. An unmanaged L2 EV draws 7.2 kW for 2 hours at 18-20h every day (my assumption, about 14 kWh/day).
6. The heat-pump addition is the median increment of 27 labeled HP homes that show heating. It is derived from the data, but the group is small and partly supplemental.
7. Capacity value of $100/kW-yr, TOU prices of $0.30 on-peak and $0.18 off-peak, and a 16-21h on-peak window are ILLUSTRATIVE and not sourced. Replace them with NYSEG/RG&E tariff and marginal-cost-of-service values.
8. The thermostat DR setback of 33% of weather-driven AC kW is illustrative and not sourced.
9. System peak means the top 100 hours of total load per season, from the 25,653 customers with data only. The file defect leaves 10,072 IDs missing.
10. Every classification threshold (6 kW block, 2,000 kWh of heat, 0.5 kW pool floor, and so on) is my choice. I set them from the distributions and from how often labeled homes cross them; none is physically verified.
