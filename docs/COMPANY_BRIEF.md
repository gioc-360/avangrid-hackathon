# Company brief: what the judges' company has said, with sources

Judges in the battle test read this page for Avangrid context. Every line quotes its source and ends with a tag
that tests/test_house_rules.py opens to confirm the quote is really there. Digits appear only inside quotes, so no
number on this page was typed from memory.

Tags: `citation:ID` is a page-verified entry in checks/citations.yaml; `pdf:DOC:PAGE` is an organizer PDF named in
checks/requirements.yaml; `scott MM:SS` is the office-hours transcript in sources/qa/; `repo:PATH:LINE` is a repo
file line.

## Sourced

### The company
- Avangrid Networks runs "eight regulated electric and natural gas utilities across New York, Maine, Connecticut, and Massachusetts, serving over 3 million customers". [citation:avangrid-scale]
- Its yearly investing outflow keeps growing: "Cash Flow from Investing Activities (2,548,000) (3,099,000) (4,157,000)": two fiscal years, then the latest trailing twelve months, in thousands of dollars. [citation:avangrid-investing-cash]
- NYSEG is the large New York utility: "As of December 2016, NYSEG served approximately 890,000 electricity customers", from a dated company profile. [citation:avangrid-utilities-2018]

### What the organizers asked for
- The challenge wants a framework that is "quantitative, reproducible, and decision-oriented". [pdf:challenge:3]
- The code deliverable is a "Tool applied to hourly loads that will estimate inventory of heating and cooling appliances, and identify customers eligible for utility programs, BESS, etc." [pdf:kickoff:9]
- Only the deck is scored: "you will only be scored on your slide deck". [pdf:kickoff:9]
- Load knowledge matters because it "is critical to forecasting load growth, designing programs, targeting investments". [pdf:kickoff:8]
- Service headroom is a stated limit: "A residential 200-amp service should not exceed approximately 3 kVA of additional incremental load without further evaluation." [pdf:challenge:3]
- The battery is fixed: "Total Energy Capacity 20.16 kWh (10.08 kWh per unit)" and "Continuous Power (Grid) 7.68 kW total". [pdf:challenge:3]
- The battery program runs "Warranty Through Program 15 years (Extended manufacturer warranty)". [pdf:challenge:3]
- Judges will ask about scale: "How would your approach scale to millions of customers?" [pdf:challenge:5]

### What Scott Bochenek (Program Director, Load Research) said at office hours
- The network is sized for the top hours: "the infrastructure is built to meet that, those top hours". [scott 15:52]
- The system peaks he named: "July, July 2nd". [scott 11:29]
- And for winter: "February 7th was the winter peak". [scott 11:41]
- Peaky homes suit batteries: "the more peaky that the customer load shape is". [scott 02:17]
- Flat, long loads do not: "if the shape is very flat". [scott 02:35]
- He doubts winter thermostat events: "people are going to be less open to the idea". [scott 08:03]
- EVs are the flexible load: "they have a lot more potential for flexibility than, uh, than heating or, or air conditioning". [scott 09:40]
- Heat type is the hard part: "who might be primarily heating with electricity versus supplementing". [scott 06:14]
- Summer thermostat events already run: "smart thermostat programs in the summertime". [scott 07:31]
- Local bottlenecks are a future problem: "today there's not a lot of bottleneck". [scott 09:19]

### Industry context the judges will recognize
- EVs "will add enough load to require targeted network and transmission upgrades". [citation:ev-upgrades]
- Peak load means operators "must invest in excess capacity". [citation:peak-forces-slack]
- One utility found that "up to 17% of their transformers may need to be upgraded due to increasing EV adoption". [citation:doe-smud-17pct]
- A neighborhood transformer example from DOE: "three customers buy a Tesla". [citation:doe-tesla-transformer]
- A leased home battery program exists next door: participants "get two home batteries installed for $55 a month over a 10-year lease". [citation:vermont-gmp-vpp]

## Unverified, do not trust

These are the teammate's claims from the business case draft. Each quote is checked to be the teammate's own words,
but nobody has found an outside source for them. Judges are told not to rely on them, and they stay off the demo page.

- Rate Decoupling Mechanism: "everyone gets lower rates as NYSEG's Rate Decoupling Mechanism returns the value". [repo:runs/business_case_team_v2.txt:58]
- Capital strain: "capital spending runs at 3.4 times operating cash flow". Our PitchBook source gives investing outflow, not this ratio. [repo:runs/business_case_team_v2.txt:58]
- Stillwater: "third party owned via RFP as at Stillwater". [repo:runs/business_case_team_v2.txt:51]
- Upgrade price: "upgrade $10,000 to $20,000 (Eversource)". [repo:runs/business_case_team_v2.txt:60]
- Capacity value: "NYISO rest of state capacity about $60 per kW a year". [repo:runs/business_case_team_v2.txt:60]
- Battery incentive: "NYSERDA $200 per kWh". [repo:runs/business_case_team_v2.txt:60]
- Managed charging price: "$150 plus $86 a year, as OptimizEV". [repo:runs/business_case_team_v2.txt:47]
- Scenario basis: "New York 2030 heat pump and ZEV targets". [repo:runs/business_case_team_v2.txt:60]
