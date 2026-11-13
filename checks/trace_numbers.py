"""Trace numbers: every number in a doc equals a fact the code wrote or an input in config/ewu.yaml.

What: reads one or more Markdown docs, finds every number a reader would take as a claim, and looks for a
      key in facts/facts.json or config/ewu.yaml whose value, rounded to the digits the doc shows, is that
      number (a share like 0.2 may be shown as 20). Prints each number with the key it traced to, then every
      number that traced to nothing; exits 1 if any did. `--selftest` plants untraced numbers and must catch
      each while passing the traced, skipped and year cases.
Why:  the build rule is that no number is typed from memory. A judge can ask where any number came from;
      this script answers with a key for every one, and fails the build the moment a number has no source.
How:  a number is skipped only when it is part of a name, not a claim: inside a word or dotted key
      (margin_115, M2), after a colon or slash (file.py:42, 23:00), a date part (2026-02-07), a plain year,
      or an ordered list marker at the start of a line. Everything else, units glued on or not (11pm, 7.2kW),
      must match at its shown precision.
"""
import argparse, json, re, sys, tempfile
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
NUMBER = re.compile(r"(?<![\w.:/#-])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(?![\d:]|\.\d|-\d)")
LIST_MARKER = re.compile(r"^\s*\d+\.\s")


def numeric_sources(root=ROOT):
    """(key, value) for every number in facts/facts.json and every input value in config/ewu.yaml."""
    found = []
    facts = json.loads((root / "facts" / "facts.json").read_text())
    for key, fact in facts.items():
        if isinstance(fact.get("value"), (int, float)) and not isinstance(fact["value"], bool):
            found.append((f"fact:{key}", float(fact["value"])))

    def walk(node, prefix):
        for key, child in node.items():
            if isinstance(child, dict) and "value" in child:
                values = child["value"] if isinstance(child["value"], list) else [child["value"]]
                for v in values:
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        found.append((f"config:{prefix}{key}", float(v)))
            elif isinstance(child, dict):
                walk(child, f"{prefix}{key}.")
    walk(yaml.safe_load((root / "config" / "ewu.yaml").read_text()), "")
    return found


def claimed_numbers(text):
    """Yield (line number, shown text, value, decimals) for each number that reads as a claim."""
    for number, line in enumerate(text.splitlines(), 1):
        if LIST_MARKER.match(line):
            line = LIST_MARKER.sub(" ", line, count=1)
        for m in NUMBER.finditer(line):
            raw = m.group(1).replace(",", "")
            value = float(raw)
            decimals = len(raw.split(".")[1]) if "." in raw else 0
            if decimals == 0 and 1900 <= value <= 2100:
                continue
            yield number, m.group(1), value, decimals


def matching_key(value, decimals, sources):
    """A key whose value equals the number exactly, else one that rounds to it at the shown precision.

    Exact matches win, and config inputs and ewu facts are tried before older facts, so the printed key is
    the most likely source, not just the first coincidence."""
    ranked = sorted(sources, key=lambda pair: 0 if pair[0].startswith("config:") else 1 if ".ewu." in
                    f".{pair[0][5:]}" else 2)
    for tolerance in (1e-9, 0.5 * 10 ** (-decimals) + 1e-9):
        for key, source in ranked:
            for shown in (source, source * 100):
                if abs(shown - value) <= tolerance:
                    return key
    return None


def trace_document(path, sources):
    """Return (traced rows, untraced rows) for one document."""
    traced, untraced = [], []
    for line, shown, value, decimals in claimed_numbers(Path(path).read_text()):
        key = matching_key(value, decimals, sources)
        (traced if key else untraced).append((f"{path}:{line}", shown, key))
    return traced, untraced


def run_selftest(sources):
    """Plant numbers with known answers; pass only if each is traced, skipped or caught as expected."""
    fact_key, fact_value = next((k, v) for k, v in sources if k.startswith("fact:") and 1 < v < 1000 and v != int(v))
    shown = f"{fact_value:.2f}"
    near_miss = next(f"{fact_value + step:.2f}" for step in (0.37, 0.43, 0.61, 0.79, 1.13)
                     if matching_key(round(fact_value + step, 2), 2, sources) is None)
    doc = (f"Traced fact {shown} and config share 20% and limit 1.20.\n"
           f"Skipped: year 2030, date 2026-02-07, time 23:00, ref ewu/stress.py:42, key margin_115.\n"
           f"1. A list marker is not a claim.\n"
           f"Planted untraced 98765.4321 and near miss {near_miss}.\n")
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "planted.md"
        path.write_text(doc)
        traced, untraced = trace_document(path, sources)
    caught = sorted(shown for _, shown, _ in untraced)
    expected = sorted(["98765.4321", near_miss])
    ok_traced = [shown for _, shown, _ in traced] == [shown, "20", "1.20"]
    ok = caught == expected and ok_traced
    print(f"{'PASS' if caught == expected else 'FAIL'}  caught planted untraced numbers {caught} (want {expected})")
    print(f"{'PASS' if ok_traced else 'FAIL'}  traced {fact_key} and two config inputs; skipped year, date, time, "
          f"file:line, key and list marker; traced {[s for _, s, _ in traced]}")
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("docs", nargs="*", help="Markdown files to trace")
    parser.add_argument("--selftest", action="store_true", help="plant untraced numbers and require each caught")
    parser.add_argument("--quiet", action="store_true", help="print only untraced numbers and the totals")
    args = parser.parse_args()
    sources = numeric_sources()
    if args.selftest:
        sys.exit(0 if run_selftest(sources) else 1)
    if not args.docs:
        parser.error("name at least one doc, or pass --selftest")
    bad = 0
    for doc in args.docs:
        traced, untraced = trace_document(ROOT / doc if not Path(doc).is_absolute() else doc, sources)
        if not args.quiet:
            print("".join(f"ok    {where:<28} {shown:>10}  {key}\n" for where, shown, key in traced), end="")
        print("".join(f"FAIL  {where:<28} {shown:>10}  traces to no fact or config input\n"
                      for where, shown, _ in untraced), end="")
        print(f"trace_numbers: {doc}: {len(traced)} traced, {len(untraced)} untraced")
        bad += len(untraced)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
