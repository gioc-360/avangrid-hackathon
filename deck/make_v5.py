"""Deck v5: v4b cut to 10 content slides (title and thank-you not counted); nothing deleted, three slides move to the appendix.

What: slide 10 (business value test) becomes "Where a battery pays": its left panel now leads with the 2,610 homes'
      8.8 MW summer peak cut (from slide 9) and still ends "does not pay on its own"; the right panel shows the same
      units on an overloading transformer. Results (12) move before the demo video (11). Slides 7, 5 and 9 move
      to the end of the appendix as A20, A21 and A22. Scalability's third column uses the challenge's wording.
Why:  judges read the 8.8 MW homes and the batteries that pay as two fleets; one slide tells it as one story, and
      the results arrive at slide 8 instead of 12. Every number is unchanged from v4b.
How:  .venv/bin/python -I deck/make_v5.py V4B.pptx OUT.pptx   (never overwrites OUT; each edit asserts its old text)
"""
import sys
from pathlib import Path
from pptx import Presentation

SRC, OUT = Path(sys.argv[1]), Path(sys.argv[2])
if OUT.exists():
    sys.exit(f"refusing to overwrite {OUT}")
deck = Presentation(str(SRC))
slides = list(deck.slides)
assert len(slides) == 37
log = []


def shape(slide, sid):
    found = [s for s in slide.shapes if s.shape_id == sid]
    assert len(found) == 1, f"shape {sid} not found"
    return found[0]


def put(slide, sid, old, new):
    """Replace the whole text of a one-run shape, after checking it is exactly the old text."""
    runs = [r for p in shape(slide, sid).text_frame.paragraphs for r in p.runs]
    assert len(runs) == 1 and runs[0].text == old, f"shape {sid}: {[r.text for r in runs]!r} is not {old!r}"
    runs[0].text = new
    log.append((old[:50], new[:70]))


def swap(slide, sid, old, new, notes=False):
    tf = slide.notes_slide.notes_text_frame if notes else shape(slide, sid).text_frame
    runs = [r for p in tf.paragraphs for r in p.runs if old in r.text]
    assert len(runs) == 1 and runs[0].text.count(old) == 1, f"'{old}' in {len(runs)} runs"
    runs[0].text = runs[0].text.replace(old, new)
    log.append((old[:50], new[:70]))


# The merged slide (v4b slide 10)
m = slides[9]
put(m, 2, "PART 3  |  BUSINESS VALUE TEST", "PART 3  |  WHERE A BATTERY PAYS")
put(m, 3, "A battery fleet for the peak alone does not pay; the same battery placed where it avoids an upgrade does",
    "Batteries cut the summer peak by 8.8 MW, but pay only where they avoid a transformer upgrade")
put(m, 6, "Battery fleet for the summer peak only", "2,610 priority homes, summer peak only")
put(m, 7, "0.85", "8.8 MW")
put(m, 8, "benefit to cost (0.56 without NYSERDA)", "peak cut (11%), export allowed; 44 of the top 50 hours lowered")
put(m, 9, "Cost", "Benefit to cost")
put(m, 10, "$36.5M for 2,610 homes x 2 units", "0.85 on $36.5M for 2 units each (0.56 without NYSERDA)")
put(m, 18, "Battery placed on a transformer that will overload", "Same units on a transformer that will overload")
swap(m, None, "(2, 10, 12, 13, A11, A13)", "(2, 7, 8, 10, A11, A13)", notes=True)

# Scalability: the challenge asks "What additional data would improve your analysis?"
put(slides[13], 18, "Data that would improve it", "Additional data that would help")

# Slides moving to the appendix get appendix labels
put(slides[6], 2, "PART 3  |  WHEN THE GRID PEAKS", "APPENDIX  |  A20")
put(slides[4], 2, "PART 2  |  CUSTOMER SEGMENTATION", "APPENDIX  |  A21")
put(slides[8], 2, "PART 3  |  ESTIMATED OPERATIONAL BENEFITS", "APPENDIX  |  A22")

# The appendix index gains one line under A19 (same style: copy the A19 box)
import copy
idx = slides[15]
a19 = shape(idx, 22)
assert a19.text_frame.text == "A19 Tech specs"
el = copy.deepcopy(a19._element)
a19._element.addnext(el)
new = [s for s in idx.shapes if s._element is el][0]
new.top = a19.top + (a19.top - shape(idx, 21).top)
new.text_frame.paragraphs[0].runs[0].text = "A20 to A22 Grid peaks, segment chart, peak cut"
new._element.nvSpPr.cNvPr.id = max(s.shape_id for s in idx.shapes) + 1
log.append(("index", "A20 to A22 line added"))

# The ranking now sits on slide 6 (v4b slide 8)
swap(slides[33], 39, "slide 8", "slide 6")
swap(slides[33], None, "Part 3 ranking (slide 9)", "Part 3 ranking (slide 6)", notes=True)

# New order: title, 2, 3, 4, 6, 8, 10 (merged), 12 results, 11 video, 13, 14, thank you, appendix, then 7, 5, 9
order = [1, 2, 3, 4, 6, 8, 10, 12, 11, 13, 14, 15] + list(range(16, 38)) + [7, 5, 9]
assert sorted(order) == list(range(1, 38))
lst = deck.slides._sldIdLst
ids = list(lst)
for el in ids:
    lst.remove(el)
for n in order:
    lst.append(ids[n - 1])
deck.save(str(OUT))
for a, b in log:
    print(f"{a}  ->  {b}")
print(f"{len(log)} edits, 10 content slides, 25 appendix slides -> {OUT}")
