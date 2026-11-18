"""Brand Dream Team effects sampler: 17 effects rendered on the creator's own footage.
Usage: python3 fx.py [effect numbers...]   (default: all)"""
import os, sys, math, subprocess, random
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(S, "..")
BASE = os.environ.get("BDT_FX_BASE", "")
F = os.path.join(ROOT, "..", "fonts")
import tempfile as _tf
OUT = _tf.mkdtemp(prefix="fx_")
W, H, FPS, DUR = 1080, 1920, 30, 3.0
N = int(FPS * DUR)

BLUSH = (245, 186, 203); ROSE = (233, 163, 192); INK = (10, 10, 10); CREAM = (243, 235, 221)
ON = INK          # text drawn on a BLUSH (brand accent) fill
BRAND = None      # brand.Brand: set by fx_live so every card uses the creator's fonts

def font(name, size):
    if BRAND is not None:
        import brand as _b; pth, w = BRAND.map(name); return _b.load(pth, size, w)
    return ImageFont.truetype(os.path.join(F, name), size)
def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def back(x):  # ease-out with overshoot
    x = max(0.0, min(1.0, x)); c = 1.7; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

# ---------- frame / mask IO ----------
def read_frames(t0, dur=DUR):
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-i", BASE, "-t", f"{dur:.3f}", "-vf", f"fps={FPS}",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    fr = np.frombuffer(p, np.uint8).reshape(-1, H, W, 3)
    return fr[:int(FPS * dur)]

def mask_for(k, i):
    path = os.path.join(S, "masks", f"e{k:02d}_{min(i // 2, 44):03d}.png")
    if not os.path.exists(path):
        return np.zeros((H, W), np.float32)
    m = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255
    m = np.clip((m - 0.35) / 0.4, 0, 1)
    return cv2.GaussianBlur(m, (5, 5), 0)

def write_clip(name, frames, t0, dur=DUR):
    path = os.path.join(OUT, name + ".mp4")
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-ss", f"{t0:.3f}", "-t", f"{dur:.3f}", "-i", BASE, "-map", "0:v", "-map", "1:a?", "-shortest",
                            "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p", "-c:a", "aac", path], stdin=subprocess.PIPE)
    for f in frames:
        enc.stdin.write(np.clip(f, 0, 255).astype(np.uint8).tobytes())
    enc.stdin.close(); enc.wait()
    return path

# ---------- drawing helpers ----------
def rgba_text(text, fnt, fill, shadow=0.45, blur=12, pad=40, track=0):
    """drawn at 3x and downscaled so edges stay crisp"""
    K = 3
    try:
        big = ImageFont.truetype(fnt.path, fnt.size * K)
        if getattr(fnt, "_fallback", None): big._fallback = ImageFont.truetype(fnt._fallback.path, fnt._fallback.size * K)
        if getattr(fnt, "_wght", None):
            try: big.set_variation_by_axes([fnt._wght])
            except Exception: pass
    except Exception:
        big, K = fnt, 1
    w = int(big.getlength(text) + track * K * len(text)) + 2 * pad * K
    asc, desc = big.getmetrics(); h = asc + desc + 2 * pad * K
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = pad * K
    if track:
        for ch in text:
            d.text((x, pad * K), ch, font=big, fill=fill); x += big.getlength(ch) + track * K
    else:
        d.text((pad * K, pad * K), text, font=big, fill=fill)
    im = im.resize((max(1, w // K), max(1, h // K)), Image.LANCZOS)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * shadow)))
        im = Image.alpha_composite(sh, im)
    return np.array(im)

def over(dst, rgba, x, y, a=1.0, mask=None):
    """alpha-composite rgba (h,w,4 uint8) onto dst (H,W,3 float) at x,y; mask (H,W) hides where mask=1"""
    h, w = rgba.shape[:2]; x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x0 >= x1 or y0 >= y1 or a <= 0: return dst
    src = rgba[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32)
    al = src[..., 3:4] / 255 * a
    if mask is not None: al = al * (1 - mask[y0:y1, x0:x1, None])
    dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - al) + src[..., :3] * al
    return dst

def scale_rgba(rgba, s):
    if abs(s - 1) < 1e-3: return rgba
    h, w = rgba.shape[:2]
    return cv2.resize(rgba, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)

def rotate_rgba(rgba, deg):
    return np.array(Image.fromarray(rgba).rotate(deg, resample=Image.BICUBIC, expand=True))

def card(w, h, fill, radius=36, shadow=True, outline=None):
    """rounded panel drawn at 3x then downscaled (smooth corners); callers draw text on the returned 1x image"""
    pad, K = 40, 3
    im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([pad, pad + 12, pad + w, pad + h + 12], radius, fill=(0, 0, 0, 90))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(20)))
    big = Image.new("RGBA", ((w + 2 * pad) * K, (h + 2 * pad) * K), (0, 0, 0, 0))
    ImageDraw.Draw(big).rounded_rectangle([pad * K, pad * K, (pad + w) * K, (pad + h) * K], radius * K, fill=fill,
                                          outline=outline, width=2 * K if outline else 0)
    im = Image.alpha_composite(im, big.resize(im.size, Image.LANCZOS))
    return im, pad

def label_chip(dst, num, name):
    f = font("InterDisplay-SemiBold.otf", 34)
    txt = f"{num:02d}  {name}"
    w = int(f.getlength(txt)) + 52
    im, p = card(w, 66, (16, 14, 15, 170), 33, shadow=False)
    ImageDraw.Draw(im).text((p + 26, p + 33), txt, font=f, fill="white", anchor="lm")
    return over(dst, np.array(im), 60 - p, H - 230 - p)

def caption(dst, small, big=None, y=1420, a=1.0, big_color=None, left=None):
    big_color = big_color or BLUSH
    if small:
        r = rgba_text(small, font("InterDisplay-Bold.otf", 74), (255, 255, 255, 255), track=-3)
        over(dst, r, (W - r.shape[1]) / 2 if left is None else left, y - 40, a)
    if big:
        r = rgba_text(big, font("PlayfairDisplay-BoldItalic.ttf", 150), big_color + (255,))
        over(dst, r, (W - r.shape[1]) / 2 if left is None else left - 10, y + 30, a)
    return dst

def thumbs(n=6):
    """frames from the creator's other videos, used as her own photos"""
    srcs = [(os.path.join(ROOT, "base.mp4"), [3, 14, 30]), (os.path.join(ROOT, "v2clip", "base.mp4"), [6, 22, 40]),
            (BASE, [10, 50, 70])]
    out = []
    for path, ts in srcs:
        for t in ts:
            p = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", path, "-frames:v", "1", "-f", "rawvideo",
                                "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
            if len(p) == W * H * 3:
                out.append(np.frombuffer(p, np.uint8).reshape(H, W, 3))
    return out[:n] if n else out

def polaroid(img, w=230, deg=0):
    crop = img[300:1380, :]  # face-ish square region
    ph = cv2.resize(crop, (w, int(w * 1.0)), interpolation=cv2.INTER_AREA)
    b = 14
    im = Image.new("RGBA", (w + 2 * b + 40, w + b + 54 + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([20, 28, 20 + w + 2 * b, 28 + w + b + 54], fill=(0, 0, 0, 120))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(10)))
    ImageDraw.Draw(im).rectangle([20, 20, 20 + w + 2 * b, 20 + w + b + 54], fill=(252, 250, 246, 255))
    im.paste(Image.fromarray(ph), (20 + b, 20 + b))
    return np.array(im.rotate(deg, resample=Image.BICUBIC, expand=True))

def person_over(dst, frame, m):
    return dst * (1 - m[..., None]) + frame.astype(np.float32) * m[..., None]

# ---------- the 17 effects ----------
TH = None
def T():
    global TH
    if TH is None: TH = thumbs(9)
    return TH

def fx_orbit(k, fr):
    pols = [polaroid(T()[j], 260, d) for j, d in ((1, -8), (4, 6), (7, -4))]
    word = rgba_text("faithful", font("PlayfairDisplay-BoldItalic.ttf", 150), BLUSH + (255,))
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; m = mask_for(k, i); bg = f.astype(np.float32)
        items = []
        for j, p in enumerate(pols):
            ang = t * 1.6 + j * 2 * math.pi / 3
            depth = math.sin(ang); s = 0.78 + 0.28 * (depth + 1) / 2
            x = 540 + 420 * math.cos(ang); y = 1130 + 150 * depth
            items.append((depth, scale_rgba(p, s), x, y))
        for d, p, x, y in sorted(items, key=lambda z: z[0]):
            if d < 0: over(bg, p, x - p.shape[1] / 2, y - p.shape[0] / 2, ease(t / 0.4))
        bg = person_over(bg, f, m)
        for d, p, x, y in sorted(items, key=lambda z: z[0]):
            if d >= 0: over(bg, p, x - p.shape[1] / 2, y - p.shape[0] / 2, ease(t / 0.4))
        over(bg, word, (W - word.shape[1]) / 2, 1500, ease((t - 0.3) / 0.4))
        out.append(label_chip(bg, 1, "orbit"))
    return out

def fx_glass(k, fr):
    big = rgba_text("GUIDED", font("InterDisplay-Black.otf", 300), (255, 255, 255, 240), shadow=0.3, track=-14)
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; m = mask_for(k, i); bg = f.astype(np.float32)
        e = ease(t / 0.5)
        over(bg, big, (W - big.shape[1]) / 2, 330 + 160 * (1 - e), e)
        bg = person_over(bg, f, m)
        out.append(label_chip(bg, 2, "glass type"))
    return out

def phone_screen():
    w, h = 380, 780
    im = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([40, 52, 40 + w, 52 + h], 60, fill=(0, 0, 0, 140))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(20)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([40, 40, 40 + w, 40 + h], 60, fill=(14, 14, 16, 255))
    d.rounded_rectangle([54, 54, 26 + w, 26 + h], 48, fill=(255, 255, 255, 255))
    d.rounded_rectangle([40 + w / 2 - 50, 66, 40 + w / 2 + 50, 92], 13, fill=(14, 14, 16, 255))
    av = cv2.resize(T()[2][380:980, 240:840], (110, 110))
    avm = Image.new("L", (110, 110), 0); ImageDraw.Draw(avm).ellipse([0, 0, 109, 109], fill=255)
    im.paste(Image.fromarray(av), (80, 130), avm)
    d.ellipse([76, 126, 194, 244], outline=BLUSH + (255,), width=5)
    d.text((214, 150), "She Is Guided", font=font("InterDisplay-Bold.otf", 30), fill=(15, 15, 15))
    d.text((214, 190), "faith · purpose · becoming", font=font("InterDisplay-SemiBold.otf", 20), fill=(110, 110, 110))
    d.rounded_rectangle([80, 270, 40 + w - 26, 318], 14, fill=BLUSH + (255,))
    d.text(((80 + 14 + w) / 2, 294), "Follow", font=font("InterDisplay-Bold.otf", 24), fill=ON, anchor="mm")
    tw = (w - 60) / 3
    for j in range(6):
        cx, cy = 66 + (j % 3) * (tw + 4), 340 + (j // 3) * (tw * 1.3 + 4)
        th = cv2.resize(T()[j][200:1600], (int(tw), int(tw * 1.3)))
        im.paste(Image.fromarray(th), (int(cx), int(cy)))
    return np.array(im)

def fx_phone(k, fr):
    ph = scale_rgba(rotate_rgba(phone_screen(), -6), 0.72)
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        e = back(t / 0.55)
        over(bg, ph, 690 + 420 * (1 - e), 880)
        caption(bg, "all you need is", "one video", 1330, ease((t - 0.4) / 0.3), left=20)
        out.append(label_chip(bg, 3, "phone mock-up"))
    return out

def checklist_img(n_checked, items):
    w, h = 640, 110 + 96 * len(items)
    im, p = card(w, h, (22, 20, 22, 205), 34, outline=(255, 255, 255, 60))
    d = ImageDraw.Draw(im)
    d.text((p + 40, p + 50), "MY WORKFLOW", font=font("InterDisplay-SemiBold.otf", 28), fill=(200, 200, 200), anchor="lm")
    d.text((p + w - 40, p + 50), f"{max(1, n_checked)} of {len(items)}", font=font("InterDisplay-SemiBold.otf", 28), fill=(200, 200, 200), anchor="rm")
    for j, it in enumerate(items):
        y = p + 120 + j * 96; cx = p + 64
        if j < n_checked:
            d.ellipse([cx - 24, y - 24, cx + 24, y + 24], fill=BLUSH + (255,))
            d.line([(cx - 11, y), (cx - 3, y + 9), (cx + 12, y - 9)], fill=ON, width=6)
        else:
            d.ellipse([cx - 24, y - 24, cx + 24, y + 24], outline=(200, 200, 200), width=4)
        d.text((cx + 50, y), it, font=font("InterDisplay-SemiBold.otf", 40), fill="white" if j < n_checked else (190, 190, 190), anchor="lm")
    return np.array(im)

def fx_checklist(k, fr):
    items = ["Film one take", "Let the AI edit", "Say yes or no"]
    states = [checklist_img(n, items) for n in range(4)]
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        n = 0 if t < 0.7 else 1 if t < 1.4 else 2 if t < 2.1 else 3
        e = ease(t / 0.4)
        over(bg, scale_rgba(states[n], 0.85), 40, 1130 + 60 * (1 - e), e)
        out.append(label_chip(bg, 4, "checklist"))
    return out

def doodle_layer(prog):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    def heart(cx, cy, s, frac):
        pts = []
        for a in np.linspace(0, 2 * math.pi, 80):
            x = 16 * math.sin(a) ** 3; y = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
            pts.append((cx + x * s, cy + y * s))
        n = max(2, int(len(pts) * frac)); d.line(pts[:n], fill="white", width=9, joint="curve")
    def note(cx, cy, frac):
        if frac > 0: d.line([(cx, cy), (cx, cy - 150 * min(1, frac * 2))], fill="white", width=9)
        if frac > 0.5:
            d.line([(cx, cy - 150), (cx + 70, cy - 120)], fill="white", width=9)
            d.ellipse([cx - 44, cy - 14, cx + 6, cy + 28], outline="white", width=9)
    def sparkle(cx, cy, r, frac):
        if frac <= 0: return
        rr = r * min(1, frac)
        d.line([(cx, cy - rr), (cx, cy + rr)], fill="white", width=8); d.line([(cx - rr, cy), (cx + rr, cy)], fill="white", width=8)
    heart(230, 560, 7, prog); note(850, 760, prog); sparkle(880, 470, 46, prog * 1.4 - 0.4); sparkle(170, 900, 34, prog * 1.4 - 0.6)
    a = np.array(im)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * 0.35)))
    return np.array(Image.alpha_composite(sh, im))

def fx_doodle(k, fr):
    kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (29, 29))
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; m = mask_for(k, i); bg = f.astype(np.float32)
        ring = np.clip(cv2.dilate((m > 0.5).astype(np.uint8), kern).astype(np.float32) - m, 0, 1) * ease(t / 0.3)
        bg = bg * (1 - ring[..., None]) + 255 * ring[..., None]
        if i % 3 == 0 or i < 3: dl = doodle_layer(ease((t - 0.2) / 1.2))
        over(bg, dl, 0, 0)
        out.append(label_chip(bg, 5, "doodle"))
    return out

def upload_card():
    w, h = 820, 300
    im, p = card(w, h, (255, 255, 255, 250), 30)
    d = ImageDraw.Draw(im)
    d.text((p + w / 2, p + 46), "✓ raw video added", font=font("InterDisplay-Bold.otf", 34), fill=INK, anchor="mm")
    d.text((p + 36, p + 104), "RAW CLIPS", font=font("InterDisplay-SemiBold.otf", 22), fill=(130, 130, 130))
    for j in range(4):
        th = cv2.resize(T()[j + 3][300:1500], (110, 140))
        im.paste(Image.fromarray(th), (p + 36 + j * 124, p + 140))
    d.rounded_rectangle([p + w - 220, p + 190, p + w - 36, p + 250], 30, fill=BLUSH + (255,))
    d.text((p + w - 128, p + 220), "Edit it", font=font("InterDisplay-Bold.otf", 30), fill=ON, anchor="mm")
    return np.array(im)

def fx_upload(k, fr):
    c = scale_rgba(upload_card(), 0.85); out = []
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        e = back(t / 0.5)
        over(bg, c, (W - c.shape[1]) / 2, 170 - 420 * (1 - e))
        out.append(label_chip(bg, 6, "screenshot drop"))
    return out

def ui_panel(prog):
    im = Image.new("RGB", (W, H), (26, 23, 27)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([60, 180, W - 60, 760], 40, fill=(38, 34, 39), outline=(70, 64, 72), width=2)
    d.text((110, 250), "✦ Brand Dream Team · editing", font=font("InterDisplay-SemiBold.otf", 36), fill=(225, 225, 225), anchor="lm")
    secs = int(prog * 125)
    d.text((W - 110, 250), f"00:{secs // 60:02d}:{secs % 60:02d}", font=font("InterDisplay-Bold.otf", 40), fill=BLUSH, anchor="rm")
    d.text((110, 360), "Cut the pauses, add captions,", font=font("InterDisplay-Bold.otf", 52), fill="white", anchor="lm")
    d.text((110, 430), "titles and sounds", font=font("InterDisplay-Bold.otf", 52), fill="white", anchor="lm")
    d.rounded_rectangle([110, 540, W - 110, 570], 15, fill=(70, 64, 72))
    d.rounded_rectangle([110, 540, 110 + int((W - 220) * prog), 570], 15, fill=BLUSH)
    for j, s in enumerate(["captions", "hook", "pop-ups", "export"]):
        on = prog > (j + 1) / 5
        d.rounded_rectangle([110 + j * 215, 620, 300 + j * 215, 690], 35, fill=BLUSH if on else (60, 55, 62))
        d.text((205 + j * 215, 655), s, font=font("InterDisplay-SemiBold.otf", 28), fill=ON if on else (190, 190, 190), anchor="mm")
    return np.array(im).astype(np.float32)

def fx_greenscreen(k, fr):
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; m = mask_for(k, i)
        bg = ui_panel(ease(t / 2.6))
        e = ease(t / 0.35)
        bg = f.astype(np.float32) * (1 - e) + bg * e
        bg = person_over(bg, f, m)
        caption(bg, None, "now AI edits", 1360, ease((t - 0.5) / 0.4))
        out.append(label_chip(bg, 7, "green screen"))
    return out

def fx_framebreak(k, fr):
    x0, y0, x1, y1 = 70, 560, 1010, 1880
    frame = Image.new("L", (W, H), 0); ImageDraw.Draw(frame).rounded_rectangle([x0, y0, x1, y1], 44, fill=255)
    inside = cv2.GaussianBlur(np.array(frame).astype(np.float32) / 255, (5, 5), 0)
    border = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(border).rounded_rectangle([x0, y0, x1, y1], 44, outline=(255, 255, 255, 250), width=10)
    bd = np.array(border)
    tag = rgba_text("@sheisguided", font("InterDisplay-SemiBold.otf", 34), (255, 255, 255, 255), shadow=0.5)
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; m = mask_for(k, i); e = ease(t / 0.4)
        fl = f.astype(np.float32)
        dim = cv2.GaussianBlur(fl, (0, 0), 18) * 0.28
        inn = inside[..., None] * e + (1 - e)
        bg = fl * inn + dim * (1 - inn)
        over(bg, bd, 0, 0, e)
        over(bg, tag, x0 + 10, y0 + 6, e)
        bg = person_over(bg, f, m)
        out.append(label_chip(bg, 8, "frame break"))
    return out

def paper_bg():
    rng = np.random.default_rng(3)
    base = np.ones((H, W, 3), np.float32) * np.array(CREAM, np.float32)
    base += rng.normal(0, 4, (H, W, 1)).astype(np.float32)
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    pts = [(60 + j * 32, 150 + (0 if j % 2 else 30)) for j in range(31)]
    d.line(pts, fill=ROSE, width=6, joint="curve")
    d.line([(820, 300), (860, 340)], fill=INK, width=6); d.line([(860, 300), (820, 340)], fill=INK, width=6)
    d.line([(910, 290), (910, 350)], fill=INK, width=5); d.line([(880, 320), (940, 320)], fill=INK, width=5)
    return np.array(im).astype(np.float32)

def tape(text, deg):
    f = font("PlayfairDisplay-BoldItalic.ttf", 50)
    w = int(f.getlength(text)) + 60
    im = Image.new("RGBA", (w + 20, 100), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([10, 10, w + 10, 90], fill=BLUSH + (235,))
    d.text((w / 2 + 10, 50), text, font=f, fill=ON, anchor="mm")
    return rotate_rgba(np.array(im), deg)

def fx_paper(k, fr):
    pb = paper_bg(); tg = tape("5 min", 8); out = []
    for i, f in enumerate(fr):
        t = i / FPS; m = mask_for(k, i); e = ease(t / 0.4)
        s = 1 - 0.12 * e
        fs = cv2.resize(f, None, fx=s, fy=s); ms = cv2.resize(m, None, fx=s, fy=s)
        ox, oy = (W - fs.shape[1]) // 2, H - fs.shape[0]
        canvas = f.astype(np.float32) * (1 - e) + pb * e
        sh = cv2.GaussianBlur(ms, (0, 0), 12) * 0.35 * e
        reg = canvas[oy:oy + fs.shape[0], ox:ox + fs.shape[1]]
        reg *= (1 - sh[..., None])
        mm = ms * e + (1 - e)
        reg[:] = reg * (1 - mm[..., None]) + fs.astype(np.float32) * mm[..., None]
        over(canvas, tg, 640, 420, ease((t - 0.5) / 0.3))
        out.append(label_chip(canvas, 9, "paper cut"))
    return out

def fx_vertigo(k, fr):
    out = []
    kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41))
    for i, f in enumerate(fr):
        t = i / FPS; m = mask_for(k, i)
        small = cv2.resize(f, (W // 4, H // 4)); ms = cv2.resize((m > 0.3).astype(np.uint8), (W // 4, H // 4))
        ms = cv2.dilate(ms, kern[::4, ::4] if False else cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
        clean = cv2.inpaint(small, ms * 255, 7, cv2.INPAINT_TELEA)
        clean = cv2.GaussianBlur(cv2.resize(clean, (W, H)), (0, 0), 3)
        z = 1 + 0.8 * ease(t / DUR)
        M = cv2.getRotationMatrix2D((540, 760), 0, z)
        bg = cv2.warpAffine(clean, M, (W, H), borderMode=cv2.BORDER_REFLECT).astype(np.float32)
        bg = person_over(bg, f, m)
        out.append(label_chip(bg, 10, "vertigo"))
    return out

def fx_pushback(k, fr):
    th = T(); out = []
    tiles = [cv2.resize(th[j][200:1600], (280, 360)) for j in range(6)]
    pos = [(60, 120), (400, 120), (740, 120), (60, 1440), (400, 1440), (740, 1440)]
    for i, f in enumerate(fr):
        t = i / FPS; e = ease((t - 0.2) / 0.8)
        s = 1 - 0.42 * e
        canvas = np.ones((H, W, 3), np.float32) * np.array([20, 18, 20], np.float32)
        for j, (tl, (x, y)) in enumerate(zip(tiles, pos)):
            a = ease((t - 0.6 - j * 0.08) / 0.4)
            if a <= 0: continue
            reg = canvas[y:y + 360, x:x + 280]; reg[:] = reg * (1 - a) + tl.astype(np.float32) * a
        fs = cv2.resize(f, None, fx=s, fy=s).astype(np.float32)
        ox, oy = (W - fs.shape[1]) // 2, (H - fs.shape[0]) // 2
        rm = Image.new("L", (fs.shape[1], fs.shape[0]), 0)
        ImageDraw.Draw(rm).rounded_rectangle([0, 0, fs.shape[1] - 1, fs.shape[0] - 1], int(50 * e), fill=255)
        rm = np.array(rm).astype(np.float32)[..., None] / 255
        reg = canvas[oy:oy + fs.shape[0], ox:ox + fs.shape[1]]
        reg[:] = reg * (1 - rm) + fs * rm
        out.append(label_chip(canvas, 11, "push-back reveal"))
    return out

def fx_labels(k, fr):
    tags = [(tape("one take", -6), 70, 260, 0.3), (tape("no timeline", 5), 560, 360, 0.9), (tape("my style", -3), 600, 1180, 1.5)]
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        for img, x, y, st in tags:
            p = (t - st) / 0.25
            if p <= 0: continue
            s = 1.6 - 0.6 * ease(p)
            im = scale_rgba(img, s)
            over(bg, im, x - (im.shape[1] - img.shape[1]) / 2, y - (im.shape[0] - img.shape[0]) / 2, min(1, p * 2))
        out.append(label_chip(bg, 12, "labels"))
    return out

def fx_digizoom(k, fr):
    out = []
    for i, f in enumerate(fr):
        t = i / FPS
        g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY)
        g = cv2.cvtColor(cv2.convertScaleAbs(g, alpha=1.15, beta=-10), cv2.COLOR_GRAY2RGB)
        z = 1 + 0.25 * ease((t - 0.3) / 0.15)
        M = cv2.getRotationMatrix2D((540, 780), 0, z)
        bg = cv2.warpAffine(g, M, (W, H), borderMode=cv2.BORDER_REFLECT).astype(np.float32)
        r = rgba_text("video", font("InterDisplay-Bold.otf", 120), (255, 255, 255, 255), track=-5)
        over(bg, r, (W - r.shape[1]) / 2, 1380, ease((t - 0.3) / 0.2))
        out.append(label_chip(bg, 13, "digital zoom"))
    return out

def fx_cover(k, fr):
    mast = rgba_text("GUIDED", font("PlayfairDisplay-BoldItalic.ttf", 240), (255, 255, 255, 245), shadow=0.25)
    sub = rgba_text("THE FAITH ISSUE  ·  2026", font("InterDisplay-SemiBold.otf", 34), (255, 255, 255, 255), shadow=0.5, track=6)
    side = rgba_text("the obedience edit", font("PlayfairDisplay-BoldItalic.ttf", 64), BLUSH + (255,))
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; m = mask_for(k, i); bg = f.astype(np.float32)
        e = ease(t / 0.5)
        over(bg, mast, (W - mast.shape[1]) / 2, 110 - 120 * (1 - e), e)
        bg = person_over(bg, f, m)
        over(bg, sub, (W - sub.shape[1]) / 2, 470, ease((t - 0.4) / 0.4))
        over(bg, side, 50, 1480, ease((t - 0.7) / 0.4))
        out.append(label_chip(bg, 14, "cover story"))
    return out

def fx_chart(k, fr):
    vals = [0.35, 0.6, 1.0]; names = ["wk 1", "wk 4", "wk 8"]
    head = rgba_text("consistency", font("PlayfairDisplay-BoldItalic.ttf", 70), (214, 92, 146, 255), shadow=0.35)
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
        base_y = 560
        for j, v in enumerate(vals):
            g = ease((t - 0.2 - j * 0.25) / 0.6) * v
            x = 50 + j * 74
            if g > 0: d.rounded_rectangle([x, base_y - int(250 * g), x + 54, base_y], 10, fill=BLUSH + (245,))
            d.text((x + 27, base_y + 24), names[j], font=font("InterDisplay-SemiBold.otf", 22), fill="white", anchor="mm")
        sh = layer.split()[3].filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * 0.3))
        shl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); shl.putalpha(sh)
        over(bg, np.array(Image.alpha_composite(shl, layer)), 0, 0)
        over(bg, head, 0, 150, ease(t / 0.4))
        out.append(label_chip(bg, 15, "chart grow"))
    return out

def fx_photowall(k, fr):
    th = T()
    spots = [(40, 120, -7, 0), (300, 70, 5, 1), (560, 130, -4, 2), (800, 90, 8, 3), (160, 420, 4, 4), (700, 430, -6, 5)]
    pols = [(polaroid(th[j + 2], 170, d), x, y) for x, y, d, j in spots]
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; m = mask_for(k, i); bg = f.astype(np.float32)
        for j, (p, x, y) in enumerate(pols):
            pr = (t - j * 0.15) / 0.35
            if pr <= 0: continue
            over(bg, p, x, y - 80 * (1 - back(pr)), min(1, pr * 2))
        bg = person_over(bg, f, m)
        out.append(label_chip(bg, 16, "photo wall"))
    return out

def fx_zoomthrough(k, fr):
    fr2 = read_frames(4 * 16 + 0.5 + 6.0)
    out = []
    cut = 1.5
    for i in range(N):
        t = i / FPS
        if t < cut:
            p = ease((t - (cut - 0.35)) / 0.35)
            src = fr[i]; z = 1 + 3.0 * p ** 2
        else:
            p = ease((t - cut) / 0.4)
            src = fr2[min(i, len(fr2) - 1)]; z = 1 + 1.4 * (1 - p)
        acc = None
        steps = 5 if z > 1.05 else 1
        for s in range(steps):
            zz = z * (1 - 0.04 * s)
            M = cv2.getRotationMatrix2D((540, 780), 0, max(1, zz))
            w_ = cv2.warpAffine(src, M, (W, H), borderMode=cv2.BORDER_REFLECT).astype(np.float32)
            acc = w_ if acc is None else acc + w_
        bg = acc / steps
        if abs(t - cut) < 0.07: bg = bg * 0.3 + 255 * 0.7
        out.append(label_chip(bg, 17, "zoom-through cut"))
    return out

EFFECTS = [("01_orbit", fx_orbit), ("02_glass-type", fx_glass), ("03_phone-mockup", fx_phone), ("04_checklist", fx_checklist),
           ("05_doodle", fx_doodle), ("06_screenshot-drop", fx_upload), ("07_green-screen", fx_greenscreen),
           ("08_frame-break", fx_framebreak), ("09_paper-cut", fx_paper), ("10_vertigo", fx_vertigo),
           ("11_push-back-reveal", fx_pushback), ("12_labels", fx_labels), ("13_digital-zoom", fx_digizoom),
           ("14_cover-story", fx_cover), ("15_chart-grow", fx_chart), ("16_photo-wall", fx_photowall), ("17_zoom-through-cut", fx_zoomthrough)]

if __name__ == "__main__":
    pick = [int(a) - 1 for a in sys.argv[1:]] or list(range(len(EFFECTS)))
    for k in pick:
        name, fn = EFFECTS[k]
        t0 = 4 * k + 0.5
        fr = read_frames(t0)
        frames = fn(k, fr)
        print(write_clip(name, frames, t0), flush=True)
