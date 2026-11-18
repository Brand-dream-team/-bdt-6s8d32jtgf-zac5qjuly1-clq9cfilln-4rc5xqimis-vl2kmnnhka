"""Brand Dream Team preset 5: Pink Label.
Captions 2-3 words at a time in caps, pink text on solid black label boxes, centered just below the face.
Hook in the same style, bigger, at the top for the first seconds.
usage: python3 pink_label.py <project folder> [edit.json]   (run make_base.py first)"""
import json, os, subprocess, sys
import os as _os2, sys as _sys2
_sys2.path.insert(0, _os2.path.dirname(_os2.path.abspath(__file__)))
from fxquiet import quiet as _quiet
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from sdr import sdr_vf, TAGS
from PIL import ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(HERE, "..", "fonts")
WORK = os.path.abspath(sys.argv[1])
CFG = json.load(open(os.path.join(WORK, sys.argv[2] if len(sys.argv) > 2 else "edit.json")))
base = os.path.join(WORK, "base.mp4"); assert os.path.exists(base), "run scripts/make_base.py on this project first"
words = [w for w in json.load(open(os.path.join(WORK, "timeline_words.json"))) if w["w"].strip()]
TOTAL = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", base], capture_output=True, text=True).stdout)
W, H = 1080, 1920

def hx(h): h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
def ass(rgb, a=0): return "&H%02X%02X%02X%02X" % (a, rgb[2], rgb[1], rgb[0])
PAL = CFG.get("palette", {})
TEXT = hx(CFG.get("label_text", PAL.get("accent", "#F79EBB")))
if sum(TEXT) < 200:                                       # text must read on black: lighten their accent
    import brand as _b; TEXT = _b.Brand(CFG).light
    while sum(TEXT) < 200: TEXT = _b.mix(TEXT, (255, 255, 255), 0.12)
BOX = hx(CFG.get("label_box", "#000000"))
CAP_Y = CFG.get("caption_y", 1250)                        # center of the caption label
SIZE = {"small": 60, "medium": 70, "large": 80}.get(CFG.get("caption_size", "medium"), 70)
FONT = "BDT Mont Bold"
import brand as _bb; _BB = _bb.Brand(CFG)
def _BRF(name, size):
    p, w = _BB.map(name, own=True); return _bb.load(p, size, w)
fnt = _BRF("BDTMontBold.ttf", SIZE)

# ---- group: 2-3 words, max ~16 characters, break on pauses
groups, cur = [], []
for w in words:
    if cur:
        txt = " ".join(x["w"] for x in cur + [w])
        if len(cur) >= 3 or len(txt) > 16 or w["t"] - cur[-1]["te"] > 0.35:
            groups.append(cur); cur = []
    cur.append(w)
if cur: groups.append(cur)

def ts(x):
    x = max(0, x); return f"{int(x//3600)}:{int(x%3600//60):02d}:{x%60:05.2f}"

hook = CFG.get("hook", {})
hook_end = hook.get("dur", 2.8) if hook else 0
ev = []
pad = int(SIZE * 0.32)
for i, g in enumerate(groups):
    a = g[0]["t"]; nxt = groups[i+1][0]["t"] if i + 1 < len(groups) else TOTAL
    b = max(a + 0.4, min(nxt, g[-1]["te"] + 0.5))
    txt = " ".join(x["w"] for x in g).upper()
    ev.append(f"Dialogue: 1,{ts(a)},{ts(b)},Lab,,0,0,0,,{{\\an5\\pos(540,{CAP_Y})\\fscx104\\fscy104\\t(0,90,\\fscx100\\fscy100)}}{txt}")
HFN = ("\\fn" + _bb.ass_name(_BB.hook_title[0]) + "\\b0\\i0") if _BB.hook_title else ""
if hook:
    lines = [l for l in (hook.get("line1", ""), hook.get("line2", "")) if l]
    y = CFG.get("hook_y", 360)
    for k, l in enumerate(lines):
        ev.append(f"Dialogue: 2,{ts(0.05)},{ts(hook_end)},Hook,,0,0,0,,{{\\an5\\pos(540,{y + k * int(SIZE*1.62)})\\fad(80,160){HFN}}}{l.upper()}")

assf = os.path.join(WORK, "caps_pink_label.ass")
open(assf, "w").write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Lab,{FONT},{SIZE},{ass(TEXT)},{ass(TEXT)},{ass(BOX)},{ass(BOX)},0,0,0,0,100,100,1,0,3,{pad},0,5,60,60,0,1
Style: Hook,{FONT},{int(SIZE*1.18)},{ass(TEXT)},{ass(TEXT)},{ass(BOX)},{ass(BOX)},0,0,0,0,100,100,1,0,3,{pad+4},0,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(_quiet(ev, WORK)) + "\n")

out = os.path.join(WORK, "out"); os.makedirs(out, exist_ok=True)
final = os.path.join(out, CFG.get("output", "edit.mp4").replace(".mp4", "-pink-label.mp4"))
ap = assf.replace(":", "\\:")
import brand as _b; _BF = _b.patch_ass(ap, _b.Brand(CFG), F)   # their own brand fonts in the captions, if they have them
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", base, "-vf", f"ass='{ap}':fontsdir='{_BF}'", "-c:v", "libx264", *TAGS, "-preset", "medium", "-crf", "20",
                "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", final], check=True)
print("ok", final, len(groups), "captions")
