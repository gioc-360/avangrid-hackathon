# Video script: Electrify Without Upgrade

A silent screen recording of the real tool for the team's pptx, with this script as the read-along for a human
voice recorded later. The film is `outputs/video/ewu_demo_vN.mp4` (v2 and later); it carries no voice. The Time
column below is the cut: `video/build.py` writes each row's start and end from the pacing rules, the takes are
recorded to the same plan, and the edit places every take, marker and card from it, so a reader who starts each
line at its time lands on the pointer. Sentence by sentence times are in `outputs/video/ewu_demo_vN_readalong.srt`
(not burned into the film), `outputs/video/ewu_demo_vN_transcript.txt` and the optional cue clicks
`outputs/video/ewu_demo_vN_cues.wav` (one soft tick at each sentence start, never in the film).

Who it is for: an Avangrid distribution planner (Sam, illustrative) deciding which neighborhood transformers need
what before 2030. The households (Dana, the Riveras, illustrative) are who benefits.

Pacing: each sentence gets the longer of 140 spoken words a minute (numbers read out in full) and the length of
the earlier recorded take of the same sentence, used only as a length guide; 0.5 s of breathing room between
sentences. The pointer lands on what a sentence names at that word's place in the sentence, at the same rate.

Every picture is a real screen recording of this laptop: the offline demo page `outputs/demo/ewu_demo.html`
(built by `bin/ewu demo --no-open`, aggregates only, Composite homes) in a full-screen Chrome window, driven by
the real system pointer with real clicks on the page's side panel and buttons and real hovers that open the
page's own fact-key tooltips; and one live run of `bin/ewu screen` in a full-screen Terminal. Every step is
reached by clicking its link in the page's left side panel. The edit adds only the markers, the step indicator
and the person cards. Every number below traces to facts/facts.json or config/ewu.yaml
(`checks/trace_numbers.py docs/VIDEO_SCRIPT.md`). Results are for the moderate 2030 scenario, transformers rated
at today's group peak x 1.15, random grouping, unless a row says otherwise.

Rules this script keeps: the people are story devices, heard in the narration and seen only as short
lower-third cards labeled Illustrative, one at a time; over the limit is never called a failure or an outage;
placeholder prices are called placeholders; no real home, meter or customer appears anywhere. The narration
rounds a number so it can be said in one breath (26%); the page and the markers show the exact value (26.18%).

## Script

| Time | Picture | Narration | On-screen note | Fact keys |
|---|---|---|---|---|
| 0:00.0 to 0:04.0 | T0 title card on a plain page-coloured background: "Electrify Without Upgrade", under it "Flag, Shift, Protect, Upgrade: a working tool on the full meter data"; fade up from black, 0.3 s crossfade into the app | (silence) | | |
| 0:04.0 to 0:22.8 | P0 Overview, side panel on the left with Overview current; card "Sam, Illustrative"; the pointer rests, then hovers the headline 0.42% so its fact key shows. Marker on the headline number: "Only 0.42% need a new transformer" | "This is Sam, a distribution planner at Avangrid. Before 2030, Sam has to decide which neighborhood transformers need what. The tool's answer is on its first screen: only 0.4% of transformers need a new one." | Illustrative. 0.42% need a new transformer | ewu.sensitivity.moderate.random.margin_115.upgrade_left_pct |
| 0:22.8 to 0:35.2 | P0 Overview, the pointer moves off the number to a quiet spot and rests; card "Dana, Illustrative" | "Dana is who benefits. By 2030 she wants an electric car and a heat pump. In our model, 8 homes share each transformer." | Illustrative. 8 homes per transformer, assumed | config:transformer.homes_per_transformer |
| 0:35.2 to 0:58.9 | P1 click Inventory in the side panel; click the segment button "EV and electric heat"; hover 69.07%. Markers: "Composite: a segment average, not a customer" on the Composite caption, then "69.07% of homes qualify for a program" on the headline | "The tool reads each home's hourly meter and lists its equipment. This Composite home is the average of 105 homes with an EV and electric heat, not a real customer. In all, 69% of homes qualify for at least one program." | Composite: a segment average, not a customer | ewu.demo.composite_2.homes; ewu.inventory.any_program_pct |
| 0:58.9 to 1:20.1 | P2 click Flag in the side panel; pointer on the Moderate scenario button, then hovers the headline 26.18%. Marker on the headline: "26.18% of transformers over limit by 2030" | "Rung one is Flag. In a moderate 2030, 20% of homes add an EV and 15% add a heat pump. If cars charge whenever they plug in, 26% of transformers go over their limit." | 26.18% flagged | config:scenarios.moderate.ev_share; config:scenarios.moderate.hp_share; ewu.sensitivity.moderate.random.margin_115.flagged_pct; config:transformer.overload_limit |
| 1:20.1 to 1:33.8 | P2 click x 1.50 (headline reads 3.74%), click x 1.05 (42.84%), click x 1.15 (back to 26.18%); hover the headline so its fact key shows. Markers: "Range, not one number: 3.74% to 42.84%" on the sizing chart, then "Every number traced to code" on the headline | "Transformer sizes are not known yet, so the tool shows a range, from 4% to 43%. Hover any number and its source key appears." | Range 3.74% to 42.84% | ewu.sensitivity.moderate.random.margin_150.flagged_pct; ewu.sensitivity.moderate.random.margin_105.flagged_pct |
| 1:33.8 to 2:04.5 | P3 click Shift in the side panel; card "Dana, Illustrative"; pointer on the green Shift part of the ladder bar, then hovers the headline 20.57%. Marker on the headline: "Shift fixes most, no new equipment" | "Rung two is Shift. Today, 53% of measured charging sessions start in the evening. The tool staggers them: each car on a transformer gets its own late-night slot, at half power, same energy, so Dana's car still charges overnight. That alone fixes 21% of all transformers, most of the 26% flagged, with no new equipment." | Shift fixes 20.57% of all transformers, 78.56% of flagged ones | ewu.adoption.ev_start_16_to_22_pct; config:shift.stagger_start_hour; config:shift.stagger_end_hour; config:shift.stagger_power_share; ewu.sensitivity.moderate.random.margin_115.shift_fixed_pct; ewu.shift.moderate.random.margin_115.staggered.fixed_pct |
| 2:04.5 to 2:22.5 | P4 click Protect in the side panel; hover 2.70% in the so-line. Marker on 2.70%: "2.70% still over in the cold snap" | "Rung three is Protect. In the coldest two days of the data, Feb 7-8 at -5 F, shifting is not enough: 2.7% of transformers still go over." | Feb 7-8, coldest hour -5.0 F | ewu.coldsnap.window_min_temp_f; ewu.coldsnap.moderate.staggered.margin_115.flagged_pct |
| 2:22.5 to 2:36.7 | P4 card "The Riveras, Illustrative"; hover 89.88%, click "2 host homes" (the load with batteries redraws), hover 92.84%. Marker on the so-line: "Batteries carry the cold snap shifting cannot" | "The Riveras host two battery units, picked by the tool's fit score. One host home clears 90% of those transformers; two hosts clear 93%." | One host 89.88%, two hosts 92.84% | config:battery.energy_kwh_two_units; ewu.coldsnap.moderate.staggered.margin_115.hosts_1.cleared_pct; ewu.coldsnap.moderate.staggered.margin_115.hosts_2.cleared_pct |
| 2:36.7 to 2:50.1 | P5 click Upgrade in the side panel; hover the headline 0.42%. Marker on the headline: "Capital only where nothing else works" | "Rung four is Upgrade. Capital goes only where nothing else works: 0.4% of transformers, out of 26% flagged." | Upgrade: 0.42% of transformers | ewu.sensitivity.moderate.random.margin_115.upgrade_left_pct; ewu.sensitivity.moderate.random.margin_115.flagged_pct |
| 2:50.1 to 3:02.7 | T1 full-screen Terminal, prompt `$`, `bin/ewu screen --scenario moderate --margin 1.15` typed at a human pace and run for real; its real output prints at its real time. Marker on the Flag to Upgrade lines: "Live run on the full meter data" | "The same ladder runs live on the full meter data: 3,000 synthetic transformers, in seconds." | Live run, full meter data | config:transformer.count |
| 3:02.7 to 3:19.1 | P6 back in the app, click Money in the side panel; hover 43.47%, then 51.92%. Marker on the Shift, then upgrade bar: "Shift then upgrade: 43.47% of upgrade-all cost" | "For Avangrid, the money is in shifting. Shifting, then upgrading what is still over, costs 43% of upgrading every flagged transformer; the full ladder costs 52%." | Shift then upgrade 43.47%, ladder 51.92% | ewu.economics.headline.shift_then_upgrade_share_pct.base; ewu.economics.headline.ladder_share_pct.base |
| 3:19.1 to 3:32.5 | P6 hover the $7,730 tie price. Marker on it: "Battery tie price, at placeholder prices" | "At placeholder prices, a battery beats the upgrade only below $7,730 a unit, so batteries go only where shifting cannot reach." | Prices are placeholders | ewu.economics.battery_vs_upgrade.mid.tie_unit_usd_equal_life |
| 3:32.5 to 3:49.4 | T2 the same Terminal, `bin/ewu screen --scenario moderate --margin 1.15 --map` typed, not run. Marker on `--map`: "Next: Avangrid's meter-to-transformer map" | "What the tool needs next is Avangrid's meter-to-transformer map. The same command runs on it with one flag, and the answer is about the real transformers on Dana's street." | Next: Avangrid's meter-to-transformer map | repo:ewu/cli.py:138 (`--map`) |
| 3:49.4 to 3:54.4 | C1 close card on the plain background: "Electrify Without Upgrade" and "Shift first. Batteries where shifting cannot reach. Capital last."; fade to black | (silence) | | |
## Claims

| Claim | Fact key or source | Kind |
|---|---|---|
| Sam, Dana and the Riveras, their street, their car and battery | none: story devices | illustrative |
| 0.42% of transformers are left for an upgrade | ewu.sensitivity.moderate.random.margin_115.upgrade_left_pct | measured |
| 8 homes share each transformer | config:transformer.homes_per_transformer | assumption |
| Equipment is read from each home's hourly meter alone | demo page Inventory so-line; ewu/demo_template.html | measured method |
| Composite home is the average of 105 homes | ewu.demo.composite_2.homes | measured |
| 69.07% of 33,757 homes qualify for at least one program | ewu.inventory.any_program_pct, ewu.inventory.homes | measured |
| Moderate 2030: 20% of homes add an EV, 15% a heat pump | config:scenarios.moderate.ev_share, config:scenarios.moderate.hp_share | assumption |
| Over the limit means loading above 1.20 x rating | config:transformer.overload_limit | assumption |
| 26.18% of transformers go over the limit with unmanaged charging | ewu.sensitivity.moderate.random.margin_115.flagged_pct | measured (model on meter data) |
| Range over transformer sizing, 3.74% to 42.84% | ewu.sensitivity.moderate.random.margin_150.flagged_pct, ewu.sensitivity.moderate.random.margin_105.flagged_pct | measured over assumed sizings |
| 53.1% of measured charging sessions start between 16:00 and 22:00 | ewu.adoption.ev_start_16_to_22_pct | measured |
| Staggering gives each car its own slot in a late window (23:00 to 3:00), at half power, same energy | config:shift.stagger_start_hour, config:shift.stagger_end_hour, config:shift.stagger_power_share; ewu/shift.py docstring | assumption (program design) |
| Staggering fixes 20.57% of all transformers, 78.56% of flagged ones | ewu.sensitivity.moderate.random.margin_115.shift_fixed_pct, ewu.shift.moderate.random.margin_115.staggered.fixed_pct | measured |
| "Dana's car still charges overnight" | same energy per session, start slot inside the late window (ewu/shift.py docstring) | illustrative, follows from the model |
| Coldest hour -5.0 F over Feb 7-8 | ewu.coldsnap.window_min_temp_f | measured (weather data) |
| 2.70% of transformers go over in the cold snap with staggered charging | ewu.coldsnap.moderate.staggered.margin_115.flagged_pct | measured |
| Two units hold 20.16 kWh | config:battery.energy_kwh_two_units | challenge spec |
| One host clears 89.88%, two hosts 92.84% | ewu.coldsnap.moderate.staggered.margin_115.hosts_1.cleared_pct, hosts_2.cleared_pct | measured (dispatch model, recomputed by checks/recompute_battery.py) |
| Hosts are picked by fit score | ewu/fitscore.py | measured method |
| Live run on 3,000 synthetic transformers in seconds | config:transformer.count; the run's own last line | measured (one seed) |
| Shift then upgrade 43.47%, ladder 51.92% of upgrading every flag | ewu.economics.headline.* | measured on placeholder prices |
| Battery beats the upgrade only below $7,730 a unit | ewu.economics.battery_vs_upgrade.mid.tie_unit_usd_equal_life | measured on placeholder prices |
| The same command runs on a real map with `--map` | ewu/cli.py:138 | measured (flag exists) |

## Takes

The film is cut from short real takes, one per step, each recorded to this plan's clock (`video/record.py`).
A take starts on the state the last one ended on (same step, same pointer spot), so each cut is a hard cut
between identical frames. Every take waits for 3 minutes with no user input and no live Loggie recording, and
stops and is thrown away the moment the pointer is not where the script left it.

| Take | Rows | Starts on | What the real pointer does |
|---|---|---|---|
| overview | P0 | Overview | rests, hovers the headline, moves to a quiet spot |
| inventory | P1 | Overview | clicks Inventory in the side panel, clicks "EV and electric heat", hovers 69.07% |
| flag | P2 | Inventory | clicks Flag, points at Moderate, hovers 26.18%, clicks x 1.50, x 1.05, x 1.15, hovers the headline |
| shift | P3 | Flag | clicks Shift, points at the ladder bar, hovers 20.57% |
| protect | P4 | Shift | clicks Protect, hovers 2.70%, 89.88%, clicks 2 host homes, hovers 92.84% |
| upgrade | P5 | Protect (2 hosts) | clicks Upgrade, hovers 0.42% |
| terminal | T1, T2 | a fresh full-screen Terminal | the wrapper types and runs the command, then types the `--map` line without running it |
| money | P6 | Upgrade | clicks Money, hovers 43.47%, 51.92%, $7,730 |

## Markers and the step indicator

One marker at a time, one accent colour: a thin rounded box drawn from the element's real DOM rectangle, read
from the filmed window during the take and logged in `outputs/video/ewu_demo_vN_takes.json`, with a label of at
most 8 words placed beside the box, never on it; each fades in and out in 0.2 s and never moves. In the
terminal the box comes from the text rows found in the recorded frame. A small step indicator in the lower
right names Flag, Shift, Protect, Upgrade and Money with the current rung in the accent colour. The words are in
the Picture column; `video/path.py` holds them and `tests/test_video.py` traces their numbers.

## Privacy

- Inventory shows a Composite home: the average of every home in a segment (105 homes here), labeled on the page
  as not a real customer. No meter id, customer id or single-home row is on the page.
- Flag, Shift, Upgrade and Money show only shares of all transformers and money totals across the synthetic fleet.
- Protect draws one synthetic transformer's summed load, the sum of its 8 homes, a group aggregate; the narration
  speaks none of its kW values, no hover lands on it, and the battery charge lines are the fleet median and
  bottom tenth across every flagged transformer.
- The terminal prints system totals only and ends with the line "aggregates only"; its prompt is a bare `$`
  with no user name or path; the `--map` line runs nothing.
- Each take's frames are checked for notifications, other windows and dialogs before it is used.
- The film is silent; no voice is rendered or sent anywhere, and no frame leaves this machine.

## Rubric moments

| Rubric line | Where the film earns it |
|---|---|
| Business value (40) | Upgrade 0.42%, then Money: shift then upgrade 43.47%, tie price $7,730 at placeholder prices |
| Analytics and modeling (35) | Inventory: equipment read from meters, Composite segment; Flag: range over sizing; Protect: hour by hour battery dispatch in the cold snap |
| Presentation (15) | One planner, two households as cards, four rungs plus the money, each reached from the side panel with one marker at a time |
| Innovation (10) | The live run on the full data; the same command on a real map |
