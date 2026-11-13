# Electrify Without Upgrade: the business case on the prototype's numbers

[[note]]

## Deck profile, the default: the final deck's method, run by this tool on our data

`bin/ewu screen` runs the team's final-deck method by default (the teammate's spec of 2026-11-13, saved at
runs/teammate_deck_spec_2026-11-13.txt). [[config:profiles.deck.transformer_count|,.0f]] synthetic transformers of [[config:profiles.deck.homes_per_transformer]] random homes are each
rated at the smallest standard size at or above today's group peak / [[config:profiles.deck.peak_to_rating_divisor]] (kW read as kVA). A transformer is
overloaded above [[config:profiles.deck.overload_limit|.2f]] times its rating in any hour, and home batteries are the only fix: [[config:profiles.deck.units_min]] to
[[config:profiles.deck.units_max]] battery units per transformer, sized to each day's peak excess and excess energy; more than [[config:profiles.deck.units_max]] means an upgrade.
Money counts [[config:profiles.deck.years]] years at [[config:profiles.deck.discount_rate|.0%]]; an upgrade is counted for [[config:profiles.deck.years]] of its [[config:profiles.deck.upgrade_life_years]] years, $[[ewu.deck.prices.upgrade_counted_usd|,.0f]] each.
The two input arrays are the teammate's own files, given by her ewu_inputs.py and built from the hackathon meter
data, copied by `bin/ewu arrays` and checked by sha256 on every run: EV start hours ([[ewu.deck.inputs.ev_start_pmf.hour0_pct|.1f]]% at midnight)
and one heat pump curve ([[ewu.deck.inputs.hp_increment.annual_kwh|,.0f]] kWh a year, highest hour [[ewu.deck.inputs.hp_increment.max_kw|.2f]] kW).

The replica column is `bin/ewu screen --replica`: our code following her ewu_sim_bo2.py line for line, which equals
her own run on all [[ewu.deck_replica.moderate.rows_equal_her_run|,.0f]] transformers in each case.

| At a [[config:profiles.deck.overload_limit|.2f]] limit | Moderate, ours | Moderate, her code | Moderate, deck | High, ours | High, her code | High, deck |
|---|---|---|---|---|---|---|
| Overloaded, % of transformers | [[ewu.deck.moderate.limit_120.overloaded_pct|.1f]]% | [[ewu.deck_replica.moderate.limit_120.overloaded_pct|.1f]]% | [[config:profiles.deck.targets.overloaded_pct.0]]% | [[ewu.deck.high.limit_120.overloaded_pct|.1f]]% | [[ewu.deck_replica.high.limit_120.overloaded_pct|.1f]]% | [[config:profiles.deck.targets.overloaded_pct.1]]% |
| Fixed without an upgrade, % of overloaded | [[ewu.deck.moderate.limit_120.fixed_of_overloaded_pct|.1f]]% | [[ewu.deck_replica.moderate.limit_120.fixed_of_overloaded_pct|.1f]]% | [[config:profiles.deck.targets.fixed_without_upgrade_pct.0]]% | [[ewu.deck.high.limit_120.fixed_of_overloaded_pct|.1f]]% | [[ewu.deck_replica.high.limit_120.fixed_of_overloaded_pct|.1f]]% | [[config:profiles.deck.targets.fixed_without_upgrade_pct.1]]% |
| Average units per fixed transformer | [[ewu.deck.moderate.limit_120.average_units|.2f]] | [[ewu.deck_replica.moderate.limit_120.average_units|.2f]] | [[config:profiles.deck.targets.average_units.0]] | [[ewu.deck.high.limit_120.average_units|.2f]] | [[ewu.deck_replica.high.limit_120.average_units|.2f]] | [[config:profiles.deck.targets.average_units.1]] |
| Winter driven, % of overloaded | [[ewu.deck.moderate.limit_120.winter_of_overloaded_pct|.1f]]% | [[ewu.deck_replica.moderate.limit_120.winter_of_overloaded_pct|.1f]]% | [[config:profiles.deck.targets.winter_share_pct.0]]% | [[ewu.deck.high.limit_120.winter_of_overloaded_pct|.1f]]% | [[ewu.deck_replica.high.limit_120.winter_of_overloaded_pct|.1f]]% | [[config:profiles.deck.targets.winter_share_pct.1]]% |
| Gross cost across NYSEG, $M | [[ewu.deck.moderate.limit_120.nyseg_gross_musd|.1f]] | [[ewu.deck_replica.moderate.limit_120.nyseg_gross_musd|.1f]] | [[config:profiles.deck.targets.gross_musd.0]] | [[ewu.deck.high.limit_120.nyseg_gross_musd|.1f]] | [[ewu.deck_replica.high.limit_120.nyseg_gross_musd|.1f]] | [[config:profiles.deck.targets.gross_musd.1]] (her code gives [[ewu.deck_replica.high.limit_120.nyseg_gross_musd|.0f]]) |
| Net without NYSERDA, $M | [[ewu.deck.moderate.limit_120.nyseg_net_without_nyserda_musd|.1f]] | [[ewu.deck_replica.moderate.limit_120.nyseg_net_without_nyserda_musd|.1f]] | not in the deck | [[ewu.deck.high.limit_120.nyseg_net_without_nyserda_musd|.1f]] | [[ewu.deck_replica.high.limit_120.nyseg_net_without_nyserda_musd|.1f]] | not in the deck |
| Avangrid cost (net of lease and NYSERDA), $M | [[ewu.deck.moderate.limit_120.nyseg_avangrid_cost_musd|.1f]] | [[ewu.deck_replica.moderate.limit_120.nyseg_avangrid_cost_musd|.1f]] | [[config:profiles.deck.targets.avangrid_cost_musd.0]] | [[ewu.deck.high.limit_120.nyseg_avangrid_cost_musd|.1f]] | [[ewu.deck_replica.high.limit_120.nyseg_avangrid_cost_musd|.1f]] | [[config:profiles.deck.targets.avangrid_cost_musd.1]] |
| Upgrade every overloaded transformer, $M | [[ewu.deck.moderate.limit_120.nyseg_upgrade_all_musd|.1f]] | [[ewu.deck_replica.moderate.limit_120.nyseg_upgrade_all_musd|.1f]] | [[config:profiles.deck.targets.upgrade_all_musd.0]] | [[ewu.deck.high.limit_120.nyseg_upgrade_all_musd|.1f]] | [[ewu.deck_replica.high.limit_120.nyseg_upgrade_all_musd|.1f]] | [[config:profiles.deck.targets.upgrade_all_musd.1]] |

Avangrid cost is the saving's whole basis: at gross, the high case costs more than upgrading every overloaded
transformer. Peak cut with export, [[ewu.deck.peakcut.hosts|,.0f]] priority homes with [[config:profiles.deck.units_per_host]] units each pooled as one fleet:
[[ewu.deck.peakcut.export_peak_drop_mw|.2f]] MW off the yearly peak (deck [[config:profiles.deck.targets.peak_cut_export_mw]] MW, the same metric as the teammate's program.py;
[[ewu.deck.peakcut.export_mw|.2f]] MW on average over the top [[config:profiles.deck.peak_hours]] hours). Behind the meter only, the conservative case:
[[ewu.deck.peakcut.behind_meter_mw|.2f]] MW over the top hours (deck [[config:profiles.deck.targets.peak_cut_behind_meter_mw]] MW, our earlier number; the teammate's own behind-the-meter figure is
[[teammate.audit.rerun.btm_mw|.2f]] MW, see docs/TEAMMATE_AUDIT.md).

Two deck numbers miss on our tool's own run, and we report them rather than tune constants. High-case fixed
without an upgrade is lower because our inventory flags which homes already have an EV or electric heat
differently from the teammate's tiers: swapping only the tiers in her run moves it from
[[ewu.deck_replica.ladder.a_her_run.high.fixed_of_overloaded_pct|.1f]]% to [[ewu.deck_replica.ladder.b_our_tiers.high.fixed_of_overloaded_pct|.1f]]%. Moderate winter driven share is higher on our seed: over seeds 1 to [[config:profiles.deck_replica.spread_seeds]] it
runs from [[ewu.deck_replica.spread.moderate.winter_of_overloaded_pct.min|.1f]]% to [[ewu.deck_replica.spread.moderate.winter_of_overloaded_pct.max|.1f]]%. `bin/ewu screen --profile cautious` gives the earlier method below.

## Cautious profile: the earlier method, kept as a named sensitivity

**Find the street transformers that 2030 electrification will push over their limit, and give each one the
cheapest fix: Flag, Shift, Protect, Upgrade.** In the moderate 2030 case, [[ewu.stress.moderate.random.margin_115.overloaded_pct]]% of
neighborhood transformers go over the limit at least once a year ([[ewu.stress.high.random.margin_115.overloaded_pct]]% in the high case). Staggered
EV charging fixes [[ewu.shift.moderate.random.margin_115.staggered.fixed_pct]]% of them. Shifting and then upgrading what is still over costs
[[ewu.economics.headline.shift_then_upgrade_share_pct.base]]% of upgrading every flagged transformer; the full ladder with batteries costs [[ewu.economics.headline.ladder_share_pct.base]]%.
Shifting is the money saver. A battery is the targeted rung for the places shifting cannot reach.

## WHAT: the flagged share depends on how much room a transformer has, so we state it as a range

| Rating, as today's group peak times | [[config:transformer.sizing_margins.0|.2f]] | [[config:transformer.sizing_margins.1|.2f]] | [[config:transformer.sizing_margins.2|.2f]] | [[config:transformer.sizing_margins.3|.2f]] |
|---|---|---|---|---|
| Moderate 2030 (EV charging unmanaged) | [[ewu.stress.moderate.random.margin_105.overloaded_pct]]% | [[ewu.stress.moderate.random.margin_115.overloaded_pct]]% | [[ewu.stress.moderate.random.margin_130.overloaded_pct]]% | [[ewu.stress.moderate.random.margin_150.overloaded_pct]]% |
| High 2030 (EV charging unmanaged) | [[ewu.stress.high.random.margin_105.overloaded_pct]]% | [[ewu.stress.high.random.margin_115.overloaded_pct]]% | [[ewu.stress.high.random.margin_130.overloaded_pct]]% | [[ewu.stress.high.random.margin_150.overloaded_pct]]% |
| Moderate 2030, over at least [[config:robustness.flag_min_hours]] hours a year | [[ewu.robustness.flag_hours.moderate.random.margin_105.flagged_min_hours_pct]]% | [[ewu.robustness.flag_hours.moderate.random.margin_115.flagged_min_hours_pct]]% | [[ewu.robustness.flag_hours.moderate.random.margin_130.flagged_min_hours_pct]]% | [[ewu.robustness.flag_hours.moderate.random.margin_150.flagged_min_hours_pct]]% |
| High 2030, over at least [[config:robustness.flag_min_hours]] hours a year | [[ewu.robustness.flag_hours.high.random.margin_105.flagged_min_hours_pct]]% | [[ewu.robustness.flag_hours.high.random.margin_115.flagged_min_hours_pct]]% | [[ewu.robustness.flag_hours.high.random.margin_130.flagged_min_hours_pct]]% | [[ewu.robustness.flag_hours.high.random.margin_150.flagged_min_hours_pct]]% |

A flag is any hour above [[config:transformer.overload_limit|.1f]] times the rating, so the flag is also a duration question.
In the moderate case at today's peak times [[config:transformer.base_margin]], [[ewu.robustness.flag_hours.moderate.random.margin_115.short_of_flagged_pct]]% of flagged transformers are over for fewer than
[[config:robustness.flag_min_hours]] hours a year (median [[ewu.robustness.flag_hours.moderate.random.margin_115.median_hours_of_flagged|.0f]] hours). A rule of at least [[config:robustness.flag_min_hours]] hours over flags [[ewu.robustness.flag_hours.moderate.random.margin_115.flagged_min_hours_pct]]% instead of
[[ewu.robustness.flag_hours.moderate.random.margin_115.flagged_pct]]%. Upgrade-all prices every flagged transformer at $[[config:prices.upgrade_cost_usd|,.0f]] (mid placeholder), even one over for a single hour a year,
so it is the costliest reading of the flag; Avangrid's own duration rule is an ask. On the
Feb 7-8 cold snap, with staggered charging, [[ewu.coldsnap.moderate.staggered.margin_115.flagged_pct|.2f]]% of transformers go over, for a median of
[[ewu.coldsnap.moderate.staggered.margin_115.hours_over_median|.0f]] hours and [[ewu.coldsnap.moderate.staggered.margin_115.kwh_over_median]] kWh above the limit.

## WHY: at the measured heat pump load, EV timing decides whether a transformer overloads; heat pumps decide when

Heat pumps run in [[ewu.attribution.moderate.random.margin_115.unmanaged.hours_with_hp_running_pct]]% of overload hours but are the larger cause in only
[[ewu.attribution.moderate.random.margin_115.unmanaged.hours_lead_hp_pct]]%. In [[ewu.attribution.moderate.random.margin_115.unmanaged.hours_both_needed_pct]]% of overload hours it takes both: neither new load alone crosses the
limit. What decides the program is that [[ewu.attribution.moderate.random.margin_115.unmanaged.hours_clear_without_ev_pct]]% of overload hours stay under with no new EV load.
The heat pump raises the floor all night; the charger is the spike that crosses the limit.
So staggering cuts the moderate case from [[ewu.stress.moderate.random.margin_115.overloaded_pct]]% to [[ewu.shift.moderate.random.margin_115.staggered.overloaded_pct]]% of transformers. A simple timer that
starts every car at once does not: it nets [[ewu.shift.moderate.random.margin_115.timer.overloaded_pct]]% in the moderate case and backfires in the high
case, from [[ewu.stress.high.random.margin_115.overloaded_pct]]% to [[ewu.shift.high.random.margin_115.timer.overloaded_pct]]%, because cars start together on the coldest nights.

That answer leans on one input. The heat pump load is a single slope, [[config:scenarios.loads.hp_kw_per_degf]] kW per F below [[config:scenarios.loads.hp_balance_temp_f]] F
([[ewu.robustness.hp_slope_x100.kw_at_0f|.1f]] kW at 0 F), taken as the median difference between electric-heat homes and the rest, not a heat pump model.
At [[config:robustness.hp_slope_multipliers.1]] times that slope, staggering fixes [[ewu.robustness.hp_slope_x150.moderate.margin_115.staggered.fixed_pct]]% instead of [[ewu.robustness.hp_slope_x100.moderate.margin_115.staggered.fixed_pct]]% and the heat pump leads
[[ewu.robustness.hp_slope_x150.moderate.margin_115.unmanaged.hours_lead_hp_pct]]% of overload hours; at [[config:robustness.hp_slope_multipliers.2|.0f]] times, [[ewu.robustness.hp_slope_x200.moderate.margin_115.staggered.fixed_pct]]% and [[ewu.robustness.hp_slope_x200.moderate.margin_115.unmanaged.hours_lead_hp_pct]]% (moderate). So the answer holds
near the measured slope. A heavier heat pump moves work from Shift to Protect and Upgrade; metered heat
pump homes would settle the slope. A second soft input: the runs draw both devices off one random order, so
[[ewu.robustness.adoption_one_order.moderate.margin_115.hp_homes_with_new_ev_pct]]% of new heat pump homes also get a new EV (a labeled assumption). Drawn apart ([[ewu.robustness.adoption_own_order.moderate.margin_115.hp_homes_with_new_ev_pct]]% overlap),
[[ewu.robustness.adoption_own_order.moderate.margin_115.unmanaged.overloaded_pct]]% of transformers overload instead of [[ewu.robustness.adoption_one_order.moderate.margin_115.unmanaged.overloaded_pct]]% and staggering fixes [[ewu.robustness.adoption_own_order.moderate.margin_115.staggered.fixed_pct]]%, so the answer does not rest on the stacking.

What shifting cannot reach is where a battery earns its place:
- **Heat pumps alone.** [[ewu.attribution.moderate.random.margin_115.unmanaged.overloaded_without_ev_of_all_pct]]% of transformers (moderate) and [[ewu.attribution.high.random.margin_115.unmanaged.overloaded_without_ev_of_all_pct]]% (high) overload with no
  new EV at all. These are heat pump nights, and no EV program reaches them.
- **The 3 kVA rule.** A home may add about [[config:transformer.service_added_kva_max]] kVA without a service study. With a charge as long as the
  measured mean session ([[ewu.headroom.ev.measured_mean_hours]] hours from [[config:robustness.headroom_ev_start_hour]]:00, an assumed start), only [[ewu.headroom.ev.charge_measured_mean.pass_pct_none]]% of homes without
  an EV can add a Level 2 charger within it today; one battery unit raises that to [[ewu.headroom.ev.charge_measured_mean.pass_pct_one_unit]]%, two to
  [[ewu.headroom.ev.charge_measured_mean.pass_pct_two_units|.0f]]%. The older [[config:robustness.headroom_ev_hours_assumed]]-hour charge (an assumption) gave [[ewu.headroom.ev.charge_assumed.pass_pct_one_unit]]% for one unit. Two units let that home electrify now.
- **The cold snap.** One host home with two units ([[ewu.coldsnap.moderate.staggered.margin_115.hosts_1.usable_kwh]] kWh) clears [[ewu.coldsnap.moderate.staggered.margin_115.hosts_1.cleared_pct]]% of the
  transformers still over on Feb 7-8, with state of charge carried hour by hour.

## Scott's metric: what the battery hosts cut in the system's top hours

Hosts sit on the transformers still over with staggered charging ([[ewu.tophours.moderate.staggered.margin_115.flagged_per_seed]] per 3,000, moderate), one
host each, chosen by fit score: the kW a battery in that home can cut across the system's top hours, so a
peaky home ranks above a flat, long-loaded one. Random hosts on the same transformers are the control.
Each battery here is dispatched for the system on the hours shown; one unit per host.

| System hours (metered) | Jul 2 hours in set | Feb 7 hours in set | kW per battery, fit score | kW per battery, random | MW, fit-score fleet | % of these homes' 2030 load |
|---|---|---|---|---|---|---|
| Top 20 of the year | [[ewu.tophours.sets.top_20.hours_on_summer_peak_date]] | [[ewu.tophours.sets.top_20.hours_on_winter_peak_date]] | [[ewu.tophours.moderate.staggered.margin_115.fit_score.units_1.top_20.kw_per_battery|.2f]] | [[ewu.tophours.moderate.staggered.margin_115.random.units_1.top_20.kw_per_battery|.2f]] | [[ewu.tophours.moderate.staggered.margin_115.fit_score.units_1.top_20.fleet_mw|.2f]] | [[ewu.tophours.moderate.staggered.margin_115.fit_score.units_1.top_20.share_of_load_pct|.2f]]% |
| Top 50 of the year | [[ewu.tophours.sets.top_50.hours_on_summer_peak_date]] | [[ewu.tophours.sets.top_50.hours_on_winter_peak_date]] | [[ewu.tophours.moderate.staggered.margin_115.fit_score.units_1.top_50.kw_per_battery|.2f]] | [[ewu.tophours.moderate.staggered.margin_115.random.units_1.top_50.kw_per_battery|.2f]] | [[ewu.tophours.moderate.staggered.margin_115.fit_score.units_1.top_50.fleet_mw|.2f]] | [[ewu.tophours.moderate.staggered.margin_115.fit_score.units_1.top_50.share_of_load_pct|.2f]]% |
| Winter top [[ewu.tophours.sets.winter_top.hours]] | [[ewu.tophours.sets.winter_top.hours_on_summer_peak_date]] | [[ewu.tophours.sets.winter_top.hours_on_winter_peak_date]] | [[ewu.tophours.moderate.staggered.margin_115.fit_score.units_1.winter_top.kw_per_battery|.2f]] | [[ewu.tophours.moderate.staggered.margin_115.random.units_1.winter_top.kw_per_battery|.2f]] | [[ewu.tophours.moderate.staggered.margin_115.fit_score.units_1.winter_top.fleet_mw|.2f]] | [[ewu.tophours.moderate.staggered.margin_115.fit_score.units_1.winter_top.share_of_load_pct|.2f]]% |
| Jul 2 peak hour | [[ewu.tophours.sets.summer_peak_date.hours]] | [[ewu.tophours.sets.summer_peak_date.hours_on_winter_peak_date]] | [[ewu.tophours.moderate.staggered.margin_115.fit_score.units_1.summer_peak_date.kw_per_battery|.2f]] | [[ewu.tophours.moderate.staggered.margin_115.random.units_1.summer_peak_date.kw_per_battery|.2f]] | [[ewu.tophours.moderate.staggered.margin_115.fit_score.units_1.summer_peak_date.fleet_mw|.2f]] | [[ewu.tophours.moderate.staggered.margin_115.fit_score.units_1.summer_peak_date.share_of_load_pct|.2f]]% |
| Feb 7 peak hour | [[ewu.tophours.sets.winter_peak_date.hours_on_summer_peak_date]] | [[ewu.tophours.sets.winter_peak_date.hours]] | [[ewu.tophours.moderate.staggered.margin_115.fit_score.units_1.winter_peak_date.kw_per_battery|.2f]] | [[ewu.tophours.moderate.staggered.margin_115.random.units_1.winter_peak_date.kw_per_battery|.2f]] | [[ewu.tophours.moderate.staggered.margin_115.fit_score.units_1.winter_peak_date.fleet_mw|.2f]] | [[ewu.tophours.moderate.staggered.margin_115.fit_score.units_1.winter_peak_date.share_of_load_pct|.2f]]% |

Jul 2 holds the year's highest metered hour. Feb 7 is the winter peak, but its highest hour ranks
[[ewu.tophours.winter_peak_date.rank]] of the year, so today's annual top 50 are all summer hours; the winter set is where Feb 7 counts.
Fit-score hosts cut more per battery than random hosts in every set, scenario and unit count. In the high
case the fit-score fleet cuts on average [[ewu.tophours.high.staggered.margin_115.fit_score.units_1.top_20.fleet_mw|.2f]] MW across the top 20 hours. The fleet is small because the sample is: the
portable number is kW per battery.

## HOW: four rungs, cheapest first (moderate 2030, today's peak times [[config:transformer.base_margin]])

| Rung | What Avangrid does | Share of all transformers |
|---|---|---|
| 1. Flag | Run `bin/ewu screen` on hourly meter data | [[ewu.sensitivity.moderate.random.margin_115.flagged_pct]]% |
| 2. Shift | Default EV homes on flagged transformers to staggered charging | [[ewu.sensitivity.moderate.random.margin_115.shift_fixed_pct]]% fixed |
| 3. Protect | One or two fit-score host homes, one or two units each ([[ewu.sensitivity.moderate.random.margin_115.batteries_per_protected]] per transformer) | [[ewu.sensitivity.moderate.random.margin_115.protected_pct]]% cleared |
| 4. Upgrade | Upgrade what nothing else clears | [[ewu.sensitivity.moderate.random.margin_115.upgrade_left_pct]]% |

Check status: the number review (`checks/review_numbers.py`, record in runs/review_round.json) rebuilt headline numbers
its own way, among them the flagged share and its duration, the heat pump and EV shares of overload hours, the
3 kVA pass shares and the pricing arithmetic behind the [[ewu.economics.headline.ladder_share_pct.base]]% ladder share. The battery numbers were then rebuilt by
separate code (`checks/recompute_battery.py`, record in runs/recompute_battery.json, part of `make check`): the cold snap clear rates, the
fit-score kW in the top 20 hours and the [[ewu.sensitivity.moderate.random.margin_115.batteries_per_protected]] batteries per protected transformer all reproduce.

**The battery price that makes Protect pay.** At placeholder prices a cleared transformer's batteries cost
$[[ewu.economics.battery_vs_upgrade.mid.battery_yearly_usd|,.0f]] a year against $[[ewu.economics.battery_vs_upgrade.mid.upgrade_yearly_usd|,.0f]] for the upgrade they put off (equal life, [[config:prices.discount_rate|.0%]] rate, a placeholder). A battery beats
the upgrade only below $[[ewu.economics.battery_vs_upgrade.mid.tie_unit_usd_equal_life|,.0f]] per installed unit; the placeholder range is $[[config:prices.battery_unit_cost_low_usd|,.0f]] to $[[config:prices.battery_unit_cost_high_usd|,.0f]]. Not counted,
all upside for batteries and none verified: host lease payments, the NYSERDA incentive, capacity value.
Across all [[ewu.sensitivity.cells]] grid cells and price cases the ladder runs [[ewu.economics.headline.ladder_share_pct.low]]% to [[ewu.economics.headline.ladder_share_pct.high]]% of upgrade-all,
shift-then-upgrade [[ewu.economics.headline.shift_then_upgrade_share_pct.low]]% to [[ewu.economics.headline.shift_then_upgrade_share_pct.high]]%.

Scaled to NYSEG (labeled assumption: our sample is typical of [[config:prices.nyseg_electric_customers|,.0f]] customers, [[config:transformer.homes_per_transformer]] per transformer),
present value at mid prices: upgrade every flagged transformer $[[ewu.economics.moderate.random.margin_115.mid.nyseg_upgrade_all_musd]]M, the ladder $[[ewu.economics.moderate.random.margin_115.mid.nyseg_ladder_musd]]M,
shift then upgrade $[[ewu.economics.moderate.random.margin_115.mid.nyseg_shift_then_upgrade_musd]]M.

## The asks to Avangrid (open items, not claims)

1. A meter-to-transformer map with ratings. It replaces the synthetic groups with one flag (`--map`).
   Without it the ratings are guessed, which is why the flagged share above is a range.
2. The installed battery price Avangrid can get, against the $[[ewu.economics.battery_vs_upgrade.mid.tie_unit_usd_equal_life|,.0f]] tie, and whether NYSERDA
   incentives, host leases and capacity value can be counted.
3. How a home battery that defers a transformer upgrade is treated under New York's non-wires-alternative
   benefit-cost test. We do not know, and the answer decides whether Protect is a utility program.

**How it holds up.** Measured on [[data.customers_usable|,.0f]] homes' hourly meters: EV session start times, heat pump load
against temperature, the 3 kVA test, the system top hours. Simulated: transformers are [[config:transformer.homes_per_transformer]] random homes,
[[config:transformer.count|,.0f]] per run, [[config:checks.seeds]] seeds; hourly data hides 15-minute peaks; no ambient derate. Every number here is
written by `ewu/business_case.py` from facts/facts.json and config/ewu.yaml, and `checks/trace_numbers.py`
traces each one. The teammate's earlier figures (for example 9.8% and 29.8% flagged) came from a different
simulation and are not used here; the differences are listed in docs/FINDINGS.md. Left out because we
could not source them: rate decoupling returning value to customers, capital spending as a multiple of
cash flow, and a return on avoided capital.
