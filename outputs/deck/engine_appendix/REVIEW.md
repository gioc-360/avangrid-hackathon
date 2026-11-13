# Engine appendix review (A18a, A18b, A18c)

Read only review of outputs/deck/engine_appendix/EWU_engine_appendix.pptx and its PowerPoint renders
(render/hi-1.png to hi-3.png), 2026-11-13 16:51 ET. Deck v3 was read with python-pptx from
~/Downloads/D4G Cornell 2_Final Submission_v3.pptx (slide text, tables and notes). Nothing was edited.

Verdict: not passed. Three must-fix items, each a one-line change in deck/engine_appendix/build.py.

```
+-------------------+----------+------------------------------------------------------------+
| Slide             | Reader 1 | Must-fix (Reader 2)                                         |
+-------------------+----------+------------------------------------------------------------+
| A18a top level    | 4 / 5    | program_targets.csv does not hold the 2,610 priority homes |
| A18b mid level    | 3 / 5    | Flag step missing ASSUMED (120% loading limit)              |
| A18c low level    | 4 / 5    | "measured sessions" where v3 says "observed sessions"       |
+-------------------+----------+------------------------------------------------------------+
```

## Must-fix

1. **A18a, middle row.** The slide draws `program_targets.csv` feeding "2,610 priority homes to offer 2 leased
   battery units". That file (ewu/plan_output.py, ewu/plan_readme_template.md:74) lists homes on actioned
   synthetic transformers with the programs each qualifies for; the showcase copy has 4,414 simulated rows. The
   2,610 is the Part 3 ranking (v3 slide 9), recomputed by checks/teammate_audit.py
   (fact `teammate.audit.rerun.priority_homes`); no bin/ewu output file holds it, and
   outputs/bess_candidates.csv uses other tiers. The slide's own notes already say so.
   Fix: in the middle box replace `program_targets.csv` with "Part 3 ranking, slide 9" (or keep the file and drop
   the 2,610 for what the file holds). Keep the label "Priority homes list" only if the 2,610 stays.

2. **A18b, Flag step.** Tagged SIMULATED only, but its number, "any hour above 120% of rating", is set by us:
   config/ewu.yaml `overload_limit` carries `assumption: true` ("real loading limits are an Avangrid ask"), v3 A12
   calls it a "Planning assumption; tested 110% and 140%", and v3 A16 lists real loading limits as an open question.
   The slide's own legend defines ASSUMED as "set by us, to confirm". Fix: add an ASSUMED pill under SIMULATED on
   Flag, as Add 2030 load already has.

3. **A18c, Hourly load box.** "start hour drawn from 20,800 measured sessions"; v3 A12 says "20,800 observed
   sessions", and A18b's legend uses "observed" for the same idea. One concept, two words. Fix: "observed sessions".

## Reader 1: Avangrid judge, 30 seconds a slide

**A18a, 4 / 5.** In 30 seconds a judge gets the whole engine: three feeds Avangrid already has on the left, one
offline run in the middle, three files on the right, and the team and headline number each file serves. The caption
carries the reason in one clause (no new hardware; customer data never leaves) and the dashed transformer map says
what is still missing. Weak spots: "EWU engine" is the only place the acronym appears as a word, v3 calls it the
engine or Electrify Without Upgrade; and the dashed border is not explained on this slide.
One change: name the box "Electrify Without Upgrade engine" so the judge ties it to the recommendation slides.

**A18b, 3 / 5.** The left to right chain and the tags land, and the checks bar answers "can I trust the numbers"
before it is asked. But each box spends its middle on file paths (ewu/ deck.py repeats in four boxes), so the
plain line that says what the step does sits at the bottom, below the code. Seven boxes, two tag rows, a checks bar
and a legend is a lot for 30 seconds, and the title carries two claims.
One change: move each step's plain line directly under its name and put the file name on one small line beneath
it (or only in the notes), so the eye reads step, result, tag.

**A18c, 4 / 5.** The math reads as a test anyone can rerun: load per hour, compare with 120% of rating, size units
from the excess, then batteries or upgrade with a price on each. The caption gives the reason both paths compare
(same 15 years at 7%) and how Avangrid's real rating drops in. Weak spots: a judge doing mental arithmetic gets
$7,000 less $3,000 less $2,016 = $1,984, not $1,978 (the lease is $3,006 rounded), and "15 of its 40 years" of
$15,000 reads as $5,625, not $10,248 (it is a present value share). Both match v3 A11 and A13 word for word, so the
fix belongs in both places. The bottom third of the slide is empty.
One change: write "counted in present value for 15 of its 40 years = $10,248" so the upgrade figure checks on sight.

## Reader 2: independent checker

```
+------------------------------+--------+-----------------------------------------------------------+
| Check                        | Result | Evidence                                                  |
+------------------------------+--------+-----------------------------------------------------------+
| Numbers equal deck v3        | pass*  | every number on the 3 slides appears in v3 text/tables    |
| File names exist in repo     | pass   | 17 of 17 paths found (analysis/, ewu/, checks/, data/)    |
| File names say the right job | FAIL   | must-fix 1 (program_targets.csv vs 2,610)                 |
| Terms match v3               | FAIL   | must-fix 3; checks/terms_check.py synonyms: 0 hits        |
| Tags right                   | FAIL   | must-fix 2; others agree with architecture.png            |
| Native, editable shapes      | pass   | rounded rectangles, connectors, text boxes; no pictures   |
| Text 12 pt and up            | pass   | only v3's own 11 pt eyebrow                               |
| On slide, no em/en dash      | pass   | 0 shapes off slide, 0 dashes                              |
| Nothing private              | pass   | no names, ids or customer rows; one media file = logo     |
| Copies delivered             | pass   | Downloads and OneDrive deck-v3 copies md5-identical       |
| v3 untouched                 | pass   | v3 in Downloads and OneDrive md5-identical, dated 15:17   |
+------------------------------+--------+-----------------------------------------------------------+
```

\* Speaker notes on A18c say a new EV charges "on 47% of days" (config `ev_day_share` 0.47). v3 states the same
claim as "3.3 sessions a week", and 47 appears nowhere in v3. Not wrong, but outside the rule; see should-fix.

Numbers traced: 33,757 homes (`data.customers_usable`), 10% to 30% (9.73, 29.87), 92% to 98% (91.63, 98.29),
2,610 (`teammate.audit.rerun.priority_homes`), 58% to 69%, $34M vs $111M and $144M vs $340M, 3,000 x 8,
25 to 167 kVA, 0.85, 120%, 7.2 kW, 3 hours, 3.3 a week, 20,800, about 8,800 kWh (8,760.6), 3.84 kW, 8.06 kWh,
1 to 4 units, $7,000, $3,000 (3,005.6), $2,016, $1,978, $15,000, $10,248, 15 years, 40 years, 7%,
x 890,000 / (8 x 3,000). Each equals v3's number for the same claim.

Tags, step by step:

```
+---------------------+------------------+-------------------------------------------------------+
| Step                | On slide         | Verdict                                               |
+---------------------+------------------+-------------------------------------------------------+
| Profile every home  | GIVEN, DERIVED   | right: meter data given, technology and segment derived|
| Build the network   | SIMULATED        | right; 8 homes and 0.85 are set by us (should-fix)    |
| Add 2030 load       | SIMULATED, ASSUMED | right: adoption shares are scenarios                |
| Flag                | SIMULATED        | wrong: 120% loading limit is ASSUMED (must-fix 2)     |
| Place battery units | SIMULATED        | right                                                 |
| Upgrade             | SIMULATED        | right; the 4 unit cap is v3 A12 assumption (optional) |
| Price both paths    | ASSUMED          | right: $7,000 and $15,000 are "to confirm" in v3       |
+---------------------+------------------+-------------------------------------------------------+
```

## Should-fix (not blocking)

- A18c notes: replace "on 47% of days" with "3.3 sessions a week" so the notes use v3's number.
- A18c box title "Compare with limit": "Compare with loading limit", v3's term (the caption already uses it).
- A18b Build the network: add ASSUMED for "8 real homes" and "peak / 0.85" (config `homes_per_transformer`
  carries `assumption: true`), and optionally Upgrade for the 4 unit cap.
- A18a and A18c captions break mid-phrase ("meter to transformer / map", "a real rating / or loading limit");
  let the text box wrap instead of a hard line break.
- A18b: each step is a rounded rectangle plus separate, ungrouped text boxes and pills; grouping each step would
  let a teammate move a box in one drag.
- Tell the teammates that v3's appendix index (slide 16) still lists "A18 How the engine works" as one slide.
