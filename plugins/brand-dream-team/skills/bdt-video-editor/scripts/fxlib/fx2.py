"""Effects 18-33: built from the viiolini plugin reel, corbinsylk's effects reel and andreakyton's tutorials.
Usage: python3 fx2.py [effect numbers 18..33]"""
import sys, math, random
from fx import *

EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
GOLD = (240, 214, 140)

def emoji_img(ch, size):
    try:
        ef = ImageFont.truetype(EMOJI, 109)
        e = Image.new("RGBA", (140, 140), (0, 0, 0, 0))
        ImageDraw.Draw(e).text((70, 70), ch, font=ef, embedded_color=True, anchor="mm")
        return np.array(e.resize((size, size), Image.LANCZOS))
    except Exception:
        return np.zeros((size, size, 4), np.uint8)

def pill_tag(text, fill=(255, 255, 255, 235), color=INK, size=34, icon=None):
    f = font("InterDisplay-SemiBold.otf", size)
    fi = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    iw = int(fi.getlength(icon)) + 14 if icon else 0
    w = int(f.getlength(text)) + 48 + iw
    h = int(size * 1.9)
    im, p = card(w, h, fill, h // 2)
    d = ImageDraw.Draw(im)
    x = p + 24
    if icon:
        d.text((x, p + h / 2), icon, font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size), fill=color, anchor="lm"); x += iw
    d.text((x, p + h / 2), text, font=f, fill=color, anchor="lm")
    return np.array(im)

def pop_in(dst, img, x, y, t, start, dur=0.3):
    p = (t - start) / dur
    if p <= 0: return dst
    s = 0.6 + 0.4 * back(p)
    im = scale_rgba(img, s)
    return over(dst, im, x - (im.shape[1] - img.shape[1]) / 2, y - (im.shape[0] - img.shape[0]) / 2, min(1, p * 2))

def two_line(dst, small, accent, y, a=1.0, x=60):
    if small:
        r = rgba_text(small, font("InterDisplay-SemiBold.otf", 56), (255, 255, 255, 255), track=-2)
        over(dst, r, x - 40, y - 40, a)
    if accent:
        r = rgba_text(accent, font("PlayfairDisplay-BoldItalic.ttf", 110), BLUSH + (255,))
        over(dst, r, x - 46, y + 10, a)

# 18 keyword cloud: labels float around her while she lists the tools
def fx_cloud(k, fr):
    words = [("CapCut", 80, 180, 0.1), ("effects", 780, 220, 0.35), ("captions", 60, 420, 0.6), ("music", 840, 470, 0.85),
             ("AI tools", 400, 90, 1.1), ("templates", 700, 1060, 1.35)]
    imgs = [(rgba_text(w, font("InterDisplay-SemiBold.otf", 44), (255, 255, 255, 235), shadow=0.6), x, y, s) for w, x, y, s in words]
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        for j, (im, x, y, s) in enumerate(imgs):
            a = ease((t - s) / 0.3)
            over(bg, im, x + 8 * math.sin(t * 2 + j), y - 20 * a + 6 * math.cos(t * 1.7 + j), a)
        two_line(bg, "so I decided", "to simplify it", 1380, ease((t - 1.6) / 0.3))
        out.append(label_chip(bg, 18, "keyword cloud"))
    return out

# 19 terminal card: install command types out, then a checked list
def terminal(lines_done, typed):
    w, h = 900, 400
    im, p = card(w, h, (32, 28, 33, 238), 30, outline=(255, 255, 255, 40))
    d = ImageDraw.Draw(im)
    for j, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([p + 30 + j * 30, p + 26, p + 48 + j * 30, p + 44], fill=c)
    d.text((p + 140, p + 35), "Brand Dream Team  ~/reels", font=font("InterDisplay-SemiBold.otf", 24), fill=(170, 165, 172), anchor="lm")
    mono = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 32)
    d.text((p + 36, p + 90), "> " + typed, font=mono, fill="white")
    items = ["video editor", "auto captions", "effects library", "your brand presets"]
    for j in range(lines_done):
        y = p + 150 + j * 52
        d.text((p + 60, y), "✓", font=font("InterDisplay-Bold.otf", 32), fill=BLUSH)
        d.text((p + 100, y), items[j], font=mono, fill=(225, 225, 225))
    return np.array(im)

def fx_terminal(k, fr):
    cmd = "install brand-dream-team"
    tag = pill_tag("that's literally it ✓", BLUSH + (255,), ON, 30)
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        n = int(len(cmd) * min(1, t / 0.9)); done = max(0, min(4, int((t - 1.0) / 0.3)))
        if i % 2 == 0 or i < 2: tm = terminal(done, cmd[:n] + ("|" if n < len(cmd) else ""))
        e = ease(t / 0.3)
        over(bg, tm, (W - tm.shape[1]) / 2, 170 - 40 * (1 - e), e)
        pop_in(bg, tag, 600, 120, t, 2.3)
        out.append(label_chip(bg, 19, "terminal"))
    return out

# 20 style cards fan: four preset cards fan out above her
def style_card(img, name):
    w, h = 250, 380
    im = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([20, 28, 20 + w, 28 + h], 28, fill=(0, 0, 0, 120))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(12)))
    th = cv2.resize(img[100:1700], (w - 16, h - 16))
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], 28, fill=255)
    base = Image.new("RGBA", (w, h), (255, 255, 255, 255)); base.paste(Image.fromarray(th), (8, 8))
    im.paste(base, (20, 20), m)
    d = ImageDraw.Draw(im)
    f = font("PlayfairDisplay-BoldItalic.ttf", 34)
    d.text((20 + w / 2, 20 + h - 50), name, font=f, fill="white", anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0))
    return np.array(im)

def fx_fan(k, fr):
    names = ["Soft Glass", "Bold", "Editorial", "Minimal"]
    cards = [style_card(T()[j * 2], n) for j, n in enumerate(names)]
    tag = pill_tag("ready-to-use presets", BLUSH + (255,), ON, 30)
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        e = back(t / 0.7)
        for j, c in enumerate(cards):
            ang = (-18 + j * 12) * e
            rc = rotate_rgba(c, -ang)
            cx = 540 + (j - 1.5) * 220 * e; cy = 330 + abs(j - 1.5) * 40 * e
            over(bg, rc, cx - rc.shape[1] / 2, cy - rc.shape[0] / 2, ease(t / 0.2))
        pop_in(bg, tag, 330, 40, t, 0.9)
        out.append(label_chip(bg, 20, "style cards"))
    return out

# 21 feature tags: icon pills appear one by one around her
def fx_tags(k, fr):
    tags = [(pill_tag("pauses & bad takes", icon="✂"), 60, 220, 0.2), (pill_tag("captions", icon="Aa"), 660, 220, 0.6),
            (pill_tag("transitions", icon="⇄"), 60, 340, 1.0), (pill_tag("music", icon="♪"), 700, 340, 1.4)]
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        for im, x, y, s in tags: pop_in(bg, im, x, y, t, s)
        two_line(bg, "it cuts out", "everything", 1380, ease((t - 0.3) / 0.3))
        out.append(label_chip(bg, 21, "feature tags"))
    return out

# 22 timer card: elapsed time ticks, then "fully edited"
def timer_card(secs, done, thumb):
    w, h = 820, 420
    im, p = card(w, h, (255, 255, 255, 248), 34)
    d = ImageDraw.Draw(im)
    d.text((p + 40, p + 50), f"{secs // 60:02d}:{secs % 60:02d}", font=font("InterDisplay-Bold.otf", 44), fill=INK, anchor="lm")
    if done:
        d.rounded_rectangle([p + w - 260, p + 26, p + w - 30, p + 76], 25, fill=BLUSH)
        d.text((p + w - 145, p + 51), "fully edited ✓", font=font("InterDisplay-Bold.otf", 26), fill=ON, anchor="mm")
    th = cv2.resize(thumb[100:1700], (220, 300))
    im.paste(Image.fromarray(th), (p + 40, p + 100))
    d.rounded_rectangle([p + 310, p + 210, p + 690, p + 290], 40, fill=(16, 16, 16))
    d.text((p + 340, p + 250), "your reel is", font=font("InterDisplay-Bold.otf", 34), fill="white", anchor="lm")
    d.text((p + 545, p + 250), "ready", font=font("PlayfairDisplay-BoldItalic.ttf", 40), fill=BLUSH, anchor="lm")
    return np.array(im)

def fx_timer(k, fr):
    out = []; th = T()[5]
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        secs = int(100 + 140 * ease(t / 2.0)); done = t > 2.0
        c = timer_card(secs, done, th)
        e = ease(t / 0.3)
        over(bg, c, (W - c.shape[1]) / 2, 160 - 40 * (1 - e), e)
        out.append(label_chip(bg, 22, "timer card"))
    return out

# 23 text thread: contact header, bubbles, emoji sticker
def fx_thread(k, fr):
    head = pill_tag("Mom ♥ · day 1", (40, 38, 42, 200), (255, 255, 255), 26)
    b1 = pill_tag("I did it!! my first reel 😭".replace("😭", ""), (245, 245, 247, 245), INK, 36)
    b2 = pill_tag("told you it's easy ♥", (86, 120, 255, 255), (255, 255, 255), 36)
    emo = emoji_img("🥹", 120)
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        pop_in(bg, head, 60, 200, t, 0.0)
        pop_in(bg, b1, 60, 300, t, 0.4)
        pop_in(bg, b2, W - b2.shape[1] - 40, 410, t, 1.1)
        pop_in(bg, emo, 780, 520, t, 1.7)
        out.append(label_chip(bg, 23, "text thread"))
    return out

# 24 pinned comment: CTA comment card
def comment_card():
    w, h = 900, 150
    im, p = card(w, h, (40, 38, 42, 225), 28)
    d = ImageDraw.Draw(im)
    av = cv2.resize(T()[1][400:1000, 240:840], (84, 84))
    m = Image.new("L", (84, 84), 0); ImageDraw.Draw(m).ellipse([0, 0, 83, 83], fill=255)
    im.paste(Image.fromarray(av), (p + 30, p + 33), m)
    d.text((p + 136, p + 50), "sheisguided  ·  pinned", font=font("InterDisplay-SemiBold.otf", 26), fill=(180, 175, 182), anchor="lm")
    d.text((p + 136, p + 98), "the kit is here ♡ link in bio", font=font("InterDisplay-Bold.otf", 36), fill="white", anchor="lm")
    return np.array(im)

def fx_comment(k, fr):
    c = comment_card(); pin = emoji_img("📌", 70); out = []
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        e = back(t / 0.5)
        over(bg, c, (W - c.shape[1]) / 2, 1520 + 300 * (1 - e), min(1, t * 4))
        pop_in(bg, pin, 70, 1500, t, 0.5)
        out.append(label_chip(bg, 24, "pinned comment"))
    return out

# 25 LED word: dot-matrix word lights up on a dark screen
def led_word(word, frac):
    f = font("InterDisplay-Black.otf", 300)
    m = Image.new("L", (W, 500), 0); ImageDraw.Draw(m).text((W / 2, 250), word, font=f, fill=255, anchor="mm")
    m = np.array(m)
    im = Image.new("RGBA", (W, 500), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    step = 14
    for y in range(0, 500, step):
        for x in range(0, W, step):
            on = m[y, x] > 128 and (x / W) < frac
            if on: d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=BLUSH + (255,))
            else: d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(255, 255, 255, 22))
    glow = im.filter(ImageFilter.GaussianBlur(8))
    return np.array(Image.alpha_composite(glow, im))

def fx_led(k, fr):
    out = []
    for i, f in enumerate(fr):
        t = i / FPS
        dark = np.ones((H, W, 3), np.float32) * 14
        if i % 2 == 0 or i < 2: lw = led_word("one", ease((t - 0.2) / 0.8))
        over(dark, lw, 0, 700)
        mix = ease((t - 2.2) / 0.5)
        bg = dark * (1 - mix) + f.astype(np.float32) * mix
        out.append(label_chip(bg, 25, "LED word"))
    return out

# 26 glass graph card: frosted card with a line that climbs and a %
def glass_graph(frac):
    w, h = 640, 380
    im, p = card(w, h, (255, 255, 255, 60), 34, outline=(255, 255, 255, 120))
    d = ImageDraw.Draw(im)
    d.text((p + 36, p + 46), "ENGAGEMENT", font=font("InterDisplay-SemiBold.otf", 24), fill=(255, 255, 255, 220), anchor="lm")
    d.text((p + w - 36, p + 60), f"{int(56 * frac)}%", font=font("InterDisplay-Bold.otf", 72), fill="white", anchor="rm")
    pts = []
    for j in range(41):
        x = j / 40; y = x ** 2.2 + 0.05 * math.sin(x * 12)
        pts.append((p + 40 + x * (w - 80), p + h - 50 - y * (h - 170)))
    n = max(2, int(len(pts) * frac))
    d.line(pts[:n], fill=BLUSH + (255,), width=8, joint="curve")
    ex, ey = pts[n - 1]; d.ellipse([ex - 12, ey - 12, ex + 12, ey + 12], fill="white")
    return np.array(im)

def fx_glassgraph(k, fr):
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; fl = f.astype(np.float32)
        blur = cv2.GaussianBlur(fl, (0, 0), 22)
        gg = glass_graph(ease((t - 0.3) / 1.6))
        x0, y0 = int((W - gg.shape[1]) / 2), 1260
        bg = fl.copy()
        reg = bg[y0 + 40:y0 + gg.shape[0] - 40, x0 + 40:x0 + gg.shape[1] - 40]
        a = ease(t / 0.3)
        reg[:] = reg * (1 - 0.85 * a) + blur[y0 + 40:y0 + gg.shape[0] - 40, x0 + 40:x0 + gg.shape[1] - 40] * 0.85 * a
        over(bg, gg, x0, y0, a)
        out.append(label_chip(bg, 26, "glass graph"))
    return out

# 27 before/after number cards
def num_card(top, big, sub, deg):
    w, h = 340, 200
    im, p = card(w, h, (255, 255, 255, 250), 24)
    d = ImageDraw.Draw(im)
    d.text((p + 26, p + 34), top, font=font("InterDisplay-SemiBold.otf", 24), fill=(140, 140, 140), anchor="lm")
    d.text((p + 26, p + 100), big, font=font("InterDisplay-Black.otf", 72), fill=(200, 60, 100), anchor="lm")
    d.text((p + 26, p + 160), sub, font=font("InterDisplay-SemiBold.otf", 24), fill=(120, 120, 120), anchor="lm")
    return rotate_rgba(np.array(im), deg)

def fx_numbers(k, fr):
    a = num_card("BEFORE", "1 reel", "per week", 5); b = num_card("AFTER", "7 reels", "per week", -6)
    out = []
    for i, f in enumerate(fr):
        t = i / FPS
        z = 1 + 0.18 * ease((t - 0.1) / 0.6)
        M = cv2.getRotationMatrix2D((560, 700), 0, z)
        bg = cv2.warpAffine(f, M, (W, H), borderMode=cv2.BORDER_REFLECT).astype(np.float32)
        pop_in(bg, a, 30, 1080, t, 0.4)
        pop_in(bg, b, 640, 300, t, 1.3)
        out.append(label_chip(bg, 27, "before / after"))
    return out

# 28 highlighted article: blurred paragraph, one key phrase boxed
def fx_article(k, fr):
    lines = ["I used to spend whole weekends", "editing one video, cutting", "every pause by hand, then", "I let", "do the heavy lifting and", "got my weekends back."]
    w, h = 820, 660
    base, p = card(w, h, (250, 250, 250, 252), 30)
    d = ImageDraw.Draw(base); f = font("InterDisplay-SemiBold.otf", 50)
    for j, ln in enumerate(lines):
        d.text((p + 40, p + 60 + j * 100), ln, font=f, fill=(30, 30, 30), anchor="lm")
    base_np = np.array(base)
    blurred = np.array(Image.fromarray(base_np).filter(ImageFilter.GaussianBlur(9)))
    out = []
    for i, f_ in enumerate(fr):
        t = i / FPS; bg = f_.astype(np.float32)
        e = ease(t / 0.3)
        AY = 1040
        over(bg, blurred, (W - base_np.shape[1]) / 2, AY, e)
        hp = ease((t - 0.6) / 0.35)
        if hp > 0:
            bx = Image.new("RGBA", (int(420 * hp) + 1, 110), (0, 0, 0, 0)); bd = ImageDraw.Draw(bx)
            bd.rectangle([0, 0, int(420 * hp), 110], fill=(200, 40, 70, 255))
            bd.text((18, 55), "Brand Dream Team"[:max(1, int(16 * hp))], font=font("InterDisplay-Bold.otf", 42), fill="white", anchor="lm")
            over(bg, np.array(bx), (W - base_np.shape[1]) / 2 + p + 160, AY + p + 60 + 3 * 100 - 55)
        out.append(label_chip(bg, 28, "highlighted article"))
    return out

# 29 step header: uppercase step + title + subline (great for YouTube chapters)
def step_header(step, title, sub, a_sub):
    f1 = font("Montserrat-800.ttf", 46); f2 = font("Montserrat-800.ttf", 62); f3 = font("Montserrat-600.ttf", 32)
    im = Image.new("RGBA", (W, 330), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.text((W / 2, 60), step, font=f1, fill=(255, 255, 255), anchor="mm")
    d.text((W / 2, 140), title, font=f2, fill=GOLD, anchor="mm")
    if a_sub > 0:
        d.text((W / 2, 225), sub, font=f3, fill=(255, 255, 255, int(255 * a_sub)), anchor="mm")
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.55)))
    return np.array(Image.alpha_composite(sh, im))

def fx_step(k, fr):
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        if i % 3 == 0 or i < 2: sh = step_header("STEP 1", "FIND YOUR MESSAGE", "WHAT DO PEOPLE ALWAYS ASK YOU?", ease((t - 0.7) / 0.3))
        e = ease(t / 0.3)
        over(bg, sh, 0, 120 - 40 * (1 - e), e)
        w_ = rgba_text("message", font("InterDisplay-Bold.otf", 84), (255, 255, 255, 255))
        over(bg, w_, (W - w_.shape[1]) / 2, 1180, ease((t - 1.0) / 0.15))
        out.append(label_chip(bg, 29, "step header"))
    return out

# 30 sales notification stack
def sale_note(amount, what):
    w, h = 900, 130
    im, p = card(w, h, (245, 245, 247, 235), 30)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([p + 24, p + 25, p + 104, p + 105], 20, fill=(86, 70, 230))
    d.text((p + 64, p + 65), "$", font=font("InterDisplay-Black.otf", 52), fill="white", anchor="mm")
    d.text((p + 128, p + 46), f"You just earned {amount}", font=font("InterDisplay-Bold.otf", 32), fill=INK, anchor="lm")
    d.text((p + 128, p + 90), what, font=font("InterDisplay-SemiBold.otf", 26), fill=(110, 110, 110), anchor="lm")
    d.text((p + w - 30, p + 46), "now", font=font("InterDisplay-SemiBold.otf", 24), fill=(140, 140, 140), anchor="rm")
    return np.array(im)

def fx_sales(k, fr):
    notes = [sale_note("$97.00", "Brand Dream Team AI · purchased") for _ in range(4)]
    head = rgba_text("$1,000", font("PlayfairDisplay-BoldItalic.ttf", 170), GOLD + (255,))
    sub = rgba_text("IN LESS THAN 24 HOURS", font("Montserrat-800.ttf", 44), (255, 255, 255, 255))
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        for j, n in enumerate(notes):
            st = 0.15 + j * 0.3
            p = ease((t - st) / 0.3)
            if p <= 0: continue
            shift = sum(1 for jj in range(j + 1, 4) if t > 0.15 + jj * 0.3) * 30
            over(bg, n, (W - n.shape[1]) / 2, 140 + j * 0 - 60 * (1 - p) + shift + j * 12, p * (0.55 + 0.45 * (j == 3 or t < 0.15 + (j + 1) * 0.3)))
        over(bg, head, (W - head.shape[1]) / 2, 1180, ease((t - 1.4) / 0.3))
        over(bg, sub, (W - sub.shape[1]) / 2, 1390, ease((t - 1.6) / 0.3))
        out.append(label_chip(bg, 30, "sales notifications"))
    return out

# 31 name intro with flanking photos
def fx_intro(k, fr):
    hi = rgba_text("HI, I'M", font("Montserrat-800.ttf", 46), (255, 255, 255, 255))
    nm = rgba_text("Destiny", font("PlayfairDisplay-BoldItalic.ttf", 150), GOLD + (255,))
    wave = emoji_img("👋", 90)
    p1 = polaroid(T()[3], 220, -6); p2 = polaroid(T()[7], 220, 6)
    out = []
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        pop_in(bg, p1, 20, 160, t, 0.6, 0.35); pop_in(bg, p2, 760, 140, t, 0.8, 0.35)
        over(bg, hi, (W - hi.shape[1]) / 2, 160, ease(t / 0.3))
        over(bg, nm, (W - nm.shape[1]) / 2, 210, ease((t - 0.2) / 0.3))
        pop_in(bg, wave, 500, 410, t, 0.5)
        out.append(label_chip(bg, 31, "name intro"))
    return out

# 32 prompt "copy this" box under a screenshot-style header
def prompt_box(n):
    text = "Edit this video in my Soft Glass style with my Guided Blush colors."
    w, h = 900, 200
    im, p = card(w, h, (255, 255, 255, 250), 22)
    d = ImageDraw.Draw(im)
    d.text((p + 30, p + 36), "PROMPT · COPY THIS", font=font("Montserrat-800.ttf", 22), fill=(150, 150, 150), anchor="lm")
    s = text[:n]; f = font("InterDisplay-Bold.otf", 34)
    words = s.split(" "); line, lines = "", []
    for wd in words:
        if f.getlength(line + " " + wd) > w - 60: lines.append(line); line = wd
        else: line = (line + " " + wd).strip()
    lines.append(line)
    for j, ln in enumerate(lines[:3]):
        d.text((p + 30, p + 86 + j * 44), ln, font=f, fill=INK, anchor="lm")
    return np.array(im)

def fx_prompt(k, fr):
    head = step_header("STEP 2", "TELL IT YOUR STYLE", "", 0)
    out = []; L = 66
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        over(bg, head, 0, 60, ease(t / 0.3))
        if i % 2 == 0 or i < 2: pb = prompt_box(int(L * min(1, (t - 0.3) / 1.6)))
        over(bg, pb, (W - pb.shape[1]) / 2, 300, ease((t - 0.2) / 0.3))
        out.append(label_chip(bg, 32, "prompt box"))
    return out

# 33 shutter strike: camera flash, freeze frame drops in as a print
def fx_shutter(k, fr):
    out = []; snap = 0.9; frozen = None
    for i, f in enumerate(fr):
        t = i / FPS; bg = f.astype(np.float32)
        if frozen is None and t >= snap:
            frozen = polaroid(f, 420, -5)
        if frozen is not None:
            p = (t - snap) / 0.45
            sc = 1.6 - 0.6 * ease(p)
            im = scale_rgba(frozen, sc)
            bg = bg * 0.75 + cv2.GaussianBlur(bg, (0, 0), 10) * 0.25
            over(bg, im, (W - im.shape[1]) / 2 + 200, 1060 - (im.shape[0] - frozen.shape[0]) / 2)
        fl = max(0, 1 - abs(t - snap) / 0.12)
        bg = bg * (1 - fl) + 255 * fl
        out.append(label_chip(bg, 33, "shutter strike"))
    return out

import fx3
EFFECTS2 = {18: ("18_keyword-cloud", fx_cloud), 19: ("19_terminal", fx_terminal), 20: ("20_style-cards", fx_fan),
            21: ("21_feature-tags", fx3.q_tags), 22: ("22_timer-card", fx_timer), 23: ("23_text-thread", fx3.q_thread),
            24: ("24_pinned-comment", fx_comment), 25: ("25_led-word", fx_led), 26: ("26_glass-graph", fx_glassgraph),
            27: ("27_before-after", fx_numbers), 28: ("28_highlighted-article", fx_article), 29: ("29_step-header", fx_step),
            30: ("30_sales-notifications", fx3.q_sales), 31: ("31_name-intro", fx_intro), 32: ("32_prompt-box", fx_prompt),
            33: ("33_shutter-strike", fx_shutter), 34: ("34_iphone-notification", fx3.q_notify)}

if __name__ == "__main__":
    pick = [int(a) for a in sys.argv[1:]] or sorted(EFFECTS2)
    for n in pick:
        name, fn = EFFECTS2[n]
        t0 = (n * 4.3) % 72 + 0.5
        fr = read_frames(t0)
        print(write_clip(name, fn(n, fr), t0), flush=True)
