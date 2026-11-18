"""B-roll Matchmaker step 1: look at clips.
Makes one contact sheet per 8 clips (3 frames each: 15%, 50%, 85%) so Claude can see what's in them,
and writes clips.json (path, duration, width, height, rotation-corrected size, is_photo).
usage: python3 broll_look.py <out folder> <clip or photo> [<clip or photo> ...]"""
import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageOps

out = os.path.abspath(sys.argv[1]); os.makedirs(out, exist_ok=True)
files = sys.argv[2:]
PHOTO = (".jpg", ".jpeg", ".png", ".heic", ".webp")
FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts", "Inter-Bold.otf")
info = []
for k, f in enumerate(files):
    if f.lower().endswith(PHOTO):
        im = ImageOps.exif_transpose(Image.open(f))
        info.append({"id": k, "src": f, "photo": True, "dur": 0, "w": im.width, "h": im.height}); continue
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f], capture_output=True, text=True).stdout.strip()
    d = float(p or 0)
    fr = os.path.join(out, f"_f{k}.jpg")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(d * 0.5), "-i", f, "-frames:v", "1", fr])
    w, h = Image.open(fr).size if os.path.exists(fr) else (0, 0)
    info.append({"id": k, "src": f, "photo": False, "dur": round(d, 2), "w": w, "h": h})
json.dump(info, open(os.path.join(out, "clips.json"), "w"), indent=1)

TW, TH = 200, 356
font = ImageFont.truetype(FONT, 26)
for b in range(0, len(info), 8):
    batch = info[b:b + 8]
    sheet = Image.new("RGB", (TW * 3 + 10, (TH + 8) * len(batch)), "white")
    for r, c in enumerate(batch):
        for j, frac in enumerate((0.15, 0.5, 0.85)):
            if c["photo"]:
                im = ImageOps.exif_transpose(Image.open(c["src"])).convert("RGB")
            else:
                fp = os.path.join(out, f"_t{c['id']}_{j}.jpg")
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(c["dur"] * frac), "-i", c["src"], "-frames:v", "1", fp])
                im = Image.open(fp).convert("RGB") if os.path.exists(fp) else Image.new("RGB", (TW, TH), "gray")
            im = ImageOps.fit(im, (TW, TH))
            d = ImageDraw.Draw(im)
            if j == 0:
                d.rectangle((0, 0, 92, 38), fill="black"); d.text((6, 4), f"#{c['id']}", font=font, fill="white")
            sheet.paste(im, (j * (TW + 5), r * (TH + 8)))
    sheet.save(os.path.join(out, f"sheet_{b // 8 + 1}.jpg"), quality=85)
print(f"{len(info)} clips, {((len(info) - 1) // 8) + 1} sheets in {out}")
for c in info: print(f"#{c['id']} {'photo' if c['photo'] else str(c['dur'])+'s'} {c['w']}x{c['h']} {os.path.basename(c['src'])}")
