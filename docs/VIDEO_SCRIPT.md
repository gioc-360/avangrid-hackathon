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
sentences, longer where the pointer has moves to make. The pointer never moves while a line is read: every glide,
click and hover for a sentence plays in the gap before it (`video/gaps.py` sizes that gap from each glide's
length), then the pointer rests on what the line names while it is read.

Every picture is a real screen recording of this laptop: the offline demo page `outputs/demo/ewu_demo.html`
(built by `bin/ewu demo --no-open`, aggregates only, Composite homes) in a full-screen Chrome window, driven by
the real system pointer with real clicks on the page's side panel and buttons and real rests on the % (or M)
just after each named number, so its digits stay clear and no tooltip covers the page; and one live run of `bin/ewu screen` in a full-screen Terminal. Every step is
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
| 0:04.0 to 0:22.5 | P0 Overview, side panel on the left with Overview current; card "Sam, Illustrative"; before the second line the pointer moves onto the % of the headline 0.42% and rests. Marker on the headline number: "Only 0.42% need a new transformer" | "This is Sam, a distribution planner at Avangrid, deciding which neighborhood transformers need what before 2030. The tool's answer is on its first screen: only 0.4% of transformers need a new one." | Illustrative. 0.42% need a new transformer | ewu.sensitivity.moderate.random.margin_115.upgrade_left_pct |
| 0:22.5 to 0:36.3 | P0 Overview, the pointer moves off the number to a quiet spot and rests; card "Dana, Illustrative" | "Dana is who benefits. By 2030 she wants an electric car and a heat pump. In our model, 8 homes share each transformer." | Illustrative. 8 homes per transformer, assumed | config:transformer.homes_per_transformer |
| 0:36.3 to 1:02.6 | P1 click Inventory in the side panel; click the segment button "EV and electric heat"; hover 69.07%. Markers: "Composite: a segment average, not a customer" on the Composite caption, then "Who can enroll: 69.07% of homes" on the headline | "The tool reads each home's hourly meter and lists its equipment. This Composite home is the average of 105 homes with an EV and electric heat, not a real customer. In all, 69% of homes qualify for at least one program." | Composite: a segment average, not a customer | ewu.demo.composite_2.homes; ewu.inventory.any_program_pct |
| 1:02.6 to 1:26.6 | P2 click Flag in the side panel; card "Sam, Illustrative" (first question); in the gaps between lines the pointer moves to the Moderate scenario button, then to the headline 26.18%, and rests. Marker on the headline with its %: "26.18% of transformers over limit by 2030" | "Rung one is Flag, Sam's first question. In a moderate 2030, 20% of homes add an EV and 15% add a heat pump. If cars charge whenever they plug in, 26% of transformers go over their limit." | 26.18% flagged | config:scenarios.moderate.ev_share; config:scenarios.moderate.hp_share; ewu.sensitivity.moderate.random.margin_115.flagged_pct; config:transformer.overload_limit |
| 1:26.6 to 1:42.8 | P2 before the line click x 1.50 (headline reads 3.74%), x 1.05 (42.84%), then x 1.15 (back to 26.18%), and rest on the button. Marker on the sizing chart: "Range, not one number: 3.74% to 42.84%" | "Transformer sizes are not known yet, so the tool shows a range, from 4% to 43%." | Range 3.74% to 42.84% | ewu.sensitivity.moderate.random.margin_150.flagged_pct; ewu.sensitivity.moderate.random.margin_105.flagged_pct |
| 1:42.8 to 2:14.5 | P3 click Shift in the side panel; card "Dana, Illustrative"; before the third line the pointer moves onto the green Shift part of the ladder bar and rests there (no tooltip over the headline). Marker on the headline 20.57% with its %: "Staggered, not a timer: same energy, overnight" | "Rung two is Shift. A plain timer that starts every car at once still leaves 24% of transformers over. The tool staggers them instead: each car gets its own late-night slot at half power, so Dana's car still charges overnight. That fixes 79% of flagged transformers, 21% of all, with no new equipment." | Timer leaves 24.28% over; staggering fixes 20.57% of all, 78.56% of flagged | ewu.shift.moderate.random.margin_115.timer.overloaded_pct; config:shift.stagger_start_hour; config:shift.stagger_end_hour; config:shift.stagger_power_share; ewu.sensitivity.moderate.random.margin_115.shift_fixed_pct; ewu.shift.moderate.random.margin_115.staggered.fixed_pct |
| 2:14.5 to 2:31.4 | P4 click Protect in the side panel; before the second line the pointer rests on 2.70% in the so-line. Marker on 2.70%: "2.70% still over in the cold snap" | "Rung three is Protect. In the coldest two days, at -5 F, shifting is not enough: 2.7% of transformers still go over." | Feb 7-8, coldest hour -5.0 F | ewu.coldsnap.window_min_temp_f; ewu.coldsnap.moderate.staggered.margin_115.flagged_pct |
| 2:31.4 to 3:00.1 | P4 card "The Riveras, Illustrative" (host a battery, room for a charger); before the second line click "2 host homes" (the load with batteries redraws) and rest on the button. Marker on the so-line: "Batteries carry the cold snap shifting cannot" | "The Riveras host two battery units, picked by the tool's fit score. One host home clears 90% of those transformers, two hosts 93%, and no one's heat is turned down. Two units also give every home we tested room for an EV charger; with none, only 0.5% have it." | One host 89.88%, two hosts 92.84%; charger room 0.5% of homes with no battery | config:battery.energy_kwh_two_units; ewu.coldsnap.moderate.staggered.margin_115.hosts_1.cleared_pct; ewu.coldsnap.moderate.staggered.margin_115.hosts_2.cleared_pct; ewu.headroom.ev.charge_measured_mean.pass_pct_none; ewu.headroom.ev.charge_measured_mean.pass_pct_two_units |
| 3:00.1 to 3:12.8 | P5 click Upgrade in the side panel, then rest on the headline 0.42%; card "Sam, Illustrative" (spends capital last). Marker on the headline with its %: "Capital only where nothing else works" | "Rung four is Upgrade: Sam spends capital only where nothing else works, 0.4% of transformers." | Upgrade: 0.42% of transformers | ewu.sensitivity.moderate.random.margin_115.upgrade_left_pct |
| 3:12.8 to 3:33.1 | T1 full-screen Terminal, prompt `$` with a left margin, `bin/ewu screen --scenario moderate --margin 1.15` typed at a human pace and run for real; its real output prints at its real time, every line inside the screen. Marker on the Flag to Upgrade lines: "Live run on the full meter data" | "The same ladder runs live on the full meter data: 3,000 synthetic transformers, in seconds. Each run is one random grouping; the page pools five, each within 1.05 points." | Live run, full meter data; one grouping within 1.05 points of the pooled share | config:transformer.count; ewu.stress.moderate.random.margin_115.seed_gap_pts |
| 3:33.1 to 4:00.0 | P6 back in the app, click Money in the side panel; before the second line rest on $436.9M in the grey "Labeled scaling" line. Marker on that line: "Scaled to NYSEG: $436.9M against $226.8M" | "For Avangrid, the money is in shifting. Scaled to NYSEG, an assumption, upgrading every flagged transformer costs $436.9 million. The ladder costs $226.8 million; shift then upgrade, $189.9 million." | NYSEG scaling, an assumption: upgrade all $436.9M, ladder $226.8M, shift then upgrade $189.9M, present value | ewu.economics.moderate.random.margin_115.mid.nyseg_upgrade_all_musd; ewu.economics.moderate.random.margin_115.mid.nyseg_ladder_musd; ewu.economics.moderate.random.margin_115.mid.nyseg_shift_then_upgrade_musd |
| 4:00.0 to 4:10.0 | P6 rest on the $7,730 tie price. Marker on it: "Battery tie price, at placeholder prices" | "At placeholder prices, a battery beats the upgrade only below $7,730 a unit." | Prices are placeholders | ewu.economics.battery_vs_upgrade.mid.tie_unit_usd_equal_life |
| 4:10.0 to 4:20.7 | T2 the same Terminal, `bin/ewu screen --scenario moderate --margin 1.15 --map` typed, not run. Marker on `--map`: "Next: Avangrid's meter-to-transformer map" | "What the tool needs next is Avangrid's meter-to-transformer map; the same command runs on it with one flag." | Next: Avangrid's meter-to-transformer map | repo:ewu/cli.py:138 (`--map`) |
| 4:20.7 to 4:25.7 | C1 close card on the plain background: "Electrify Without Upgrade" and "Shift first. Batteries where shifting cannot reach. Capital last."; fade to black | (silence) | | |
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
| A plain timer that starts every car at once leaves 24.28% of transformers over | ewu.shift.moderate.random.margin_115.timer.overloaded_pct | measured |
| Staggering gives each car its own slot in a late window (23:00 to 3:00), at half power, same energy | config:shift.stagger_start_hour, config:shift.stagger_end_hour, config:shift.stagger_power_share; ewu/shift.py docstring | assumption (program design) |
| Staggering fixes 20.57% of all transformers, 78.56% of flagged ones | ewu.sensitivity.moderate.random.margin_115.shift_fixed_pct, ewu.shift.moderate.random.margin_115.staggered.fixed_pct | measured |
| "Dana's car still charges overnight" | same energy per session, start slot inside the late window (ewu/shift.py docstring) | illustrative, follows from the model |
| Coldest hour -5.0 F over Feb 7-8 | ewu.coldsnap.window_min_temp_f | measured (weather data) |
| 2.70% of transformers go over in the cold snap with staggered charging | ewu.coldsnap.moderate.staggered.margin_115.flagged_pct | measured |
| Two units hold 20.16 kWh | config:battery.energy_kwh_two_units | challenge spec |
| No one's heat is turned down | only EV sessions move (ewu/shift.py) and batteries only add supply; no code in ewu/ reduces heating load | follows from the model |
| Two battery units give every home without an EV room for a charger; with none, 0.5% have room | ewu.headroom.ev.charge_measured_mean.pass_pct_two_units, pass_pct_none (new peak within today's peak plus 3 kVA, 29,793 homes) | measured |
| One host clears 89.88%, two hosts 92.84% | ewu.coldsnap.moderate.staggered.margin_115.hosts_1.cleared_pct, hosts_2.cleared_pct | measured (dispatch model, recomputed by checks/recompute_battery.py) |
| Hosts are picked by fit score | ewu/fitscore.py | measured method |
| Live run on 3,000 synthetic transformers in seconds | config:transformer.count; the run's own last line | measured (one seed) |
| One random grouping's flagged share is within 1.05 points of the five-grouping mean | ewu.stress.moderate.random.margin_115.seed_gap_pts | measured |
| Scaled to NYSEG: upgrade every flagged transformer $436.9M, ladder $226.8M, shift then upgrade $189.9M, present value | ewu.economics.moderate.random.margin_115.mid.nyseg_upgrade_all_musd, nyseg_ladder_musd, nyseg_shift_then_upgrade_musd | measured on placeholder prices and an assumed scaling |
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
| flag | P2 | Inventory | clicks Flag, points at Moderate, hovers 26.18%, clicks x 1.50, x 1.05, x 1.15 |
| shift | P3 | Flag | clicks Shift, rests on the ladder bar |
| protect | P4 | Shift | clicks Protect, hovers 2.70%, clicks 2 host homes |
| upgrade | P5 | Protect (2 hosts) | clicks Upgrade, hovers 0.42% |
| terminal | T1, T2 | a fresh full-screen Terminal | the wrapper types and runs the command, then types the `--map` line without running it |
| money | P6 | Upgrade | clicks Money, hovers $436.9M, $7,730 |

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
| Business value (40) | Upgrade 0.42%, then Money in dollars scaled to NYSEG: $436.9M to upgrade every flag against $226.8M for the ladder, tie price $7,730 at placeholder prices |
| Analytics and modeling (35) | Inventory: equipment read from meters, Composite segment; Flag: range over sizing; Shift: a plain timer leaves 24.28% over, staggering fixes 78.56% of flags; Protect: hour by hour battery dispatch in the cold snap; terminal: one grouping within 1.05 points of the pooled answer |
| Presentation (15) | One planner, two households as cards, four rungs plus the money, each reached from the side panel with one marker at a time |
| Innovation (10) | The live run on the full data; the same command on a real map |

## Round 1 changes

v3 (`outputs/video/ewu_demo_v3.mp4`) answers simulated judge round 1 on v2 (people impact the lowest criterion; scores in the round's
record) and the v2 gate report (`outputs/video/check_v2.md`). Shared fixes first, then the lowest
criterion, then the rest.

| Fix | From | Applied? | What changed, or why not |
|---|---|---|---|
| Shift: a plain timer still leaves 24% over; cut the 53% line; marker "Staggered, not a timer: same energy, overnight" | both used judges (exec fix 3, customer programs fix 2) | applied | new second Shift line (ewu.shift...timer.overloaded_pct 24.28), 79% of flagged said aloud (78.56), the 53% line is gone, marker relabeled and drawn round the headline with its %; the exec's "95.38% of overload hours stay under with no new EV" line is not added (length: the film would pass 4:30) |
| Riveras: what changes for a household | customer programs fix 1 (people impact, the lowest criterion) | applied, reworded | "One host home clears 90%..., two hosts 93%, and no one's heat is turned down. Two units also give every home we tested room for an EV charger; with none, only 0.5% have it." Card subtitle "Host a battery, room for a charger". Not said: "without a service study" (the model tests peak plus 3 kVA, not a utility process) and "Level 2" (the test uses measured mean charging power) |
| Flag and Upgrade name Sam, with Sam cards | v2 gate 6 | applied | "Rung one is Flag, Sam's first question"; "Rung four is Upgrade: Sam spends capital only where nothing else works"; two Illustrative Sam cards |
| Money in dollars: box the Labeled scaling line, say $436.9M, $226.8M, $189.9M | exec fix 1 | applied | marker "Scaled to NYSEG: $436.9M against $226.8M" on the grey line, the pointer rests on $436.9M; the three nyseg_*_musd facts are spoken; "an assumption" said aloud; the 43.47% and 51.92% lines are cut for length |
| Terminal: explain 26.00 vs 26.18 | exec fix 2 | applied in narration | "Each run is one random grouping; the page pools five, each within 1.05 points." (ewu.stress...seed_gap_pts, a flagged-share gap); no separate marker on the Upgrade 0.60 row, because 1.05 points is about the flagged share and the table marker already boxes all four rows |
| Pointer still while a line is read | v2 gate 8 | applied | every move now plays in the gap before its sentence (video/gaps.py sizes the gap from each glide's length, geometry from the v2 take logs in video/geometry.json) |
| Pointer on the digits, box edge through the % | v2 gate 8 | applied | hovers aim at a number's bottom right corner; headline markers box `.big` (number and %) |
| Shift tooltip over 26.18% | v2 gate 8 | applied | the Shift take no longer hovers the headline; the pointer rests on the ladder bar |
| Terminal lines wrap at the right edge | v2 gate 5 | applied | `bin/ewu screen` prints its two long lines as four lines under 80 columns (ewu/screen.py); the take indents every line two columns and starts one row down |
| Fade from and to black | v2 gate 7 | applied | video/build.py took min() of the two ramps; now max() |
| Source-key tooltips 11 to 14 px; the line promising "its source key appears" | v2 gate 5 | applied, by removal | the line is cut, and every rest now lands on the % (or M) after a number, outside its span, so no 11 to 14 px tooltip opens; this drops v2's on-screen proof of the fact keys (the side panel foot still says "hover it for the key") |
| Marker label "69.07% of homes qualify for a program" | gate 3 on the first v3 draft | relabeled | "Who can enroll: 69.07% of homes": the old label read so close to the page headline (ratio 0.8 or more) that the gate's OCR dropped the page line as if it were the label |
| Type floor: film the page at 170% | v2 gate 5 | skipped | at 170% Inventory, Protect and Money lose their lower half below the fold (checked with headless Chrome), and the brief forbids scrolling; person cards went from 26 to 30 px role text |
| Held-out judge's fixes | held out | not applied, by rule | |

No earlier round's fix was undone: v2 was the first film judged.
