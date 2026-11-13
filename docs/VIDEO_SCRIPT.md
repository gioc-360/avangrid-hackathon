# Video script: Electrify Without Upgrade

A demo film for the team's pptx, planned at 4:20 with a 3:30 to 4:30 window, timed at 140 spoken words a minute with numbers read out in full. One narrator, deadpan, short
sentences, about 140 words a minute. Three illustrative people carry the story: Dana, a NYSEG household that wants
an EV and a heat pump by 2030; Sam, the distribution planner who has to answer her; and the Riveras, neighbors on
the same transformer. Every product shot is the real tool: the offline demo page `outputs/demo/ewu_demo.html` and
one live run of `bin/ewu screen`. Every number below traces to facts/facts.json or config/ewu.yaml
(`checks/trace_numbers.py docs/VIDEO_SCRIPT.md`). Results are for the moderate 2030 scenario, transformers rated at
today's group peak x 1.15, random grouping, unless a row says otherwise.

Rules this script keeps: people are labeled "Illustrative" on screen whenever they appear; what happens to them
follows from a tool output named in the Fact keys column; over the limit is never called a failure or an outage;
placeholder prices are called placeholders; no real home, meter or customer appears anywhere. The narration rounds
a number so it can be said in one breath (26%); the page and the on-screen note show the exact value (26.18%), and
the trace check holds the rounded form to the same fact at the precision spoken.

## Script

| Time | Picture | Narration | On-screen note | Fact keys |
|---|---|---|---|---|
| 0:00 to 0:04 | C1 title card: black, fades in to "Electrify Without Upgrade", small line under it "A transformer screen for 2030 electrification" | (silence) | | |
| 0:04 to 0:20 | I1 illustrated scene, a summer evening on a NYSEG street of 8 houses, one transformer on a pole, Dana's house lit | "This is Dana, on a NYSEG street. By 2030 she wants an electric car and a heat pump. Her home shares one transformer with her neighbors. In our model, 8 homes share each one." | Illustrative. 8 homes per transformer, assumed | config:transformer.homes_per_transformer |
| 0:20 to 0:37 | I2 illustrated scene, Sam at a planning desk, Dana's request on the screen beside a map with the same pole | "This is Sam. Sam plans the grid and has to answer her. Two questions decide it. Can she electrify without waiting for a new transformer? And on the coldest night of the year, does her transformer stay under its limit?" | Illustrative | |
| 0:37 to 1:03 | P2 demo page, Screen step at `#home=2&scenario=moderate&grouping=random&margin=1&hosts=0&only=2`; cursor clicks x 1.05, then x 1.50, then back to x 1.15 | "In a moderate 2030, 20% of homes add an EV and 15% add a heat pump. If cars charge whenever they plug in, 26% of transformers go over their limit in some hour of the year. Transformer sizes are not known yet, so the tool shows a range, from 4% to 43%." | 26.18%, range 3.74% to 42.84% | config:scenarios.moderate.ev_share; config:scenarios.moderate.hp_share; ewu.sensitivity.moderate.random.margin_115.flagged_pct; ewu.sensitivity.moderate.random.margin_150.flagged_pct; ewu.sensitivity.moderate.random.margin_105.flagged_pct; config:transformer.overload_limit |
| 1:03 to 1:24 | P1 demo page, Inventory step at `#home=2&scenario=moderate&grouping=random&margin=1&hosts=0&only=1`: Composite home, dual electrified segment, equipment table, program chips, winter and summer day lines | "How does the tool know who has what? It reads each home's hourly meter, nothing else, and lists its equipment. This Composite home averages the 105 homes in the dual electrified segment. In all, 69% of homes qualify for at least one program." | Composite: a segment average, not a customer | ewu.demo.composite_2.homes; ewu.inventory.homes; ewu.inventory.any_program_pct |
| 1:24 to 1:39 | P2 again, the big Flag number held, cursor resting on it so its fact key shows on hover | "Rung one is Flag. Say Dana's transformer is in that 26%. In 76% of the hours it is over, it takes both the new cars and the new heat pumps." | Flag: both new loads, 76.0% of hours | ewu.sensitivity.moderate.random.margin_115.flagged_pct; ewu.attribution.moderate.random.margin_115.unmanaged.hours_both_needed_pct |
| 1:39 to 1:51 | I3 illustrated scene, the same summer evening, Dana plugs in her car in the driveway | "Rung two is Shift. On a summer evening Dana gets home and plugs in. Today, 53% of measured charging sessions start in the evening." | Illustrative. Sessions starting 16:00 to 22:00: 53.1% | ewu.adoption.ev_start_16_to_22_pct |
| 1:51 to 2:10 | P2 again, the Shift row of the ladder bar and table, Shift segment of the bar highlighted by cursor | "The tool staggers them: each car on her transformer gets its own slot late at night, at half power, same energy. For Dana nothing changes. Her car still charges overnight. Staggering alone brings 79% of flagged transformers back under the limit." | Shift fixes 20.57% of all transformers | config:shift.stagger_start_hour; config:shift.stagger_end_hour; config:shift.stagger_power_share; ewu.sensitivity.moderate.random.margin_115.shift_fixed_pct; ewu.shift.moderate.random.margin_115.staggered.fixed_pct |
| 2:10 to 2:25 | T1 terminal, full screen, prompt `$`, types and runs `bin/ewu screen --scenario moderate --margin 1.15`; the ladder table prints | "The same ladder, live, on the full meter data: 3,000 synthetic transformers, in seconds. It prints 26% flagged and 0.6% left to upgrade." | Live run, full meter data | config:transformer.count; config:demo.margin; ewu.screen.moderate.random.margin_115.flagged_pct; ewu.screen.moderate.random.margin_115.shift_fixed_pct; ewu.screen.moderate.random.margin_115.protected_pct; ewu.screen.moderate.random.margin_115.upgrade_left_pct |
| 2:25 to 2:40 | I4 illustrated scene, a cold February night, the street under snow, the Riveras' garage with two battery units, Dana's window lit | "Rung three is Protect. Feb 7-8 is the coldest stretch in the data, -5 F at the coldest hour. Even with staggered charging, 2.7% of transformers go over their limit." | Illustrative. Feb 7-8, coldest hour -5.0 F | ewu.coldsnap.window_min_temp_f; ewu.coldsnap.moderate.staggered.margin_115.flagged_pct |
| 2:40 to 3:06 | P3 demo page, Cold snap step at `#home=2&scenario=moderate&grouping=random&margin=1&hosts=0&only=3`, then click 2 host homes (`hosts=1`); load line drops under the limit line; cursor ends on the fleet battery charge lines | "The Riveras host two battery units, picked by the tool's fit score. One host home clears 90% of those transformers. Two hosts clear 93%. The battery charges only when the transformer has room, so its charge that night is earned, not assumed. In 10% of cases it runs empty, and the tool says so." | One host 89.88%, two hosts 92.84% | config:battery.energy_kwh_two_units; ewu.coldsnap.moderate.staggered.margin_115.hosts_1.cleared_pct; ewu.coldsnap.moderate.staggered.margin_115.hosts_2.cleared_pct; ewu.coldsnap.moderate.staggered.margin_115.hosts_1.ran_empty_pct |
| 3:06 to 3:17 | P2 again at `only=2`, cursor on the Upgrade row of the ladder table | "Rung four is Upgrade. Sam spends capital only where nothing else works: 0.4% of transformers, out of 26% flagged." | Upgrade: 0.42% of transformers | ewu.sensitivity.moderate.random.margin_115.upgrade_left_pct; ewu.sensitivity.moderate.random.margin_115.flagged_pct |
| 3:17 to 3:36 | I5 illustrated triptych, three panels: Dana's car and heat pump outside her house, the Riveras' garage battery, Sam's list on screen | "For Dana, the car and heat pump go in, and her fix is a charging schedule. For the Riveras, a battery in the garage keeps the transformer under its limit through a cold snap. For Sam, one list: every transformer, its cheapest fix, in order." | Illustrative | ewu.shift.moderate.random.margin_115.staggered.fixed_pct; ewu.coldsnap.moderate.staggered.margin_115.hosts_1.cleared_pct |
| 3:36 to 4:00 | P4 demo page, Money step at `#home=2&scenario=moderate&grouping=random&margin=1&hosts=0&only=4`: the three bars, then the tie price paragraph | "For Avangrid, shifting and then upgrading the rest costs 43% of upgrading every flagged transformer. The full ladder costs 52%. At placeholder prices, a battery beats the upgrade only below $7,730 a unit. So the money is in shifting, and batteries go where shifting cannot reach." | Ladder range 30.8% to 151.19%; prices placeholder | ewu.economics.headline.shift_then_upgrade_share_pct.base; ewu.economics.headline.ladder_share_pct.base; ewu.economics.headline.ladder_share_pct.low; ewu.economics.headline.ladder_share_pct.high; ewu.economics.battery_vs_upgrade.mid.tie_unit_usd_equal_life; ewu.economics.moderate.random.margin_115.mid.nyseg_upgrade_all_musd; ewu.economics.moderate.random.margin_115.mid.nyseg_shift_then_upgrade_musd |
| 4:00 to 4:15 | T2 terminal, prompt `$`, `bin/ewu screen --scenario moderate --margin 1.15 --map` typed, not run, cursor blinking after `--map` | "What the tool needs next is the meter-to-transformer map. The same command runs on it, with one flag. Then Sam's list is about real transformers, and Dana's answer is about her own street." | Next: Avangrid's meter-to-transformer map | repo:ewu/cli.py:136 (`--map`) |
| 4:15 to 4:20 | C2 fade to black, title card returns, then black | (silence) | | |

## Claims

| Claim | Fact key or source | Kind |
|---|---|---|
| Dana, Sam and the Riveras, their street, their car and battery | none: story devices | illustrative |
| 8 homes share each transformer | config:transformer.homes_per_transformer | assumption |
| Moderate 2030: 20% of homes add an EV, 15% a heat pump | config:scenarios.moderate.ev_share, config:scenarios.moderate.hp_share | assumption |
| Over the limit means loading above 1.20 x rating | config:transformer.overload_limit | assumption |
| 26.18% of transformers go over the limit with unmanaged charging | ewu.sensitivity.moderate.random.margin_115.flagged_pct | measured (model on meter data) |
| Range over transformer sizing, 3.74% to 42.84% | ewu.sensitivity.moderate.random.margin_150.flagged_pct, ewu.sensitivity.moderate.random.margin_105.flagged_pct | measured over assumed sizings |
| Equipment is read from each home's hourly meter alone, with a confidence word | demo page step 1 text; ewu/demo_template.html | measured method |
| Composite home is the average of 105 homes | ewu.demo.composite_2.homes | measured |
| 69.07% of 33,757 homes qualify for at least one program | ewu.inventory.any_program_pct, ewu.inventory.homes | measured |
| In 76.0% of over-limit hours neither new load alone would push the transformer over | ewu.attribution.moderate.random.margin_115.unmanaged.hours_both_needed_pct | measured |
| 53.1% of measured charging sessions start between 16:00 and 22:00 | ewu.adoption.ev_start_16_to_22_pct | measured |
| Staggering gives each car its own slot in a late window (23:00 to 3:00), at half power, same energy | config:shift.stagger_start_hour, config:shift.stagger_end_hour, config:shift.stagger_power_share; ewu/shift.py docstring | assumption (program design) |
| Staggering fixes 20.57% of all transformers, 78.56% of flagged ones | ewu.sensitivity.moderate.random.margin_115.shift_fixed_pct, ewu.shift.moderate.random.margin_115.staggered.fixed_pct | measured |
| "For Dana nothing changes; her car still charges overnight" | same energy per session, start slot inside the late window (ewu/shift.py docstring) | illustrative, follows from the model |
| Live run: 3,000 transformers, 26.00%, 20.50%, 4.97%, 0.60% | config:transformer.count; ewu.screen.moderate.random.margin_115.* (flagged_pct, shift_fixed_pct, protected_pct, upgrade_left_pct); docs/demo/cli_output.txt | measured (one seed) |
| Coldest hour -5.0 F over Feb 7-8 | ewu.coldsnap.window_min_temp_f | measured (weather data) |
| 2.70% of transformers go over in the cold snap with staggered charging | ewu.coldsnap.moderate.staggered.margin_115.flagged_pct | measured |
| Two units hold 20.16 kWh | config:battery.energy_kwh_two_units | challenge spec |
| One host clears 89.88%, two hosts 92.84%, one host runs empty in 9.63% | ewu.coldsnap.moderate.staggered.margin_115.hosts_1.cleared_pct, hosts_2.cleared_pct, hosts_1.ran_empty_pct | measured (dispatch model, recomputed by checks/recompute_battery.py) |
| Battery charge on the cold night is earned, not assumed full | demo page step 3 text; ewu/coldsnap.py | measured method |
| Hosts are picked by fit score | ewu/fitscore.py | measured method |
| 0.42% of transformers left for an upgrade | ewu.sensitivity.moderate.random.margin_115.upgrade_left_pct | measured |
| Shift then upgrade 43.47%, ladder 51.92%, range 30.8% to 151.19% of upgrading every flag | ewu.economics.headline.* | measured on placeholder prices |
| Battery beats the upgrade only below $7,730 a unit | ewu.economics.battery_vs_upgrade.mid.tie_unit_usd_equal_life | measured on placeholder prices |
| NYSEG scaled: $436.9M upgrade-all vs $189.9M shift then upgrade (on the P4 page note, not narrated) | ewu.economics.moderate.random.margin_115.mid.nyseg_upgrade_all_musd, nyseg_shift_then_upgrade_musd | assumption (labeled scaling) |
| The same command runs on a real map with `--map` | ewu/cli.py:136 | measured (flag exists) |

## Shot list

### Tool page states (screen recording of `outputs/demo/ewu_demo.html`, built by `bin/ewu demo --no-open`)

| Shot | Hash | What must be built |
|---|---|---|
| P1 Inventory | `#home=2&scenario=moderate&grouping=random&margin=1&hosts=0&only=1` | Record as is; dual electrified Composite home is index 2 |
| P2 Screen | `#home=2&scenario=moderate&grouping=random&margin=1&hosts=0&only=2` | Three takes from one recording: sizing clicks, Flag hover, Shift and Upgrade rows; margin index 1 is x 1.15 |
| P3 Cold snap | `#home=2&scenario=moderate&grouping=random&margin=1&hosts=0&only=3` then `hosts=1` | Record the click from one host to two hosts; end on the fleet charge lines |
| P4 Money | `#home=2&scenario=moderate&grouping=random&margin=1&hosts=0&only=4` | Record with the screen step left on moderate, x 1.15, random, so the money step matches |

### Terminal

| Shot | Command | What must be built |
|---|---|---|
| T1 Live screen | `bin/ewu screen --scenario moderate --margin 1.15` | Run live with `PS1='$ '` and a clean window title so no home folder or user name shows; keep the real wall clock, trim only the wait if it runs long |
| T2 Next step | `bin/ewu screen --scenario moderate --margin 1.15 --map` typed, not run | Same window; no map file named |

### Illustrated scenes (drawn, no photos, no logos, each with an "Illustrative" tag)

| Shot | Scene | What must be built |
|---|---|---|
| I1 Street | Summer evening, a street of 8 houses on one pole transformer, Dana's house lit | One still with a slow push in |
| I2 Planner | Sam at a desk, Dana's request beside a map with the same pole | One still |
| I3 Plug in | Dana plugs in her car in the driveway, same evening | One still |
| I4 Cold night | Feb 7-8, snow, the Riveras' garage with two battery units | One still |
| I5 Triptych | Dana's car and heat pump, the Riveras' battery, Sam's list | Three panels in one frame |

### Title cards

| Shot | Card | What must be built |
|---|---|---|
| C1 Open | Black, fade in "Electrify Without Upgrade" and its subtitle | Plain type on black |
| C2 Close | Fade to black, the title returns, then black | Same card as C1 |

## Privacy

- P1 shows a Composite home: the average of every home in a segment (105 homes here), labeled on the page as not a
  real customer. No meter id, customer id or single-home row is on the page.
- P2 and P4 show only shares of all transformers and money totals across the synthetic fleet.
- P3 draws one synthetic transformer's summed load, the sum of its 8 homes, which the house rules allow as a
  group aggregate; the narration speaks none of its kW values, and the battery charge lines are fleet median and
  bottom tenth across every flagged transformer, not one host's battery.
- T1 prints system totals only and ends with the line "aggregates only"; T2 runs nothing.
- The page file itself still holds that synthetic transformer's hourly values, so it is recorded on this laptop
  and never shared; only the rendered video goes into the pptx.
- Illustrated people, houses and the street are drawn, not traced from any real home, and carry the tag
  "Illustrative".
- Narration and the voice track are produced on this machine; no cloud text to speech and no upload of any frame.

## Rubric moments

| Rubric line | Where the video earns it |
|---|---|
| Business value (40) | 3:06 to 4:00: Upgrade only 0.42%, shift then upgrade 43.47%, tie price $7,730, labeled NYSEG scaling on the page |
| Analytics and modeling (35) | 1:03 to 1:39: equipment read from meters, Composite segment, both loads needed 76.0%; 2:40 to 3:06: hour by hour battery dispatch |
| Presentation (15) | One story, three people, four rungs, each rung shown in the real tool |
| Innovation (10) | 2:10 to 2:25: the live run on the full data; 4:00 to 4:15: the same command on a real map |
