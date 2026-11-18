"""B-roll Matchmaker step 3: make a text-on-screen reel from B-roll clips.
usage: python3 broll_reel.py reel.json
reel.json:
{"type": "pov" | "thought" | "tips" | "hook",
 "output": "<file>.mp4",
 "clips": [{"src": "<clip or photo>", "ss": 1.0, "dur": 2.0}],      # in order; photos get a slow push-in
 "palette": {"accent": "#F5BACB", "on_accent": "#0A0A0A"},
 "look": "soft_glass" | "bold_highlight" | "pink_pop" | "typewriter" | "pink_label" | "chunky_word",  # their preset look
 "accent_words": ["prepared"],          # 1-3 words that switch to the brand color (and the look's accent font)
 "outline": "auto" | true | false,      # thin black outline on the words (auto = only over bright footage)
 "dim": "auto" | 0.0-0.3,                # darken the footage a touch so white words read (auto = only when bright)
 "text": ...per type:
    pov:     {"line": "POV: you finally stopped waiting for a sign"}             # use \n to choose line breaks
    thought (full prayer/thought on screen, the creator's style):
             {"header": "Girl pray,", "body": "Dear Heavenly Father,\n\nHelp me become...\n\nIn Jesus' name, Amen.", "body_color": "white" | "accent", "font": "rounded"}
             header = big title in the brand color with a white outline; body = the whole text, centered, footage dimmed
    thought (one line per clip): {"parts": ["Lord, I don't have it all figured out.", "But I trust You with every step."]}   # one part per clip (or fewer: spread evenly)
    tips:    {"title": "3 ways I protect my quiet time", "tips": ["Phone stays in the kitchen", "Bible before email", "Five minutes of silence"]}
    hook:    {"line": "You're not behind. You're being prepared.", "accent_words": ["prepared"]}
 "music": "<optional audio file>"}
No music = silent track, so the creator can add Instagram audio."""
import json, os, subprocess, sys, tempfile
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from sdr import sdr_vf, TAGS
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); FD = os.path.join(HERE, "..", "fonts")
P = json.load(open(sys.argv[1]))
W, H, FPS = 1080, 1920, 30
TMP = tempfile.mkdtemp(prefix="reel_")
def hx(h): h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
PAL = P.get("palette", {}); ACC = hx(PAL.get("accent", "#F5BACB")); ON = hx(PAL.get("on_accent", "#0A0A0A"))
import brand as _b0; _B0 = _b0.Brand(P); ACC, ON = _B0.light, _B0.on      # brand accent that reads on footage
# white words + accent words in the brand color, in each look's fonts (no boxes)
LOOKS = {   # body font, accent font, size scale, align
 "soft_glass":     ("InterDisplay-SemiBold.otf", "PlayfairDisplay-BoldItalic.ttf", 1.0, "left"),
 "bold_highlight": ("InterDisplay-Bold.otf",     "PlayfairDisplay-BoldItalic.ttf", 1.05, "center"),
 "pink_pop":       ("BDTMontBold.ttf",           "BDTMontBlack.ttf",               1.0, "center"),
 "typewriter":     ("PlexMono-SemiBold.ttf",     "PlexMono-SemiBold.ttf",          0.85, "center"),
 "pink_label":     ("BDTMontBold.ttf",           "BDTMontBold.ttf",                0.95, "center"),
 "chunky_word":    ("InterDisplay-Bold.otf",     "InterDisplay-Bold.otf",          1.15, "center")}
BODY, ACCF, SCALE, ALIGN = LOOKS.get(P.get("look", "soft_glass"), LOOKS["soft_glass"])
ALIGN = P.get("align", ALIGN)
ACCENTS = set(w.lower().strip(".,!?:") for w in P.get("accent_words", P.get("text", {}).get("accent_words", [])))
import brand as _bb; _BB = _bb.Brand(P)
def font(name, size):
    p, w = _BB.map(name, own=True) if not os.path.isabs(name) else (name, None); return _bb.load(p, size, w)

# ---------- 1. clips -> uniform 1080x1920 segments, all matched to one look ----------
from sdr import measure, match_vf
_m = []
for c in P["clips"]:
    if c["src"].lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".heic")): _m.append(None); continue
    _m.append(measure(c["src"], c.get("ss", 0) + float(c.get("dur", 2.0)) / 2))
_ok = sorted(x for x in _m if x)
T_LUM = sorted(l for l, _ in _ok)[len(_ok) // 2] if _ok else 128
T_LUM = max(110, min(150, T_LUM))                      # shared brightness: the middle clip, kept natural
T_SAT = sorted(s_ for _, s_ in _ok)[len(_ok) // 2] if _ok else 90
segs = []
for i, c in enumerate(P["clips"]):
    d = float(c.get("dur", 2.0)); out = os.path.join(TMP, f"s{i:02d}.mp4"); segs.append((out, d))
    fit = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    if c["src"].lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".heic")):
        n = int(d * FPS)
        vf = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
              f"zoompan=z='1+0.07*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS},format=yuv420p")
        cmd = ["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", c["src"], "-t", f"{d:.3f}", "-vf", vf]
    else:
        mv = match_vf(*_m[i], T_LUM, T_SAT) if _m[i] else ""
        vf = f"{sdr_vf(c['src'])}{mv}{fit},fps={FPS},format=yuv420p"
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(c.get("ss", 0)), "-i", c["src"], "-t", f"{d:.3f}", "-vf", vf]
    subprocess.run(cmd + ["-an", "-c:v", "libx264", *TAGS, "-preset", "veryfast", "-crf", "16", out], check=True)
lst = os.path.join(TMP, "list.txt"); open(lst, "w").write("".join(f"file '{s}'\n" for s, _ in segs))
body = os.path.join(TMP, "body.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", body], check=True)
starts, t = [], 0.0
for _, d in segs: starts.append(t); t += d
TOTAL = t

# ---------- 2. how bright is the footage where the words go? ----------
def band_luma(cy, half=170):
    vals = []
    for (sp, d) in segs:
        fp = os.path.join(TMP, "luma.jpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{d*0.5:.2f}", "-i", sp, "-frames:v", "1", fp])
        if os.path.exists(fp):
            g = Image.open(fp).convert("L").crop((80, max(0, cy - half), W - 80, min(H, cy + half)))
            px = g.get_flattened_data() if hasattr(g, "get_flattened_data") else g.getdata()
            vals.append(sum(px) / (g.width * g.height))
    return max(vals) if vals else 128

def wrap(text, f, maxw):
    if "\n" in text:
        return [l for part in text.split("\n") for l in wrap(part.strip(), f, maxw)]
    words, lines, cur = text.split(), [], ""
    for w in words:
        tt = (cur + " " + w).strip()
        if f.getlength(tt) <= maxw or not cur: cur = tt
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def text_block(text, size, cy, color=(255, 255, 255), all_accent=False, maxw=None):
    """White words (accent words in the brand color + accent font), soft shadow, optional thin outline."""
    size = int(size * SCALE)
    fb, fa = font(BODY, size), font(ACCF, int(size * (1.12 if ACCF != BODY else 1.0)))
    maxw = maxw or (W - 170)
    lines = wrap(text, fb, maxw); lh = int(size * 1.28)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d, ds = ImageDraw.Draw(im), ImageDraw.Draw(sh)
    top = cy - len(lines) * lh / 2
    for k, ln in enumerate(lines):
        words = ln.split()
        parts = [(w, all_accent or w.lower().strip(".,!?:") in ACCENTS) for w in words]
        widths = [(fa if acc else fb).getlength(w) for w, acc in parts]; space = fb.getlength(" ")
        total = sum(widths) + space * (len(parts) - 1)
        x = 85 if ALIGN == "left" else (W - total) / 2
        y = top + k * lh + lh * 0.78                       # baseline
        for (w, acc), ww in zip(parts, widths):
            f = fa if acc else fb; c = (ACC if acc else color) + (255,)
            ds.text((x, y + 4), w, font=f, fill=(0, 0, 0, 205), anchor="ls", stroke_width=2, stroke_fill=(0, 0, 0, 120))
            if OUTLINE: d.text((x, y), w, font=f, fill=c, anchor="ls", stroke_width=max(2, size // 34), stroke_fill=(0, 0, 0, 235))
            else: d.text((x, y), w, font=f, fill=c, anchor="ls")
            x += ww + space
    out = sh.filter(ImageFilter.GaussianBlur(8)); out.alpha_composite(im)
    return out

def prayer_block(X):
    """Whole prayer on screen: optional big header (brand color, thick white outline), body centered in a narrow column."""
    rounded = X.get("font", P.get("font")) == "rounded"
    hb = "Nunito-900.ttf" if rounded else (ACCF if ACCF.startswith("Inter") or ACCF.startswith("BDT") else BODY)
    bb = "Nunito-900.ttf" if rounded else BODY
    col = ACC if X.get("body_color") == "accent" else (255, 255, 255)
    top_lim, bot_lim, colw = 330, 1560, 800
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d, ds = ImageDraw.Draw(im), ImageDraw.Draw(sh)
    y = top_lim
    if X.get("header"):
        hs = 150; hf = font(hb, hs)
        while hf.getlength(X["header"]) > W - 140 and hs > 80: hs -= 6; hf = font(hb, hs)
        y += hs * 0.85
        ds.text((W / 2, y + 6), X["header"], font=hf, fill=(0, 0, 0, 120), anchor="ms", stroke_width=10, stroke_fill=(0, 0, 0, 120))
        d.text((W / 2, y), X["header"], font=hf, fill=ACC + (255,), anchor="ms", stroke_width=max(6, hs // 18), stroke_fill=(255, 255, 255, 255))
        y += hs * 0.55
    paras = X["body"].split("\n")
    size = 62
    while True:                                           # shrink until the whole prayer fits
        bf = font(bb, size); lh = size * 1.14; gap = size * 0.55
        blocks = [wrap(pp, bf, colw) if pp.strip() else [] for pp in paras]
        hgt = sum(len(b) * lh if b else gap for b in blocks)
        if y + hgt <= bot_lim or size <= 34: break
        size -= 2
    y += max(0, (bot_lim - y - hgt) / 2) * 0.35
    for b in blocks:
        if not b: y += gap; continue
        for ln in b:
            y += lh
            ds.text((W / 2, y + 3), ln, font=bf, fill=(0, 0, 0, 200), anchor="ms", stroke_width=3, stroke_fill=(0, 0, 0, 140))
            d.text((W / 2, y), ln, font=bf, fill=col + (255,), anchor="ms",
                   **({"stroke_width": 2, "stroke_fill": (0, 0, 0, 220)} if OUTLINE else {}))
    out = sh.filter(ImageFilter.GaussianBlur(10)); out.alpha_composite(im)
    return out

def girl_pray_block(X):
    """Destiny's prayer reel look: rounded heavy header in her pink with a white outline,
    then the prayer in bold white (or light pink), centered, tight lines, soft shadow."""
    import brand as _b; _B = _b.Brand(P)
    hf_name, bf_name = ("Nunito-900.ttf", "Figtree-800.ttf") if not _B.custom else (_B.fonts["black"][0], _B.fonts["bold"][0])
    hcol = hx(X.get("header_color", PAL.get("accent", "#DE97B5")))
    bcol = hx(X.get("body_hex", "#%02X%02X%02X" % _B.light)) if X.get("body_color") == "accent" else (255, 255, 255)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d, ds = ImageDraw.Draw(im), ImageDraw.Draw(sh)
    y = 300
    if X.get("header"):
        hs = 130; hf = font(hf_name, hs)
        while hf.getlength(X["header"]) > 600 and hs > 70: hs -= 4; hf = font(hf_name, hs)
        y += hs * 0.8
        ds.text((W / 2, y + 5), X["header"], font=hf, fill=(0, 0, 0, 110), anchor="ms", stroke_width=9, stroke_fill=(0, 0, 0, 110))
        d.text((W / 2, y), X["header"], font=hf, fill=hcol + (255,), anchor="ms", stroke_width=7, stroke_fill=(255, 255, 255, 255))
        y += hs * 1.05
    paras = X["body"].split("\n"); colw = 680; size = 56
    while True:
        bf = font(bf_name, size); lh = size * 1.08; gap = size * 0.6
        blocks = [wrap(pp, bf, colw) if pp.strip() else [] for pp in paras]
        hgt = sum(len(b) * lh if b else gap for b in blocks)
        if y + hgt <= 1600 or size <= 34: break
        size -= 2
    for b in blocks:
        if not b: y += gap; continue
        for ln in b:
            y += lh
            ds.text((W / 2, y + 3), ln, font=bf, fill=(0, 0, 0, 190), anchor="ms", stroke_width=2, stroke_fill=(0, 0, 0, 120))
            d.text((W / 2, y), ln, font=bf, fill=bcol + (255,), anchor="ms")
    out = sh.filter(ImageFilter.GaussianBlur(6)); out.alpha_composite(im)
    return out

cards = []   # (png, start, end)
def add(im, a, b):
    p = os.path.join(TMP, f"c{len(cards):02d}.png"); im.save(p); cards.append((p, a, b))

# ---------- text height: keep words off faces ----------
def face_boxes():
    try:
        import cv2
    except ImportError:
        for args in (["-q", "opencv-python-headless"], ["-q", "--break-system-packages", "opencv-python-headless"]):
            subprocess.run([sys.executable, "-m", "pip", "install", *args], capture_output=True)
        try: import cv2
        except ImportError: return None
    try:
        det = cv2.CascadeClassifier(os.path.join(HERE, "..", "data", "haarcascade_frontalface_default.xml"))
        if det.empty(): return None
    except Exception:
        return None
    boxes = []
    for (sp, d) in segs:
        for frac in (0.3, 0.7):
            fp = os.path.join(TMP, "face.jpg")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{d*frac:.2f}", "-i", sp, "-frames:v", "1", fp])
            img = cv2.imread(fp)
            if img is None: continue
            g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            for (x, y, w, h) in det.detectMultiScale(g, 1.1, 6, minSize=(90, 90)):
                boxes.append((y - h * 0.25, y + h * 1.15))        # forehead to chin
    return boxes

def pick_y(block_h):
    if "text_y" in P: return P["text_y"]
    faces = face_boxes()
    cands = [760, 600, 940, 1120, 460, 1260]
    if not faces: return cands[0]
    def hits(cy): return sum(1 for a, b in faces if not (cy + block_h / 2 + 30 < a or cy - block_h / 2 - 30 > b))
    return min(cands, key=lambda cy: (hits(cy), cands.index(cy)))


ty, X = P["type"], P.get("text", {})
_est = {"pov": 2 * 90, "hook": 3 * 120, "thought": 3 * 86, "tips": 2 * 80}.get(ty, 200)
FULL = ty == "thought" and "body" in X
TEXT_Y = 940 if FULL else pick_y(_est)
LUMA = band_luma(TEXT_Y, 520 if FULL else 170)
DIM = P.get("dim", "auto")
if DIM == "auto":
    if FULL and X.get("style") == "girl_pray": DIM = 0.12
    elif FULL: DIM = 0.28 if LUMA > 140 else 0.2
    else: DIM = 0.08 if LUMA > 200 else 0.0      # words carry their own shadow; only shade very bright spots
else: DIM = float(DIM)
OUT_ = P.get("outline", "auto"); OUTLINE = (LUMA > 195) if OUT_ == "auto" else bool(OUT_)
print("look target: brightness", int(T_LUM), "saturation", int(T_SAT)); print("text height:", TEXT_Y, "brightness:", int(LUMA), "dim:", DIM, "outline:", OUTLINE)

if ty == "pov":
    add(text_block(X["line"], 66, TEXT_Y), 0.15, TOTAL)
elif ty == "hook":
    add(text_block(X["line"], 100, TEXT_Y), 0.1, TOTAL)
elif ty == "thought" and "body" in X and X.get("style") == "girl_pray":
    add(girl_pray_block(X), 0.12, TOTAL)
elif ty == "thought" and "body" in X:
    add(prayer_block(X), 0.12, TOTAL)
elif ty == "thought":
    parts = X["parts"]; n = len(parts); per = TOTAL / n
    for k, part in enumerate(parts):
        a = starts[k] if n == len(starts) else k * per
        b = (starts[k + 1] if k + 1 < len(starts) else TOTAL) if n == len(starts) else (k + 1) * per
        add(text_block(part, 68, TEXT_Y), a + (0.12 if k == 0 else 0), b)
elif ty == "tips":
    tips = X["tips"]; first_end = starts[1] if len(starts) > 1 else TOTAL
    add(text_block(X["title"], 84, TEXT_Y), 0.12, first_end)
    tip_starts = starts[1:] if len(starts) > 1 else [0]
    for k, tip in enumerate(tips):
        a = tip_starts[k] if k < len(tip_starts) else tip_starts[-1]
        b = tip_starts[k + 1] if k + 1 < len(tip_starts) else TOTAL
        im = text_block(X["title"], 46, 330)
        im.alpha_composite(text_block(f"{k + 1}. {tip}", 70, TEXT_Y))
        add(im, a, b)
else:
    sys.exit("type must be pov, thought, tips or hook")

if DIM > 0:   # soft shade only behind the words, so the rest of the clip keeps its true colors
    band = Image.new("L", (1, H), 0); half = 520 if FULL else 300
    for yy in range(H):
        t = max(0.0, 1 - abs(yy - TEXT_Y) / half); band.putpixel((0, yy), int(255 * DIM * 2.2 * (t ** 1.6)))
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0)); shade.putalpha(band.resize((W, H)))
    sp_ = os.path.join(TMP, "shade.png"); shade.save(sp_); cards.insert(0, (sp_, 0.0, TOTAL))

# ---------- 3. composite ----------
out = os.path.abspath(P["output"]); os.makedirs(os.path.dirname(out), exist_ok=True)
cmd = ["ffmpeg", "-v", "error", "-y", "-i", body]
for p, a, b in cards: cmd += ["-loop", "1", "-t", f"{TOTAL:.3f}", "-i", p]
music = P.get("music")
if music: cmd += ["-i", music]
else: cmd += ["-f", "lavfi", "-t", f"{TOTAL:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
fc, last = [], "[0:v]"
for k, (p, a, b) in enumerate(cards):
    fc.append(f"[{k+1}:v]format=rgba,fade=t=in:st={a:.3f}:d=0.18:alpha=1[t{k}]")
    fc.append(f"{last}[t{k}]overlay=0:0:enable='between(t,{a:.3f},{b:.3f})'[v{k}]"); last = f"[v{k}]"
fc.append(f"{last}format=yuv420p[vout]")
ai = len(cards) + 1
cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", f"{ai}:a", "-t", f"{TOTAL:.3f}",
        "-c:v", "libx264", *TAGS, "-preset", "medium", "-crf", "19", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out]
subprocess.run(cmd, check=True)
print("ok", out, f"{TOTAL:.1f}s", len(cards), "text cards")
