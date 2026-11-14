"""No deck words: nothing a viewer of the app or of `bin/ewu` sees names the deck or its version.

What: renders the demo page in every state checks/demo_check.py renders (each state fills every view, the "How
      this is computed" dropdowns, the controls and the transformer panel) and reads its visible text, aria-labels,
      hover titles and tab title; runs the printouts checks/terms_check.py runs plus the help of every command;
      scans every string literal in ewu/*.py that is not a docstring, so the long runs (sensitivity, robustness,
      cold snap, replica, recharge, arrays) are covered without running them. Fails on "deck" or "v3" as a whole
      word, any case. A planted page, printout and module must each be caught.
Why:  Gio, 2026-11-13: "in the app it shouldn't refer anything explicitly in deck like (not in v3); just note me
      here or note it in a markdown for final auditing checks". Where the app and the deck meet, and where
      they differ, lives in docs/DECK_AUDIT_NOTES.md instead.
How:  reuses terms_check's Chrome dump and CLI runner. Code identifiers, fact and config keys and file paths (a
      token with '.', '_', '/' or ':' inside it, such as ewu.deck.prices or profiles.deck.seed) are names, not
      words, and are skipped; a number's hover title is its fact key (the page's traceability promise), so the
      title of an element carrying data-key is skipped too.
"""
import ast, re
from pathlib import Path
from checks import terms_check

ROOT = Path(__file__).resolve().parent.parent
WORD = re.compile(r"\b(deck|v3)\b", re.I)
NAME = re.compile(r"\w[._/:]\w")


class SeenText(terms_check.PageText):
    """terms_check's visible text (the tab's <title> included) plus hover titles that are not a number's fact key."""

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)
        found = dict(attrs)
        if found.get("title") and "data-key" not in found:
            self.parts.append(f"\n{found['title']}\n")


def deck_words(text):
    """Every line of `text` that names the deck or v3 as a word, keys and paths aside."""
    return [line.strip() for line in text.splitlines()
            if any(WORD.search(token) and not NAME.search(token) for token in line.split())]


def page_seen_text(dom):
    reader = SeenText()
    reader.feed(dom)
    return reader.text()


def literal_strings(path):
    """(line, text) of every string constant in a module that is not a docstring and holds a space."""
    tree = ast.parse(Path(path).read_text())
    docs = {id(node.body[0].value) for node in ast.walk(tree)
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body
            and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant)}
    return [(node.lineno, node.value) for node in ast.walk(tree) if isinstance(node, ast.Constant)
            and isinstance(node.value, str) and id(node) not in docs and re.search(r"\s", node.value)]


def test_the_check_catches_planted_deck_words(tmp_path):
    assert deck_words("Loading limit 100% (not in deck v3)") and deck_words("Money is V3's basis")
    assert deck_words("EWU screen, deck-replica profile") and deck_words("the Deck setup")
    assert not deck_words("fact:ewu.deck.prices.factor profiles.deck.seed outputs/plan/battery decked v30")
    dom = '<p>Battery plan</p><span class="n" data-key="fact:ewu.deck.x" title="fact:ewu.deck.x">1</span><button title="Deck setup">x</button>'
    assert deck_words(page_seen_text(dom)) == ["Deck setup"]
    assert deck_words(page_seen_text("<html><head><title>Deck v3 demo</title></head><body></body></html>"))
    module = tmp_path / "planted.py"
    module.write_text('"""The deck profile, in a docstring: fine."""\nprint("EWU screen, deck profile")\nKEY = "ewu.deck.seconds"\n')
    assert [text for _, text in literal_strings(module) if deck_words(text)] == ["EWU screen, deck profile"]


def test_no_page_state_names_the_deck():
    from checks.demo_audit import read_sources, run_chrome
    from checks.demo_check import page_states
    from ewu import config_value, read_config
    from ewu.demo_page import PAGE, build_page
    import tempfile
    build_page(read_config())
    states = page_states(read_sources()) + [f"step={step}" for step in ("network", "money")]
    assert len(states) >= 2 * len(config_value("profiles.deck.overload_limit_options"))
    found = {}
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs" / "private") as profile:
        for state in states:
            text = page_seen_text(run_chrome(f"{PAGE.as_uri()}#{state}", profile, "--dump-dom"))
            assert "Electrify Without Upgrade" in text and "How this is computed" in text, state
            found.update({line: state for line in deck_words(text)})
    assert found == {}


def test_no_printout_or_help_names_the_deck():
    texts = terms_check.cli_texts()
    assert len(texts) > 10 and all("\nEXIT " not in t for t in texts.values()), [k for k, t in texts.items() if "\nEXIT " in t]
    assert {label: deck_words(text) for label, text in texts.items() if deck_words(text)} == {}


def test_no_string_a_command_can_print_names_the_deck():
    found = [f"{path.name}:{line}: {text[:90]}" for path in sorted((ROOT / "ewu").glob("*.py"))
             for line, text in literal_strings(path) if deck_words(text)]
    assert found == []
