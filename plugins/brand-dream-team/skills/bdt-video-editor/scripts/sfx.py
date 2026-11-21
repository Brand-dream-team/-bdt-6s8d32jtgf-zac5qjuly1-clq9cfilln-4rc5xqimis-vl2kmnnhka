"""Add sound effects to a finished video.
Usage: python3 sfx.py <project> <video_in> <video_out> [cues.json]
Reads "sounds" from <project>/edit.json:  [{"id": "pop", "at": "exact words"}, {"id": "whoosh", "t": 0.0}, ...]
  id   = a sound in ../sounds/sounds.json, or a file name (without extension) in "sounds_dir" (their own Sounds folder)
  at   = words they say; the sound lands as those words start (found in the FINISHED video, so cuts don't matter)
  t    = or an exact second in the finished video
  gain = optional, 0.1 to 1.0 (default 0.32 so the voice always stays on top)
"""
import json, os, subprocess, sys, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
work, vin, vout = os.path.abspath(sys.argv[1]), sys.argv[2], sys.argv[3]
final = vout
if os.path.abspath(vin) == os.path.abspath(vout): vout = vout + ".sfx.mp4"
cfg = json.load(open(os.path.join(work, "edit.json")))
cues = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else (cfg.get("sounds") or [])
if not cues:
    if os.path.abspath(vin) != os.path.abspath(final): subprocess.run(["cp", vin, final], check=True)
    print("no sounds"); sys.exit(0)
lib = {s["id"]: os.path.join(ROOT, "sounds", s["id"] + ".mp3") for s in json.load(open(os.path.join(ROOT, "sounds", "sounds.json")))}
own = os.path.expanduser(cfg.get("sounds_dir") or "")
if own and os.path.isdir(own):
    for f in os.listdir(own):
        if re.search(r"\.(mp3|wav|m4a|aac|ogg|aif|aiff)$", f, re.I): lib.setdefault(os.path.splitext(f)[0].lower(), os.path.join(own, f))
words = None
def norm(s): return re.sub(r"[^a-z0-9' ]", "", s.lower()).split()
def find(phrase, after=0.0):
    global words
    if words is None:
        wav = os.path.join(work, "_sfx.wav"); out = os.path.join(work, "_sfx_words.json")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vin, "-ac", "1", "-ar", "16000", wav], check=True)
        md = os.path.expanduser("~/.cache/bdt/sherpa-onnx-zipformer-en-2023-06-26")
        subprocess.run([sys.executable, os.path.join(HERE, "tr2.py"), md, wav, out], check=True, capture_output=True)
        words = [w for w in json.load(open(out)) if w["w"].strip()]
    want = norm(phrase); seq = [norm(w["w"])[0] if norm(w["w"]) else "" for w in words]
    for i in range(len(seq) - len(want) + 1):
        if words[i]["s"] >= after and seq[i:i + len(want)] == want: return words[i]["s"]
    for i, s in enumerate(seq):  # fall back to the first word
        if s == want[0] and words[i]["s"] >= after: return words[i]["s"]
    return None
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", vin], capture_output=True, text=True).stdout)
res = []
for c in cues:
    f = lib.get(str(c.get("id", "")).lower())
    if not f: print("skip unknown sound:", c.get("id")); continue
    t = c.get("t")
    if t is None and c.get("at"): t = find(c["at"], float(c.get("after", 0)))
    if t is None: print("skip, words not found:", c.get("at")); continue
    res.append((max(0.0, min(float(t) + float(c.get("nudge", -0.04)), dur - 0.2)), f, float(c.get("gain", 0.32)), c.get("force")))
placed, last = [], -9.0
for t, f, g, force in sorted(res, key=lambda r: r[0]):
    if t - last < 0.9 and not force: print("skip, too close to the last sound:", os.path.basename(f)); continue
    placed.append((t, f, g)); last = t
if not placed:
    if os.path.abspath(vin) != os.path.abspath(final): subprocess.run(["cp", vin, final], check=True)
    print("no sounds placed"); sys.exit(0)
cmd = ["ffmpeg", "-v", "error", "-y", "-i", vin]
for _, f, _ in placed: cmd += ["-i", f]
fc = []
for i, (t, _, g) in enumerate(placed, 1):
    ms = int(t * 1000); fc.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,volume={g},adelay={ms}|{ms}[s{i}]")
fc.append("[0:a]aresample=48000,aformat=channel_layouts=stereo[v]")
fc.append("[v]" + "".join(f"[s{i}]" for i in range(1, len(placed) + 1)) + f"amix=inputs={len(placed)+1}:duration=first:normalize=0,alimiter=limit=0.95[a]")
cmd += ["-filter_complex", ";".join(fc), "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", vout]
subprocess.run(cmd, check=True)
if vout != final: os.replace(vout, final)
print("sounds:", ", ".join(f"{os.path.basename(f).rsplit('.',1)[0]}@{t:.2f}s" for t, f, _ in placed))
