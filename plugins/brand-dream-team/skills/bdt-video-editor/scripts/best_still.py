"""Pick the best still from a clip for carousels and covers: sharp (no motion blur), and when a person
is in frame, a clear front-facing face. usage: best_still(src, out_png[, start, end, need_face])"""
import os, subprocess, tempfile, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sdr import sdr_vf

def best_still(src, out, start=0.0, end=None, need_face=None, samples=24):
    import cv2
    det = cv2.CascadeClassifier(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "haarcascade_frontalface_default.xml"))
    if end is None:
        end = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                                   capture_output=True, text=True).stdout.strip() or 1)
    tmp = tempfile.mkdtemp(); best = (-1, None)
    span = max(0.1, end - start - 0.1)
    for k in range(samples):
        t = start + 0.05 + span * k / max(1, samples - 1)
        fp = os.path.join(tmp, f"{k}.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", src, "-frames:v", "1", "-vf", sdr_vf(src) + "format=rgb24", fp])
        img = cv2.imread(fp)
        if img is None: continue
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY); h, w = g.shape
        small = cv2.resize(g, (540, int(540 * h / w)))
        sharp = cv2.Laplacian(small, cv2.CV_64F).var()
        faces = det.detectMultiScale(small, 1.1, 7, minSize=(60, 60))
        face_score = 0.0
        if len(faces):
            x, y, fw, fh = max(faces, key=lambda r: r[2] * r[3])
            crop = small[y:y + fh, x:x + fw]
            fsharp = cv2.Laplacian(crop, cv2.CV_64F).var()
            face_score = 1.0 + min(fsharp / 150, 2.0)          # a clear, sharp face wins
        if need_face and not len(faces): face_score = -0.5
        score = min(sharp / 200, 3.0) + face_score * 2
        if score > best[0]: best = (score, fp, t)
    if best[1] is None: raise RuntimeError("no frame found")
    os.replace(best[1], out)
    return best[2]
