"""Engine figures: the architecture diagram and the tech specs sheet, as 1920x1080 SVG and PNG, numbers from facts.

What: architecture_svg() draws the engine as one left-to-right flow (Read inputs, Profile every home, Add 2030
      load, Run the steps, Ship action lists) with the file names under each box and a trust layer across
      the bottom; spec_rows() lists the measured specs as (spec, value) pairs; specs_svg() draws them as a
      ruled table; render_png() screenshots each SVG with headless Chrome. Writes outputs/deck/.
Why:  the product is the engine, not the viewer page, so the deck needs a picture of the engine and a sheet
      of its measured specs. Drawing them from facts/facts.json and config/ewu.yaml means a rerun of
      deck/engine_specs.py updates every number, and nothing is typed from memory.
How:  plain SVG strings, one accent colour with one job (the action lists Avangrid receives), thin single
      borders, text 24 px or larger. The action lists are the files `bin/ewu plan` writes (ewu/plan.py).
      Chrome runs with an empty profile from checks/demo_check.py's path. No customer data is drawn.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from checks.demo_check import CHROME
from ewu import config_value

OUT = ROOT / "outputs" / "deck"
TRUST_TOP = 800
TAGS = {"GIVEN": "in the hackathon data", "DERIVED": "computed from given data",
        "SIMULATED": "modeled, not observed", "ASSUMED": "placeholder, to confirm"}
INK, GREY, RULE, ACCENT = "#1b1b1b", "#555555", "#9a9a9a", "#0a6e8a"
SANS, MONO = "Helvetica Neue, Helvetica, Arial, sans-serif", "Menlo, Monaco, monospace"


def facts():
    return json.loads((ROOT / "facts" / "facts.json").read_text())


def fact(key, fmt="{:,}"):
    return fmt.format(facts()[key]["value"])


def text(x, y, words, size=24, weight=400, fill=INK, family=SANS, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}">{escape(words)}</text>')


def draw_box(x, y, w, h, stroke=INK, width=2):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{stroke}" stroke-width="{width}"/>'


def arrow(x1, y1, x2, y2):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{INK}" stroke-width="2.5" '
            f'marker-end="url(#head)"/>')


def svg_page(parts):
    head = ('<defs><marker id="head" markerUnits="userSpaceOnUse" markerWidth="20" markerHeight="20" refX="18" refY="10" orient="auto">'
            f'<path d="M0,2 L20,10 L0,18 z" fill="{INK}"/></marker></defs>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">'
            f'<rect width="1920" height="1080" fill="#ffffff"/>{head}{"".join(parts)}</svg>')


def flow_boxes():
    """(label, x, width, rows); a row is (words, style) with style bold, grey, mono, accent or rule."""
    homes, hours = fact("specs.matrix.homes"), fact("specs.matrix.hours")
    return [
        ("Read inputs", 60, 330, [("Hourly meter data", "bold"), ("GIVEN", "tag"), (f"{homes} homes x {hours} h", "grey"),
                                  ("Hourly weather", "bold"), ("GIVEN", "tag"),
                                  ("Transformer map", "bold"), ("SIMULATED", "tag"), ("synthetic until --map", "grey"),
                                  ("Prices, scenarios", "bold"), ("ASSUMED", "tag"), ("config/ewu.yaml", "mono")]),
        ("Profile every home", 436, 300, [("DERIVED", "tag"), ("analysis/", "grey"), ("ingest.py", "mono"), ("features.py", "mono"),
                                          ("classify.py", "mono"), ("segment.py", "mono"), ("bess.py", "mono"),
                                          ("ewu/inventory.py", "mono"), ("", "rule"),
                                          (f"load matrix {fact('specs.matrix.gb', '{}')} GB", "grey")]),
        ("Add 2030 load", 782, 290, [("SIMULATED", "tag"), ("ewu/", "grey"), ("feeders.py", "mono"), ("adoption.py", "mono"),
                                     ("stress.py", "mono"), ("", "rule"), (f"{config_value('transformer.count'):,} transformers", "grey"),
                                     (f"of {config_value('transformer.homes_per_transformer')} homes each", "grey"), ("or the real map", "grey"),
                                     ("EVs, heat pumps", "grey"), ("by scenario", "grey"), ("EV sessions from", "grey"), ("given meter data", "grey")]),
        ("Run the steps", 1118, 290, [("SIMULATED", "tag"), ("Flag, Shift,", "bold"), ("Place, Upgrade", "bold"), ("ewu/", "grey"),
                                       ("shift.py", "mono"), ("fitscore.py", "mono"), ("dispatch.py", "mono"),
                                       ("coldsnap.py", "mono"), ("economics.py", "mono"), ("sensitivity.py", "mono"),
                                       ("screen.py", "mono")]),
        ("Ship action lists", 1454, 400, [("Transformer actions", "accent"), ("SIMULATED", "tag"), ("transformer_actions.csv", "mono"),
                                          ("Battery hosts", "accent"), ("SIMULATED", "tag"), ("battery_hosts.csv", "mono"),
                                          ("Program targets", "accent"), ("SIMULATED", "tag"), ("program_targets.csv", "mono"),
                                          ("Capital plan", "accent"), ("ASSUMED", "tag"), ("capital_plan.csv", "mono"), ("", "rule"),
                                          ("Viewer page, business case", "bold")]),
    ]


def architecture_svg():
    top, height = 166, 560
    parts = [text(60, 84, "One offline engine turns meter data into action lists and checks every number", 40, 700),
             text(60, 132, "The ewu Python package and bin/ewu CLI, run as a batch job on Avangrid's own machines",
                  26, 400, GREY)]
    styles = {"bold": (24, 700, INK, SANS), "grey": (24, 400, GREY, SANS), "mono": (24, 400, INK, MONO),
              "accent": (24, 700, ACCENT, SANS)}
    boxes = flow_boxes()
    for i, (label, x, w, rows) in enumerate(boxes):
        last = i == len(boxes) - 1
        parts += [draw_box(x, top, w, height, ACCENT if last else INK, 4 if last else 2),
                  text(x + 20, top + 50, label, 30, 700, ACCENT if last else INK),
                  f'<line x1="{x}" y1="{top + 72}" x2="{x + w}" y2="{top + 72}" stroke="{RULE}" stroke-width="1.5"/>']
        y = top + 112
        for words, style in rows:
            if style == "rule":
                parts.append(f'<line x1="{x + 20}" y1="{y - 18}" x2="{x + w - 20}" y2="{y - 18}" stroke="{RULE}"/>')
                y += 14
                continue
            if style == "tag":
                parts += tag(x + 20, y - 22, words)
                y += 36
                continue
            size, weight, fill, family = styles[style]
            parts.append(text(x + 20, y, words, size, weight, fill, family))
            y += 36 if style in ("mono", "grey") else 33
        if not last:
            parts.append(arrow(x + w + 6, top + height / 2, boxes[i + 1][1] - 8, top + height / 2))
        if i:
            parts += [arrow(x + w / 2, top + height + 4, x + w / 2, TRUST_TOP - 4), text(x + w / 2 + 12, top + height + 44, "facts", 20, 400, GREY)]
    parts += trust_layer()
    return svg_page(parts)


def tag(x, y, word):
    """Provenance pill; the word itself carries the meaning, so it reads without colour."""
    w = 24 + 13 * len(word)
    solid = word == "GIVEN"
    dash = "" if word in ("GIVEN", "DERIVED") else ' stroke-dasharray="6 4"'
    return [f'<rect x="{x}" y="{y}" width="{w}" height="28" rx="14" fill="{INK if solid else '#ffffff'}" '
            f'stroke="{INK}" stroke-width="2"{dash}/>',
            text(x + w / 2, y + 20, word, 18, 700, "#ffffff" if solid else INK, SANS, "middle")]


def legend(y):
    parts, x = [], 60
    for word, meaning in TAGS.items():
        parts += tag(x, y - 21, word)
        x += 24 + 13 * len(word) + 12
        parts.append(text(x, y, meaning, 22, 400, GREY))
        x += 13 * len(meaning) + 40
    return parts


def trust_layer():
    items = [("facts/facts.json", "one source of numbers"), ("trace_numbers.py", "docs equal facts"),
             ("demo_check.py", "viewer equals facts"), ("recompute_battery.py", "second code, same answer"),
             ("pytest", f"{fact('specs.tests_collected')} tests"),
             ("make check", f"exit {fact('specs.make_check.exit_code')} in {fact('specs.make_check.seconds')} s")]
    top = TRUST_TOP
    parts = [draw_box(60, top, 1794, 170), text(90, top + 44, "Check every number", 30, 700),
             f'<line x1="60" y1="{top + 70}" x2="1854" y2="{top + 70}" stroke="{RULE}" stroke-width="1.5"/>']
    for x, (name, what) in zip((90, 385, 665, 945, 1320, 1580), items):
        parts += [text(x, top + 108, name, 24, 400, INK, MONO), text(x, top + 146, what, 24, 400, GREY)]
    return parts + legend(1030) + [text(1854, 1066, "Figure 1  EWU engine; tags show what is given, derived, simulated or assumed", 20, 400, GREY, SANS, "end")]


def spec_rows():
    """(spec, measured value) pairs; every number comes from facts/facts.json or config/ewu.yaml."""
    pkg = ", ".join(f"{n} {fact('specs.package.' + n, '{}')}" for n in ("numpy", "pandas", "polars", "scipy", "pyarrow"))
    return [
        ("Language", f"Python {fact('specs.python_version', '{}')}; {pkg}"),
        ("Engine code", f"{fact('specs.code.engine.lines')} lines in {fact('specs.code.engine.files')} ewu modules, "
                        f"none over {fact('specs.code.engine.largest_module_lines')}"),
        ("Pipeline, checks", f"analysis {fact('specs.code.analysis.lines')} lines; checks {fact('specs.code.checks.lines')}; "
                             f"tests {fact('specs.code.tests.lines')}"),
        ("Command line", f"bin/ewu, {fact('specs.cli_commands')} commands: " + ", ".join(facts()["specs.cli_command_names"]["value"][:9])
         + (f" and {len(facts()['specs.cli_command_names']['value']) - 9} more" if len(facts()["specs.cli_command_names"]["value"]) > 9 else "")),
        ("Input matrix", f"{fact('specs.matrix.homes')} homes x {fact('specs.matrix.hours')} hours, "
                         f"{fact('specs.matrix.dtype', '{}')}, {fact('specs.matrix.gb', '{}')} GB; full read "
                         f"{fact('specs.matrix.full_load_seconds', '{}')} s"),
        ("Live screen", f"bin/ewu screen {fact('specs.screen.measured_seconds', '{}')} s, full data "
                        f"(limit {config_value('checks.screen_seconds_max')} s); peak memory "
                        f"{fact('specs.screen.peak_footprint_gb', '{}')} GB"),
        ("Cold snap, grid", f"cold snap {fact('ewu.coldsnap.seconds', '{}')} s; sensitivity grid "
                            f"{fact('ewu.sensitivity.seconds', '{}')} s"),
        ("Trust", f"{fact('specs.tests_collected')} tests, {fact('specs.check_scripts')} check scripts, "
                  f"make check exit {fact('specs.make_check.exit_code')} in {fact('specs.make_check.seconds')} s"),
        ("Runs on", f"one {fact('specs.machine.model', '{}')}, {fact('specs.machine.cpu', '{}')}, "
                    f"{fact('specs.machine.ram_gb')} GB; offline, no cloud"),
        ("Action lists", f"bin/ewu plan: transformer_actions.csv ({config_value('transformer.count'):,} rows), "
                         "capital_plan.csv; home lists real only with --private"),
        ("Avangrid's map", "one flag: --map CSV with meter_id, transformer_id, kva; on bin/ewu screen today, plan next"),
        ("Deployment", "scheduled batch job on Avangrid's data platform; no customer data leaves"),
    ]


def specs_svg():
    parts = [text(60, 84, "The engine runs on one laptop, offline, and every spec below was measured", 40, 700),
             text(60, 132, "Measured by deck/engine_specs.py on this machine; cold snap and grid runtimes as the engine recorded them", 26, 400, GREY)]
    rows, top, height = spec_rows(), 168, 68
    parts.append(draw_box(60, top, 1800, height * len(rows)))
    parts.append(f'<line x1="420" y1="{top}" x2="420" y2="{top + height * len(rows)}" stroke="{RULE}" stroke-width="1.5"/>')
    for i, (spec, value) in enumerate(rows):
        y = top + i * height
        if i:
            parts.append(f'<line x1="60" y1="{y}" x2="1860" y2="{y}" stroke="{RULE}" stroke-width="1.5"/>')
        parts += [text(84, y + 44, spec, 28, 700), text(444, y + 44, value, 26)]
    return svg_page(parts)


def render_png(svg_path, png_path):
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run([CHROME, "--headless=new", f"--user-data-dir={profile}", "--hide-scrollbars",
                        "--window-size=1920,1080", "--default-background-color=ffffffff",
                        f"--screenshot={png_path}", svg_path.as_uri()], check=True, capture_output=True, timeout=120)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "spec_rows.json").write_text(json.dumps(spec_rows(), indent=1) + "\n")
    for name, build in (("architecture", architecture_svg), ("tech_specs", specs_svg)):
        path = OUT / f"{name}.svg"
        path.write_text(build())
        render_png(path, OUT / f"{name}.png")
        print(f"wrote {path.relative_to(ROOT)} and {name}.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
