"""Quality pass: iOS-accurate bubbles, frosted notifications, frosted pills.
Everything drawn at 3x and downscaled; frosted panels blur the real video behind them."""
import sys
from fx import *

SSx = 3
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
BLUE = (10, 132, 255); GRAY = (233, 233, 235)

def F(name, size): return font(name, size * SSx)

def emoji_hi(ch, size):
    ef = ImageFont.truetype(EMOJI, 109)
    e = Image.new("RGBA", (136, 128), (0, 0, 0, 0))
    ImageDraw.Draw(e).text((68, 64), ch, font=ef, embedded_color=True, anchor="mm")
    bbox = e.getbbox(); e = e.crop(bbox)
    return np.array(e.resize((size, int(size * e.height / e.width)), Image.LANCZOS))

def down(im):
    return np.array(im.resize((im.width // SSx, im.height // SSx), Image.LANCZOS))

def frost(bg, x, y, w, h, radius, tint=(255, 255, 255), tint_a=0.55, blur=26, sat=1.15):
    """iOS-style material: blur the actual video under the panel, tint it, round corners, soft shadow + hairline."""
    x, y, w, h = int(x), int(y), int(w), int(h)
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0: return bg
    pad = 60
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad)
    patch = cv2.GaussianBlur(bg[Y0:Y1, X0:X1], (0, 0), blur)
    g = patch.mean(axis=2, keepdims=True); patch = g + (patch - g) * sat
    patch = patch[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0]
    patch = patch * (1 - tint_a) + np.array(tint, np.float32) * tint_a
    m = Image.new("L", ((x1 - x0) * SSx, (y1 - y0) * SSx), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, m.width - 1, m.height - 1], radius * SSx, fill=255)
    m = np.array(m.resize((x1 - x0, y1 - y0), Image.LANCZOS)).astype(np.float32)[..., None] / 255
    # shadow
    sh = np.zeros((H, W), np.float32); sh[y0 + 10:y1 + 10, x0:x1] = m[..., 0] * 0.22
    sh = cv2.GaussianBlur(sh, (0, 0), 18)
    bg = bg * (1 - sh[..., None])
    bg[y0:y1, x0:x1] = bg[y0:y1, x0:x1] * (1 - m) + patch * m
    return bg

def imessage_bubble(text, mine, tail=True, maxw=700):
    f = F("InterDisplay-SemiBold.otf", 44)
    words = text.split(" "); lines, line = [], ""
    for wd in words:
        if f.getlength((line + " " + wd).strip()) > (maxw - 70) * SSx: lines.append(line); line = wd
        else: line = (line + " " + wd).strip()
    lines.append(line)
    tw = max(f.getlength(l) for l in lines) / SSx
    w, h = int(tw + 64), int(36 + 56 * len(lines))
    S_ = SSx
    im = Image.new("RGBA", ((w + 40) * S_, (h + 24) * S_), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    col = BLUE if mine else GRAY
    ox = 20 * S_
    d.rounded_rectangle([ox, 0, ox + w * S_, h * S_], 46 * S_, fill=col + (255,))
    if tail:  # iOS tail: smooth curved nub joined to the bubble's bottom corner
        def bez(p0, p1, p2, n=24):
            return [((1-t)**2*p0[0]+2*(1-t)*t*p1[0]+t*t*p2[0], (1-t)**2*p0[1]+2*(1-t)*t*p1[1]+t*t*p2[1]) for t in [i/n for i in range(n+1)]]
        H_ = h * S_
        if mine:
            bx = ox + w * S_
            pts = [(bx - 40*S_, H_ - 30*S_)] + bez((bx - 6*S_, H_ - 30*S_), (bx - 2*S_, H_ - 4*S_), (bx + 14*S_, H_)) + bez((bx + 14*S_, H_), (bx - 14*S_, H_ + 2*S_), (bx - 40*S_, H_ - 8*S_))
        else:
            bx = ox
            pts = [(bx + 40*S_, H_ - 30*S_)] + bez((bx + 6*S_, H_ - 30*S_), (bx + 2*S_, H_ - 4*S_), (bx - 14*S_, H_)) + bez((bx - 14*S_, H_), (bx + 14*S_, H_ + 2*S_), (bx + 40*S_, H_ - 8*S_))
        d.polygon(pts, fill=col + (255,))
    tc = (255, 255, 255) if mine else (0, 0, 0)
    for j, l in enumerate(lines):
        d.text((ox + 32 * S_, (18 + 28 + j * 56) * S_), l, font=f, fill=tc, anchor="lm")
    return down(im)

def ios_notification(bg, x, y, app, title, body, icon_fn, a=1.0, blank=False):
    w, h = 960, 170
    if a <= 0: return bg
    under = bg.copy()
    under = frost(under, x, y, w, h, 40, (245, 245, 247), 0.62)
    if blank: return bg * (1 - a) + under * a
    lay = Image.new("RGBA", (w * SSx, h * SSx), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    icon_fn(lay, 26 * SSx, 30 * SSx, 76 * SSx)
    d.text((124 * SSx, 50 * SSx), app.upper(), font=F("InterDisplay-SemiBold.otf", 24), fill=(60, 60, 67, 160), anchor="lm")
    d.text((124 * SSx, 92 * SSx), title, font=F("InterDisplay-Bold.otf", 33), fill=(0, 0, 0), anchor="lm")
    d.text((124 * SSx, 134 * SSx), body, font=F("InterDisplay-SemiBold.otf", 31), fill=(30, 30, 30), anchor="lm")
    d.text(((w - 30) * SSx, 50 * SSx), "now", font=F("InterDisplay-SemiBold.otf", 24), fill=(60, 60, 67, 150), anchor="rm")
    under = over(under, down(lay), x, y)
    return bg * (1 - a) + under * a

def icon_sale(lay, x, y, s):
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x, y, x + s, y + s], int(s * 0.23), fill=(25, 25, 28))
    d.text((x + s / 2, y + s / 2), "$", font=font("InterDisplay-Black.otf", int(s * 0.62)), fill=BLUSH, anchor="mm")

def icon_bdt(lay, x, y, s):
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x, y, x + s, y + s], int(s * 0.23), fill=BLUSH)
    d.text((x + s / 2, y + s / 2 + s * 0.04), "B", font=font("PlayfairDisplay-BoldItalic.ttf", int(s * 0.7)), fill=ON, anchor="mm")

F_DIR = F_ = os.path.join(ROOT, "fonts")

def frost_pill(bg, text, icon, x, y, a, size=38):
    if a <= 0: return bg
    f = F("InterDisplay-SemiBold.otf", size)
    fi = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size * SSx)
    iw = (fi.getlength(icon) / SSx + 14) if icon else 0
    w = int(f.getlength(text) / SSx + iw + 56); h = int(size * 2.0)
    under = frost(bg.copy(), x, y, w, h, h // 2, (255, 255, 255), 0.28, blur=22)
    lay = Image.new("RGBA", (w * SSx, h * SSx), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([0, 0, w * SSx - 1, h * SSx - 1], h * SSx // 2, outline=(255, 255, 255, 110), width=2 * SSx)
    tx = 28 * SSx
    if icon:
        d.text((tx, h * SSx / 2), icon, font=fi, fill="white", anchor="lm"); tx += int(iw * SSx)
    d.text((tx, h * SSx / 2), text, font=f, fill="white", anchor="lm")
    under = over(under, down(lay), x, y)
    return bg * (1 - a) + under * a

def slide(t, st, d=0.35): return ease((t - st) / d)

def q_thread(k, fr):
    hdr = imessage_bubble("Mom ♥", False, tail=False)
    b1 = imessage_bubble("I did it!! my first reel", False)
    b2 = imessage_bubble("told you it's easy ♥", True)
    emo = emoji_hi("🥹", 120)
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        name = rgba_text("Mom ♥  ·  day 1", F("InterDisplay-SemiBold.otf", 9), (255, 255, 255, 230), shadow=0.6) if False else None
        lab = rgba_text("Mom ♥  ·  day 1", font("InterDisplay-SemiBold.otf", 30), (255, 255, 255, 235), shadow=0.6)
        over(bg, lab, 40, 120, slide(t, 0))
        for img, x, y, st in ((b1, 40, 230, 0.3), (b2, W - b2.shape[1] - 30, 340, 1.0)):
            p = slide(t, st, 0.3)
            if p > 0:
                im = scale_rgba(img, 0.85 + 0.15 * back((t - st) / 0.3))
                over(bg, im, x, y + 20 * (1 - p), min(1, p * 1.5))
        pop_in(bg, emo, 860, 440, t, 1.6)
        out.append(label_chip(bg, 23, "text thread"))
    return out

def pop_in(dst, img, x, y, t, start, dur=0.3):
    p = (t - start) / dur
    if p <= 0: return dst
    im = scale_rgba(img, 0.6 + 0.4 * back(p))
    return over(dst, im, x - (im.shape[1] - img.shape[1]) / 2, y - (im.shape[0] - img.shape[0]) / 2, min(1, p * 2))

def q_notify(k, fr):
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        p = back((t - 0.1) / 0.45)
        y = 120 - 260 * (1 - p) if t > 0.1 else -300
        bg = ios_notification(bg, 60, y, "Brand Dream Team", "Your reel is ready ✨".replace("✨", ""), "Edited in Soft Glass · 0:42", icon_bdt, min(1, max(0, (t - 0.1) * 5)))
        out.append(label_chip(bg, 34, "iPhone notification"))
    return out

def q_tags(k, fr):
    tags = [("pauses & bad takes", "✂", 50, 200, 0.2), ("captions", "Aa", 640, 200, 0.6), ("transitions", "⇄", 50, 310, 1.0), ("music", "♪", 720, 310, 1.4)]
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        for text, ic, x, y, st in tags:
            bg = frost_pill(bg, text, ic, x, y + 14 * (1 - slide(t, st, 0.3)), slide(t, st, 0.25))
        out.append(label_chip(bg, 21, "feature tags"))
    return out

def q_sales(k, fr):
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        n = sum(1 for j in range(4) if t > 0.15 + j * 0.35)
        stack = min(n, 3)
        for depth in range(stack - 1, -1, -1):
            j = n - 1 - depth
            y = 120 + depth * 26; xo = 60 + depth * 24; wsc = depth
            if depth == 0:
                p = back((t - (0.15 + j * 0.35)) / 0.35); y = y - 200 * (1 - p)
            bg = ios_notification(bg, xo, y, "Sales", "New sale: $97.00", "Brand Dream Team AI kit", icon_sale, [1, 0.8, 0.6][depth], blank=depth > 0)
        out.append(label_chip(bg, 30, "sale notifications"))
    return out

Q = {1: ("q_text-thread", q_thread, 23), 2: ("q_ios-notification", q_notify, 6), 3: ("q_feature-tags", q_tags, 21), 4: ("q_sales", q_sales, 30)}
if __name__ == "__main__":
    for n in [int(a) for a in sys.argv[1:]] or sorted(Q):
        name, fn, k = Q[n]
        t0 = (k * 4.3) % 72 + 0.5
        fr = read_frames(t0)
        frames = fn(k, fr)
        path = os.path.join(OUT, name + ".mp4")
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                "-ss", f"{t0:.3f}", "-t", "3", "-i", BASE, "-map", "0:v", "-map", "1:a?", "-shortest",
                                "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p", "-c:a", "aac", path], stdin=subprocess.PIPE)
        for fr_ in frames: enc.stdin.write(np.clip(fr_, 0, 255).astype(np.uint8).tobytes())
        enc.stdin.close(); enc.wait(); print(path, flush=True)
