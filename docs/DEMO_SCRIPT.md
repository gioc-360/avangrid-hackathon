# Demo script: three minutes, one page, one live command

The demo is the offline page `outputs/demo/ewu_demo.html` plus one terminal command run live on the full meter
data. Each row is one click, one sentence to say, and the judge objection that sentence answers. Every number
below traces to facts/facts.json or config/ewu.yaml (`checks/trace_numbers.py docs/DEMO_SCRIPT.md`); the page
shows the same numbers, each with its key on hover. Results are for the moderate 2030 scenario (20% of homes add
an EV, 15% a heat pump), transformers rated at today's group peak times 1.15, random grouping, unless a row
says otherwise.

## Before you go on

- Run `bin/ewu demo` to build and open the page. It needs no network and no server.
- Open a terminal in the repo with `bin/ewu screen --scenario moderate --margin 1.15` typed and not yet run.
- On the page, leave the screen step on Moderate, x 1.15, Random neighbors: the money step reads the same choice.
- Keep the page on this laptop. Step 1 shows Composite homes (segment averages, no real customer) and the cold
  snap step shows one synthetic transformer's summed load with fleet battery charge, but the page file still
  holds that transformer's hourly values, so it is never uploaded or shared; record the screen, not the file.

## The click path

| Time | Click | Say (one sentence) | Objection it answers |
|---|---|---|---|
| 0:00 | Page open at the top | "This finds the neighborhood transformers that 2030 EVs and heat pumps will overload and gives each the cheapest fix in order: Flag, Shift, Protect, Upgrade." | "What does it actually do?" |
| 0:15 | Inventory: click EV home, then Electric heat, in the Composite home picker | "Each Composite home is a segment average, not a customer; equipment is read from each home's hourly meter alone, with a confidence word per device, and 69.07% of the 33,757 usable homes qualify for at least one program." | "Where is the tool the challenge asked for, the appliance inventory and program list?" |
| 0:35 | Hover any number on the page | "Every number on this page carries the key of the fact the code wrote, and a check fails the build if one does not match." | "Did you type these numbers?" |
| 0:45 | Screen: Moderate, x 1.15, Random neighbors | "In the moderate case 26.18% of transformers go over the limit with unmanaged charging; staggered charging fixes 20.57%, home batteries clear 5.23%, and only 0.42% are left for an upgrade." | "How big is the problem, and how much of it needs a new transformer?" |
| 1:05 | Screen: click x 1.05, then x 1.50 | "Transformer sizing is the input we know least, so we show the flagged share at every sizing, from 42.84% down to 3.74%, and report a range, never one number." | "Your headline depends on how big the transformers are." |
| 1:20 | Screen: click Same-segment neighbors, then back to Random neighbors | "If neighbors are alike, flagged transformers rise to 32.65% and the upgrade share to 1.55%, but the order of fixes holds." | "Random grouping ignores that adoption clusters." |
| 1:35 | Terminal: run `bin/ewu screen --scenario moderate --margin 1.15` | "This is the same ladder running live on the full meter data, one of the five seeds, in seconds (the check fails it at 60); it printed 26.00% flagged against 26.18% pooled." | "Is this real or a cached chart?" |
| 1:55 | Cold snap: click 1 host home, then 2 host homes | "Through Feb 7-8, coldest hour -5.0 F, one host home with two battery units clears 89.88% of the transformers the cold snap pushes over, and two hosts clear 92.84%." | "A battery was never tested on a long cold night." |
| 2:15 | Cold snap: point at the fleet battery charge lines | "Across every flagged transformer the battery runs all year and charges only when the transformer has room under the limit, so its charge on the first cold night is earned, not assumed full." | "You assumed the battery starts full." |
| 2:25 | Money: point at the three bars | "On an equal-life basis the full ladder costs 51.92% of upgrading every flagged transformer, 30.8% to 151.19% across all 16 grid cells and price cases, and shifting then upgrading costs 43.47%." | "Batteries do not avoid an upgrade; they last half as long." |
| 2:45 | Money: point at the tie price | "At placeholder prices a battery beats the upgrade only below $7,730 a unit, so shifting is where the money is and batteries go where shifting cannot reach." | "Are batteries worth it at all?" |
| 2:55 | Back to the terminal | "Give us the meter-to-transformer map and the same command runs on it with `--map`, no other change." | "Your transformers are synthetic." |

## If something breaks

- Page will not open: `bin/ewu demo --no-open`, then open `outputs/demo/ewu_demo.html` from Finder.
- Terminal command fails or hangs: show `docs/demo/cli_output.txt`, the stored output of the same command.
- Page will not render: the step screenshots are in `outputs/private/demo_shots/` on this machine only; the deck
  carries the aggregate numbers above.

## Questions after the demo

Code questions are answered with file and line in `docs/CODE_QA.md`; the reasoning behind the heat pump and EV
split is in `docs/FINDINGS.md`.
