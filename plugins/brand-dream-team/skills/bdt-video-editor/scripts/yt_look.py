"""YouTube look (16:9, "coming soon"): frosted dark glass cards, a dark split panel, bold white type with pink italic serif accents.
Run after make_base.py with "size": [1920, 1080] in edit.json:
    python3 scripts/yt_look.py <project>
edit.json "yt": {
  "accent": ["overthinker", ...],               # subtitle words drawn in pink italic serif
  "titles":  [{"at": "professional", "top": "PROFESSIONAL", "word": "overthinker", "dur": 3.6}],
  "checklist": [{"at": "sometimes", "label": "TO HEAR GOD CLEARLY", "items": [["stop overthinking", "over thinking"], ...], "until": "will of god"}],
  "list":    [{"at": "ask god to silence", "label": "...", "title": "Ask God", "accent": "to", "items": [["silence the voices", "silence the"], ...], "until": "promise you"}],
  "compare": [{"at": "promise you you will", "rows": [{"label": "...", "text": "a", "accent": "happier life", "at": "happier"}], "until": "focused"}]
}
Every "at"/"until" is exact lowercase words from the transcript (first match after the previous effect)."""
import json, os, subprocess, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sdr import TAGS

HERE = os.path.dirname(os.path.abspath(__file__)); FD = os.path.join(HERE, "..", "fonts")
WORK = os.path.abspath(sys.argv[1]); CFG = json.load(open(os.path.join(WORK, "edit.json"))); Y = CFG.get("yt", {})
W, H, FPS = 1920, 1080, 30
# Brand colors: from the creator's palette (same 4 role colors as the reel presets).
def _hx(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def _lum(c):
    v = [(x / 255) ** 2.2 for x in c]; return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
def _mix(c, t, k): return tuple(int(round(a + (b - a) * k)) for a, b in zip(c, t))
PAL = {"accent": "#F5BACB", "on_accent": "#2B171C"}; PAL.update(CFG.get("palette", {}))
_acc = _hx(PAL.get("accent_on_dark") or PAL["accent"])
_l = _acc                                   # accent on dark glass: lighten until it reads on dark
while _lum(_l) < 0.16: _l = _mix(_l, (255, 255, 255), 0.12)
_d = _hx(PAL["accent"])                     # accent on white cards / bright frames: darken until it reads on white
while (1.05) / (_lum(_d) + 0.05) < 3.6: _d = _mix(_d, (0, 0, 0), 0.08)
PINK_L = tuple(Y.get("pink_light", _l)); PINK_D = tuple(Y.get("pink_dark", _d))
ON = _hx(PAL.get("on_accent", "#2B171C")) if _lum(PINK_L) > 0.35 else (255, 255, 255)   # text on accent fills
PRESSED = _mix(PINK_L, (0, 0, 0), 0.12)
INK = (24, 20, 22); GREY = (172, 166, 168)

_fc = {}
def font(name, size, wght=None):
    k = (name, size, wght)
    if k not in _fc:
        f = ImageFont.truetype(os.path.join(FD, name), size)
        if wght:
            try: f.set_variation_by_axes([wght])
            except Exception: pass
        _fc[k] = f
    return _fc[k]
# Brand fonts: follow the creator's reel preset (their Studio look), or their own font files in yt.fonts.
import brand as _brand
FONTSETS = {k: dict(v) for k, v in _brand.FONTSETS.items()}
FONTSETS["soft_glass"].update(semi="Inter-SemiBold.otf", accent=["PlayfairDisplay-Italic-VF.ttf", 620])   # the approved YouTube look
_look = str(Y.get("look") or CFG.get("look") or CFG.get("preset") or "soft_glass").lower().replace(" ", "_").replace("-", "_")
FS = dict(FONTSETS.get(_brand.norm_look(_look), FONTSETS["soft_glass"])); _hk = _brand.STUDIO_FONTS.get(str(CFG.get("hook_font") or "").strip().strip(".").lower(), {})
if _hk.get("accent"): FS["accent"] = _hk["accent"]          # Studio Fonts tab: the big accent words
FS.update(CFG.get("brand_fonts", {})); FS.update(Y.get("fonts", {}))
def _ff(role):
    v = FS[role]; name, w = (v[0], v[1]) if isinstance(v, (list, tuple)) else (v, None)
    path = name if os.path.isabs(name) else os.path.join(FD, name)
    if not os.path.exists(path): print(f"font missing for {role}: {name}, using Inter"); return ("InterDisplay-Bold.otf", None)
    return (path, w)
_F = {r: _ff(r) for r in ("bold", "black", "semi", "med", "accent")}
BOLD = lambda s: font(_F["bold"][0], s, _F["bold"][1])
BLACK = lambda s: font(_F["black"][0], s, _F["black"][1])
SEMI = lambda s: font(_F["semi"][0], s, _F["semi"][1])
MED = lambda s: font(_F["med"][0], s, _F["med"][1])
SERIF = lambda s: font(_F["accent"][0], s, _F["accent"][1])

def ease(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def caps(t): return " ".join(w.capitalize() if w.lower().strip(",.?!") in ("god", "god's", "him", "his", "he") and i > 0 or w == "i" else w for i, w in enumerate(t.split()))

words = json.load(open(os.path.join(WORK, "timeline_words.json")))
TOK = [w["w"].lower().strip(",.?!") for w in words]
def find(phrase, after=0.0):
    ph = phrase.lower().split()
    for i in range(len(TOK)):
        if words[i]["t"] >= after - 0.01 and TOK[i:i + len(ph)] == ph: return words[i]["t"]
    raise SystemExit(f'"{phrase}" not found after {after:.1f}s')

# ---------------------------------------------------------------- drawing helpers
def text_layer(parts, size, gap=0):
    """parts: [(text, font, rgb)] on one line -> RGBA image"""
    tmp = Image.new("RGBA", (10, 10)); d = ImageDraw.Draw(tmp)
    widths = [d.textlength(t, font=f) for t, f, c in parts]
    asc = max(f.getmetrics()[0] for t, f, c in parts); desc = max(f.getmetrics()[1] for t, f, c in parts)
    im = Image.new("RGBA", (int(sum(widths) + gap * (len(parts) - 1)) + 8, asc + desc + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = 4
    for (t, f, c), w in zip(parts, widths):
        d.text((x, 4 + asc), t, font=f, fill=c + (255,), anchor="ls"); x += w + gap
    return im

def fit_layer(text, accent, size, asize, maxw, col=(255, 255, 255), acol=None):
    acol = acol or PINK_L
    while True:
        im = text_layer([(text + " ", BOLD(size), col), (accent, SERIF(asize), acol)] if accent else [(text, BOLD(size), col)], size)
        if im.width <= maxw or size < 40: return im
        size -= 4; asize -= 4

def shadowed(im, r=10, a=0.45):
    pad = r * 3; out = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0)); sh.paste((0, 0, 0, int(255 * a)), (pad, pad + 3), im.split()[3])
    out = Image.alpha_composite(out, sh.filter(ImageFilter.GaussianBlur(r))); out.alpha_composite(im, (pad, pad)); return out, pad

def over(frame, im, x, y, a=1.0):
    """alpha-composite RGBA PIL image onto float numpy frame"""
    if a <= 0: return
    x, y = int(x), int(y); h, w = im.height, im.width
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0: return
    arr = np.asarray(im, np.float32)[y0 - y:y1 - y, x0 - x:x1 - x]
    al = arr[..., 3:4] / 255 * a
    frame[y0:y1, x0:x1] = frame[y0:y1, x0:x1] * (1 - al) + arr[..., :3] * al

def glass(frame, x, y, w, h, r=26, a=1.0, tint=0.42):
    """frosted dark glass panel drawn into the frame (blurs what's behind it)"""
    x, y, w, h = int(x), int(y), int(w), int(h)
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0 or a <= 0: return
    reg = frame[y0:y1, x0:x1]
    bl = cv2.GaussianBlur(reg, (0, 0), 26)
    bl = bl * (1 - tint) + np.array([22, 18, 20], np.float32) * tint + 10
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255)
    m = np.asarray(m, np.float32)[y0 - y:y1 - y, x0 - x:x1 - x, None] / 255 * a
    # soft drop shadow first
    sh = np.zeros((H, W), np.float32); sh[y0 + 10:y1 + 10, x0:x1] = 1
    sh = cv2.GaussianBlur(sh, (0, 0), 22)[..., None] * 0.28 * a
    frame[:] = frame * (1 - sh)
    reg = frame[y0:y1, x0:x1]; frame[y0:y1, x0:x1] = reg * (1 - m) + bl * m
    b = Image.new("RGBA", (w, h), (0, 0, 0, 0)); ImageDraw.Draw(b).rounded_rectangle([1, 1, w - 2, h - 2], r, outline=(255, 255, 255, 46), width=2)
    over(frame, b, x, y, a)

def checkbox(on, s=34):
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if on:
        d.rounded_rectangle([0, 0, s - 1, s - 1], 8, fill=PINK_L + (255,))
        d.line([(s * .26, s * .52), (s * .43, s * .7), (s * .76, s * .3)], fill=ON + (255,), width=4)
    else: d.rounded_rectangle([1, 1, s - 2, s - 2], 8, outline=(255, 255, 255, 110), width=3)
    return im

# ---------------------------------------------------------------- effects
EV = []   # (start, end, kind, data)
cur = 0.0
def span(e, dflt):
    global cur
    s = find(e["at"], cur) - 0.15
    end = find(e["until"], s) if e.get("until") else s + e.get("dur", dflt)
    cur = s + 0.5; return s, end

for t in Y.get("titles", []):
    s, e = span(t, 3.4)
    EV.append((s, e, "title", t))
cur = 0.0
for c in Y.get("checklist", []):
    s, e = span(c, 8); ticks = [find(it[1], s) for it in c["items"]]
    EV.append((s, e, "check", (c, ticks)))
cur = 0.0
for c in Y.get("list", []):
    s, e = span(c, 8); hits = [find(it[1], s) for it in c["items"]]
    EV.append((s, e, "list", (c, hits)))
cur = 0.0
for c in Y.get("compare", []):
    if "start" in c: s, e = c["start"], c["start"] + c.get("dur", 7); hits = [s + h for h in c.get("hits", [0.6 + 2.2 * i for i in range(len(c["rows"]))])]
    else: s, e = span(c, 8); hits = [find(r["at"], s) for r in c["rows"]]
    EV.append((s, e, "compare", (c, hits)))
SPLIT = [(s, e) for s, e, k, d in EV if k in ("list", "compare")]
QUIET_TITLES = [(s, e) for s, e, k, d in EV if k == "title"]

_tc = {}
def title_imgs(f, d):
    """dark ink on a clean light wall (like the reference); white + light pink with a soft shadow on anything busy"""
    k = id(d)
    if k not in _tc:
        x, y = d.get("x", 110), d.get("y", 110)
        reg = cv2.cvtColor(np.clip(f[y:y + 260, x:x + 700], 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
        clean = reg.mean() > 170 and reg.std() < 38
        top = text_layer([(d["top"], BLACK(84), INK if clean else (255, 255, 255))], 84)
        acc = text_layer([(d["word"], SERIF(112), PINK_D if clean else PINK_L)], 112)
        if not clean: top, acc = shadowed(top, 14, .6)[0], shadowed(acc, 14, .6)[0]; x, y = x - 42, y - 42
        _tc[k] = (top, acc, x, y)
    return _tc[k]

def draw_title(f, t, s, e, d):
    top, acc, x, y = title_imgs(f, d); a = ease((t - s) / 0.35) * (1 - ease((t - e + 0.3) / 0.3)); dy = 24 * (1 - ease((t - s) / 0.4))
    over(f, top, x, y + dy, a)
    a2 = ease((t - s - 0.25) / 0.35) * (1 - ease((t - e + 0.3) / 0.3))
    over(f, acc, x - 4, y + top.height - 18 + 24 * (1 - ease((t - s - 0.25) / 0.4)), a2)

def draw_check(f, t, s, e, d):
    c, ticks = d; a = ease((t - s) / 0.35) * (1 - ease((t - e + 0.35) / 0.35))
    rows = c["items"]; w, h = 640, 104 + 74 * len(rows); x, y = W - w - 90, 150 - 20 * (1 - ease((t - s) / 0.4))
    glass(f, x, y, w, h, a=a)
    over(f, text_layer([(c["label"], SEMI(25), GREY)], 25), x + 36, y + 30, a)
    for i, (txt, _) in enumerate(rows):
        on = t >= ticks[i]; yy = y + 84 + i * 74
        over(f, checkbox(on, 38), x + 36, yy, a)
        over(f, text_layer([(txt, SEMI(38), (255, 255, 255) if on else (226, 220, 222))], 38), x + 94, yy - 6, a * (1 if on else 0.8))

def split_amt(t):
    for s, e in SPLIT:
        if s - 0.05 <= t <= e + 0.05: return ease((t - s) / 0.45) * (1 - ease((t - e + 0.45) / 0.45))
    return 0.0

def apply_split(f, t, k):
    """speaker slides into the left half; dark glass fills the right half"""
    src = f.copy(); half = W // 2
    cx = W // 2 + Y.get("face_dx", 0)
    shift = int((cx - half // 2) * k)            # move the face toward the left-half centre
    M = np.float32([[1, 0, -shift], [0, 1, 0]]); moved = cv2.warpAffine(src, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    f[:] = moved
    px = int(W - half * k)
    if px < W:
        reg = cv2.GaussianBlur(src[:, px:], (0, 0), 30) * 0.18 + np.array([24, 20, 22], np.float32) * 0.82
        f[:, px:] = reg
        f[:, max(0, px - 2):px + 1] = np.array(PINK_L, np.float32) * 0.85
    return px

def panel_text(f, x0, a, items):
    for im, x, y, aa in items: over(f, im, x0 + x, y, a * aa)

def draw_list(f, t, s, e, d, px):
    c, hits = d; a = ease((t - s - 0.25) / 0.35) * (1 - ease((t - e + 0.4) / 0.3)); x0 = px + 90
    items = []
    if c.get("label"): items.append((text_layer([(c["label"], SEMI(28), GREY)], 28), 0, 150, 1))
    items.append((fit_layer(c["title"], c.get("accent", ""), 84, 96, W - px - 150), 0, 192, 1))
    for i, (txt, _) in enumerate(c["items"]):
        on = t >= hits[i]; act = on and (i == len(hits) - 1 or t < hits[i + 1]); yy = 370 + i * 110
        if act:
            hl = Image.new("RGBA", (W // 2 - 170, 90), (0, 0, 0, 0)); ImageDraw.Draw(hl).rounded_rectangle([0, 0, hl.width - 1, 89], 16, fill=(255, 255, 255, 22), outline=(255, 255, 255, 40), width=2)
            items.append((hl, -16, yy - 14, 1))
        items.append((text_layer([(f"{i + 1}", BOLD(36), PINK_L if act else GREY), ("   " + txt, SEMI(46), (255, 255, 255) if on else (120, 114, 116))], 36), 6, yy, ease((t - hits[i] + 0.6) / 0.4) * 0.55 + 0.45))
    panel_text(f, x0, a, items)

_ct = {}
def phone_thumb(p):
    im = Image.open(p).convert("RGB"); w, h = 100, 178
    sc = max(w / im.width, h / im.height); im = im.resize((int(im.width * sc + 1), int(im.height * sc + 1)))
    im = im.crop(((im.width - w) // 2, 0, (im.width - w) // 2 + w, h)).convert("RGBA")
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], 12, fill=255); im.putalpha(m)
    fr = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0)); ImageDraw.Draw(fr).rounded_rectangle([0, 0, w + 7, h + 7], 15, fill=(255, 255, 255, 230)); fr.alpha_composite(im, (4, 4)); return fr

def draw_compare(f, t, s, e, d, px):
    c, hits = d; a = ease((t - s - 0.25) / 0.35) * (1 - ease((t - e + 0.4) / 0.3)); x0 = px + 90; items = []
    for i, r in enumerate(c["rows"]):
        k = ease((t - hits[i] + 0.1) / 0.4); yy = 120 + i * (400 if any(rr.get("thumbs") for rr in c["rows"]) else 280)
        items.append((text_layer([(r["label"], SEMI(28), GREY)], 28), 0, yy, k))
        for j, th in enumerate(r.get("thumbs", [])):
            kj = ease((t - hits[i] - 0.4 - j * 0.15) / 0.3)
            if kj > 0:
                if ("ct", th) not in _ct: _ct[("ct", th)] = phone_thumb(th)
                items.append((_ct[("ct", th)], j * 118, yy + 150, kj))
        items.append((fit_layer(r["text"], r["accent"], 86, 100, W - px - 150), 0, yy + 40 + 16 * (1 - k), k))
    panel_text(f, x0, a, items)

# ================================================================ more effects (rounds 2 and 3)
import textwrap
def img_load(p, w=None, h=None, r=0):
    p = p if os.path.isabs(p) else os.path.join(WORK, p)
    im = Image.open(p).convert("RGBA")
    if w and h:
        s = max(w / im.width, h / im.height); im = im.resize((int(im.width * s + 1), int(im.height * s + 1)), Image.LANCZOS)
        x, y = (im.width - w) // 2, 0 if h / w > 1.3 else (im.height - h) // 2; im = im.crop((x, y, x + w, y + h))
    elif w:
        im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    if r:
        m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], r, fill=255); im.putalpha(m)
    return im

def pill(text, on=True, size=26):
    f = SEMI(size); tw = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength(text, font=f)
    im = Image.new("RGBA", (int(tw) + 40, size + 22), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], im.height // 2, fill=(PINK_L + (255,)) if on else (255, 255, 255, 40))
    d.text((im.width / 2, im.height / 2), text, font=f, fill=ON if on else (255, 255, 255), anchor="mm"); return im

def wrap_lines(text, f, maxw):
    out, line = [], ""
    for w in text.split():
        t = (line + " " + w).strip()
        if ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(t, font=f) > maxw and line: out.append(line); line = w
        else: line = t
    if line: out.append(line)
    return out

def fade(t, s, e, ins=0.35, outs=0.35): return ease((t - s) / ins) * (1 - ease((t - e + outs) / outs))
def card_xy(d, w, h, t, s):
    side = d.get("side", "right"); y = d.get("y", 150) - 20 * (1 - ease((t - s) / 0.4))
    return (W - w - 90 if side == "right" else 90), y

def d_clock(f, t, s, e, d, px):
    a = fade(t, s, e); w, h = 380, 360; x, y = card_xy(d, w, h, t, s); glass(f, x, y, w, h, a=a)
    c = Image.new("RGBA", (150, 150), (0, 0, 0, 0)); g = ImageDraw.Draw(c); g.ellipse([4, 4, 145, 145], outline=(255, 255, 255, 220), width=5)
    for k in range(12):
        an = k / 12 * 6.283; g.line([(75 + 58 * np.sin(an), 75 - 58 * np.cos(an)), (75 + 66 * np.sin(an), 75 - 66 * np.cos(an))], fill=(255, 255, 255, 160), width=3)
    sp = (t - s) * 2.4; g.line([(75, 75), (75 + 40 * np.sin(sp / 12), 75 - 40 * np.cos(sp / 12))], fill=(255, 255, 255, 255), width=6)
    g.line([(75, 75), (75 + 56 * np.sin(sp), 75 - 56 * np.cos(sp))], fill=PINK_L + (255,), width=4)
    over(f, c, x + (w - 150) / 2, y + 32, a)
    tl = text_layer([(d.get("word", "few") + " ", BOLD(54), (255, 255, 255)), (d.get("accent", "minutes"), SERIF(60), PINK_L)], 54)
    over(f, tl, x + (w - tl.width) / 2, y + 196, a)
    lb = text_layer([(d.get("label", "AND IT EDITS YOUR VIDEO"), SEMI(20), GREY)], 20); over(f, lb, x + (w - lb.width) / 2, y + 290, a)

def d_calc(f, t, s, e, d, px):
    a = fade(t, s, e); w, h = 400, 540; x, y = card_xy(d, w, h, t, s); glass(f, x, y, w, h, a=a)
    disp = Image.new("RGBA", (w - 48, 150), (0, 0, 0, 0)); ImageDraw.Draw(disp).rounded_rectangle([0, 0, w - 49, 149], 16, fill=(10, 8, 9, 150))
    over(f, disp, x + 24, y + 24, a)
    k = ease((t - s - 0.5) / max(0.6, (e - s) * 0.5)); v = d.get("from", 0) + (d.get("to", 20) - d.get("from", 0)) * k
    num = text_layer([(f'{d.get("prefix", "$")}{v:,.0f}', BOLD(76), (255, 255, 255))], 76); over(f, num, x + w - 40 - num.width, y + 70, a)
    lb = text_layer([(d.get("label", "a month"), SEMI(20), GREY)], 20); over(f, lb, x + w - 44 - lb.width, y + 40, a)
    keys = ["7", "8", "9", "÷", "4", "5", "6", "×", "1", "2", "3", "−", "0", ".", "=", "+"]
    for i, kk in enumerate(keys):
        kx, ky = x + 28 + (i % 4) * 88, y + 200 + (i // 4) * 80
        on = kk == "="; b = Image.new("RGBA", (76, 64), (0, 0, 0, 0)); bd = ImageDraw.Draw(b)
        bd.rounded_rectangle([0, 0, 75, 63], 14, fill=(PINK_L + (235,)) if on else (255, 255, 255, 26))
        bd.text((38, 32), kk, font=SEMI(28), fill=INK if on else (235, 230, 232), anchor="mm"); over(f, b, kx, ky, a)
    for i, p in enumerate(d.get("pills", [])):
        pa = a * ease((t - s - 0.6 - i * 0.4) / 0.3)
        if pa > 0: pi = pill(p, i == len(d["pills"]) - 1); over(f, pi, x - pi.width - 24, y + 60 + i * 64, pa)

def d_meter(f, t, s, e, d, px):
    a = fade(t, s, e); tl = shadowed(text_layer([(d.get("big", "3–4 h") + " ", BOLD(80), (255, 255, 255)), (d.get("accent", "one reel"), SERIF(54), PINK_L)], 80), 12, .5)[0]
    x = W - tl.width - 60 if d.get("side", "right") == "right" else 60; y = d.get("y", 90); over(f, tl, x, y, a)
    n = d.get("blocks", 4)
    for i in range(n):
        on = t > s + 0.5 + i * 0.35; b = Image.new("RGBA", (64, 34), (0, 0, 0, 0))
        ImageDraw.Draw(b).rounded_rectangle([0, 0, 63, 33], 9, fill=(PINK_L + (255,)) if on else (255, 255, 255, 70)); over(f, b, x + 40 + i * 76, y + tl.height - 20, a)

def d_plan(f, t, s, e, d, px):
    a = fade(t, s, e); items = d.get("items", []); w = 600; h = 110 + 52 * len(items) + 100; x, y = card_xy(d, w, h, t, s); glass(f, x, y, w, h, a=a)
    over(f, text_layer([(d.get("label", "CLAUDE · QUICK PLAN"), SEMI(24), GREY)], 24), x + 36, y + 28, a)
    for i, it in enumerate(items):
        last = i == len(items) - 1 and d.get("accent_last", True)
        parts = [("• ", SEMI(34), (255, 255, 255))] + ([(it.split(":")[0] + ": ", SEMI(34), (255, 255, 255)), (it.split(":", 1)[1].strip(), SERIF(38), PINK_L)] if last and ":" in it else [(it, SEMI(34), (255, 255, 255))])
        over(f, text_layer(parts, 34), x + 36, y + 74 + i * 52, a * ease((t - s - 0.2 - i * 0.18) / 0.3))
    by = y + h - 92; click = s + (e - s) * 0.6; pressed = t >= click
    yes = Image.new("RGBA", (250, 64), (0, 0, 0, 0)); ImageDraw.Draw(yes).rounded_rectangle([0, 0, 249, 63], 14, fill=(PRESSED if pressed else PINK_L) + (255,))
    ImageDraw.Draw(yes).text((125, 32), "Yes", font=BOLD(32), fill=ON, anchor="mm"); over(f, yes, x + 36, by, a)
    no = Image.new("RGBA", (250, 64), (0, 0, 0, 0)); ImageDraw.Draw(no).rounded_rectangle([0, 0, 249, 63], 14, fill=(255, 255, 255, 26))
    ImageDraw.Draw(no).text((125, 32), "No", font=BOLD(32), fill=(240, 236, 238), anchor="mm"); over(f, no, x + 314, by, a)
    k = ease((t - s - 0.6) / max(0.4, click - s - 0.6)); cx, cy = x + 520 + (x + 160 - x - 520) * k, by + 160 + (34 - 160) * k
    cur_ = Image.new("RGBA", (40, 50), (0, 0, 0, 0)); ImageDraw.Draw(cur_).polygon([(4, 2), (4, 40), (14, 30), (22, 46), (29, 43), (21, 27), (35, 27)], fill=(255, 255, 255, 255), outline=(20, 20, 20, 255))
    over(f, cur_, cx, cy, a * (1 - ease((t - click - 0.6) / 0.3)))

def d_prompt(f, t, s, e, d, px):
    a = fade(t, s, e); w, h = 660, 150; x, y = card_xy(d, w, h, t, s); glass(f, x, y, w, h, a=a)
    over(f, text_layer([(d.get("label", "CLAUDE"), SEMI(22), GREY)], 22), x + 30, y + 22, a)
    box = Image.new("RGBA", (w - 60, 66), (0, 0, 0, 0)); ImageDraw.Draw(box).rounded_rectangle([0, 0, w - 61, 65], 14, fill=(10, 8, 9, 150), outline=(255, 255, 255, 40), width=2); over(f, box, x + 30, y + 60, a)
    txt = d.get("text", "edit my new video"); n = int(len(txt) * min(1, max(0, (t - s - 0.4) / max(0.5, (e - s) * 0.55))))
    caret = "|" if int(t * 2.5) % 2 == 0 else " "
    over(f, text_layer([(txt[:n] + caret, SEMI(32), (255, 255, 255))], 32), x + 50, y + 68, a)

def d_note(f, t, s, e, d, px):
    a = fade(t, s, e); fb = BOLD(52); lines = [d.get("big", "")]; sm = d.get("small", "")
    w = max(int(ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(d.get("big", ""), font=fb)) + 80, 420); h = 190 if sm else 140
    x, y = card_xy(d, w, h, t, s); glass(f, x, y, w, h, a=a)
    over(f, text_layer([(d.get("label", ""), SEMI(22), GREY)], 22), x + 36, y + 26, a)
    over(f, text_layer([(d.get("big", ""), fb, (255, 255, 255))], 52), x + 34, y + 58, a)
    if sm: over(f, text_layer([(sm, SERIF(36), PINK_L)], 36), x + 36, y + 128, a)

def d_message(f, t, s, e, d, px):
    a = fade(t, s, e); w = 640; lines = wrap_lines(d.get("text", ""), MED(32), w - 80); h = 90 + 44 * len(lines) + (80 if d.get("pill") else 20)
    x, y = card_xy(d, w, h, t, s); glass(f, x, y, w, h, a=a)
    over(f, text_layer([(d.get("label", "MESSAGE"), SEMI(22), GREY)], 22), x + 36, y + 26, a)
    for i, l in enumerate(lines): over(f, text_layer([(l, MED(32), (235, 230, 232))], 32), x + 36, y + 62 + i * 44, a)
    if d.get("pill"):
        pa = a * ease((t - s - 1.0) / 0.3); pi = pill(d["pill"]); over(f, pi, x + w - pi.width - 30, y + h - 66, pa)

def d_days(f, t, s, e, d, px):
    a = fade(t, s, e); n = d.get("n", 7); w = 120 + n * 62; notes = d.get("notes", []); h = 236 + 46 * len(notes)
    im = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0)); sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([30, 38, 30 + w, 38 + h], 10, fill=(0, 0, 0, 90)); im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(14)))
    g = ImageDraw.Draw(im); g.rounded_rectangle([30, 30, 30 + w, 30 + h], 10, fill=(250, 249, 247, 255))
    g.text((64, 60), d.get("title", "7 days"), font=BOLD(46), fill=INK); g.text((64, 112), d.get("accent", ""), font=SERIF(36), fill=PINK_D)
    filled = int(min(n, max(0, (t - s - 0.4) / max(0.2, (e - s) * 0.5 / n))))
    for i in range(n):
        bx = 64 + i * 62; on = i < filled
        g.rounded_rectangle([bx, 166, bx + 48, 214], 8, fill=PINK_D if on else None, outline=PINK_D if on else (60, 56, 58), width=3)
        g.text((bx + 24, 190), str(i + 1), font=SEMI(24), fill=(255, 255, 255) if on else INK, anchor="mm")
    for i, nt in enumerate(notes):
        if t > s + 1.2 + i * 0.8: g.text((64, 236 + i * 46), nt, font=SEMI(28), fill=INK)
    im = im.rotate(d.get("tilt", -2), resample=Image.BICUBIC, expand=True); x, y = card_xy(d, im.width - 60, h, t, s); over(f, im, x - 30, y - 30, a)

def d_name(f, t, s, e, d, px):
    a = fade(t, s, e); top = shadowed(text_layer([(d.get("hi", ("I'm " + CFG.get("brand", {}).get("first_name", "") + ",") if CFG.get("brand", {}).get("first_name") else "Hi, I'm"), BOLD(64), (255, 255, 255))], 64), 12, .55)[0]
    acc = shadowed(text_layer([(d.get("word", "creator"), SERIF(104), PINK_L)], 104), 12, .55)[0]
    x, y = d.get("x", 70), d.get("y", 80); over(f, top, x, y + 20 * (1 - ease((t - s) / 0.4)), a)
    over(f, acc, x - 6, y + top.height - 40 + 20 * (1 - ease((t - s - 0.25) / 0.4)), a * ease((t - s - 0.25) / 0.35))
    if d.get("icon"):
        ic = img_load(d["icon"], 120) if os.path.exists(os.path.join(WORK, d["icon"])) or os.path.isabs(d["icon"]) else None
        if ic: over(f, ic, x + acc.width - 30, y + top.height, a)

def d_corner(f, t, s, e, d, px):
    a = fade(t, s, e); sm = shadowed(text_layer([(d.get("small", ""), SEMI(28), (230, 225, 227))], 28), 8, .5)[0]
    bg = shadowed(text_layer([(d.get("big", ""), BOLD(76), (255, 255, 255))], 76), 12, .55)[0]
    x = W - bg.width - 50; over(f, sm, x + 6, 50, a); over(f, bg, x, 80 + 14 * (1 - ease((t - s) / 0.4)), a)

def d_cta(f, t, s, e, d, px):
    a = fade(t, s, e); tl = text_layer([(d.get("text", "Tap the button") + " ", BOLD(64), (255, 255, 255)), (d.get("accent", "below"), SERIF(74), PINK_L)], 64)
    w, h = tl.width + 70, tl.height + 34; x, y = (W - w) / 2, 70 - 20 * (1 - ease((t - s) / 0.4)); glass(f, x, y, w, h, r=24, a=a); over(f, tl, x + 35, y + 17, a)
    ar = Image.new("RGBA", (90, 120), (0, 0, 0, 0)); g = ImageDraw.Draw(ar); g.rectangle([36, 0, 54, 70], fill=PINK_L + (255,)); g.polygon([(10, 64), (80, 64), (45, 112)], fill=PINK_L + (255,))
    bob = 12 * np.sin((t - s) * 6); over(f, ar, d.get("ax", W - 380), d.get("ay", H - 300) + bob, a * ease((t - s - 0.4) / 0.3))

_pip = {}
def pip_frames(src, w, h, n, start=0):
    k = (src, w, h, start)
    if k not in _pip:
        p = src if os.path.isabs(src) else os.path.join(WORK, src)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-i", p, "-t", f"{n / 15 + 0.2:.2f}", "-vf", f"fps=15,scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        fr = [np.frombuffer(raw[i:i + w * h * 3], np.uint8).reshape(h, w, 3) for i in range(0, len(raw) - w * h * 3 + 1, w * h * 3)]
        _pip[k] = fr or [np.zeros((h, w, 3), np.uint8)]
    return _pip[k]

def phone_frame(screen, w, h):
    im = Image.new("RGBA", (w + 24, h + 24), (0, 0, 0, 0)); g = ImageDraw.Draw(im); g.rounded_rectangle([0, 0, w + 23, h + 23], 44, fill=(16, 14, 15, 255), outline=(255, 255, 255, 60), width=2)
    sc = Image.fromarray(screen).convert("RGBA"); m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], 34, fill=255); sc.putalpha(m); im.alpha_composite(sc, (12, 12))
    g.rounded_rectangle([(w + 24) / 2 - 40, 22, (w + 24) / 2 + 40, 44], 11, fill=(16, 14, 15, 255)); return im

def d_phone(f, t, s, e, d, px):
    a = fade(t, s, e); pw, ph = 300, 534
    fr = pip_frames(d["src"], pw, ph, int((e - s) * 15) + 2, d.get("start", 0)); i = min(len(fr) - 1, int((t - s) * 15))
    im = phone_frame(fr[i], pw, ph); x = W - im.width - 120 if d.get("side", "right") == "right" else 120; y = 150 + 40 * (1 - ease((t - s) / 0.4))
    over(f, shadowed(im, 16, .45)[0], x - 48, y - 48, a)
    if d.get("label"): lb = shadowed(text_layer([(d["label"], SEMI(22), (255, 255, 255))], 22), 6, .6)[0]; over(f, lb, x + (im.width - lb.width) / 2, y + im.height + 8, a)
    for k, p in enumerate(d.get("pills", [])):
        pa = a * ease((t - s - 0.8 - k * 0.45) / 0.3)
        if pa > 0: pi = pill(p); over(f, pi, x - pi.width - 20 if d.get("side", "right") == "right" else x + im.width + 20, y + 120 + k * 70, pa)

def folder_icon(w=230, h=180, col=(246, 180, 200)):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); g = ImageDraw.Draw(im); dk = tuple(int(c * .88) for c in col)
    g.rounded_rectangle([0, 0, w * .42, h * .3], 14, fill=dk + (255,)); g.rounded_rectangle([0, h * .16, w - 1, h - 1], 18, fill=col + (255,)); return im

def d_folder(f, t, s, e, d, px):
    a = fade(t, s, e); fo = folder_icon(); x, y = W - 420, 300; over(f, shadowed(fo, 14, .35)[0], x - 42, y - 42 + 20 * (1 - ease((t - s) / 0.4)), a)
    lb = shadowed(text_layer([(d.get("label", "New Videos"), SEMI(32), (255, 255, 255))], 32), 8, .6)[0]; over(f, lb, x + (fo.width - lb.width) / 2, y + fo.height + 6, a)
    k = ease((t - s - 0.7) / 0.6)
    if k > 0:
        fl = Image.new("RGBA", (120, 150), (0, 0, 0, 0)); g = ImageDraw.Draw(fl); g.rounded_rectangle([0, 0, 119, 149], 12, fill=(255, 255, 255, 255))
        g.polygon([(46, 52), (46, 98), (84, 75)], fill=PINK_D); g.text((60, 128), d.get("file", "IMG_0427.MOV"), font=SEMI(14), fill=INK, anchor="mm")
        fx_ = x + 55 - 300 * (1 - k); fy = y - 180 + 200 * k * k
        over(f, fl, fx_, fy, a * min(1, (1 - k) * 4 + 0.0) if k > 0.9 else a)

def d_timeline(f, t, s, e, d, px):
    a = fade(t, s, e); n = 7; tw, th = 90, 52; w = n * (tw + 6) + 40; x, y = W - w - 70, d.get("y", 740)
    glass(f, x, y, w, 210, r=20, a=a)
    over(f, text_layer([("TIMELINE", SEMI(20), GREY)], 20), x + 22, y + 14, a)
    fr = pip_frames("base.mp4", tw, th, 1, d.get("thumb_from", 1.0))
    if len(_pip.get(("thumbs", s), [])) == 0:
        _pip[("thumbs", s)] = [pip_frames("base.mp4", tw, th, 1, d.get("thumb_from", 1.0) + k * 3)[0] for k in range(n)]
    cut = s + 1.0
    for k, im in enumerate(_pip[("thumbs", s)]):
        if k in d.get("cut", [2, 5]) and t > cut:
            continue
        pi = Image.fromarray(im).convert("RGBA"); m = Image.new("L", pi.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, tw - 1, th - 1], 8, fill=255); pi.putalpha(m)
        off = sum(1 for c in d.get("cut", [2, 5]) if c < k) * (tw + 6) * ease((t - cut) / 0.4) if t > cut else 0
        over(f, pi, x + 20 + k * (tw + 6) - off, y + 48, a)
    ws = d.get("words", "give me one evening and you'll install").split()
    xx = x + 20
    for k, wd in enumerate(ws):
        if t < s + 0.4 + k * 0.12: break
        b = pill(wd, True, 20); over(f, b, xx, y + 126, a); xx += b.width + 6
    if d.get("tag"):
        pa = a * ease((t - s - 0.5) / 0.3); pi = pill(d["tag"], True, 26); over(f, pi, x + 20, y - 62, pa)

def d_presets(f, t, s, e, d, px):
    a = fade(t, s, e, 0.3, 0.3)
    bg = np.ones_like(f) * np.array([248, 245, 246], np.float32); f[:] = f * (1 - a) + bg * a
    tl = text_layer([(d.get("title", "ready") + " ", BOLD(80), INK), (d.get("accent", "presets"), SERIF(92), PINK_D)], 80); over(f, tl, (W - tl.width) / 2, 90, a)
    cards = d.get("cards", []); cw, chh = 290, 516; gap = 50; total = len(cards) * cw + (len(cards) - 1) * gap; x0 = (W - total) / 2
    for i, (src, name) in enumerate(cards):
        k = ease((t - s - 0.3 - i * 0.35) / 0.45)
        if k <= 0: continue
        if ("pc", src) not in _pip: _pip[("pc", src)] = shadowed(img_load(src, cw, chh, 22), 16, .3)[0]
        im = _pip[("pc", src)]; over(f, im, x0 + i * (cw + gap) - 48, 260 - 48 + 60 * (1 - k), a * k)
        lb = text_layer([(name, SERIF(40), PINK_D)], 40); over(f, lb, x0 + i * (cw + gap) + (cw - lb.width) / 2, 800, a * k)

def d_panel_check(f, t, s, e, d, px):
    a = fade(t, s + 0.25, e, 0.35, 0.3); x0 = px + 90; items = d.get("items", []); hits = d["_hits"]
    over(f, text_layer([(d.get("label", ""), SEMI(28), GREY)], 28), x0, 120, a)
    over(f, fit_layer(d.get("title", ""), d.get("accent", ""), 76, 88, W - px - 150), x0, 156, a)
    for i, it in enumerate(items):
        k = ease((t - hits[i]) / 0.3)
        if k <= 0: continue
        over(f, checkbox(True, 40), x0, 288 + i * 70, a * k); over(f, text_layer([(it[0], SEMI(40), (255, 255, 255))], 40), x0 + 60, 282 + i * 70, a * k)
    if d.get("image"):
        yy = 300 + 70 * len(items) + 10
        if ("pi", d["image"]) not in _pip: _pip[("pi", d["image"])] = img_load(d["image"], W // 2 - 200, None, 16)
        im = _pip[("pi", d["image"])]; im = im.crop((0, 0, im.width, min(im.height, H - yy - 110)))
        fr_ = Image.new("RGBA", (im.width + 16, im.height + 16), (0, 0, 0, 0)); ImageDraw.Draw(fr_).rounded_rectangle([0, 0, fr_.width - 1, fr_.height - 1], 20, fill=(255, 255, 255, 30)); fr_.alpha_composite(im, (8, 8))
        over(f, fr_, x0 - 8, yy, a * ease((t - s - 0.8) / 0.4))
        if d.get("caption"): over(f, text_layer([(d["caption"], SEMI(22), GREY)], 22), x0, yy + fr_.height + 12, a)

def d_panel_app(f, t, s, e, d, px):
    a = fade(t, s + 0.25, e, 0.35, 0.3); x0 = px + 70; ww = W // 2 - 140
    if ("pa", d["image"]) not in _pip:
        im = img_load(d["image"], ww - 20); im = im.crop((0, 0, im.width, min(im.height, 560)))
        win = Image.new("RGBA", (ww, im.height + 56), (0, 0, 0, 0)); g = ImageDraw.Draw(win); g.rounded_rectangle([0, 0, ww - 1, win.height - 1], 18, fill=(36, 32, 34, 255), outline=(255, 255, 255, 50), width=2)
        for k, c in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]): g.ellipse([20 + k * 26, 16, 36 + k * 26, 32], fill=c)
        if d.get("title"): g.text((ww / 2, 24), d["title"], font=SEMI(20), fill=(220, 214, 216), anchor="mm")
        win.alpha_composite(im, (10, 46)); _pip[("pa", d["image"])] = shadowed(win, 18, .45)[0]
    win = _pip[("pa", d["image"])]; over(f, win, x0 - 54, 130 - 54 + 30 * (1 - ease((t - s - 0.3) / 0.4)), a)
    xx = x0
    for k, p in enumerate(d.get("pills", [])):
        if t < d["_hits"][k]: break
        pi = pill(p, True, 30); over(f, pi, xx, 130 + win.height - 80, a * ease((t - d["_hits"][k]) / 0.25)); xx += pi.width + 14

def d_compare_thumbs(f, t, s, e, d, px):
    pass

DRAW = {"clock": d_clock, "calc": d_calc, "meter": d_meter, "plan": d_plan, "prompt": d_prompt, "note": d_note, "message": d_message, "days": d_days,
        "name": d_name, "corner": d_corner, "cta": d_cta, "phone": d_phone, "folder": d_folder, "timeline": d_timeline, "presets": d_presets,
        "panel_check": d_panel_check, "panel_app": d_panel_app}
SPLIT_TYPES = {"panel_check", "panel_app"}
cur = 0.0
for e_ in Y.get("fx", []):
    if "start" in e_: s_ = e_["start"]; en_ = s_ + e_.get("dur", 4)
    else: s_, en_ = span(e_, e_.get("dur", 4))
    if "hits" in e_: e_["_hits"] = [s_ + h for h in e_["hits"]]
    elif e_["type"] in ("panel_check",): e_["_hits"] = [s_ + 0.8 + i * 0.7 for i in range(len(e_.get("items", [])))]
    elif e_["type"] == "panel_app": e_["_hits"] = [s_ + 1.2 + i * 0.6 for i in range(len(e_.get("pills", [])))]
    EV.append((s_, en_, e_["type"], e_))
    if e_["type"] in SPLIT_TYPES: SPLIT.append((s_, en_))
EV.sort(key=lambda r: 0 if r[2] == "presets" else 1)
# ================================================================

# ---------------------------------------------------------------- subtitles: small lead-in line + big bold line, accent words in pink serif
ACC = set(w.lower() for w in Y.get("accent", []))
def chunks():
    out, cur_ = [], []
    for i, w in enumerate(words):
        gap = (words[i + 1]["t"] - w["te"]) if i + 1 < len(words) else 1
        cur_.append(i)
        if len(cur_) >= 4 or gap > 0.28 or w["w"].endswith((",", ".", "?")) or (len(cur_) >= 2 and TOK[i] in ACC):
            out.append(cur_); cur_ = []
    if cur_: out.append(cur_)
    return out
SUBS = []
for ch in chunks():
    s = words[ch[0]]["t"]; e = words[ch[-1]]["te"] + 0.12
    lead = ch[:-2] if len(ch) > 2 else ch[:-1]; big = ch[len(lead):]
    SUBS.append((s, e, lead, big))
for i in range(len(SUBS) - 1):
    s, e, l, b = SUBS[i]; SUBS[i] = (s, min(e + 0.25, SUBS[i + 1][0]), l, b)
_sc = {}
def sub_img(k):
    if k in _sc: return _sc[k]
    s, e, lead, big = SUBS[k]
    def w(i): return caps(words[i]["w"]) if i else words[i]["w"]
    l = text_layer([(" ".join(caps(words[i]["w"]) for i in lead), SEMI(34), (255, 255, 255))], 34) if lead else None
    parts = []
    for j, i in enumerate(big):
        txt = caps(words[i]["w"]) + (" " if j < len(big) - 1 else "")
        parts.append((txt, SERIF(64), PINK_L) if TOK[i] in ACC else (txt, BOLD(56), (255, 255, 255)))
    b = text_layer(parts, 56)
    _sc[k] = (shadowed(l, 8, .55) if l else None, shadowed(b, 10, .55)); return _sc[k]

def draw_subs(f, t, px):
    for k, (s, e, lead, big) in enumerate(SUBS):
        if s <= t < e:
            l, b = sub_img(k); a = ease((t - s) / 0.12)
            x = 96; yb = H - 150
            if l: over(f, l[0], x - l[1], yb - 52 - l[1], a)
            over(f, b[0], x - b[1], yb - b[1], a); return

# ---------------------------------------------------------------- render
base = os.path.join(WORK, "base.mp4"); out = os.path.join(WORK, "out"); os.makedirs(out, exist_ok=True)
dst = os.path.join(out, CFG.get("name", "youtube") + ".mp4")
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", base], capture_output=True, text=True).stdout)
rd = subprocess.Popen(["ffmpeg", "-v", "error", "-i", base, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
wr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", base,
                       "-map", "0:v", "-map", "1:a", "-c:v", "libx264", *TAGS, "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                       "-c:a", "copy", "-movflags", "+faststart", "-shortest", dst], stdin=subprocess.PIPE)
STILLS = [float(x) for x in os.environ.get("STILLS", "").split(",") if x]
if STILLS: wr.stdin.close(); wr.kill()
n = 0
while True:
    raw = rd.stdout.read(W * H * 3)
    if len(raw) < W * H * 3: break
    t = n / FPS
    if STILLS:
        if not any(abs(t - x) < 0.5 / FPS for x in STILLS): n += 1; continue
    f = np.frombuffer(raw, np.uint8).reshape(H, W, 3).astype(np.float32)
    k = split_amt(t); px = W
    if k > 0: px = apply_split(f, t, k)
    for s, e, kind, d in EV:
        if not (s <= t <= e): continue
        if kind == "title": draw_title(f, t, s, e, d)
        elif kind == "check": draw_check(f, t, s, e, d)
        elif kind == "list": draw_list(f, t, s, e, d, px)
        elif kind == "compare": draw_compare(f, t, s, e, d, px)
        elif kind in DRAW: DRAW[kind](f, t, s, e, d, px)
    if not any(k_ == "presets" and s_ <= t <= e_ for s_, e_, k_, d_ in EV): draw_subs(f, t, px)
    if STILLS: Image.fromarray(np.clip(f, 0, 255).astype(np.uint8)).save(os.path.join(out, f"still_{t:05.1f}.jpg"), quality=88); n += 1; continue
    wr.stdin.write(np.clip(f, 0, 255).astype(np.uint8).tobytes()); n += 1
if not STILLS: wr.stdin.close(); wr.wait()
print("ok", dst, "effects:", ", ".join(f"{k}@{s:.1f}s" for s, e, k, d in EV))
