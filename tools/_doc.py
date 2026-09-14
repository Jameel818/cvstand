import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.rendering import document_html
S = json.loads((ROOT/"data"/"sample_resume.json").read_text(encoding="utf-8"))
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":900,"height":1200})
    for key in sys.argv[1:]:
        pg.set_content(document_html(S, key, for_pdf=True), wait_until="networkidle")
        pg.evaluate("window.ResumeAutofit.ready")
        pg.emulate_media(media="print")
        print(key, pg.evaluate("""() => {
            const t = document.querySelector('.tpl'), cs = getComputedStyle(t);
            const r = t.getBoundingClientRect();
            const deepest = [...t.querySelectorAll('*')]
                .map(e => ({b: e.getBoundingClientRect().bottom - r.top,
                            c: (e.className||'').toString().slice(0,24), t: e.tagName}))
                .sort((a,z) => z.b - a.b).slice(0,3);
            return {docSH: document.documentElement.scrollHeight,
                    bodySH: document.body.scrollHeight,
                    tplRect: [Math.round(r.top), Math.round(r.height)],
                    tplSH: t.scrollHeight, ovY: cs.overflowY,
                    mb: cs.marginBottom, bb: cs.borderBottomWidth,
                    deepest: deepest.map(d => [d.b.toFixed(3), d.t, d.c]),
                    tplH: r.height.toFixed(4), bodyH: document.body.getBoundingClientRect().height.toFixed(4)};
        }"""))
    b.close()
