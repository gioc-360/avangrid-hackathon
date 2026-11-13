"""Front-end guide for the team: one screenshot per view of the EWU page plus what it is for, as a PDF.

What: captures every side-panel view of outputs/demo/ewu_demo.html with headless Chrome and lays them out
      with a short caption (what the view answers, who uses it, what to click) into
      outputs/deck/frontend_guide/EWU_frontend_guide.pdf.
Why:  teammates build the deck and need to know what the tool shows without running it. Captions carry no
      numbers, so the guide never disagrees with the screenshots: every number on a page is in its picture.
How:  python3 -I deck/frontend_guide.py  (rebuild the page first with bin/ewu demo --no-open).
      The drill-down of a single transformer is not captured: it draws 8 real homes' summed load.
"""
import subprocess
import tempfile
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "outputs" / "demo" / "ewu_demo.html"
OUT = ROOT / "outputs" / "deck" / "frontend_guide"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# (hash, title, what it answers, who uses it, what to click)
VIEWS = [
    ("step=deck", "Deck", "The deck's headline numbers, recomputed by our engine next to the numbers from her code.",
     "Whoever presents: proves the slides reproduce.", "Hover a number to see the fact it comes from."),
    ("step=network&net=today", "Network: today", "The whole simulated grid: one substation, six feeders, 3,000 transformers of 8 real homes each.",
     "Distribution planner.", "The buttons above the diagram step through the plan on the same network."),
    ("step=network&net=flag", "Network: 2030 Flag", "Which transformers go over their limit once 2030 EVs and heat pumps are added.",
     "Distribution planner.", "Click a transformer to see its worst day against its limit (keep that view on the laptop)."),
    ("step=network&net=upgrade", "Network: after every fix", "What is left for a new transformer after batteries (and optional managed charging) do their part.",
     "Planner and finance.", "Compare the counts in the top right with the Flag view."),
    ("step=overview", "Overview", "The plan on one screen: problem size, fixes in order, cost against upgrading everything.",
     "Anyone new to the tool.", "Open “How this is computed” for assumptions and sources."),
    ("step=inventory", "Inventory", "What equipment each kind of home has, read from hourly meter data, and which programs it qualifies for.",
     "Customer programs team.", "Pick a segment; homes shown are composites of segment averages, not real customers."),
    ("step=flag", "Flag", "How many transformers overload, as a range over transformer sizing and grouping.",
     "Distribution planner.", "Switch scenario and sizing to see the range."),
    ("step=shift", "Shift", "How much managed (staggered) EV charging fixes, an optional scenario in the team setup.",
     "Customer programs team.", "Compare unmanaged, timer and staggered charging."),
    ("step=protect", "Protect", "Battery hosts: how many units each transformer needs and whether they last through the Feb 7-8 cold snap.",
     "Planner and programs team.", "Choose 1 or 2 host homes per transformer."),
    ("step=upgrade", "Upgrade", "The transformers nothing else can fix.", "Planner and finance.", "Read with the Money view."),
    ("step=money", "Money", "Cost of the plan against upgrading every overloaded transformer: gross, net without NYSERDA, Avangrid net.",
     "Finance and regulatory.", "Open “How this is computed” for prices; prices are placeholders to confirm."),
]


def shoot(profile, frag, path):
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
                    f"--user-data-dir={profile}", "--virtual-time-budget=3000", "--window-size=1600,1000",
                    f"--screenshot={path}", f"{PAGE.as_uri()}#{frag}"], capture_output=True, timeout=90, check=True)


def page_html(shots):
    css = ("@page{size:11in 8.5in;margin:0.45in}body{font:13px Helvetica,Arial,sans-serif;color:#1b1b1b}"
           "h1{font-size:24px;margin:0 0 6px}p.lead{font-size:14px;color:#444;max-width:9.5in}"
           ".v{break-before:page;margin:0}.v.first{break-before:auto}.v img{display:block;max-width:100%;max-height:5.7in;border:1px solid #ccc}.v.first img{max-height:3.6in}"
           ".cap{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:14px;margin:6px 0 0}.cap b{display:block;font-size:11px;"
           "color:#666;text-transform:uppercase;letter-spacing:.04em}h2{font-size:17px;margin:14px 0 4px}"
           "table{border-collapse:collapse;margin:8px 0 16px}td,th{border:1px solid #bbb;padding:5px 9px;text-align:left}")
    intro = ("<h1>Electrify Without Upgrade: the tool, view by view</h1>"
             "<p class='lead'>The product is the engine: a Python package that reads Avangrid's hourly meter data and weather, "
             "simulates 2030 EV and heat pump load on transformers, and writes action lists (which transformers need batteries, "
             "which need an upgrade, which homes to enroll). This page is the viewer for one run. Every number on it comes from "
             "the engine's stored facts, and checks fail the build if one does not match.</p>"
             "<table><tr><th>Tag</th><th>Meaning</th></tr>"
             "<tr><td>GIVEN</td><td>In the hackathon data: hourly meter data, weather, labeled homes</td></tr>"
             "<tr><td>DERIVED</td><td>Computed from given data: equipment inventory, segments, EV sessions, her EV and heat pump tables</td></tr>"
             "<tr><td>SIMULATED</td><td>Modeled, not observed: transformers and feeders (no map was given), 2030 adopters, overloads and fixes</td></tr>"
             "<tr><td>ASSUMED</td><td>Placeholders to confirm with Avangrid: ratings rule, 120% limit, prices, discount rate</td></tr></table>"
             "<p class='lead'>Run it: <code>bin/ewu demo</code> opens this page; <code>bin/ewu screen</code> runs the plan live in seconds; "
             "<code>bin/ewu plan --showcase</code> writes the action lists (home lists use simulated SIM- homes).</p>")
    body = "".join(
        f"<div class='v{' first' if i == 0 else ''}'><h2>{escape(t)}</h2><img src='{s.name}'><div class='cap'><div><b>Answers</b>{escape(a)}</div>"
        f"<div><b>Used by</b>{escape(u)}</div><div><b>Try</b>{escape(c)}</div></div></div>"
        for i, (s, (_, t, a, u, c)) in enumerate(zip(shots, VIEWS)))
    return f"<!doctype html><meta charset='utf-8'><title>EWU front end guide</title><style>{css}</style>{intro}{body}"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    shots = []
    with tempfile.TemporaryDirectory(dir="/private/tmp/claude-501") as profile:
        for i, (frag, *_rest) in enumerate(VIEWS):
            path = OUT / f"view_{i:02d}.png"
            shoot(profile, frag, path)
            shots.append(path)
        html = OUT / "guide.html"
        html.write_text(page_html(shots))
        pdf = OUT / "EWU_frontend_guide.pdf"
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={profile}",
                        "--no-pdf-header-footer", "--virtual-time-budget=3000", f"--print-to-pdf={pdf}", html.as_uri()],
                       capture_output=True, timeout=120, check=True)
    print(f"wrote {pdf}")


if __name__ == "__main__":
    main()
