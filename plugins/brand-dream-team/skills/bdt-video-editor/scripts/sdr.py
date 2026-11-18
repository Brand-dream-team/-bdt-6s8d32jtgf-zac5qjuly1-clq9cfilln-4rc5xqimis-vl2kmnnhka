"""iPhone clips are often HDR (HLG). Edits must be normal (SDR, bt709) video, or phones show the whole
video, text included, in HDR: brand colors turn muddy and white looks gray.
sdr_vf(src) -> filter prefix that converts an HDR clip to SDR ("" when the clip is already SDR).
TAGS -> ffmpeg output flags that label the result as SDR bt709."""
import subprocess

def is_hdr(src):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer",
                          "-of", "csv=p=0", src], capture_output=True, text=True).stdout.replace(",", " ").split()
    out = out[0] if out else ""
    return out in ("arib-std-b67", "smpte2084")

def sdr_vf(src):
    if not is_hdr(src): return ""
    # mobius keeps highlights soft; the eq step restores the warmth and contrast tone mapping takes out,
    # so skin doesn't turn gray
    # neutral conversion: reference white stays white, highlights roll off gently, no color boosts
    return ("zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=mobius:param=0.8:desat=0,"
            "zscale=t=bt709:m=bt709:r=tv,format=yuv420p,"
            "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv,")

TAGS = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]


def measure(src, ss, vf_pre=""):
    """mean brightness (0-255) and mean saturation (0-255) of one frame after conversion."""
    import os, tempfile
    from PIL import Image, ImageStat
    fp = os.path.join(tempfile.mkdtemp(), "m.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{ss:.2f}", "-i", src, "-frames:v", "1",
                    "-vf", f"{vf_pre}{sdr_vf(src)}scale=270:480:force_original_aspect_ratio=increase,crop=270:480,format=rgb24", fp])
    im = Image.open(fp).convert("RGB")
    return ImageStat.Stat(im.convert("L")).mean[0], ImageStat.Stat(im.convert("HSV")).mean[1]

def match_vf(lum, sat, t_lum, t_sat):
    """eq filter that pulls one clip toward the shared look (gentle, clamped)."""
    import math
    g = math.log(max(t_lum, 1) / 255) / math.log(max(lum, 1) / 255)      # gamma that maps lum -> t_lum
    g = max(0.8, min(1.25, 1 / g))
    k = max(0.85, min(1.2, t_sat / max(sat, 1)))
    return f"eq=gamma={g:.3f}:saturation={k:.3f},"
