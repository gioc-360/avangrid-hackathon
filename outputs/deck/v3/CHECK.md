# Independent check of deck v3

Checked 2026-11-13, 15:23 ET, read only, on `~/Downloads/D4G Cornell 2_Final Submission_v3.pptx`
(sha256 `62afbf98...d9f4`, the same bytes as `outputs/deck/v3/v3_out.pptx` and `render_src_v3.pptx`).
Script: `deck/v3/independent_check.py`, its own python-pptx walk; it shares no code with apply.py, finish.py or inventory.py.

```
.venv/bin/python -I deck/v3/independent_check.py outputs/deck/v3/source_copy.pptx \
    ~/Downloads/"D4G Cornell 2_Final Submission_v3.pptx" <out.json>
```

**Verdict: one must-fix.** The A13 footer (slide 29) says something the table directly above it disproves. Every
mapped number is correct.

## 1. Mapped numbers vs facts

| Check | Result |
|---|---|
| Mapped and pending entries in `deck/v3/fact_map.yaml` | 215 checked (207 mapped, 8 pending now backed by facts) |
| v3 number equals the fact after the entry's `fmt` rounding | 215 of 215 |
| Missing fact keys | 0 |
| Number changes at places the map does not cover | 38, all from finish.py; each one checked by hand below |

The unmapped changes are all correct.

- 3,000 transformers (slides 2, 12, 15 and A17): matches `cfg:profiles.deck.transformer_count`.
- Slide 11 notes and the A13 footer:
  - $10,248 = 15,000 x 9.108 / 13.332 (`ewu.deck.prices.upgrade_counted_usd` 10,247.65).
  - $330 lease = 3,005.61 / 9.108.
  - $2,016 matches the config.
  - $1,978 = 7,000 - 3,005.61 - 2,016.
  - 1.5 to 1.9 units = `average_units` 1.54 and 1.91.
- A17: 33,757 homes, 8,760 hours and 8 homes per transformer. The screenshot shows 292 of 3,000 over and 2,708 within, matching `moderate.limit_120.overloaded`.
- A18 and A19: "162 tests" matches `pytest --collect-only` (162).
- Slide 16 index: A18 and A19 added.

## 2. The same claim in several places

| Claim | Where | Values | OK |
|---|---|---|---|
| Saving vs upgrading | 2 title, 11 verdict, 15, A13 $15k rows | 58% to 69%; A13 57.8% and 69.1% | yes |
| Overloaded share | 2, 12 chart, A13 | 10% to 30%; 9.7% and 29.9% | yes |
| Fixed without upgrade | 2, 15, A13; slide 12 "2% to 8%" upgrades | 92% to 98%; 100 - 98.29 = 1.7, 100 - 91.63 = 8.4 | yes |
| Upgrade all | 2 (twice), 12 chart, A13 | $111M and $340M; chart 110.964 and 340.491 (label $340M); A13 $111.0M and $340.5M | yes |
| Net battery path | 2, 12 chart, A13 | $34M and $144M; 34.327 and 143.758; $34.3M and $143.8M | yes |
| Net without NYSERDA (high) | 12 footer, A13 | $261M; $261.2M | yes |
| Capital avoided | 13 | $77M to $197M = 110.96 - 34.33 and 340.49 - 143.76 | yes |
| Winter share | 2, 12 | 80% to 90% (79.79 and 89.96) | yes |
| Peak cut | 2, 10, 11, 15, A11; 13 | 8.8 MW and 2,610 homes everywhere (rerun 8.8025); 13: 1.7 kW per unit, 28 to 98 MW = 8.8025 / 5,220 x 16,391 and x 58,258 | yes |
| Peak-only fleet | 11, A11 | 0.85 (0.56); $36.5M; lease $15.7M; capacity $4.8M; NYSERDA $10.5M; break-even $129 ($260): all recomputed | yes |
| Lease per month | 13, A14, A15 | about $55 for 2 units = 2 x 330 / 12 | yes |
| Unit spec | 9, A8, A10, A12 | 2 units 20.16 kWh and 7.68 kW; 1 unit 3.84 kW and 8.06 kWh usable | yes |
| **A13 footer vs A13 table** | **29** | **footer: before offsets the battery path "costs more than upgrading in every row"; the table shows it costs less in 3 rows** | **no** |

Rows where the gross battery path is cheaper than upgrading everything. These were recomputed from facts, not from the rounded table.

| Row | Gross (before lease, NYSERDA) | Upgrade all |
|---|---|---|
| Moderate, 120%, $20k | $117.3M | $148.0M |
| Moderate, 140%, $15k | $25.3M | $27.7M |
| High, 120%, $20k | $445.8M | $454.0M |

In the other 7 rows the gross battery path costs more. The fact_map claim for this footer tests only the
120%, $15,000 rows, so apply.py passed it. `~/Downloads/D4G_v3_changes.md` repeats the claim as "(true on our
numbers)".

## 3. Renders (`outputs/deck/v3/render_v3`, from the exact v3 bytes)

I viewed all 35 pages: 2, 11, 12, 13, 15, 16, 29, 33, 34 and 35 at full size, the rest on contact sheets.

- No overflow, overlap, broken chart or unreadable text.
- Slide 12 chart labels read $111M, $34M, $340M and $144M, matching the text.
- The slide number field on 34 and 35 renders as 34 and 35. The XML holds the cached value 33; PowerPoint updates it.

## 4. Files

| File | sha256 | Note |
|---|---|---|
| `~/Downloads/D4G Cornell 2_Final Submission.pptx` | `666d4852...6dbd` | mtime 12:42:56, before any v3 work. Equals `outputs/deck/v3/source_copy.pptx` (copied 14:38), so it is unchanged. |
| `~/Downloads/D4G Cornell 2_Final Submission_v3.pptx` | `62afbf98...d9f4` | A new file: 35 slides, against 33 in the original. |

## Must-fix

1. **Slide 29 (A13) footer, last clause.**
   - Replace "before those offsets the battery path costs more than upgrading in every row." with "before those offsets the battery path costs more than upgrading in 7 of 10 rows; it costs less only at $20,000 per upgrade and in the moderate 140% row."
   - The v3 file now exists in ~/Downloads, so under the house rules the fix must ship as a new file (v3b), with a matching new changes note.
   - Also widen the fact_map claim to test all 10 rows.

## Should-fix (not blocking)

- **Slide 11, "≈ $3,000 net cost per transformer fixed".** The slide's own inputs give $3,050 to $3,780 (1.54 to 1.91 units x $1,978). The map defines the figure as the two-scenario mean rounded to the nearest $1,000. The text is unchanged from the original. "$3,000 to $3,800" would match the units row and the speaker notes.
- **Repeated shape ids.** finish.py's copied label shapes reuse their source's shape id on slides 2, 12, 15 and 16. The original already has the same pattern on slides 3, 4, 5 and 11 and renders fine, so the risk is low.
- **Slide 12 stacked bars.** The bars add to 9.8 and 29.8, while the category labels say 9.7% and 29.9%. This is the rounding of the parts.
- **Slide 16 index.** It names A10 "Example customer", but the example home is on A8 and A10 is the sizing check. This was already in the original.

## Listed, unchanged by decision

- Slide 13 "23% to 44% more energy sold": neither model has a source for it.
- No behind-the-meter MW total appears anywhere in the deck, so the 7.0 or 7.11 MW decision is not exercised.
- Teammate-only numbers stay unchanged: 16.5 MW, 44 of 50, 2.1 kW, 7,154 and the slide 10 charts.
- `facts/facts.json` has an uncommitted change from 15:19. It touches only two timing facts (screen seconds) and no deck number.
