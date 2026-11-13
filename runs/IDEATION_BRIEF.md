# Ideation brief (identical for all 20 teams)

## Event
Avangrid (Iberdrola; NYSEG, RG&E in NY, CMP in Maine, UI in CT; "over 3 million customers") Energy Innovation Hackathon.
Virtual. Team of 3. Submission: PowerPoint deck + GitHub repo (code or Excel model), due 5pm ET 2026-11-13 (about 29 hours from now).
"You will only be scored on your slide deck." Top 5 present virtually 11-19. Prizes $5k / $2.5k / $1k.
Our team's hack is software.

## Challenge (read the full PDFs if useful)
- `pdftotext -layout "/Users/giocaballero/Downloads/00_Hackathon Materials/Challenge Statement.pdf" -`
- `pdftotext -layout "/Users/giocaballero/Downloads/00_Hackathon Materials/Scoring Rubric.pdf" -`
Part 1 classify end uses from hourly AMI + weather (EV L1/L2, AC, resistance heat, heat pumps, water heaters, pools,
hot tubs, solar+battery, other). Part 2 segment customers. Part 3 demand-flex + behind-the-meter battery (2x Enphase IQ 10C:
20.16 kWh, 7.68 kW) candidates, sizing, quantified value; 200 A service should not take >~3 kVA added load without study.
Code deliverable: "Tool applied to hourly loads that will estimate inventory of heating and cooling appliances, and identify
customers eligible for utility programs, BESS, etc." Considerations include scaling to millions of customers.

## Rubric
Solution & Business Value 40% | Analytics & Modeling 35% | Presentation & Communication 15% | Innovation & Creativity 10%
| each judge may give 1 bonus point (novel customer insights, highly effective appliance ID, innovative BESS prioritization,
improves planning/electrification programs, technical sophistication + business value).

## Judges (Avangrid staff)
Program Director Load Research; Senior Manager Clean Energy Policy - Energy Storage; Customer Programs & Products Manager;
Director Advanced Load Forecasting; Data Engineer; Director Reliability & Tech Processes; Senior Director Technology,
Innovation & Quality; Director Regulatory Affairs NY; Senior Director Talent Development.

## What we already have (built today, all numbers computed from the data)
A working pipeline: ingest (20 s for 25,653 homes x 8,760 hours) -> features -> per-class rules + positive-unlabeled models
-> segments -> battery ranking/sizing/3 kVA test -> self-checking repo (every number on a slide must trace to code; every
quote to a source page). Data defect: 10,072 of 35,725 customers missing (a zip repeats another).
Key computed facts (facts/facts.json; assumption.* = unverified placeholder prices):
- assumption.capacity_value_usd_kw_yr = 100.0 $/kW-yr
- assumption.thermostat_shed_pct = 33 %
- assumption.tou_off_peak_usd_kwh = 0.18 $/kWh
- assumption.tou_on_peak_usd_kwh = 0.3 $/kWh
- assumption.unit_cost_high_usd = 13000 $ per IQ 10C installed
- assumption.unit_cost_low_usd = 9000 $ per IQ 10C installed
- bess.bill_savings_per_home_usd_yr = 359 $/yr
- bess.bill_savings_usd_yr = 1497000 $/yr
- bess.candidates.count = 4079 homes
- bess.candidates.share_pct = 15.9 % of homes
- bess.capacity_relief_mw = 14.86 MW
- bess.capacity_relief_pct_of_event_load = 29.1 % of summer event-hour system load
- bess.capacity_relief_winter_mw = 11.32 MW
- bess.capacity_value_usd_yr = 1704000 $/yr
- bess.capex_high_usd_m = 106.1 $M
- bess.capex_low_usd_m = 73.4 $M
- bess.electrification_enabled.count = 22346 homes
- bess.electrification_enabled.ev_homes = 22346 homes
- bess.electrification_enabled.hp_homes = 672 homes
- bess.event_window_summer_hours = 16:00-20:00 on the top day
- bess.event_window_winter_hours = 17:00-21:00 on the top day
- bess.headroom_rule.ev_fail_pct_none = 99.3 % of homes without an EV
- bess.headroom_rule.ev_pass_pct_none = 0.7 % of homes without it today
- bess.headroom_rule.ev_pass_pct_one_unit = 56.6 % of homes without it today
- bess.headroom_rule.ev_pass_pct_two_units = 100.0 % of homes without it today
- bess.headroom_rule.hp_kw_at_0f = 3.06 kW
- bess.headroom_rule.hp_kw_per_degf = 0.051 kW per F below 60F
- bess.headroom_rule.hp_pass_pct_none = 96.8 % of homes without it today
- bess.headroom_rule.hp_pass_pct_one_unit = 100.0 % of homes without it today
- bess.headroom_rule.hp_pass_pct_two_units = 100.0 % of homes without it today
- bess.load_shift_kwh_per_home = 3643 kWh/yr
- bess.load_shift_mwh_yr = 15172.0 MWh/yr
- bess.peak_reduction_kw = 4.2 kW
- bess.peak_reduction_pct = 48.3 % of own annual peak
- bess.relief_per_home_kw = 4.17 kW
- bess.simple_payback_high_yr = 33.0 years
- bess.simple_payback_low_yr = 23.0 years
- bess.size.median_second_unit_gain_kw = 1.8 kW
- bess.size.one_unit = 0 homes
- bess.size.two_units = 4079 homes
- bess.solar_charge_days = 127 days/yr
- bess.solar_charge_share = 0.348 share of days
- bess.supply_curve.top1000_summer_mw = 2.72 MW
- bess.supply_curve.top1000_winter_mw = 4.43 MW
- bess.supply_curve.top2000_summer_mw = 6.49 MW
- bess.supply_curve.top2000_winter_mw = 7.45 MW
- bess.supply_curve.top500_summer_mw = 1.42 MW
- bess.supply_curve.top500_winter_mw = 2.25 MW
- bess.tier.T1_electrified_peaker.count = 1491 homes
- bess.tier.T1_electrified_peaker.summer_mw = 4.4 MW
- bess.tier.T1_electrified_peaker.winter_mw = 5.98 MW
- bess.tier.T2_solar_storage.count = 6 homes
- bess.tier.T2_solar_storage.summer_mw = 0.02 MW
- bess.tier.T2_solar_storage.winter_mw = 0.01 MW
- bess.tier.T3_grid_peaker.count = 2582 homes
- bess.tier.T3_grid_peaker.summer_mw = 10.43 MW
- bess.tier.T3_grid_peaker.winter_mw = 5.33 MW
- bess.units_total = 8158 IQ 10C units
- class.ac.confidence = high
- class.ac.count = 17556 homes
- class.ac.share_pct = 68.4 % of homes
- class.ac_central.confidence = medium
- class.ac_central.count = 8287 homes
- class.ac_central.share_pct = 32.3 % of homes
- class.electric_heat.confidence = high that heat is electric
- class.electric_heat.count = 2873 homes
- class.electric_heat.labeled_hits = 24 labeled homes
- class.electric_heat.recall_pct = 40.0 % of labeled
- class.electric_heat.sensitivity_high = 4143 homes
- class.electric_heat.sensitivity_low = 2873 homes
- class.electric_heat.share_pct = 11.2 % of homes
- class.ev.implied_total = 560 homes
- class.ev.l2_listed_owners_found = 172 homes
- class.ev.l2_precision_floor_pct = 30.5 %
- class.ev.l2_unlisted = 392 homes
- class.ev.labeled_no_home_l2_pct = 51.4 % of labeled EVs
- class.ev.pu_auc = 0.79 AUC
- class.ev.recall_heldout = 30.7 % of labeled EVs
- class.ev_l1.confidence = low: dehumidifiers and well pumps look alike
- class.ev_l1.count = 1663 homes
- class.ev_l1.labeled_hits = 18 labeled homes
- class.ev_l1.recall_pct = 12.9 % of labeled
- class.ev_l1.share_pct = 6.5 % of homes
- class.ev_l2.confidence = high
- class.ev_l2.count = 564 homes
- class.ev_l2.labeled_hits = 43 labeled homes
- class.ev_l2.recall_pct = 30.7 % of labeled
- class.ev_l2.share_pct = 2.2 % of homes
- class.heat_pump.confidence = low: listed HP homes and resistance homes share one kW-vs-temperature curve
- class.heat_pump.count = 1231 homes
- class.heat_pump.labeled_hits = 10 labeled homes
- class.heat_pump.labeled_little_heat_pct = 48.3 % of labeled HPs
- class.heat_pump.pu_auc = 0.718 AUC
- class.heat_pump.recall_heldout = 16.7 % of labeled HPs
- class.heat_pump.recall_pct = 16.7 % of labeled
- class.heat_pump.share_pct = 4.8 % of homes
- class.hot_tub.confidence = low, no labels
- class.hot_tub.count = 181 homes
- class.hot_tub.share_pct = 0.7 % of homes
- class.other_flat_large.confidence = medium
- class.other_flat_large.count = 5 homes
- class.other_flat_large.share_pct = 0.0 % of homes
- class.other_inactive.confidence = high
- class.other_inactive.count = 163 homes
- class.other_inactive.share_pct = 0.6 % of homes
- class.other_seasonal.confidence = high (shape)
- class.other_seasonal.count = 2455 homes
- class.other_seasonal.share_pct = 9.6 % of homes
- class.pool.confidence = medium
- class.pool.count = 1474 homes
- class.pool.share_pct = 5.7 % of homes
- class.resistance_heat.confidence = low (the remainder of electric heat)
- class.resistance_heat.count = 1642 homes
- class.resistance_heat.share_pct = 6.4 % of homes
- class.solar.confidence = high
- class.solar.count = 335 homes
- class.solar.labeled_hits = 288 labeled homes
- class.solar.precision_pct = 86.0 %
- class.solar.recall_heldout = 91.1 % of known PV
- class.solar.recall_pct = 91.1 % of labeled
- class.solar.share_pct = 1.3 % of homes
- class.solar.undisclosed = 47 homes
- class.solar_battery.confidence = low (tiny n)
- class.solar_battery.count = 0 homes
- class.solar_battery.share_pct = 0.0 % of homes
- class.water_heater.confidence = low, no labels
- class.water_heater.count = 441 homes
- class.water_heater.share_pct = 1.7 % of homes
- class.weather_gain.ev_auc_points = 1.0 AUC points
- class.weather_gain.ev_auc_without_weather = 0.78 AUC
- class.weather_gain.heat_pump_auc_points = 4.2 AUC points
- class.weather_gain.heat_pump_auc_without_weather = 0.676 AUC
- data.customers_missing = 10072 customers
- data.customers_present = 25653 customers
- data.customers_promised = 35725 customers
- data.rows_read = 223319163 hourly readings
- flex.ac_weather_load_mw = 30.1 MW
- flex.reduction_kw = 0.5 kW per AC home
- flex.thermostat_mw = 9.9 MW
- insight.electric_heat_home_share_pct = 11.2 % of homes
- insight.electric_heat_winter_peak_share_pct = 31.9 % of winter top-100h load
- insight.heat_conversion_added_kw_at_winter_peak = 3.29 kW per home
- insight.homes_to_flip_winter_peaking = 5100 homes
- insight.kmeans_silhouette_k3 = 0.122 silhouette
- insight.kmeans_silhouette_k6 = 0.064 silhouette
- insight.seasonal_winter_peak_share_pct = 12.2 % of winter top-100h load
- insight.share_to_flip_winter_peaking_pct = 19.9 % of homes
- insight.summer_minus_winter_mw = 16.8 MW
- insight.system_peak_mw = 59.4 MW
- insight.system_peak_temp_f = 92.0 F
- insight.system_peak_when = 2026-07-02 17:00:00
- insight.winter_peak_mw = 42.6 MW
- insight.winter_peak_temp_f = 2.1 F
- insight.winter_peak_when = 2026-02-08 17:00:00
- scale.ingest_seconds = 18.6 s
- scale.matrix_gb = 1.25 GB
- seg.baseline.count = 11602 homes
- seg.baseline.median_kwh = 4335 kWh/yr
- seg.baseline.share_pct = 45.2 % of homes
- seg.baseline.summer_peak_share_pct = 27.9 % of summer top-100h load
- seg.baseline.winter_peak_share_pct = 23.8 % of winter top-100h load
- seg.dual_electrified.count = 79 homes
- seg.dual_electrified.median_kwh = 23705 kWh/yr
- seg.dual_electrified.share_pct = 0.3 % of homes
- seg.dual_electrified.summer_peak_share_pct = 0.6 % of summer top-100h load
- seg.dual_electrified.winter_peak_share_pct = 1.1 % of winter top-100h load
- seg.electric_heat.count = 1941 homes
- seg.electric_heat.median_kwh = 15008 kWh/yr
- seg.electric_heat.share_pct = 7.6 % of homes
- seg.electric_heat.summer_peak_share_pct = 9.0 % of summer top-100h load
- seg.electric_heat.winter_peak_share_pct = 21.1 % of winter top-100h load
- seg.emerging.count = 3573 homes
- seg.emerging.median_kwh = 8359 kWh/yr
- seg.emerging.share_pct = 13.9 % of homes
- seg.emerging.summer_peak_share_pct = 14.8 % of summer top-100h load
- seg.emerging.winter_peak_share_pct = 14.6 % of winter top-100h load
- seg.ev_home.count = 397 homes
- seg.ev_home.median_kwh = 15391 kWh/yr
- seg.ev_home.share_pct = 1.5 % of homes
- seg.ev_home.summer_peak_share_pct = 3.5 % of summer top-100h load
- seg.ev_home.winter_peak_share_pct = 2.6 % of winter top-100h load
- seg.inactive.count = 163 homes
- seg.inactive.median_kwh = 65 kWh/yr
- seg.inactive.share_pct = 0.6 % of homes
- seg.inactive.summer_peak_share_pct = 0.0 % of summer top-100h load
- seg.inactive.winter_peak_share_pct = 0.0 % of winter top-100h load
- seg.seasonal.count = 2455 homes
- seg.seasonal.median_kwh = 5496 kWh/yr
- seg.seasonal.share_pct = 9.6 % of homes
- seg.seasonal.summer_peak_share_pct = 5.3 % of summer top-100h load
- seg.seasonal.winter_peak_share_pct = 12.2 % of winter top-100h load
- seg.solar.count = 267 homes
- seg.solar.median_kwh = 7222 kWh/yr
- seg.solar.share_pct = 1.0 % of homes
- seg.solar.summer_peak_share_pct = 0.7 % of summer top-100h load
- seg.solar.winter_peak_share_pct = 1.4 % of winter top-100h load
- seg.summer_peaker.count = 5176 homes
- seg.summer_peaker.median_kwh = 10255 kWh/yr
- seg.summer_peaker.share_pct = 20.2 % of homes
- seg.summer_peaker.summer_peak_share_pct = 38.2 % of summer top-100h load
- seg.summer_peaker.winter_peak_share_pct = 23.1 % of winter top-100h load

## Outside facts you may cite (page-verified in checks/citations.yaml)
- ACEEE 2020: "Hourly data can identify loads that correlate with outdoor temperature (like HVAC), continuous loads, and
  time-dependent loads (like pool pumps...)"; targeting on AMI features: top half saved "nearly 3.5 times more".
- DOE AMI report 2019: "three customers buy a Tesla" -> transformer load triples; SMUD: up to 17% of transformers may need
  upgrades from EVs; SCE thermostat DR 51,000 customers, 37 MW per event.
- NREL 2024 AMI classifier (AC, electric heat, water heat) + ResStock matching: 16.6% median monthly CV-RMSE.
- Vermont Green Mountain Power (via a write-up of a BBC piece): batteries in 5,500+ homes, ~110 MW, $55/month lease.
- IBISWorld T&D 2026: residential customers cutting use "primarily because of higher utility bills"; peak forces operators
  to "invest in excess capacity"; EVs will "require targeted network and transmission upgrades".
- House Rpt 116-474: law asks for "measuring peak load reductions" from smart metering, DR, storage.
- RMI 2025: aggregate 2035 demand forecasts in utility plans up "over 20 percent"; overbuilding cost almost $2 billion.
- Avangrid investing cash $2.5B (FY22) -> $4.2B (TTM Sep-24) (PitchBook).
