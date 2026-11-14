"""Deck v5b: v5 (10 content slides) with the heat-wave chart back and the simulation stated where the results are.

What: the merged "Where a battery pays" slide gets the July heat-wave chart (today vs 2,610 priority homes vs plus
      secondary) in its left panel in place of two text rows; its verdict keeps the 0.85 benefit to cost. The results
      slide says the network is simulated, gives the saving at every loading limit (facts), and its footnote shows the
      gross cost before the lease and NYSERDA. The executive summary marks the overload share as simulated.
Why:  three Skimmer runs scored v5 4 points under v4b, each citing too few charts (the heat-wave chart was the one
      visual v4b's judges praised); every judge asked for the simulated network and who pays to sit by the headline.
How:  .venv/bin/python -I deck/make_v5b.py V5.pptx HEATWAVE_CHART.png OUT.pptx   (never overwrites OUT)
"""
import json
import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Emu

SRC, CHART, OUT = (Path(a) for a in sys.argv[1:4])
if OUT.exists():
    sys.exit(f"refusing to overwrite {OUT}")
FACTS = json.loads((Path(__file__).resolve().parent.parent / "facts" / "facts.json").read_text())
fact = lambda k: FACTS[k]["value"]
saving = {sc: [fact(f"ewu.deck.{sc}.limit_{l}.saving_vs_upgrade_all_pct") for l in (100, 110, 120, 140)] for sc in ("moderate", "high")}
lo, hi = round(min(saving["high"])), round(max(saving["moderate"]))                       # 50, 73
gross = {sc: round(fact(f"ewu.deck.{sc}.limit_120.nyseg_gross_musd")) for sc in ("moderate", "high")}       # 117, 436
upall = {sc: int(fact(f"ewu.deck.{sc}.limit_120.nyseg_upgrade_all_musd")) for sc in ("moderate", "high")}   # 111, 340
assert (lo, hi, gross["moderate"], gross["high"], upall["moderate"], upall["high"]) == (50, 73, 117, 436, 111, 340)

deck = Presentation(str(SRC))
log = []


def shape(n, sid):
    found = [s for s in deck.slides[n - 1].shapes if s.shape_id == sid]
    assert len(found) == 1, f"slide {n}: shape {sid} not found"
    return found[0]


def put(n, sid, old, new):
    runs = [r for p in shape(n, sid).text_frame.paragraphs for r in p.runs]
    assert len(runs) == 1 and runs[0].text == old, f"slide {n} shape {sid}: {[r.text for r in runs]!r}"
    runs[0].text = new
    log.append((n, old[:45], new[:80]))


# Slide 2: the overload share is a simulation result
put(2, 8, "of neighborhood transformers overload by 2030 as homes add EVs and heat pumps",
    "of neighborhood transformers overload by 2030 as homes add EVs and heat pumps (simulated)")

# Slide 7: heat-wave chart in the left panel, in place of the benefit, 15-year value and break-even rows
for sid in (9, 10, 11, 12, 13, 14):
    el = shape(7, sid)._element
    el.getparent().remove(el)
put(7, 16, "Does not pay on its own", "Does not pay on its own: benefit to cost 0.85 (0.56 without NYSERDA)")
top, height = Emu(3246120), Emu(2057400)
pic = deck.slides[6].shapes.add_picture(str(CHART), Emu(822960), top, height=height)
assert pic.left + pic.width <= Emu(548640 + 5394960) and pic.top + pic.height <= shape(7, 15).top
log.append((7, "rows: benefit, 15 year value, break even", "July heat-wave chart"))

# Slide 8: simulated network, saving at every loading limit, gross cost in the footnote
put(8, 27, "of neighborhood transformers overload by 2030 (moderate to high case)",
    "of neighborhood transformers overload by 2030 (moderate to high case), simulated on 3,000 transformers of 8 real homes")
put(8, 31, "lower cost than upgrading every overloaded transformer",
    f"lower net cost than upgrading every overloaded transformer; {lo}% to {hi}% at loading limits from 100% to 140%")
put(8, 24, "Moderate: 20% of homes add an EV, 15% a heat pump; high: 35% and 30%. Upgrades counted for 15 of their 40 years. "
           "Net = after customer lease and NYSERDA ($261M high case without NYSERDA).",
    "Overloaded = above 120% of rating. Moderate: 20% of homes add an EV, 15% a heat pump; high: 35% and 30%. Upgrades counted "
    f"for 15 of their 40 years. Net = after customer lease and NYSERDA; before them the battery path costs ${gross['moderate']}M vs "
    f"${upall['moderate']}M (moderate) and ${gross['high']}M vs ${upall['high']}M (high).")

deck.save(str(OUT))
for n, a, b in log:
    print(f"slide {n}: {a}  ->  {b}")
print(f"{len(log)} edits -> {OUT}")
