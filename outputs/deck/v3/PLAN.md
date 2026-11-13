# D4G deck v3: plan for the number update and the added slides

Prep only. Nothing in `~/Downloads` was touched; the v3 deck has not been written. Every number below that comes from
the engine is a snapshot of facts/facts.json at 14:50 ET on 2026-11-13 and will move when the run that is feeding the
teammate's arrays finishes. Rerun the dry run then; read its log, not this file, for final values.

## 1. Run order once the other run has finished

```
 facts.json final            inventory (unchanged deck)          fact map                      new deck
+----------------------+    +--------------------------+    +------------------------+    +--------------------------+
| other run commits    | -> | deck/v3/inventory.py     | -> | deck/v3/build_fact_    | -> | deck/v3/apply.py         |
| ewu.deck.* facts     |    | numbers.csv (2,575 rows) |    | map.py: fact_map.yaml  |    | --dry-run, read the log, |
+----------------------+    +--------------------------+    +------------------------+    | then without: D4G_v3.pptx|
                                                                                          +-------------+------------+
                                                                                                        |
                                                                          render with deck/v3/render_ppt.py, look at 2, 12, 15, A13
```

```
.venv/bin/python -I deck/v3/inventory.py outputs/deck/v3/source_copy.pptx outputs/deck/v3/numbers.csv
.venv/bin/python -I deck/v3/build_fact_map.py outputs/deck/v3/numbers.csv deck/v3/fact_map.yaml
.venv/bin/python -I deck/v3/apply.py outputs/deck/v3/source_copy.pptx --dry-run
.venv/bin/python -I deck/v3/apply.py outputs/deck/v3/source_copy.pptx          # writes outputs/deck/v3/D4G_v3.pptx
cp outputs/deck/v3/D4G_v3.pptx outputs/deck/v3/render_src_v3.pptx
.venv/bin/python deck/v3/render_ppt.py outputs/deck/v3/render_src_v3.pptx outputs/deck/v3/render_v3
```

apply.py refuses to write if a mapped key is missing, if a paragraph's text or an old number no longer matches the
inventory, or if a format would turn a number into a different kind (for example "5,220" into "5,220 units"). It never
overwrites: a second run writes D4G_v3b.pptx. A scratch write was rendered once to check the charts: slide 12's two
charts keep their colors and labels after `chart.replace_data`.

## 2. One decision before running: whose fleet supplies the peak cut

`aliases.peak_source.selected` in fact_map.yaml. It is set to `teammate_rerun`.

| Choice | Peak cut, hosts (now) | What stays consistent | What goes stale |
|---|---|---|---|
| teammate_rerun (set) | 8.80 MW, 2,610 homes: our audit's rerun of her fleet code on our load matrix | slides 7, 9, 10, A9, A10 per-segment counts, scatter legend, July fleet chart all describe the same 2,610 homes | nothing; the headline stays 8.8 MW |
| ours | 9.05 MW, 2,733 hosts: ewu.deck.peakcut (same 4 kW and 2 kW thresholds, our simulation) | slides 2, 10, 11, 13, 15, A11 move together | 1,745 / 341 / 232 / 212 / 68 / 12 by segment, 4,544 secondary, 26,603 not a candidate, the slide 9 scatter and the slide 10 July chart still describe 2,610 homes |

With `ours` the dry run changes 8.8 MW to 9.1 MW, 11% to 12%, 2,610 to 2,733, $36.5M to $38.3M and the A11 table.

## 3. What the current dry run changes (93 of 207 mapped numbers)

The headline wording that moves most, today's facts:

| Where | Final deck | v3 now | Source |
|---|---|---|---|
| Title s2, s11 verdict, s15 | 70% to 79% less | 69% to 78% | 1 - net / upgrade-all, deck basis |
| s2 problem | 10% to 30% overload | 10% to 30% | ewu.deck.{moderate,high}.limit_120.overloaded_pct (9.73, 29.87) |
| s2, s12 footer | 73% to 89% winter | 80% to 90% | winter_of_overloaded_pct (79.79, 89.96), her majority-of-hours rule |
| s2, s15 | 94% to 98% fixed | 92% to 98% | fixed_of_overloaded_pct (91.63, 98.29) |
| s2, s12 chart | $34M vs $164M; $151M vs $498M | $35M vs $162M; $157M vs $498M | rebuilt from our counts, upgrade at full $15,000 |
| s12 | upgrade 2% to 7% | 2% to 8% | 100 - fixed |
| s13 | $130M to $347M less capital | $127M to $341M | upgrade-all - net |
| A13 | ten sensitivity rows | all money and % cells recomputed | counts at limit 110, 120, 140; upgrade $10k, $15k, $20k |

Money basis: the engine's own money facts count the upgrade for 15 of its 40 years ($10,248, the spec's
"$33M vs $112M"). The final deck shows the upgrade at its full $15,000 ("$34M vs $164M"). v3 keeps the deck's basis,
rebuilt from our engine's counts (overloaded, batteries, upgrades) with the formula the audit verified to the decimal
(docs/TEAMMATE_AUDIT.md section 1). To switch basis, change `U` in `money()` of build_fact_map.py.

All five claims in fact_map.yaml still hold on today's facts (gross cheaper than upgrading at $15,000 and costlier in
the high case at $10,000; peak-only fleet below 1.0 benefit to cost; most overloads fixed; most overloads winter).
apply.py prints any claim that stops holding, and any "A to B" range whose order flips.

## 4. Pending and no source

| Numbers | Status | Needs |
|---|---|---|
| s2 and s8: 30.8 MW average, 39% load factor | pending | `insight.system_mean_mw` (mean combined load); nothing in facts.json holds it |
| s12 stacked chart: fixed by 1 or 2 units, by 3 or 4 units (four bars) | pending | `ewu.deck.{moderate,high}.limit_120.fixed_units_1_2` and `fixed_units_3_4`. Until then the bars (8.9 + 0.8 + 0.2) no longer add to the new category label (9.7%); fallback: one "Fixed by batteries" series = fixed / 3,000 |
| s13: 23% to 44% more energy sold | no source | added EV and heat pump kWh over today's kWh of the sampled homes; suggested key `ewu.deck.{s}.limit_120.added_energy_pct`, or cut the line |

## 5. Demo video slide

Recommendation: do not put the film in the main flow after slide 12 as it stands. `~/Downloads/EWU_demo_video.mp4`
(4 min 29 s, 7.8 MB) shows the earlier cautious numbers, so its screens would contradict slide 12 one click later.

```
 main flow                                        appendix
+-----+   +-----+   +----------------------+      +-----+   +---------------------+   +-----+   +-----+
| 12  |-->| 13  |   | 12b "Demo: the tool  |      | A16 |-->| A17 Analytical tool |-->| A18 |-->| A19 |
| Rec.|   |     |   |  flags every         |      |     |   | film or network     |   | How |   | Tech|
+-----+   +-----+   |  transformer" (only  |      +-----+   | still               |   | the |   | specs|
                    |  if refilmed)        |               +---------------------+   | eng.|   +-----+
                    +----------------------+                                         +-----+
```

- If the film is refilmed on the deck profile after the other run: new slide 12b right after slide 12, titled
  "Demo: the tool flags every transformer and prices the fix", film embedded, poster frame = the Network view.
- If not refilmed: embed the existing film in A17 with a one-line caption "Earlier settings; current numbers on slides
  2 and 12", or skip the film and use a still of the current Network view (section 7).

## 6. Engine slides

`~/Downloads/EWU_engine_slides_c.pptx` holds two slides: "How the engine works" (architecture picture) and "Tech specs".
They go after A17 as A18 and A19 (diagram above). Same 16:9 size as the deck (12,191,695 vs 12,192,000 EMU wide).
python-pptx cannot copy slides between decks with their layouts intact: insert them in PowerPoint (Home, New Slide,
Reuse Slides, keep source formatting) into the written D4G_v3.pptx, then add both to the appendix index on slide 16.

Stale on arrival: the Tech specs slide says "Screens 3,000 transformers in 2.4 s"; `ewu.deck.seconds` now reads 3.3 s.
Rebuild both with `deck/engine_slides.py` (numbers from facts via `deck/engine_specs.py`) after the other run finishes.

## 7. "Simulated" label lines

Each line names the simulation in the slide's own terms. The numbers in them come from config (3,000 transformers,
8 homes, 120%), the same values A12 shows. Add them in PowerPoint after apply.py, then rerun inventory.py so the
new numbers are listed.

| Slide | Where | Line |
|---|---|---|
| 2 | under "of neighborhood transformers overload by 2030", small grey | Simulated: 3,000 synthetic transformers, each serving 8 real homes; no meter to transformer map in the data. |
| 12 | first sentence of the grey footer box | Simulated 2030 stress test on 3,000 synthetic transformers of 8 real homes; overloaded = any hour above 120% of rating. |
| 15 | under the three stats | Transformer results simulated on 3,000 synthetic transformers built from 33,757 real meters. |

## 8. A17 "Tool screenshot to be added"

Fill it with a screenshot of the Network view (Network tab, "2030: Flag") of the demo page in the deck profile, taken
after the other run. Do not reuse `outputs/video/network/network_flag_b.png`: it says "780 of 3,000 transformers go over
their limit", the earlier cautious screen. The deck profile now gives 917 over (high) and 312 (moderate)
(`ewu.deck.network.{high,moderate}.flag.over`); the page's own "Synthetic network" chip doubles as the simulated label.

A17's text also describes the teammate's tool ("python run.py config.yaml", "customer_inventory.csv"). If the slide is
meant to show our tool, its four steps become: input (hourly AMI, weather, labels; settings in config/ewu.yaml); run
(`bin/ewu screen`, `bin/ewu plan`, `bin/ewu demo`); output (transformer action list, capital plan, offline demo page);
repo (README, tests, facts.json; no customer data committed).

## 9. Numbers baked into images

| Image | Numbers in it | Stale after v3? |
|---|---|---|
| s20 A4 load signatures (six panels) | 5,190; 4,625; 23,942; 16,833; 11,928; 4,996; 433; 525; 10.9%, 4.6%, 2.3%, 0.4% | No: her classification, kept as teammate-only, and the text on s4 and A3 shows the same counts |
| s24 A8 example priority home, July 2 | cut from 6.2 to 3.6 kW; overnight charging 2.6 kW | No: her battery simulation, teammate-only. Note: it plots one real home's hours (the audit lists its source figure as single-home data) |
| s1, s15 logo and headshots | none | No |
| Demo film (section 5) | cautious-era screens | Yes |
| Network stills in outputs/video/network | "780 of 3,000" | Yes |
| Engine slides A18 picture, A19 text | architecture labels; "2.4 s" | A19 yes (rebuild) |

So no picture inside the deck itself carries a model number that v3 changes; the stale images are the film, the
old network stills and the engine slides' tech specs.

## 10. Other things the map found

- A1 and A16 say 1,402 customers missing plus 85 empty; our facts say 1,487 missing (data.customers_missing). Same
  total (1,968 not usable), split differently. Kept.
- A12 "start times from 20,800 observed sessions" is the teammate's array; the audit rebuilds it from 266 EV homes on
  145 mild days. Kept as teammate-only.
- s11 "about $3,000 net cost per transformer fixed" is mean units of both scenarios times $1,978, to the nearest $1,000;
  it stays $3,000 on today's facts.
- outputs/deck/v3 is not covered by .gitignore except its .pptx files: numbers.csv, the renders (including s24's
  single-home picture) and this file would be picked up by `git add -A`. Only deck/v3 was committed.
