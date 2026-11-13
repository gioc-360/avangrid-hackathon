# Business case v3: flatten the peak cheaply, lease batteries to electrifying homes, sell the empty hours

All numbers computed from the full corrected data (33,757 homes, 8,760 hours), unless marked "compendium" (teammate's
sourced figure) or "assumption".

## Problem
Avangrid targets peak programs by device list, but the peak is made of components. Top 50 summer hours average 68.8 MW:
cooling in central-AC homes 37% (thermostat program), EV charging 4% (managed charging), cooling in room-AC homes 19%,
everyday household use 3-8pm 26%, always-on 13%, pools 1% (no lever). Programs reach 34-40% depending on the baseline
definition (tested under 4 mild-day windows). Grid is sized for the 78.5 MW peak but averages 30.8 MW (load factor 0.39);
only 18 hours a year are within 10% of peak. Electric-heat homes: 11% of homes, 31% of winter peak load. Winter peak 56.6 MW
(Jan 25 and Feb 8 tie; Scott named Feb 7, 1.6% lower). 7,250 more heat conversions would make the system winter-peaking.

## Three steps
1. Identify: a per-home ledger that splits each top hour into components and assigns one lever per component, each kW
   counted once. User: Load Research (Scott's team) and Customer Programs.
2. Flatten, cheapest lever first: thermostats ($300/kW, compendium; SCE gets 0.73 kW per thermostat, DOE source) before
   batteries ($4,150/kW). Batteries are energy-limited: 2,612 priority homes (threshold: >=4 kW load and >=2 kW cut in
   top 50 hours) cut 7.0 MW behind the meter and the peak moves to 2pm; widening the discharge window from 6 to 10 hours
   lowers the real cut from 7.0 to 4.9 MW. The compendium's 8.8 MW needs grid export that no source confirms.
3. Sell the empty hours: grow kWh into unused capacity. Tightest night still has 26.5 MW and 254 MWh free (0-7am).
   Filling 10% of night room adds 5.0% kWh on the same peak, so fixed grid cost per kWh falls about 5%.
   9,684 homes have central AC but no electric heat (ducted, likely heat-pump-ready: hypothesis); the 21.9 MW winter gap
   fits about 7,250 of them.

## Focus: utility-leased battery (2x Enphase IQ 10C, 20.16 kWh, 7.68 kW) for electrifying homes
Per leased home per year, Avangrid view, 15 years, 7% (capital recovery factor 0.1098):
- Cost: $14,000 installed (compendium) -> $1,537/yr; with NYSERDA $200/kWh (~$4,030, eligibility for utility-owned
  batteries unconfirmed) -> $1,094/yr. Our earlier assumption $9-13k per unit would be $18-26k for two (unsourced).
- Lease fee: $55/month = $660/yr (Green Mountain Power benchmark, compendium; 1,200-customer waitlist).
- Summer capacity: 2.69 kW at system peak x $50-275/kW-yr = $134-740.
- Winter capacity: 1.14 kW x $50-275 = $57-314, only if capacity is paid per season (compendium says per season; verify).
- EV enablement: only 0.7% of homes can add a Level 2 EV within the 3 kVA rule unaided; one unit 57%, two units 100%.
  Level 2 EV homes use up to 8,500 kWh/yr more than matched non-EV homes (upper bound, selection bias) -> up to
  $779/yr delivery revenue at $0.09138/kWh (NYSEG SC1, compendium), only if the battery is why the EV gets added, and
  only if revenue is not decoupled.
- Heat pumps do NOT need the battery for the 3 kVA rule (98.1% pass unaided), so heat-pump kWh cannot be credited to it.
- Targeting barely moves value: best 500 homes average 2.25 kW cut vs 2.15 for all 2,612.
Base case (NYSERDA yes, $50/kW summer only): $794 revenue vs $1,094 cost = -$300/yr per home.
Break-even levers: lease $80/month; or capacity >= ~$163/kW-yr; or one-time avoided service upgrade >= ~$2,700 per home
(an Avangrid number we must ask for); without NYSERDA the gap is $743/yr (lease $117/month or avoided upgrade >= ~$6,800).

## Cost of not doing
- 99.3% of homes would exceed the 3 kVA rule adding a Level 2 EV: each triggers a review or service upgrade.
- 7,250 more heat conversions flip the system to winter-peaking, with no winter thermostat program.
- NYSERDA pays storage incentives in NYSEG territory only with utility program enrollment (compendium): without a program,
  those batteries are not dispatchable for Avangrid. New York storage goal 6,000 MW by 2030 (compendium).

## CSAT / NPS
- Battery events are invisible to the customer (no setpoint change), unlike thermostat events (+2-4F); 20% kept for backup.
- Proposed pilot metrics (hand-set, not measured): NPS at 90 days, opt-out rate per event, waitlist conversion,
  complaints per 1,000 homes. Evidence of demand: GMP waitlist (compendium). No satisfaction data in AMI.

## Open asks for Avangrid
Battery export allowed and 20% reserve; avoided capacity cost $/kW-yr (vs program payments); utility-owned home batteries
allowed in NY and NYSERDA eligibility; cost of a typical service upgrade; feeder/transformer mapping.
