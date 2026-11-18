"""B-roll Matchmaker step 2: sort clips into topic folders (copies, never moves).
Claude writes sort.json after looking at the contact sheets from broll_look.py:
{"library": "<B-roll folder>",
 "clips": [{"src": "<path>", "folder": "Motherhood", "about": "swinging with my son at the park",
            "best": [1.0, 3.0], "skip": false}]}
- best: [start, length] of the nicest steady moment (photos: omit)
- skip: true for clips that already have text/captions burned in or are unusable (kept in "Already edited")
Copies each clip into <library>/<folder>/ (keeps the original name; never overwrites a different file)
and updates <library>/library.json, the index the reel maker and future sorts read.
usage: python3 broll_sort.py sort.json"""
import json, os, shutil, sys, hashlib

plan = json.load(open(sys.argv[1]))
lib = os.path.abspath(os.path.expanduser(plan["library"])); os.makedirs(lib, exist_ok=True)
idx_path = os.path.join(lib, "library.json")
index = json.load(open(idx_path)) if os.path.exists(idx_path) else {"clips": []}

def digest(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()

known = {c["md5"]: c for c in index["clips"]}
added = 0
for c in plan["clips"]:
    md5 = digest(c["src"])
    if md5 in known:
        print("already sorted:", os.path.basename(c["src"]), "->", known[md5]["folder"]); continue
    folder = "Already edited" if c.get("skip") else c["folder"]
    dst_dir = os.path.join(lib, folder); os.makedirs(dst_dir, exist_ok=True)
    name = os.path.basename(c["src"]); dst = os.path.join(dst_dir, name); n = 1
    while os.path.exists(dst):
        if digest(dst) == md5: break
        stem, ext = os.path.splitext(name); dst = os.path.join(dst_dir, f"{stem}-{n}{ext}"); n += 1
    if not os.path.exists(dst): shutil.copy2(c["src"], dst)
    entry = {"file": os.path.relpath(dst, lib), "folder": folder, "about": c.get("about", ""),
             "best": c.get("best"), "skip": bool(c.get("skip")), "md5": md5,
             "photo": name.lower().endswith((".jpg", ".jpeg", ".png", ".heic", ".webp"))}
    index["clips"].append(entry); known[md5] = entry; added += 1
json.dump(index, open(idx_path, "w"), indent=1)
counts = {}
for c in index["clips"]: counts[c["folder"]] = counts.get(c["folder"], 0) + 1
print(f"added {added}; library now:", ", ".join(f"{k} ({v})" for k, v in sorted(counts.items())))
