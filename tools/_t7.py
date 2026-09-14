import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.rendering import document_html
from app.exporters.pdf import render_pdf
S = json.loads((ROOT/"data"/"sample_resume.json").read_text(encoding="utf-8"))
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":900,"height":1200})
    pg.set_content(document_html(S, "ats-t7", for_pdf=True), wait_until="networkidle")
    pg.evaluate("window.ResumeAutofit.ready")
    print(pg.evaluate("""() => {
        const t = document.querySelector('.tpl');
        const cs = getComputedStyle(t);
        const top = t.getBoundingClientRect().top;
        const out = [];
        t.querySelectorAll('*').forEach(el => {
            const r = el.getBoundingClientRect();
            if (r.bottom - top > 1100.5)
                out.push({tag: el.tagName, cls: (el.className||'').toString().slice(0,30),
                          bottom: Math.round(r.bottom-top), h: Math.round(r.height),
                          txt: (el.textContent||'').trim().slice(0,25)});
        });
        return {overflow: cs.overflow, tplH: cs.height, sh: t.scrollHeight, culprits: out.slice(0,6)};
    }"""))
    b.close()
pdf = render_pdf(S, "ats-t7")
print("pdf pages ~", pdf.count(b"/Type /Page\n") or pdf.count(b"/Type/Page"))
