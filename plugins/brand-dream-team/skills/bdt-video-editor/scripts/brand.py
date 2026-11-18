"""Brand Dream Team: one place for the creator's brand colors and fonts.
Every effect, card and look reads from here, so nothing ships in Destiny's pinks or fonts
unless that IS the creator's brand.

edit.json keys it reads:
  "palette": {"accent", "on_accent", "accent_on_dark", "ghost"}   (from palettes.json / Brand DNA)
  "look":    their preset (soft_glass, bold_highlight, pink_pop, typewriter, pink_label, chunky_word)
  "brand_fonts": optional {bold, black, semi, med, accent}: file names in fonts/, full paths,
                 or [file, weight] for variable fonts. Use scripts/get_font.py to fetch a Google font.
"""
import os
from PIL import ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); FD = os.path.normpath(os.path.join(HERE, "..", "fonts"))

def hx(h):
    if isinstance(h, (list, tuple)): return tuple(int(x) for x in h[:3])
    h = str(h).lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def lum(c):
    v = [(x / 255) ** 2.2 for x in c[:3]]; return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
def contrast(a, b):
    x, y = sorted((lum(a), lum(b))); return (y + 0.05) / (x + 0.05)
def mix(c, t, k): return tuple(int(round(a + (b - a) * k)) for a, b in zip(c[:3], t))
def ass(c): c = hx(c); return "&H%02X%02X%02X&" % (c[2], c[1], c[0])

FONTSETS = {
    "soft_glass":     {"bold": "InterDisplay-Bold.otf", "black": "InterDisplay-Black.otf", "semi": "InterDisplay-SemiBold.otf", "med": "Inter-Medium.otf", "accent": "PlayfairDisplay-BoldItalic.ttf"},
    "bold_highlight": {"bold": "InterDisplay-Bold.otf", "black": "InterDisplay-Black.otf", "semi": "InterDisplay-SemiBold.otf", "med": "Inter-Medium.otf", "accent": "PlayfairDisplay-BoldItalic.ttf"},
    "pink_pop":       {"bold": "BDTMontBold.ttf", "black": "BDTMontBlack.ttf", "semi": "BDTMontMedium.ttf", "med": "BDTInterMedium.ttf", "accent": "BDTMontBlack.ttf"},
    "typewriter":     {"bold": "PlexMono-SemiBold.ttf", "black": "PlexMono-SemiBold.ttf", "semi": "PlexMono-SemiBold.ttf", "med": "PlexMono-Medium.ttf", "accent": "CourierPrime-Bold.ttf"},
    "pink_label":     {"bold": "BDTMontBold.ttf", "black": "BDTMontBlack.ttf", "semi": "BDTMontMedium.ttf", "med": "BDTInterMedium.ttf", "accent": "BDTInterHeavyItalic.ttf"},
    "chunky_word":    {"bold": "InterDisplay-Bold.otf", "black": "InterDisplay-Black.otf", "semi": "InterDisplay-SemiBold.otf", "med": "Inter-Medium.otf", "accent": "BDTMontBlack.ttf"},
}
# the built-in font files the effects are drawn with, and which role each one plays
ROLE_OF = {
    "InterDisplay-Bold.otf": "bold", "Inter-Bold.otf": "bold", "BDTMontBold.ttf": "bold", "Montserrat-800.ttf": "bold",
    "InterDisplay-Black.otf": "black", "Inter-Black.otf": "black", "BDTMontBlack.ttf": "black",
    "InterDisplay-SemiBold.otf": "semi", "Inter-SemiBold.otf": "semi", "Montserrat-600.ttf": "semi",
    "Inter-Medium.otf": "med", "BDTInterMedium.ttf": "med", "BDTInterRegular.ttf": "med",
    "PlayfairDisplay-BoldItalic.ttf": "accent", "PlayfairDisplay-Italic-VF.ttf": "accent",
}

# The Studio's Fonts tab ("Hook font: <name>"): the hook title + the big accent words. Captions stay the preset's.
STUDIO_FONTS = {
    "editorial": {},
    "script + clean": {"title": "InterDisplay-Bold.otf", "accent": "MrsSaintDelafield-Regular.ttf"},
    "wide + flourish": {"title": "Lexend-Bold.ttf", "accent": "MonsieurLaDoulaise-Regular.ttf"},
    "grotesk + serif": {"title": "Archivo-SemiBold.ttf", "accent": "NotoSerifCondensed-SemiBoldItalic.ttf"},
    "headline mix": {"title": "ArchivoBlack-Regular.ttf", "accent": "PlayfairDisplay-BoldItalic.ttf"},
    "quiet luxury": {"title": "InstrumentSerif-Regular.ttf", "accent": "InstrumentSerif-Italic.ttf"},
    "butter stack": {"title": "ArchivoBlack-Regular.ttf", "accent": "InstrumentSerif-Italic.ttf"},
    "magazine": {"title": "Lexend-ExtraBold.ttf", "accent": "PlayfairDisplay-BoldItalic.ttf"},
    "playfair italic": {"accent": "PlayfairDisplay-BoldItalic.ttf"},
    "instrument serif": {"title": "InstrumentSerif-Regular.ttf", "accent": "InstrumentSerif-Italic.ttf"},
    "noto serif condensed": {"accent": "NotoSerifCondensed-SemiBoldItalic.ttf"},
    "inter": {"title": "InterDisplay-Bold.otf", "accent": "InterDisplay-Black.otf"},
    "montserrat": {"title": "Montserrat-800.ttf", "accent": "Montserrat-800.ttf"},
    "poppins": {"title": "Poppins-Bold.ttf", "accent": "Poppins-ExtraBold.ttf"},
    "lexend": {"title": "Lexend-Bold.ttf", "accent": "Lexend-ExtraBold.ttf"},
    "archivo": {"title": "Archivo-SemiBold.ttf", "accent": "Archivo-ExtraBold.ttf"},
    "archivo black": {"title": "ArchivoBlack-Regular.ttf", "accent": "ArchivoBlack-Regular.ttf"},
    "anton": {"title": "Anton-Regular.ttf", "accent": "Anton-Regular.ttf"},
    "open sans": {"title": "OpenSans-Bold.ttf", "accent": "OpenSans-ExtraBold.ttf"},
    "yellowtail": {"accent": "Yellowtail-Regular.ttf"},
    "mrs saint delafield": {"accent": "MrsSaintDelafield-Regular.ttf"},
    "monsieur la doulaise": {"accent": "MonsieurLaDoulaise-Regular.ttf"},
    "cookie": {"accent": "Cookie-Regular.ttf"},
    "caveat": {"accent": "Caveat-Bold.ttf"},
    "gaegu": {"accent": "Gaegu-Bold.ttf"},
}

def norm_look(v): return str(v or "soft_glass").lower().replace(" ", "_").replace("-", "_").replace("pinkpop", "pink_pop")

class Brand:
    def __init__(self, cfg, overrides=None):
        cfg = cfg or {}
        pal = {"accent": "#F5BACB", "on_accent": "#2B171C"}; pal.update(cfg.get("palette") or {})
        self.pal = pal
        self.acc = hx(pal["accent"])
        l = hx(pal.get("accent_on_dark") or pal["accent"])            # accent that reads on dark video / dark glass
        while lum(l) < 0.16: l = mix(l, (255, 255, 255), 0.12)
        d = self.acc                                                   # accent that reads on white cards
        while 1.05 / (lum(d) + 0.05) < 3.6: d = mix(d, (0, 0, 0), 0.08)
        self.light, self.deep = l, d
        on = hx(pal.get("on_accent", "#2B171C"))                       # text on an accent fill: keep it readable
        if contrast(on, l) < 3.0: on = (20, 16, 18) if contrast((20, 16, 18), l) >= contrast((255, 255, 255), l) else (255, 255, 255)
        self.on = on
        self.ghost = hx(pal.get("ghost") or pal.get("accent_on_dark") or pal["accent"])
        self.look = norm_look(cfg.get("look") or cfg.get("preset") or cfg.get("style"))
        fs = dict(FONTSETS.get(self.look, FONTSETS["soft_glass"]))
        custom = dict(cfg.get("brand_fonts") or {}); custom.update(overrides or {})
        fs.update(custom); self.custom = bool(custom)
        # Studio hook font: the hook title + every big accent word (their own font files still win)
        hk = STUDIO_FONTS.get(str(cfg.get("hook_font") or "").strip().strip(".").lower(), {})
        if hk.get("accent") and "accent" not in custom: fs["accent"] = hk["accent"]
        self.fonts = {r: self._resolve(v) for r, v in fs.items()}
        self.hook_title = self._resolve(custom.get("black") or hk["title"]) if (hk.get("title") or custom.get("black")) else None
        self.hook_accent = bool(hk.get("accent")) or "accent" in custom
        # which built-in fonts get swapped: all of them for another preset or their own fonts,
        # only the accent words for a Studio hook font; Soft Glass + Editorial = the original drawings
        if self.custom or self.look != "soft_glass": self.remap_roles = set(self.fonts)
        else: self.remap_roles = {"accent"} if self.hook_accent else set()
        self.remap = bool(self.remap_roles)

    def _resolve(self, v):
        name, w = (v[0], v[1]) if isinstance(v, (list, tuple)) else (v, None)
        p = name if os.path.isabs(name) else os.path.join(FD, name)
        if not os.path.exists(p): print(f"[brand] font not found: {name} (using Inter)"); p, w = os.path.join(FD, "InterDisplay-Bold.otf"), None
        return (p, w)

    def map(self, filename, own=False):
        """built-in font file -> (path, weight) in the creator's brand.
        own=True: inside a preset's own drawing, so only their own fonts / Studio hook font swap in."""
        role = ROLE_OF.get(os.path.basename(filename))
        roles = (set(self.fonts) if self.custom else {"accent"} if self.hook_accent else set()) if own else self.remap_roles
        if role and role in roles and role in self.fonts: return self.fonts[role]
        return (filename if os.path.isabs(filename) else os.path.join(FD, filename), None)

    def hook(self, size, default="InterDisplay-Bold.otf"):
        """the hook title font: Studio hook font / their own font, else the preset's"""
        p, w = self.hook_title or (os.path.join(FD, default), None); return load(p, size, w)

    def font(self, role_or_file, size):
        p, w = self.fonts[role_or_file] if role_or_file in self.fonts else self.map(role_or_file)
        return load(p, size, w)

# script fonts draw small next to a bold sans: bump them so the big word still reads big
SCRIPT_SCALE = {"MonsieurLaDoulaise-Regular.ttf": 1.45, "MrsSaintDelafield-Regular.ttf": 1.5, "Yellowtail-Regular.ttf": 1.15,
                "Cookie-Regular.ttf": 1.25, "Caveat-Bold.ttf": 1.2, "Gaegu-Bold.ttf": 1.15}
_fc = {}
def load(path, size, wght=None):
    size = size * SCRIPT_SCALE.get(os.path.basename(path), 1.0)
    k = (path, int(size), wght)
    if k not in _fc:
        f = ImageFont.truetype(path, int(size))
        if wght:
            try: f.set_variation_by_axes([wght])
            except Exception: pass
        f._wght = wght
        if os.path.dirname(os.path.abspath(path)) != FD or os.path.basename(path) not in ROLE_OF:
            f._fallback = _fallback_for(path, size)         # their own font may not have ♡ ✓ → etc.
        _fc[k] = f
    return _fc[k]

# ---- captions (ASS): swap the preset's font families for the creator's own brand fonts
ASS_ROLE = [("Inter Display SemiBold", "semi"), ("Inter Display Black", "black"), ("BDT Mont Black", "black"),
            ("BDT Mont Medium", "semi"), ("BDT Mont Bold", "bold"), ("Playfair Display", "accent"), ("Inter Display", "bold")]
def patch_ass(ass_path, B, fontsdir=FD):
    """Rewrite an .ass file to use the creator's brand fonts. Returns the fonts folder to burn with."""
    if not (B.custom or B.hook_accent or B.hook_title): return fontsdir
    import re, shutil, tempfile
    txt = open(ass_path, encoding="utf-8").read()
    fam = {}
    for r, (p, w) in B.fonts.items():
        fam[r] = ass_name(p)
    for name, role in ASS_ROLE:                       # longest names first, so "Inter Display" goes last
        if not B.custom and role != "accent": continue   # Studio hook font: captions stay the preset's
        if role in fam:
            sc = int(100 * SCRIPT_SCALE.get(os.path.basename(B.fonts[role][0]), 1.0))
            def blk(m, name=name, f=fam[role], sc=sc):       # swap the font, and size a script up in that same tag block
                b = re.sub(r"(?<=\\fn)" + re.escape(name) + r"(?=[\\}])", lambda _: f, m.group(0))
                if b != m.group(0): b = b.replace("\\b1", "\\b0").replace("\\i1", "\\i0")   # their font's own weight/slant, no fake bold
                if sc != 100 and b != m.group(0): b = re.sub(r"\\fs(\d+(?:\.\d+)?)", lambda q: "\\fs%.0f" % (float(q.group(1)) * sc / 100), b)
                return b
            txt = re.sub(r"\{[^}]*\}", blk, txt)
            txt = re.sub(r"(?<=,)" + re.escape(name) + r"(?=,)", fam[role], txt)
    open(ass_path, "w", encoding="utf-8").write(txt)
    d = tempfile.mkdtemp(prefix="bdtfonts_")
    for f in os.listdir(fontsdir): shutil.copy(os.path.join(fontsdir, f), d)
    for p, w in list(B.fonts.values()) + ([B.hook_title] if B.hook_title else []):
        if os.path.dirname(p) != os.path.normpath(fontsdir): shutil.copy(p, d)
    return d

def ass_name(path):
    """the name libass knows a font file by (its full name), for \\fn overrides"""
    try:
        from fontTools.ttLib import TTFont
        n = TTFont(path, lazy=True)["name"]; return str(n.getDebugName(4) or n.getDebugName(1))
    except Exception: return ImageFont.truetype(path, 20).getname()[0]

# ---- missing glyphs in a creator's own font fall back to Inter (♡, ✓, arrows...)
_cm = {}
def _cmap(path):
    if path not in _cm:
        try:
            from fontTools.ttLib import TTFont; _cm[path] = set(TTFont(path, lazy=True).getBestCmap())
        except Exception: _cm[path] = None
    return _cm[path]
def _fallback_for(path, size):
    if _cmap(path) is None: return None
    return ImageFont.truetype(os.path.join(FD, "InterDisplay-Bold.otf"), int(size))
def _runs(text, f):
    cm = _cmap(f.path); out = []
    for ch in text:
        fb = cm is not None and ord(ch) not in cm and not ch.isspace()
        if out and out[-1][1] == fb: out[-1][0] += ch
        else: out.append([ch, fb])
    return out
from PIL import ImageDraw as _ID
_orig_text = _ID.ImageDraw.text
def _text(self, xy, text, fill=None, font=None, anchor=None, *a, **k):
    fb = getattr(font, "_fallback", None)
    if fb is None or not isinstance(text, str) or "\n" in text or all(not r[1] for r in _runs(text, font)):
        return _orig_text(self, xy, text, fill, font, anchor, *a, **k)
    runs = _runs(text, font); fs = [(r[0], fb if r[1] else font) for r in runs]
    tot = sum(f.getlength(t) for t, f in fs); anchor = anchor or "la"
    x = xy[0] - {"l": 0, "m": tot / 2, "r": tot}.get(anchor[0], 0)
    for t, f in fs:
        _orig_text(self, (x, xy[1]), t, fill, f, "l" + anchor[1], *a, **k); x += f.getlength(t)
_ID.ImageDraw.text = _text
