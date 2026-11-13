"""Render a .pptx to PDF and PNG pages with Microsoft PowerPoint. Copied from
~/gilead-case-reader/team-deck/v4d/render_ppt.py and hardened for this deck: it acts only on the presentation it opened,
by name, and refuses any file whose name looks like a deck the user may have open (D4G, EWU_engine).
PowerPoint is sandboxed, so it saves the PDF into its own container and this script moves it out.
    .venv/bin/python deck/v3/render_ppt.py /abs/path/render_copy.pptx /abs/out_dir"""
import os, shutil, subprocess, sys, time

GUARD = ("D4G", "EWU_engine", "Final Submission")

pptx, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
name = os.path.basename(pptx)
if any(g.lower() in name.lower() for g in GUARD):
    sys.exit(f"refusing: {name} carries a deck name the user may have open; render a renamed copy")
os.makedirs(out, exist_ok=True)
box = os.path.expanduser("~/Library/Containers/com.microsoft.Powerpoint/Data/Documents")
tmp = os.path.join(box, f"render_{int(time.time())}.pdf")
script = f'''with timeout of 300 seconds
tell application "Microsoft PowerPoint"
  open POSIX file "{pptx}"
  delay 2
  set p to presentation "{name}"
  save p in POSIX file "{tmp}" as save as PDF
  close p saving no
end tell
end timeout'''
subprocess.run(["osascript", "-e", script], check=True)
pdf = os.path.join(out, "deck.pdf")
shutil.move(tmp, pdf)
for f in os.listdir(out):
    if f.startswith("p-") and f.endswith(".png"):
        os.remove(os.path.join(out, f))
subprocess.run(["pdftoppm", "-png", "-r", "80", pdf, os.path.join(out, "p")], check=True)
print("rendered", len([f for f in os.listdir(out) if f.startswith("p-")]), "pages to", out)
