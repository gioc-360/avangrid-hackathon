# D4G deck v3: what changed from the final submission

File: `~/Downloads/D4G Cornell 2_Final Submission_v3.pptx` (35 slides; the final submission has 33 and is untouched).
Every model number now comes from our engine's deck profile (the team's battery-only method run in our engine on the
teammate's arrays), facts as of 15:17 ET on 2026-11-13. 98 of 215 mapped numbers changed; 33 outside the A13 table.

## Money basis (one basis on every slide)

All dollar figures use our engine's basis (ewu/deck_money.py): present value over 15 years at 7%, batteries net of
the customer lease and NYSERDA, and an upgrade counted for the 15 of its 40 years the program runs, so a $15,000
upgrade counts as $10,248. The final deck counted the full $15,000 against 15 years of batteries, which made the
saving look larger. This is why the headline moves from "70% to 79%" to "58% to 69%". Slide 11's speaker notes and
the A13 footer state the basis.

## Per slide, old -> new

| Slide | Old | New |
|---|---|---|
| 2 title | 70% to 79% less than upgrading | 58% to 69% less |
| 2 problem | 73% to 89% of overloads on winter nights; upgrading all costs $164M to $498M | 80% to 90%; $111M to $340M |
| 2 impact | 94% to 98% fixed; net $34M vs $164M (moderate), $151M vs $498M (high) | 92% to 98%; $34M vs $111M, $144M vs $340M |
| 2 | (none) | two small lines: "Simulated on 3,000 synthetic transformers of real homes" |
| 2, 8 | 30.8 MW average, 39% load factor | unchanged, now recorded as facts (insight.system_mean_mw, system_load_factor_pct) |
| 11 verdict | Pays: 70% to 79% below upgrading | 58% to 69% |
| 11 notes | (none) | money basis paragraph appended |
| 12 step 4 | 2% to 7% of overloads | 2% to 8% |
| 12 left chart | categories 9.8% / 29.8%; bars 8.9, 0.8 / 20.8, 7.1, 1.9 | 9.7% / 29.9%; fixed by 1 or 2 units 8.4 / 20.2, by 3 or 4 units 1.2 / 7.1, upgrade 0.2 / 2.5 |
| 12 right chart | $164M vs $34M; $498M vs $151M | $111M vs $34M; $340M vs $144M |
| 12 footer | 73% to 89% winter; $271M high without NYSERDA | 80% to 90%; $261M |
| 12 | (none) | "Simulated on 3,000 synthetic transformers of real homes" under step 4 |
| 13 Avangrid | $130M to $347M less capital | $77M to $197M |
| 13 Grid | 26 to 100 MW across NYSEG | 28 to 98 MW |
| 15 stats | 94% to 98%; 70% to 79% | 92% to 98%; 58% to 69% |
| 15 | (none) | "Overload and cost results simulated on 3,000 synthetic transformers of real homes" |
| 16 index | A1 to A17 | adds A18 How the engine works, A19 Tech specs |
| 29 (A13) table | 65 cells | all overload %, fixed %, money and saving cells recomputed; savings now 40.9% to 76.4% |
| 29 (A13) footer | "Before those offsets, the battery path is cheaper at $15,000 or more per upgrade, and costlier in the high case at $10,000." | states the basis; "before those offsets the battery path costs more than upgrading in every row" (true on our numbers) |
| 33 (A17) | teammate's run.py tool, "Tool screenshot to be added" | our engine: bin/ewu reads hourly meter data and weather, simulates 2030 load on transformers, writes action lists; Network view screenshot (292 of 3,000 over, moderate 2030) captioned "Simulated" |
| 34 (A18, new) | | How the engine works: architecture figure |
| 35 (A19, new) | | Tech specs: measured specs figure, rerun today |

## Wording changed beyond numbers

- A13 footer (above): the old claim no longer holds on the engine basis; apply.py checks the new one.
- A17 title and its four steps now describe our tool, not the teammate's pipeline.

## Left as is

- Slide 13 "23% to 44% more energy sold": no source in either model. Kept unchanged; flag before presenting.
- Teammate-only numbers (her classification, segments, priority ranking, fleet run): slides 3 to 7, 9, 10 and
  A1 to A11, including 2,610 priority homes and the 8.8 MW peak cut (her ranking rerun on our data, consistent
  with slides 9 and 10) and the $36.5M fleet cost on slide 11.
- Behind the meter peak cut: the deck shows no behind-the-meter number, so nothing changed. If one is added,
  ours is 7.11 MW for 2,733 hosts (no fact exists for the earlier 2,612-home run).
- Slide 11 "about $3,000 net cost per transformer fixed, vs a $15,000 upgrade": 1.5 to 1.9 units at $1,978; the
  $15,000 is the upgrade's sticker price (notes explain).
- Pictures: A4 load signatures and A8 example home carry her numbers, unchanged; no picture in the deck carries a
  number v3 changes.
- No demo video in v3 (the film shows the earlier cautious numbers).

## For the teammate (paste)

I updated the deck to v3 so every model number comes from one engine run: your battery-only method and your
arrays, run in our engine on all 33,757 meters. The headline moves to 58% to 69% less than upgrading because
v3 counts each $15,000 upgrade for the 15 of its 40 years the program covers ($10,248), the same basis on
every slide; overloads are 10% to 30%, 92% to 98% are fixed by batteries, and your 2,610 homes and 8.8 MW are unchanged.
I also added a "simulated" label on slides 2, 12 and 15, replaced A17 with our tool and added A18 and A19;
the one line I could not source is "23% to 44% more energy sold" on slide 13, so it is unchanged and worth a check.
