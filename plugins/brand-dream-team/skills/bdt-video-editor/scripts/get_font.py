"""Fetch a Google Font by name into the skill's fonts/ folder, for a creator whose Brand DNA names their fonts.
usage: python3 scripts/get_font.py "Cormorant Garamond" ["Bold"]
Prints the file name(s) to put in edit.json "brand_fonts" (e.g. {"accent": ["CormorantGaramond-Italic[wght].ttf", 700]}).
Fonts that aren't on Google Fonts: ask the creator to attach the .ttf/.otf file and use its full path instead."""
import os, re, sys, urllib.request, urllib.parse
FD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts"))
name = sys.argv[1]; slug = re.sub(r"[^a-z0-9]", "", name.lower())
base = "https://raw.githubusercontent.com/google/fonts/main"
meta = None
for lic in ("ofl", "apache", "ufl"):
    try: meta = urllib.request.urlopen(f"{base}/{lic}/{slug}/METADATA.pb", timeout=20).read().decode(); break
    except Exception: continue
if not meta: sys.exit(f"'{name}' isn't on Google Fonts. Ask the creator for the font file.")
files = re.findall(r'filename:\s*"([^"]+)"', meta)
for f in files:
    dst = os.path.join(FD, f)
    if not os.path.exists(dst):
        urllib.request.urlretrieve(f"{base}/{lic}/{slug}/{urllib.parse.quote(f)}", dst)
    print(f)
if any("[" in f for f in files): print("variable font: give a weight, e.g. [\"file.ttf\", 700] for bold, 900 for black, 600 for semibold, 500 for medium")
