"""Video build tests: the film's words, markers, plan, pointer pace and outputs follow the brief and house rules.

What: the narration's spoken form carries no digit; every marker label is at most 8 words and traces to a fact
      or config input (a planted wrong number is caught); the plan lands inside 3:30 to 4:30 with one marker
      and one card at a time, every pointer move anchored to a word the script really says, every step reached
      by a side panel click, and every script row in exactly one take; the pointer's top speed stays under
      800 film px a second; the terminal check catches an edited number; labels never cover their box or the
      side panel; versions never overwrite; video media and the compiled pointer tool stay out of git; every
      video/ module passes the house rules.
Why:  the film goes to Avangrid; each promise in its brief fails a test the moment it breaks, without a take.
How:  imports the video modules directly (no Chrome, no screen recording, no ffmpeg needed).
"""
import subprocess, sys
from pathlib import Path
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "video"))
import build, look, plan, script_rows, term_take  # noqa: E402
from align import glide_lag, text_blocks  # noqa: E402
from path import CARDS, MARKERS, PATH, TAKES  # noqa: E402
from takes import VMAX, glide_seconds  # noqa: E402
from tests.test_house_rules import house_rule_breaks, line_cap  # noqa: E402

ROWS, TOTAL = plan.layout(script_rows.rows(), recorded={})


def test_script_rows_speak_every_number_in_words():
    assert script_rows.selftest() == 0
    assert script_rows.spoken("26% of 3,000 at -5 F") == "twenty six percent of three thousand at minus five degrees Fahrenheit"


def test_marker_labels_are_short_and_traced(tmp_path):
    labels = [m[-1] for m in MARKERS]
    assert all(len(lb.split()) <= 8 for lb in labels)
    doc = tmp_path / "labels.md"
    doc.write_text("# labels\n\n" + "\n\n".join(labels + [f"{c[3]}: {c[4]}" for c in CARDS]) + "\n")
    run = subprocess.run([sys.executable, str(ROOT / "checks/trace_numbers.py"), str(doc)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout[-400:]
    bad = tmp_path / "bad.md"
    bad.write_text("# labels\n\nShift fixes 21.57% of all transformers\n")
    assert subprocess.run([sys.executable, str(ROOT / "checks/trace_numbers.py"), str(bad)], capture_output=True).returncode == 1


def test_plan_fits_the_window_one_cue_at_a_time():
    assert 210 <= TOTAL <= 270
    assert plan.overlaps([m[:2] for m in plan.timed_markers(ROWS)]) == []
    assert plan.overlaps([c[:2] for c in plan.timed_cards(ROWS)]) == []
    acts = plan.actions(ROWS)
    assert len(acts) == len(PATH)
    for a in acts:
        r = ROWS[a["row"]]
        assert r["t0"] <= a["at"] <= r["t0"] + r["dur"], a


def test_every_step_is_reached_from_the_side_panel():
    navs = [t for *_, kind, t in PATH if kind == "nav"]
    assert len(navs) == 6 and all("aside a.step-link" in t for t in navs)
    assert not any(kind == "scroll" for *_, kind, _ in PATH)


def test_every_row_is_in_exactly_one_take():
    owned = sorted(r for rows, *_ in TAKES.values() for r in rows)
    assert owned == list(range(1, len(ROWS) - 1))


def test_pointer_top_speed_stays_under_800_film_px():
    film_per_point = 1920 / 1800
    assert VMAX * film_per_point <= 800
    for d in (20, 150, 400, 900, 1500):
        secs = glide_seconds(d)
        assert d / secs * film_per_point <= 800
        assert 0 < glide_lag(d) < secs


def test_terminal_check_catches_an_edited_number():
    lines = (ROOT / "docs/demo/cli_output.txt").read_text().splitlines()[1:]
    typed = [["out", 1.0, ln] for ln in lines]
    assert term_take.screen_check(typed) == []
    assert any("Flag" in p for p in term_take.screen_check([[k, t, ln.replace("26.00", "25.00")] for k, t, ln in typed]))


def test_text_blocks_split_on_blank_lines():
    fr = np.zeros((300, 600, 3), np.uint8)
    for y in (20, 60, 180, 220, 260):
        fr[y:y + 24, 40:400] = 230
    blocks = text_blocks(fr)
    assert [(b[1], b[3]) for b in blocks] == [(20, 83), (180, 283)]


def test_labels_never_cover_their_box_or_the_side_panel():
    frame = np.full((1080, 1920, 3), 246, np.uint8)
    box = (440, 100, 600, 150)
    x, y = look.place_label(box, (300, 50), frame)
    assert x >= look.PANEL_RIGHT
    assert x + 300 <= box[0] - 9 or x >= box[2] + 9 or y + 50 <= box[1] - 9 or y >= box[3] + 9


def test_versions_never_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "OUT", tmp_path)
    (tmp_path / "ewu_demo_v9.mp4").write_bytes(b"x")
    monkeypatch.setattr(sys, "argv", ["build.py", "--version", "9"])
    with pytest.raises(SystemExit):
        build.main()


def test_video_media_is_ignored_by_git():
    for p in ("outputs/video/ewu_demo_v2.mp4", "outputs/video/takes/v2/flag.mov", "outputs/video/ewu_demo_v2_cues.wav",
              "outputs/film.m4a", "outputs/deck/x.pptx", "video/rec/mouse"):
        assert subprocess.run(["git", "check-ignore", "-q", p], cwd=ROOT).returncode == 0, p


def test_video_modules_follow_the_house_rules():
    cap = line_cap()
    for path in sorted((ROOT / "video").glob("*.py")):
        assert house_rule_breaks(path, cap) == [], path.name
