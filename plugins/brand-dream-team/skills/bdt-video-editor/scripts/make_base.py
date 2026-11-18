import json, subprocess, os
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
W, H = CFG.get("size", [1080, 1920])

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
        z = 1.0 if i % 2 == 0 else CFG.get("punch", 1.12)
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


# timeline for other presets (Typewriter): remapped word times
for w in words: w["te"] = remap(w.get("e", w["s"] + 0.3))
json.dump([{"w": w["w"], "t": round(w["t"], 2), "te": round(w["te"], 2)} for w in words], open(os.path.join(WORK, "timeline_words.json"), "w"))
print("base:", base, "length:", round(total, 2), "s")
