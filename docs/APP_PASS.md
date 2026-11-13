# App pass: text, hierarchy and side panel

The demo page and the CLI got one pass before the video is filmed: every text block kept only if the planner
needs it to decide or to trust a number, one headline per step that states the takeaway, and a persistent left
side panel that reaches every step in one click. No number was added: every number on the page is still a
stored fact or config input, bound to its key (`checks/demo_check.py`, 0 problems).

Who the page is for, said once at the top of Overview: Avangrid distribution planners at NYSEG and RG&E deciding
which neighborhood transformers need what before 2030, and the customer programs team choosing who to enroll
in managed charging or offer a home battery. Homeowners benefit; they do not use the page.

Skills used: page-hierarchy (scan order, panel labels, the question per step, next links), dashboard-design
(Overview as a single screen, text for precise values, one stacked bar for part-to-whole, no gauges),
ui-distinctiveness (floor_check, contrast, focus ring, consistency audit). Facts came from the code, not the
skills: every number and behavior below was read from `ewu/demo_template.html`, `checks/demo_check.py` and the
rendered DOM.

## The shape

```
+------------------+---------------------------------------------------------------+
| SIDE PANEL       | STEP (one at a time, swaps in place, no motion)               |
|                  |                                                               |
| app name         | step name                                                     |
| Overview         | HEADLINE: big number + its so-what        <- first look       |
| Inventory        | so-line: range or consequence                                 |
| CHEAPEST FIX     | controls, one row (scenario | sizing | grouping)              |
|  Flag            | PRIMARY VISUAL in a card                  <- second look      |
|  Shift           | secondary detail, notes                   <- third look       |
|  Protect         | "How this is computed" (folded)                               |
|  Upgrade         | Next: <step> ->                                               |
| DECIDE           |                                                               |
|  Money           |                                                               |
| ---------------- |                                                               |
| case shown       |                                                               |
| hover = fact key |                                                               |
+------------------+---------------------------------------------------------------+
```

Side panel, as built: a `nav` of real links (`#step=overview` to `#step=money`), each with the step name and the
user's question; the current step carries `aria-current="page"` and is marked twice (bold name plus an accent
left bar on a lifted card). The foot names the case every number is shown for (needed because Money and every
ladder step read the same scenario, sizing and grouping) and the trust line (hover any number for its key).
Native links and buttons, so Tab reaches every one, with a 2 px focus ring on `:focus-visible`. Sticky at full
height on wide screens; on narrow screens it becomes a top bar with the step names in one scrolling row.
Old links still work: `#step=1` to `#step=4` and `#only=1` to `#only=4` map to Inventory, Flag, Protect, Money.

## Words on the page, before and after

Measured on the rendered DOM in headless Chrome with one extractor for both pages (script and style text
skipped); the before page was rebuilt from the committed template with today's facts. These are counts of page
text, not data, so `trace_numbers` lists them as untraced; they are the only untraced numbers in this doc.

| View | Before (words) | After, visible (words) | After, folded detail (words) |
|---|---|---|---|
| Frame (header, nav, footer / side panel) | 57 | 80 | 0 |
| Overview | none | 249 | 0 |
| Inventory | 254 | 218 | 17 |
| Screen, split into Flag / Shift / Upgrade | 233 | 195 / 182 / 172 | 0 |
| Cold snap, now Protect | 234 | 222 | 78 |
| Money | 285 | 283 | 36 |
| Whole page, every step | 835 | 1,041 | 131 |

Every existing view got shorter or held; the page as a whole grew because it now has seven views instead of
four, a side panel that names each step's question, and a controls row repeated on each step that reads it.

## Every block: removed, moved, kept

Necessary means removing it would lose something the planner needs to decide or to trust a number. Rule names:
PH = page-hierarchy, DD = dashboard-design, UD = ui-distinctiveness.

| Before block | Action | Where now | Reason, and the rule that drove it |
|---|---|---|---|
| Title "Electrify Without Upgrade" | kept | panel app name, links to Overview | site ID, upper left (PH Trunk Test) |
| Intro "Which neighborhood transformers ... Flag, Shift, Protect, Upgrade" | moved | Overview headline and the panel's "Cheapest fix first" group | the takeaway goes in the headline, the ladder order in the nav (PH summaries above details) |
| Intro "Built from cached results ...; works offline" | removed | README and DEMO_SCRIPT already say it | a presenter concern, not a planner one (PH Krug law 3) |
| Pill nav (Inventory, Screen, Cold snap, Money) | removed | replaced by the side panel | one navigation model, persistent, "you are here" in two ways (PH rules 5 and 7) |
| Step 1 heading "Inventory: what each kind of home has ..." | moved | panel question + Inventory headline | the heading now states the number (PH one point per page) |
| Step 1 ask "Pick a segment." | removed | control label "Segment" | an instruction for an obvious action (PH Krug law 3) |
| Step 1 ask "Each Composite home is the average ... not a real customer." | removed | the Composite caption says the same, next to the home | duplicate; the label stays where the home is shown (necessary for privacy) |
| Step 1 ask "Equipment is read from hourly meter data alone." | kept | Inventory so-line | trust: where the inventory comes from |
| Picker label "Composite home" | reworded | "Segment" | the buttons are segments; the Composite label stays in the caption |
| Composite caption (segment, homes, kWh a year, highest hour) | kept | card, top left | the "Composite" label and the segment size are never removed |
| Equipment table | kept | card | the programs team's answer |
| Rows "Average EV owner score", "Average heat pump owner score" | moved | "How this is computed" | model detail a skeptic may ask for; not needed to pick a program |
| Program chips | kept | card | the programs team's answer |
| Note "Across all 33,757 homes, 69.07% qualify ..." | moved | Inventory headline | it is the step's takeaway (PH one point, DD emphasis zone) |
| Winter and summer day chart with legend | kept | card, right | when the segment peaks is what a transformer feels |
| Monthly energy bars and caption | removed | none | restates the season the day profiles already show (PH noise rule, DD meaningless variety) |
| Step 2 heading "Screen: which transformers 2030 overloads, and the cheapest fix" | moved | split into Flag, Shift, Upgrade headlines | two points on one page (PH one point per page) |
| Step 2 ask "Pick a scenario, how big ..., how neighbors are grouped." | removed | control labels | instruction (PH Krug law 3) |
| Three control rows | merged | one row on every step that reads them | controls grouped in one row above the visual (task rule; PH related = visually related) |
| Big 26.18% + "of transformers go over 1.20 x their rating ... (Flag)" | kept | Flag headline | the Flag takeaway |
| Ladder stacked bar | kept | Overview (all rungs), Shift and Upgrade (its rung lit, others dimmed) | part-to-whole as one stacked bar (DD), same vocabulary on every view (PH rule 4) |
| Ladder table, three rows with keys | reworded | legend under the bar with the same three numbers | direct labels on the bar; the table repeated it |
| Note "Shares of all transformers." | kept | Overview note | the shares are of all transformers, not of flagged; a planner misreads them without it |
| Note "Staggering newly overloads 0.04%, which join Protect or Upgrade." | moved | Shift so-line | trust: the side effect of the rung |
| Note "Batteries per protected transformer: 1.42" | moved | Protect headline | it is what the Protect rung costs in units |
| Note "Flagged share at every sizing ...: shown as a range" | reworded | Flag so-line range + bar caption | the range on the headline is never removed |
| Flagged share at every sizing table | kept | Flag primary visual; the same table for Shift and Upgrade | the headline range, drawn (DD bars for categories) |
| Note "3,000 synthetic transformers of 8 homes, 5 seeds pooled. A real map replaces ..." | kept | under the Flag visual | trust: transformers are synthetic |
| Step 3 heading "Cold snap: does a home battery last two cold nights?" | moved | Protect headline and so-line | the heading now states the number |
| Step 3 ask "One flagged transformer through the coldest two days ...; fleet charge" | moved | chart caption | it names what the chart shows |
| Host picker + "each host has 2 battery units, 20.16 kWh" | kept | controls row; battery size in the caption | what a host is |
| Load legend, load chart, limit line | kept | card | Protect's proof |
| Fleet charge caption + chart | kept | card, shortened | answers "you assumed the battery starts full" |
| Paragraph: case, 8 homes summed, kWh over the limit with no battery | split | case into the caption; the no-battery kWh into "How this is computed" | the chart shows the overshoot; the case is necessary because the cold snap runs one case |
| Paragraph: 2.70% pushed over, one host clears 89.88%, two clear 92.84% | moved | Protect so-line | the step's so-what |
| Note: coldest hour -5.0 F | moved | chart caption | context for the chart |
| Note: battery runs all year, charge earned not assumed, charges only with room | moved | "How this is computed" | method for a skeptic |
| Step 4 heading "Money: the ladder against upgrading every flagged transformer" | moved | Money headline | the heading now states 51.92% |
| Step 4 ask: equal-life cost explanation | moved | "How this is computed" | method |
| Note "For the scenario, sizing and grouping picked in the screen step: ..." | removed | the controls row on Money and the panel foot show the case | duplicate |
| Three cost bars with labels | kept | card | the cost comparison |
| Note "Mid prices. Low ..., high ...; at a zero discount rate ..." | kept | under the bars | sensitivity to price (range) |
| "Headline as a range." paragraph | moved | Money headline and so-line | the range on the headline is kept |
| "Batteries alone cost more ..." paragraph with the $7,730 tie price | kept | right column | the decision rule for batteries |
| Assumptions note (lives, discount rate, placeholders) | kept | right column, starts with "Assumptions:" | placeholder and assumption labels are never removed |
| NYSEG scaling note | kept | right column, labeled assumption | the money in dollars, labeled |
| Footer "Every number on this page is read from facts ... Hover a number to see its key." | moved | panel foot, shorter | the trust proof, on every view |

Counts: 47 blocks before; 7 removed, 21 moved, reworded, merged or split, 19 kept as they were.

New blocks, each necessary: the panel (step names, questions, the two group labels, the case line); the Overview
who line, headline, range, ladder bar and five linked tiles (Flag, Shift, Protect, Upgrade, Money); a step name
above each headline (PH Trunk Test: the page name matches what was clicked); one "Next" link per step (PH
Krug law 2, each click mindless); three folded "How this is computed" disclosures (Inventory, Protect, Money).

## Hierarchy per step, checked on the screenshots

Screenshots: before in `outputs/video/app_pass/before/`, after in `outputs/video/app_pass/after/` (one per step
at 1920x1080, a narrow view, a dark mode view). Gitignored, local only.

| Step | First look | Second look | Third look |
|---|---|---|---|
| Overview | 0.42% of transformers need a new one | ladder bar across the width | five tiles, each a link to its step |
| Inventory | 69.07% of 33,757 homes qualify | Composite home: equipment and programs | winter and summer day chart |
| Flag | 26.18% go over 1.20 x their rating | flagged share at every sizing, x 1.15 drawn dark | synthetic transformer note |
| Shift | 20.57% fixed by staggering EV charging | ladder bar, Shift lit | Shift at every sizing |
| Protect | 5.23% cleared by batteries, 1.42 each | cold snap load chart against the limit | fleet battery charge |
| Upgrade | 0.42% still over: replace these | ladder bar, Upgrade lit | Upgrade at every sizing |
| Money | the plan costs 51.92% of upgrading all | three cost bars | battery tie price and the assumptions |

In every after screenshot the largest, heaviest text on the page is the headline number at the top left of the
content (the biggest and heaviest type on the page), so the first look lands there (DD emphasis zone, UD F1: weight and size together).
Every step fits one 1920x1080 screen with no scrolling.

Motion: none. Steps swap in place; nothing slides, bounces or counts up; the old jump-scroll to a step anchor
is gone. A `prefers-reduced-motion` guard keeps any future transition off.

## Accessibility floor and visual audit

`python3 ~/.claude/skills/ui-distinctiveness/scripts/floor_check.py ewu` and `... outputs/demo`: exit 0 both,
0 blocking, 0 warnings.

Manual floor, measured: muted text on the page background 6.23:1, on the panel 5.69:1, the panel group labels
4.81:1, the link colour 4.84:1, control borders 3.50:1 on the background (raised past 3:1 by darkening one
token); dark mode text 6.40:1 or better. Toggle state is `aria-pressed` plus fill plus weight, never colour
alone; the current step is `aria-current` plus bold plus the accent bar. Charts carry `role="img"` with a label.

Five failure categories: F1 hierarchy now uses weight and colour as well as size; F2 colours are tokens on
`:root` with a dark set, one new token (`--ctl`) for control borders; F3 the system font stays, because the page
may load nothing from outside and it has tabular figures; F4 cards and the current panel item use a two-layer
shadow instead of a border; F5 accent top borders on the tiles and the accent bar on the current step.

## CLI text

`ewu/cli.py`: `demo` help no longer says "4-step"; the cold snap header now names every abbreviated column
(med, p90, run, Nh) in one line. `ewu/printouts.py`: the sensitivity table prints one legend line for
`batt/prot` and the price-case columns. Every other line was kept: each prints an aggregate a planner reads
(scenario, sizing, shares, costs, the labeled NYSEG scaling) and none repeats another.

## For the video

Section ids changed from `#step1` to `#step4` to named ids: `#overview`, `#inventory`, `#flag`, `#shift`,
`#protect`, `#upgrade`, `#money`. The header and its `.sub` intro, the pill nav and `.ask` paragraphs are gone;
navigate with `aside a.step-link[data-step="flag"]`. The big number sits in `h2.headline .big .n`. A capture
script that still uses the old selectors fails loudly (a null element), never silently.

## Gates

| Gate | Result |
|---|---|
| `checks/demo_check.py` | 16 states, 2,600 bound numbers, 7 screenshots, 0 problems |
| `checks/demo_check.py --selftest` | 8 of 8 PASS |
| floor_check, both folders | exit 0 |
| pytest (`tests/`, without the untracked `tests/test_video.py` another session is writing) | all passed, 0 failed |
| `make check` | exit 0 |
| `checks/qa_refs.py docs/CODE_QA.md` | 75 references, 0 problems (`ewu/cli.py:138 "--map"` moved) |
| `checks/trace_numbers.py docs/DEMO_SCRIPT.md` | 0 untraced |
