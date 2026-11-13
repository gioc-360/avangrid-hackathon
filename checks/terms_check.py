"""Terms check: one word per idea, deck v3's word, on every surface a judge or teammate reads.

What: reads docs/TERMS.md (the Terms table: canonical term and banned synonyms as regular expressions; the
      Allowlist table: surface, exact text, reason) and fails on any banned synonym in the rendered demo page
      (every view, dropdown and transformer panel, in every scenario x loading limit state demo_check renders),
      in `bin/ewu` printouts (screen, network, plan --showcase, inventory, case) and the help of every command,
      in README.md and the docs below (inline `code` spans skipped: identifiers, not words), in the front-end
      guide captions (deck/frontend_guide.py) and in the engine figures' labels (deck/engine_figures.py).
      `--selftest` plants synonyms, an allowlisted text in the wrong surface and a code span.
Why:  Gio: "make sure terms are consistent and not using synonyms". A reader who sees "Avangrid cost" on one
      screen and "net cost" on the next asks whether they are two numbers; one word per idea, checked by code,
      keeps the page, the CLI and the docs speaking deck v3's words after every later edit.
How:  Chrome dumps the page DOM after its script runs (checks/demo_audit.py's run_chrome, empty profile, offline);
      the CLI runs as a subprocess; the guide and figures are imported and their text pulled out. Matching is
      per line, case-insensitive; an allowlist entry covers a hit only inside its exact text and surface.
"""
import html, re, subprocess, sys, tempfile
from html.parser import HTMLParser
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TERMS = ROOT / "docs" / "TERMS.md"
DOCS = ("README.md", "docs/BUSINESS_CASE.md", "docs/DEMO_SCRIPT.md", "docs/CODE_QA.md", "docs/ARCHITECTURE.md",
        "docs/TECH_SPECS.md", "docs/demo/cli_output.txt")
RUNS = (("screen",), ("network",), ("plan", "--showcase"), ("inventory",), ("case",))
BLOCKS = {"p", "div", "li", "tr", "td", "th", "h1", "h2", "h3", "section", "summary", "dt", "dd", "button", "table",
          "details", "nav", "aside", "main", "text", "a", "br"}


def table_rows(markdown, heading):
    """Cells of each body row of the first table under `## heading`; an escaped \\| stays inside its cell."""
    part = markdown.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]
    rows = [line for line in part.splitlines() if line.startswith("|")][2:]
    return [[c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", row.strip()[1:-1])] for row in rows]


def read_terms(markdown):
    """([(canonical, [compiled banned]), ...], [(surface, text, reason), ...]) from docs/TERMS.md."""
    terms = [(row[1], [re.compile(p, re.I) for p in re.findall(r"`([^`]+)`", row[3])]) for row in table_rows(markdown, "Terms")]
    allow = [(row[0], re.findall(r"`([^`]+)`", row[1])[0], row[2]) for row in table_rows(markdown, "Allowlist")]
    return terms, allow


def find_synonyms(surface, text, terms, allow):
    """Problems: each banned hit in `text`, with its canonical term, unless an allowlist text of this surface covers it."""
    spans = [a for s, a, reason in allow if s == surface and reason]
    problems = []
    for line in text.splitlines():
        covered = [(m.start(), m.end()) for a in spans for m in re.finditer(re.escape(a), line)]
        for canonical, banned in terms:
            for pattern in banned:
                for m in pattern.finditer(line):
                    if not any(s <= m.start() and m.end() <= e for s, e in covered):
                        context = line[max(0, m.start() - 50):m.end() + 40].strip()
                        problems.append(f"{surface}: '{m.group(0)}' (say '{canonical}'): ...{context}...")
    return problems


class PageText(HTMLParser):
    """Visible text of a dumped DOM, one block element per line, plus aria-labels; script and style skipped."""

    def __init__(self):
        super().__init__()
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        self.skip += tag in ("script", "style")
        if tag in BLOCKS:
            self.parts.append("\n")
        label = dict(attrs).get("aria-label")
        if label:
            self.parts.append(f"\n{label}\n")

    def handle_endtag(self, tag):
        self.skip -= tag in ("script", "style")
        if tag in BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

    def text(self):
        return "\n".join(" ".join(line.split()) for line in "".join(self.parts).splitlines() if line.strip())


def page_text():
    from checks.demo_audit import read_sources, run_chrome
    from checks.demo_check import page_states
    from ewu.demo_page import PAGE
    lines = {}
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs" / "private") as profile:
        for state in page_states(read_sources()):
            reader = PageText()
            reader.feed(run_chrome(f"{PAGE.as_uri()}#{state}", profile, "--dump-dom"))
            lines.update(dict.fromkeys(reader.text().splitlines()))
    return "\n".join(lines)


def cli_texts():
    """{label: output} for the five printouts and the help of the top level and every command."""
    run = lambda *args: subprocess.run([str(ROOT / "bin/ewu"), *args], capture_output=True, text=True, timeout=600)
    out = {}
    for args in RUNS:
        done = run(*args)
        out[f"bin/ewu {' '.join(args)}"] = done.stdout + done.stderr + (f"\nEXIT {done.returncode}" if done.returncode else "")
    top = run("--help").stdout
    out["bin/ewu --help"] = top
    for command in re.search(r"\{([a-z,]+)\}", top).group(1).split(","):
        out[f"bin/ewu {command} --help"] = run(command, "--help").stdout
    return out


def doc_text(path):
    return re.sub(r"`[^`\n]*`", "", (ROOT / path).read_text())


def guide_text():
    from deck import frontend_guide
    page = re.sub(r"<style>.*?</style>", "", frontend_guide.page_html([]), flags=re.S)
    captions = "\n".join(" ".join(view[1:]) for view in frontend_guide.VIEWS)
    return captions + "\n" + html.unescape(re.sub(r"<[^>]+>", "\n", page))


def figure_text():
    from deck import engine_figures
    svg = engine_figures.architecture_svg() + engine_figures.specs_svg()
    return "\n".join(html.unescape(t) for t in re.findall(r"<text[^>]*>(.*?)</text>", svg))


def run_selftest():
    terms, allow = read_terms(TERMS.read_text())
    ok = len(terms) >= 25 and all(banned for _, banned in terms[:3]) and all(reason for *_, reason in allow)
    print(f"{'PASS' if ok else 'FAIL'}  docs/TERMS.md: {len(terms)} terms, {len(allow)} allowlist entries, each with a reason")
    clean = [c for c, _ in terms if find_synonyms("x", c, terms, [])]
    ok &= not clean
    print(f"{'PASS' if not clean else 'FAIL'}  no canonical term is itself banned {clean}")
    defn = "Upgrade all, the cost of upgrading every overloaded transformer"
    plants = {"Avangrid cost on the page": ("page", "Net cost, then Avangrid cost", True),
              "protected in a printout": ("cli", "flag within 2,708, protected 287", True),
              "overload limit, any case": ("page", "Overloaded, by OVERLOAD LIMIT", True),
              "allowlisted text in another surface": ("docs/README.md", defn, True),
              "hit beside the allowlisted text": ("page", defn + "; upgrade every flagged one", True),
              "allowlisted text in its own surface": ("page", defn, False),
              "canonical words only": ("page", "Batteries fix 98% of overloaded transformers at a 120% loading limit", False)}
    for label, (surface, text, bad) in plants.items():
        found = find_synonyms(surface, text, terms, allow)
        ok &= bool(found) == bad
        print(f"{'PASS' if bool(found) == bad else 'FAIL'}  {label}: {found[:1] or 'no hit'}")
    planted = Path(tempfile.mkdtemp(dir=ROOT / "outputs" / "private")) / "doc.md"
    planted.write_text("Run `ewu/plan.py host_table()` and `hosts.T` here.\nOne host per transformer.\n")
    found = find_synonyms("doc", doc_text(planted), terms, allow)
    ok &= len(found) == 1
    print(f"{'PASS' if len(found) == 1 else 'FAIL'}  code spans skipped, prose checked: {len(found)} hit")
    planted.unlink()
    planted.parent.rmdir()
    return ok


def main():
    if "--selftest" in sys.argv:
        sys.exit(0 if run_selftest() else 1)
    from ewu.demo_page import PAGE
    if not PAGE.exists():
        sys.exit(f"FAIL  {PAGE.relative_to(ROOT)} not found; run bin/ewu demo --no-open")
    terms, allow = read_terms(TERMS.read_text())
    surfaces = {"page": page_text()} | cli_texts()
    surfaces |= {path: doc_text(path) for path in DOCS}
    surfaces |= {"deck/frontend_guide.py": guide_text(), "deck/engine_figures.py": figure_text()}
    problems = [f"{label}: exited non-zero" for label, text in surfaces.items() if "\nEXIT " in text]
    for surface, text in surfaces.items():
        problems += find_synonyms(surface, text, terms, allow)
    print("".join(f"FAIL  {p}\n" for p in problems[:300]), end="")
    print(f"terms_check: {len(terms)} terms, {sum(len(b) for _, b in terms)} banned patterns, {len(allow)} allowlisted texts, "
          f"{len(surfaces)} surfaces, {len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
