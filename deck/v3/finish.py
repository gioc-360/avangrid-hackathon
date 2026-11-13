"""Finish deck v3 after apply.py: wording, "simulated" labels, A17 on our tool, new A18 and A19, index, slide 11 notes.

What: reads the deck apply.py wrote (numbers already from facts), writes a new file:
        A13 footer   reworded for the engine's money basis (gross before offsets now costs more than upgrading)
        2, 12, 15    one small "simulated on 3,000 synthetic transformers of real homes" line in the slide's caption style
        A17          our engine (bin/ewu) instead of the teammate's run.py, Network view screenshot, simulated caption
        A18, A19     How the engine works, Tech specs (outputs/deck/architecture.png, tech_specs.png), same layout
        16           appendix index lists A18 and A19
        11 notes     the money basis used everywhere in the deck
Why:  Gio, 2026-11-13: "just use our calculations"; labels keep the simulated network honest on the headline slides.
How:  every new shape is a copy of an existing shape on the same slide (style kept), moved and retexted.
    .venv/bin/python -I deck/v3/finish.py outputs/deck/v3/applied.pptx outputs/deck/v3/v3_out.pptx
"""
import copy
import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Emu, Pt

ROOT = Path(__file__).resolve().parents[2]
LABEL = "Simulated on 3,000 synthetic transformers of real homes"


def shape(slide, name):
    found = [s for s in slide.shapes if s.name == name]
    if len(found) != 1:
        sys.exit(f"slide {slide.slide_id}: expected one shape named {name!r}, found {len(found)}")
    return found[0]


def retext(sh, text, expect=None):
    """Replace a one-paragraph text box's text, keeping its first run's format."""
    tf = sh.text_frame
    if expect is not None and expect not in tf.text:
        sys.exit(f"{sh.name}: expected {expect!r} in {tf.text!r}")
    p = tf.paragraphs[0]
    for extra in tf.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)
    runs = p.runs
    runs[0].text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)


def clone(slide, src, x, y, w, h, text, size=None, color=None):
    el = copy.deepcopy(src._element)
    slide.shapes._spTree.append(el)
    new = slide.shapes[-1]
    new.left, new.top, new.width, new.height = Emu(x), Emu(y), Emu(w), Emu(h)
    retext(new, text)
    run = new.text_frame.paragraphs[0].runs[0]
    if size:
        run.font.size = Pt(size)
    if color:
        from pptx.dml.color import RGBColor
        run.font.color.rgb = RGBColor.from_string(color)
    return new


def picture(slide, path, x, y, w, h, crop_top=0.0, crop_bottom=0.0):
    pic = slide.shapes.add_picture(str(path), Emu(x), Emu(y), Emu(w), Emu(h))
    pic.crop_top, pic.crop_bottom = crop_top, crop_bottom
    return pic


def fit(path, crop_top, crop_bottom, box_w, box_h):
    from PIL import Image
    W, H = Image.open(path).size
    aspect = W / (H * (1 - crop_top - crop_bottom))
    w, h = box_w, int(box_w / aspect)
    if h > box_h:
        h, w = box_h, int(box_h * aspect)
    return w, h


def main(src, out):
    prs = Presentation(src)
    S = prs.slides
    s2, s11, s12, s15, s16, s29, s33 = (S[i - 1] for i in (2, 11, 12, 15, 16, 29, 33))

    # A13 footer: engine basis (upgrade counted 15 of its 40 years); claims checked by apply.py
    retext(shape(s29, "Text 2"),
           "Costs across NYSEG, present value over 15 years at 7%, an upgrade counted for 15 of its 40 years ($15,000 "
           "counts as $10,248). Net cost subtracts the customer lease ($330 per unit a year) and NYSERDA ($2,016 per "
           "unit); before those offsets the battery path costs more than upgrading in every row.",
           expect="Before those offsets")

    # slide 11 notes: the one money basis
    notes = s11.notes_slide.notes_text_frame
    notes.text = notes.text + (
        " Money basis, the same on every slide (2, 11, 12, 13, 15, A13): our engine's present value over 15 years at "
        "7% (ewu/deck_money.py), batteries net of the customer lease and NYSERDA, and an upgrade counted for the 15 of "
        "its 40 years the program runs, so a $15,000 upgrade counts as $10,248. The $3,000 net cost per transformer "
        "fixed is 1.5 to 1.9 units at $1,978 each; the $15,000 is the upgrade's sticker price.")

    # "simulated" labels in each slide's caption style
    cap2 = shape(s2, "Text 5")
    clone(s2, cap2, 822960, 5166360, 3017520, 457200, LABEL, size=11)
    clone(s2, cap2, 8321040, 5166360, 3017520, 457200, "Transformer figures: " + LABEL[0].lower() + LABEL[1:], size=11)
    clone(s12, shape(s12, "Text 17"), 548640, 5760720, 3200400, 548640, LABEL, size=11, color="5F6B66")
    clone(s15, shape(s15, "Text 3"), 685800, 4846320, 10835640, 365760,
          "Overload and cost results " + LABEL[0].lower() + LABEL[1:], size=12)

    # A17: our tool
    retext(shape(s33, "Text 1"), "Analytical tool: bin/ewu reads hourly meter data and weather, simulates 2030 load on "
                                 "transformers and writes action lists", expect="Analytical tool")
    retext(shape(s33, "Text 5"), "Hourly AMI meter data (33,757 homes x 8,760 hours), weather, label lists; settings "
                                 "in config/ewu.yaml", expect="config.yaml")
    retext(shape(s33, "Text 9"), "bin/ewu screen, plan and demo add 2030 EVs and heat pumps to 3,000 simulated "
                                 "transformers of 8 real homes and size the fix", expect="run.py")
    retext(shape(s33, "Text 13"), "transformer_actions.csv (flag, batteries or upgrade), capital_plan.csv, an offline "
                                  "viewer page", expect="customer_inventory.csv")
    retext(shape(s33, "Text 17"), "README, tests, facts/facts.json as the one source of every number; no customer data "
                                  "committed", expect="README.md")
    rect = shape(s33, "Shape 18")
    shot = ROOT / "outputs/deck/v3/network_flag.png"
    pad = 91440
    w, h = fit(shot, 0, 0, rect.width - 2 * pad, rect.height - 2 * pad - 548640)
    picture(s33, shot, rect.left + (rect.width - w) // 2, rect.top + pad, w, h)
    cap = shape(s33, "Text 19")
    retext(cap, "Simulated: our tool's Network view, moderate 2030, deck setup. Transformers are synthetic groups of 8 "
                "real homes; the data has no meter to transformer map.", expect="Tool screenshot")
    cap.left, cap.top, cap.width, cap.height = rect.left + pad, rect.top + pad + h + 45720, rect.width - 2 * pad, Emu(502920)
    run = cap.text_frame.paragraphs[0].runs[0]
    run.font.size, run.font.bold = Pt(11), False
    cap.text_frame.word_wrap = True

    # A18, A19 after A17, same layout and header/title/number shapes as A17
    header, title, num = shape(s33, "Text 0"), shape(s33, "Text 1"), shape(s33, "Slide Number Placeholder 0")
    for code, head, img, crop in (
            ("A18", "How the engine works: one offline engine turns meter data into action lists and checks every number",
             ROOT / "outputs/deck/architecture.png", (0.135, 0.0)),
            ("A19", "Tech specs: the engine runs on one laptop, offline, and every spec below was measured",
             ROOT / "outputs/deck/tech_specs.png", (0.135, 0.07))):
        s = prs.slides.add_slide(s33.slide_layout)
        for ph in list(s.placeholders):
            ph._element.getparent().remove(ph._element)
        for src_shape in (header, title, num):
            s.shapes._spTree.append(copy.deepcopy(src_shape._element))
        retext(shape(s, "Text 0"), f"APPENDIX  |  {code}")
        retext(shape(s, "Text 1"), head)
        top, bottom = 1463040, 6309360
        w, h = fit(img, crop[0], crop[1], 11094720, bottom - top)
        picture(s, img, (prs.slide_width - w) // 2, top, w, h, *crop)

    # appendix index
    a17 = shape(s16, "Text 18")
    step = 310896
    clone(s16, a17, a17.left, a17.top + step, a17.width, a17.height, "A18 How the engine works")
    clone(s16, a17, a17.left, a17.top + 2 * step, a17.width, a17.height, "A19 Tech specs")

    out = Path(out)
    if out.exists():
        sys.exit(f"refusing to overwrite {out}")
    prs.save(out)
    print("wrote", out, "slides:", len(prs.slides))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
