"""One command answers: are we solving the problem they set, and is every claim true?

    python checks/check_all.py                      # problem coverage + sources
    python checks/check_all.py --deck deck.pptx     # also trace every number on every slide
    python checks/check_all.py --deck runs/plain/REPORT.md

Nothing here asks a person or a model to judge. Each check is a lookup:
  1 BRIEF     each requirement's quote is found on its cited page of the organizers' PDFs
  2 COVERAGE  each requirement has the facts (from code) or files it needs
  3 SOURCES   each outside citation's quote is found on its cited page
  4 NUMBERS   each number in the deck equals a computed fact or a cited number
  5 SCOPE     the deck does not drift onto things the prompt never asked for
Exit code 0 only when every check passes.
"""
import argparse, json, re, subprocess, sys, fnmatch
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "facts" / "facts.json"
# numbers that are part of the problem statement or plain counting, not claims
# 95 = confidence level; 4.5/7.2 = equipment ratings named in rule descriptions
SPEC_NUMBERS = {95, 4.5, 7.2, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 24, 100, 200, 8760, 365, 20.16, 10.08, 7.68, 11.52,
                89.4, 15, 35725, 2025, 2026, 2027, 25, 434, 50}

def norm(s):
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace("•", " ")
    s = re.sub(r"-\s*\n\s*", "", s)
    return re.sub(r"\s+", " ", s).lower().strip()

_page_cache = {}
def page_text(path, page):
    key = (str(path), page)
    if key not in _page_cache:
        p = Path(path)
        if not p.exists():
            _page_cache[key] = None
        elif page == 0:
            _page_cache[key] = p.read_text(errors="ignore")
        else:
            r = subprocess.run(["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(p), "-"],
                               capture_output=True, text=True)
            _page_cache[key] = r.stdout
    return _page_cache[key]

def quote_on_page(path, page, quote):
    t = page_text(path, page)
    if t is None:
        return "file missing"
    if norm(quote) in norm(t):
        return None
    # say where it actually is, if anywhere: a wrong page number is a different error from a made-up quote
    for p in range(1, 200):
        tp = page_text(path, p) if Path(path).suffix == ".pdf" else None
        if not tp:
            break
        if norm(quote) in norm(tp):
            return f"quote is on page {p}, not {page}"
    return "quote not found anywhere in the document"

def load_facts():
    if not FACTS.exists():
        return {}
    return json.loads(FACTS.read_text())

def has_fact(facts, pattern):
    return any(fnmatch.fnmatch(k, pattern) for k in facts)

def deck_text(path):
    p = Path(path)
    if p.suffix == ".pptx":
        from pptx import Presentation
        out = []
        for i, slide in enumerate(Presentation(p).slides, 1):
            bits = []
            for sh in slide.shapes:
                if sh.has_text_frame:
                    bits.append(sh.text_frame.text)
                if getattr(sh, "has_table", False) and sh.has_table:
                    bits += [c.text for r in sh.table.rows for c in r.cells]
            out.append((f"slide {i}", "\n".join(bits)))
        return out
    return [(f"line {i}", l) for i, l in enumerate(p.read_text().splitlines(), 1)]

NUM = re.compile(r"(?<![\w.-])[-+]?\$?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(%|k\b|K\b|M\b|MW|kW|kWh|MWh|GWh)?")

def number_traced(x, decimals, candidates):
    tol = 0.5 * 10 ** (-decimals) + 1e-9
    for c in candidates:
        for scale in (1, 100, 0.001, 1000, 1e-6):     # share as %, kW<->MW, $ -> $k / $M
            if abs(c * scale - x) <= max(tol, abs(x) * 0.005):
                return True
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", help="pptx or markdown to trace")
    a = ap.parse_args()
    req = yaml.safe_load((ROOT / "checks/requirements.yaml").read_text())
    cit = yaml.safe_load((ROOT / "checks/citations.yaml").read_text())
    facts = load_facts()
    fails, rows = 0, []

    def row(check, item, ok, why=""):
        nonlocal fails
        fails += (not ok)
        rows.append((check, item, "PASS" if ok else "FAIL", why))

    # 1 BRIEF + 2 COVERAGE
    for r in req["requirements"]:
        err = quote_on_page(req["sources"][r["doc"]], r["page"], r["quote"])
        row("brief", r["id"], err is None, err or "")
        missing = [f for f in r.get("facts", []) if not has_fact(facts, f)]
        missing += [f for f in r.get("files", []) if not (ROOT / f).exists()]
        row("coverage", r["id"], not missing, ("missing: " + ", ".join(missing)) if missing else "")

    # 3 SOURCES
    for c in cit["citations"]:
        f = c["file"] if c["file"].startswith("/") else (ROOT / c["file"] if c["page"] == 0 else Path(cit["root"]) / c["file"])
        err = quote_on_page(f, c["page"], c["quote"])
        row("source", c["id"], err is None, err or "")

    # 4 NUMBERS + 5 SCOPE
    if a.deck:
        def assumed(k, v):
            return k.startswith("assumption.") or "ASSUM" in v.get("method", "")
        cands = [v["value"] for k, v in facts.items() if isinstance(v.get("value"), (int, float)) and not assumed(k, v)]
        cands += [n for c in cit["citations"] for n in c.get("numbers", [])]
        acands = [v["value"] for k, v in facts.items() if isinstance(v.get("value"), (int, float)) and assumed(k, v)]
        assumed_hits = []
        text = deck_text(a.deck)
        # quotes already verified elsewhere (source pages, analyst reports) are not new claims
        verified = [c["quote"] for c in cit["citations"]]
        cpath = ROOT / "checks/comparison.yaml"
        if cpath.exists():
            for r in yaml.safe_load(cpath.read_text())["rows"]:
                verified += [r["plain"], r["skills"]]
        def strip_verified(t):
            for q in verified:
                t = t.replace(q, " ")
            return t
        # every phrase in curly or straight double quotes must be found on a cited page or in an analyst report
        pages = []
        for c in cit["citations"]:
            f = ROOT / c["file"] if c["page"] == 0 else Path(cit["root"]) / c["file"]
            pages.append(norm(page_text(f, c["page"]) or ""))
        if cpath.exists():
            pages += [norm((ROOT / p_).read_text()) for p_ in yaml.safe_load(cpath.read_text())["reports"].values()]
        bad_q = []
        for w_, t in text:
            for q in re.findall(r"\u201c([^\u201d]{2,})\u201d", t):
                qn = norm(q).rstrip(".,")
                if len(qn.split()) < 3:
                    bad_q.append(f"{w_}: \u201c{q[:60]}\u201d is too short to verify (quote 3+ words or drop the marks)")
                elif not any(re.search(r"(?<!\w)" + re.escape(qn) + r"(?!\w)", pg) for pg in pages):
                    bad_q.append(f"{w_}: \u201c{q[:60]}\u201d not found on any cited page")
        row("quotes", f"{len(bad_q)} unsourced quotes", not bad_q, "; ".join(bad_q[:20]))
        text = [(w_, strip_verified(t)) for w_, t in text]
        untraced = []
        for where, t in text:
            for m in NUM.finditer(t):
                raw = m.group(1).replace(",", "")
                x = float(raw)
                dec = len(raw.split(".")[1]) if "." in raw else 0
                if x in SPEC_NUMBERS or (1900 < x < 2100 and dec == 0):
                    continue
                if number_traced(x, dec, cands):
                    continue
                if number_traced(x, dec, acands):
                    assumed_hits.append(f"{where}: {m.group(0).strip()}")
                else:
                    untraced.append(f"{where}: {m.group(0).strip()}")
        row("numbers", f"{len(untraced)} untraced", not untraced, "; ".join(untraced[:40]))
        # assumption-backed numbers pass only if the same line says so
        unlabeled = [h for h in assumed_hits if not re.search(r"(?i)assum|illustrative",
                     dict(text).get(h.split(":")[0], ""))]
        row("assumed", f"{len(assumed_hits)} rest on assumptions", not unlabeled,
            ("not labeled as assumption: " + "; ".join(unlabeled[:20])) if unlabeled else "")
        full = "\n".join(t for _, t in text)
        for r in req["requirements"]:
            for pat in r.get("deck", []):
                row("deck", r["id"], re.search(pat, full) is not None, f"needs /{pat}/")
        for o in req.get("off_problem", []):
            hits = len(re.findall(o["pattern"], full))
            row("scope", o["text"][:40], hits == 0, f"{hits} mentions; origin: {o['origin']}" if hits else "")

    w = max(len(r[1]) for r in rows)
    for check, item, status, why in rows:
        print(f"{status}  {check:9} {item:<{w}}  {why}")
    by = {}
    for check, _, status, _ in rows:
        by.setdefault(check, [0, 0])[status == "PASS"] += 1
    print("\n" + "  ".join(f"{k}: {v[1]}/{sum(v)}" for k, v in by.items()))
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
