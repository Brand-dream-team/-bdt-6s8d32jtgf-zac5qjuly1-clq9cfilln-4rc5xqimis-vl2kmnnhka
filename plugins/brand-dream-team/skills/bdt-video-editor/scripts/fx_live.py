"""Brand Dream Team: approved library effects, drawn with the creator's own words and colors.
Runs on the cut base video, frame by frame, before captions are added.

usage: python3 fx_live.py <project folder> [edit.json]
  needs <project>/base.mp4 and <project>/timeline_words.json (run make_base.py first).
  Keeps the clean video as base_clean.mp4 and writes base.mp4 with the effects in it,
  so every preset script (soft_glass, bold_highlight, pinkpop, pink_label, chunky_word) picks them up.

edit.json "fx": [{"type": "...", "at": "exact words they say", "after": 0, "dur": 2.6, ...params}]
types and params (text must come from what the creator says):
  timer      line ("your reel is"), accent ("ready"), done ("fully edited ✓"), from_secs (100), to_secs (240)
  chart      title ("consistency"), labels (["wk 1","wk 4","wk 8"]), values ([0.35,0.6,1.0])
  graph      label ("ENGAGEMENT"), value (56)                      frosted card, line climbs to value %
  sales      app ("Stan"), title ("New sale: $97.00"), body ("Brand Dream Team AI kit"), count (3)
  comment    handle ("sheisguided"), text ("the kit is here ♡ link in bio")
  prompt     header ("PROMPT · COPY THIS"), text ("Edit this video in my Soft Glass style...")
  terminal   title ("Brand Dream Team ~/reels"), command ("install brand-dream-team"), items ([...4]), tag ("that's literally it ✓")
  article    lines (["I used to spend whole weekends", ...]), highlight ("my weekends back")
  step       step ("STEP 1"), title ("FIND YOUR MESSAGE"), sub ("WHAT DO PEOPLE ALWAYS ASK YOU?")
  led        word ("one")                                        dark screen, dot-matrix word, fades back
  + 25 more in fx_more.py (camera effects with the person cut out, cards, text): see SKILL.md "Studio effects".
Studio names work as types ("Push-back reveal" -> push_back). Optional edit.json keys: brand, photos, broll.
"""
import json, math, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "fxlib")); sys.path.insert(0, HERE)
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import fx, fx2, fx3
from fx import font, ease, back, over, card, rgba_text, scale_rgba, INK, W, H, FPS
from sdr import TAGS, is_hdr, sdr_vf

def hx(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

# ---------------------------------------------------------------- effects (per frame)
class Timer:
    def __init__(s, P, first):
        s.P = P; s.th = first
    def card(s, secs, done):
        P = s.P; w, h = 820, 420
        im, p = card(w, h, (255, 255, 255, 248), 34); d = ImageDraw.Draw(im)
        d.text((p + 40, p + 50), f"{secs // 60:02d}:{secs % 60:02d}", font=font("InterDisplay-Bold.otf", 44), fill=INK, anchor="lm")
        if done:
            dt = P.get("done", "fully edited ✓"); f = font("InterDisplay-Bold.otf", 26); bw = int(f.getlength(dt)) + 44
            d.rounded_rectangle([p + w - 30 - bw, p + 26, p + w - 30, p + 76], 25, fill=ACC)
            d.text((p + w - 30 - bw / 2, p + 51), dt, font=f, fill=ON, anchor="mm")
        th = cv2.resize(s.th[100:1700], (220, 300)); im.paste(Image.fromarray(th), (p + 40, p + 100))
        line, acc = P.get("line", "your reel is"), P.get("accent", "ready")
        f1, f2 = font("InterDisplay-Bold.otf", 34), font("PlayfairDisplay-BoldItalic.ttf", 40)
        bw = int(f1.getlength(line + " ") + f2.getlength(acc)) + 60
        d.rounded_rectangle([p + 310, p + 210, p + 310 + bw, p + 290], 40, fill=(16, 16, 16))
        d.text((p + 340, p + 250), line, font=f1, fill="white", anchor="lm")
        d.text((p + 340 + f1.getlength(line + " "), p + 250), acc, font=f2, fill=ACC, anchor="lm")
        return np.array(im)
    def draw(s, bg, t, dur):
        a, b = int(s.P.get("from_secs", 100)), int(s.P.get("to_secs", 240))
        k = ease(t / (dur * 0.7)); c = s.card(int(a + (b - a) * k), t > dur * 0.7)
        e = ease(t / 0.3); over(bg, c, (W - c.shape[1]) / 2, 160 - 40 * (1 - e), e)

class Chart:
    def __init__(s, P, first):
        s.P = P; s.head = rgba_text(P.get("title", "consistency"), font("PlayfairDisplay-BoldItalic.ttf", 70), ACC + (255,), shadow=0.35)
    def draw(s, bg, t, dur):
        vals = s.P.get("values", [0.35, 0.6, 1.0]); names = s.P.get("labels", ["wk 1", "wk 4", "wk 8"])
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer); base_y = 560
        for j, v in enumerate(vals):
            g = ease((t - 0.2 - j * 0.25) / 0.6) * max(0.05, min(1, v)); x = 50 + j * 74
            if g > 0: d.rounded_rectangle([x, base_y - int(250 * g), x + 54, base_y], 10, fill=ACC + (245,))
            if j < len(names): d.text((x + 27, base_y + 24), names[j], font=font("InterDisplay-SemiBold.otf", 22), fill="white", anchor="mm")
        sh = layer.split()[3].filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * 0.3))
        shl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); shl.putalpha(sh)
        over(bg, np.array(Image.alpha_composite(shl, layer)), 0, 0); over(bg, s.head, 0, 150, ease(t / 0.4))

class Graph:
    def __init__(s, P, first): s.P = P
    def card(s, frac):
        w, h = 640, 380; im, p = card(w, h, (255, 255, 255, 60), 34, outline=(255, 255, 255, 120)); d = ImageDraw.Draw(im)
        d.text((p + 36, p + 46), s.P.get("label", "ENGAGEMENT").upper(), font=font("InterDisplay-SemiBold.otf", 24), fill=(255, 255, 255, 220), anchor="lm")
        d.text((p + w - 36, p + 60), f"{int(float(s.P.get('value', 56)) * frac)}%", font=font("InterDisplay-Bold.otf", 72), fill="white", anchor="rm")
        pts = [(p + 40 + (j / 40) * (w - 80), p + h - 50 - ((j / 40) ** 2.2 + 0.05 * math.sin(j / 40 * 12)) * (h - 170)) for j in range(41)]
        n = max(2, int(len(pts) * frac)); d.line(pts[:n], fill=ACC + (255,), width=8, joint="curve")
        ex, ey = pts[n - 1]; d.ellipse([ex - 12, ey - 12, ex + 12, ey + 12], fill="white")
        return np.array(im)
    def draw(s, bg, t, dur):
        blur = cv2.GaussianBlur(bg, (0, 0), 22); gg = s.card(ease((t - 0.3) / 1.6))
        x0, y0 = int((W - gg.shape[1]) / 2), 1260; a = ease(t / 0.3)
        reg = bg[y0 + 40:y0 + gg.shape[0] - 40, x0 + 40:x0 + gg.shape[1] - 40]
        reg[:] = reg * (1 - 0.85 * a) + blur[y0 + 40:y0 + gg.shape[0] - 40, x0 + 40:x0 + gg.shape[1] - 40] * 0.85 * a
        over(bg, gg, x0, y0, a)

class Sales:
    def __init__(s, P, first): s.P = P
    def draw(s, bg, t, dur):
        P = s.P; cnt = int(P.get("count", 3)); n = sum(1 for j in range(cnt) if t > 0.15 + j * 0.35)
        for depth in range(min(n, 3) - 1, -1, -1):
            j = n - 1 - depth; y = 120 + depth * 26; xo = 60 + depth * 24
            if depth == 0: y = y - 200 * (1 - back((t - (0.15 + j * 0.35)) / 0.35))
            bg[:] = fx3.ios_notification(bg, xo, y, P.get("app", "Stan"), P.get("title", "New sale: $97.00"), P.get("body", ""),
                                         fx3.icon_sale, [1, 0.8, 0.6][depth], blank=depth > 0)

class Comment:
    def __init__(s, P, first):
        w, h = 900, 150; im, p = card(w, h, (40, 38, 42, 225), 28); d = ImageDraw.Draw(im)
        av = cv2.resize(first[300:900, 240:840], (84, 84)); m = Image.new("L", (84, 84), 0); ImageDraw.Draw(m).ellipse([0, 0, 83, 83], fill=255)
        im.paste(Image.fromarray(av), (p + 30, p + 33), m)
        d.text((p + 136, p + 50), f"{P.get('handle', 'you')}  ·  pinned", font=font("InterDisplay-SemiBold.otf", 26), fill=(180, 175, 182), anchor="lm")
        txt = P.get("text", ""); f = font("InterDisplay-Bold.otf", 36)
        while f.getlength(txt) > w - 170 and f.size > 24: f = font("InterDisplay-Bold.otf", f.size - 2)
        d.text((p + 136, p + 98), txt, font=f, fill="white", anchor="lm")
        s.c = np.array(im); s.pin = fx2.emoji_img("📌", 70)
    def draw(s, bg, t, dur):
        e = back(t / 0.5); over(bg, s.c, (W - s.c.shape[1]) / 2, 1520 + 300 * (1 - e), min(1, t * 4))
        fx2.pop_in(bg, s.pin, 70, 1500, t, 0.5)

class Prompt:
    def __init__(s, P, first): s.P = P; s.cache = {}
    def box(s, n):
        if n in s.cache: return s.cache[n]
        text = s.P.get("text", ""); w, h = 900, 200; im, p = card(w, h, (255, 255, 255, 250), 22); d = ImageDraw.Draw(im)
        d.text((p + 30, p + 36), s.P.get("header", "PROMPT · COPY THIS"), font=font("Montserrat-800.ttf", 22), fill=(150, 150, 150), anchor="lm")
        f = font("InterDisplay-Bold.otf", 34); line, lines = "", []
        for wd in text[:n].split(" "):
            if f.getlength(line + " " + wd) > w - 60: lines.append(line); line = wd
            else: line = (line + " " + wd).strip()
        lines.append(line)
        for j, ln in enumerate(lines[:3]): d.text((p + 30, p + 86 + j * 44), ln, font=f, fill=INK, anchor="lm")
        s.cache[n] = np.array(im); return s.cache[n]
    def draw(s, bg, t, dur):
        L = len(s.P.get("text", "")); pb = s.box(int(L * min(1, max(0, (t - 0.3) / 1.6))))
        over(bg, pb, (W - pb.shape[1]) / 2, 300, ease((t - 0.2) / 0.3))

class Terminal:
    def __init__(s, P, first):
        s.P = P; s.cache = {}; s.tag = fx2.pill_tag(P["tag"], ACC + (255,), ON, 30) if P.get("tag") else None
    def card(s, done, typed):
        key = (done, typed)
        if key in s.cache: return s.cache[key]
        w, h = 900, 400; im, p = card(w, h, (32, 28, 33, 238), 30, outline=(255, 255, 255, 40)); d = ImageDraw.Draw(im)
        for j, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]): d.ellipse([p + 30 + j * 30, p + 26, p + 48 + j * 30, p + 44], fill=c)
        d.text((p + 140, p + 35), s.P.get("title", "~/reels"), font=font("InterDisplay-SemiBold.otf", 24), fill=(170, 165, 172), anchor="lm")
        mono = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 32) if os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf") else font("PlexMono-SemiBold.ttf", 32)
        d.text((p + 36, p + 90), "> " + typed, font=mono, fill="white")
        for j, it in enumerate(s.P.get("items", [])[:done]):
            y = p + 150 + j * 52
            d.text((p + 60, y), "✓", font=font("InterDisplay-Bold.otf", 32), fill=ACC); d.text((p + 100, y), it, font=mono, fill=(225, 225, 225))
        s.cache[key] = np.array(im); return s.cache[key]
    def draw(s, bg, t, dur):
        cmd = s.P.get("command", ""); items = s.P.get("items", [])[:4]
        n = int(len(cmd) * min(1, t / 0.9)); done = max(0, min(len(items), int((t - 1.0) / 0.3)))
        tm = s.card(done, cmd[:n] + ("|" if n < len(cmd) else "")); e = ease(t / 0.3)
        over(bg, tm, (W - tm.shape[1]) / 2, 170 - 40 * (1 - e), e)
        if s.tag is not None: fx2.pop_in(bg, s.tag, 600, 120, t, min(2.3, dur - 0.5))

class Article:
    def __init__(s, P, first):
        s.P = P; lines = P.get("lines", []); w = 820; f = font("InterDisplay-SemiBold.otf", 50)
        h = 120 + 100 * len(lines); base, p = card(w, h, (250, 250, 250, 252), 30); d = ImageDraw.Draw(base)
        s.box = None; hl = P.get("highlight", "").lower()
        for j, ln in enumerate(lines):
            y = p + 60 + j * 100; d.text((p + 40, y), ln, font=f, fill=(30, 30, 30), anchor="lm")
            i = ln.lower().find(hl) if hl else -1
            if i >= 0 and s.box is None:
                x0 = p + 40 + f.getlength(ln[:i]); s.box = (x0, y, f.getlength(ln[i:i + len(hl)]), ln[i:i + len(hl)])
        s.img = np.array(base); s.f = f
    def draw(s, bg, t, dur):
        e = ease(t / 0.3); AY = 1040 - max(0, s.img.shape[0] - 740); x = (W - s.img.shape[1]) / 2
        over(bg, s.img, x, AY, e)
        if s.box:
            hp = ease((t - 0.6) / 0.35)
            if hp > 0:
                bx0, by, bw, word = s.box; bwid = int((bw + 24) * hp) + 1
                bx = Image.new("RGBA", (bwid, 86), (0, 0, 0, 0)); bd = ImageDraw.Draw(bx)
                bd.rectangle([0, 0, bwid, 86], fill=ACC + (255,)); bd.text((12, 43), word, font=s.f, fill=ON, anchor="lm")
                over(bg, np.array(bx), x + bx0 - 12, AY + by - 43)

class Step:
    def __init__(s, P, first): s.P = P
    def head(s, a_sub):
        P = s.P; f1 = font("Montserrat-800.ttf", 46); f2 = font("Montserrat-800.ttf", 62); f3 = font("Montserrat-600.ttf", 32)
        im = Image.new("RGBA", (W, 330), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.text((W / 2, 60), P.get("step", "STEP 1").upper(), font=f1, fill=(255, 255, 255), anchor="mm")
        title = P.get("title", "").upper()
        while f2.getlength(title) > W - 80 and f2.size > 36: f2 = font("Montserrat-800.ttf", f2.size - 2)
        d.text((W / 2, 140), title, font=f2, fill=ACC, anchor="mm")
        if a_sub > 0 and P.get("sub"): d.text((W / 2, 225), P["sub"].upper(), font=f3, fill=(255, 255, 255, int(255 * a_sub)), anchor="mm")
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.55)))
        return np.array(Image.alpha_composite(sh, im))
    def draw(s, bg, t, dur):
        h = s.head(ease((t - 0.7) / 0.3)); e = ease(t / 0.3); over(bg, h, 0, 120 - 40 * (1 - e), e)

class Led:
    def __init__(s, P, first): s.P = P; s.cache = {}
    def word(s, frac):
        q = round(frac, 2)
        if q in s.cache: return s.cache[q]
        word = s.P.get("word", "one"); size = 300; f = font("InterDisplay-Black.otf", size)
        while f.getlength(word) > W - 80 and size > 120: size -= 20; f = font("InterDisplay-Black.otf", size)
        m = Image.new("L", (W, 500), 0); ImageDraw.Draw(m).text((W / 2, 250), word, font=f, fill=255, anchor="mm"); m = np.array(m)
        im = Image.new("RGBA", (W, 500), (0, 0, 0, 0)); d = ImageDraw.Draw(im); step = 14
        for y in range(0, 500, step):
            for x in range(0, W, step):
                if m[y, x] > 128 and (x / W) < q: d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=ACC + (255,))
                else: d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(255, 255, 255, 22))
        s.cache[q] = np.array(Image.alpha_composite(im.filter(ImageFilter.GaussianBlur(8)), im)); return s.cache[q]
    def draw(s, bg, t, dur):
        dark = np.ones((H, W, 3), np.float32) * 14; over(dark, s.word(ease((t - 0.2) / 0.8)), 0, 700)
        mix = ease((t - (dur - 0.6)) / 0.5); bg[:] = dark * (1 - mix) + bg * mix

import fx_more
TYPES = {"timer": Timer, "chart": Chart, "graph": Graph, "sales": Sales, "comment": Comment, "prompt": Prompt,
         "terminal": Terminal, "article": Article, "step": Step, "led": Led}
DUR = {"timer": 2.8, "chart": 2.6, "graph": 2.6, "sales": 2.2, "comment": 2.6, "prompt": 2.8, "terminal": 3.0, "article": 2.6, "step": 2.4, "led": 2.6}
TYPES.update(fx_more.MORE); DUR.update(fx_more.MORE_DUR)
ALIASES = {"timer_card": "timer", "chart_grow": "chart", "glass_graph": "graph", "sale_notifications": "sales", "pinned_comment": "comment",
           "prompt_box": "prompt", "highlighted_article": "article", "step_header": "step", "led_word": "led", "iphone_notification": "notify",
           "phone_mockup": "phone", "screenshot_drop": "screenshot", "push_back_reveal": "push_back", "zoom_through_cut": "zoom_through",
           "shutter_strike": "shutter"}
def norm(t): t = t.replace("-", "_").replace(" ", "_").lower(); return ALIASES.get(t, t)

def stills(paths, n):
    """sharp frames spread across videos, as 1080x1920 pictures"""
    out = []
    for v in paths:
        try: d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", v], capture_output=True, text=True).stdout)
        except ValueError: continue
        k = max(1, n // max(1, len(paths)) + 1); pre = sdr_vf(v)
        for j in range(k):
            best, bs = None, -1
            for q in (0.0, 0.33, 0.66):
                t = d * (j + 0.2 + q * 0.6) / k
                raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", v, "-frames:v", "1", "-vf", pre + f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
                                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
                if len(raw) != W * H * 3: continue
                im = np.frombuffer(raw, np.uint8).reshape(H, W, 3); sc = cv2.Laplacian(cv2.cvtColor(im, cv2.COLOR_RGB2GRAY)[::4, ::4], cv2.CV_64F).var()
                if sc > bs: best, bs = im, sc
            if best is not None: out.append(best)
    return out[:n]

# ---------------------------------------------------------------- run
if __name__ == "__main__":
    WORK = os.path.abspath(sys.argv[1]); CFG = json.load(open(os.path.join(WORK, sys.argv[2] if len(sys.argv) > 2 else "edit.json")))
    import brand as _brand
    B = _brand.Brand(CFG); ACC, ON = B.light, B.on        # the creator's brand: accent that reads on video, text on accent
    for m in (fx, fx2, fx3): m.BLUSH, m.ON = ACC, ON
    fx2.GOLD = ACC; fx.ROSE = ACC; fx.BRAND = B            # every card font now maps to their preset / brand fonts
    if B.acc != (245, 186, 203): fx_more.CTX["deep"] = B.deep   # Guided Blush keeps its original shade
    clean = os.path.join(WORK, "base_clean.mp4"); base = os.path.join(WORK, "base.mp4")
    if not os.path.exists(clean): os.replace(base, clean)
    fx_more.CTX.update(work=WORK, acc=ACC, on=ON, brand=CFG.get("brand", {}))
    need = [e for e in CFG.get("fx", []) if norm(e["type"]) in ("orbit", "phone", "photo_wall", "push_back", "style_cards", "name_intro", "screenshot")]
    if need:
        pp = [os.path.join(WORK, p) if not os.path.isabs(p) else p for p in CFG.get("photos", [])]
        pd = os.path.join(WORK, "photos")
        if os.path.isdir(pd): pp += [os.path.join(pd, x) for x in sorted(os.listdir(pd)) if x.lower().endswith((".jpg", ".jpeg", ".png", ".heic", ".webp"))]
        imgs = [fx_more.fit(i) for i in (fx_more.load(p) for p in pp) if i is not None]
        if len(imgs) < 6: imgs += stills([b if os.path.isabs(b) else os.path.join(WORK, b) for b in CFG.get("broll", [])], 6 - len(imgs))
        if len(imgs) < 6: imgs += stills([clean], 6 - len(imgs))
        fx_more.CTX["photos"] = imgs
    words = json.load(open(os.path.join(WORK, "timeline_words.json")))
    ws = [w["w"].lower().strip(".,!?") for w in words]
    def find(phrase, after=0.0):
        seq = phrase.lower().split()
        for i in range(len(ws) - len(seq) + 1):
            if ws[i:i + len(seq)] == seq and words[i]["t"] >= after: return words[i]["t"]
        return None
    total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", clean], capture_output=True, text=True).stdout)
    jobs = []
    for e in CFG.get("fx", []):
        e = dict(e, type=norm(e["type"]))
        if e["type"] not in TYPES: print("unknown effect:", e["type"]); continue
        a = find(e["at"], e.get("after", 0.0)) if e.get("at") else e.get("start")
        if a is None: print("cue not found:", e.get("at")); continue
        a += e.get("offset", 0.0); d = min(e.get("dur", DUR[e["type"]]), total - a)
        if d > 0.5: jobs.append([a, a + d, e, None])
    jobs.sort(key=lambda j: j[0])
    for k in range(1, len(jobs)):                       # never two effects at once
        if jobs[k][0] < jobs[k - 1][1]: jobs[k - 1][1] = max(jobs[k - 1][0] + 0.6, jobs[k][0] - 0.05)
    json.dump([[j[0], j[1]] for j in jobs if j[2]["type"] in ("article", "graph") or j[2]["type"] in fx_more.QUIET], open(os.path.join(WORK, "fx_quiet.json"), "w"))
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", clean, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    FXS = os.environ.get("FX_STILLS")                    # test mode: save one frame per effect into this folder, no video
    if FXS: os.makedirs(FXS, exist_ok=True); shots = {id(j): j[0] + (j[1] - j[0]) * float(os.environ.get("FX_AT", "0.6")) for j in jobs}
    enc = None if FXS else subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-i", clean, "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", *TAGS, "-preset", "veryfast", "-crf", "16",
                            "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", base], stdin=subprocess.PIPE)
    n = 0
    while True:
        raw = dec.stdout.read(W * H * 3)
        if len(raw) < W * H * 3: break
        t = n / FPS; act = [j for j in jobs if j[0] <= t < j[1]]
        if act:
            f = np.frombuffer(raw, np.uint8).reshape(H, W, 3); bg = f.astype(np.float32)
            for j in act:
                if j[3] is None: j[3] = TYPES[j[2]["type"]](j[2], f.copy())
                j[3].draw(bg, t - j[0], j[1] - j[0])
            raw = np.clip(bg, 0, 255).astype(np.uint8).tobytes()
            if FXS:
                for j in act:
                    if abs(t - shots[id(j)]) < 0.5 / FPS: Image.fromarray(np.frombuffer(raw, np.uint8).reshape(H, W, 3)).save(os.path.join(FXS, f"{j[0]:05.1f}_{j[2]['type']}.jpg"), quality=85)
        if enc: enc.stdin.write(raw)
        n += 1
    if FXS: dec.kill(); print("stills", FXS); sys.exit(0)
    enc.stdin.close(); enc.wait()
    print("ok", base, "effects:", ", ".join(f"{j[2]['type']}@{j[0]:.1f}s" for j in jobs))
