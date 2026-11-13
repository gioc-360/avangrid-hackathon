"""Write a NEW deck, outputs/deck/v3/D4G_v3.pptx, with every mapped number replaced from our engine's facts.

What: reads deck/v3/fact_map.yaml, facts/facts.json and config/ewu.yaml; computes each mapped number (and each pending
      one whose key now exists); replaces it in place in text runs, table cells, notes, chart titles, chart categories,
      series names and chart values (chart.replace_data, series names kept); prints a change log (slide, id, old, new),
      the claims that no longer hold, ranges that flipped order, and the pictures that need a new image or a caption.
Why:  v3 makes the deck agree with our engine. A number we cannot source must stop the build, never be guessed:
      if any mapped key is missing, nothing is written.
How:  each entry is found again by its id (see deck/v3/inventory.py) and checked against the old number and its
      paragraph text before it is touched; a number split across runs is written into its first run and removed from
      the others, so run formatting stays. Pictures are never touched. The source must be a copy, never ~/Downloads;
      the output never overwrites: an existing D4G_v3.pptx makes D4G_v3b.pptx, then c, and so on.
    .venv/bin/python -I deck/v3/apply.py outputs/deck/v3/source_copy.pptx            # writes the new deck
    .venv/bin/python -I deck/v3/apply.py outputs/deck/v3/source_copy.pptx --dry-run  # change log only, writes nothing
"""
import argparse
import json
import re
import string
import sys
from pathlib import Path

import yaml
from pptx import Presentation
from pptx.chart.data import CategoryChartData

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inventory import A, C, NUMBER, segments, walk  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs/deck/v3"
SAFE = {"round": round, "min": min, "max": max, "abs": abs}


class Missing(Exception):
    pass


class Resolver:
    def __init__(self, fmap):
        self.facts = json.loads((ROOT / "facts/facts.json").read_text())
        self.config = yaml.safe_load((ROOT / "config/ewu.yaml").read_text())
        ps = fmap["aliases"]["peak_source"]
        self.alias = ps[ps["selected"]]
        self.selected = ps["selected"]

    def ref(self, ref):
        if ref.startswith("@"):
            return self.ref(self.alias[ref[1:]])
        if ref.startswith("cfg:"):
            node = self.config
            for part in ref[4:].split("."):
                if not isinstance(node, dict) or part not in node:
                    raise Missing(ref)
                node = node[part]
            return node["value"]
        if ref not in self.facts:
            raise Missing(ref)
        return self.facts[ref]["value"]

    def value(self, e):
        if e.get("key"):
            return self.ref(e["key"])
        names = {n: self.ref(k) for n, k in (e.get("keys") or {}).items()}
        return eval(e["expr"], {"__builtins__": SAFE}, names)   # expressions come from our own fact_map.yaml

    def money(self, col, s, L, U):
        """Same formula as build_fact_map.money: NYSEG $M on our engine's basis (upgrade counted 15 of 40 years)."""
        sc = {"m": "moderate", "h": "high"}[s]
        g = lambda name: self.ref(f"ewu.deck.{sc}.limit_{L}.{name}")
        over, bat, upg = g("overloaded"), g("batteries"), g("upgrades")
        scale = self.ref("ewu.deck.nyseg_transformers") / self.ref("cfg:profiles.deck.transformer_count") / 1e6
        unit, lease, nys = (self.ref("cfg:profiles.deck.battery_unit_usd"), self.ref("ewu.deck.prices.lease_pv_usd"),
                            self.ref("cfg:profiles.deck.nyserda_usd_unit"))
        U = U * self.ref("ewu.deck.prices.factor") / self.ref("ewu.deck.prices.life_factor")
        return {"upall": over * U, "gross": bat * unit + upg * U, "net": bat * (unit - lease - nys) + upg * U}[col] * scale

    def claim(self, c):
        names = {n: self.ref(k) for n, k in (c.get("keys") or {}).items()}
        names.update({col: (lambda col: lambda s, L, U: self.money(col, s, L, U))(col) for col in ("upall", "gross", "net")})
        return eval(c["expr"], {"__builtins__": SAFE}, names)


def compute(fmap, res):
    """New text for every entry that will be applied; refuse on any missing key of a mapped entry."""
    new, missing, promoted, skipped = {}, {}, [], []
    for eid, e in fmap["entries"].items():
        if e["status"] not in ("mapped", "pending"):
            continue
        try:
            v = res.value(e)
        except Missing as err:
            if e["status"] == "mapped":
                missing.setdefault(str(err), []).append(eid)
            else:
                skipped.append((eid, e.get("expected_key")))
            continue
        if e["status"] == "pending":
            promoted.append(eid)
        text = e["fmt"].format(v)
        if not e["kind"].startswith("chart_value"):
            a, b = NUMBER.fullmatch(text), NUMBER.fullmatch(str(e["old"]))
            if not a or not b or (a.group("cur"), (a.group("suf") or "").strip()) != (b.group("cur"), (b.group("suf") or "").strip()):
                sys.exit(f"REFUSED: {eid} formats to {text!r}, not the same kind of number as {e['old']!r}; fix its fmt")
        new[eid] = text
    return new, missing, promoted, skipped


def para_elements(prs):
    """Map 'sNN/<shape>/...' paragraph prefixes to a:p elements, mirroring inventory.py ids."""
    paras, charts = {}, {}
    for sid, slide in enumerate(prs.slides, 1):
        for sh in walk(slide.shapes):
            base = f"s{sid:02d}/{sh.shape_id}"
            if getattr(sh, "has_table", False) and sh.has_table:
                for r, row in enumerate(sh.table.rows):
                    for c, cell in enumerate(row.cells):
                        for pi, p in enumerate(cell.text_frame._txBody.iterfind(A + "p")):
                            paras[f"{base}/r{r}c{c}/p{pi}"] = p
            elif getattr(sh, "has_chart", False) and sh.has_chart:
                charts[f"{base}/chart"] = sh.chart
                cs = sh.chart._chartSpace
                t = cs.find(f".//{C}title")
                if t is not None and sh.chart.has_title:
                    for pi, p in enumerate(t.iter(A + "p")):
                        paras[f"{base}/chart/title/p{pi}"] = p
                for ai, ax in enumerate(cs.iter(C + "valAx", C + "catAx", C + "dateAx")):
                    at = ax.find(C + "title")
                    if at is not None:
                        for pi, p in enumerate(at.iter(A + "p")):
                            paras[f"{base}/chart/axis{ai}/p{pi}"] = p
            elif sh.has_text_frame:
                for pi, p in enumerate(sh.text_frame._txBody.iterfind(A + "p")):
                    paras[f"{base}/p{pi}"] = p
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame is not None:
            for pi, p in enumerate(slide.notes_slide.notes_text_frame._txBody.iterfind(A + "p")):
                paras[f"s{sid:02d}/notes/p{pi}"] = p
    return paras, charts


def replace_in_paragraph(p, edits):
    """edits: list of (k, old, new). Replace the k-th number of the paragraph, right to left, inside the runs."""
    texts = [(child, child.find(A + "t")) for child in p if child.tag in (A + "r", A + "fld")]
    full = "".join((t.text or "") if t is not None else "" for _, t in texts)
    matches = list(NUMBER.finditer(full))
    bounds, pos = [], 0
    for _, t in texts:
        n = len(t.text or "") if t is not None else 0
        bounds.append((pos, pos + n))
        pos += n
    for k, old, newtext in sorted(edits, key=lambda x: -x[0]):
        if k >= len(matches) or matches[k].group(0) != old:
            raise ValueError(f"number {k} is {matches[k].group(0) if k < len(matches) else None!r}, expected {old!r}")
        a, b = matches[k].span()
        first = True
        for (start, end), (_, t) in zip(bounds, texts):
            if t is None or end <= a or start >= b:
                continue
            s = t.text or ""
            lo, hi = max(a, start) - start, min(b, end) - start
            t.text = s[:lo] + (newtext if first else "") + s[hi:]
            first = False
    return full


def chart_updates(chart, cid, new, fmap):
    """Rebuild a chart's data with mapped categories, series names and values; keep everything else as it was."""
    plot = chart.plots[0]
    cats = [str(c) for c in plot.categories]
    for j, label in enumerate(cats):
        for k, mt in reversed(list(enumerate(NUMBER.finditer(label)))):
            nid = f"{cid}/cat{j}/m{k}"
            if nid in new:
                if mt.group(0) != fmap["entries"][nid]["old"]:
                    raise ValueError(f"{nid}: category number {mt.group(0)!r} != {fmap['entries'][nid]['old']!r}")
                label = label[:mt.start()] + new[nid] + label[mt.end():]
        cats[j] = label
    cd = CategoryChartData()
    cd.categories = cats
    changed = []
    for i, se in enumerate(s for pl in chart.plots for s in pl.series):
        name = se.name or ""
        for k, mt in reversed(list(enumerate(NUMBER.finditer(name)))):
            nid = f"{cid}/ser{i}/name/m{k}"
            if nid in new:
                name = name[:mt.start()] + new[nid] + name[mt.end():]
        vals = []
        for j, v in enumerate(se.values):
            pid = f"{cid}/ser{i}/pt{j}"
            if pid in new:
                if v is None or abs(float(fmap["entries"][pid]["old"]) - v) > 1e-6:
                    raise ValueError(f"{pid}: chart value {v} != {fmap['entries'][pid]['old']}")
                changed.append((pid, fmap["entries"][pid]["old"], new[pid]))
                v = float(new[pid])
            vals.append(v)
        cd.add_series(name, vals)
    chart.replace_data(cd)
    return changed, cats


def next_free(path):
    if not path.exists():
        return path
    for letter in string.ascii_lowercase[1:]:
        cand = path.with_name(f"{path.stem}{letter}{path.suffix}")
        if not cand.exists():
            return cand
    sys.exit("no free output name")


RANGE = re.compile(r"(\$?\d[\d,]*(?:\.\d+)?)\s?(%|M|MW|kW)? to (\$?\d[\d,]*(?:\.\d+)?)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="a COPY of the deck, e.g. outputs/deck/v3/source_copy.pptx")
    ap.add_argument("--map", default=str(Path(__file__).with_name("fact_map.yaml")))
    ap.add_argument("--out", default=str(OUT_DIR / "D4G_v3.pptx"))
    ap.add_argument("--dry-run", action="store_true", help="print the change log; write nothing")
    args = ap.parse_args()
    src = Path(args.source).resolve()
    if "Downloads" in src.parts:
        sys.exit("refusing: the source is in ~/Downloads; copy it to outputs/deck/v3 first")
    fmap = yaml.safe_load(Path(args.map).read_text())
    res = Resolver(fmap)
    new, missing, promoted, skipped = compute(fmap, res)
    if missing:
        print("REFUSED: mapped keys missing from facts.json or config (nothing written):")
        for key, ids in sorted(missing.items()):
            print(f"  {key}  <- {', '.join(ids)}")
        sys.exit(2)

    prs = Presentation(str(src))
    paras, charts = para_elements(prs)
    log, by_para, chart_ids = [], {}, set()
    for eid, text in new.items():
        e = fmap["entries"][eid]
        if "/chart/" in eid and ("/cat" in eid or "/ser" in eid):
            chart_ids.add(eid.split("/chart/")[0] + "/chart")
            continue
        pkey, k = eid.rsplit("/m", 1)
        by_para.setdefault(pkey, []).append((int(k), str(e["old"]), text, eid))
    for pkey, edits in sorted(by_para.items()):
        if pkey not in paras:
            sys.exit(f"REFUSED: paragraph {pkey} not found in {src.name} (deck changed since the inventory?)")
        before = "".join(t.text or "" for t in paras[pkey].iter(A + "t"))
        want = fmap["entries"][edits[0][3]].get("text", "")
        if want and not before.replace("\v", " / ").startswith(want[:120].rstrip()):
            sys.exit(f"REFUSED: paragraph {pkey} text changed since the inventory:\n  now  {before[:120]!r}\n  map  {want[:120]!r}")
        replace_in_paragraph(paras[pkey], [(k, old, txt) for k, old, txt, _ in edits])
        after = "".join(t.text or "" for t in paras[pkey].iter(A + "t"))
        for k, old, txt, eid in sorted(edits):
            log.append((int(eid[1:3]), eid, old, txt))
        for mt in RANGE.finditer(after):
            lo, hi = (float(x.lstrip("$").replace(",", "")) for x in (mt.group(1), mt.group(3)))
            if lo > hi:
                print(f"WARNING range order flipped in {pkey}: '{mt.group(0)}'  (full: {after[:140]!r})")
    for cid in sorted(chart_ids):
        changed, cats = chart_updates(charts[cid], cid, new, fmap)
        for eid in sorted(i for i in new if i.startswith(cid + "/cat") or "/name/" in i and i.startswith(cid)):
            log.append((int(eid[1:3]), eid, str(fmap["entries"][eid]["old"]), new[eid]))
        log += [(int(p[1:3]), p, o, n) for p, o, n in changed]

    print(f"peak source: {res.selected}")
    print(f"{'slide':>5}  {'id':32s} {'old':>12s} -> new")
    same = 0
    for sid, eid, old, txt in sorted(log):
        if old == txt:
            same += 1
            continue
        print(f"{sid:5d}  {eid:32s} {old:>12s} -> {txt}")
    print(f"{len(log)} numbers written, {len(log) - same} changed, {same} unchanged")
    for eid in promoted:
        print(f"PENDING now present, applied: {eid} = {new[eid]}")
    for eid, key in skipped:
        print(f"PENDING skipped (key {key} not written yet): {eid} stays {fmap['entries'][eid]['old']!r}")
    for eid, e in fmap["entries"].items():
        if e["status"] == "no-source":
            print(f"NO SOURCE, left as is: {eid} {e['old']!r}  ({e.get('note', '')})")
    for c in fmap.get("claims", []):
        try:
            ok = res.claim(c)
        except Missing as err:
            print(f"CLAIM not checked ({err} missing): {c['where']}: {c['says']}")
            continue
        if not ok:
            print(f"CLAIM NO LONGER HOLDS, reword: {c['where']}: {c['says']}")
    for eid, e in fmap["entries"].items():
        if e["status"] == "picture" and e.get("numbers_in_image"):
            print(f"PICTURE untouched, needs a new image or a caption: {eid}: {e['shows'][:80]} [{e['numbers_in_image'][:80]}]")
    if args.dry_run:
        print("dry run: nothing written")
        return
    out = next_free(Path(args.out).resolve())
    if "Downloads" in out.parts or out == src:
        sys.exit("refusing to write into ~/Downloads or over the source")
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
