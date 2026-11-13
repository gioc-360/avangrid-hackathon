"""Engine slides: a 16:9 two-slide pptx for the teammate, how the engine works and its tech specs.

What: build_deck() writes outputs/deck/EWU_engine_slides.pptx: slide 1 "How the engine works" carries a
      one-line takeaway and outputs/deck/architecture.png (its own title cropped off, since the slide says
      it); slide 2 "Tech specs" carries a one-line takeaway and the measured specs as a two-column table.
Why:  the teammate builds the deck in PowerPoint, so the engine needs slides that drop in as they are, with
      the same numbers as docs/TECH_SPECS.md and the figures, read from the same facts.
How:  python-pptx on a blank 13.333 x 7.5 in layout; table rows come from outputs/deck/spec_rows.json, which
      deck/engine_figures.py writes from deck/engine_figures.spec_rows(), so a rerun of deck/engine_specs.py
      and deck/engine_figures.py updates both slides. Needs only python-pptx: `python3 -I deck/engine_slides.py`.
"""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR
from pptx.util import Emu, Inches, Pt

OUT = ROOT / "outputs" / "deck"

INK, GREY, RULE = RGBColor(0x1B, 0x1B, 0x1B), RGBColor(0x55, 0x55, 0x55), RGBColor(0x9A, 0x9A, 0x9A)
FONT = "Arial"
TITLE_CROP_PX = 150
ROW_IN = 0.44


def fact(key, fmt="{:,}"):
    return fmt.format(json.loads((ROOT / "facts" / "facts.json").read_text())[key]["value"])


def spec_rows():
    """The rows deck/engine_figures.py wrote next to its PNGs, so this file needs only python-pptx."""
    return [tuple(row) for row in json.loads((OUT / "spec_rows.json").read_text())]


def add_text(slide, words, left, top, width, height, size, bold=False, color=INK):
    frame = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height)).text_frame
    frame.word_wrap = True
    run = frame.paragraphs[0].add_run()
    run.text = words
    run.font.size, run.font.bold, run.font.name, run.font.color.rgb = Pt(size), bold, FONT, color
    return frame


def heading(slide, kicker, takeaway):
    add_text(slide, kicker, 0.5, 0.3, 12.3, 0.4, 16, True, GREY)
    add_text(slide, takeaway, 0.5, 0.68, 12.3, 0.6, 26, True)


def engine_slide(deck):
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    heading(slide, "How the engine works", "Meter data in, action lists out: one offline run, every number checked")
    picture = slide.shapes.add_picture(str(OUT / "architecture.png"), Inches(0.5), Inches(1.45), width=Inches(12.3))
    picture.crop_top = TITLE_CROP_PX / 1080
    picture.height = Emu(int(Inches(12.3) * (1080 - TITLE_CROP_PX) / 1920))
    picture.name = "EWU engine architecture"
    picture._element.nvPicPr.cNvPr.set("descr", "EWU engine: read inputs, profile every home, add 2030 "
                                               "load, run the ladder, ship action lists; a trust layer checks every number")


def specs_slide(deck):
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    heading(slide, "Tech specs", f"Screens {fact('ewu.screen.moderate.random.margin_115.transformers')} transformers in "
                                 f"{fact('specs.screen.measured_seconds', '{}')} s on one "
                                 "laptop, fully offline")
    rows = spec_rows()
    shape = slide.shapes.add_table(len(rows), 2, Inches(0.5), Inches(1.45), Inches(12.3), Inches(ROW_IN * len(rows)))
    table = shape.table
    table.columns[0].width, table.columns[1].width = Inches(2.6), Inches(9.7)
    table.first_row = False
    for i, (spec, value) in enumerate(rows):
        table.rows[i].height = Inches(ROW_IN)
        for j, words in enumerate((spec, value)):
            cell = table.cell(i, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF) if i % 2 else RGBColor(0xF2, 0xF2, 0xF2)
            cell.margin_left = cell.margin_right = Inches(0.12)
            cell.text = ""
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            run = cell.text_frame.paragraphs[0].add_run()
            run.text = words
            run.font.size, run.font.bold, run.font.name, run.font.color.rgb = Pt(13), j == 0, FONT, INK
    add_text(slide, "Measured by deck/engine_specs.py; numbers from facts/facts.json. No customer data on this slide.",
             0.5, 7.02, 12.3, 0.35, 11, False, GREY)


def build_deck():
    deck = Presentation()
    deck.slide_width, deck.slide_height = Inches(13.333), Inches(7.5)
    engine_slide(deck)
    specs_slide(deck)
    path = OUT / "EWU_engine_slides.pptx"
    deck.save(path)
    return path


if __name__ == "__main__":
    print(f"wrote {build_deck().relative_to(ROOT)}")
