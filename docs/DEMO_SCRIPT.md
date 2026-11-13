# Demo script: three minutes, one page, one live command

The demo is the offline page `outputs/demo/ewu_demo.html` plus one terminal command run live on the full meter
data. Each row is one click, one sentence to say, and the judge objection that sentence answers. Every number
below traces to facts/facts.json or config/ewu.yaml (`checks/trace_numbers.py docs/DEMO_SCRIPT.md`); the page
shows the same numbers, each with its key on hover. Results are for the moderate 2030 scenario (20% of homes add
an EV, 15% a heat pump), transformers rated at today's group peak times 1.15, random grouping, unless a row
says otherwise.

## Before you go on

- Run `bin/ewu demo` to build and open the page. It needs no network and no server. It opens on Network, Today.
- Open a terminal in the repo with `bin/ewu screen --profile cautious --scenario moderate --margin 1.15` typed and not yet run.
- On the other views, leave the case on Moderate, x 1.15, Random (the pressed buttons name it; each view's
  "How this is computed" spells it out). Move between views by clicking the left side panel, not by scrolling.
- Every assumption, source and caveat sits in each view's closed "How this is computed"; an "est." tag or the
  "Synthetic network" tag opens it. Open one only if a judge asks.
- Keep the page on this laptop. It shows synthetic transformers (8 homes summed) and Composite homes, never a real
  home, but the file holds per-transformer hourly values, so it is never uploaded or shared; record the screen.

## The click path

| Time | Click | Say (one sentence) | Objection it answers |
|---|---|---|---|
| 0:00 | Page open on Network, Today | "This is the grid we plan: one substation, 6 feeders and all 3,000 transformers, every one within its limit today." | "Is this a dashboard or a planning tool?" |
| 0:12 | Ladder: 2030: Flag | "Add 2030's EVs and heat pumps with charging unmanaged and 780 transformers go over their limit." | "How big is the problem?" |
| 0:22 | Ladder: + Shift | "Staggering EV charging fixes 615 of them with no new hardware." | "What is the cheapest fix?" |
| 0:32 | Ladder: + Protect | "Home batteries at the best-fit host homes clear 149 more." | "Where do batteries go?" |
| 0:42 | Ladder: + Upgrade | "Only 18 of 3,000 transformers need a new one, and you can see exactly where they sit." | "How much of it needs a new transformer?" |
| 0:52 | Click a red square, then Next new transformer | "Each transformer opens to its 8 homes summed on its worst 2030 day: base, EV and heat pump against its limit, and the fix it gets." | "Which loads drive it?" |
| 1:05 | Point at the Synthetic network tag | "The transformers are real homes' meter data grouped 8 to a transformer, and the feeders are an illustrative split; load your map and it is your network." | "Your network is made up." |
| 1:15 | Terminal: run `bin/ewu screen --profile cautious --scenario moderate --margin 1.15` | "Same network, live on the full meter data in seconds: 780 flagged, 615 shifted, 149 protected, 18 to upgrade." | "Is this real or a cached chart?" |
| 1:30 | Panel: Inventory; click EV home, then Electric heat | "Equipment is read from each home's hourly meter alone, and 69.07% of the 33,757 usable homes qualify for at least one program." | "Where is the appliance inventory and program list?" |
| 1:45 | Panel: Overview, then Flag; click x 1.05, then x 1.50 | "Pooled over five seeds, 0.42% need an upgrade; transformer sizing is the input we know least, so flagged runs from 42.84% down to 3.74% and we report a range." | "Your headline depends on how big the transformers are." |
| 2:05 | Overview: click Same segment, then back | "If neighbors are alike, the upgrade share rises to 1.55%, but the order of fixes holds." | "Random grouping ignores that adoption clusters." |
| 2:15 | Panel: Protect; click 1 host home, then 2 host homes | "Through Feb 7-8, coldest hour -5.0 F, one host home clears 89.88% of the transformers the cold snap pushes over and two clear 92.84%, with the battery's charge earned all year." | "A battery was never tested on a long cold night." |
| 2:35 | Panel: Money | "The full ladder costs 51.92% of upgrading every flagged transformer, and a battery beats the upgrade only below $7,730 a unit, so shifting is where the money is." | "Are batteries worth it at all?" |
| 2:55 | Back to Network | "Give us the meter-to-transformer map and the same command runs on it with `--map`, no other change." | "Your transformers are synthetic." |

## If something breaks

- Page will not open: `bin/ewu demo --no-open`, then open `outputs/demo/ewu_demo.html` from Finder.
- Terminal command fails or hangs: show `docs/demo/cli_output.txt`, the stored output of the same command.
- Page will not render: one screenshot per view is in `outputs/private/demo_shots/` (network.png to money.png),
  and every Network ladder step is in `outputs/video/network/`, on this machine only.

## Questions after the demo

Code questions are answered with file and line in `docs/CODE_QA.md`; the reasoning behind the heat pump and EV
split is in `docs/FINDINGS.md`.
