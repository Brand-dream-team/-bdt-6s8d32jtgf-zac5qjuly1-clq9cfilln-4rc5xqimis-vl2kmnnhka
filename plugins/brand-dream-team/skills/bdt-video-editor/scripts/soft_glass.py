import json, subprocess, os
import os as _os2, sys as _sys2
_sys2.path.insert(0, _os2.path.dirname(_os2.path.abspath(__file__)))
from fxquiet import quiet as _quiet
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import sys
S = os.path.dirname(os.path.abspath(__file__))          # engine home (fonts)
WORK = os.path.abspath(sys.argv[1])                      # project folder with edit.json, words.json, mine.wav
CFG = json.load(open(os.path.join(WORK, sys.argv[2] if len(sys.argv) > 2 else "edit.json")))
SRC = CFG["src"]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sdr import sdr_vf, TAGS
SDRVF = sdr_vf(SRC)
OUT = os.path.join(WORK, "out"); os.makedirs(OUT, exist_ok=True)
CARDS = os.path.join(WORK, CFG.get("cards_dir", "cards")); os.makedirs(CARDS, exist_ok=True)
F = os.path.join(S, "..", "fonts")
PINK = (255, 95, 162); PINK_ASS = "&HA25FFF&"  # ASS is BGR
W, H = 1080, 1920

# ---------- 1. words + transcript fixes ----------
words = json.load(open(os.path.join(WORK, "words.json")))
for k, v in CFG.get("fixes", {}).items():
    words[int(k)]["w"] = v
for k, v in CFG.get("start_fix", {}).items():
    words[int(k)]["s"] = v
for w in words:
    w["w"] = w["w"].lower()
    if w["w"] == "i" or w["w"].startswith("i'") or w["w"].startswith("i "): w["w"] = "I" + w["w"][1:]
    if w["w"] == "god": w["w"] = "God"
words = [w for w in words if w["w"]]

# ---------- 2. cut list: remove pauses ----------
sil = subprocess.run(["ffmpeg", "-i", os.path.join(WORK, "mine.wav"), "-af", "silencedetect=noise=-32dB:d=0.3", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
import re
st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", sil)]
en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", sil)]
START, END, PAD = CFG["start"], CFG["end"], 0.09
cuts = [(s + PAD, e - PAD) for s, e in zip(st, en) if s > START and e < END and (e - s - 2 * PAD) > 0.15]
keep, t = [], START
for a, b in cuts:
    keep.append((t, a)); t = b
keep.append((t, END))

def remap(x):
    out = 0.0
    for a, b in keep:
        if x >= b: out += b - a
        elif x >= a: return out + (x - a)
        else: return out
    return out
total = sum(b - a for a, b in keep)
for w in words: w["t"] = remap(w["s"])

# ---------- 3. base video: jump cuts with alternating punch-in ----------
vw, vh = [int(x) for x in subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", SRC], capture_output=True, text=True).stdout.strip().split(",")[:2]]
base = os.path.join(WORK, "base.mp4")
if not os.path.exists(base):
    segdir = os.path.join(WORK, "segs"); os.makedirs(segdir, exist_ok=True)
    lst = []
    for i, (a, b) in enumerate(keep):
        z = 1.0 if i % 2 == 0 else 1.12
        cw, ch = int(vw / z) // 2 * 2, int(vh / z) // 2 * 2
        cx, cy = (vw - cw) // 2, int((vh - ch) * 0.3)
        d = b - a
        sp = os.path.join(segdir, f"s{i:03d}.mp4"); lst.append(sp)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-i", SRC, "-t", f"{d:.3f}",
                        "-vf", f"{SDRVF}fps=30,crop={cw}:{ch}:{cx}:{cy},scale={W}:{H}:flags=lanczos,setsar=1",
                        "-af", f"afade=t=in:d=0.015,afade=t=out:st={max(0, d - 0.02):.3f}:d=0.02,aresample=48000",
                        "-c:v", "libx264", *TAGS, "-preset", "veryfast", "-crf", "16", "-c:a", "pcm_s16le", "-f", "matroska", sp + ".mkv"], check=True)
        lst[-1] = sp + ".mkv"
    open(os.path.join(segdir, "list.txt"), "w").write("".join(f"file '{x}'\n" for x in lst))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(segdir, "list.txt"),
                    "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", base], check=True)

# ---------- 4. pop-up cards ----------
import brand as _bb; _BB = _bb.Brand(CFG)
def _BRF(name, size):
    p, w = _BB.map(name, own=True); return _bb.load(p, size, w)
def font(name, size): return _BRF(name, size)
SS = 2

def rounded_card(w, h, fill, radius=40, shadow=True):
    pad = 40
    im = Image.new("RGBA", ((w + 2 * pad) * SS, (h + 2 * pad) * SS), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([pad * SS, (pad + 10) * SS, (pad + w) * SS, (pad + h + 10) * SS], radius * SS, fill=(0, 0, 0, 110))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(18 * SS)))
    ImageDraw.Draw(im).rounded_rectangle([pad * SS, pad * SS, (pad + w) * SS, (pad + h) * SS], radius * SS, fill=fill)
    return im, pad

def finish(im, name):
    im = im.resize((im.width // SS, im.height // SS), Image.LANCZOS); p = os.path.join(CARDS, name); im.save(p); return p, im.size

def _hx(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
PAL = {"accent": "#F5BACB", "on_accent": "#2B171C", "accent_on_dark": "#F5BACB", "ghost": "#F5BACB"}
PAL.update(CFG.get("palette", {}))
import brand as _b0; _B0 = _b0.Brand(CFG)
BLUSH = _B0.light; INK = _B0.on                         # accent that reads on video + readable text on it (same as before for Guided Blush)
def frosted(w, h, radius=36):
    im, p = rounded_card(w, h, (126, 116, 118, 150), radius)
    ImageDraw.Draw(im).rounded_rectangle([p * SS, p * SS, (p + w) * SS, (p + h) * SS], radius * SS, outline=(255, 255, 255, 70), width=2 * SS)
    return im, p

def notification(name, title, body, dark=True):
    w, h = 880, 160
    im, p = frosted(w, h)
    d = ImageDraw.Draw(im); o = p * SS
    d.rounded_rectangle([o + 30 * SS, o + 34 * SS, o + 122 * SS, o + 126 * SS], 22 * SS, fill=BLUSH + (255,))
    d.text((o + 76 * SS, o + 80 * SS), title[0], font=font("InterDisplay-Bold.otf", 50 * SS), fill=INK, anchor="mm")
    d.text((o + 148 * SS, o + 44 * SS), title, font=font("InterDisplay-SemiBold.otf", 36 * SS), fill="white")
    d.text((o + 148 * SS, o + 92 * SS), body, font=font("InterDisplay-SemiBold.otf", 31 * SS), fill=(255, 255, 255, 215))
    d.text((o + (w - 32) * SS, o + 48 * SS), "now", font=font("InterDisplay-SemiBold.otf", 27 * SS), fill=(255, 255, 255, 170), anchor="ra")
    return finish(im, name)

def tilt(im, deg):
    return im.rotate(deg, resample=Image.BICUBIC, expand=True)

def bubble(name, text, mine, deg=0):
    f = font("InterDisplay-SemiBold.otf", 42 * SS)
    tw = int(f.getlength(text) / SS)
    w, h = tw + 64, 84
    if mine: im, p = rounded_card(w, h, BLUSH + (255,), 42)
    else: im, p = frosted(w, h, 42)
    d = ImageDraw.Draw(im); o = p * SS
    d.text((o + 32 * SS, o + 42 * SS), text, font=f, fill=INK if mine else "white", anchor="lm")
    return finish(tilt(im, deg), name)

def pill(name, text, deg=0):
    f = font("InterDisplay-Bold.otf", 54 * SS)
    tw = int(f.getlength(text) / SS)
    w, h = tw + 120, 98
    im, p = rounded_card(w, h, BLUSH + (255,), 49)
    d = ImageDraw.Draw(im); o = p * SS
    d.text((o + 36 * SS, o + 50 * SS), text, font=f, fill=INK, anchor="lm")
    x0 = o + (36 + tw + 22) * SS
    d.line([(x0, o + 50 * SS), (x0 + 12 * SS, o + 63 * SS), (x0 + 36 * SS, o + 33 * SS)], fill=INK, width=7 * SS, joint="curve")
    return finish(tilt(im, deg), name)

def progress(name, frac, label="moving forward"):
    w, h = 720, 230
    im, p = frosted(w, h)
    d = ImageDraw.Draw(im); o = p * SS
    d.text((o + 40 * SS, o + 30 * SS), label, font=font("InterDisplay-SemiBold.otf", 36 * SS), fill="white")
    bx0, bx1, by = o + 40 * SS, o + (w - 40) * SS, o + 92 * SS
    d.rounded_rectangle([bx0, by, bx1, by + 26 * SS], 13 * SS, fill=(255, 255, 255, 60))
    fw = int((bx1 - bx0) * frac)
    if fw > 26 * SS:
        g = Image.new("RGBA", (fw, 26 * SS)); gd = ImageDraw.Draw(g)
        import brand as _b; _B = _b.Brand(CFG)
        c0, c1 = ((247, 188, 200), (228, 67, 73)) if _B.acc == (245, 186, 203) else (_b.mix(_B.light, (255, 255, 255), 0.25), _B.deep)
        for x in range(fw):
            t = x / (bx1 - bx0)
            gd.line([(x, 0), (x, 26 * SS)], fill=tuple(int(c0[i] + (c1[i] - c0[i]) * t) for i in range(3)) + (255,))
        m = Image.new("L", g.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, fw - 1, 26 * SS - 1], 13 * SS, fill=255)
        im.paste(g, (bx0, by), m)
    d.text((o + 40 * SS, o + 136 * SS), f"{int(round(frac * 100))}%", font=font("InterDisplay-Bold.otf", 76 * SS), fill="white")
    return finish(im, name)


def search_bar(name, text, cursor=True):
    w, h = 900, 120
    im, p = frosted(w, h, 60)
    d = ImageDraw.Draw(im); o = p * SS
    cx, cy, r = o + 62 * SS, o + 56 * SS, 19 * SS
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline="white", width=5 * SS)
    d.line([(cx + 13 * SS, cy + 13 * SS), (cx + 30 * SS, cy + 30 * SS)], fill="white", width=6 * SS)
    f = font("InterDisplay-SemiBold.otf", 42 * SS)
    tx = o + 112 * SS
    if text:
        d.text((tx, o + 60 * SS), text, font=f, fill="white", anchor="lm")
    else:
        d.text((tx, o + 60 * SS), "Search", font=f, fill=(255, 255, 255, 140), anchor="lm")
    if cursor:
        cxp = tx + int(f.getlength(text)) + 6 * SS
        d.rounded_rectangle([cxp, o + 34 * SS, cxp + 5 * SS, o + 86 * SS], 2 * SS, fill=BLUSH + (255,))
    return finish(im, name)

def sticky(name, title, lines, scale=1.0, deg=-5):
    w, h = 520, 190 + 74 * 3
    pad = 40
    im = Image.new("RGBA", ((w + 2 * pad) * SS, (h + 2 * pad) * SS), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([pad * SS, (pad + 14) * SS, (pad + w) * SS, (pad + h + 10) * SS], fill=(0, 0, 0, 90))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(16 * SS)))
    d = ImageDraw.Draw(im); o = pad * SS
    d.rectangle([o, o, o + w * SS, o + h * SS], fill=(250, 214, 224, 255))
    d.rectangle([o, o, o + w * SS, o + 46 * SS], fill=(245, 186, 203, 255))
    d.rectangle([o + (w // 2 - 80) * SS, o - 22 * SS, o + (w // 2 + 80) * SS, o + 26 * SS], fill=(255, 255, 255, 150))
    fh = font("Caveat-Bold.ttf", 66 * SS)
    d.text((o + 40 * SS, o + 74 * SS), title, font=fh, fill=INK)
    for i, ln in enumerate(lines):
        d.text((o + 52 * SS, o + (150 + i * 74) * SS), ln, font=font("Caveat-Bold.ttf", 58 * SS), fill=INK)
    im = im.rotate(deg, resample=Image.BICUBIC, expand=True)
    if scale != 1.0:
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    return finish(im, name)


def hook_card(name, line1, line2, emo_l=None, emo_r=None, scale=1.0):
    CW, CH = W, 420
    im = Image.new("RGBA", (CW * SS, CH * SS), (0, 0, 0, 0))
    f1 = _BB.hook(100 * SS); f2 = font("PlayfairDisplay-BoldItalic.ttf", 132 * SS)
    txt = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(txt)
    y1, y2 = 120 * SS, 262 * SS
    d.text((CW * SS // 2, y1), line1, font=f1, fill="white", anchor="mm")
    d.text((CW * SS // 2, y2), line2, font=f2, fill=BLUSH + (255,), anchor="mm")
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    a = txt.split()[3].filter(ImageFilter.GaussianBlur(14 * SS)).point(lambda v: int(v * 0.55))
    sh.putalpha(a)
    im = Image.alpha_composite(im, sh); im = Image.alpha_composite(im, txt)
    def emoji(ch, cx, cy, deg):
        try:
            ef = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109)
            e = Image.new("RGBA", (140, 140), (0, 0, 0, 0))
            ImageDraw.Draw(e).text((70, 70), ch, font=ef, embedded_color=True, anchor="mm")
            e = e.resize((96 * SS, 96 * SS), Image.LANCZOS).rotate(deg, resample=Image.BICUBIC, expand=True)
            im.alpha_composite(e, (int(cx - e.width / 2), int(cy - e.height / 2)))
        except Exception:
            pass
    w1 = f1.getlength(line1)
    if emo_l: emoji(emo_l, CW * SS / 2 - w1 / 2 - 70 * SS, y1 + 40 * SS, 10)
    if emo_r: emoji(emo_r, CW * SS / 2 + w1 / 2 + 66 * SS, y1 + 6 * SS, -12)
    if scale != 1.0:
        big = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
        im = Image.new("RGBA", im.size, (0, 0, 0, 0))
        im.alpha_composite(big, ((im.width - big.width) // 2, (im.height - big.height) // 2)) if scale < 1 else None
        if scale > 1:
            im = big.crop(((big.width - im.width) // 2, (big.height - im.height) // 2, (big.width + im.width) // 2, (big.height + im.height) // 2))
    im = im.resize((CW, CH), Image.LANCZOS); pth = os.path.join(CARDS, name); im.save(pth); return pth, im.size

def wt(i_word):  # new-timeline start of a word by its original text index search helper
    return i_word["t"]

def find(seq, after=0.0):
    seq = seq.split()
    for i in range(len(words) - len(seq) + 1):
        if words[i]["s"] >= after and [w["w"].lower() for w in words[i:i + len(seq)]] == seq: return words[i]["t"]
    raise ValueError(seq)

overlays = []  # (png, x, y, start, end)
def add(card, x, y, start, dur, fin=None, fout=None):
    (path, (cw, chh)) = card
    auto = dur > 0.5
    overlays.append((path, x - 40, y - 40, start, min(start + dur, total), auto if fin is None else fin, auto if fout is None else fout))

hk = CFG.get("hook")
if hk:
    hd = hk.get("dur", 3.2); y = hk.get("y", 150)
    p_, sz = hook_card("hook.png", hk["line1"], hk["line2"], hk.get("emoji_left"), hk.get("emoji_right"))
    overlays.append((p_, 0, y, 0.0, hd, True, True))
for n_, c in enumerate(CFG.get("cards", [])):
    t0 = find(c["at"], c.get("after", 0.0)) + c.get("offset", 0.0)
    ty = c["type"]
    if ty == "notification":
        add(notification(f"n{n_}.png", c["title"], c["body"]), 90, c.get("y", 210), t0, c.get("dur", 3.0))
    elif ty == "bubble":
        bb = bubble(f"b{n_}.png", c["text"], c.get("mine", False), c.get("tilt", 0))
        x = (W - 70 - (bb[1][0] - 80)) if c.get("right") else 80
        add(bb, x, c.get("y", 210), t0, c.get("dur", 3.0))
    elif ty == "pill":
        add(pill(f"p{n_}.png", c["text"], c.get("tilt", 0)), 90, c.get("y", 190), t0, c.get("until", t0 + c.get("dur", 3.0)) if False else c.get("dur", 3.0))
    elif ty == "search":
        # one bar, queries typed one after another at their own moments
        qs = c["queries"]; y = c.get("y", 210)
        starts = [find(q["at"], q.get("after", 0.0)) + q.get("offset", 0.0) for q in qs]
        end_all = starts[-1] + c.get("hold", 2.0) + len(qs[-1]["text"]) * 0.04
        prev_end = None
        for qi, (q, st_q) in enumerate(zip(qs, starts)):
            txt = q["text"]; step = 2; spf = 0.07
            chunks = list(range(0, len(txt) + 1, step)) + ([len(txt)] if len(txt) % step else [])
            t = st_q
            for ci, m in enumerate(chunks):
                last_chunk = ci == len(chunks) - 1
                nxt = starts[qi + 1] if qi + 1 < len(qs) else end_all
                dur = (nxt - t) if last_chunk else spf
                first = qi == 0 and ci == 0
                final = last_chunk and qi == len(qs) - 1
                add(search_bar(f"s{n_}_{qi}_{ci}.png", txt[:m], cursor=not last_chunk or (int(t * 2) % 2 == 0)), 90, y, t, dur,
                    fin=first, fout=final)
                t += spf
    elif ty == "sticky":
        y = c.get("y", 180); x = c.get("x", 110)
        title = c["title"]; lines = c["lines"]
        times = [t0] + [find(l["at"], l.get("after", 0.0)) for l in lines]
        texts = [l["text"] for l in lines]
        end_all = times[-1] + c.get("hold", 2.0)
        # slap-in: scale frames on first state
        for si, sc in enumerate([1.35, 1.12, 0.96]):
            pth, (cw, chh) = sticky(f"k{n_}_slap{si}.png", title, [], sc, c.get("tilt", -5))
            base_w, base_h = sticky(f"k{n_}_ref.png", title, [], 1.0, c.get("tilt", -5))[1]
            add((pth, (cw, chh)), x - (cw - base_w) // 2, y - (chh - base_h) // 2, t0 + si * 0.045, 0.045, fin=(si == 0), fout=False)
        for li in range(len(lines) + 1):
            st_l = times[li] if li else t0 + 0.135
            en_l = times[li + 1] if li + 1 < len(times) else end_all
            add(sticky(f"k{n_}_{li}.png", title, texts[:li], 1.0, c.get("tilt", -5)), x, y, st_l, en_l - st_l,
                fin=False, fout=(li == len(lines)))
    elif ty == "progress":
        frames = 10
        for k in range(frames + 1):
            st_k = t0 + k * 0.08
            dur = 0.08 if k < frames else min(c.get("dur", 3.0), total - st_k)
            add(progress(f"pr{n_}_{k}.png", k / frames, c.get("label", "moving forward")), 160, c.get("y", 220), st_k, dur, fin=(k == 0), fout=(k == frames))

# ---------- 5. animated captions (ASS) ----------
EMPH = set(CFG.get("emphasis", []))
_g = _hx(PAL["ghost"]); BLUSH_ASS = "&H%02X%02X%02X&" % (_g[2], _g[1], _g[0])
groups, cur = [], []
for i, w in enumerate(words):
    cur.append(w)
    nxt = words[i + 1] if i + 1 < len(words) else None
    gap = (nxt["t"] - w["t"]) if nxt else 9
    if len(cur) >= 3 or gap > 0.55 or w["w"] in {"right", "forward", "lives", "feel", "life", "people"} or not nxt:
        groups.append(cur); cur = []

def ts(x):
    x = max(0, x); h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return f"{h}:{m:02d}:{s:05.2f}"

X0, Y1, Y2 = 64, 1268, 1384   # line baselines (bottom-left anchored)
def word(w, big, new, shadow):
    base = r"\alpha&H70&" if shadow else r"\alpha&H00&"
    fin = "&H70&" if shadow else "&H00&"
    anim = (r"\alpha&HFF&\t(0,170,\alpha" + fin + ")") if new else base
    if big and w["w"] in EMPH:
        col = r"\c&H000000&" if shadow else r"\c" + BLUSH_ASS
        f = r"\fnPlayfair Display\b1\i1\fs122\fsp0"
    elif big:
        col = r"\c&H000000&" if shadow else r"\c&HFFFFFF&"
        f = r"\fnInter Display\b1\i0\fs110\fsp-3"
    else:
        col = r"\c&H000000&" if shadow else r"\c&HFFFFFF&"
        f = r"\fnInter Display SemiBold\b0\i0\fs62\fsp-1"
    return "{" + f + col + anim + "}" + w["w"]

events = []
for gi, g in enumerate(groups):
    split = len(g) - 1 if len(g) > 1 else 0
    if len(g) >= 2 and len(g[-1]["w"]) <= 3: split = len(g) - 2
    line1, line2 = g[:split], g[split:]
    gend = groups[gi + 1][0]["t"] if gi + 1 < len(groups) else total
    gend = min(gend, g[-1]["t"] + 1.3)
    for k, w in enumerate(g):
        s = w["t"]; e = g[k + 1]["t"] if k + 1 < len(g) else gend
        if e - s < 0.02: continue
        shown = g[:k + 1]
        for layer, sh in ((0, True), (1, False)):
            blur = r"\blur14\bord0\shad0" if sh else r"\blur0.6\bord0\shad0"
            l1 = " ".join(word(x, False, x is w, sh) for x in shown if x in line1)
            l2 = " ".join(word(x, True, x is w, sh) for x in shown if x in line2)
            yo = 6 if sh else 0
            if l1: events.append(f"Dialogue: {layer},{ts(s)},{ts(e)},Cap,,0,0,0,,{{\\an1\\pos({X0},{Y1 + yo}){blur}}}{l1}")
            if l2: events.append(f"Dialogue: {layer},{ts(s)},{ts(e)},Cap,,0,0,0,,{{\\an1\\pos({X0},{Y2 + yo}){blur}}}{l2}")

ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter Display,62,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,1,64,60,360,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(_quiet(events, WORK)) + "\n"
open(os.path.join(WORK, "caps.ass"), "w").write(ass)

# ---------- 6. composite ----------
cmd = ["ffmpeg", "-v", "error", "-y", "-i", base]
fcs, last = [], "[0:v]"
punch = []
for zp in CFG.get("zoom_punch", []):
    tz = find(zp["at"], zp.get("after", 0.0)); hold = zp.get("hold", 1.0); amt = zp.get("amount", 0.16)
    # ramp in 0.12s, hold, ease out 0.3s
    punch.append(f"{amt}*clip((t-{tz:.3f})/0.12,0,1)*clip(1-(t-{tz + 0.12 + hold:.3f})/0.3,0,1)")
if punch:
    zexpr = "1+" + "+".join(punch)
    fcs.append(f"[0:v]scale=w='trunc(iw*({zexpr})/2)*2':h='trunc(ih*({zexpr})/2)*2':eval=frame:flags=bicubic,crop={W}:{H}:(iw-{W})/2:(ih-{H})*0.35,setsar=1[zb]")
    last = "[zb]"
for n, (path, x, y, s, e, fin_, fout_) in enumerate(overlays):
    d = e - s
    cmd += ["-framerate", "30", "-loop", "1", "-t", f"{d + 0.12:.3f}", "-i", path]
    fi = n + 1
    anim = fin_
    fade = (f",fade=t=in:st=0:d=0.18:alpha=1" if fin_ else "") + (f",fade=t=out:st={max(0, d - 0.2):.3f}:d=0.2:alpha=1" if fout_ else "")
    fcs.append(f"[{fi}:v]format=rgba{fade},setpts=PTS+{s:.3f}/TB[c{n}]")
    ye = f"{y}+max(0\\,(1-(t-{s:.3f})/0.18))*36" if anim else f"{y}"
    fcs.append(f"{last}[c{n}]overlay=x={x}:y='{ye}':eof_action=pass:enable='between(t,{s:.3f},{e:.3f})'[o{n}]")
    last = f"[o{n}]"
assp = os.path.join(WORK, "caps.ass").replace(":", "\\:")
import brand as _b; _BF = _b.patch_ass(assp, _b.Brand(CFG), F)   # their own brand fonts in the captions, if they have them
fcs.append(f"{last}ass='{assp}':fontsdir='{_BF}'[vout]")
final = os.path.join(OUT, CFG["output"])
cmd += ["-filter_complex", ";".join(fcs), "-map", "[vout]", "-map", "0:a", "-c:v", "libx264", *TAGS, "-preset", "slow", "-tune", "film",
        "-crf", "19", "-maxrate", "10M", "-bufsize", "20M", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", final]
subprocess.run(cmd, check=True)
print("segments", len(keep), "orig", round(58.35 - 0.85, 2), "new", round(total, 2), "groups", len(groups), "overlays", len(overlays))
print(final)
