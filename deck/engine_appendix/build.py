"""Engine appendix: three slides, top, mid and low level, that explain how the EWU engine works, in deck v3's template.

What: writes outputs/deck/engine_appendix/EWU_engine_appendix.pptx with exactly 3 slides (A18a context, A18b
      pipeline, A18c one transformer's math) that replace deck v3's A18 "How the engine works" picture. Every
      diagram is native PowerPoint shapes (rounded rectangles, arrow connectors, text boxes), so the teammates
      can edit the words in place.
Why:  Gio asked for system architecture diagrams at three levels, with what, why and how carried by the
      slide itself (title = the so-what, diagram = the how, caption and notes = the why), in the deck's look.
How:  opens a COPY of ~/Downloads/D4G Cornell 2_Final Submission_v3.pptx (never the file itself), adds three
      slides on the A18 slide's layout and copies its eyebrow, title and slide number shapes, then deletes
      every original slide and rewrites the section list. Every number comes from facts/facts.json or
      config/ewu.yaml and must appear in deck v3's own text for the same claim, else the build stops. A
      self-check then fails on any text under 12 pt (except v3's own 11 pt eyebrow), any shape off the
      slide, any em dash, and any synonym docs/TERMS.md bans.
    .venv/bin/python -I deck/engine_appendix/build.py
"""
import copy
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import yaml
from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from checks.terms_check import TERMS, find_synonyms, read_terms  # noqa: E402

V3 = Path.home() / "Downloads" / "D4G Cornell 2_Final Submission_v3.pptx"
OUT = ROOT / "outputs" / "deck" / "engine_appendix" / "EWU_engine_appendix.pptx"
FACTS = json.loads((ROOT / "facts" / "facts.json").read_text())
CONFIG = yaml.safe_load((ROOT / "config" / "ewu.yaml").read_text())

# deck v3's theme colors, read off its slides
GREEN, DARK, BLUE, BLUE_D = RGBColor(0x00, 0x8C, 0x38), RGBColor(0x0B, 0x3B, 0x30), RGBColor(0x00, 0xAB, 0xE8), RGBColor(0x00, 0x89, 0xBD)
ORANGE, ORANGE_D, INK, GREY = RGBColor(0xF7, 0x92, 0x1D), RGBColor(0xC4, 0x6A, 0x00), RGBColor(0x1D, 0x2B, 0x24), RGBColor(0x5F, 0x6B, 0x66)
RULE, LIGHT, WHITE = RGBColor(0xD5, 0xDE, 0xD8), RGBColor(0xEE, 0xF5, 0xF0), RGBColor(0xFF, 0xFF, 0xFF)
MONO = "Consolas"
P14 = "http://schemas.microsoft.com/office/powerpoint/2010/main"
MIN_PT = 12


# ---------------------------------------------------------------- numbers: facts or config, checked against deck v3
def fact(key):
    return FACTS[key]["value"]


def cfg(dotted):
    node = CONFIG
    for part in dotted.split("."):
        node = node[part]
    return node["value"]


def numbers():
    """{name: text} for every number on the three slides, each from facts or config."""
    d = "profiles.deck."
    per, nyt = cfg(d + "transformer_count"), fact("ewu.deck.nyseg_transformers")
    counted = cfg(d + "upgrade_usd") * fact("ewu.deck.prices.factor") / fact("ewu.deck.prices.life_factor")
    net_unit = cfg(d + "battery_unit_usd") - fact("ewu.deck.prices.lease_pv_usd") - cfg(d + "nyserda_usd_unit")

    def money(sc):
        k = f"ewu.deck.{sc}.limit_120."
        net = (fact(k + "batteries") * net_unit + fact(k + "upgrades") * counted) * nyt / per / 1e6
        upall = fact(k + "overloaded") * counted * nyt / per / 1e6
        return net, upall, 100 * (1 - net / upall)

    (nm, um, sm), (nh, uh, sh) = money("moderate"), money("high")
    pct = lambda sc, f: fact(f"ewu.deck.{sc}.limit_120.{f}")  # noqa: E731
    sizes = cfg(d + "standard_sizes_kva")
    return {
        "homes": f"{fact('data.customers_usable'):,}",
        "hours": "8,760",
        "overloaded": f"{pct('moderate', 'overloaded_pct'):.0f}% to {pct('high', 'overloaded_pct'):.0f}%",
        "fixed": f"{pct('high', 'fixed_of_overloaded_pct'):.0f}% to {pct('moderate', 'fixed_of_overloaded_pct'):.0f}%",
        "priority": f"{fact('teammate.audit.rerun.priority_homes'):,}",
        "peak_cut": f"{fact('teammate.audit.rerun.fleet_priority.peak_cut_mw'):.1f} MW",
        "units_per_home": f"{cfg(d + 'units_per_host')}",
        "saving": f"{sh:.0f}% to {sm:.0f}%",
        "net_m": f"${nm:,.0f}M", "upall_m": f"${um:,.0f}M", "net_h": f"${nh:,.0f}M", "upall_h": f"${uh:,.0f}M",
        "transformers": f"{per:,}",
        "homes_per": f"{cfg(d + 'homes_per_transformer')}",
        "divisor": f"{cfg(d + 'peak_to_rating_divisor'):.2f}",
        "size_lo": f"{sizes[0]:g}", "size_hi": f"{sizes[-1]:g} kVA",
        "limit": f"{cfg(d + 'overload_limit'):.0%}",
        "ev_kw": f"{cfg(d + 'ev_kw')} kW", "ev_hours": f"{cfg(d + 'ev_hours')} hours",
        "ev_week": f"{cfg(d + 'ev_day_share') * 7:.1f} sessions a week",
        "ev_sessions": f"{cfg('teammate_reference.ev_sessions'):,}",
        "hp_kwh": f"{round(fact('ewu.deck.inputs.hp_increment.annual_kwh'), -2):,.0f} kWh",
        "ev_m": f"{cfg('scenarios.moderate.ev_share'):.0%}", "hp_m": f"{cfg('scenarios.moderate.hp_share'):.0%}",
        "ev_h": f"{cfg('scenarios.high.ev_share'):.0%}", "hp_h": f"{cfg('scenarios.high.hp_share'):.0%}",
        "unit_kw": f"{cfg(d + 'unit_kw')} kW", "unit_kwh": f"{cfg(d + 'unit_kwh')} kWh",
        "units_min": f"{cfg(d + 'units_min')}", "units_max": f"{cfg(d + 'units_max')}",
        "unit_usd": f"${cfg(d + 'battery_unit_usd'):,}",
        "lease_pv": f"${round(fact('ewu.deck.prices.lease_pv_usd'), -3):,.0f}",
        "nyserda": f"${cfg(d + 'nyserda_usd_unit'):,}",
        "net_unit": f"${net_unit:,.0f}",
        "upgrade": f"${cfg(d + 'upgrade_usd'):,}",
        "counted": f"${counted:,.0f}",
        "years": f"{cfg(d + 'years')}", "life": f"{cfg(d + 'upgrade_life_years')} years",
        "rate": f"{cfg(d + 'discount_rate'):.0%}",
        "nyseg": f"{cfg('prices.nyseg_electric_customers'):,}",
    }


# where deck v3 states the same claim: each number's text must appear inside this v3 text
V3_CLAIMS = {
    "homes": "{homes} homes x {hours} hours", "overloaded": "{overloaded}", "fixed": "{fixed} of overloaded transformers",
    "priority": "{priority} priority homes with {units_per_home} units each", "peak_cut": "summer peak by {peak_cut}",
    "saving": "{saving} less than upgrading", "net_m": "Net cost {net_m} vs {upall_m} (moderate 2030) and {net_h} vs {upall_h}",
    "transformers": "{transformers} synthetic, {homes_per} real homes each",
    "divisor": "Smallest of {size_lo}, 37.5, 50, 75, 100, {size_hi} ≥ today's peak / {divisor}",
    "limit": "Any hour above {limit} of rating", "ev": "{ev_kw} Level 2, {ev_week}, {ev_hours}; start times from {ev_sessions} observed sessions",
    "hp": "about {hp_kwh} a year", "scen": "{ev_m} of homes add an EV, {hp_m} a heat pump. High: {ev_h} and {hp_h}",
    "unit": "{unit_kw}, {unit_kwh} usable; up to {units_max} units, else upgrade",
    "unit_money": "{unit_usd} less lease ({lease_pv} over {years} years) and NYSERDA ({nyserda}) = {net_unit}",
    "counted": "present value over {years} years at {rate}, an upgrade counted for {years} of its {life} ({upgrade} counts as {counted})",
    "nyseg": "x {nyseg} / ({homes_per} x {transformers})",
}


def deck_text(prs):
    """All text of a deck, runs, tables and notes, whitespace collapsed."""
    parts = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                parts.append(shape.text_frame.text)
            if shape.has_table:
                parts += [c.text for r in shape.table.rows for c in r.cells]
        if slide.has_notes_slide:
            parts.append(slide.notes_slide.notes_text_frame.text)
    return re.sub(r"\s+", " ", " \n ".join(parts))


def check_numbers(n, v3_text):
    missing = [f"{k}: '{t.format(**n)}'" for k, t in V3_CLAIMS.items() if t.format(**n) not in v3_text]
    if missing:
        sys.exit("number differs from deck v3 (or v3 no longer states it):\n  " + "\n  ".join(missing))
    return {k: t.format(**n) for k, t in V3_CLAIMS.items()}


# ---------------------------------------------------------------- drawing helpers
def I(x):  # noqa: E743
    return Inches(x)


def style_runs(par, runs):
    for words, size, bold, color, font in runs:
        r = par.add_run()
        r.text = words
        r.font.size, r.font.bold, r.font.color.rgb = Pt(size), bold, color
        if font:
            r.font.name = font


def fill_frame(tf, paras, anchor=MSO_ANCHOR.TOP, align=PP_ALIGN.LEFT, inset=0.08, space=3):
    """paras: list of paragraphs, each a list of runs (text, pt, bold, color, font or None)."""
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = I(inset)
    tf.margin_top = tf.margin_bottom = I(0.04)
    for i, runs in enumerate(paras):
        par = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        par.alignment = align
        if i:
            par.space_before = Pt(space)
        style_runs(par, runs)


def text(slide, x, y, w, h, paras, **kw):
    tb = slide.shapes.add_textbox(I(x), I(y), I(w), I(h))
    fill_frame(tb.text_frame, paras, **kw)
    return tb


def box(slide, x, y, w, h, fill=LIGHT, line=RULE, line_pt=0.75, dash=None, radius=0.06, paras=None, **kw):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, I(x), I(y), I(w), I(h))
    shp.adjustments[0] = radius / min(w, h)
    shp.shadow.inherit = False
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb, shp.line.width = line, Pt(line_pt)
        if dash:
            shp.line.dash_style = dash
    fill_frame(shp.text_frame, paras or [[("", MIN_PT, False, INK, None)]], **kw)
    return shp


PILLS = {"GIVEN": (INK, None), "DERIVED": (None, None), "SIMULATED": (None, MSO_LINE_DASH_STYLE.DASH),
         "ASSUMED": (None, MSO_LINE_DASH_STYLE.ROUND_DOT)}


def pill(slide, x, y, tag):
    fill, dash = PILLS[tag]
    w = 0.22 + 0.105 * len(tag)
    box(slide, x, y, w, 0.27, fill=fill, line=INK, line_pt=1, dash=dash, radius=0.135,
        paras=[[(tag, MIN_PT, True, WHITE if fill else INK, None)]], anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER, inset=0.02)
    return w


def arrow(slide, x1, y1, x2, y2, color=GREY, a=None, b=None):
    """Straight connector with an arrowhead at its end; glued to shapes a and b when given (right side to left side)."""
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, I(x1), I(y1), I(x2), I(y2))
    if a is not None:
        c.begin_connect(a, 3)
    if b is not None:
        c.end_connect(b, 1)
    c.line.color.rgb, c.line.width = color, Pt(1.75)
    ln = c.line._get_or_add_ln()
    tail = etree.SubElement(ln, qn("a:tailEnd"))
    tail.set("type", "triangle"), tail.set("w", "med"), tail.set("len", "med")
    return c


# ---------------------------------------------------------------- slides
def new_slide(prs, a18, eyebrow, title):
    s = prs.slides.add_slide(a18.slide_layout)
    for ph in list(s.placeholders):
        ph._element.getparent().remove(ph._element)
    for shape in a18.shapes:
        if shape.has_text_frame and (shape.name in ("Text 0", "Text 1") or shape.is_placeholder):
            el = copy.deepcopy(shape._element)
            s.shapes._spTree.append(el)
    for shape in s.shapes:
        if shape.has_text_frame and shape.text_frame.text.startswith("APPENDIX"):
            set_text(shape, eyebrow)
        elif shape.name == "Text 1":
            set_text(shape, title)
    return s


def set_text(shape, words):
    """Keep the first run's formatting, replace the text, drop every other run and paragraph."""
    paras = shape.text_frame.paragraphs
    for p in paras[1:]:
        p._p.getparent().remove(p._p)
    runs = paras[0].runs
    runs[0].text = words
    for r in runs[1:]:
        r._r.getparent().remove(r._r)


def caption(slide, y, lines):
    text(slide, 0.6, y, 12.1, 0.3 * len(lines) + 0.1, [[(ln, MIN_PT, False, GREY, None)] for ln in lines], inset=0)


def slide_top(prs, a18, n):
    s = new_slide(prs, a18, "APPENDIX  |  A18a",
                  "How the engine works, top level: data Avangrid already collects becomes one action list for each of three teams")
    heads = [(0.6, "Avangrid already collects"), (3.95, "One offline run"), (7.35, "Lists it writes"), (10.35, "Team that acts")]
    for x, h in heads:
        text(s, x, 1.62, 2.9, 0.32, [[(h, 13, True, GREY, None)]], inset=0)
    rows = [2.62, 3.82, 5.02]  # centre line of each row
    bh = 0.98
    ins = [("Hourly meter data", f"every home, {n['hours']} hours a year", None),
           ("Hourly weather", "temperature, every hour", None),
           ("Transformer map", "meter to transformer, joined in the 2027 pilot", MSO_LINE_DASH_STYLE.DASH)]
    for (label, sub, dash), cy in zip(ins, rows):
        box(s, 0.6, cy - bh / 2, 2.75, bh, fill=WHITE if dash else LIGHT, line=GREY if dash else RULE, line_pt=1.25 if dash else 0.75,
            dash=dash, paras=[[(label, 14, True, DARK, None)], [(sub, MIN_PT, False, INK, None)]], anchor=MSO_ANCHOR.MIDDLE, inset=0.14)
    top, bot = rows[0] - bh / 2, rows[-1] + bh / 2
    box(s, 3.95, top, 2.85, bot - top, fill=GREEN, line=None, radius=0.1,
        paras=[[("EWU engine", 22, True, WHITE, None)],
               [("One batch run on Avangrid's own machines", 14, False, WHITE, None)],
               [("Customer data never leaves", 14, False, WHITE, None)],
               [("bin/ewu", 14, False, WHITE, MONO)]],
        anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER, inset=0.18, space=10)
    for cy in rows:
        arrow(s, 3.35, cy, 3.95, cy)
    outs = [("Transformer action list", "transformer_actions.csv"), ("Priority homes list", "program_targets.csv"),
            ("Capital plan", "capital_plan.csv")]
    out_shapes = []
    for (label, f), cy in zip(outs, rows):
        out_shapes.append(box(s, 7.35, cy - bh / 2, 2.5, bh, fill=WHITE, line=BLUE_D, line_pt=1.5,
                              paras=[[(label, 14, True, BLUE_D, None)], [(f, MIN_PT, False, INK, MONO)]],
                              anchor=MSO_ANCHOR.MIDDLE, inset=0.14))
        arrow(s, 6.8, cy, 7.35, cy)
    teams = [("Distribution planner", n["overloaded"], "of transformers overloaded by 2030, each with its fix"),
             ("Customer programs", n["priority"], f"priority homes to offer {n['units_per_home']} leased battery units"),
             ("Finance and regulatory", n["saving"], "net cost below Upgrade all")]
    for (team, big, sub), cy, o in zip(teams, rows, out_shapes):
        text(s, 10.35, cy - 0.55, 2.4, 1.1, [[(team, 14, True, DARK, None)], [(big, 20, True, GREEN, None)],
                                              [(sub, MIN_PT, False, INK, None)]], anchor=MSO_ANCHOR.MIDDLE, inset=0, space=0)
        arrow(s, 9.85, cy, 10.3, cy)
    caption(s, 5.9, ["The engine reads only what Avangrid already collects, so it needs no new hardware; until the meter to transformer",
                     f"map is joined, it groups real homes {n['homes_per']} to a transformer. Simulated on {n['transformers']} synthetic transformers of real homes."])
    s.notes_slide.notes_text_frame.text = (
        "Replaces v3 slide A18 'How the engine works' (the picture) with three editable slides: A18a top level, A18b mid level, A18c low level. "
        f"The engine is the ewu Python package and its bin/ewu command; it reads hourly meter data for {n['homes']} homes "
        f"({n['hours']} hours each) and hourly weather, and runs as one offline batch job, so no customer row leaves Avangrid. "
        "It writes transformer_actions.csv and capital_plan.csv (ewu/plan_output.py); the program list of real homes goes only to "
        "outputs/private. Headlines: the planner's list flags "
        f"{n['overloaded']} of transformers overloaded by 2030, {n['fixed']} of them fixed by batteries; the {n['priority']} priority homes "
        f"are the Part 3 ranking (slide 9), rerun on our load matrix by checks/teammate_rerun.py; the saving is net cost "
        f"{n['net_m']} vs {n['upall_m']} Upgrade all (Moderate 2030) and {n['net_h']} vs {n['upall_h']} (High 2030), from ewu/deck_money.py.")
    return s


def slide_mid(prs, a18, n):
    s = new_slide(prs, a18, "APPENDIX  |  A18b",
                  "How the engine works, mid level: seven steps turn meter data into a priced fix for every transformer, and every number is checked")
    stages = [
        ("Profile every home", ["GIVEN", "DERIVED"], ["analysis/", "ingest.py", "features.py", "classify.py", "segment.py"],
         f"{n['homes']} homes: technology and segment"),
        ("Build the network", ["SIMULATED"], ["ewu/", "feeders.py", "deck.py"],
         f"{n['transformers']} transformers of {n['homes_per']} real homes; rating = peak / {n['divisor']}"),
        ("Add 2030 load", ["SIMULATED", "ASSUMED"], ["ewu/", "deck.py"], "new EVs and heat pumps, Moderate and High"),
        ("Flag", ["SIMULATED"], ["ewu/", "deck.py"], f"overloaded: any hour above {n['limit']} of rating"),
        ("Place battery units", ["SIMULATED"], ["ewu/", "deck.py"], f"{n['units_min']} to {n['units_max']} units per transformer"),
        ("Upgrade", ["SIMULATED"], ["ewu/", "deck.py"], f"only where more than {n['units_max']} units"),
        ("Price both paths", ["ASSUMED"], ["ewu/", "deck_money.py"], "net cost vs Upgrade all, scaled to NYSEG"),
    ]
    w, gap, y0, h = 1.5, 0.27, 1.68, 3.2
    shapes = []
    for i, (label, tags, files, detail) in enumerate(stages):
        x = 0.6 + i * (w + gap)
        last = i == len(stages) - 1
        shapes.append(box(s, x, y0, w, h, fill=WHITE if last else LIGHT, line=BLUE_D if last else RULE, line_pt=1.5 if last else 0.75))
        text(s, x, y0 + 0.06, w, 0.58, [[(label, 14, True, BLUE_D if last else DARK, None)]], anchor=MSO_ANCHOR.TOP)
        py = y0 + 0.66
        for tag in tags:
            pill(s, x + 0.1, py, tag)
            py += 0.31
        text(s, x, y0 + 1.3, w, 1.1, [[(f, MIN_PT, False, INK, MONO)] for f in files], space=0)
        text(s, x, y0 + 2.42, w, 0.75, [[(detail, MIN_PT, False, INK, None)]], anchor=MSO_ANCHOR.TOP)
        if i:
            arrow(s, x - gap, y0 + h / 2, x, y0 + h / 2, a=shapes[i - 1], b=shapes[i])
    by, bh = 5.04, 0.92
    box(s, 0.6, by, 12.1, bh, fill=WHITE, line=GREEN, line_pt=1.5)
    text(s, 0.7, by, 1.75, bh, [[("Every number checked", 14, True, GREEN, None)]], anchor=MSO_ANCHOR.MIDDLE)
    checks = [("facts.json", "one source of numbers"), ("trace_numbers.py", "docs equal facts"),
              ("recompute_battery.py", "second code, same answer"), ("independent_check.py", "deck v3 equals facts"),
              ("make check", "runs every check")]
    cw = (12.6 - 2.45) / len(checks)
    for i, (f, what) in enumerate(checks):
        text(s, 2.45 + i * cw, by + 0.12, cw - 0.05, 0.7, [[(f, MIN_PT, False, INK, MONO)], [(what, MIN_PT, False, GREY, None)]],
             inset=0, space=1)
    lx, ly = 0.6, 6.12
    for tag, meaning in [("GIVEN", "in the hackathon data"), ("DERIVED", "computed from given data"),
                         ("SIMULATED", "modeled, not observed"), ("ASSUMED", "set by us, to confirm")]:
        lx += pill(s, lx, ly, tag) + 0.08
        text(s, lx, ly - 0.04, 2.2, 0.33, [[(meaning, MIN_PT, False, GREY, None)]], inset=0)
        lx += 0.075 * len(meaning) + 0.45
    caption(s, 6.5, ["Each step reads only the one before it, so a real transformer map, rating or price replaces one input and the chain reruns."])
    s.notes_slide.notes_text_frame.text = (
        "The seven steps run left to right in one batch (bin/ewu screen calls ewu/deck_screen.py). analysis/ingest.py, features.py, "
        "classify.py and segment.py profile every home from its meter data; ewu/feeders.py draws "
        f"{n['transformers']} synthetic transformers of {n['homes_per']} real homes and ewu/deck.py rates each at the smallest of "
        f"{n['size_lo']} to {n['size_hi']} at or above today's peak / {n['divisor']}. ewu/deck.py then adds 2030 EVs and heat pumps "
        f"(Moderate 2030: {n['ev_m']} EV, {n['hp_m']} heat pump; High: {n['ev_h']} and {n['hp_h']}), flags, sizes battery units or an "
        "upgrade, and ewu/deck_money.py prices both paths, scaled to NYSEG. Every step writes its numbers to facts/facts.json; "
        "checks/trace_numbers.py fails if a doc differs from it, checks/recompute_battery.py recomputes the battery result with "
        "separate code, deck/v3/independent_check.py checks deck v3's numbers against facts, and make check runs them with pytest.")
    return s


def slide_low(prs, a18, n):
    s = new_slide(prs, a18, "APPENDIX  |  A18c",
                  "How the engine works, low level: each transformer gets an hourly test, and its excess sets battery units or an upgrade")
    y0, h = 1.75, 3.0
    mid = y0 + h / 2
    b1 = box(s, 0.6, y0, 3.05, h, paras=[
        [("Hourly load", 14, True, DARK, None)],
        [(f"load(h) = its {n['homes_per']} homes' metered kW", MIN_PT, True, INK, None)],
        [("+ new EV charging: ", MIN_PT, True, INK, None),
         (f"{n['ev_kw']} for {n['ev_hours']}, {n['ev_week']}, start hour drawn from {n['ev_sessions']} measured sessions", MIN_PT, False, INK, None)],
        [("+ new heat pump: ", MIN_PT, True, INK, None),
         (f"hourly table, about {n['hp_kwh']} a year", MIN_PT, False, INK, None)],
        [(f"every hour h of the year, {n['hours']} in all", MIN_PT, False, GREY, None)]], inset=0.14, space=7)
    b2 = box(s, 4.0, y0, 2.55, h, paras=[
        [("Compare with limit", 14, True, DARK, None)],
        [(f"limit = {n['limit']} x rating", MIN_PT, True, INK, None)],
        [(f"rating = smallest of {n['size_lo']} to {n['size_hi']} at or above today's peak / {n['divisor']}", MIN_PT, False, INK, None)],
        [("overloaded if load(h) > limit in any hour", MIN_PT, True, INK, None)],
        [("never above: no action", MIN_PT, False, GREY, None)]], inset=0.14, space=7)
    b3 = box(s, 6.9, y0, 2.75, h, paras=[
        [("Size battery units", 14, True, DARK, None)],
        [("excess(h) = load(h) - limit", MIN_PT, True, INK, None)],
        [("each day, the larger of:", MIN_PT, False, INK, None)],
        [(f"round up (peak excess / {n['unit_kw']})", MIN_PT, False, INK, None)],
        [(f"round up (excess kWh / {n['unit_kwh']})", MIN_PT, False, INK, None)],
        [("units = the largest day", MIN_PT, True, INK, None)]], inset=0.14, space=7)
    oh = (h - 0.25) / 2
    b4 = box(s, 10.0, y0, 2.7, oh, fill=WHITE, line=GREEN, line_pt=1.5, paras=[
        [("Fixed by batteries", 14, True, GREEN, None)],
        [(f"{n['units_min']} to {n['units_max']} units", MIN_PT, True, INK, None)],
        [(f"{n['unit_usd']} a unit less lease ({n['lease_pv']}) and NYSERDA ({n['nyserda']}) = {n['net_unit']} net", MIN_PT, False, INK, None)]],
        inset=0.14, space=5)
    b5 = box(s, 10.0, y0 + oh + 0.25, 2.7, oh, fill=WHITE, line=ORANGE_D, line_pt=1.5, paras=[
        [("Upgrade", 14, True, ORANGE_D, None)],
        [(f"more than {n['units_max']} units", MIN_PT, True, INK, None)],
        [(f"{n['upgrade']}, counted for {n['years']} of its {n['life']} = {n['counted']}", MIN_PT, False, INK, None)]],
        inset=0.14, space=5)
    arrow(s, 3.65, mid, 4.0, mid, a=b1, b=b2)
    arrow(s, 6.55, mid, 6.9, mid, a=b2, b=b3)
    for target in (b4, b5):
        cy = Emu(target.top + target.height // 2).inches
        arrow(s, 9.65, cy, 10.0, cy, b=target)
    caption(s, y0 + h + 0.25, [f"Both paths are priced over the same {n['years']} years at {n['rate']}, so a unit and an upgrade compare directly; a real rating",
                      "or loading limit from Avangrid drops into the same test. Simulated on synthetic transformers of real homes; no single home shown."])
    s.notes_slide.notes_text_frame.text = (
        "One transformer, as ewu/deck.py computes it for all of them at once with numpy. ev_loading() gives each new EV home a "
        f"{n['ev_kw']} charge for {n['ev_hours']} on {cfg('profiles.deck.ev_day_share'):.0%} of days, its start hour drawn from the "
        "measured start-hour table (data/processed/ev_start_pmf.npy); hp_increment() adds the hourly heat pump table "
        "(data/processed/hp_increment.npy); both files are checked by sha256 against config/ewu.yaml. run_deck() flags any hour above "
        f"{n['limit']} of the rating from standard_rating(), and battery_units() takes, for each day, the larger of the rounded-up peak "
        f"excess over {n['unit_kw']} and excess energy over {n['unit_kwh']}, then the largest day, at least {n['units_min']}; above "
        f"{n['units_max']} the transformer is an upgrade. ewu/deck_money.py nets the lease ({n['lease_pv']} present value) and NYSERDA "
        f"({n['nyserda']}) from {n['unit_usd']} per unit and counts a {n['upgrade']} upgrade for {n['years']} of its {n['life']} "
        f"({n['counted']}), {n['years']} years at {n['rate']}; scaling to NYSEG is x {n['nyseg']} / ({n['homes_per']} x {n['transformers']}).")
    return s


# ---------------------------------------------------------------- assemble and check
def drop_original_slides(prs, keep):
    lst = prs.slides._sldIdLst
    for sid in list(lst):
        if sid.id not in keep:
            rid = sid.rId
            lst.remove(sid)
            prs.part.drop_rel(rid)
    root = prs.part._element
    for sec in root.iter(f"{{{P14}}}sectionLst"):
        for section in list(sec):
            sec.remove(section)
        section = etree.SubElement(sec, f"{{{P14}}}section")
        section.set("name", "Appendix"), section.set("id", "{5E1A18A0-0000-4000-8000-0000000A18AB}")
        ids = etree.SubElement(section, f"{{{P14}}}sldIdLst")
        for sid in lst:
            etree.SubElement(ids, f"{{{P14}}}sldId").set("id", str(sid.id))


def self_check(prs):
    problems = []
    W, H = prs.slide_width, prs.slide_height
    terms, allow = read_terms(TERMS.read_text())
    if len(prs.slides) != 3:
        problems.append(f"{len(prs.slides)} slides, not 3")
    for i, slide in enumerate(prs.slides, 1):
        words = []
        for sh in slide.shapes:
            if sh.left < 0 or sh.top < 0 or sh.left + sh.width > W or sh.top + sh.height > H:
                problems.append(f"slide {i}: {sh.name} off the slide")
            if not sh.has_text_frame:
                continue
            words.append(sh.text_frame.text)
            eyebrow = sh.text_frame.text.startswith("APPENDIX")
            for p in sh.text_frame.paragraphs:
                for r in p.runs:
                    if r.text.strip() and r.font.size is not None and r.font.size.pt < MIN_PT and not eyebrow:
                        problems.append(f"slide {i}: '{r.text[:30]}' at {r.font.size.pt} pt")
        words.append(slide.notes_slide.notes_text_frame.text)
        blob = "\n".join(words)
        if "—" in blob or "–" in blob:
            problems.append(f"slide {i}: em or en dash")
        prose = re.sub(r"\S+\.(py|csv|json|npy|yaml)\b|\bbin/ewu\b|\b\w+\(\)", "", blob)
        problems += find_synonyms(f"engine appendix slide {i}", prose, terms, allow)
    return problems


def build():
    n = numbers()
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "template_copy.pptx"
        shutil.copy2(V3, src)
        prs = Presentation(str(src))
        matched = check_numbers(n, deck_text(prs))
        a18 = next(s for s in prs.slides for sh in s.shapes
                   if sh.has_text_frame and sh.text_frame.text.strip() == "APPENDIX  |  A18")
        new = [slide_top(prs, a18, n), slide_mid(prs, a18, n), slide_low(prs, a18, n)]
        drop_original_slides(prs, {s.slide_id for s in new})
        problems = self_check(prs)
        if problems:
            sys.exit("self-check failed:\n  " + "\n  ".join(problems))
        OUT.parent.mkdir(parents=True, exist_ok=True)
        prs.save(OUT)
    print(f"wrote {OUT.relative_to(ROOT)}: 3 slides, self-check 0 problems")
    for k, v in matched.items():
        print(f"  v3 states: {v}")
    return n


if __name__ == "__main__":
    build()
