# Demo script: three minutes, one page, one live command

The demo is the offline page `outputs/demo/ewu_demo.html` plus one terminal command run live on the full meter
data. Each row is one click, one sentence to say, and the judge objection that sentence answers. Deck v3 is final,
so the page and this script carry deck v3's numbers only: our engine's deck profile (the team's battery path
on the teammate's arrays), money on v3's basis. Every number below traces to facts/facts.json or
config/ewu.yaml (`checks/trace_numbers.py docs/DEMO_SCRIPT.md`); the page shows the same numbers, each with its key
on hover. Results are for the moderate 2030 scenario (20% of the homes that can add one add an EV, 15% a heat pump)
at the 120% loading limit, unless a row says otherwise. The page and this script use deck v3's terms, one per
idea (docs/TERMS.md): overloaded, loading limit, fixed by batteries, upgrade, net cost (after the lease and NYSERDA), Upgrade all, saving.

## Before you go on

- Run `bin/ewu demo` to build and open the page. It needs no network and no server. It opens on Summary.
- Open a terminal in the repo with `bin/ewu screen` typed and not yet run (the deck profile is the default).
- On the views with controls, leave Scenario on Moderate and Loading limit on 120% (the pressed buttons name it; each view's
  "How this is computed" spells it out). Move between views by clicking the left side panel, not by scrolling.
- Every assumption, source and caveat sits in each view's closed "How this is computed"; an "est." tag or the
  "Synthetic network" tag opens it. Open one only if a judge asks.
- Keep the page on this laptop. It shows synthetic transformers (8 homes summed) and Composite homes, never a real
  home, but the file holds per-transformer hourly values, so it is never uploaded or shared; record the screen.

## The click path

| Time | Click | Say (one sentence) | Objection it answers |
|---|---|---|---|
| 0:00 | Page open on Summary | "Deck v3 in one table: batteries fix 92% to 98% of overloaded transformers, and net cost is 58% to 69% less than upgrading all of them." | "What is the answer?" |
| 0:15 | Panel: Network, then Today | "This is the grid we plan: one substation, 6 feeders and all 3,000 transformers, every one within limit today." | "Is this a dashboard or a planning tool?" |
| 0:25 | Step: 2030: Flag | "Add 2030's EVs and heat pumps and 292 transformers are overloaded." | "How big is the problem?" |
| 0:35 | Step: + Place batteries | "Batteries, one to four units each, fix 287 of them." | "Where do batteries go?" |
| 0:45 | Step: + Upgrade | "Only 5 of 3,000 transformers need an upgrade, and you can see exactly where they sit." | "How many need an upgrade?" |
| 0:55 | Click an orange square, then Next: Upgrade | "Each transformer opens to its 8 homes summed on its worst 2030 day: base, EV and heat pump against its limit, and the fix it gets." | "Which loads drive it?" |
| 1:08 | Point at the Synthetic network tag | "The transformers are real homes' meter data grouped 8 to a transformer, and the feeders are an illustrative split; load your map and it is your network." | "Your network is made up." |
| 1:18 | Terminal: run `bin/ewu screen` | "Same engine, live on the full meter data in seconds: 9.7% of transformers overload in the moderate scenario and 29.9% in the high, with the money columns deck v3 shows." | "Is this real or a cached chart?" |
| 1:33 | Panel: Inventory; click EV home, then Electric heat | "Technology is read from each home's hourly meter alone, and 69.07% of the 33,757 usable homes are eligible for at least one program." | "Where is the technology inventory and program list?" |
| 1:48 | Panel: Flag; click 100%, then 140%, then back to 120% | "The loading limit is the input we know least: overloaded runs from 30.0% at a 100% limit down to 2.4% at 140%, and deck v3 reports 120% with the others as its sensitivity." | "Your headline depends on the limit you picked." |
| 2:05 | Panel: Overview; click High, then back to Moderate | "In the high scenario 29.9% are overloaded, batteries still fix 92% of them, and 2.5% of all transformers need an upgrade." | "Does it hold in the High 2030 scenario?" |
| 2:18 | Panel: Place | "Each overloaded transformer gets the fewest battery units that cover every day's excess, coldest nights included: 1.5 battery units on average here, 1.9 in the high scenario." | "A battery was never tested on a long cold night." |
| 2:35 | Panel: Money | "On deck v3's basis net cost is $34.3M against $111.0M for Upgrade all, a 69% saving; gross cost, before the lease and NYSERDA, is $116.6M, so the saving rests on those two." | "Are batteries worth it at all?" |
| 2:55 | Back to Summary | "The 2,610 priority homes also make an 8.8 MW summer peak cut, and with your meter-to-transformer map the same command runs on it with `--map`, no other change." | "Your transformers are synthetic." |

## If something breaks

- Page will not open: `bin/ewu demo --no-open`, then open `outputs/demo/ewu_demo.html` from Finder.
- Terminal command fails or hangs: show `docs/demo/cli_output.txt`, the stored output of the same command (its
  first block; the second is the earlier cautious method, kept in the CLI only).
- Page will not render: one screenshot per view is in `outputs/private/demo_shots/` (deck.png for Summary, then
  network.png to money.png), on this machine only.

## Questions after the demo

Code questions are answered with file and line in `docs/CODE_QA.md`; the reasoning behind the heat pump and EV
split is in `docs/FINDINGS.md`.
