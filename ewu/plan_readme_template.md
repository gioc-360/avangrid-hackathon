# EWU engine output: showcase set

{note}.

This folder is what `bin/ewu plan --showcase` hands a planner and a programs team, for one scenario and one sizing: {scenario} 2030, transformer rating = today's peak x {margin}, {grouping} grouping, seed {seed}. The transformer counts are the same run as `bin/ewu screen` (docs/demo/cli_output.txt).

| file | rows | level | what it is |
|---|---|---|---|
| transformer_actions.csv | {rows_transformer_actions} | transformer (8-home sums) | what to do at each synthetic transformer, ranked |
| capital_plan.csv | {rows_capital_plan} | whole sample | cost of each option, present value |
| battery_hosts.csv | {rows_battery_hosts} | home, SIMULATED | which homes host batteries on each protected transformer |
| program_targets.csv | {rows_program_targets} | home, SIMULATED | which homes to enroll in which program, and why |
| simulated_homes.csv | {rows_simulated_homes} | home, SIMULATED | the simulated home index the two lists above draw from |

Actions in this run: none {n_none}, shift {n_shift}, protect {n_protect}, upgrade {n_upgrade} transformers.

Every CSV starts with one `#` line saying what it is; read with `pandas.read_csv(path, comment="#")`.

Source words used below: **measured** = computed by the engine from the hackathon hourly meter data and weather; **assumption** = a value in config/ewu.yaml marked assumption (sizing, 2030 adoption, prices); **simulated** = drawn at random from segment-level statistics; **placeholder** = a price nobody at Avangrid has confirmed.

## Privacy

The real home-level lists (real customer numbers) are written only by `bin/ewu plan --private`, only to outputs/private/plan/, which git ignores. The home files here are simulated: home ids SIM-00001 onward, segment drawn by each segment's share of all homes, annual kWh and peak kW drawn from the segment's mean and spread, each program flag drawn from the segment's eligible share. The simulator reads only those aggregates ({segments} segments, recorded in facts/facts.json under ewu.plan.showcase). A privacy guard then compares every simulated home and host with the real rows and redraws any value that happens to match one ({redrawn} values redrawn in this run). Tests check that no real customer number and no real home's (segment, annual kWh, peak kW) appears here.

## transformer_actions.csv (transformer level, measured)

| column | unit | source | meaning |
|---|---|---|---|
| transformer_id | id | synthetic | T-0001 onward; 8 real homes grouped at random, no meter-to-transformer map exists yet |
| feeder_id | id | assumption | F1 to F{feeders}: an illustrative split, transformer ids cut into equal blocks (same rule as the Network view, config network.feeders); a real feeder map replaces it |
| homes | homes | synthetic | homes on the transformer (8) |
| new_evs_2030 | homes | assumption | homes on it that add a Level 2 EV in the scenario |
| new_heat_pumps_2030 | homes | assumption | homes on it that add a heat pump in the scenario |
| today_peak_kw | kW | measured | highest hour of the 8 homes' summed metered load |
| rating_kw | kW | assumption | today_peak_kw x the sizing margin |
| limit_kw | kW | assumption | rating_kw x the overload limit (config transformer.overload_limit) |
| worst_2030_kw | kW | measured + assumption | highest hour of 2030 load: metered + new EVs charging unmanaged + new heat pumps |
| worst_2030_hour | date hour | measured | when that hour falls in the data year |
| over_limit | true/false | measured | any 2030 hour above limit_kw with unmanaged charging (the Flag step) |
| hours_over | hours per year | measured | 2030 hours above limit_kw with unmanaged charging |
| main_driver | word | measured | at the worst hour: the load that leads the overload by fair shares (base, EV, heat pump), or both when neither new load alone crosses the limit; under the limit, the larger new load |
| action | word | measured | none (within the limit), shift (staggered EV charging fixes it), protect (fit-score home batteries clear it), upgrade (nothing short of an upgrade clears it) |
| battery_hosts | homes | measured | host homes the cheapest clearing option uses (protect only) |
| units_per_host | IQ 10C units | measured | 1 or 2 per host |
| batteries_needed | units | measured | battery_hosts x units_per_host |
| est_cost_usd | $ present value | placeholder | over the transformer life at mid placeholder prices (config prices.*): shift = EV homes enrolled; protect = enrollment + batteries on equal life; upgrade = enrollment + one upgrade. The column adds up to the ladder row of capital_plan.csv, to rounding |
| priority | rank | measured | 1 = most urgent: upgrade, then protect, then shift, then none; within each, highest worst_2030_kw against limit_kw first |

A transformer can be pushed over the limit only by staggered charging (its EVs bunching into the night window); it then shows over_limit false with a protect or upgrade action, as `bin/ewu screen` reports.

## capital_plan.csv (whole sample, placeholder prices)

| column | unit | source | meaning |
|---|---|---|---|
| option | word | | upgrade_all, shift_then_upgrade, ladder (shift, protect, upgrade) |
| transformers_upgraded | transformers | measured | upgrades the option buys |
| batteries | units | measured | batteries the option installs |
| ev_homes_enrolled | homes | assumption | EV homes enrolled in managed charging |
| pv_usd_low, pv_usd_mid, pv_usd_high | $ present value | placeholder | cost over the transformer life at each price case, equal-life batteries (ewu/economics.py) |
| share_of_upgrade_all_pct_low, _mid, _high | % | placeholder | the option's cost as a share of upgrading every flagged transformer |
| prices | word | | placeholder: every price is an assumption in config/ewu.yaml |

## battery_hosts.csv (SIMULATED)

| column | unit | source | meaning |
|---|---|---|---|
| transformer_id | id | measured | a protected transformer from transformer_actions.csv; host count and units match its row |
| rank | rank | simulated | 1 = best fit on that transformer |
| home_id | id | simulated | SIM home from simulated_homes.csv |
| fit_score | share 0 to 1 | simulated | kw_cut_top_hours as a share of the battery's power |
| kw_cut_top_hours | kW | simulated | kW the battery would cut, averaged over the system's top hours; drawn from the real hosts' mean and spread for that battery size |
| units | IQ 10C units | measured | 1 or 2, as chosen for the transformer |

## program_targets.csv (SIMULATED)

| column | unit | source | meaning |
|---|---|---|---|
| home_id | id | simulated | SIM home on a transformer whose action is not none |
| transformer_id | id | measured | its transformer |
| segment | word | simulated | drawn by segment share |
| programs | list | simulated | battery host, managed charging, winter demand response, heat pump conversion, smart thermostat: the ones the home qualifies for (eligibility drawn from segment shares; rules in config programs.rules) |
| reason | phrase | | why the first program on the list applies |
| priority | rank | measured | the transformer's priority from transformer_actions.csv |

Managed charging goes to homes that already have a Level 2 charger. The new 2030 EVs in transformer_actions.csv are future buyers nobody can name today; they join managed charging when they buy or connect a charger, which is what the shift action prices.

## simulated_homes.csv (SIMULATED)

home_id, transformer_id, segment, annual_kwh (kWh, drawn), peak_kw (kW, drawn), and one true/false column per program flag (drawn). Eight per transformer, matching transformer_actions.csv.
