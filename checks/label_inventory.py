"""Label inventory: every visible text block per view of the demo page, its word count, and the words folded
into "How this is computed", for the labeling pass in docs/APP_PASS.md.

What: builds the demo page from a template (the current one, or any committed one with --rev) and today's values,
      renders each view in headless Chrome, and lists per view the visible blocks (side panel and view separately),
      the visible word total and the folded word total; checks the labeling rule on the current template: each
      view has exactly one closed "How this is computed" disclosure and every est. marker opens its own view's
      disclosure. --shots DIR also saves one 1920x1080 screenshot per view (and one with the disclosure open).
Why:  "too much text" is a count, not an impression: the pass is done when visible words per view fall by half
      while every assumption is still one click away, and this script says both from the rendered page.
How:  a measuring script is appended to a scratch copy of the page; it steps through the views with the page's own
      hash handler and walks text nodes: a node is folded when it sits in a closed <details> outside its <summary>,
      visible when Element.checkVisibility() is true. A word is a whitespace token with a letter or digit.
      The scratch copy lives in outputs/private and is deleted; Chrome runs with its own empty profile.
"""
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from checks.demo_check import run_chrome
from ewu import read_config
from ewu.demo_page import TEMPLATE, collect_values, steps_built

MEASURE = r"""<pre id="label-inventory"></pre><script>
(function () {
  const words = s => (s.match(/\S+/g) || []).filter(t => /[A-Za-z0-9]/.test(t)).length;
  const BLOCK = "h2,h3,p,li,tr,button,a,summary,dt,dd,svg,span.label,span.chip,.legend>span,span.tname,span.tnum,span.tsub,div.foot";
  const folded = n => { for (let e = n.parentElement; e; e = e.parentElement) {
    if (e.tagName === "DETAILS" && !e.open) { const s = n.parentElement.closest("summary"); return !(s && s.parentElement === e); } }
    return false; };
  function blocks(root) {
    const vis = new Map(); let hidden = 0;
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) {
      const t = n.textContent.replace(/\s+/g, " ").trim(); if (!t) continue;
      const el = n.parentElement; if (!el || el.closest("script,style,#label-inventory")) continue;
      if (folded(n)) { hidden += words(t); continue; }
      if (el.checkVisibility && !el.checkVisibility()) continue;
      const b = el.closest(BLOCK) || el;
      vis.set(b, (vis.get(b) || "") + " " + t);
    }
    const list = [...vis.values()].map(t => t.replace(/\s+/g, " ").trim()).map(t => [t, words(t)]).filter(([, n]) => n);
    return { blocks: list, words: list.reduce((a, [, n]) => a + n, 0), folded: hidden };
  }
  const out = {};
  for (const s of STEPS) {
    location.hash = "#step=" + s.id; (typeof onHash === "function" ? onHash : render)();
    const sec = document.getElementById(s.id), view = blocks(sec), side = blocks(document.querySelector("aside, header"));
    const hows = [...sec.querySelectorAll("details")];
    const ests = [...sec.querySelectorAll("button.est, button.tag")].map(b => (b.getAttribute("onclick") || "").match(/openHow\('(\w+)'\)/));
    out[s.id] = { view, side, details: hows.length, closed: hows.filter(d => !d.open).length,
      summary: hows.map(d => (d.querySelector("summary") || {}).textContent || ""), ids: hows.map(d => d.id),
      markers: ests.length, marker_targets: ests.map(m => m ? m[1] : null) };
  }
  document.getElementById("label-inventory").textContent = JSON.stringify(out);
})();
</script>"""
OPEN_HOW = """<script>document.querySelectorAll("section.show details").forEach(d => d.open = true);</script>"""


def template_text(rev):
    if not rev:
        return TEMPLATE.read_text()
    return subprocess.run(["git", "show", f"{rev}:ewu/demo_template.html"], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def page_from(template):
    values = collect_values(read_config())
    built, missing = steps_built(values)
    payload = json.dumps({"values": values, "built": built, "missing": missing}, separators=(",", ":"))
    return template.replace("/*DATA*/", payload.replace("</", "<\\/"))


def measure(page, scratch, profile):
    path = scratch / "label_inventory.html"
    path.write_text(page.replace("</body>", MEASURE + "</body>"))
    dom = run_chrome(path.as_uri(), profile, "--dump-dom", "--window-size=1920,1080")
    found = re.search(r'<pre id="label-inventory">(.*?)</pre>', dom, re.S)
    if not found or not found.group(1).strip():
        raise SystemExit("FAIL  the measuring script wrote nothing")
    return json.loads(found.group(1).replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&"))


def screenshots(page, scratch, profile, views, folder):
    folder.mkdir(parents=True, exist_ok=True)
    for name, html in (("", page), ("_how_open", page.replace("</body>", OPEN_HOW + "</body>"))):
        path = scratch / f"label_shot{name}.html"
        path.write_text(html)
        for view in views:
            run_chrome(f"{path.as_uri()}#step={view}", profile, f"--screenshot={folder / f'{view}{name}.png'}", "--window-size=1920,1080")


def rule_problems(found):
    """The labeling rule on one page: one closed disclosure per view, titled, and every marker opens its own."""
    problems = []
    for view, f in found.items():
        if f["details"] != 1 or f["closed"] != 1 or f["summary"] != ["How this is computed"]:
            problems.append(f"{view}: {f['details']} disclosures, {f['closed']} closed, titles {f['summary']}")
        problems += [f"{view}: a marker opens {t}" for t in f["marker_targets"] if t != view]
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rev", help="measure the template committed at this git revision instead of the working copy")
    ap.add_argument("--json", type=Path, help="write the full inventory here")
    ap.add_argument("--shots", type=Path, help="save one screenshot per view in this folder")
    ap.add_argument("--blocks", action="store_true", help="print every visible block")
    args = ap.parse_args()
    page = page_from(template_text(args.rev))
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs" / "private") as tmp:
        scratch = Path(tmp)
        found = measure(page, scratch, scratch / "profile")
        if args.shots:
            screenshots(page, scratch, scratch / "profile", list(found), args.shots)
    if args.json:
        args.json.write_text(json.dumps(found, indent=1))
    print(f"{'view':<10} {'view words':>10} {'panel words':>11} {'face total':>10} {'folded':>7} {'markers':>7}")
    for view, f in found.items():
        print(f"{view:<10} {f['view']['words']:>10} {f['side']['words']:>11} {f['view']['words'] + f['side']['words']:>10} "
              f"{f['view']['folded']:>7} {f['markers']:>7}")
        if args.blocks:
            for text, n in f["view"]["blocks"]:
                print(f"    {n:>4}  {text[:110]}")
    problems = [] if args.rev else rule_problems(found)
    print("".join(f"FAIL  {p}\n" for p in problems), end="")
    print(f"label_inventory: {len(found)} views, {len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
