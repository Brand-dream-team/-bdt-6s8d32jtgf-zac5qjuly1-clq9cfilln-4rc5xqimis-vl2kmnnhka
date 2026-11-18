"""Brand Dream Team preset 6: Chunky Word.
One word at a time in huge, tightly spaced white letters above the head; key words switch to the creator's
brand color with a period. Optional name intro (big white line at the bottom with a script name in the brand color).
usage: python3 chunky_word.py <project folder> [edit.json]   (run make_base.py first)"""
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
def col(rgb, a=0): return "&H%02X%02X%02X%02X" % (a, rgb[2], rgb[1], rgb[0])
def lum(c): return 0.2126*c[0] + 0.7152*c[1] + 0.0722*c[2]
PAL = CFG.get("palette", {})
import brand as _b0
ACC = hx(CFG["word_accent"]) if CFG.get("word_accent") else _b0.Brand(CFG).light        # the creator's chosen brand color
WHITE = (255, 255, 255)
WORD_Y = CFG.get("word_y", 440)           # center of the big word (above the head)
BIG = CFG.get("word_size", 250)
FONT = "Inter Display"
import brand as _bb; _BB = _bb.Brand(CFG)
def _BRF(name, size):
    p, w = _BB.map(name, own=True); return _bb.load(p, size, w)
fbig = _BRF("InterDisplay-Bold.otf", BIG)
TRACK = -16
EMPH = set(x.lower() for x in CFG.get("emphasis", []))

def ts(x):
    x = max(0, x); return f"{int(x//3600)}:{int(x%3600//60):02d}:{x%60:05.2f}"
def clean(w): return w.strip(",.!?").lower() if w not in ("I",) and not w.startswith("I'") else w.strip(",.!?")
def find(phrase, after=0.0):
    seq = phrase.lower().split(); ws = [x["w"].lower().strip(",.!?") for x in words]
    for i in range(len(ws) - len(seq) + 1):
        if ws[i:i+len(seq)] == seq and words[i]["t"] >= after: return i
    return None

def in_frame(t): return False

ev = []
hook = CFG.get("hook", {})
hook_end = 0.0
HFN = ("\\fn" + _bb.ass_name(_BB.hook_title[0]) + "\\b0\\i0") if _BB.hook_title else ""
if hook:
    hook_end = hook.get("dur", 1.8)
    hl = [l for l in (hook.get("line1", ""), hook.get("line2", "")) if l]
    for k, l in enumerate(hl):
        sz = BIG * 0.5
        f = _BB.hook(int(sz))
        while f.getlength(l) > W - 120 and sz > 60: sz -= 6; f = _BB.hook(int(sz))
        c = ACC if k == len(hl) - 1 else WHITE
        y = WORD_Y - (len(hl) - 1) * sz * 0.55 + k * sz * 1.05
        ev.append(f"Dialogue: 1,{ts(0.0)},{ts(hook_end)},Big,,0,0,0,,{{\\an5\\pos(540,{y:.0f}){HFN}\\fs{sz:.0f}\\fsp{TRACK*sz/BIG:.1f}\\c{col(c)}\\fad(0,120)}}{l}")

name = CFG.get("name_intro")
name_span = None
if name:
    i = find(name["at"]) if name.get("at") else 0
    if i is not None:
        a = words[i]["t"]; b = min(TOTAL, a + name.get("dur", 2.2)); name_span = (a, b)
        line = name.get("line", "")
        sz = 175; f = _BRF("InterDisplay-Bold.otf", sz)
        while f.getlength(line) > W - 100 and sz > 70: sz -= 6; f = _BRF("InterDisplay-Bold.otf", sz)
        ev.append(f"Dialogue: 2,{ts(a)},{ts(b)},Big,,0,0,0,,{{\\an3\\pos(1030,1600)\\fs{sz}\\fsp{TRACK*sz/BIG:.1f}\\c{col(WHITE)}\\fad(60,150)}}{line}")
        if name.get("script"):
            ev.append(f"Dialogue: 3,{ts(a+0.15)},{ts(b)},Script,,0,0,0,,{{\\an3\\pos(1050,1840)\\c{col(ACC)}\\fad(120,150)}}{name['script']}")

for i, w in enumerate(words):
    a = w["t"]
    if a < hook_end: continue
    nxt = words[i+1]["t"] if i + 1 < len(words) else TOTAL
    b = max(a + 0.16, min(nxt, w["te"] + 0.35))
    txt = w["w"].strip(",")
    key = clean(txt) in EMPH
    gap_after = nxt - w["te"]
    if key and gap_after > 0.35 and not txt.endswith((".", "!", "?")): txt += "."
    if not (txt == "I" or txt.startswith("I'")): txt = txt.lower()
    c = ACC if key else WHITE
    if in_frame(a):
        ev.append(f"Dialogue: 1,{ts(a)},{ts(b)},Big,,0,0,0,,{{\\an2\\pos(540,620)\\fs{int(BIG*0.6)}\\fsp{TRACK*0.6:.1f}\\c{col(WHITE)}}}{txt}")
        continue
    sz = BIG
    while (fbig.getlength(txt) + TRACK * len(txt)) * sz / BIG > W - 90 and sz > 90: sz -= 8
    pop = r"\fscx106\fscy106\t(0,70,\fscx100\fscy100)"
    ev.append(f"Dialogue: 1,{ts(a)},{ts(b)},Big,,0,0,0,,{{\\an5\\pos(540,{WORD_Y})\\fs{sz}\\fsp{TRACK*sz/BIG:.1f}\\c{col(c)}{pop}}}{txt}")

assf = os.path.join(WORK, "caps_chunky_word.ass")
open(assf, "w").write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Big,{FONT},{BIG},&H00FFFFFF,&H00FFFFFF,&H00000000,&HA0000000,1,0,0,0,100,100,{TRACK},0,1,0,3,5,0,0,0,1
Style: Script,Mrs Saint Delafield,330,{col(ACC)},{col(ACC)},{col(ACC)},&HB0000000,0,0,0,0,100,100,0,0,1,2,2,3,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(_quiet(ev, WORK)) + "\n")

out = os.path.join(WORK, "out"); os.makedirs(out, exist_ok=True)
final = os.path.join(out, CFG.get("output", "edit.mp4").replace(".mp4", "-chunky-word.mp4"))
ap = assf.replace(":", "\\:")
import brand as _b; _BF = _b.patch_ass(ap, _b.Brand(CFG), F)   # their own brand fonts in the captions, if they have them
fc = f"[0:v]ass='{ap}':fontsdir='{_BF}'[vout]"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", base, "-filter_complex", fc, "-map", "[vout]", "-map", "0:a",
                "-c:v", "libx264", *TAGS, "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", final], check=True)
print("ok", final, len(ev), "events")
