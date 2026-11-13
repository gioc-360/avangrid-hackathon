"""Future concept slide: a mockup of the EWU app on real streets, and one new slide in deck v3's template.

What: concept_svg() draws the Electrify Without Upgrade app as it would look once Avangrid loads its
      meter-to-transformer map and GIS: the app's side panel with a Layers control (the future opportunities of
      deck v3 slide 14 as toggles), and a map canvas of FICTIONAL streets with transformer markers in the app's
      shapes and words. render_png() screenshots it with headless Chrome at 2x. build_pptx() copies deck v3,
      keeps only slide 14 to inherit its layout, and rebuilds it as slide 14b: eyebrow, takeaway title, the
      mockup, a three-step strip (Today, Add, Then), a caption and speaker notes. --render renders the slide
      with PowerPoint through deck/v3/render_ppt.py on a copy with a neutral name; --deliver copies the pptx
      to OneDrive deck-v3 and ~/Downloads as new files (letter suffix if a name exists).
Why:  slide 14 lists the future opportunities as text. Gio asked for a picture of that future. Our data has no
      locations, so every street and marker here is invented and the picture says CONCEPT three times: a tag
      on the map, the slide caption, and the notes. No number on the mockup can be read as a result.
How:  plain SVG strings in the app's palette (ewu/demo_template.html :root tokens) and its marker glyphs
      (GLYPH in the same file: dot within limit, triangle overloaded, battery fixed by batteries, square
      Upgrade). Marker states come from a seeded generator, not from any run. Text 22 px or more on a
      1280 x 720 canvas, which lands at about 10 pt or more on the slide.
    .venv/bin/python deck/future_slide/build.py [--render] [--deliver]
"""
import copy
import os
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "outputs" / "deck" / "future_slide"
V3 = Path("/Users/giocaballero/Downloads/D4G Cornell 2_Final Submission_v3.pptx")
ONEDRIVE = Path("/Users/giocaballero/Library/CloudStorage/OneDrive-CornellUniversity/Avangrid Hackathon/deck-v3")
DOWNLOADS = Path.home() / "Downloads"
NAME = "EWU_future_concept_slide.pptx"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# app tokens (ewu/demo_template.html :root, light theme) and deck v3 slide 14 colours
BG, PANEL, CARD, INK, MUTED, FAINT, LINE = "#f7faf8", "#eef5f0", "#ffffff", "#1d2b24", "#4a5651", "#5f6b66", "#d5ded8"
NODE, PROTECT, UPGRADE, ACCENT, BLUE = "#a0aaa5", "#0b3b30", "#c46a00", "#008c38", "#0089bd"
SANS = "Helvetica Neue, Helvetica, Arial, sans-serif"
W, H = 1280, 720

# ---------- the concept mockup


def text(x, y, words, size=24, weight=400, fill=INK, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}">{escape(words)}</text>')


def glyph(look, x, y, scale=1.0):
    """The app's marker shapes (GLYPH in ewu/demo_template.html), drawn at x, y."""
    shape = {
        "within": f'<circle r="3.4" fill="{NODE}"/>',
        "over": f'<path d="M0,-6.2L5.6,4.2L-5.6,4.2Z" fill="{UPGRADE}"/>',
        "protected": f'<path d="M-6,-3.8h10.4v7.6h-10.4ZM4.4,-1.8h2v3.6h-2Z" fill="{PROTECT}"/>',
        "upgrade": f'<rect x="-6.6" y="-6.6" width="13.2" height="13.2" fill="{UPGRADE}" stroke="{INK}" stroke-width="2.4"/>',
    }[look]
    return f'<g transform="translate({x:.1f},{y:.1f}) scale({scale})">{shape}</g>'


def side_panel():
    parts = [f'<rect x="0" y="0" width="290" height="{H}" fill="{PANEL}"/>',
             f'<line x1="290" y1="0" x2="290" y2="{H}" stroke="{LINE}" stroke-width="1.5"/>',
             text(26, 48, "Electrify Without", 24, 700), text(26, 78, "Upgrade", 24, 700)]
    y = 128
    for name, current in (("Summary", False), ("Map", True), ("Network", False), ("Money", False)):
        if current:
            parts.append(f'<rect x="16" y="{y - 30}" width="258" height="44" rx="7" fill="{CARD}" '
                         f'style="filter:drop-shadow(0 2px 4px rgba(29,43,36,.10))"/>')
            parts.append(f'<rect x="16" y="{y - 30}" width="4" height="44" fill="{ACCENT}"/>')
        parts.append(text(34, y, name, 24, 700 if current else 500))
        y += 46
    parts.append(f'<line x1="26" y1="{y - 12}" x2="264" y2="{y - 12}" stroke="{LINE}" stroke-width="1.5"/>')
    y += 28
    parts.append(text(26, y, "Layers", 24, 700))
    y += 4
    for name, on in (("Overloads 2030", True), ("Battery placement", True), ("Heat pump targets", False),
                     ("Load forecast", False), ("Rate segments", False)):
        y += 50
        fill, knob = (ACCENT, 239) if on else ("#c9d3ce", 219)
        parts.append(f'<rect x="26" y="{y - 22}" width="46" height="26" rx="13" fill="{fill}"/>')
        parts.append(f'<circle cx="{knob - 180}" cy="{y - 9}" r="10" fill="#ffffff"/>')
        parts.append(text(84, y, name, 22, 600 if on else 400, INK if on else MUTED))
    return parts


def streets():
    """A fictional street plan in map-card coordinates (930 x 520): a few straight streets, one avenue."""
    h = [(0, 92, 930, 92), (0, 262, 930, 262), (0, 432, 930, 432)]
    v = [(150, 0, 150, 520), (400, 0, 400, 520), (640, 0, 640, 520), (850, 0, 850, 262)]
    avenue = [(150, 432, 400, 262), (640, 262, 850, 432)]
    return h + v + avenue


def on_street_points(segs, step=58, clear=30):
    """Transformer spots along each street, kept clear of the crossings."""
    crossings = []
    for a in segs:
        for b in segs:
            if a is b:
                continue
            for px, py in ((a[0], a[1]), (a[2], a[3])):
                crossings.append((px, py))
    for x, y in ((150, 92), (400, 92), (640, 92), (850, 92), (150, 262), (400, 262), (640, 262), (850, 262),
                 (150, 432), (400, 432), (640, 432)):
        crossings.append((x, y))
    pts = []
    for x1, y1, x2, y2 in segs:
        length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        n = int(length // step)
        for i in range(1, n + 1):
            t = (i * step - step / 2) / length
            if t >= 1:
                break
            px, py = x1 + t * (x2 - x1), y1 + t * (y2 - y1)
            if any(abs(px - cx) < clear and abs(py - cy) < clear for cx, cy in crossings):
                continue
            if not (14 < px < 916 and 14 < py < 506):
                continue
            pts.append((px, py))
    return pts


def map_card(x0=320, y0=186, w=930, h=520):
    segs = streets()
    parts = [f'<g transform="translate({x0},{y0})">',
             f'<defs><clipPath id="mapclip"><rect width="{w}" height="{h}" rx="12"/></clipPath></defs>',
             f'<rect width="{w}" height="{h}" rx="12" fill="#f1f5f2" stroke="{LINE}" stroke-width="1.5"/>',
             '<g clip-path="url(#mapclip)">',
             # a park block, so the plan reads as a town and not a grid diagram
             f'<rect x="412" y="104" width="216" height="146" rx="6" fill="#e2efe5"/>']
    for x1, y1, x2, y2 in segs:   # street casing, then street
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#c9d3ce" stroke-width="22" stroke-linecap="square"/>')
    for x1, y1, x2, y2 in segs:
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#ffffff" stroke-width="18" stroke-linecap="square"/>')
    # the feeder: substation in the left block, out along the middle street and up one side street
    parts += [f'<polyline points="70,214 70,262 640,262 640,92 850,92" fill="none" stroke="{INK}" stroke-width="3.5"/>',
              f'<rect x="26" y="168" width="88" height="46" rx="7" fill="{CARD}" stroke="{INK}" stroke-width="2"/>',
              f'<circle cx="62" cy="191" r="10" fill="none" stroke="{INK}" stroke-width="2"/>',
              f'<circle cx="78" cy="191" r="10" fill="none" stroke="{INK}" stroke-width="2"/>',
              f'<rect x="232" y="276" width="112" height="32" rx="5" fill="{CARD}" opacity=".92"/>',
              text(240, 300, "Feeder A", 22, 700)]
    rng = random.Random(14)
    cx, cy, cw, ch = 568, 296, 348, 204       # the detail card; no marker hides under it
    pts = [(px, py) for px, py in on_street_points(segs)
           if not (cx - 16 < px < cx + cw + 16 and cy - 16 < py < cy + ch + 16)]
    looks = []
    for _ in pts:
        r = rng.random()
        looks.append("within" if r < 0.66 else "over" if r < 0.80 else "protected" if r < 0.96 else "upgrade")
    # one marker the detail card points to, fixed by batteries
    pick = min(range(len(pts)), key=lambda i: (pts[i][0] - 520) ** 2 + (pts[i][1] - 262) ** 2)
    looks[pick] = "protected"
    upgrades = [i for i, look in enumerate(looks) if look == "upgrade"]
    if not upgrades:
        looks[len(looks) // 3] = "upgrade"
    for (px, py), look in zip(pts, looks):
        parts.append(glyph(look, px, py, 2.0 if look != "within" else 1.9))
    sx, sy = pts[pick]
    parts.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="21" fill="none" stroke="{BLUE}" stroke-width="3.5"/>')
    # detail card: words only
    parts += [f'<line x1="{sx:.1f}" y1="{sy + 21:.1f}" x2="{cx + 40}" y2="{cy}" stroke="{BLUE}" stroke-width="3"/>',
              f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="10" fill="{CARD}" stroke="{BLUE}" stroke-width="2.5" '
              f'style="filter:drop-shadow(0 4px 10px rgba(29,43,36,.18))"/>',
              text(cx + 20, cy + 36, "Example transformer", 22, 600, MUTED),
              glyph("protected", cx + 34, cy + 72, 2.2),
              text(cx + 58, cy + 81, "Fixed by batteries", 26, 700),
              text(cx + 20, cy + 122, "Battery units at priority homes", 22),
              text(cx + 20, cy + 156, "Overloaded on winter nights", 22),
              text(cx + 20, cy + 182, "before batteries", 22)]
    # the CONCEPT tag, top left, over everything
    parts += [f'<rect x="14" y="14" width="742" height="48" rx="8" fill="{INK}"/>',
              f'<text x="30" y="47" font-family="{SANS}" font-size="24" fill="#ffffff">'
              '<tspan font-weight="800">CONCEPT:</tspan> illustrative streets, not real locations or data</text>']
    parts += ['</g>', '</g>']
    return parts


def legend_row(x=320, y=128):
    parts, cx = [], x
    for look, word in (("within", "Within limit"), ("over", "Overloaded"), ("protected", "Fixed by batteries"),
                       ("upgrade", "Upgrade")):
        width = 50 + int(len(word) * 12.2)
        parts.append(f'<rect x="{cx}" y="{y}" width="{width}" height="42" rx="7" fill="{CARD}" stroke="{LINE}" stroke-width="1.5"/>')
        parts.append(glyph(look, cx + 22, y + 21, 1.7 if look != "within" else 2.0))
        parts.append(text(cx + 40, y + 29, word, 22))
        cx += width + 12
    return parts


def concept_svg():
    parts = [f'<rect width="{W}" height="{H}" fill="{BG}"/>'] + side_panel()
    parts += [text(320, 58, "Map", 26, 700),
              f'<rect x="384" y="30" width="300" height="38" rx="19" fill="{CARD}" stroke="{INK}" stroke-width="1.5" stroke-dasharray="4 3"/>',
              text(534, 57, "Transformer map + GIS", 22, 600, anchor="middle"),
              text(320, 108, "Overloaded transformers, street by street", 32, 700)]
    parts += legend_row() + map_card()
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            + "".join(parts) + "</svg>")


def render_png(svg_path, png_path):
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run([CHROME, "--headless=new", f"--user-data-dir={profile}", "--hide-scrollbars",
                        f"--window-size={W},{H}", "--force-device-scale-factor=2", "--default-background-color=ffffffff",
                        f"--screenshot={png_path}", svg_path.as_uri()], check=True, capture_output=True, timeout=120)


# ---------- the slide

EMU_IN = 914400
TITLE = ("With Avangrid's transformer map, the same engine becomes a map of real streets, "
         "with each future use as a layer")
STEPS = [("Today", "Synthetic network from real homes", "008C38"),
         ("Add", "Meter-to-transformer map and GIS", "00ABE8"),
         ("Then", "Real streets, plus forecasting, heat pump targeting and rate design as layers", "F7921D")]
CAPTION = "Concept mockup. Streets and markers are illustrative."
NOTES = ("What is real today is the engine and its synthetic network: every transformer is built from real homes' "
         "meter data, but the data has no locations, so the network has no streets. Avangrid's meter-to-transformer "
         "map and GIS would put the same results on real streets and turn the stress test into a list of real "
         "transformers. Forecasting, heat pump targeting and rate design then become layers on that one map; this "
         "picture is a concept, and its streets and markers are illustrative.")


def keep_only(prs, index):
    sld_ids = prs.slides._sldIdLst
    for i, sld in reversed(list(enumerate(list(sld_ids)))):
        if i != index:
            prs.part.drop_rel(sld.get(qn("r:id")))
            sld_ids.remove(sld)


def textbox(slide, x, y, w, h, runs, size, color="1D2B24", bold=False, align=None, anchor=MSO_ANCHOR.TOP):
    """runs: list of paragraphs, each a list of (text, bold) pairs."""
    tb = slide.shapes.add_textbox(Emu(x), Emu(y), Emu(w), Emu(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    for i, para in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        if align:
            p.alignment = align
        for words, b in para:
            r = p.add_run()
            r.text = words
            r.font.size = Pt(size)
            r.font.bold = bold or b
            r.font.color.rgb = RGBColor.from_string(color)
    return tb


def solid(shape, hexcolor, line=None):
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor.from_string(hexcolor)
    if line:
        shape.line.color.rgb = RGBColor.from_string(line)
        shape.line.width = Pt(0.75)
    else:
        shape.line.fill.background()
    shape.shadow.inherit = False


def build_pptx(png, out):
    work = OUT / "_v3_copy.pptx"
    shutil.copyfile(V3, work)          # read v3 through a copy; v3 itself is never opened for writing
    prs = Presentation(str(work))
    keep_only(prs, 13)
    slide = prs.slides[0]
    keep = {"Text 0", "Text 1", "Slide Number Placeholder 0"}
    for shape in list(slide.shapes):
        if shape.name not in keep:
            shape._element.getparent().remove(shape._element)
    shapes = {s.name: s for s in slide.shapes}
    shapes["Text 1"].text_frame.paragraphs[0].runs[0].text = TITLE
    for r in shapes["Text 1"].text_frame.paragraphs[0].runs[1:]:
        r._r.getparent().remove(r._r)
    # slide number: the slidenum field would print 1 in a one-slide file, so it reads 14b as plain text
    num = shapes["Slide Number Placeholder 0"].text_frame.paragraphs[0]
    for fld in num._p.findall(qn("a:fld")):
        rpr = fld.find(qn("a:rPr"))
        r = etree.SubElement(num._p, qn("a:r"))
        if rpr is not None:
            r.append(copy.deepcopy(rpr))
        t = etree.SubElement(r, qn("a:t"))
        t.text = "14b"
        fld.addprevious(r)
        num._p.remove(fld)

    left, top = int(0.6 * EMU_IN), int(1.75 * EMU_IN)
    img_w = int(8.5 * EMU_IN)
    img_h = int(img_w * H / W)
    pic = slide.shapes.add_picture(str(png), Emu(left), Emu(top), Emu(img_w), Emu(img_h))
    pic.line.color.rgb = RGBColor.from_string("D5DED8")
    pic.line.width = Pt(0.75)
    pic.name = "Concept mockup"
    textbox(slide, left, top + img_h + int(0.07 * EMU_IN), img_w, int(0.28 * EMU_IN),
            [[(CAPTION, False)]], 12, "5F6B66")

    # three-step strip beside the mockup, in slide 14's card style
    sx = left + img_w + int(0.25 * EMU_IN)
    sw = int(12.65 * EMU_IN) - sx
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Emu(sx), Emu(top), Emu(sw), Emu(img_h))
    card.adjustments[0] = 0.03
    solid(card, "EEF5F0")
    card.name = "Steps card"
    pad = int(0.22 * EMU_IN)
    circle = int(0.5 * EMU_IN)
    y = top + int(0.3 * EMU_IN)
    gap = (img_h - int(0.6 * EMU_IN)) // 3
    for i, (label, body, colour) in enumerate(STEPS):
        c = slide.shapes.add_shape(MSO_SHAPE.OVAL, Emu(sx + pad), Emu(y), Emu(circle), Emu(circle))
        solid(c, colour)
        c.name = f"Step {i + 1} circle"
        tf = c.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = str(i + 1)
        r.font.size, r.font.bold = Pt(16), True
        r.font.color.rgb = RGBColor.from_string("FFFFFF")
        tx = sx + pad + circle + int(0.16 * EMU_IN)
        tw = sx + sw - pad - tx
        textbox(slide, tx, y + int(0.04 * EMU_IN), tw, int(0.32 * EMU_IN), [[(label, True)]], 16, "0B3B30")
        textbox(slide, tx, y + int(0.4 * EMU_IN), tw, gap - int(0.5 * EMU_IN), [[(body, False)]], 15)
        if i < len(STEPS) - 1:   # a down arrow under the circle to the next step
            ay = y + circle + int(0.12 * EMU_IN)
            ah = gap - circle - int(0.24 * EMU_IN)
            a = slide.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Emu(sx + pad + circle // 2 - int(0.09 * EMU_IN)),
                                       Emu(ay), Emu(int(0.18 * EMU_IN)), Emu(ah))
            solid(a, "A0AAA5")
            a.name = f"Step arrow {i + 1}"
        y += gap

    notes = slide.notes_slide.notes_text_frame
    notes.text = NOTES
    prs.save(str(out))
    work.unlink()


def free_name(folder, name):
    """name in folder, or name with a letter suffix (b, c, ...) if it exists: never overwrite."""
    path = folder / name
    stem, ext = os.path.splitext(name)
    for letter in "bcdefghijklmnopqrstuvwxyz":
        if not path.exists():
            return path
        path = folder / f"{stem}_{letter}{ext}"
    sys.exit(f"no free name for {name} in {folder}")


def render_slide(pptx):
    count = subprocess.run(["osascript", "-e", 'tell application "Microsoft PowerPoint" to count presentations'],
                           capture_output=True, text=True).stdout.strip()
    print("PowerPoint presentations open before render:", count or "PowerPoint not running")
    copy_path = OUT / "render" / "fs_render_copy.pptx"   # neutral name: no deck name in it
    copy_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(pptx, copy_path)
    subprocess.run([sys.executable, str(ROOT / "deck" / "v3" / "render_ppt.py"), str(copy_path),
                    str(OUT / "render")], check=True)
    pdf = OUT / "render" / "deck.pdf"
    subprocess.run(["pdftoppm", "-png", "-r", "200", "-singlefile", str(pdf), str(OUT / "render" / "slide_full")],
                   check=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    svg = OUT / "concept_mockup.svg"
    png = OUT / "concept_mockup.png"
    svg.write_text(concept_svg())
    render_png(svg, png)
    pptx = OUT / NAME
    build_pptx(png, pptx)
    print("wrote", svg.relative_to(ROOT), png.relative_to(ROOT), pptx.relative_to(ROOT))
    if "--render" in sys.argv:
        render_slide(pptx)
    if "--deliver" in sys.argv:
        for folder in (ONEDRIVE, DOWNLOADS):
            dest = free_name(folder, NAME)
            shutil.copyfile(pptx, dest)
            print("copied to", dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
