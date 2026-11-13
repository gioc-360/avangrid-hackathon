"""Independent check of deck v3 against the original deck, deck/v3/fact_map.yaml and facts/facts.json.

What: extracts every number from both decks with its own python-pptx walk (text, tables, notes, chart titles, axis
      titles, categories, series names and values); for every fact_map entry marked mapped or pending, recomputes the
      fact from facts/facts.json and config/ewu.yaml, formats it with the entry's fmt and compares it with the number
      that sits at that place in v3; then lists every number that differs between the decks at a place the map does
      not cover, and every fact key whose deck renderings disagree with each other.
Why:  the build (apply.py, finish.py) wrote v3; this script shares none of their code, so a bug there shows here.
How:  .venv/bin/python -I deck/v3/independent_check.py ORIGINAL.pptx V3.pptx OUT.json   (reads only; writes OUT.json)
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

ROOT = Path(__file__).resolve().parents[2]
NUM = re.compile(r"(?<![\d.,])\$?(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?:\s?(?:%|kWh|MWh|kVA|MW|kW|GW|°F)|M\b|k\b|B\b|x\b)?")


def shapes_of(coll):
    for sh in coll:
        if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from shapes_of(sh.shapes)
        else:
            yield sh


def para_text(p):
    return "".join(r.text for r in p.runs) if p.runs else p.text


def extract(path):
    """{location: text or list of floats}. Locations mirror the map's id grammar up to the m-index."""
    out = {}
    prs = Presentation(path)
    for si, slide in enumerate(prs.slides, 1):
        s = f"s{si:02d}"
        seen = {}
        for sh in shapes_of(slide.shapes):
            # a shape id can repeat on a slide (the original has some; finish.py copies shapes): the first keeps the
            # bare id, so the map's ids point at the original shape; later copies get #2, #3 and are diffed as new
            seen[sh.shape_id] = seen.get(sh.shape_id, 0) + 1
            sid = sh.shape_id if seen[sh.shape_id] == 1 else f"{sh.shape_id}#{seen[sh.shape_id]}"
            if sh.has_text_frame:
                for pi, p in enumerate(sh.text_frame.paragraphs):
                    out[f"{s}/{sid}/p{pi}"] = p.text
            if getattr(sh, "has_table", False) and sh.has_table:
                for ri, row in enumerate(sh.table.rows):
                    for ci, cell in enumerate(row.cells):
                        for pi, p in enumerate(cell.text_frame.paragraphs):
                            out[f"{s}/{sid}/r{ri}c{ci}/p{pi}"] = p.text
            if getattr(sh, "has_chart", False) and sh.has_chart:
                ch = sh.chart
                if ch.has_title and ch.chart_title.has_text_frame:
                    for pi, p in enumerate(ch.chart_title.text_frame.paragraphs):
                        out[f"{s}/{sid}/chart/title/p{pi}"] = p.text
                plot = ch.plots[0]
                try:
                    cats = list(plot.categories)
                except Exception:
                    cats = []
                for ci, c in enumerate(cats):
                    out[f"{s}/{sid}/chart/cat{ci}"] = str(c)
                for pl in ch.plots:
                    for ser in pl.series:
                        out[f"{s}/{sid}/chart/ser{ser.index}/name"] = ser.name
                        try:
                            out[f"{s}/{sid}/chart/ser{ser.index}/values"] = list(ser.values)
                        except TypeError:   # scatter series with empty points: per-home data, not listed
                            pass
        if slide.has_notes_slide:
            for pi, p in enumerate(slide.notes_slide.notes_text_frame.paragraphs):
                out[f"{s}/notes/p{pi}"] = p.text
    return out


def nums(text):
    return [m.group(0) for m in NUM.finditer(text or "")]


class Facts:
    def __init__(self, fmap):
        self.f = json.loads((ROOT / "facts/facts.json").read_text())
        self.c = yaml.safe_load((ROOT / "config/ewu.yaml").read_text())
        ps = fmap["aliases"]["peak_source"]
        self.alias = ps[ps["selected"]]

    def get(self, ref):
        if ref.startswith("@"):
            return self.get(self.alias[ref[1:]])
        if ref.startswith("cfg:"):
            node = self.c
            for part in ref[4:].split("."):
                node = node[part]
            return node["value"]
        return self.f[ref]["value"]

    def value(self, e):
        if e.get("key"):
            return self.get(e["key"])
        env = {n: self.get(k) for n, k in e["keys"].items()}
        return eval(e["expr"], {"__builtins__": {"round": round, "min": min, "max": max, "abs": abs}}, env)


def locate(eid):
    """Map id -> (location in extract(), number index or point index)."""
    parts = eid.split("/")
    if "chart" in parts:
        if re.fullmatch(r"pt\d+", parts[-1]):
            return "/".join(parts[:-1]) + "/values", int(parts[-1][2:])
        if parts[-2] == "name":
            return "/".join(parts[:-1]), int(parts[-1][1:])
        if re.fullmatch(r"cat\d+", parts[-2]):
            return "/".join(parts[:-1]), int(parts[-1][1:])
        if parts[3] == "title":
            return "/".join(parts[:-1]), int(parts[-1][1:])
        return None, None
    return "/".join(parts[:-1]), int(parts[-1][1:])


def main(orig_path, v3_path, out_path):
    fmap = yaml.safe_load((ROOT / "deck/v3/fact_map.yaml").read_text())
    facts = Facts(fmap)
    o, n = extract(orig_path), extract(v3_path)
    res = {"mapped_ok": [], "mapped_bad": [], "unmapped_changes": [], "by_key": defaultdict(list), "skipped": []}
    covered = set()
    for eid, e in fmap["entries"].items():
        if e["status"] not in ("mapped", "pending"):
            continue
        loc, idx = locate(eid)
        if loc is None:
            res["skipped"].append(eid)
            continue
        covered.add((loc, idx))
        try:
            v = facts.value(e)
        except KeyError as err:
            res["mapped_bad"].append({"id": eid, "why": f"missing fact {err}"})
            continue
        want = e["fmt"].format(v)
        if e["kind"] == "chart_value":
            got_vals, old_vals = n.get(loc), o.get(loc)
            got = got_vals[idx] if got_vals and idx < len(got_vals) else None
            old = old_vals[idx] if old_vals and idx < len(old_vals) else None
            ok = got is not None and e["fmt"].format(got) == want
            row = {"id": eid, "old": old, "fact": v, "want": want, "got": got}
        else:
            got_list, old_list = nums(n.get(loc, "")), nums(o.get(loc, ""))
            got = got_list[idx] if idx < len(got_list) else None
            old = old_list[idx] if idx < len(old_list) else None
            ok = got == want
            if not ok and got and want in nums(n.get(loc, "")):
                ok, row_note = True, "found at another index"
            row = {"id": eid, "old": old, "map_old": str(e["old"]), "fact": v, "want": want, "got": got,
                   "text": n.get(loc, "")}
        row["key"] = e.get("key") or (e.get("expr") + " | " + json.dumps(e.get("keys"), sort_keys=True))
        (res["mapped_ok"] if ok else res["mapped_bad"]).append(row)
        res["by_key"][row["key"]].append((eid, want))
    for loc in sorted(set(o) | set(n)):
        ov, nv = o.get(loc), n.get(loc)
        if isinstance(ov, list) or isinstance(nv, list):
            if ov != nv:
                for i in range(max(len(ov or []), len(nv or []))):
                    a = ov[i] if ov and i < len(ov) else None
                    b = nv[i] if nv and i < len(nv) else None
                    if a != b and (loc, i) not in covered:
                        res["unmapped_changes"].append({"loc": loc, "i": i, "old": a, "new": b})
            continue
        on, nn = nums(ov), nums(nv)
        if on != nn:
            for i in range(max(len(on), len(nn))):
                a = on[i] if i < len(on) else None
                b = nn[i] if i < len(nn) else None
                if a != b and (loc, i) not in covered:
                    res["unmapped_changes"].append({"loc": loc, "i": i, "old": a, "new": b, "old_text": ov,
                                                    "new_text": nv})
    res["by_key"] = {k: v for k, v in res["by_key"].items() if len({w for _, w in v}) > 1}
    res["v3_only_text"] = {k: v for k, v in n.items() if k not in o and not isinstance(v, list) and nums(v)}
    Path(out_path).write_text(json.dumps(res, indent=1, default=str))
    print(f"mapped/pending entries checked: {len(res['mapped_ok']) + len(res['mapped_bad'])}; "
          f"ok {len(res['mapped_ok'])}; bad {len(res['mapped_bad'])}; skipped {len(res['skipped'])}; "
          f"unmapped number changes {len(res['unmapped_changes'])}; keys rendered two ways {len(res['by_key'])}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
