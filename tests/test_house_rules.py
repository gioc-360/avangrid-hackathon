"""House rules: every new module and doc follows the build's written rules, checked by code, not by eye.

What: new Python modules carry a What/Why/How docstring, stay under the line cap in config/ewu.yaml, hold no
      em dash and use plain snake_case function names; docs hold no em dash; private facts stay out of git;
      every line of docs/COMPANY_BRIEF.md quotes words that really sit at its cited source.
Why:  the plan's guardrails only hold if a test fails the moment one is broken, including overnight.
How:  ast for docstrings and names, plain text scans for dashes, `git check-ignore` for private paths, and the
      config checker's source reader plus checks/check_all.py's page reader for the brief's quotes.
"""
import ast, json, re, subprocess
from pathlib import Path
import yaml
from analysis import facts
from checks import check_all, config_check

ROOT = Path(__file__).resolve().parent.parent
NEW_CHECKS = ("config_check", "trace_numbers", "demo_check", "qa_refs", "judge_rounds_check", "review_numbers")
EM_DASH = chr(0x2014)
PLAIN_NAME = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")


def new_modules():
    paths = sorted(ROOT.glob("ewu/*.py")) + sorted(ROOT.glob("tests/*.py")) + [ROOT / "analysis/facts.py"]
    return paths + [ROOT / f"checks/{n}.py" for n in NEW_CHECKS if (ROOT / f"checks/{n}.py").exists()]


def text_files():
    paths = sorted(ROOT.glob("docs/*.md")) + [ROOT / "config/ewu.yaml", ROOT / "README.md"]
    return paths + [p for p in (ROOT / "bin/ewu",) if p.exists()]


def line_cap():
    return yaml.safe_load((ROOT / "config/ewu.yaml").read_text())["checks"]["module_line_cap"]["value"]


def house_rule_breaks(path, cap):
    """Return every house rule this Python file breaks, as plain sentences."""
    text = Path(path).read_text()
    breaks = [f"{len(text.splitlines())} lines, over the cap of {cap}"] if len(text.splitlines()) > cap else []
    if EM_DASH in text:
        breaks.append("holds an em dash")
    tree = ast.parse(text)
    doc = ast.get_docstring(tree) or ""
    breaks += [f"docstring lacks '{label}'" for label in ("What:", "Why:", "How:") if label not in doc]
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("__"):
            if not PLAIN_NAME.match(node.name) or len(node.name) < 4:
                breaks.append(f"function name '{node.name}' does not read as plain words")
    return breaks


def test_new_modules_follow_the_house_rules():
    cap = line_cap()
    found = {str(p.relative_to(ROOT)): house_rule_breaks(p, cap) for p in new_modules()}
    assert {k: v for k, v in found.items() if v} == {}


def test_docs_hold_no_em_dash():
    assert [str(p.relative_to(ROOT)) for p in text_files() if EM_DASH in p.read_text()] == []


def test_a_planted_bad_module_is_caught(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text('"""No labels here ' + EM_DASH + ' none."""\n' + "x = 1\n" * 210 + "def f(a):\n    return a\n")
    breaks = " ".join(house_rule_breaks(bad, 200))
    for expected in ("over the cap", "em dash", "What:", "plain words"):
        assert expected in breaks


def test_private_facts_go_to_the_private_file(tmp_path, monkeypatch):
    monkeypatch.setattr(facts, "FACTS", tmp_path / "facts.json")
    monkeypatch.setattr(facts, "PRIVATE_FACTS", tmp_path / "private" / "facts_private.json")
    facts.record("ewu.test.one_home_kw", 1.234567, "kW", "planted", private=True)
    facts.record("ewu.test.share_pct", 12.5, "%", "planted")
    private = json.loads((tmp_path / "private" / "facts_private.json").read_text())
    public = json.loads((tmp_path / "facts.json").read_text())
    assert private["ewu.test.one_home_kw"]["value"] == 1.2346 and "ewu.test.one_home_kw" not in public
    assert "ewu.test.share_pct" in public and "ewu.test.share_pct" not in private


def test_private_outputs_are_ignored_by_git():
    for path in ("outputs/private/facts_private.json", "outputs/private/inventory.parquet", "outputs/demo/ewu_demo.html"):
        assert subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", path]).returncode == 0, path


def quote_is_at_tag(quote, tag, reader, citations):
    kind, _, where = tag.partition(":") if not tag.startswith("scott ") else ("scott", "", tag[6:])
    if kind == "citation":
        c = citations[where]
        file = c["file"] if c["file"].startswith("/") else (ROOT / c["file"] if c["page"] == 0 else Path(citations["_root"]) / c["file"])
        return check_all.quote_on_page(file, c["page"], quote) is None
    if kind == "scott":
        lines = (ROOT / "sources/qa/office-hours-2026-11-12-scott.txt").read_text().splitlines()
        text = next((l for l in lines if l.startswith(f"[{where}]")), None)
    elif kind == "pdf":
        doc, _, page = where.rpartition(":")
        text, _ = reader.pdf_page(doc, int(page))
    else:
        path, _, line = where.rpartition(":")
        text, _ = reader.repo_line(path, int(line))
    return text is not None and config_check.normalize(quote) in config_check.normalize(text)


def test_every_company_brief_line_quotes_its_source():
    cit_file = yaml.safe_load((ROOT / "checks/citations.yaml").read_text())
    citations = {c["id"]: c for c in cit_file["citations"]} | {"_root": cit_file["root"]}
    reader = config_check.SourceReader()
    bullets = [l for l in (ROOT / "docs/COMPANY_BRIEF.md").read_text().splitlines() if l.startswith("- ")]
    assert len(bullets) >= 20
    wrong = []
    for line in bullets:
        tag = re.search(r"\[([^\]]+)\]\s*$", line)
        quotes = re.findall(r'"([^"]+)"', line)
        outside = re.sub(r'"[^"]*"', "", line[:tag.start()] if tag else line)
        if not tag or not quotes:
            wrong.append(f"no tag or no quote: {line[:60]}")
        elif re.search(r"\d", outside):
            wrong.append(f"digit outside a quote: {line[:60]}")
        elif not all(quote_is_at_tag(q, tag.group(1), reader, citations) for q in quotes):
            wrong.append(f"quote not at {tag.group(1)}: {line[:60]}")
    assert wrong == []


def test_company_brief_keeps_unverified_claims_apart():
    text = (ROOT / "docs/COMPANY_BRIEF.md").read_text()
    sourced, _, unverified = text.partition("## Unverified, do not trust")
    for claim in ("Rate Decoupling Mechanism", "3.4 times operating cash flow", "Stillwater"):
        assert claim in unverified and claim not in sourced
