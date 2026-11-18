"""Hide captions while a big on-screen effect (article card, graph card) is showing, so they never overlap."""
import json, os
def _sec(ts):
    h, m, s = ts.split(":"); return int(h) * 3600 + int(m) * 60 + float(s)
def quiet(events, work):
    p = os.path.join(work, "fx_quiet.json")
    if not os.path.exists(p): return events
    wins = json.load(open(p)); out = []
    for e in events:
        parts = e.split(",", 9)
        style = parts[3].strip() if len(parts) > 3 else ""
        if style in ("Cap", "Lab", "Big") and any(a - 0.05 <= _sec(parts[1]) < b for a, b in wins): continue
        out.append(e)
    return out
