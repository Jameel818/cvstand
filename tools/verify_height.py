import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.rendering import document_html

SAMPLE = json.loads((ROOT / "data" / "sample_resume.json").read_text(encoding="utf-8"))
keys = sys.argv[1:] or ["ats-t5"]

with sync_playwright() as p:
    b = p.chromium.launch()
    for key in keys:
        page = b.new_page(viewport={"width": 900, "height": 1200})
        # for_pdf=True embeds the fonts. set_content()'s base URL is about:blank,
        # so the linked stylesheet would not resolve and every height here would
        # be measured in a fallback face — silently wrong, no error.
        page.set_content(document_html(SAMPLE, key, for_pdf=True),
                         wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        # Every document now carries the auto-fit engine and self-fits after
        # fonts.ready. Await it, or this races the fit and measures a layout
        # that is halfway compressed. `af.natural` is the pre-fit height, which
        # is the number a port should be judged on — auto-fit is a safety net
        # for variable user content, not a licence to ship an overflowing port.
        af = page.evaluate("window.ResumeAutofit ? window.ResumeAutofit.ready : null")
        m = page.evaluate("""() => {
            const t = document.querySelector('.tpl');
            const r = t.getBoundingClientRect();
            return {sh: t.scrollHeight, w: Math.round(r.width), h: Math.round(r.height)};
        }""")
        from app.rendering import canvas_html
        frag = canvas_html(SAMPLE, key)
        html = page.content()
        natural = af["natural"] if af else m["sh"]
        checks = {
            "natural height<=1102 (port fits unaided)": natural <= 1102,
            "scrollHeight<=1102": m["sh"] <= 1102,
            "width==850": m["w"] == 850,
            "no ::before/::after in fragment": "::before" not in frag and "::after" not in frag,
            "skill name text": "Brand Systems" in html,
            "skill level text": "Expert" in html,
        }
        af_note = (f" | autofit natural={af['natural']} fitted={af['height']} "
                   f"density={af['density']}") if af else " | autofit MISSING"
        print(f"\n{key}: scrollHeight={m['sh']} width={m['w']} height={m['h']}{af_note}")
        for k, v in checks.items():
            print(f"  {'OK ' if v else 'FAIL'} {k}")
        page.screenshot(path=str(Path(__file__).parent / f"{key}.png"), full_page=True)
    b.close()
