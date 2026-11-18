"""Brand Dream Team preset: Pink Pop.
Small line, huge keyword in the pop color, small line. Optional floating photo cards made from the
creator's own B-roll or photos, each timed to the moment they talk about it.
usage: python3 pinkpop.py <project folder> [edit.json]   (run make_base.py first)"""
import json, subprocess, os, sys, re, random
import os as _os2, sys as _sys2
_sys2.path.insert(0, _os2.path.dirname(_os2.path.abspath(__file__)))
from fxquiet import quiet as _quiet
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from sdr import sdr_vf, TAGS
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

S = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(S, "..", "fonts")
WORK = os.path.abspath(sys.argv[1]); STYLE = "pinkpop"
CFG = json.load(open(os.path.join(WORK, sys.argv[2] if len(sys.argv) > 2 else "edit.json")))
SRC = CFG["src"]; W, H = 1080, 1920
OUT = os.path.join(WORK, "out"); os.makedirs(OUT, exist_ok=True)
CARDS = os.path.join(WORK, "cards_" + STYLE); os.makedirs(CARDS, exist_ok=True)

# ---------- words, cuts, timeline (same rules as the other presets) ----------
words = json.load(open(os.path.join(WORK, "words.json")))
for k, v in CFG.get("fixes", {}).items(): words[int(k)]["w"] = v
for k, v in CFG.get("start_fix", {}).items(): words[int(k)]["s"] = v
for w in words:
    w["w"] = w["w"].lower()
    if w["w"] == "i" or w["w"].startswith("i'"): w["w"] = "I" + w["w"][1:]
    if w["w"] == "god": w["w"] = "God"
words = [w for w in words if w["w"]]
sil = subprocess.run(["ffmpeg", "-i", os.path.join(WORK, "mine.wav"), "-af", "silencedetect=noise=-32dB:d=0.3", "-f", "null", "-"], capture_output=True, text=True).stderr
st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", sil)]; en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", sil)]
START, END, PAD = CFG["start"], CFG["end"], 0.09
cuts = [(s + PAD, e - PAD) for s, e in zip(st, en) if s > START and e < END and (e - s - 2 * PAD) > 0.15]
keep, t = [], START
for a, b in cuts: keep.append((t, a)); t = b
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
base = os.path.join(WORK, "base.mp4")
assert os.path.exists(base), "run scripts/make_base.py on this project first"

PAL = CFG.get("palette", {"accent": "#F5BACB"})
def hx(h): h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
def ass_col(rgb): return "&H%02X%02X%02X&" % (rgb[2], rgb[1], rgb[0])
def mix(a, b, k): return tuple(int(a[i]*(1-k) + b[i]*k) for i in range(3))
def ts(x):
    x = max(0, x); h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return f"{h}:{m:02d}:{s:05.2f}"
import brand as _bb; _BB = _bb.Brand(CFG)
def _BRF(name, size):
    p, w = _BB.map(name, own=True); return _bb.load(p, size, w)
def pfont(name, size): return _BRF(name.replace(" ", "") + ".ttf", size)

STOP = set("the a an and but or to of in on for with at by from is are was were be been am i i'm you your you're my me we our it it's that this these those what so do did don't not just like have has had will would can could all about there their they them he she his her as if then than too very really because before after should would could always never every something anything everything through myself going getting things thing".split())
EMPH = set(w.lower() for w in CFG.get("emphasis", []))
def strong(w): return w["w"].lower().strip(".,!?") in EMPH or (len(w["w"]) >= 6 and w["w"].lower() not in STOP)

# ---------- readability: pace-aware grouping ----------
RATE = len(words) / max(1.0, total)                       # words per second after cuts
FAST = RATE > 2.8
MIN_SPAN = 0.95 if FAST else 0.7                            # a group should cover at least this much speech
def chunk(maxn, gap=0.45, adaptive=True):
    if not adaptive:
        groups, cur = [], []
        for i, w in enumerate(words):
            cur.append(w); nxt = words[i+1] if i+1 < len(words) else None
            g = (nxt["t"] - w["t"]) if nxt else 9
            if len(cur) >= maxn or g > gap or not nxt: groups.append(cur); cur = []
        return groups
    if FAST: maxn += 1
    groups, cur = [], []
    for i, w in enumerate(words):
        cur.append(w); nxt = words[i+1] if i+1 < len(words) else None
        g = (nxt["t"] - w["t"]) if nxt else 9
        span = (nxt["t"] if nxt else w["t"] + 0.4) - cur[0]["t"]
        if not nxt or g > gap or (len(cur) >= maxn) or (len(cur) >= maxn - 1 and span >= MIN_SPAN):
            if nxt and len(cur) < maxn + 1 and span < MIN_SPAN and g <= gap:
                continue
            groups.append(cur); cur = []
    return groups
def hold_for(g): return max(1.3, 0.30 * len(g) + 0.5)       # seconds a group needs to be readable
def keyword(g):
    em = [x for x in g if x["w"].lower().strip(".,!?") in EMPH]
    if em: return em[0]
    cands = [x for x in g if strong(x)]
    return max(cands, key=lambda x: len(x["w"])) if cands else None

def find(phrase, after=0.0):
    seq = phrase.lower().split(); ws = [w["w"].lower() for w in words]
    for i in range(len(ws) - len(seq) + 1):
        if ws[i:i+len(seq)] == seq and words[i]["t"] >= after: return words[i]["t"]
    return None

events = []; overlays = []; blur_ranges = []

if True:
    import brand as _b, colorsys as _cs
    _a = hx(PAL.get("accent", "#F5BACB"))
    if CFG.get("pop_color"): POP = hx(CFG["pop_color"])
    elif _a == (245, 186, 203): POP = hx("#FF5FA2")                       # Guided Blush keeps the original hot pink
    else:                                                                # a punchy version of their accent
        _h, _s, _v = _cs.rgb_to_hsv(*[c / 255 for c in _a])
        POP = tuple(int(c * 255) for c in _cs.hsv_to_rgb(_h, max(_s, 0.62) if _s > 0.08 else _s, max(_v, 0.92)))
    POPA = ass_col(POP); SHADA = "&H3A0A24&" if POP == hx("#FF5FA2") else ass_col(mix(POP, (8, 0, 12), 0.82))
    SMALL_F, KW_F = "BDT Mont Bold", "BDT Mont Black"
    CY = CFG.get("caption_y", 1330)
    def lockup(top, kw, bot, s_top, s_kw, s_bot, t_end, cy):
        fsz = 215; f = pfont(KW_F, fsz)
        while f.getlength(kw.upper()) > W - 90 and fsz > 70: fsz -= 6; f = pfont(KW_F, fsz)
        kww = f.getlength(kw.upper())
        if top:
            events.append(f"Dialogue: 1,{ts(s_top)},{ts(t_end)},Cap,,0,0,0,,{{\\an1\\pos({(W-kww)/2+6:.0f},{cy-fsz*0.78:.0f})\\fn{SMALL_F}\\fs60\\c&HFFFFFF&\\shad0\\bord0\\blur0.5\\fad(90,120)}}{top}")
            events.append(f"Dialogue: 0,{ts(s_top)},{ts(t_end)},Cap,,0,0,0,,{{\\an1\\pos({(W-kww)/2+8:.0f},{cy-fsz*0.78+3:.0f})\\fn{SMALL_F}\\fs60\\c&H000000&\\alpha&H70&\\blur10\\fad(90,120)}}{top}")
        anim = r"\fscx128\fscy128\t(0,140,\fscx96\fscy96)\t(140,220,\fscx100\fscy100)\alpha&HFF&\t(0,80,\alpha&H00&)"
        events.append(f"Dialogue: 0,{ts(s_kw)},{ts(t_end)},Cap,,0,0,0,,{{\\an2\\pos(544,{cy+6})\\fn{KW_F}\\fs{fsz}\\fsp-1\\c{SHADA}\\alpha&H60&\\blur12\\fad(60,120)}}{kw.upper()}")
        events.append(f"Dialogue: 2,{ts(s_kw)},{ts(t_end)},Cap,,0,0,0,,{{\\an2\\pos(540,{cy})\\fn{KW_F}\\fs{fsz}\\fsp-1\\c{POPA}\\blur0.6{anim}\\fad(0,120)}}{kw.upper()}")
        if bot:
            events.append(f"Dialogue: 1,{ts(s_bot)},{ts(t_end)},Cap,,0,0,0,,{{\\an9\\pos({(W+kww)/2-6:.0f},{cy+6})\\fn{SMALL_F}\\fs56\\c&HFFFFFF&\\blur0.5\\fad(90,120)}}{bot}")
            events.append(f"Dialogue: 0,{ts(s_bot)},{ts(t_end)},Cap,,0,0,0,,{{\\an9\\pos({(W+kww)/2-4:.0f},{cy+9})\\fn{SMALL_F}\\fs56\\c&H000000&\\alpha&H70&\\blur10\\fad(90,120)}}{bot}")
    def plain(g, t_end, cy):
        kw = keyword(g)
        txt = " ".join((r"{\fnBDT Mont Black}" + w["w"] + r"{\fnBDT Mont Medium}") if w is kw else w["w"] for w in g)
        s_ = g[0]["t"]
        events.append(f"Dialogue: 0,{ts(s_)},{ts(t_end)},Cap,,0,0,0,,{{\\an2\\pos(543,{cy+4})\\fnBDT Mont Medium\\fs66\\c&H000000&\\alpha&H70&\\blur10\\fad(80,120)}}{txt}")
        events.append(f"Dialogue: 1,{ts(s_)},{ts(t_end)},Cap,,0,0,0,,{{\\an2\\pos(540,{cy})\\fnBDT Mont Medium\\fs66\\c&HFFFFFF&\\blur0.5\\fad(80,120)}}{txt}")
    groups = chunk(5, 0.45, adaptive=False)
    hook = CFG.get("hook", {}); hook_end = hook.get("dur", 3.0) + 0.6
    if hook:
        l2 = hook.get("line2", "").split(); kwh = l2[-1].strip(".") if l2 else ""
        top = (hook.get("line1", "") + " " + " ".join(l2[:-1])).strip()
        lockup(top, kwh, hook.get("pink_sub", ""), 0.05, 0.35, 0.6, hook_end, CY)
    prev_kw_t = -99
    for gi, g in enumerate(groups):
        if hook and g[0]["t"] < hook_end: continue
        t_end = min(groups[gi+1][0]["t"] if gi+1 < len(groups) else total, g[-1]["t"] + 1.1)
        kw = keyword(g)
        if kw is not None and len(g) >= 2 and kw["t"] - prev_kw_t > 1.6 and len(kw["w"]) <= 11:
            i = g.index(kw); top = " ".join(x["w"] for x in g[:i]); bot = " ".join(x["w"] for x in g[i+1:])
            s_bot = g[i+1]["t"] if i+1 < len(g) else t_end
            lockup(top, kw["w"].strip(".,!?"), bot, g[0]["t"], kw["t"], s_bot, t_end, CY); prev_kw_t = kw["t"]
        else:
            plain(g, t_end, CY - 20)
    # ---------- floating photo cards: the creator's own B-roll or photos, timed to what they say ----------
    # edit.json "photos": [{"src": "<image or video>", "ss": 1.2, "at": "phrase they say", "after": 0, "dur": 2.6}]
    # No "photos" (or an empty list) = no cards. Never use stills of the creator's own talking footage.
    spots = [(50, 130, -4), (730, 170, 4), (70, 560, 3), (750, 590, -4), (400, 90, -2)]
    photos = CFG.get("photos", [])
    placed = []
    for k, ph in enumerate(photos[:8]):
        if ph.get("at"):
            s0 = find(ph["at"].lower(), ph.get("after", 0.0))
            if s0 is None: print("photo cue not found:", ph["at"]); continue
            s0 += ph.get("offset", 0.0)
        else:
            s0 = 0.25 + k * 0.22                               # no cue: float in together during the hook
        e0 = min(total - 0.1, s0 + ph.get("dur", 2.6 if ph.get("at") else max(1.5, hook_end - s0)))
        if e0 - s0 < 0.6: continue
        raw = os.path.join(CARDS, f"photo{k}.jpg")
        src = ph["src"]
        if src.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".heic")):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-frames:v", "1", raw], check=True)
        else:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(ph.get("ss", 0.8)), "-i", src, "-frames:v", "1", raw], check=True)
        busy = [p for p in placed if p[1] > s0 and p[0] < e0]           # spots already on screen
        x, y, ang = [sp for sp in spots if sp not in [b[2] for b in busy]][0] if len(busy) < len(spots) else spots[k % len(spots)]
        placed.append((s0, e0, (x, y, ang)))
        im = Image.open(raw).convert("RGB"); im = ImageOps.fit(im, (270, 390), centering=(0.5, 0.45))
        m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width-1, im.height-1), 22, fill=255)
        card = Image.new("RGBA", (im.width+40, im.height+40), (0, 0, 0, 0))
        sh = Image.new("RGBA", card.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((20, 26, 20+im.width, 26+im.height), 22, fill=(0, 0, 0, 110))
        card.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
        frame = Image.new("RGBA", (im.width+12, im.height+12), (0, 0, 0, 0)); ImageDraw.Draw(frame).rounded_rectangle((0, 0, im.width+11, im.height+11), 26, fill=(255, 255, 255, 255))
        card.alpha_composite(frame, (14, 14)); ci = im.convert("RGBA"); ci.putalpha(m); card.alpha_composite(ci, (20, 20))
        card = card.rotate(ang, resample=Image.BICUBIC, expand=True)
        fp = os.path.join(CARDS, f"photo{k}.png"); card.save(fp)
        overlays.append((fp, x, y, s0, e0))

# ---------- write captions ----------
ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,BDT Inter Regular,60,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,1,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(_quiet(events, WORK)) + "\n"
assp = os.path.join(WORK, f"caps_{STYLE}.ass"); open(assp, "w").write(ass)

# ---------- composite ----------
cmd = ["ffmpeg", "-v", "error", "-y", "-i", base]; fcs = []; last = "[0:v]"
if False:
    sp = f"[0:v]split={len(blur_ranges)+1}" + "".join(f"[s{i}]" for i in range(len(blur_ranges)+1)); fcs.append(sp); last = "[s0]"
    for i, (a, b) in enumerate(blur_ranges, 1):
        a0 = max(0, a - 0.05); d = b - a0
        fcs.append(f"[s{i}]trim=start={a0:.3f}:duration={d+0.1:.3f},setpts=PTS-STARTPTS,gblur=sigma=34,format=yuva420p,fade=t=in:st=0:d=0.25:alpha=1,fade=t=out:st={max(0,d-0.25):.3f}:d=0.25:alpha=1,setpts=PTS+{a0:.3f}/TB[g{i}]")
        fcs.append(f"{last}[g{i}]overlay=0:0:eof_action=pass:enable='between(t,{a0:.3f},{b:.3f})'[gb{i}]"); last = f"[gb{i}]"
for n, (path, x, y, s, e) in enumerate(overlays):
    d = e - s
    cmd += ["-framerate", "30", "-loop", "1", "-t", f"{d+0.1:.3f}", "-i", path]
    fcs.append(f"[{n+1}:v]format=rgba,fade=t=in:st=0:d=0.16:alpha=1,fade=t=out:st={max(0, d-0.22):.3f}:d=0.22:alpha=1,setpts=PTS+{s:.3f}/TB[c{n}]")
    fcs.append(f"{last}[c{n}]overlay=x={x}:y='{y}+max(0\\,(1-(t-{s:.3f})/0.16))*30+9*sin(2*PI*(t-{s:.3f})/2.6)':eof_action=pass:enable='between(t,{s:.3f},{e:.3f})'[o{n}]"); last = f"[o{n}]"
ap = assp.replace(":", "\\:")
import brand as _b; _BF = _b.patch_ass(ap, _b.Brand(CFG), F)   # their own brand fonts in the captions, if they have them
fcs.append(f"{last}ass='{ap}':fontsdir='{_BF}'[vout]")
final = os.path.join(OUT, CFG.get("output", "edit.mp4").replace(".mp4", f"-{STYLE}.mp4"))
cmd += ["-filter_complex", ";".join(fcs), "-map", "[vout]", "-map", "0:a", "-c:v", "libx264", *TAGS, "-preset", "medium", "-crf", "21",
        "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", final]
subprocess.run(cmd, check=True)
print(final, "events", len(events), "blur", blur_ranges, "rate", round(RATE,2), "fast", FAST)
