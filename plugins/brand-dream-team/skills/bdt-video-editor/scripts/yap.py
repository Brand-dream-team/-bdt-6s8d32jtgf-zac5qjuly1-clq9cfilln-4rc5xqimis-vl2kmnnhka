"""Brand Dream Team preset: The Original Yap.
Talking-head "yap" style: a two-line hook that types itself on at the top (clean line + big italic accent line)
with a small handwritten line under it, captions that build a few words at a time in the middle of the frame with
key words switching to an italic serif in the creator's color, optional photo pop-ups and handwritten side notes,
and a sound on every moment that matters.
usage: python3 yap.py <project folder> [edit.json]   (run make_base.py first)

edit.json keys it reads (all optional except words come from the video):
  "hook": {"line1": "you probably know", "line2": "a mom like this...", "sub": "this is your sign to check on her", "dur": 0}
          dur 0 or missing = the hook stays the whole video
  "emphasis": ["a lot", "how hard", "first"]      words or short phrases that switch to the accent italic
  "caption_y": 1100                               center of the captions (move it if it covers the face)
  "pops":  [{"img": "/path/photo.jpg", "at": "three boys", "dur": 1.6}]   their own photos only
  "notes": [{"text": "also this is my first yap post :)", "at": "viral launch", "dur": 4}]
  "sounds": [...]                                 your own sound cues; if missing, sounds are placed automatically
  "sfx": false                                    no sound effects
"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from sdr import TAGS
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import brand as _bb

F = os.path.join(HERE, "..", "fonts")
WORK = os.path.abspath(sys.argv[1])
CFG_NAME = sys.argv[2] if len(sys.argv) > 2 else "edit.json"
CFG = json.load(open(os.path.join(WORK, CFG_NAME)))
base = os.path.join(WORK, "base.mp4"); assert os.path.exists(base), "run scripts/make_base.py on this project first"
words = [w for w in json.load(open(os.path.join(WORK, "timeline_words.json"))) if w["w"].strip()]
TOTAL = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", base], capture_output=True, text=True).stdout)
W, H = 1080, 1920
B = _bb.Brand(CFG)
ACC = B.light
WHITE = (255, 255, 255)

def col(rgb, a=0): return "&H%02X%02X%02X%02X" % (a, rgb[2], rgb[1], rgb[0])
def ts(x): x = max(0, x); return f"{int(x//3600)}:{int(x%3600//60):02d}:{x%60:05.2f}"
def esc(s): return s.replace("{", "(").replace("}", ")").replace("\\", "/")
def norm(s): return s.lower().strip(",.!?\"'")

# fonts: clean sans for the main text, italic serif (or their hook font) for accents, a legible handwriting for notes
SANS_P = os.path.join(F, "Inter-SemiBold.otf"); SANS = "Inter SemiBold"
ITAL_P = os.path.join(F, "InstrumentSerif-Italic.ttf")
if B.hook_title: ITAL_P = B.hook_title[0]
ITAL = _bb.ass_name(ITAL_P)
HAND_P = os.path.join(F, "Caveat-Bold.ttf"); HAND = _bb.ass_name(HAND_P)
def pil(p, s): return ImageFont.truetype(p, s)

def find(phrase, after=0.0):
    seq = [norm(x) for x in phrase.split()]; ws = [norm(x["w"]) for x in words]
    for i in range(len(ws) - len(seq) + 1):
        if ws[i:i+len(seq)] == seq and words[i]["t"] >= after - 0.01: return i
    return None

ev = []; cues = []
SHADOW = r"\bord2\3c&H000000&\3a&HB4&\shad3\4c&H000000&\4a&H60&\blur1"

# ---- hook: types itself on, then stays
hook = CFG.get("hook") or {}
l1, l2, sub = hook.get("line1", ""), hook.get("line2", ""), hook.get("sub", "")
hook_end = TOTAL if not hook.get("dur") else min(TOTAL, float(hook["dur"]))
if l1 or l2:
    s1, s2 = 112, 150
    while pil(SANS_P, s1).getlength(l1) > W - 140 and s1 > 50: s1 -= 4
    while pil(ITAL_P, s2).getlength(l2) > W - 120 and s2 > 60: s2 -= 4
    y1, y2 = 215, 215 + s1 * 0.72 + s2 * 0.55
    full = l1 + l2; n = max(1, len(full)); tt = min(1.1, 0.045 * n)   # typing time
    steps = list(range(1, n + 1, max(1, n // 22))) + [n]
    for k, c in enumerate(steps):
        a = tt * (k / len(steps)); b = tt * ((k + 1) / len(steps))
        p1, p2 = full[:min(c, len(l1))], full[len(l1):c]
        cur = "|" if k < len(steps) - 1 else ""
        if p1: ev.append(f"Dialogue: 3,{ts(a)},{ts(b if cur else hook_end)},Hook,,0,0,0,,{{\\an5\\pos(540,{y1:.0f})\\fn{SANS}\\fs{s1}\\c{col(WHITE)}{SHADOW}}}{esc(p1)}{cur if not p2 else ''}")
        if p2: ev.append(f"Dialogue: 3,{ts(a)},{ts(b if cur else hook_end)},Hook,,0,0,0,,{{\\an5\\pos(540,{y2:.0f})\\fn{ITAL}\\fs{s2}\\c{col(ACC)}{SHADOW}}}{esc(p2)}{cur}")
    if sub:
        s3 = 66
        while pil(HAND_P, s3).getlength(sub) > W - 160 and s3 > 30: s3 -= 2
        y3 = y2 + s2 * 0.66
        ev.append(f"Dialogue: 3,{ts(tt + 0.15)},{ts(hook_end)},Hook,,0,0,0,,{{\\an5\\pos(540,{y3:.0f})\\fn{HAND}\\fs{s3}\\c{col(WHITE)}{SHADOW}\\fad(250,0)}}{esc(sub)}")
    cues.append({"id": "whoosh", "t": 0.0})

# ---- captions: a few words at a time, building word by word, key words in the accent italic
EMPH = [[norm(x) for x in e.split()] for e in CFG.get("emphasis", [])]
key = [False] * len(words)
ws = [norm(x["w"]) for x in words]
for e in EMPH:
    for i in range(len(ws) - len(e) + 1):
        if ws[i:i+len(e)] == e:
            for j in range(i, i + len(e)): key[j] = True
CY = CFG.get("caption_y", 1290); CS, KS = 80, 98
fs_, fk_ = pil(SANS_P, CS), pil(ITAL_P, KS)
def wlen(i): t = words[i]["w"].strip() + " "; return (fk_ if key[i] else fs_).getlength(t)
chunks, cur = [], []
for i, w in enumerate(words):
    if cur:
        gap = w["t"] - words[cur[-1]]["te"]
        if gap > 0.35 or len(cur) >= 7 or words[cur[-1]]["w"].rstrip().endswith((".", "!", "?")):
            chunks.append(cur); cur = []
    cur.append(i)
if cur: chunks.append(cur)
MAXW = W - 180
def lines_of(ids):
    out, line, lw = [], [], 0
    for i in ids:
        if line and lw + wlen(i) > MAXW: out.append(line); line, lw = [], 0
        line.append(i); lw += wlen(i)
    if line: out.append(line)
    return out[:2] if len(out) <= 2 else [sum(out[:-1], []), out[-1]]
def word_txt(i):
    t = esc(words[i]["w"].strip())
    if not (t == "I" or t.startswith("I'")): t = t.lower()
    if key[i]: return f"{{\\fn{ITAL}\\fs{KS}\\c{col(ACC)}\\3a&H70&}}{t}{{\\fn{SANS}\\fs{CS}\\c{col(WHITE)}\\3a&HB4&}}"
    return t
last_pop = -9
for ch in chunks:
    end = min(TOTAL, max(words[ch[-1]]["te"] + 0.25, words[ch[-1]]["t"] + 0.3))
    nxt = [c for c in chunks if words[c[0]]["t"] > words[ch[-1]]["t"]]
    if nxt: end = min(end, words[nxt[0][0]]["t"])
    for k, i in enumerate(ch):
        a = words[i]["t"]; b = words[ch[k+1]]["t"] if k + 1 < len(ch) else end
        if b <= a: continue
        shown = ch[:k+1]; ls = lines_of(shown)
        txt = "\\N".join(" ".join(word_txt(j) for j in l) for l in ls)
        ev.append(f"Dialogue: 1,{ts(a)},{ts(b)},Cap,,0,0,0,,{{\\an5\\pos(540,{CY})\\fn{SANS}\\fs{CS}\\c{col(WHITE)}{SHADOW}\\q2}}{txt}")
        if key[i] and (i == 0 or not key[i-1]) and a - last_pop > 1.2:
            cues.append({"id": "pop", "t": a}); last_pop = a

# ---- handwritten side notes
for n in CFG.get("notes", []):
    i = find(n["at"]) if n.get("at") else None
    a = words[i]["t"] if i is not None else float(n.get("t", 1.0)); b = min(TOTAL, a + float(n.get("dur", 4)))
    s = 58
    lines = n["text"].split("\n") if "\n" in n["text"] else [n["text"]]
    ev.append(f"Dialogue: 2,{ts(a)},{ts(b)},Hook,,0,0,0,,{{\\an7\\pos(80,1330)\\frz6\\fn{HAND}\\fs{s}\\c{col(WHITE)}{SHADOW}\\fad(200,200)}}{'\\N'.join(esc(x) for x in lines)}")
    cues.append({"id": "marker", "t": a})

# ---- photo pop-ups (their own photos)
pops = []
for k, p in enumerate(CFG.get("pops", [])):
    if not p.get("img") or not os.path.exists(os.path.expanduser(p["img"])): continue
    i = find(p["at"]) if p.get("at") else None
    if i is None and "t" not in p: continue
    a = words[i]["t"] if i is not None else float(p["t"]); b = min(TOTAL, a + float(p.get("dur", 1.6)))
    im = Image.open(os.path.expanduser(p["img"])).convert("RGB"); im.thumbnail((620, 620))
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, im.size[0]-1, im.size[1]-1], 26, fill=255)
    pad = 30; card = Image.new("RGBA", (im.size[0] + pad*2, im.size[1] + pad*2), (0, 0, 0, 0))
    sh = Image.new("RGBA", card.size, (0, 0, 0, 0)); sh.paste((0, 0, 0, 120), (pad, pad + 8), m); sh = sh.filter(ImageFilter.GaussianBlur(14))
    card.alpha_composite(sh); im = im.convert("RGBA"); im.putalpha(m); card.alpha_composite(im, (pad, pad))
    fp = os.path.join(WORK, f"_yap_pop{k}.png"); card.save(fp)
    pops.append((fp, a, b, card.size)); cues.append({"id": "pop_soft", "t": a})

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
Style: Hook,{SANS},84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H70000000,0,0,0,0,100,100,0,0,1,0,3,5,0,0,0,1
Style: Cap,{SANS},{CS},&H00FFFFFF,&H00FFFFFF,&H00000000,&H70000000,0,0,0,0,100,100,0,0,1,0,3,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n")

out = os.path.join(WORK, "out"); os.makedirs(out, exist_ok=True)
final = os.path.join(out, CFG.get("output", "edit.mp4").replace(".mp4", "-original-yap.mp4"))
ap = assf.replace(":", "\\:")
_BF = _bb.patch_ass(ap, B, F)
inputs = ["-i", base]; fc = "[0:v]null[v0]"; last = "v0"
for k, (fp, a, b, (cw, chh)) in enumerate(pops):
    inputs += ["-loop", "1", "-t", f"{TOTAL:.2f}", "-i", fp]
    fc += f";[{k+1}:v]format=rgba,fade=t=in:st={a:.2f}:d=0.15:alpha=1,fade=t=out:st={max(a, b-0.15):.2f}:d=0.15:alpha=1[p{k}]"
    fc += f";[{last}][p{k}]overlay=x=(W-w)/2:y=1180-h/2:enable='between(t,{a:.2f},{b:.2f})'[v{k+1}]"; last = f"v{k+1}"
fc += f";[{last}]ass='{ap}':fontsdir='{_BF}'[vout]"
tmp = final if CFG.get("sfx") is False else final.replace(".mp4", "._nosfx.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[vout]", "-map", "0:a",
                "-c:v", "libx264", *TAGS, "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "copy",
                "-movflags", "+faststart", "-t", f"{TOTAL:.2f}", tmp], check=True)
if tmp != final:
    cf = os.path.join(WORK, "_yap_sounds.json")
    json.dump(CFG.get("sounds") or cues, open(cf, "w"))
    subprocess.run([sys.executable, os.path.join(HERE, "sfx.py"), WORK, tmp, final, cf], check=True)
    os.remove(tmp)
print("ok", final, len(ev), "events", len(pops), "pops")
