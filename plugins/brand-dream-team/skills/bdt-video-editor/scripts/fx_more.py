"""The rest of the Studio effect library, drawn live on the creator's video (used by fx_live.py).
Camera effects cut the creator out (seg.py) so graphics can sit behind her.
Pictures: the effect's own "photos"/"image", else the project's photos, else sharp stills from her own video."""
import math, os
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter
import fx, fx2, fx3
from fx import font, ease, back, over, card, rgba_text, scale_rgba, rotate_rgba, INK, W, H, FPS
from seg import person_mask
fx3.F_DIR = fx.F

CTX = {"work": "", "photos": [], "acc": (245, 186, 203), "on": (10, 10, 10), "brand": {}}

def acc(): return CTX["acc"]

def fit(img):
    """any picture -> 1080x1920 cover crop"""
    h, w = img.shape[:2]; s = max(W / w, H / h)
    r = cv2.resize(img, (int(w * s + 1), int(h * s + 1)), interpolation=cv2.INTER_AREA)
    y = (r.shape[0] - H) // 2; x = (r.shape[1] - W) // 2
    return r[y:y + H, x:x + W]

def load(path):
    p = path if os.path.isabs(path) else os.path.join(CTX["work"], path)
    im = cv2.imread(p, cv2.IMREAD_COLOR)
    return None if im is None else cv2.cvtColor(im, cv2.COLOR_BGR2RGB)

def pics(P, n):
    out = [load(p) for p in P.get("photos", [])]
    out = [fit(i) for i in out if i is not None]
    pool = CTX["photos"]
    j = 0
    while len(out) < n and pool: out.append(pool[j % len(pool)]); j += 1
    return out[:n]

def person_over(dst, frame, m): return dst * (1 - m[..., None]) + frame * m[..., None]

class Base:
    cut = False
    def __init__(s, P, first):
        s.P = P; s.first = first; s.m = None; s.k = 0
    def mask(s, f):
        if s.m is None or s.k % 2 == 0:
            m = person_mask(f.astype(np.uint8))
            s.m = m if s.m is None else 0.65 * m + 0.35 * s.m
        s.k += 1; return s.m

def tape(text, deg, size=50):
    f = font("PlayfairDisplay-BoldItalic.ttf", size); w = int(f.getlength(text)) + 60
    im = Image.new("RGBA", (w + 20, int(size * 2)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([10, 10, w + 10, size * 2 - 10], fill=acc() + (235,))
    d.text((w / 2 + 10, size), text, font=f, fill=CTX["on"], anchor="mm")
    return rotate_rgba(np.array(im), deg)

def accent_text(text, size=110):
    return rgba_text(text, font("PlayfairDisplay-BoldItalic.ttf", size), acc() + (255,))

def fitw(text, fname, size, maxw, **kw):
    f = font(fname, size)
    while f.getlength(text) > maxw and size > 40: size -= 10; f = font(fname, size)
    return f

# ------------------------------------------------------------------ camera (cutout) effects
class Orbit(Base):
    """photos circle around her, passing behind and in front"""
    def __init__(s, P, first):
        super().__init__(P, first)
        s.pols = [fx.polaroid(p, 260, d) for p, d in zip(pics(P, 3), (-8, 6, -4))]
        s.word = accent_text(P["word"], 150) if P.get("word") else None
    def draw(s, bg, t, dur):
        f = bg.copy(); m = s.mask(f); a = ease(t / 0.4) * (1 - ease((t - dur + 0.35) / 0.35)); items = []
        for j, p in enumerate(s.pols):
            ang = t * 1.6 + j * 2 * math.pi / max(1, len(s.pols)); dp = math.sin(ang)
            items.append((dp, scale_rgba(p, 0.78 + 0.28 * (dp + 1) / 2), 540 + 420 * math.cos(ang), 1130 + 150 * dp))
        items.sort(key=lambda z: z[0])
        for d, p, x, y in items:
            if d < 0: over(bg, p, x - p.shape[1] / 2, y - p.shape[0] / 2, a)
        bg[:] = person_over(bg, f, m)
        for d, p, x, y in items:
            if d >= 0: over(bg, p, x - p.shape[1] / 2, y - p.shape[0] / 2, a)
        if s.word is not None: over(bg, s.word, (W - s.word.shape[1]) / 2, 1500, ease((t - 0.3) / 0.4))

class GlassType(Base):
    """one huge word rises up behind her"""
    def __init__(s, P, first):
        super().__init__(P, first); txt = P.get("word", "").upper()
        s.big = rgba_text(txt, fitw(txt, "InterDisplay-Black.otf", 300, W - 60), (255, 255, 255, 240), shadow=0.3, track=-14)
    def draw(s, bg, t, dur):
        f = bg.copy(); m = s.mask(f); e = ease(t / 0.5) * (1 - ease((t - dur + 0.3) / 0.3))
        over(bg, s.big, (W - s.big.shape[1]) / 2, 330 + 160 * (1 - ease(t / 0.5)), e)
        bg[:] = person_over(bg, f, m)

class Doodle(Base):
    """white outline traces her, hand-drawn doodles appear"""
    kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (29, 29))
    def draw(s, bg, t, dur):
        f = bg.copy(); m = s.mask(f); fade = 1 - ease((t - dur + 0.3) / 0.3)
        ring = np.clip(cv2.dilate((m > 0.5).astype(np.uint8), s.kern).astype(np.float32) - m, 0, 1) * ease(t / 0.3) * fade
        bg[:] = bg * (1 - ring[..., None]) + 255 * ring[..., None]
        if s.k % 3 == 1 or not hasattr(s, "dl"): s.dl = fx.doodle_layer(ease((t - 0.2) / 1.2))
        over(bg, s.dl, 0, 0, fade)

class GreenScreen(Base):
    """her background swaps for a picture or screenshot (or a brand-color title card)"""
    def __init__(s, P, first):
        super().__init__(P, first)
        img = load(P["image"]) if P.get("image") else None
        if img is None:
            canvas = Image.new("RGB", (W, H), (24, 22, 25)); d = ImageDraw.Draw(canvas)
            title = P.get("title", ""); ft = fitw(title, "InterDisplay-Bold.otf", 84, W - 160)
            d.rounded_rectangle([60, 200, W - 60, 760], 40, fill=(38, 34, 39))
            d.text((W / 2, 400), title, font=ft, fill="white", anchor="mm")
            d.rounded_rectangle([140, 540, W - 140, 570], 15, fill=acc())
            s.bgimg = np.array(canvas).astype(np.float32)
        else:
            s.bgimg = fit(img).astype(np.float32)
    def draw(s, bg, t, dur):
        f = bg.copy(); m = s.mask(f); e = ease(t / 0.35) * (1 - ease((t - dur + 0.3) / 0.3))
        bg[:] = person_over(f * (1 - e) + s.bgimg * e, f, m)

class FrameBreak(Base):
    """a frame drops around her, everything outside dims, she stays in front of the frame"""
    def __init__(s, P, first):
        super().__init__(P, first); x0, y0, x1, y1 = 70, 560, 1010, 1880; s.x0, s.y0 = x0, y0
        fr = Image.new("L", (W, H), 0); ImageDraw.Draw(fr).rounded_rectangle([x0, y0, x1, y1], 44, fill=255)
        s.inside = cv2.GaussianBlur(np.array(fr).astype(np.float32) / 255, (5, 5), 0)
        b = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(b).rounded_rectangle([x0, y0, x1, y1], 44, outline=(255, 255, 255, 250), width=10)
        s.bd = np.array(b)
        h = P.get("handle") or CTX["brand"].get("handle", "")
        s.tag = rgba_text("@" + h.lstrip("@"), font("InterDisplay-SemiBold.otf", 34), (255, 255, 255, 255), shadow=0.5) if h else None
    def draw(s, bg, t, dur):
        f = bg.copy(); m = s.mask(f); e = ease(t / 0.4) * (1 - ease((t - dur + 0.3) / 0.3))
        dim = cv2.GaussianBlur(f, (0, 0), 18) * 0.28; inn = s.inside[..., None] * e + (1 - e)
        bg[:] = f * inn + dim * (1 - inn); over(bg, s.bd, 0, 0, e)
        if s.tag is not None: over(bg, s.tag, s.x0 + 10, s.y0 + 6, e)
        bg[:] = person_over(bg, f, m)

class PaperCut(Base):
    """she becomes a paper cut-out on a notebook page with a taped label"""
    def __init__(s, P, first):
        super().__init__(P, first); fx.ROSE = acc(); s.pb = fx.paper_bg(); s.tg = tape(P["tag"], 8) if P.get("tag") else None
    def draw(s, bg, t, dur):
        f = bg.copy(); m = s.mask(f); e = ease(t / 0.4) * (1 - ease((t - dur + 0.3) / 0.3)); sc = 1 - 0.12 * e
        fs = cv2.resize(f, None, fx=sc, fy=sc); ms = cv2.resize(m, None, fx=sc, fy=sc)
        ox, oy = (W - fs.shape[1]) // 2, H - fs.shape[0]
        canvas = f * (1 - e) + s.pb * e
        sh = cv2.GaussianBlur(ms, (0, 0), 12) * 0.35 * e
        reg = canvas[oy:oy + fs.shape[0], ox:ox + fs.shape[1]]; reg *= (1 - sh[..., None])
        mm = ms * e + (1 - e); reg[:] = reg * (1 - mm[..., None]) + fs * mm[..., None]
        if s.tg is not None: over(canvas, s.tg, 640, 420, ease((t - 0.5) / 0.3) * (1 - ease((t - dur + 0.3) / 0.3)))
        bg[:] = canvas

class Vertigo(Base):
    """the room pushes away behind her while she stays still"""
    def draw(s, bg, t, dur):
        f = bg.copy(); m = s.mask(f)
        small = cv2.resize(f.astype(np.uint8), (W // 4, H // 4)); ms = cv2.resize((m > 0.3).astype(np.uint8), (W // 4, H // 4))
        ms = cv2.dilate(ms, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
        clean = cv2.GaussianBlur(cv2.resize(cv2.inpaint(small, ms * 255, 7, cv2.INPAINT_TELEA), (W, H)), (0, 0), 3)
        z = 1 + 0.8 * ease(t / dur) * (1 - ease((t - dur + 0.25) / 0.25))
        M = cv2.getRotationMatrix2D((540, 760), 0, z)
        bg[:] = person_over(cv2.warpAffine(clean, M, (W, H), borderMode=cv2.BORDER_REFLECT).astype(np.float32), f, m)

class CoverStory(Base):
    """magazine masthead behind her head, cover lines in front"""
    def __init__(s, P, first):
        super().__init__(P, first); txt = P.get("title", "").upper()
        s.mast = rgba_text(txt, fitw(txt, "PlayfairDisplay-BoldItalic.ttf", 240, W - 60), (255, 255, 255, 245), shadow=0.25)
        s.sub = rgba_text(P.get("sub", "").upper(), font("InterDisplay-SemiBold.otf", 34), (255, 255, 255, 255), shadow=0.5, track=6) if P.get("sub") else None
        s.side = accent_text(P["side"], 64) if P.get("side") else None
    def draw(s, bg, t, dur):
        f = bg.copy(); m = s.mask(f); out = 1 - ease((t - dur + 0.3) / 0.3); e = ease(t / 0.5) * out
        over(bg, s.mast, (W - s.mast.shape[1]) / 2, 110 - 120 * (1 - ease(t / 0.5)), e)
        bg[:] = person_over(bg, f, m)
        if s.sub is not None: over(bg, s.sub, (W - s.sub.shape[1]) / 2, 470, ease((t - 0.4) / 0.4) * out)
        if s.side is not None: over(bg, s.side, 50, 1480, ease((t - 0.7) / 0.4) * out)

class PhotoWall(Base):
    """photos pin up on the wall behind her"""
    def __init__(s, P, first):
        super().__init__(P, first)
        spots = [(40, 120, -7), (300, 70, 5), (560, 130, -4), (800, 90, 8), (160, 420, 4), (700, 430, -6)]
        s.pols = [(fx.polaroid(p, 170, d), x, y) for p, (x, y, d) in zip(pics(P, 6), spots)]
    def draw(s, bg, t, dur):
        f = bg.copy(); m = s.mask(f); out = 1 - ease((t - dur + 0.3) / 0.3)
        for j, (p, x, y) in enumerate(s.pols):
            pr = (t - j * 0.15) / 0.35
            if pr > 0: over(bg, p, x, y - 80 * (1 - back(pr)), min(1, pr * 2) * out)
        bg[:] = person_over(bg, f, m)

# ------------------------------------------------------------------ camera moves (no cutout)
class PushBack(Base):
    """the video shrinks into a card and the bigger picture fills in around it"""
    def __init__(s, P, first):
        super().__init__(P, first); s.tiles = [cv2.resize(p[200:1600], (280, 360)) for p in pics(P, 6)]
        s.pos = [(60, 120), (400, 120), (740, 120), (60, 1440), (400, 1440), (740, 1440)]
    def draw(s, bg, t, dur):
        f = bg.copy(); e = ease((t - 0.2) / 0.8) * (1 - ease((t - dur + 0.4) / 0.4)); sc = 1 - 0.42 * e
        canvas = np.ones((H, W, 3), np.float32) * np.array([20, 18, 20], np.float32)
        for j, (tl, (x, y)) in enumerate(zip(s.tiles, s.pos)):
            a = ease((t - 0.6 - j * 0.08) / 0.4) * (1 - ease((t - dur + 0.4) / 0.3))
            if a > 0: reg = canvas[y:y + 360, x:x + 280]; reg[:] = reg * (1 - a) + tl * a
        fs = cv2.resize(f, None, fx=sc, fy=sc); ox, oy = (W - fs.shape[1]) // 2, (H - fs.shape[0]) // 2
        rm = Image.new("L", (fs.shape[1], fs.shape[0]), 0)
        ImageDraw.Draw(rm).rounded_rectangle([0, 0, fs.shape[1] - 1, fs.shape[0] - 1], int(50 * e), fill=255)
        rm = np.array(rm).astype(np.float32)[..., None] / 255
        reg = canvas[oy:oy + fs.shape[0], ox:ox + fs.shape[1]]; reg[:] = reg * (1 - rm) + fs * rm
        bg[:] = canvas

class ZoomThrough(Base):
    """fast zoom-blur into a white flash, then zoom back out: a topic change"""
    def draw(s, bg, t, dur):
        f = bg.copy().astype(np.uint8); cut = 0.4
        z = 1 + 3.0 * ease(t / cut) ** 2 if t < cut else 1 + 1.4 * (1 - ease((t - cut) / 0.4))
        if z <= 1.01: return
        acc_ = None
        for k in range(5):
            M = cv2.getRotationMatrix2D((540, 780), 0, max(1, z * (1 - 0.04 * k)))
            w_ = cv2.warpAffine(f, M, (W, H), borderMode=cv2.BORDER_REFLECT).astype(np.float32)
            acc_ = w_ if acc_ is None else acc_ + w_
        out = acc_ / 5; fl = max(0, 1 - abs(t - cut) / 0.08)
        bg[:] = out * (1 - fl * 0.7) + 255 * fl * 0.7

class DigitalZoom(Base):
    """black-and-white punch-in on one word"""
    def __init__(s, P, first):
        super().__init__(P, first); w = P.get("word", "")
        s.r = rgba_text(w, fitw(w, "InterDisplay-Bold.otf", 120, W - 100), (255, 255, 255, 255), track=-5) if w else None
    def draw(s, bg, t, dur):
        f = bg.copy().astype(np.uint8); g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY)
        g = cv2.cvtColor(cv2.convertScaleAbs(g, alpha=1.15, beta=-10), cv2.COLOR_GRAY2RGB)
        z = 1 + 0.25 * ease((t - 0.1) / 0.15); M = cv2.getRotationMatrix2D((540, 780), 0, z)
        bg[:] = cv2.warpAffine(g, M, (W, H), borderMode=cv2.BORDER_REFLECT).astype(np.float32)
        if s.r is not None: over(bg, s.r, (W - s.r.shape[1]) / 2, 1380, ease((t - 0.1) / 0.2))

class Shutter(Base):
    """camera flash, the moment freezes and drops in as a print"""
    def __init__(s, P, first): super().__init__(P, first); s.frozen = None
    def draw(s, bg, t, dur):
        snap = 0.25
        if s.frozen is None and t >= snap: s.frozen = fx.polaroid(bg.astype(np.uint8), 420, -5)
        out = 1 - ease((t - dur + 0.3) / 0.3)
        if s.frozen is not None:
            im = scale_rgba(s.frozen, 1.6 - 0.6 * ease((t - snap) / 0.45))
            bg[:] = bg * (1 - 0.25 * out) + cv2.GaussianBlur(bg, (0, 0), 10) * 0.25 * out
            over(bg, im, (W - im.shape[1]) / 2 + 200, 1060 - (im.shape[0] - s.frozen.shape[0]) / 2, out)
        fl = max(0, 1 - abs(t - snap) / 0.12); bg[:] = bg * (1 - fl) + 255 * fl

class BeforeAfter(Base):
    """slow push-in with a BEFORE card, then an AFTER card"""
    def __init__(s, P, first):
        super().__init__(P, first); b = P.get("before", {}); a = P.get("after", {})
        s.a = s.card("BEFORE", b, 5); s.b = s.card("AFTER", a, -6)
    def card(s, top, d, deg):
        big = d.get("big", ""); f = fitw(big, "InterDisplay-Black.otf", 72, 380)
        w = max(340, int(f.getlength(big)) + 60); h = 200
        im, p = card(w, h, (255, 255, 255, 250), 24); dr = ImageDraw.Draw(im)
        dr.text((p + 26, p + 34), d.get("top", top), font=font("InterDisplay-SemiBold.otf", 24), fill=(140, 140, 140), anchor="lm")
        dr.text((p + 26, p + 100), big, font=f, fill=tuple(int(c * 0.8) for c in acc()), anchor="lm")
        dr.text((p + 26, p + 160), d.get("sub", ""), font=font("InterDisplay-SemiBold.otf", 24), fill=(120, 120, 120), anchor="lm")
        return rotate_rgba(np.array(im), deg)
    def draw(s, bg, t, dur):
        f = bg.copy().astype(np.uint8); out = 1 - ease((t - dur + 0.3) / 0.3)
        M = cv2.getRotationMatrix2D((560, 700), 0, 1 + 0.18 * ease((t - 0.1) / 0.6) * out)
        bg[:] = cv2.warpAffine(f, M, (W, H), borderMode=cv2.BORDER_REFLECT).astype(np.float32)
        if out > 0.05:
            fx2.pop_in(bg, s.a, 30, 1080, t, 0.2); fx2.pop_in(bg, s.b, W - s.b.shape[1] - 30, 300, t, 0.9 * dur / 2.6 + 0.2)

# ------------------------------------------------------------------ cards and text
class Checklist(Base):
    def __init__(s, P, first):
        super().__init__(P, first); its = P.get("items", [])[:5]; fx.BLUSH = acc()
        title = P.get("title", "").upper()
        s.states = []
        for n in range(len(its) + 1):
            w, h = 640, 110 + 96 * len(its); im, p = card(w, h, (22, 20, 22, 205), 34, outline=(255, 255, 255, 60)); d = ImageDraw.Draw(im)
            d.text((p + 40, p + 50), title, font=font("InterDisplay-SemiBold.otf", 28), fill=(200, 200, 200), anchor="lm")
            d.text((p + w - 40, p + 50), f"{max(1, n)} of {len(its)}", font=font("InterDisplay-SemiBold.otf", 28), fill=(200, 200, 200), anchor="rm")
            for j, it in enumerate(its):
                y = p + 120 + j * 96; cx = p + 64
                if j < n:
                    d.ellipse([cx - 24, y - 24, cx + 24, y + 24], fill=acc() + (255,))
                    d.line([(cx - 11, y), (cx - 3, y + 9), (cx + 12, y - 9)], fill=CTX["on"], width=6)
                else: d.ellipse([cx - 24, y - 24, cx + 24, y + 24], outline=(200, 200, 200), width=4)
                d.text((cx + 50, y), it, font=fitw(it, "InterDisplay-SemiBold.otf", 40, w - 170), fill="white" if j < n else (190, 190, 190), anchor="lm")
            s.states.append(scale_rgba(np.array(im), 0.85))
    def draw(s, bg, t, dur):
        n = min(len(s.states) - 1, int(max(0, t - 0.3) / max(0.3, (dur - 0.9) / max(1, len(s.states) - 1))) + (1 if t > 0.3 else 0))
        e = ease(t / 0.4) * (1 - ease((t - dur + 0.3) / 0.3)); st = s.states[n]
        over(bg, st, 40, 1130 + 60 * (1 - ease(t / 0.4)) - max(0, st.shape[0] - 650), e)

class PhoneMockup(Base):
    """her profile on a phone slides in: avatar, name, bio, follow button, grid of her photos"""
    def __init__(s, P, first):
        super().__init__(P, first); ph = pics(P, 7); w, h = 380, 780; B = CTX["brand"]
        im = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0)); sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([40, 52, 40 + w, 52 + h], 60, fill=(0, 0, 0, 140))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(20))); d = ImageDraw.Draw(im)
        d.rounded_rectangle([40, 40, 40 + w, 40 + h], 60, fill=(14, 14, 16, 255)); d.rounded_rectangle([54, 54, 26 + w, 26 + h], 48, fill=(255, 255, 255, 255))
        d.rounded_rectangle([40 + w / 2 - 50, 66, 40 + w / 2 + 50, 92], 13, fill=(14, 14, 16, 255))
        if ph:
            av = cv2.resize(ph[0][380:980, 240:840], (110, 110)); avm = Image.new("L", (110, 110), 0); ImageDraw.Draw(avm).ellipse([0, 0, 109, 109], fill=255)
            im.paste(Image.fromarray(av), (80, 130), avm)
        d.ellipse([76, 126, 194, 244], outline=acc() + (255,), width=5)
        name = P.get("name") or B.get("name", ""); bio = P.get("bio") or B.get("bio", "")
        d.text((214, 150), name, font=fitw(name, "InterDisplay-Bold.otf", 30, 190), fill=(15, 15, 15))
        d.text((214, 190), bio, font=fitw(bio, "InterDisplay-SemiBold.otf", 20, 190), fill=(110, 110, 110))
        d.rounded_rectangle([80, 270, 40 + w - 26, 318], 14, fill=acc() + (255,))
        d.text(((80 + 14 + w) / 2, 294), P.get("button", "Follow"), font=font("InterDisplay-Bold.otf", 24), fill=CTX["on"], anchor="mm")
        tw = (w - 60) / 3
        for j, p in enumerate(ph[1:7]):
            th = cv2.resize(p[200:1600], (int(tw), int(tw * 1.3))); im.paste(Image.fromarray(th), (int(66 + (j % 3) * (tw + 4)), int(340 + (j // 3) * (tw * 1.3 + 4))))
        s.ph = scale_rgba(rotate_rgba(np.array(im), -6), 0.72)
    def draw(s, bg, t, dur):
        e = back(t / 0.55); out = ease((t - dur + 0.35) / 0.35)
        over(bg, s.ph, 690 + 420 * (1 - e) + 500 * out, 880)

class ScreenshotDrop(Base):
    """their screenshot drops in from the top as a rounded card"""
    def __init__(s, P, first):
        super().__init__(P, first); img = load(P["image"]) if P.get("image") else None
        if img is None: img = pics(P, 1)[0] if pics(P, 1) else np.full((H, W, 3), 240, np.uint8)
        h, w = img.shape[:2]; sc = min(760 / w, 900 / h); img = cv2.resize(img, (int(w * sc), int(h * sc)), interpolation=cv2.INTER_AREA)
        c, p = card(img.shape[1] + 24, img.shape[0] + 24, (255, 255, 255, 255), 34)
        m = Image.new("L", (img.shape[1], img.shape[0]), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, img.shape[1] - 1, img.shape[0] - 1], 26, fill=255)
        c.paste(Image.fromarray(img), (p + 12, p + 12), m); s.c = rotate_rgba(np.array(c), P.get("tilt", -3))
    def draw(s, bg, t, dur):
        e = back(t / 0.5); out = ease((t - dur + 0.3) / 0.3)
        over(bg, s.c, (W - s.c.shape[1]) / 2, 140 - (s.c.shape[0] + 200) * (1 - e) - 400 * out, 1 - out)

class Labels(Base):
    """2-3 taped labels slap on, one at a time"""
    def __init__(s, P, first):
        super().__init__(P, first); spots = [(70, 260, -6), (560, 380, 5), (120, 520, -3)]
        s.tags = [(tape(txt, d), x, y, 0.2 + j * 0.5) for j, (txt, (x, y, d)) in enumerate(zip(P.get("items", [])[:3], spots))]
    def draw(s, bg, t, dur):
        out = 1 - ease((t - dur + 0.3) / 0.3)
        for img, x, y, st in s.tags:
            p = (t - st) / 0.25
            if p <= 0: continue
            im = scale_rgba(img, 1.6 - 0.6 * ease(p))
            over(bg, im, min(x, W - img.shape[1] - 20) - (im.shape[1] - img.shape[1]) / 2, y - (im.shape[0] - img.shape[0]) / 2, min(1, p * 2) * out)

class KeywordCloud(Base):
    """the things she lists float around her"""
    def __init__(s, P, first):
        super().__init__(P, first); spots = [(80, 180), (700, 220), (60, 420), (760, 470), (380, 90), (640, 1060), (90, 1000), (420, 300)]
        ws = P.get("words", [])[:8]; gap = 1.4 / max(1, len(ws))
        s.imgs = []
        for j, (wd, (x, y)) in enumerate(zip(ws, spots)):
            r = rgba_text(wd, font("InterDisplay-SemiBold.otf", 44), (255, 255, 255, 235), shadow=0.6)
            s.imgs.append((r, min(x, W - r.shape[1]), y, 0.1 + j * gap))
    def draw(s, bg, t, dur):
        out = 1 - ease((t - dur + 0.3) / 0.3)
        for j, (im, x, y, st) in enumerate(s.imgs):
            a = ease((t - st) / 0.3) * out
            over(bg, im, x + 8 * math.sin(t * 2 + j), y - 20 * a + 6 * math.cos(t * 1.7 + j), a)

class StyleCards(Base):
    """picture cards fan out: options side by side"""
    def __init__(s, P, first):
        super().__init__(P, first); names = P.get("names", [])[:4]; ph = pics(P, len(names))
        s.cards = [fx2.style_card(p, n) for p, n in zip(ph, names)]
        s.tag = fx2.pill_tag(P["tag"], acc() + (255,), CTX["on"], 30) if P.get("tag") else None
    def draw(s, bg, t, dur):
        e = back(t / 0.7); out = 1 - ease((t - dur + 0.3) / 0.3); n = len(s.cards); mid = (n - 1) / 2
        for j, c in enumerate(s.cards):
            rc = rotate_rgba(c, -((j - mid) * 12) * e); cx = 540 + (j - mid) * 220 * e; cy = 330 + abs(j - mid) * 40 * e
            over(bg, rc, cx - rc.shape[1] / 2, cy - rc.shape[0] / 2, ease(t / 0.2) * out)
        if s.tag is not None and out > 0.05: fx2.pop_in(bg, s.tag, (W - s.tag.shape[1]) / 2, 40, t, 0.9)

class FeatureTags(Base):
    """frosted pills with icons appear one by one"""
    def __init__(s, P, first):
        super().__init__(P, first); its = P.get("items", [])[:4]; s.its = []
        for j, it in enumerate(its):
            txt, ic = (it.get("text", ""), it.get("icon")) if isinstance(it, dict) else (it, None)
            s.its.append((txt, ic, 50 if j % 2 == 0 else None, 200 + (j // 2) * 110, 0.2 + j * 0.4))
    def draw(s, bg, t, dur):
        out = 1 - ease((t - dur + 0.3) / 0.3)
        for txt, ic, x, y, st in s.its:
            if x is None: x = W - 50 - int(font("InterDisplay-SemiBold.otf", 38).getlength(txt) + (60 if ic else 0) + 56)
            bg[:] = fx3.frost_pill(bg, txt, ic, x, y + 14 * (1 - fx3.slide(t, st, 0.3)), fx3.slide(t, st, 0.25) * out)

class TextThread(Base):
    """iMessage bubbles: contact name, then the messages"""
    def __init__(s, P, first):
        super().__init__(P, first)
        s.lab = rgba_text(P.get("contact", ""), font("InterDisplay-SemiBold.otf", 30), (255, 255, 255, 235), shadow=0.6) if P.get("contact") else None
        s.b = [(fx3.imessage_bubble(m["text"], m.get("mine", False)), m.get("mine", False)) for m in P.get("messages", [])[:4]]
    def draw(s, bg, t, dur):
        out = 1 - ease((t - dur + 0.3) / 0.3); y = 230; gap = (dur - 0.8) / max(1, len(s.b))
        if s.lab is not None: over(bg, s.lab, 40, 120, fx3.slide(t, 0) * out)
        for j, (img, mine) in enumerate(s.b):
            p = fx3.slide(t, 0.3 + j * gap, 0.3)
            if p > 0: over(bg, img, (W - img.shape[1] - 30) if mine else 40, y + 20 * (1 - p), p * out)
            y += img.shape[0] + 14

class NameIntro(Base):
    """HI, I'M + her name in script, two of her photos pop in beside it"""
    def __init__(s, P, first):
        super().__init__(P, first); nm = P.get("name") or CTX["brand"].get("first_name", "")
        s.hi = rgba_text(P.get("hi", "HI, I'M"), font("Montserrat-800.ttf", 46), (255, 255, 255, 255))
        s.nm = accent_text(nm, 150); ph = pics(P, 2)
        s.p = [fx.polaroid(ph[0], 220, -6), fx.polaroid(ph[1], 220, 6)] if len(ph) >= 2 else []
        s.wave = fx2.emoji_img("👋", 90) if P.get("wave", True) else None
    def draw(s, bg, t, dur):
        out = 1 - ease((t - dur + 0.3) / 0.3)
        if out > 0.05:
            if s.p: fx2.pop_in(bg, s.p[0], 20, 160, t, 0.6, 0.35); fx2.pop_in(bg, s.p[1], 760, 140, t, 0.8, 0.35)
            if s.wave is not None: fx2.pop_in(bg, s.wave, 500, 410, t, 0.5)
        over(bg, s.hi, (W - s.hi.shape[1]) / 2, 160, ease(t / 0.3) * out)
        over(bg, s.nm, (W - s.nm.shape[1]) / 2, 210, ease((t - 0.2) / 0.3) * out)

def app_icon(letter):
    def ic(lay, x, y, sz):
        d = ImageDraw.Draw(lay); d.rounded_rectangle([x, y, x + sz, y + sz], int(sz * 0.23), fill=acc())
        d.text((x + sz / 2, y + sz / 2), letter, font=font("InterDisplay-Black.otf", int(sz * 0.55)), fill=CTX["on"], anchor="mm")
    return ic

class Notify(Base):
    """one iPhone notification slides down"""
    def __init__(s, P, first): super().__init__(P, first); s.ic = app_icon((P.get("app") or "•")[:1].upper())
    def draw(s, bg, t, dur):
        p = back((t - 0.1) / 0.45); out = ease((t - dur + 0.35) / 0.35)
        y = 120 - 260 * (1 - p) - 300 * out if t > 0.1 else -300
        bg[:] = fx3.ios_notification(bg, 60, y, s.P.get("app", ""), s.P.get("title", ""), s.P.get("body", ""), s.ic, min(1, max(0, (t - 0.1) * 5)) * (1 - out))

class WhitePage(Base):
    """cuts to a plain white page and types her words or a list (her voice keeps playing)"""
    def __init__(s, P, first):
        super().__init__(P, first); s.lines = P.get("lines", [])[:8]; s.title = P.get("title", ""); s.cache = {}
    def page(s, n):
        if n in s.cache: return s.cache[n]
        im = Image.new("RGB", (W, H), (250, 249, 246)); d = ImageDraw.Draw(im); y = 520; left = n
        if s.title:
            d.text((90, 400), s.title, font=fitw(s.title, "PlayfairDisplay-BoldItalic.ttf", 90, W - 180), fill=CTX.get("deep", tuple(int(c * 0.85) for c in acc())), anchor="lm")
        f = font("CourierPrime-Bold.ttf", 52) if os.path.exists(os.path.join(fx.F, "CourierPrime-Bold.ttf")) else font("InterDisplay-SemiBold.otf", 50)
        for ln in s.lines:
            if left <= 0: break
            d.text((90, y), ln[:left], font=f, fill=(20, 20, 20), anchor="lm"); left -= len(ln); y += 90
        s.cache[n] = np.array(im).astype(np.float32); return s.cache[n]
    def draw(s, bg, t, dur):
        total = sum(len(l) for l in s.lines); n = int(total * min(1, max(0, (t - 0.25) / max(0.5, dur - 1.0))))
        a = ease(t / 0.15) * (1 - ease((t - dur + 0.15) / 0.15)); bg[:] = bg * (1 - a) + s.page(n) * a

MORE = {"orbit": Orbit, "glass_type": GlassType, "phone": PhoneMockup, "checklist": Checklist, "doodle": Doodle,
        "screenshot": ScreenshotDrop, "green_screen": GreenScreen, "frame_break": FrameBreak, "paper_cut": PaperCut,
        "vertigo": Vertigo, "push_back": PushBack, "labels": Labels, "digital_zoom": DigitalZoom, "cover_story": CoverStory,
        "photo_wall": PhotoWall, "zoom_through": ZoomThrough, "keyword_cloud": KeywordCloud, "style_cards": StyleCards,
        "feature_tags": FeatureTags, "text_thread": TextThread, "before_after": BeforeAfter, "name_intro": NameIntro,
        "shutter": Shutter, "notify": Notify, "white_page": WhitePage}
MORE_DUR = {"orbit": 3.0, "glass_type": 2.4, "phone": 2.8, "checklist": 3.0, "doodle": 2.6, "screenshot": 2.6, "green_screen": 3.0,
            "frame_break": 2.6, "paper_cut": 2.6, "vertigo": 2.4, "push_back": 3.0, "labels": 2.4, "digital_zoom": 1.2,
            "cover_story": 2.8, "photo_wall": 2.8, "zoom_through": 0.9, "keyword_cloud": 2.8, "style_cards": 2.8,
            "feature_tags": 2.6, "text_thread": 3.0, "before_after": 2.8, "name_intro": 2.6, "shutter": 2.4, "notify": 2.4,
            "white_page": 3.5}
QUIET = {"white_page", "push_back", "green_screen", "paper_cut", "text_thread", "checklist", "style_cards", "orbit", "digital_zoom",
         "cover_story", "before_after", "shutter", "phone"}
