"""Config check: every EWU input names a source that really holds it, or says plainly that it is assumed.

What: walks config/ewu.yaml. Each input must be {value, unit} plus a source, or `assumption: true` with a
      `basis`, or both. A bare number, a missing unit or a source that does not hold the value fails.
Why:  judges marked us down for unsourced numbers (plan objection 7). A source string that nobody opens
      proves nothing, so this script opens every one.
How:  repo:PATH:LINE reads that line; fact:KEY reads facts/facts.json; pdf:DOC:PAGE runs pdftotext on that
      page; citation:ID reads the page-verified numbers in checks/citations.yaml. The value (or the entry's
      `quote`) must be found there. `--selftest` plants seven bad inputs and fails unless it catches each.
"""
import argparse, copy, json, re, subprocess, sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "ewu.yaml"
REQUIRED_BLOCKS = ("scenarios", "transformer", "battery", "shift", "prices", "demo", "checks", "teammate_reference")
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def normalize(text):
    text = text.replace("’", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", text).lower().strip()


class SourceReader:
    """Opens each kind of source once and keeps the text."""

    def __init__(self, root=ROOT):
        self.root = root
        facts_path = root / "facts" / "facts.json"
        self.facts = json.loads(facts_path.read_text()) if facts_path.exists() else {}
        self.documents = yaml.safe_load((root / "checks/requirements.yaml").read_text())["sources"]
        self.citations = {c["id"]: c for c in yaml.safe_load((root / "checks/citations.yaml").read_text())["citations"]}
        self.pages = {}

    def repo_line(self, path, line):
        file = self.root / path
        if not file.exists():
            return None, f"file {path} not found"
        lines = file.read_text(errors="ignore").splitlines()
        if not 1 <= line <= len(lines):
            return None, f"{path} has no line {line}"
        return lines[line - 1], None

    def pdf_page(self, doc, page):
        if doc not in self.documents:
            return None, f"document '{doc}' is not named in checks/requirements.yaml"
        key = (doc, page)
        if key not in self.pages:
            run = subprocess.run(["pdftotext", "-layout", "-f", str(page), "-l", str(page), self.documents[doc], "-"],
                                 capture_output=True, text=True)
            self.pages[key] = run.stdout if run.returncode == 0 else None
        if not self.pages[key]:
            return None, f"could not read {doc} page {page}"
        return self.pages[key], None


def number_found(value, text):
    """A number counts as found if it appears as itself or as a percent (0.2 found as 20)."""
    for n in (float(m.replace(",", "")) for m in NUMBER.findall(text)):
        for shown in (value, value * 100):
            if abs(n - shown) <= 1e-6 * max(1.0, abs(shown)):
                return True
    return False


def value_found_in_text(entry, text):
    if "quote" in entry:
        return normalize(str(entry["quote"])) in normalize(text)
    values = entry["value"] if isinstance(entry["value"], list) else [entry["value"]]
    for v in values:
        if isinstance(v, bool):
            return False
        if isinstance(v, (int, float)):
            if not number_found(float(v), text):
                return False
        elif normalize(str(v)) not in normalize(text):
            return False
    return True


def problem_with_source(entry, reader):
    """Return None when the source holds the value, else a plain sentence saying why not."""
    kind, _, rest = str(entry["source"]).partition(":")
    if kind == "repo":
        path, _, line = rest.rpartition(":")
        if not line.isdigit():
            return f"source '{entry['source']}' needs repo:PATH:LINE"
        text, err = reader.repo_line(path, int(line))
    elif kind == "pdf":
        doc, _, page = rest.rpartition(":")
        if not page.isdigit():
            return f"source '{entry['source']}' needs pdf:DOC:PAGE"
        text, err = reader.pdf_page(doc, int(page))
    elif kind == "fact":
        if rest not in reader.facts:
            return f"fact {rest} is not in facts/facts.json"
        fact = reader.facts[rest]["value"]
        same = fact == entry["value"] or (isinstance(fact, (int, float)) and isinstance(entry["value"], (int, float))
                                          and abs(fact - entry["value"]) <= 1e-9 * max(1.0, abs(fact)))
        return None if same else f"value {entry['value']} differs from fact {rest} = {fact}"
    elif kind == "citation":
        if rest not in reader.citations:
            return f"citation {rest} is not in checks/citations.yaml"
        return None if entry["value"] in reader.citations[rest].get("numbers", []) else \
            f"value {entry['value']} is not a listed number of citation {rest}"
    else:
        return f"source '{entry['source']}' is not repo:, fact:, pdf: or citation:"
    if err:
        return err
    if not value_found_in_text(entry, text):
        what = f"quote '{entry['quote']}'" if "quote" in entry else f"value {entry['value']}"
        return f"{what} not found at {entry['source']}"
    return None


def walk_inputs(tree, prefix=""):
    """Yield (name, entry) for every input and (name, None) for any bare value that is not an input."""
    for key, node in tree.items():
        name = f"{prefix}{key}"
        if isinstance(node, dict) and "value" in node:
            yield name, node
        elif isinstance(node, dict):
            yield from walk_inputs(node, name + ".")
        else:
            yield name, None


def find_problems(config, reader):
    problems = [f"block '{b}' is missing" for b in REQUIRED_BLOCKS if b not in (config or {})]
    counts = {"inputs": 0, "sourced": 0, "assumed": 0}
    for name, entry in walk_inputs(config or {}):
        if entry is None:
            problems.append(f"{name}: bare value; write it as {{value, unit, source}} or flag it as an assumption")
            continue
        counts["inputs"] += 1
        if not str(entry.get("unit", "")).strip():
            problems.append(f"{name}: no unit")
        has_source, assumed = "source" in entry, entry.get("assumption") is True
        if not has_source and not assumed:
            problems.append(f"{name}: no source and no assumption flag")
        if assumed:
            counts["assumed"] += 1
            if not str(entry.get("basis", "")).strip():
                problems.append(f"{name}: assumption without a basis saying where it came from")
        if has_source:
            why = problem_with_source(entry, reader)
            if why:
                problems.append(f"{name}: {why}")
            else:
                counts["sourced"] += 1
    return problems, counts


def run_selftest(reader):
    base = {b: {"x": {"value": 20, "unit": "%", "source": "repo:runs/business_case_team_v2.txt:6"}} for b in REQUIRED_BLOCKS}
    plants = {
        "unsourced value": lambda c: c["transformer"].update(planted={"value": 1.25, "unit": "x"}),
        "source on the wrong line": lambda c: c["battery"]["x"].update(source="repo:runs/business_case_team_v2.txt:1"),
        "assumption without basis": lambda c: c["prices"].update(planted={"value": 7, "unit": "$", "assumption": True}),
        "bare number": lambda c: c["shift"].update(planted=42),
        "missing block": lambda c: c.pop("checks"),
        "fact that disagrees": lambda c: c["demo"].update(planted={"value": 0.99, "unit": "kW",
                                                                   "source": "fact:insight.system_peak_mw"}),
        "missing unit": lambda c: c["scenarios"]["x"].pop("unit"),
    }
    clean, _ = find_problems(base, reader)
    ok = not clean
    print(f"{'PASS' if ok else 'FAIL'}  clean planted config has no problems {clean}")
    for label, plant in plants.items():
        bad = copy.deepcopy(base)
        plant(bad)
        caught, _ = find_problems(bad, reader)
        ok &= bool(caught)
        print(f"{'PASS' if caught else 'FAIL'}  caught {label}: {caught[:1]}")
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--selftest", action="store_true", help="plant bad inputs and require each to be caught")
    parser.add_argument("--config", default=str(CONFIG))
    args = parser.parse_args()
    reader = SourceReader()
    if args.selftest:
        sys.exit(0 if run_selftest(reader) else 1)
    problems, counts = find_problems(yaml.safe_load(Path(args.config).read_text()), reader)
    print("".join(f"FAIL  {p}\n" for p in problems), end="")
    print(f"config_check: {counts['inputs']} inputs, {counts['sourced']} with a verified source, "
          f"{counts['assumed']} flagged as assumptions, {len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
