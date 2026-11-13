# Terms: one word per idea, taken from deck v3

Deck v3 (D4G Cornell 2_Final Submission_v3.pptx, read with python-pptx: slide text, tables and notes) is the
source of truth for words. For each idea the app, the CLI and the docs talk about, the canonical term is the
one deck v3 uses most for that idea; the count is how often deck v3 uses it. Every other word for the same
idea is banned on the page (all views, dropdowns and the transformer panel), in `bin/ewu` printouts and help,
in README.md, docs/BUSINESS_CASE.md, docs/DEMO_SCRIPT.md, docs/CODE_QA.md, docs/ARCHITECTURE.md,
docs/TECH_SPECS.md, docs/demo/cli_output.txt, the front-end guide captions and the engine figures.
`checks/terms_check.py` reads the Banned column below as case-insensitive regular expressions and fails on
any hit outside the allowlist. Code identifiers, file names, fact keys and inline `code` spans in the docs
are not words on a page and are not checked.

## Terms

| Idea | Canonical term | Deck v3 uses | Banned |
|---|---|---|---|
| A transformer whose 2030 load passes its loading limit in any hour | overloaded | overload, 18 | `\bover (the\|its\|their) limit` `\bgo(es)? over\b` `\bstill over\b(?!loaded)` `\bflagged (transformers?\|share)` `% flagged\b` `\bover limit\b` |
| A transformer's size in kVA | rating | 3 | `\bnameplate\b` `\bkVA size\b` |
| The share of rating above which a transformer counts as overloaded (100%, 110%, 120%, 140%) | loading limit | loading limit, 2 | `\boverload limits?\b` `\boverload threshold` |
| One Enphase IQ 10C behind a transformer | battery unit (unit) | unit, 41 | `\bbattery modules?\b` `\bbatteries per\b` `\bbatt\b` |
| A home the battery threshold and score put first | priority home | 9 | `\bpriority hosts?\b` `\bpriority customers?\b` |
| A home that holds battery units for its transformer | battery host | 1 | `\bhost homes?\b` `(?<!battery )\bhosts?\b` |
| Replacing a transformer with a larger one | upgrade | upgrad-, 37 | `\bnew transformers?\b` `\btransformer replacements?\b` `\breplace the transformer` |
| An overloaded transformer that 1 to 4 battery units bring back within its limit | fixed by batteries | fixed by batteries / batteries fix, 3 | `\bfixed without an? upgrade` `\bprotect(s\|ed\|ing)\b` `\bclear(s\|ed)?\b` |
| The plan's steps in order | Flag, Place, Dispatch, Upgrade (the cautious profile: Flag, Shift, Place, Upgrade); the page and `bin/ewu screen` size batteries and run three of the four, never Dispatch, and say so | slide 12, 1 each | `\bprotect\b` `\bladder\b` `\brungs?\b` `\bfix order\b` `\bdeck v3's steps\b` |
| The battery plan priced against Upgrade all | battery path | 3 | `\bbattery-only\b` |
| Battery path cost after the customer lease and NYSERDA | net cost | 5 | `\bavangrid cost\b` |
| Battery path cost before the lease and NYSERDA | gross cost | Gross, 1 | `\bat gross\b` |
| Battery path cost after the lease, before NYSERDA | net cost without NYSERDA | without NYSERDA, 4 | `\bnet without\b` `\bnet, no nyserda\b` |
| Upgrading every overloaded transformer, priced | Upgrade all | Upgrade all / upgrading them all, 2 | `\bupgrade-all\b` `\bupgrad\w* every (overloaded\|flagged)` |
| One minus net cost over Upgrade all | saving | Saving, 1 | `\bsavings\b` |
| The drop in the summer system peak from the priority homes' batteries | summer peak cut | 2 | `\bpeak reduction\b` `\bpeak shaving\b` |
| Batteries take turns and may send power back to the grid | export allowed | 2 | `\bwith export\b(?! allowed)` `\bexport fleet\b` |
| Each battery cuts only its own home's load | behind the meter | 2 | `\bBTM\b` |
| An overload in the winter months (November to March, the teammate's rule) | winter nights | 3 | `\bwinter[- ]driven\b` |
| EV charging moved out of the evening peak | managed charging | not in deck v3 | `\bstagger(ed\|ing)? (ev )?charging\b` `\bstaggering\b` `\bsmart charging\b` |
| A modeled transformer of 8 real homes, since the data has no meter-to-transformer map | synthetic transformer | 4 | `\bsynthetic groups?\b` `\bsimulated (neighborhood )?transformers?\b` `\btransformer groups?\b` `\brandom groups?\b` |
| The modeled substation, feeders and synthetic transformers the Network view draws | synthetic network | not in deck v3 (the page's tag) | `\bsimulated grid\b` `\bsimulated network\b` `\bsynthetic grid\b` |
| A 2030 adoption setting | scenario | Scenario, 1 (tie with case, 1; names below, 14) | `\b(moderate\|high\|base\|conservative)[ -]cases?\b` `\bin each case\b` `\bthe same case\b` |
| The two scenarios | Moderate 2030, High 2030 (Moderate, High) | 14 | `\baggressive\b` `\bmid scenario\b` |
| One of the engine's own rule groups the Inventory view picks (EV home, Electric heat, EV and electric heat, Summer peaker, Solar, Baseline) | home type | not in deck v3 (deck v3's segment is the teammate's seven, below) | `\bshare of segment\b` `\bpick a segment\b` `\bsegment averages\b` |
| The seven segments | High use, heavy AC; Evening AC peakers; Steady mid users; Low use, light cooling; Electric heating homes; Seasonal and intermittent; Solar prosumers | slides 6, 7, A6, A7 | none found |
| Electric vehicle | EV | 40 | `\belectric vehicles?\b` `(?-i:\bL[12]\b)` `\bfast home EV charger\b` `\bslow EV charging\b` |
| A 7.2 kW home charger / charging from an outlet | Level 2 / Level 1 (spelled Level two / Level one on the page, where a digit fails the number check) | 4 | `(?-i:\bL[12]\b)` |
| Heat pump | heat pump | 33 | `(?-i:\bHPs?\b)` |
| The people in the homes the programs reach | customers | customer, 32 | `\bhomeowners?\b` |
| The utility the plan scales to | NYSEG | 20 | `\bNew York State Electric\b` |
| What the meter reads in a home (AC, EV, heat pump, solar, pool) | technology | 7 | `\bequipment\b` `\bappliances?\b` `\bdevice class(es)?\b` |
| The teammate's two input files (ev_start_pmf.npy, hp_increment.npy) | the teammate's EV start-hour shares and heat pump curve | not in deck v3 | `\btwo arrays\b` `\binput arrays\b` `\b(EV\|heat pump) (and heat pump )?tables\b` `^Arrays:` |
| The teammate's own simulation, which our replica follows | the teammate's model | not in deck v3 | `\bher code\b` `\bher model\b` `\boriginal model\b` `\bteammate's code\b` |
| Money over 15 years at 7% | present value | 2 | `\bNPV\b` |

## Allowlist

Each entry lets one exact text stand in one surface, with the reason.

| Surface | Text | Reason |
|---|---|---|
| page | `Upgrade all, the cost of upgrading every overloaded transformer` | defines Upgrade all once, in the Summary and Money dropdowns |
| docs/BUSINESS_CASE.md | `Upgrade all, the cost of upgrading every overloaded transformer` | defines Upgrade all once |
| docs/TECH_SPECS.md | `HP Customers` | quoted tab name of the organizers' workbook |

## Deck wording to align

Deck v3 uses two terms for one idea in these spots. The app follows the majority term; the deck is not edited
here. For the teammates:

| Slide | Deck v3 text | Majority term |
|---|---|---|
| 2 | "pilot on meter flagged transformers" | overloaded transformers |
| 2 | "92% to 98% of overloaded transformers fixed without an upgrade" | fixed by batteries |
| 15 | "of 2030 overloads fixed without an upgrade" | fixed by batteries |
| 29 (A13) | column header "Overload limit" | loading limit |
| 29 (A13) | column header "Battery path, net" | net cost |
| 29 (A13) | column header "Net, no NYSERDA" | net cost without NYSERDA |
| 12 | "$261M in the high case without NYSERDA" | High 2030 scenario |
| 12 (notes) | "3,000 simulated neighborhood transformers" | synthetic transformers |
| 33 (A17) | "3,000 simulated transformers of 8 real homes" | synthetic transformers |
| 33 (A17) | "Transformers are synthetic groups of 8 real homes" | synthetic transformers |
| 13 | "Winter overloads solved where heat pumps cluster" | winter nights |
| 7 | column header "Priority battery homes" | priority homes |
| 9 | title "Identifying and sizing battery homes" | priority homes |
| 3 | "an appliance inventory" | technology inventory |
| 5 | "Same tool, different appliances" | technologies |
| 14 | "the appliance inventory", "EV and appliance signatures" | technology |
| 32 (A16) | "short EV and appliance spikes" | technology |

## Open points for Gio

- Two ideas shared the word segment. Deck v3's seven segments come from the teammate's k-means; the app's
  Inventory view picks among the engine's own rule groups (Baseline, Summer peaker, EV home, Electric heat,
  Solar, ...), which have different members and counts. The engine's groups are now called home types on the
  page, in the guide and in `bin/ewu inventory`, so segment means only deck v3's seven. Showing v3's seven
  segments in the Inventory view instead is the other way, Gio's call.
- "Winter nights" is deck v3's word for the 80% to 90% share; the rule behind the number counts overloaded
  hours in November to March, not hours of the night.
