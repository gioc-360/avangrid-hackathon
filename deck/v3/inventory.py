"""Inventory every number in the team deck: text runs, table cells, chart values, categories, series names and
titles, speaker notes; and every picture (numbers baked into an image cannot be edited).

What: writes outputs/deck/v3/numbers.csv, one row per number with a stable id that fact_map.yaml and apply.py use.
      Text ids are  sNN/<shape id>/pP/mK  (paragraph P, K-th number in it), tables add rRcC, notes use "notes",
      chart values  sNN/<shape id>/chart/serI/ptJ, categories .../chart/catJ/mK, series names .../chart/serI/name/mK,
      titles .../chart/title/mK and .../chart/axis<A>/mK. Pictures get one row each, described from the render
      (PICTURES below, written after looking at outputs/deck/v3/render_current).
Why:  v3 must make every number consistent with our engine; a number we never listed is a number nobody checks.
How:  python-pptx on a copy of the deck (never the file in ~/Downloads). Numbers are matched on the paragraph's
      concatenated run text, so a number split across runs is still one row, with the runs it spans recorded.
      Scatter charts hold per-home points: they are summarized as one row per series (count and ranges), never
      listed point by point, so no per-home data lands in a CSV.
    .venv/bin/python -I deck/v3/inventory.py outputs/deck/v3/source_copy.pptx outputs/deck/v3/numbers.csv
"""
import csv
import re
import sys
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
C = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"

# A number: optional $, digits with thousands commas or a decimal, optional unit suffix glued or after one space.
NUMBER = re.compile(
    r"(?<![\d.,])(?P<cur>\$)?(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"(?P<suf>(?:\s?(?:%|kWh|MWh|kVA|MW|kW|GW|GB|°F)|M\b|k\b|B\b|x\b))?")
UNIT_WORDS = {"homes", "home", "transformers", "transformer", "days", "day", "hours", "hour", "min", "minutes",
              "units", "unit", "meters", "years", "year", "segments", "customers", "features", "files", "parts",
              "sessions", "rows", "temperatures", "fold", "times", "batteries", "evs", "zevs", "kwh", "kw", "mw"}

# What each picture shows, from the render (outputs/deck/v3/render_current/p-NN.png), keyed by (slide, shape id).
PICTURES = {
    (1, 2): ("Avangrid logo", ""),
    (1, 6): ("headshot, Kayin Bejide", ""),
    (1, 9): ("headshot, Raissa Refita Pramudi", ""),
    (1, 12): ("headshot, Gio Caballero", ""),
    (15, 2): ("Avangrid logo", ""),
    (20, 4): ("A4 six-panel figure 'Part 1: load signatures used to classify technologies': EV Level 2 week trace "
              "(9 to 13 kW blocks), electric heating scatter, AC scatter, pool, solar, known-EV share by EV tier",
              "Primary electric heat (5,190); Supplemental (4,625); No electric heat (23,942); Central AC likely "
              "(16,833); Room or light use (11,928); No AC signal (4,996); Pool (exploratory, 433); Solar (525); "
              "EV tier bars 10.9%, 4.6%, 2.3%, 0.4%; 9 to 13 kW; above about 60°F; axis ticks"),
    (24, 6): ("A8 example priority customer (heavy AC), July 2: hourly bars, home load today vs with battery, "
              "overnight charging; a single real home",
              "cut from 6.2 to 3.6 kW; Slow overnight charging (2.6 kW); axis ticks 0 to 7 kWh, hours 0 to 22"),
}


def walk(shapes):
    for sh in shapes:
        if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from walk(sh.shapes)
        else:
            yield sh


def segments(p_el):
    """Text pieces of a paragraph in order: (run index or None, text). Runs (a:r) and fields (a:fld) carry text,
    a:br is a line break inside the paragraph."""
    out, k = [], 0
    for child in p_el:
        tag = child.tag
        if tag in (A + "r", A + "fld"):
            t = child.find(A + "t")
            out.append((k, t.text if t is not None and t.text else ""))
            k += 1
        elif tag == A + "br":
            out.append((None, "\v"))
    return out


def unit_of(m, text):
    if m.group("cur"):
        return "$" + (m.group("suf") or "").strip()
    suf = (m.group("suf") or "").strip()
    if suf:
        return suf
    num = m.group("num")
    before = text[max(0, m.start() - 1):m.start()]
    if before.isalpha() or before in ("β",):
        return "label"
    if re.fullmatch(r"20[2-3]\d|19\d\d", num):
        return "year"
    after = text[m.end():m.end() + 30].strip().split(" ")
    word = re.sub(r"[^A-Za-z]", "", after[0]).lower() if after and after[0] else ""
    return word if word in UNIT_WORDS else ""


def numbers_in(text):
    for k, m in enumerate(NUMBER.finditer(text)):
        yield k, m


def value_of(m):
    try:
        return float(m.group("num").replace(",", ""))
    except ValueError:
        return ""


def text_rows(prefix, base, p_els):
    rows = []
    for pi, p_el in enumerate(p_els):
        segs = segments(p_el)
        text = "".join(t for _, t in segs)
        if not any(ch.isdigit() for ch in text):
            continue
        # character offset -> run index
        owner, pos = [], 0
        for ri, t in segs:
            owner.extend([ri] * len(t))
        for k, m in numbers_in(text):
            runs = sorted({owner[i] for i in range(m.start(), m.end()) if owner[i] is not None})
            rows.append(dict(base, id=f"{prefix}/p{pi}/m{k}", para=pi, runs="-".join(map(str, runs)),
                             spans_runs=len(runs) > 1, text=text.replace("\v", " / "), number=m.group(0),
                             value=value_of(m), unit=unit_of(m, text)))
    return rows


def chart_rows(sid, sh, base):
    rows, chart = [], sh.chart
    cs = chart._chartSpace
    pre = f"s{sid:02d}/{sh.shape_id}/chart"
    title = cs.find(f".//{C}title")
    if title is not None and chart.has_title:
        rows += text_rows(f"{pre}/title", dict(base, kind="chart_title"), title.iter(A + "p"))
    for ai, ax in enumerate(cs.iter(C + "valAx", C + "catAx", C + "dateAx")):
        t = ax.find(C + "title")
        if t is not None:
            rows += text_rows(f"{pre}/axis{ai}", dict(base, kind="chart_axis_title"), t.iter(A + "p"))
    sers = [s for pl in chart.plots for s in pl.series]
    xy = chart.chart_type is not None and "SCATTER" in str(chart.chart_type)
    if not xy:
        cats = list(chart.plots[0].categories)
        for j, c in enumerate(cats):
            label = str(c)
            for k, m in numbers_in(label):
                rows.append(dict(base, kind="chart_category", id=f"{pre}/cat{j}/m{k}", para="", runs="",
                                 spans_runs=False, text=label, number=m.group(0), value=value_of(m),
                                 unit=unit_of(m, label)))
    for i, se in enumerate(sers):
        name = se.name or ""
        for k, m in numbers_in(name):
            rows.append(dict(base, kind="chart_series_name", id=f"{pre}/ser{i}/name/m{k}", para="", runs="",
                             spans_runs=False, text=name, number=m.group(0), value=value_of(m), unit=unit_of(m, name)))
        if xy:
            xs = [float(v.text) for v in se._element.iterfind(f"./{C}xVal//{C}pt/{C}v") if v.text]
            ys = [float(v.text) for v in se._element.iterfind(f"./{C}yVal//{C}pt/{C}v") if v.text]
            rng = (f"{len(ys)} points; x {min(xs):.2f} to {max(xs):.2f}; y {min(ys):.2f} to {max(ys):.2f}"
                   if ys and xs else f"{len(ys)} points")
            rows.append(dict(base, kind="chart_xy_series", id=f"{pre}/ser{i}", para="", runs="", spans_runs=False,
                             text=f"{name}: {rng} (per-home points, summarized)", number=len(ys), value=len(ys),
                             unit="points"))
            continue
        cats = list(chart.plots[0].categories)
        for pt in se._element.iterfind(f"./{C}val//{C}pt"):
            j = int(pt.get("idx"))
            v = pt.find(C + "v")
            if v is None or v.text is None:
                continue
            rows.append(dict(base, kind="chart_value", id=f"{pre}/ser{i}/pt{j}", para="", runs="", spans_runs=False,
                             text=f"{name} @ {cats[j] if j < len(cats) else j}", number=v.text, value=float(v.text),
                             unit=""))
    return rows


def inventory(path):
    prs = Presentation(path)
    rows = []
    for sid, slide in enumerate(prs.slides, 1):
        for sh in walk(slide.shapes):
            base = dict(slide=sid, shape_id=sh.shape_id, shape_name=sh.name, cell="")
            if sh.is_placeholder and sh.placeholder_format.type is not None and "SLIDE_NUMBER" in str(sh.placeholder_format.type):
                continue                                   # page numbers: layout field, not content
            if getattr(sh, "has_table", False) and sh.has_table:
                for r, row in enumerate(sh.table.rows):
                    for c, cell in enumerate(row.cells):
                        rows += text_rows(f"s{sid:02d}/{sh.shape_id}/r{r}c{c}", dict(base, kind="table", cell=f"r{r}c{c}"),
                                          cell.text_frame._txBody.iterfind(A + "p"))
            elif getattr(sh, "has_chart", False) and sh.has_chart:
                rows += chart_rows(sid, sh, base)
            elif sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
                what, nums = PICTURES.get((sid, sh.shape_id), ("NOT DESCRIBED: look at the render", "?"))
                rows.append(dict(base, kind="picture", id=f"s{sid:02d}/{sh.shape_id}/picture", para="", runs="",
                                 spans_runs=False, text=what, number=nums, value="", unit="baked into image"))
            elif sh.has_text_frame:
                rows += text_rows(f"s{sid:02d}/{sh.shape_id}", dict(base, kind="text"),
                                  sh.text_frame._txBody.iterfind(A + "p"))
        if slide.has_notes_slide:
            tf = slide.notes_slide.notes_text_frame
            if tf is not None:
                rows += text_rows(f"s{sid:02d}/notes", dict(slide=sid, shape_id="notes", shape_name="notes", cell="",
                                                            kind="notes"), tf._txBody.iterfind(A + "p"))
    return rows


FIELDS = ["id", "slide", "shape_id", "shape_name", "kind", "cell", "para", "runs", "spans_runs", "text", "number",
          "value", "unit"]

if __name__ == "__main__":
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    if "Downloads" in src.resolve().parts:
        sys.exit("refusing to read from ~/Downloads directly: copy the deck to outputs/deck/v3 first")
    rows = inventory(src)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(f"{len(rows)} rows to {out}")
    for k, n in sorted(Counter(r["kind"] for r in rows).items()):
        print(f"  {k:20s} {n}")
    print("  numbers spanning runs:", sum(1 for r in rows if r["spans_runs"]))
