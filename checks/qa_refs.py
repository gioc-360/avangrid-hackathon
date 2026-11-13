"""QA refs: every answer in docs/CODE_QA.md points at code that really says what the answer claims.

What: reads a question-and-answer doc whose questions are `### Q<n>.` headings and whose answers cite code
      inside backticks as `path:line anchor` or `path:first-last anchor`. A reference resolves when the file
      is in the repo and not gitignored, the lines exist, and the anchor text sits on those lines. The doc
      fails when any reference does not resolve, when a question cites nothing, or when it holds fewer
      questions than `checks.qa_questions` in config/ewu.yaml. `--selftest` plants one of each fault in a
      scratch doc and must catch every one while passing a good reference.
Why:  the code examiner checks each answer against its file:line, and a judge may open any of them live. A line
      number goes stale the moment code above it moves; the anchor makes this check fail then, instead of
      sending a judge to the wrong line. Ignored paths (outputs/private, data) are refused because nobody
      outside this machine can open them, and they may hold customer rows.
How:  regular expressions find headings and references; `git ls-files` lists the files a reference may name;
      the anchor is compared with the cited lines after collapsing whitespace, so wrapping does not matter.
"""
import argparse, re, subprocess, sys, tempfile
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
QUESTION = re.compile(r"^###\s+Q\d+\.", re.M)
REFERENCE = re.compile(r"`((?:[\w.-]+/)*[\w.-]+):(\d+)(?:-(\d+))?(?:\s+([^`]+))?`")


def required_questions(root=ROOT):
    config = yaml.safe_load((root / "config" / "ewu.yaml").read_text())
    return config["checks"]["qa_questions"]["value"]


def files_a_judge_can_open(root=ROOT):
    """Repo paths that are tracked or new but not gitignored."""
    run = subprocess.run(["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"],
                         capture_output=True, text=True, check=True)
    return set(run.stdout.splitlines())


def squeeze(text):
    return re.sub(r"\s+", " ", text).strip()


def reference_problem(path, first, last, anchor, openable, root=ROOT):
    """Why one reference does not resolve, or None when it does."""
    if not anchor:
        return "has no anchor text after the line number"
    if path not in openable:
        return "names a file that is not in the repo or is gitignored"
    lines = (root / path).read_text(errors="ignore").splitlines()
    if not 1 <= first <= last <= len(lines):
        return f"asks for lines {first}-{last} but the file has {len(lines)}"
    if squeeze(anchor) not in squeeze(" ".join(lines[first - 1:last])):
        return f"anchor '{anchor}' is not on those lines"
    return None


def check_document(text, openable, minimum, root=ROOT):
    """(resolved references, problems) for one Q&A doc."""
    starts = [m.start() for m in QUESTION.finditer(text)] + [len(text)]
    resolved, problems = [], []
    if len(starts) - 1 < minimum:
        problems.append(f"holds {len(starts) - 1} questions, needs at least {minimum}")
    for begin, end in zip(starts, starts[1:]):
        block = text[begin:end]
        title = block.splitlines()[0].lstrip("#").strip()
        refs = list(REFERENCE.finditer(block))
        if not refs:
            problems.append(f"{title}: cites no file:line")
        for m in refs:
            path, first = m.group(1), int(m.group(2))
            last = int(m.group(3)) if m.group(3) else first
            problem = reference_problem(path, first, last, (m.group(4) or "").strip(), openable, root)
            where = f"{title}: {m.group(0)}"
            (problems.append(f"{where} {problem}") if problem else resolved.append(where))
    return resolved, problems


def run_selftest():
    """Plant one fault of each kind; pass only if each is caught and the good reference resolves."""
    openable = files_a_judge_can_open()
    lines = (ROOT / "ewu" / "feeders.py").read_text().splitlines()
    good = next(i for i, line in enumerate(lines, 1) if line.startswith("def rate("))
    doc = "\n".join([
        "### Q1. Good", f"See `ewu/feeders.py:{good} def rate(`.",
        "### Q2. Missing file", "See `ewu/no_such_module.py:3 def nothing`.",
        "### Q3. Past the end", f"See `ewu/feeders.py:{len(lines) + 5} def rate(`.",
        "### Q4. Wrong anchor", f"See `ewu/feeders.py:{good} def build_transformers`.",
        "### Q5. No reference", "Trust me.",
        "### Q6. Private path", "See `outputs/private/facts_private.json:1 value`.",
        "### Q7. No anchor", f"See `ewu/feeders.py:{good}`.", ""])
    minimum = required_questions()
    with tempfile.TemporaryDirectory() as folder:
        (Path(folder) / "planted.md").write_text(doc)
        resolved, problems = check_document((Path(folder) / "planted.md").read_text(), openable, minimum)
    wanted = {"questions, needs at least": "too few questions", "Q2.": "missing file", "Q3.": "lines past the end",
              "Q4.": "anchor not on the line", "Q5.": "question with no reference", "Q6.": "gitignored path",
              "Q7.": "reference with no anchor"}
    caught = {label: any(key in p for p in problems) for key, label in wanted.items()}
    ok = all(caught.values()) and len(problems) == len(wanted) and resolved == [f"Q1. Good: `ewu/feeders.py:{good} def rate(`"]
    for label, hit in caught.items():
        print(f"{'PASS' if hit else 'FAIL'}  caught planted {label}")
    print(f"{'PASS' if ok else 'FAIL'}  good reference resolved, {len(problems)} problems for {len(wanted)} planted faults")
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("doc", nargs="?", help="the Q&A Markdown file, e.g. docs/CODE_QA.md")
    parser.add_argument("--selftest", action="store_true", help="plant faults and require each caught")
    args = parser.parse_args()
    if args.selftest:
        sys.exit(0 if run_selftest() else 1)
    if not args.doc:
        parser.error("name the Q&A doc, or pass --selftest")
    path = Path(args.doc) if Path(args.doc).is_absolute() else ROOT / args.doc
    resolved, problems = check_document(path.read_text(), files_a_judge_can_open(), required_questions())
    print("".join(f"ok    {r}\n" for r in resolved), end="")
    print("".join(f"FAIL  {p}\n" for p in problems), end="")
    questions = len(QUESTION.findall(path.read_text()))
    print(f"qa_refs: {args.doc}: {questions} questions, {len(resolved)} references resolve, {len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
