"""Face box tests: the punch-in framing of Kayin's box in the final film follows Gio's decision of 11-13.

What: the tight crop is 0.8 of the medium crop, the box's 8:9 shape, even numbers, inside her 1280 x 720 frame, and
      keeps her measured face centre where the medium crop has it; every audio seam changes framing (medium, tight,
      medium, tight, medium); punch mode drops only the four seam hides and keeps both corner-move hides; hide mode
      renders EWU_demo_final_b's box (one framing, every hide); the compiled face finder stays out of git.
Why:  a seam with no framing change shows her face jump; a seam that keeps its hide makes the box blink.
How:  imports video/v4_edit_face.py directly; no ffmpeg, no film needed.
"""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "video"))
import v4_edit_face as F  # noqa: E402
import v4_edit_plan as P  # noqa: E402

HIDES = [(s - P.HIDE_HALF, s + P.HIDE_HALF, "audio seam") for s in P.seams()] + [
    (130.28, 131.48, "box moves to the right of the terminal table"), (145.28, 146.48, "box moves back to bottom left")]


def test_tight_crop_is_a_punch_in_on_her_face():
    mw, mh, mx, my = F.crop_numbers(F.FRAMINGS["medium"])
    tw, th, tx, ty = F.crop_numbers(F.FRAMINGS["tight"])
    assert abs(tw / mw - F.PUNCH) < 0.01 and abs(th / mh - F.PUNCH) < 0.01
    assert tw * 9 == th * 8 and all(v % 2 == 0 for v in (tw, th, tx, ty))
    assert tx >= 0 and ty >= 0 and tx + tw <= 1280 and ty + th <= 720
    cx, cy = F.FACE_CENTRE
    assert abs((cx - mx) / mw * P.BOX_W - (cx - tx) / tw * P.BOX_W) <= 2
    assert abs((cy - my) / mh * P.BOX_H - (cy - ty) / th * P.BOX_H) <= 2


def test_every_audio_seam_changes_framing():
    assert len(F.SPAN_FRAMING) == len(P.KEEP)
    crops = F.span_crops("punch")
    assert all(crops[i] != crops[i + 1] for i in range(len(crops) - 1))


def test_punch_mode_keeps_only_the_corner_move_hides():
    kept = F.face_hides(HIDES, "punch")
    assert [h[2] for h in kept] == [h[2] for h in HIDES[-2:]]


def test_hide_mode_renders_the_b_box():
    assert F.span_crops("hide") == [P.FACE_CROP] * len(P.KEEP)
    assert F.face_hides(HIDES, "hide") == HIDES


def test_face_finder_binary_is_ignored_by_git():
    assert subprocess.run(["git", "check-ignore", "-q", "video/rec/face"], cwd=ROOT).returncode == 0
