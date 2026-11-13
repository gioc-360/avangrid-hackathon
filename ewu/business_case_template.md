# Electrify Without Upgrade: the business case on the prototype's numbers

[[note]]

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

A flag is any hour above [[config:transformer.overload_limit|.1f]] times the rating; the tool also reports how long and how far. On the
Feb 7-8 cold snap, with staggered charging, [[ewu.coldsnap.moderate.staggered.margin_115.flagged_pct|.2f]]% of transformers go over, for a median of
[[ewu.coldsnap.moderate.staggered.margin_115.hours_over_median|.0f]] hours and [[ewu.coldsnap.moderate.staggered.margin_115.kwh_over_median]] kWh above the limit.

## WHY: EV timing decides whether a transformer overloads; heat pumps decide when

Heat pumps run in [[ewu.attribution.moderate.random.margin_115.unmanaged.hours_with_hp_running_pct]]% of overload hours but are the larger cause in only
[[ewu.attribution.moderate.random.margin_115.unmanaged.hours_lead_hp_pct]]%. The heat pump raises the floor all night; the charger is the spike that crosses the limit.
So staggering cuts the moderate case from [[ewu.stress.moderate.random.margin_115.overloaded_pct]]% to [[ewu.shift.moderate.random.margin_115.staggered.overloaded_pct]]% of transformers. A simple timer that
starts every car at once does not: it nets [[ewu.shift.moderate.random.margin_115.timer.overloaded_pct]]% in the moderate case and backfires in the high
case, from [[ewu.stress.high.random.margin_115.overloaded_pct]]% to [[ewu.shift.high.random.margin_115.timer.overloaded_pct]]%, because cars start together on the coldest nights.

What shifting cannot reach is where a battery earns its place:
- **Heat pumps alone.** [[ewu.attribution.moderate.random.margin_115.unmanaged.overloaded_without_ev_of_all_pct]]% of transformers (moderate) and [[ewu.attribution.high.random.margin_115.unmanaged.overloaded_without_ev_of_all_pct]]% (high) overload with no
  new EV at all. These are heat pump nights, and no EV program reaches them.
- **The 3 kVA rule.** A home may add about [[config:transformer.service_added_kva_max]] kVA without a service study. Only [[bess.headroom_rule.ev_pass_pct_none]]% of homes
  without an EV can add a Level 2 charger within it today; one battery unit raises that to [[bess.headroom_rule.ev_pass_pct_one_unit]]%, two to
  [[bess.headroom_rule.ev_pass_pct_two_units|.0f]]%. The battery lets that home electrify now.
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

**The battery price that makes Protect pay.** At placeholder prices a cleared transformer's batteries cost
$[[ewu.economics.battery_vs_upgrade.mid.battery_yearly_usd|,.0f]] a year against $[[ewu.economics.battery_vs_upgrade.mid.upgrade_yearly_usd|,.0f]] for the upgrade they put off (equal life, [[config:prices.discount_rate|.0%]] rate). A battery beats
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
