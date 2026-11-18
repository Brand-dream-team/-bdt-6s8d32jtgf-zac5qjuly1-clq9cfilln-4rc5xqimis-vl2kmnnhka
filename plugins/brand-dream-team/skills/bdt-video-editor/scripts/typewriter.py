"""Brand Dream Team preset: Typewriter.
Monospace caps captions typed on in white label boxes, full white title pages
(big bold word + small typewriter line), and split screens (B-roll top, creator bottom)
with black caption boxes.
usage: python3 typewriter.py <words.json (remapped)> <base.mp4> <plan.json> <out.mp4>"""
import json, subprocess, sys, os
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from sdr import sdr_vf, TAGS
from PIL import ImageFont

WJ, BASE, PLAN, OUT = sys.argv[1:5]
HERE = os.path.dirname(os.path.abspath(__file__)); FD = os.path.join(HERE, "..", "fonts")
W, H = 1080, 1920
P = json.load(open(PLAN))
words = [dict(w) for w in json.load(open(WJ)) if w["w"].strip()]
for w in words: w["w"] = w["w"].upper()

CAP = 62                                                  # caption size
ADV = ImageFont.truetype(os.path.join(FD, "PlexMono-SemiBold.ttf"), CAP).getlength("M")
TOTAL = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", BASE], capture_output=True, text=True).stdout)

def mode_at(t):
    for p in P["pages"]:
        if p["a"] <= t < p["b"]: return "page"
    for s in P["splits"]:
        if s["a"] <= t < s["b"]: return "split"
    return "cam"

# ---- group words: up to 3 words / 17 chars, break on pauses and mode changes
groups, cur = [], []
for i, w in enumerate(words):
    if cur:
        txt = " ".join(x["w"] for x in cur + [w])
        gap = w["t"] - cur[-1]["te"]
        if len(cur) >= 3 or len(txt) > 17 or gap > 0.28 or mode_at(w["t"]) != mode_at(cur[0]["t"]):
            groups.append(cur); cur = []
    cur.append(w)
groups.append(cur)

def ts(x):
    x = max(0, x); return f"{int(x//3600)}:{int(x%3600//60):02d}:{x%60:05.2f}"

ev = []
for gi, g in enumerate(groups):
    a = g[0]["t"]; nxt = groups[gi+1][0]["t"] if gi + 1 < len(groups) else TOTAL
    b = min(nxt, g[-1]["te"] + 0.6); b = max(b, a + 0.35)
    text = " ".join(x["w"] for x in g); m = mode_at(a)
    style = {"cam": "Box", "page": "Page", "split": "Split"}[m]
    y = {"cam": 1235, "page": 1180, "split": 960}[m]
    x0 = round(W/2 - len(text)*ADV/2)
    step = min(0.035, (b - a) * 0.45 / max(1, len(text)))
    for k in range(1, len(text) + 1):
        if k < len(text) and text[k-1] == " ": continue
        s = a + (k-1)*step; e = a + k*step if k < len(text) else b
        if e - s < 0.005: continue
        ev.append(f"Dialogue: 2,{ts(s)},{ts(e)},{style},,0,0,0,,{{\\an4\\pos({x0},{y})}}{text[:k]}")

# ---- white title pages: big word pops in, small typewriter line under it
for p in P["pages"]:
    a, b = p["a"], p["b"]
    ev.append(f"Dialogue: 3,{ts(a)},{ts(b)},Big,,0,0,0,,{{\\an5\\pos(540,820)\\fscx88\\fscy88\\t(0,180,\\fscx100\\fscy100)\\fad(60,0)}}{p['big']}")
    sub = p["small"]; n = len(sub)
    for k in range(1, n + 1):
        s = a + 0.25 + (k-1)*0.03; e = a + 0.25 + k*0.03 if k < n else b
        ev.append(f"Dialogue: 3,{ts(s)},{ts(e)},Small,,0,0,0,,{{\\an7\\pos({round(540 - n*19.2/2)},{935})}}{sub[:k]}")

ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Box,IBM Plex Mono SemiBold,{CAP},&H00141414,&H00141414,&H00FFFFFF,&H00FFFFFF,0,0,0,0,100,100,0,0,3,16,0,4,0,0,0,1
Style: Split,IBM Plex Mono SemiBold,{CAP},&H00FFFFFF,&H00FFFFFF,&H00141414,&H00141414,0,0,0,0,100,100,0,0,3,16,0,4,0,0,0,1
Style: Page,IBM Plex Mono SemiBold,{CAP},&H00141414,&H00141414,&H00FFFFFF,&H00FFFFFF,0,0,0,0,100,100,0,0,1,0,0,4,0,0,0,1
Style: Big,Inter Display Black,210,&H00141414,&H00141414,&H00FFFFFF,&H00FFFFFF,0,0,0,0,100,100,-4,0,1,0,0,5,0,0,0,1
Style: Small,IBM Plex Mono Medium,32,&H00141414,&H00141414,&H00FFFFFF,&H00FFFFFF,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n"
assp = os.path.join(os.path.dirname(os.path.abspath(OUT)), "typewriter.ass"); open(assp, "w").write(ass)

# ---- compose: splits (B-roll top, creator bottom), white pages, captions
inputs = ["-i", BASE]; fc = "[0:v]setsar=1,format=yuv420p[v0];"; last = "v0"
cam = f"[0:v]crop=1080:960:0:{P.get('face_y', 360)},setsar=1[camc];"
fc += cam; fc += "[camc]split=" + str(max(1, len(P["splits"]))) + "".join(f"[cc{i}]" for i in range(max(1, len(P["splits"])))) + ";"
for i, s in enumerate(P["splits"]):
    inputs += ["-i", s["broll"]]; k = i + 1
    d = s["b"] - s["a"]
    fc += f"[{k}:v]{sdr_vf(s['broll'])}trim=start={s.get('ss',0)}:duration={d},setpts=PTS-STARTPTS+{s['a']}/TB,scale=1080:1920,crop=1080:960:0:{s.get('crop_y', 480)},setsar=1[t{i}];"
    fc += f"[{last}][t{i}]overlay=0:0:eof_action=pass:enable='between(t,{s['a']},{s['b']})'[o{i}a];"
    fc += f"[o{i}a][cc{i}]overlay=0:960:enable='between(t,{s['a']},{s['b']})',drawbox=0:957:1080:6:white:t=fill:enable='between(t,{s['a']},{s['b']})'[o{i}];"
    last = f"o{i}"
for j, p in enumerate(P["pages"]):
    fc += f"[{last}]drawbox=0:0:1080:1920:0xFAFAF7:t=fill:enable='between(t,{p['a']},{p['b']})'[pg{j}];"; last = f"pg{j}"
fc += f"[{last}]subtitles='{assp}':fontsdir='{FD}'[o]"
cmd = ["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", fc, "-map", "[o]", "-map", "0:a?", "-c:v", "libx264", *TAGS, "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", OUT]
subprocess.run(cmd, check=True)
print("ok", OUT, len(groups), "caption groups")
