import json, sys, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import registry
from app.exporters.pdf import render_pdf
sys.path.insert(0, str(ROOT/"tools"))
from verify_autofit import heavy_sample
S = heavy_sample()
bad = []
for key in sorted(registry.ported_keys()):
    pdf = render_pdf(S, key)
    m = re.search(rb"/Type\s*/Pages[^>]*?/Count\s+(\d+)", pdf) or         re.search(rb"/Count\s+(\d+)[^>]*?/Type\s*/Pages", pdf)
    n = int(m.group(1)) if m else -1
    if n != 1:
        bad.append((key, n)); print(f"  {key}: {n} PAGES")
print(f"\n{len(bad)} of 49 export more than one page on the shared sample")
print(", ".join(f"{k}({n})" for k, n in bad) or "none")
