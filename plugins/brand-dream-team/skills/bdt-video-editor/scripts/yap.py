"""Brand Dream Team preset: The Original Yap (approved Nov 20, 2026).
- Titles at the top: the hook first ("clarity comes from / *moving* your feet..."), shown 5 to 10 seconds, then short
  titles that match each point. Bold tight white words, ONE word in the thin italic in their color. No typing.
- Captions: one bold white word at a time, a few inches under the chin. Key words get a small bounce and a pop.
- Handwritten pop-ups at the bottom left (Shadows Into Light Two), small but easy to read, repeating what they say.
- Sounds: a whoosh as each title appears, pops on key words, a marker squeak on pop-ups, a whoosh out at the end.
usage: python3 yap.py <project> [edit.json]   (run make_base.py first)
  "titles": [{"line1": "clarity comes from", "line2": "moving your feet...", "italic": "moving", "t": 0, "dur": 8},
             {"line1": "stop waiting", "line2": "for clarity", "italic": "clarity", "at": "their exact words"}]
  "emphasis": ["accountable", "purpose"]   words that get the bounce and pop
  "notes": [{"text": "you don't have to have it all figured out", "at": "their exact words", "dur": 3.5}]
  "caption_y": 1360                       move it if it covers the face (check frames)
"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); VE = os.path.dirname(HERE); sys.path.insert(0, HERE)
from sdr import TAGS
from PIL import ImageFont
import brand as _bb
F = os.path.join(VE, "fonts"); HAND_P = os.path.join(F, "ShadowsIntoLightTwo-Regular.ttf")
WORK = os.path.abspath(sys.argv[1]); CFG = json.load(open(os.path.join(WORK, sys.argv[2] if len(sys.argv) > 2 else "edit.json")))
base = os.path.join(WORK, "base.mp4")
words = [w for w in json.load(open(os.path.join(WORK, "timeline_words.json"))) if w["w"].strip()]
TOTAL = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", base], capture_output=True, text=True).stdout)
W, H = 1080, 1920
B = _bb.Brand(CFG); ACC = B.light; WHITE = (255, 255, 255)
def col(rgb, a=0): return "&H%02X%02X%02X%02X" % (a, rgb[2], rgb[1], rgb[0])
def ts(x): x = max(0, x); return f"{int(x//3600)}:{int(x%3600//60):02d}:{x%60:05.2f}"
def esc(s): return s.replace("{", "(").replace("}", ")").replace("\\", "/")
def norm(s): return s.lower().strip(",.!?\"'")
BOLD_P = os.path.join(F, "InterDisplay-Black.otf"); BOLD = _bb.ass_name(BOLD_P)
SEMI = _bb.ass_name(os.path.join(F, "InterDisplay-SemiBold.otf"))
ITAL_P = B.hook_title[0] if B.hook_title else os.path.join(F, "InstrumentSerif-Italic.ttf"); ITAL = _bb.ass_name(ITAL_P)
HAND = _bb.ass_name(HAND_P)
SH = r"\bord0\shad0\4a&HFF&"
RI, RS = 0.82, 0.77   # libass draws Inter at ~82% and Instrument Serif at ~77% of the PIL width
GLOW = r"\bord4\3c&H000000&\3a&HB4&\blur9"
THICK = r"\bord1.2\3c&HFFFFFF&\3a&H00&\shad3\4c&H000000&\4a&H90&"   # soft dark halo, like the example
def find(phrase, after=0.0):
    seq = [norm(x) for x in phrase.split()]; ws = [norm(x["w"]) for x in words]
    for i in range(len(ws) - len(seq) + 1):
        if ws[i:i+len(seq)] == seq and words[i]["t"] >= after - 0.01: return i
    return None
ev, cues = [], []

# ---- titles at the top: the hook first (5-10 s), then short titles that match each point. One italic word each.
TITLES = CFG.get("titles") or []
def tline(txt, fs, ital):
    out = []
    for wd in txt.split():
        if ital and norm(wd) == norm(ital): out.append(f"{{\\fn{ITAL}\\fs{int(fs*1.3)}\\fsp0\\c{col(ACC)}}}{esc(wd)}{{\\fn{BOLD}\\fs{fs}\\fsp-6\\c{col(WHITE)}}}")
        else: out.append(esc(wd))
    return " ".join(out)
def twidth(txt, fs, ital):
    f1, f2 = ImageFont.truetype(BOLD_P, fs), ImageFont.truetype(ITAL_P, int(fs * 1.3))
    return sum((f2.getlength(w + " ") * RS if ital and norm(w) == norm(ital) else f1.getlength(w + " ") * RI - 6) for w in txt.split())
starts = []
for k, t in enumerate(TITLES):
    if "t" in t: starts.append(float(t["t"]))
    else:
        i = find(t["at"]) if t.get("at") else None
        starts.append(words[i]["t"] if i is not None else (0.0 if k == 0 else None))
for k, t in enumerate(TITLES):
    a = starts[k]
    if a is None: continue
    nxt = [x for x in starts[k+1:] if x is not None]
    b = nxt[0] if nxt else TOTAL
    if t.get("dur"): b = min(b, a + float(t["dur"]))
    lines_t = [x for x in (t.get("line1", ""), t.get("line2", "")) if x]
    fs = 150 if k == 0 else 120
    while any(twidth(x, fs, t.get("italic")) > W - 110 for x in lines_t) and fs > 60: fs -= 4
    y = 330
    for x in lines_t:
        ev.append(f"Dialogue: 3,{ts(a)},{ts(b)},S,,0,0,0,,{{\\an2\\pos(540,{y})\\fn{BOLD}\\fs{fs}\\fsp-6\\c{col(WHITE)}{GLOW}\\fad(120,120)}}{tline(x, fs, t.get('italic'))}")
        y += int(fs * 0.86)
    cues.append({"id": "whoosh", "t": a})

# ---- captions: one white word at a time, a few inches under the chin
CY = CFG.get("caption_y", 1360); CS = 100
CAPB = _bb.ass_name(os.path.join(F, "InterDisplay-Black.otf"))
EMPH = [[norm(x) for x in e.split()] for e in CFG.get("emphasis", [])]
ws = [norm(x["w"]) for x in words]; key = [False] * len(words)
for e in EMPH:
    for i in range(len(ws) - len(e) + 1):
        if ws[i:i+len(e)] == e: key[i] = True
last_pop = -9
for i, w in enumerate(words):
    a = w["t"]; nxt = words[i+1]["t"] if i + 1 < len(words) else TOTAL
    b = max(a + 0.14, min(nxt, w["te"] + 0.3)); txt = esc(w["w"].strip())
    if not (txt == "I" or txt.startswith("I'")): txt = txt.lower()
    bounce = r"\fscx118\fscy118\t(0,110,\fscx100\fscy100)" if key[i] else r"\fscx104\fscy104\t(0,60,\fscx100\fscy100)"
    ev.append(f"Dialogue: 1,{ts(a)},{ts(b)},S,,0,0,0,,{{\\an5\\pos(540,{CY})\\fn{CAPB}\\fs{CS}\\fsp-3\\c{col(WHITE)}{GLOW}{bounce}}}{txt}")
    if key[i] and a - last_pop > 1.2: cues.append({"id": "pop", "t": a}); last_pop = a

# ---- handwritten pop-ups at the bottom that repeat what they're saying (smaller, still easy to read)
for n in CFG.get("notes", []):
    i = find(n["at"]) if n.get("at") else None
    a = words[i]["t"] if i is not None else float(n.get("t", 2)); b = min(TOTAL, a + float(n.get("dur", 3.5)))
    s = 72; f = ImageFont.truetype(HAND_P, s); lines, cur = [], ""
    for wd in n["text"].split():
        if cur and f.getlength(cur + " " + wd) * 0.8 > 520: lines.append(cur); cur = wd
        else: cur = (cur + " " + wd).strip()
    lines.append(cur)
    ev.append(f"Dialogue: 2,{ts(a)},{ts(b)},S,,0,0,0,,{{\\an7\\pos(70,{CY+150})\\frz4\\fn{HAND}\\fs{s}\\c{col(WHITE)}{THICK}\\fad(180,220)}}{'\\N'.join(esc(x) for x in lines)}")
    cues.append({"id": "marker", "t": a})
if words and TOTAL > 8: cues.append({"id": "whoosh_out", "t": max(0, words[-1]["t"] - 0.1)})

assf = os.path.join(WORK, "caps_yap.ass")
open(assf, "w").write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: S,{SEMI},{CS},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n")
fd = os.path.join(WORK, "_yapfonts"); os.makedirs(fd, exist_ok=True)
for p in (BOLD_P, os.path.join(F, "InterDisplay-SemiBold.otf"), ITAL_P, HAND_P):
    subprocess.run(["cp", p, fd])
out = os.path.join(WORK, "out"); os.makedirs(out, exist_ok=True)
final = os.path.join(out, CFG.get("output", "edit.mp4").replace(".mp4", "-original-yap.mp4")); tmp = final + ".tmp.mp4"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", base, "-vf", f"ass='{assf}':fontsdir='{fd}'", "-c:v", "libx264", *TAGS,
                "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", tmp], check=True)
cf = os.path.join(WORK, "_yap_sounds.json"); json.dump(cues, open(cf, "w"))
subprocess.run([sys.executable, os.path.join(VE, "scripts", "sfx.py"), WORK, tmp, final, cf], check=True); os.remove(tmp)
print("ok", final)
