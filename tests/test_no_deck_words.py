"""No deck words: nothing a viewer of the app or of `bin/ewu` sees names the deck or its version.

What: renders the demo page in every state checks/demo_check.py renders (each state fills every view, the "How
      this is computed" dropdowns, the controls and the transformer panel) and reads its visible text, aria-labels,
      hover titles and tab title; runs the printouts checks/terms_check.py runs plus the help of every command;
      scans every string literal in ewu/*.py that is not a docstring, so the long runs (sensitivity, robustness,
      cold snap, replica, recharge, arrays) are covered without running them. Fails on "deck" or "v3" as a whole
      word, any case. A planted page, printout and module must each be caught. The same printouts, help and
      literals must not say "teammate" as a word (a fact's method string, passed to record(), may), and the
      battery plan screen must open with the meter matrix it read ("Read 33,757 homes, hourly meters, 8,760
      hours", the numbers checked against the matrix's own shape).
Why:  Gio, 2026-11-13: "in the app it shouldn't refer anything explicitly in deck like (not in v3); just note me
      here or note it in a markdown for final auditing checks". Where the app and the deck meet, and where
      they differ, lives in docs/DECK_AUDIT_NOTES.md instead. The film's judge, 2026-11-13: the terminal said
      "the teammate's" (an anonymous person) and never showed the 33,757 homes Kayin names over it.
How:  reuses terms_check's Chrome dump and CLI runner. Code identifiers, fact and config keys and file paths (a
      token with '.', '_', '/' or ':' inside it, such as ewu.deck.prices or profiles.deck.seed) are names, not
      words, and are skipped; a number's hover title is its fact key (the page's traceability promise), so the
      title of an element carrying data-key is skipped too.
"""
import ast, re
from pathlib import Path
import numpy as np
import pytest
from checks import terms_check

ROOT = Path(__file__).resolve().parent.parent
WORD = re.compile(r"\b(deck|v3)\b", re.I)
TEAMMATE = re.compile(r"\bteammates?\b", re.I)
NAME = re.compile(r"\w[._/:]\w")


class SeenText(terms_check.PageText):
    """terms_check's visible text (the tab's <title> included) plus hover titles that are not a number's fact key."""

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)
        found = dict(attrs)
        if found.get("title") and "data-key" not in found:
            self.parts.append(f"\n{found['title']}\n")


def deck_words(text, word=WORD):
    """Every line of `text` that names the deck or v3 (or `word`) as a word, keys and paths aside."""
    return [line.strip() for line in text.splitlines()
            if any(word.search(token) and not NAME.search(token) for token in line.split())]


def teammate_words(text):
    return deck_words(text, TEAMMATE)


@pytest.fixture(scope="module")
def cli_texts():
    """The printouts and every command's help, run once for the module."""
    return terms_check.cli_texts()


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


def test_no_printout_or_help_names_the_deck(cli_texts):
    texts = cli_texts
    assert len(texts) > 10 and all("\nEXIT " not in t for t in texts.values()), [k for k, t in texts.items() if "\nEXIT " in t]
    assert {label: deck_words(text) for label, text in texts.items() if deck_words(text)} == {}


def test_no_string_a_command_can_print_names_the_deck():
    found = [f"{path.name}:{line}: {text[:90]}" for path in sorted((ROOT / "ewu").glob("*.py"))
             for line, text in literal_strings(path) if deck_words(text)]
    assert found == []


def record_literal_ids(tree):
    """ids of the string constants inside record(...) calls: a fact's unit and method, stored, never printed."""
    return {id(c) for call in ast.walk(tree) if isinstance(call, ast.Call) and getattr(call.func, "id", None) == "record"
            for c in ast.walk(call) if isinstance(c, ast.Constant)}


def test_the_check_catches_planted_teammate_words(tmp_path):
    assert teammate_words("The teammate's EV start-hour shares") and teammate_words("from the Teammate (sha256 checked)")
    assert teammate_words("--tiers {teammate,ours}") and teammate_words("our teammates")
    assert not teammate_words("checks/teammate_audit.py profiles.deck.teammate_folder fact:teammate.audit.rerun the team's")
    module = tmp_path / "planted.py"
    module.write_text('record("k", 1, "", "teammate = their file")\nprint("from the teammate here")\n')
    tree = ast.parse(module.read_text())
    assert [t for t in printable_strings(module, tree) if teammate_words(t)] == ["from the teammate here"]


def printable_strings(path, tree=None):
    """literal_strings of a module minus the fact methods passed to record()."""
    tree = tree or ast.parse(Path(path).read_text())
    stored = record_literal_ids(tree)
    return [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and id(node) not in stored
            and (node.lineno, node.value) in set(literal_strings(path))]


def test_no_printout_or_help_says_teammate(cli_texts):
    assert {label: teammate_words(text) for label, text in cli_texts.items() if teammate_words(text)} == {}


def test_no_string_a_command_can_print_says_teammate():
    found = [f"{path.name}: {text[:90]}" for path in sorted((ROOT / "ewu").glob("*.py"))
             for text in printable_strings(path) if teammate_words(text)]
    assert found == []


def test_screen_opens_with_the_homes_it_read(cli_texts):
    import json
    from analysis.facts import FACTS
    from ewu import PROCESSED
    homes, hours = np.load(PROCESSED / "load_present.npy", mmap_mode="r").shape
    assert homes == json.loads(FACTS.read_text())["data.customers_usable"]["value"] == 33757 and hours == 8760
    lines = cli_texts["bin/ewu screen"].splitlines()
    assert f"Read {homes:,} homes, hourly meters, {hours:,} hours" in lines[:3], lines[:3]
