"""Put the final demo film on the deck's Demo video slide: plays by itself when the slide opens, full screen.

What: on the slide whose header is "OUTPUT 1  |  DEMO VIDEO", replace the thumbnail picture (the placeholder)
      with the film embedded in the same box, the thumbnail as its poster frame; remove the play-button marks
      and the "Video placeholder" bar; set the slide's timing so the film starts automatically and full screen.
Why:  Gio wants the video on slide 12, running on its own, full screen; the deck is the only submission.
How:  .venv/bin/python -I deck/add_demo_video.py SRC.pptx FILM.mp4 POSTER.png OUT.pptx  (never overwrites OUT)
"""
import sys
from pathlib import Path
from lxml import etree
from pptx import Presentation

SRC, FILM, POSTER, OUT = (Path(a) for a in sys.argv[1:5])
if OUT.exists():
    sys.exit(f"refusing to overwrite {OUT}")
NS = "http://schemas.openxmlformats.org/presentationml/2006/main"

deck = Presentation(str(SRC))
slides = [s for s in deck.slides
          if any(sh.has_text_frame and sh.text_frame.text.strip() == "OUTPUT 1  |  DEMO VIDEO" for sh in s.shapes)]
assert len(slides) == 1, f"expected one demo video slide, found {len(slides)}"
slide = slides[0]
pics = [sh for sh in slide.shapes if sh.shape_type == 13]
assert len(pics) == 1, "expected one placeholder picture"
pic = pics[0]
box = (pic.left, pic.top, pic.width, pic.height)
drop = [pic] + [sh for sh in slide.shapes if sh.name in ("VID 303", "VID 304", "VID 305", "VID 306")]
assert any(sh.has_text_frame and "Video placeholder" in sh.text_frame.text for sh in drop), "placeholder bar not found"
for sh in drop:
    sh._element.getparent().remove(sh._element)

movie = slide.shapes.add_movie(str(FILM), *box, poster_frame_image=str(POSTER), mime_type="video/mp4")
sid = movie.shape_id
dur = sys.argv[5] if len(sys.argv) > 5 else "174000"
TIMING = f"""<p:timing xmlns:p="{NS}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>
<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>
<p:par><p:cTn id="3" fill="hold"><p:stCondLst><p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst><p:childTnLst>
<p:par><p:cTn id="4" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>
<p:par><p:cTn id="5" presetID="1" presetClass="mediacall" presetSubtype="0" fill="hold" nodeType="afterEffect"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>
<p:cmd type="call" cmd="playFrom(0.0)"><p:cBhvr><p:cTn id="6" dur="{dur}" fill="hold"/><p:tgtEl><p:spTgt spid="{sid}"/></p:tgtEl></p:cBhvr></p:cmd>
</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>
</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>
<p:video fullScrn="1"><p:cMediaNode vol="80000"><p:cTn id="7" fill="hold" display="0"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst></p:cTn><p:tgtEl><p:spTgt spid="{sid}"/></p:tgtEl></p:cMediaNode></p:video>
</p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>"""
root = slide._element
for old in root.findall(f"{{{NS}}}timing"):
    root.remove(old)
new = etree.fromstring(TIMING.replace("\n", ""))
ext = root.find(f"{{{NS}}}extLst")
(ext.addprevious(new) if ext is not None else root.append(new))
deck.save(str(OUT))
print(f"slide {deck.slides.index(slide) + 1}: film shape {sid} in box {box}, autoplay, full screen -> {OUT}")
