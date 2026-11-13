"""Demo video script for the teammate's voice: numbered lines, timing, what is on screen, words to say.

What: writes outputs/deck/video_script/EWU_demo_script.docx and docs/DEMO_VIDEO_SCRIPT.md from LINES below.
Why:  the teammate rewords it in her own voice and records it; each line keeps its number so the picture can be
      cut to her recording line by line. Every number is deck v3's (checked by checks/trace_numbers.py on the md).
How:  python3 -I deck/video_script/script.py
"""
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.table import WD_TABLE_ALIGNMENT

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "deck" / "video_script"

# (time, on screen, words)
LINES = [
    ("0:00-0:12", "Summary view", "Every home in New York that adds an EV or a heat pump puts more load on the transformer outside. "
     "Avangrid needs to know which transformers will overload before they do."),
    ("0:12-0:25", "Network view, Today", "This is the tool we built for the distribution planner. Each mark is one transformer serving "
     "eight real homes, built from the hourly meter data Avangrid already collects."),
    ("0:25-0:36", "Network view, Synthetic network tag", "The data came without a transformer map, so the network is simulated from "
     "real homes. Load Avangrid's map, and the same engine runs on the real grid."),
    ("0:36-0:55", "Click 2030: Flag", "Now jump to 2030, when 20% of homes have added an EV and 15% a heat pump. In the moderate case, 292 of 3,000 "
     "transformers go over their limit, most of them on winter nights when heat pumps run hardest."),
    ("0:52-1:07", "Click Place (batteries)", "The cheapest fix comes first. For each overloaded transformer, the engine sizes one to "
     "four leased battery units, placed in priority homes behind it."),
    ("1:07-1:20", "Click Upgrade", "Only 5 transformers are left that batteries cannot fix. That is the only place a new transformer "
     "is needed. Across both scenarios, batteries fix 92% to 98% of overloaded transformers."),
    ("1:20-1:33", "Click one transformer: its worst day", "Click any transformer and the planner sees why: its load hour by hour "
     "against its limit, and how much the battery units must cover on its worst day."),
    ("1:33-1:50", "Money view", "Across NYSEG, that is a net cost of $34M instead of $111M in the moderate case, after lease "
     "payments and NYSERDA incentives: 58% to 69% less than upgrading every overloaded transformer."),
    ("1:50-2:05", "Terminal: bin/ewu screen runs live", "And this is not a slide. The engine runs on all 33,757 homes in seconds, "
     "and every number on screen is written by the code, never typed. A check fails if one does not match."),
    ("2:05-2:18", "Back to the Network view, Upgrade", "So the planner gets one list: which transformers will overload, where to "
     "place batteries, and the few that need an upgrade. Customers electrify sooner, without waiting for a new transformer."),
]

GUIDE = [
    "Reword any line in your own voice. Keep its number, keep its numbers exactly, and keep it about the same length.",
    "Record in a quiet room; a phone voice memo is fine. Read the lines in order and pause about one second between lines.",
    "If you change a number or a term, tell Gio: the screen shows the deck's numbers and words.",
    "Terms match the deck: overloaded, Flag, Place, Upgrade, battery units, priority homes, net cost.",
]


def words(text):
    return len(text.split())


def write_md():
    total = sum(words(w) for *_, w in LINES)
    rows = "\n".join(f"| {i} | {t} | {s} | {w} |" for i, (t, s, w) in enumerate(LINES, 1))
    md = (f"# Demo video script (for the teammate's voice)\n\nAbout 2:18, {total} words, about 140 words a minute. "
          "Numbers and terms are deck v3's.\n\n| # | Time | On screen | Say |\n|---|---|---|---|\n" + rows + "\n")
    (ROOT / "docs" / "DEMO_VIDEO_SCRIPT.md").write_text(md)
    return total


def write_docx(total):
    doc = Document()
    st = doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(11)
    doc.add_heading("Electrify Without Upgrade: demo video script", level=1)
    doc.add_paragraph(f"About 2 minutes 20 seconds, {total} words. One row per line; the video will be cut to your recording line by line.")
    for g in GUIDE:
        doc.add_paragraph(g, style="List Bullet")
    t = doc.add_table(rows=1, cols=4); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for c, h in zip(t.rows[0].cells, ["#", "Time", "On screen", "Say (edit freely, keep the numbers)"]):
        c.text = h; c.paragraphs[0].runs[0].font.bold = True
    for i, (tm, scr, w) in enumerate(LINES, 1):
        cells = t.add_row().cells
        cells[0].text, cells[1].text, cells[2].text, cells[3].text = str(i), tm, scr, w
        for c in cells[:3]:
            for r in c.paragraphs[0].runs:
                r.font.size = Pt(9); r.font.color.rgb = RGBColor(0x5F, 0x6B, 0x66)
    widths = [0.3, 0.8, 1.5, 4.4]
    from docx.shared import Inches
    t.autofit = False
    for col, wd in zip(t.columns, widths):
        col.width = Inches(wd)
    for row in t.rows:
        for c, wd in zip(row.cells, widths):
            c.width = Inches(wd)
    OUT.mkdir(parents=True, exist_ok=True)
    doc.save(OUT / "EWU_demo_script.docx")


if __name__ == "__main__":
    n = write_md()
    write_docx(n)
    print(f"{len(LINES)} lines, {n} words; wrote {OUT / 'EWU_demo_script.docx'} and docs/DEMO_VIDEO_SCRIPT.md")
