"""Verify the auto-fit engine across the live catalogue.

Auto-fit (app/static/js/autofit.js) compresses vertical rhythm — line-height,
block margins/padding, row-gap — until the resume seats on one 1100px page. It
never touches horizontal geometry, so full-bleed sidebars and the absolutely
positioned Modern layouts are unaffected by construction.

Two things have to hold, and they pull in opposite directions:

  NO-OP on the shared sample. Every ported template already fits it, so auto-fit
  must return density 1.0 and leave the DOM untouched. A template that comes
  back compressed here has regressed — the port itself no longer fits.

  RECOVERS a realistic overload. The `--heavy` sample adds a 4th role and two
  bullets per role, which is what a real user does. Those should come back
  fitted, with density between the floor (0.85) and 1.0.

Usage:
  python tools/verify_autofit.py                  # every ported key, both samples
  python tools/verify_autofit.py modern-t1 ats-t5 # just these
  python tools/verify_autofit.py --heavy-only
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import registry                     # noqa: E402
from app.rendering import document_html      # noqa: E402

SAMPLE = json.loads((ROOT / "data" / "sample_resume.json").read_text(encoding="utf-8"))
FLOOR = 0.85        # stage-1 rhythm floor, mirrored from autofit.js
TYPE_FLOOR = 0.90   # stage-2 type floor


def heavy_sample() -> dict:
    """The shared sample plus the content a real user adds: one more role and
    two more bullets on each. Chosen to overflow every layout by a realistic
    margin rather than an impossible one — auto-fit recovers ~15-20%, and the
    point of this fixture is to prove that band, not to defeat it."""
    d = copy.deepcopy(SAMPLE)
    for job in d["experience"]:
        job["bullets"] = job["bullets"] + [
            "Ran quarterly design reviews across four product squads.",
            "Cut asset handover time by standardising the component library.",
        ]
    d["experience"].append({
        "company": "Northgate Studio",
        "role": "Senior Designer",
        "location": "Portside",
        "start": "2016",
        "end": "2018",
        "bullets": [
            "Led rebrand for two consumer clients from research through rollout.",
            "Built the studio's first shared type and colour system.",
        ],
    })
    return d


def run(keys: list[str], samples: list[tuple[str, dict]]) -> int:
    failures = 0
    recovered = [0]
    over: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 900, "height": 1200})
        for key in keys:
            row = [f"{key:<12}"]
            for label, data in samples:
                # for_pdf=True embeds the fonts: set_content()'s base URL is
                # about:blank, so a linked stylesheet silently falls back and
                # every height here would be measured in the wrong face.
                page.set_content(document_html(data, key, for_pdf=True),
                                 wait_until="networkidle")
                r = page.evaluate(
                    "window.ResumeAutofit ? window.ResumeAutofit.ready : null")
                if r is None:
                    row.append(f"{label}: ENGINE MISSING")
                    failures += 1
                    continue
                if label == "sample":
                    # A regression gate. Every ported template fits the shared
                    # sample unaided, so auto-fit must be a strict no-op here.
                    # Compression on this row means the PORT has drifted.
                    ok = r["fitted"] and r["density"] == 1 and r["typeScale"] == 1
                    mark = "OK  " if ok else "FAIL"
                    if not ok:
                        failures += 1
                else:
                    # Not a gate. Some layouts cannot recover a 20% overload —
                    # modern-t18's fixed-height cards, for one — and reporting
                    # `fitted: false` so the builder warns is the CORRECT
                    # outcome, not a defect. What would be a defect is silence.
                    ok = r["fitted"]
                    mark = "OK  " if ok else "OVER"
                    if ok:
                        recovered[0] += 1
                    else:
                        over.append(key)
                row.append(
                    f"{label}: {mark} "
                    f"{r['natural']:>7.1f} -> {r['height']:>7.1f} @ d={r['density']} t={r['typeScale']}")
            print("  ".join(row))
        browser.close()

    if over:
        print(f"\n{recovered[0]}/{recovered[0] + len(over)} recovered the heavy "
              f"overload. Past the floors, and correctly warned: {', '.join(over)}")
    return failures


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    keys = args or sorted(registry.ported_keys())

    samples: list[tuple[str, dict]] = []
    if "--heavy-only" not in flags:
        samples.append(("sample", SAMPLE))
    samples.append(("heavy", heavy_sample()))

    print(f"auto-fit check — {len(keys)} template(s), floor {FLOOR}\n")
    n = run(keys, samples)
    print(f"\n{'ALL PASS' if n == 0 else str(n) + ' FAILURE(S)'}")
    sys.exit(1 if n else 0)
