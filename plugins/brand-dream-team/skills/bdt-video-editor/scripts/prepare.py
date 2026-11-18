"""Prepare a video for editing: install tools, extract audio, transcribe with word timings.

Usage: python3 prepare.py <video file> <project folder>
Works with any camera or phone video (DJI, GoPro, iPhone, Android, laptop; .mp4 .mov .mts .mkv .avi ...,
HEVC/10-bit/HDR, sideways or landscape). It first makes <project>/source.mp4: vertical 1080x1920, 30 fps,
SDR, H.264 with clean audio. Use source.mp4 as "src" in edit.json, never the original.
Writes <project>/source.mp4, mine.wav and words.json, and prints the transcript with word numbers.
"""
import os, sys, subprocess, json, shutil, tarfile, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
src, work = sys.argv[1], os.path.abspath(sys.argv[2])
os.makedirs(work, exist_ok=True)

def pip(*pkgs):
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *pkgs], check=False)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", *pkgs], check=False)

for mod, pkg in [("sherpa_onnx", "sherpa-onnx"), ("soundfile", "soundfile"), ("PIL", "pillow")]:
    try:
        __import__(mod)
    except ImportError:
        pip(pkg)

if not shutil.which("ffmpeg"):
    sys.exit("FFmpeg is not available in this environment. It is required for editing.")

model_dir = os.path.expanduser("~/.cache/bdt/sherpa-onnx-zipformer-en-2023-06-26")
if not os.path.exists(os.path.join(model_dir, "tokens.txt")):
    os.makedirs(os.path.dirname(model_dir), exist_ok=True)
    url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-zipformer-en-2023-06-26.tar.bz2"
    tmp = os.path.join(os.path.dirname(model_dir), "model.tar.bz2")
    print("Downloading speech model (one time)...", flush=True)
    urllib.request.urlretrieve(url, tmp)
    with tarfile.open(tmp) as t:
        t.extractall(os.path.dirname(model_dir))
    os.remove(tmp)

# ---- 1. one clean vertical source, whatever the camera ----
sys.path.insert(0, HERE)
from sdr import sdr_vf, TAGS
orig = src
source = os.path.join(work, "source.mp4")
if not os.path.exists(source):
    probe = [s.get("codec_type") for s in json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
             "-of", "json", orig], capture_output=True, text=True).stdout or "{}").get("streams", [])]
    if "video" not in probe:
        sys.exit("This file has no video in it. Attach the video itself (not a link or a preview).")
    has_audio = "audio" in probe
    # ffmpeg turns sideways phone video upright on its own; landscape is cropped to a centered vertical frame
    vf = f"{sdr_vf(orig)}scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920:(iw-1080)/2:(ih-1920)*0.4,fps=30,setsar=1,format=yuv420p"
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", orig]
    if not has_audio:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    cmd += ["-map", "0:v:0", "-map", "0:a:0" if has_audio else "1:a:0", "-vf", vf,
            "-c:v", "libx264", *TAGS, "-preset", "veryfast", "-crf", "16",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest", "-movflags", "+faststart", source]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(source):
        sys.exit("Couldn't read this video file: " + (r.stderr.strip().splitlines() or ["unknown error"])[-1])
src = source
print(f"source: {source}  (use this as src in edit.json)")

wav = os.path.join(work, "mine.wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ac", "1", "-ar", "16000", wav], check=True)
subprocess.run([sys.executable, os.path.join(HERE, "tr2.py"), model_dir, wav, os.path.join(work, "words.json")],
               check=True, stdout=subprocess.DEVNULL)

words = json.load(open(os.path.join(work, "words.json")))
dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                     capture_output=True, text=True).stdout.strip()
print(f"duration: {dur}s, words: {len(words)}")
print(" ".join(f"{i}:{w['w'].lower()}@{w['s']}" for i, w in enumerate(words)))
