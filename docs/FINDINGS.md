# Findings: does staggered EV charging fix heat pump night overloads?

Mostly yes, because on a cold night the heat pump fills the transformer and the new EV is what tips it over.
Heat pumps are running in 90.52% of the hours a transformer is over its limit, yet in 95.38% of those hours
the transformer would stay under the limit with no new EV load at all (moderate 2030 scenario). Staggering
cannot fix the transformers that overload on heat pumps alone, 1.97% of all transformers in the moderate
scenario and 11.73% in the high one, so those go to batteries or an upgrade.

Every number below comes from facts/facts.json (written by ewu/attribution.py and ewu/stress.py) or from
config/ewu.yaml, and `checks/trace_numbers.py docs/FINDINGS.md` fails the build if one does not. Unless a line
says otherwise, results are for random grouping of 8 homes per transformer, 3,000 synthetic transformers,
5 seeds, transformers rated at today's group peak times 1.15 and overloaded above 1.2 times the rating.

## The question

The teammate's case makes two claims that look like they collide. In the moderate scenario, 73% of
overloads are "driven by winter heat pump nights", and smart staggered EV charging fixes 8.7 of the 9.8
points of overloaded transformers, which is 88.8% of them. If most overloads were heat pump problems,
moving EV charging should fix few of them. Both claims can hold only if heat pumps decide when the
overloads happen while EVs decide whether they happen. We measured which one it is.

## The answer in numbers

| Result | Moderate 2030 | High 2030 |
|---|---|---|
| Transformers overloaded, EV charging unmanaged | 26.18% | 54.77% |
| Overload hours with heat pumps running | 90.52% | 94.81% |
| Overload hours where the heat pump is the larger cause | 4.57% | 13.61% |
| Overload hours where the EV is the larger cause | 95.43% | 86.39% |
| Overload hours that stay under the limit with no new EV load | 95.38% | 86.22% |
| Energy above the limit caused by EVs | 56.77% | 50.48% |
| Energy above the limit caused by heat pumps | 43.23% | 49.52% |
| Transformers overloaded, staggered charging | 5.65% | 22.35% |
| Overloaded transformers that staggering fixes | 78.56% | 59.43% |
| Transformers staggering newly overloads | 0.04% | 0.13% |
| Transformers that overload with no new EV at all | 1.97% | 11.73% |

## Why staggering works on heat pump nights

A new heat pump adds 0.05 kW for every degree below 60 F, so it adds a few kW for many hours. A new Level
2 charger adds 7.2 kW for the length of a session, 3.78 hours on average in the measured sessions. The heat
pump raises the floor all night; the charger is the spike that crosses the limit. That is why the heat pump is
running in 90.52% of overload hours while the EV is the larger cause in 95.43% of them. In the moderate
scenario the worst hour of only 0.61% of overloaded transformers is led by the heat pump (1.85% in the high
scenario). The teammate's 73% is consistent with our timing number, not with our cause number.

Staggering moves the same EV energy into the window that opens at hour 23 and closes at hour 3 of the clock, at half power, with each EV on a
transformer given its own start slot. Half power halves the spike, and separate slots stop two cars on one
transformer from stacking. Overload hours per transformer per year fall from 3.62 to 0.9 in the moderate
scenario and from 18.98 to 8.97 in the high one.

## What staggering cannot fix

Some transformers overload on heat pumps alone. No EV program can reach them, so they set a floor under
every charging mode: 1.97% of all transformers in the moderate scenario and 11.73% in the high one. The
floor is the same whether charging is unmanaged, on a timer or staggered, which the tests check.

After staggering, the overloads that remain are heat pump nights in both senses. Heat pumps run in 99.87% of
the remaining overload hours (moderate) and 99.92% (high), and the heat pump leads the worst hour on 13.33%
and 20.29% of the remaining overloaded transformers. Of the transformers still overloaded after staggering,
34.91% (moderate) and 52.51% (high) overload with no new EV at all. These are the targets for the next
two rungs of the ladder: Protect (batteries) and Upgrade.

## Simple timers do not help and can backfire

A timer that starts every car at hour 23 fixes 23.17% of overloaded transformers in the moderate scenario but
newly overloads 4.17% of all transformers, for a net fall from 26.18% to 24.28%. In the high scenario the
net goes the wrong way, from 54.77% to 56.14%. The backfire grows when transformers are rated with more room:
at today's peak times 1.30, overloads rise from 11.87% to 13.76% (moderate) and from 33.05% to 39.82% (high);
at times 1.50, from 3.74% to 5.84% and from 14.38% to 22.79%. Cars that charged at different hours now all
start together on the coldest nights. The teammate's timer result (9.8% rising to 16% in the moderate case)
points the same way.

## The answer holds when neighbors are alike

Grouping homes of the same segment onto one transformer (the clustered case judges asked about) raises the
heat pump's role but does not change the answer. In the moderate scenario, staggering cuts overloaded
transformers from 32.65% to 10.24% and fixes 68.7% of them; heat pumps lead 7.8% of overload hours and run in
89.51%. In the high scenario staggering cuts 53.65% to 29.76%. The heat-pump-only floor rises to 4.31% and
18.23% of all transformers.

## How the split works

The energy above the limit in an hour is the load minus 1.2 times the rating, when positive. Today's load
goes first, because it is already on the wire: it is charged only with what it would put over the limit alone,
which is 0.0% in every case, since each rating is at least today's peak times 1.05. The EV and the heat pump
then split the rest by their added effect averaged over both orders of arrival (a two-load Shapley value), so
the shares always add up to the hour's energy above the limit. An hour's larger cause is the load with the
larger share. "Stays under the limit with no new EV load" means today's load plus the heat pumps never crosses
the limit in that hour. Code: ewu/attribution.py (split, counts, facts), ewu/shift.py (timer and staggered
placement), tests/test_attribution.py (shares add up, energy is moved and never lost, facts match).

## Money: the ladder against upgrading every flagged transformer

Shifting EV charging is where the money is. Batteries, at the placeholder prices in config/ewu.yaml, cost more than the upgrade they put off. In the moderate scenario at today's peak times 1.15, the full ladder (Shift, Protect, Upgrade) costs 51.92% of upgrading every flagged transformer on an equal-life basis, while shifting and then upgrading what is still over, with no batteries, costs 43.47%. Across all 16 grid cells (two scenarios, four sizing margins, two grouping modes) and the low and high price cases, the ladder runs from 30.8% to 151.19% of the upgrade-everything cost, and shift-then-upgrade from 28.72% to 102.97%. A battery beats the upgrade only when an installed unit costs under $7,730 (mid prices, equal life); the placeholder range is $9,000 to $13,000 a unit.

How the money is counted. Every price is an input in config/ewu.yaml with its source or an assumption flag, and ewu/economics.py
types none. A battery lasts its 15-year warranty and a transformer 30 years, so each is turned into an equal-life yearly cost
at a 7% discount rate (a placeholder; Avangrid's cost of capital is an ask), which replaces the battery at the end of its life
at the same price. Upgrades cost $10,000, $15,000 or $20,000 (low, mid, high; the teammate's range credited to Eversource,
not verified). Batteries cost $9,000 to $13,000 per installed battery unit (placeholders); the mid case takes the middle of that range.
Staggered charging costs $150 to enroll and $86 a year per EV home (the teammate's OptimizEV figures, not verified), for every new
EV home on a flagged transformer. Not counted, all upside for batteries and none verified: lease payments from hosts, the
NYSERDA incentive of $200 per kWh, and capacity value at the system peak.

| Ladder rung, moderate 2030, peak x 1.15, random grouping | Share of all transformers |
|---|---|
| Flag: overloaded with unmanaged EV charging | 26.18% |
| Shift: fixed by staggered charging | 20.57% |
| Protect: cleared by fit-score batteries (92.57% of the 5.65% still over) | 5.23% |
| Upgrade: left when no battery option clears it | 0.42% |

Each protected transformer takes 1.42 batteries on average (the fewest of one or two hosts with one or two
units that clears every hour of the year), and each flagged transformer has 2.7 new EV homes to enroll.

### One cleared transformer: batteries against the upgrade

| Price case | Battery capital | Battery, yearly | Upgrade, yearly | Unit price that ties, equal life | Deferral value | Unit price that ties, deferral |
|---|---|---|---|---|---|---|
| low | $12,818 | $1,407 | $806 | $5,154 | $6,376 | $4,477 |
| mid | $15,666 | $1,720 | $1,209 | $7,730 | $9,563 | $6,715 |
| high | $18,515 | $2,033 | $1,612 | $10,307 | $12,751 | $8,953 |

Two fair framings, one answer. Equal life asks whether batteries replaced every 15 years cost less a year than an upgrade that lasts
30; at mid prices they cost $1,720 a year against $1,209. Deferral asks what holding the upgrade off for the
battery's 15-year life is worth today: $9,563 at mid prices, against $15,666 for the batteries. A deferral is never
worth more than the upgrade itself, and at a zero discount rate it is worth nothing, which the tests check. At a zero rate the
ladder costs 92.42% of upgrading everything and shift-then-upgrade 70.65%, because the battery is bought twice in
30 years and the yearly charging fee is never discounted.

### Every grid cell, mid prices, 7% discount rate

| Scenario | Grouping | Sizing | Flag % | Shift % | Protect % | Upgrade % | Batteries per protected | Ladder, % of upgrade-all | Shift then upgrade, % |
|---|---|---|---|---|---|---|---|---|---|
| moderate | random | peak x 1.05 | 42.84 | 30.79 | 11.03 | 1.16 | 1.43 | 58.81 | 47.82 |
| moderate | random | peak x 1.15 | 26.18 | 20.57 | 5.23 | 0.42 | 1.42 | 51.92 | 43.47 |
| moderate | random | peak x 1.30 | 11.87 | 10.1 | 1.69 | 0.1 | 1.34 | 44.57 | 39.81 |
| moderate | random | peak x 1.50 | 3.74 | 3.44 | 0.3 | 0.0 | 1.42 | 39.0 | 35.62 |
| moderate | same segment | peak x 1.05 | 43.81 | 27.03 | 13.79 | 3.05 | 1.52 | 72.83 | 56.6 |
| moderate | same segment | peak x 1.15 | 32.65 | 22.43 | 8.69 | 1.55 | 1.56 | 65.87 | 50.92 |
| moderate | same segment | peak x 1.30 | 20.11 | 15.21 | 4.39 | 0.56 | 1.54 | 58.11 | 46.44 |
| moderate | same segment | peak x 1.50 | 10.5 | 8.67 | 1.73 | 0.11 | 1.45 | 49.2 | 41.8 |
| high | random | peak x 1.05 | 71.71 | 35.4 | 28.25 | 8.21 | 1.63 | 102.21 | 77.35 |
| high | random | peak x 1.15 | 54.77 | 32.55 | 18.24 | 4.11 | 1.59 | 89.1 | 69.37 |
| high | random | peak x 1.30 | 33.05 | 23.34 | 8.46 | 1.32 | 1.58 | 75.75 | 60.9 |
| high | random | peak x 1.50 | 14.38 | 11.29 | 2.91 | 0.21 | 1.53 | 67.0 | 56.37 |
| high | same segment | peak x 1.05 | 62.85 | 22.79 | 26.03 | 14.13 | 1.77 | 121.57 | 89.95 |
| high | same segment | peak x 1.15 | 53.65 | 23.98 | 20.51 | 9.25 | 1.75 | 111.06 | 82.43 |
| high | same segment | peak x 1.30 | 41.1 | 22.54 | 13.85 | 4.72 | 1.74 | 98.62 | 73.84 |
| high | same segment | peak x 1.50 | 26.67 | 17.15 | 7.77 | 1.77 | 1.67 | 86.3 | 66.72 |

Shifting is the cheapest rung in every cell. Batteries add cost wherever they are used, so the ladder costs more than
shift-then-upgrade in every cell at these prices; the gap is widest where high adoption, clustered neighbors and tight sizing
leave many transformers still over after shifting. Batteries earn their rung only if Avangrid's installed price, lease income, incentives
or capacity value bring a unit under the tie price above.

Scaled to NYSEG (a labeled assumption): 890,000 electric customers over 8 homes per transformer is 111,250 transformers, as if
every customer were a home like our sample, which is how the teammate scaled. For the moderate scenario at mid prices, in present
value over the transformer's 30-year life, upgrading every flagged transformer costs $436.9M, the ladder $226.8M
($210.0M less) and shift-then-upgrade $189.9M.

Code: ewu/sensitivity.py (the ladder in every cell), ewu/economics.py (prices, equal life, deferral, scaling),
tests/test_economics.py, and `bin/ewu sensitivity`, which reruns the grid and prints this table.

## Our rebuild versus the teammate's numbers (decision D2)

Our rebuild is the reference. Differences are reported here and not tuned away. We cannot see the teammate's
simulation code, so the cause of each gap is not known; the inputs we share are the same scenarios, 8 homes per
transformer, 3,000 transformers, sizing at today's peak times 1.15 and the limit of 1.2.

| Number | Ours | Teammate |
|---|---|---|
| Overloaded, no action, moderate | 26.18% | 9.8% |
| Overloaded, no action, high | 54.77% | 29.8% |
| Overloads that are heat pump nights, moderate | 90.52% of hours with heat pumps running; 4.57% led by the heat pump | 73% |
| Overloads that are heat pump nights, high | 94.81% of hours with heat pumps running; 13.61% led by the heat pump | 89% |
| Overloaded transformers fixed by staggering, moderate | 78.56% | 88.8% (8.7 of 9.8 points) |
| Overloaded transformers fixed by staggering, high | 59.43% | 65.4% (19.5 of 29.8 points) |
| Overloaded with a timer at hour 23, moderate | 24.28% | 16% |
| Cleared by batteries, moderate | 5.23% | 1.1% |
| Still need an upgrade, moderate | 0.42% | under 0.1% |
| Upgrade every overloaded transformer, NYSEG, moderate | $436.9M present value, equal to the capital | $164M capital |
| Electrify Without Upgrade ladder, NYSEG, moderate | $226.8M present value | $27M |
| Cleared by batteries, high | 18.24% | 9.6% |
| Still need an upgrade, high | 4.11% | 0.9% |
| Upgrade every overloaded transformer, NYSEG, high | $913.9M present value, equal to the capital | $498M capital |
| Electrify Without Upgrade ladder, NYSEG, high | $814.3M present value | $135M |
| Batteries per protected transformer, moderate | 1.42 | 1.7 |
| Measured EV charging sessions | 20,940 | about 20,800 |

## Limits

Transformers are synthetic groups of homes because no meter-to-transformer map exists in the data; ratings
are today's peak times a margin, not nameplates. The staggered window, half power and timer hour are the
teammate's settings, flagged as assumptions in config/ewu.yaml. Each staggered session runs until its energy
is delivered, so a long session at half power can run past the window's close. The heat pump load is one measured slope per
degree, not a model of each home.
