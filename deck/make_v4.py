"""Deck v4: the team's v3 deck with every number made consistent with the engine (facts/facts.json) and the app.

What: text-only edits (numbers and the words that say what a number means), two slide 12 charts and the slide 7
      axis rebuilt from the same values, the slide 5 average-home lines moved to the bubbles' own basis, and the
      A17 screenshot swapped for a current app frame. Every edit asserts its old text appears exactly once.
Why:  four judges stopped at slide 12, whose numbers came from an older saved run; one run (the engine's, the one
      in the video, the dashboard and A13) must drive every slide.
How:  .venv/bin/python -I deck/make_v4.py SRC.pptx APP_SCREENSHOT.png OUT.pptx   (never overwrites OUT)
"""
import copy
import json
import sys
from pathlib import Path
from pptx import Presentation
from pptx.chart.data import CategoryChartData

SRC, SHOT, OUT = (Path(a) for a in sys.argv[1:4])
if OUT.exists():
    sys.exit(f"refusing to overwrite {OUT}")
FACTS = json.loads((Path(__file__).resolve().parent.parent / "facts" / "facts.json").read_text())


def fact(key):
    return FACTS[key]["value"]


M, H = "ewu.deck.moderate.limit_120", "ewu.deck.high.limit_120"
fixed = (round(fact(f"{H}.fixed_of_overloaded_pct")), round(fact(f"{M}.fixed_of_overloaded_pct")))      # 92, 98
saving = (round(fact(f"{H}.saving_vs_upgrade_all_pct")), round(fact(f"{M}.saving_vs_upgrade_all_pct")))  # 58, 69
over = (fact(f"{M}.overloaded_pct"), fact(f"{H}.overloaded_pct"))                                          # 9.73, 29.87
lease = round(fact("ewu.deck.prices.lease_pv_usd"))                                                       # 3006
upgrade_pv = round(fact("ewu.deck.prices.upgrade_counted_usd"))                                           # 10248
units = (fact(f"{M}.average_units"), fact(f"{H}.average_units"))                                          # 1.54, 1.91
energy = (fact("ewu.deck.moderate.added_energy_pct"), fact("ewu.deck.high.added_energy_pct"))             # 23.5, 44.8
net_unit = 7000 - lease - 2016
assert (fixed, saving, lease, net_unit) == ((92, 98), (58, 69), 3006, 1978), (fixed, saving, lease, net_unit)
per_tf = (round(units[0] * net_unit, -2), round(units[1] * net_unit, -2))                                 # 3000, 3800
FIX, SAVE = f"{fixed[0]}% to {fixed[1]}%", f"{saving[0]}% to {saving[1]}%"
OVER = f"{over[0]:.1f}% to {over[1]:.1f}%"

deck = Presentation(str(SRC))
log = []


def shape(n, sid):
    found = [s for s in deck.slides[n - 1].shapes if s.shape_id == sid]
    assert len(found) == 1, f"slide {n}: shape {sid} not found"
    return found[0]


def swap(n, sid, old, new):
    """Replace old with new inside one run of shape sid on slide n; old must occur exactly once in the shape."""
    frames = [shape(n, sid).text_frame]
    hits = [r for tf in frames for p in tf.paragraphs for r in p.runs if old in r.text]
    total = sum(r.text.count(old) for r in hits)
    assert total == 1, f"slide {n} shape {sid}: '{old}' found {total} times"
    hits[0].text = hits[0].text.replace(old, new)
    log.append((n, old, new))


def swap_cell(n, sid, row, col, old, new):
    cell = shape(n, sid).table.cell(row, col)
    runs = [r for p in cell.text_frame.paragraphs for r in p.runs if old in r.text]
    assert len(runs) == 1 and runs[0].text.count(old) == 1, f"slide {n} cell {row},{col}: '{old}'"
    runs[0].text = runs[0].text.replace(old, new)
    log.append((n, old, new))


def swap_notes(n, old, new):
    tf = deck.slides[n - 1].notes_slide.notes_text_frame
    runs = [r for p in tf.paragraphs for r in p.runs if old in r.text]
    assert len(runs) == 1, f"slide {n} notes: '{old}' in {len(runs)} runs"
    runs[0].text = runs[0].text.replace(old, new)
    log.append((n, "notes: " + old[:40], new[:40]))


# Slide 2: executive summary
swap(2, 19, "94% to 98%", FIX)
swap(2, 9, "Upgrading transformers costs $111M to $340M", "Upgrading transformers costs $111M to $340M (present value, 15 years)")
swap(2, 18, "with 2 units each", "with 2 units each, export allowed")
# Slide 4: classification
swap(4, 3, "and about 1,300 likely own an EV", "and 1,331 show EV charging (about 724 expected owners)")
swap(4, 152, "About 31% of charging sessions", "About 29% of charging sessions")
# Slide 5: bubbles are top-100-hour averages (A6), so the axes and the average-home lines use that basis too
swap(5, 221, "at the summer peak (July 2, 5pm)", "in the top 100 summer system hours")
swap(5, 222, "at the winter peak (Jan 25, 5pm)", "in the top 100 winter system hours")
swap(5, 245, "1.5 times the average home", "about 2 times the average home")
swap(5, 245, "twice the average", "2.5 times the average")
X0, XU, Y0, YU = 1143000, 1348740, 5532120, 937260          # axis origin and one unit, from the tick shapes
seg = {"heavy": (4436, 3.48, 2.02), "evening": (8941, 1.83, 0.79), "steady": (7806, 1.92, 1.07), "low": (5324, 0.56, 0.63),
       "heat": (3703, 1.90, 3.26), "seasonal": (3022, 0.65, 0.97), "solar": (525, 0.90, 1.49)}   # A6, top 100 hours
homes = sum(v[0] for v in seg.values())
avg_s = sum(v[0] * v[1] for v in seg.values()) / homes       # 1.75 kW
avg_w = sum(v[0] * v[2] for v in seg.values()) / homes       # 1.29 kW
vline, hline, label = shape(5, 223), shape(5, 224), shape(5, 225)
assert abs((vline.left - X0) / XU - 2.33) < 0.01 and abs((Y0 - hline.top) / YU - 1.68) < 0.01
vline.left = int(X0 + avg_s * XU)
label.left = vline.left + 45720
hline.top = int(Y0 - avg_w * YU)
log.append((5, "average lines 2.33 / 1.68 kW", f"{avg_s:.2f} / {avg_w:.2f} kW"))
# Slide 6: share of the summer peak from the A6 table
two_ac = (seg["heavy"][0] * seg["heavy"][1] + seg["evening"][0] * seg["evening"][1]) / (avg_s * homes)
swap(6, 3, "but 52% of the summer peak", f"but {round(100 * two_ac)}% of the summer peak")
# Slide 7: a date axis, one label per month (the old category axis put a label every 30 days, so "Oct 25" showed twice)
import datetime as dt
from lxml import etree
chart7 = next(s for s in deck.slides[6].shapes if s.has_chart).chart
values = list(chart7.plots[0].series[0].values)
assert len(values) == 365
cd = CategoryChartData(number_format="mmm yyyy")
cd.categories = [dt.date(2025, 9, 1) + dt.timedelta(days=i) for i in range(365)]
cd.add_series(chart7.plots[0].series[0].name, values)
chart7.replace_data(cd)
C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
cat = chart7._chartSpace.xpath(".//c:catAx")
assert len(cat) == 1
ax = cat[0]
ax.tag = f"{{{C}}}dateAx"
for name in ("lblAlgn", "tickLblSkip", "tickMarkSkip", "noMultiLvlLbl"):
    for el in ax.findall(f"{{{C}}}{name}"):
        ax.remove(el)
fmt = ax.find(f"{{{C}}}numFmt")
fmt.set("formatCode", "mmm"), fmt.set("sourceLinked", "0")
offset = ax.find(f"{{{C}}}lblOffset")
for tag, val in (("majorTimeUnit", "months"), ("majorUnit", "1"), ("baseTimeUnit", "days")):
    el = etree.SubElement(ax, f"{{{C}}}{tag}")
    el.set("val", val)
    offset.addnext(el)
log.append((7, "axis: a label every 30 days", "date axis, one label per month"))
# Slide 8 and A8: recharge rate, 16.1 kWh / 0.894 / 7 h
swap(8, 9, "about 2.3 kW", "about 2.6 kW")
swap(24, 5, "about 2.3 kW", "about 2.6 kW")
# Slide 9 and 15: the 8.8 MW fleet cut lets batteries export in turns
swap(9, 7, "peak cut (11%), 2,610 homes", "peak cut (11%), 2,610 homes, export allowed")
swap(15, 6, "summer peak cut today", "summer peak cut, export allowed")
# Slide 10: per-transformer money on one present-value basis
swap(10, 19, "≈ $3,000", f"${per_tf[0]:,.0f} to ${per_tf[1]:,.0f}")
swap(10, 20, "vs a $15,000 upgrade", f"vs ${upgrade_pv:,} for a $15,000 upgrade, same 15-year basis")
swap(10, 24, "($3,000 over 15 years)", f"(${lease:,} over 15 years)")
swap(36, 29, "lease ($3,000)", f"lease (${lease:,})")
# Slide 12: results from the engine run
swap(12, 3, "94% to 98%", FIX)
swap(12, 3, "59% to 71%", SAVE)
swap(12, 26, "9.8% to 29.8%", OVER)
swap(12, 28, "94% to 98%", FIX)
swap(12, 30, "59% to 71%", SAVE)
charts = {s.shape_id: s.chart for s in deck.slides[11].shapes if s.has_chart}
bands = CategoryChartData()
bands.categories = [f"Moderate: {over[0]:.1f}%", f"High: {over[1]:.1f}%"]
for name, key in (("Fixed by 1 or 2 batteries", "fixed_units_1_2_pct"), ("Fixed by 3 or 4 batteries", "fixed_units_3_4_pct"),
                  ("Still needs an upgrade", "upgrades_pct")):
    bands.add_series(name, (fact(f"{M}.{key}"), fact(f"{H}.{key}")))
charts[21].replace_data(bands)
cost = CategoryChartData()
cost.categories = ["Moderate 2030", "High 2030"]
cost.add_series("Upgrade every overloaded transformer", (round(fact(f"{M}.nyseg_upgrade_all_musd")), int(fact(f"{H}.nyseg_upgrade_all_musd"))))
cost.add_series("Electrify Without Upgrade (net)", (round(fact(f"{M}.nyseg_avangrid_cost_musd")), round(fact(f"{H}.nyseg_avangrid_cost_musd"))))
charts[22].replace_data(cost)
log.append((12, "charts from the saved run", "charts from facts.json"))
# Slide 13: money is a present-value net gap; energy from ewu/deck_energy.py
swap(13, 10, "$77M to $197M less capital for neighborhood upgrades", "$77M to $197M lower net cost than neighborhood upgrades (present value)")
swap(13, 13, "23% to 44% more energy sold", f"{energy[0]:.1f}% to {energy[1]:.1f}% more energy sold")
# Slide 14: two different run times
swap(14, 9, "33,757 homes in about 15 minutes;", "33,757 homes profiled in about 15 minutes; the transformer screen runs in about 2 seconds;")
# Appendix
swap(16, 13, "A10 Example customer", "A10 Sizing check")
swap(16, 21, "A18 How the engine works", "A18a to A18c How the engine works")
table19 = next(s for s in deck.slides[18].shapes if s.has_table).shape_id
swap_cell(19, table19, 1, 4, "2.9x more common", "3.1x more common")
swap_cell(19, table19, 7, 4, "23 listed show no pattern", "30 listed not found")
swap(29, 5, "in every row", "in 7 of 10 rows")
swap(33, 19, "the one source of every number", "the one source of every transformer and money number")
swap(33, 21, "deck setup", "battery plan")
swap(35, 75, "deck v3 equals facts", "slides equal facts")
swap_notes(34, "Replaces v3 slide A18 'How the engine works' (the picture) with three editable slides: A18a top level, A18b mid level, A18c low level. ",
           "Three levels: A18a top, A18b mid, A18c low. ")
swap_notes(35, "deck/v3/independent_check.py checks deck v3's numbers against facts", "an independent check compares the slides' numbers against facts")
# A17: current app screenshot in the same box and stacking position
old = shape(33, 26)
box = (old.left, old.top, old.width, old.height)
new = deck.slides[32].shapes.add_picture(str(SHOT), *box)
old._element.addprevious(new._element)
old._element.getparent().remove(old._element)
log.append((33, "screenshot with Deck setup tabs", "current app, Network view, Upgrade"))

deck.save(str(OUT))
for n, a, b in log:
    print(f"slide {n:>2}: {a}  ->  {b}")
print(f"{len(log)} edits -> {OUT}")
