"""Label tests: the face of every demo view carries only headline, numbers, control labels and state names; every
assumption, placeholder and range sits one click away in that view's closed "How this is computed".

What: in the template, each view function builds exactly one disclosure, each assumed number carries the one est.
      marker (or the Synthetic network tag) that opens its own view's disclosure, and the placeholder, scenario,
      rating, grouping, range and synthetic-transformer wording lives inside a disclosure, not on the face;
      rendered in headless Chrome, every view has one closed disclosure titled "How this is computed", every
      marker opens it, and the visible words per view stay under the labeling-pass cap.
Why:  Gio's rule for the app, "if its assumptions, make it into a drop down": an assumed price or a synthetic
      network must stay labeled (audit MUST_FIX 3), but by a marker and the disclosure, not by sentences on
      the face. A test that only looked for the word "placeholder" anywhere would pass a page that shouts it.
How:  the template text is split per view function; the rendered check reuses checks/label_inventory.py.
"""
import re
from checks import label_inventory
from ewu.demo_page import TEMPLATE

PAGE = TEMPLATE.read_text()
VIEWS = ("deck", "network", "overview", "inventory", "flag", "protect", "upgrade", "money")
FACE_WORDS_MAX = 100   # visible words per view, side panel included, after the 2026-11-13 labeling pass


def view_source(view):
    start = PAGE.index(f"function step{view.capitalize()}(")
    return PAGE[start:PAGE.index("\nfunction ", start + 10)]


def split(source):
    """(face, disclosure) text of one view function: what sits before and inside its how(...) call."""
    at = source.index("${how(")
    return source[:at], source[at:]


def test_each_view_builds_one_disclosure_and_marks_its_assumed_numbers():
    for view in VIEWS:
        source = view_source(view)
        assert source.count("${how(") == 1, view
        face, how = split(source)
        assert f'how("{view}"' in how, view
        marks = re.findall(r'est\("(\w+)"\)|openHow\(\'(\w+)\'\)', face)
        assert marks and all(view in m for m in marks), (view, marks)


def test_assumptions_live_in_the_disclosure_not_on_the_face():
    moved = {"deck": ["kW read as kVA", "our replica of the teammate's model", "GIVEN, from the teammate", "ASSUMED", "Money is v3's basis"],
             "money": ["Scaling, assumption", "present value factors", "customer lease"],
             "overview": ["deck v3's four steps", "distribution planners"],
             "network": ["GIVEN", "illustrative split", "kW read as kVA"],
             "inventory": ["not a real customer", "Confidence for each technology"],
             "protect": ["every day's excess", "no separate cold snap test"],
             "flag": ["EV charging unmanaged"], "upgrade": ["Still overloaded after"]}
    for view, phrases in moved.items():
        face, how = split(view_source(view))
        for phrase in phrases:
            assert phrase in how, (view, phrase)
            assert phrase not in face, (view, phrase)
    controls = PAGE[PAGE.index("function caseControls("):PAGE.index("const caseNote")]
    assert "ev_share" not in controls and "today's peak" not in controls
    assert "${caseNote()}" in PAGE[PAGE.index("const synthetic"):] and "caseNote()}`)}`;" in view_source("money")


def test_rendered_views_keep_the_rule_and_the_word_cap():
    page = label_inventory.page_from(PAGE)
    from ewu import ROOT
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs" / "private") as tmp:
        found = label_inventory.measure(page, Path(tmp), Path(tmp) / "profile")
    assert set(found) == set(VIEWS)
    assert label_inventory.rule_problems(found) == []
    for view, f in found.items():
        assert f["view"]["words"] + f["side"]["words"] <= FACE_WORDS_MAX, (view, f["view"]["blocks"])
        assert f["view"]["folded"] > f["view"]["words"], view   # more is one click away than on the face
