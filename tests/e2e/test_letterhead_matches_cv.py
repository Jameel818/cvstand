"""The cover letter's letterhead IS the CV's header (user, 2026-10-20): for
every template, English and Arabic, the letter page's name (size, weight,
face), its top, the headline's and the contact line's tops and the height of
the band the name stands on equal the CV's within 1pt.

The letter is built exactly as the PDF export builds it (exporters/pdf.py):
the CV is laid out first and its auto-fit passed to the letter, whose
letterhead takes it (static/js/autofit.js pinned()) - an Arabic CV that
tightened its gaps to fit its page drew its header a few px higher than an
unfitted letter would. The Word side is tests/test_letterhead_word.py.
"""
from __future__ import annotations

import pytest

from app import letter, registry
from app.rendering import document_html
from tests import letter_samples as LS

pytestmark = pytest.mark.e2e

#: 1pt on the page: the 850px canvas prints on 612pt, so 1pt = 850/612 px
PT = 850 / 612

_MEASURE = r"""([title, email, isCv]) => {
  const tpl = document.querySelector('.tpl');
  const T = tpl.getBoundingClientRect();
  const name = [...tpl.querySelectorAll('.cv-name')].find((e) => !e.closest('.cl-body'));
  // the header ends where the CV's first section begins: a headline the
  // template does not print must not be confused with a job title below
  const firstSec = [...tpl.querySelectorAll('.cv-section')].map((e) => e.getBoundingClientRect().top - T.top);
  // (the CV only: a letter keeps no sections but a side column's Contact)
  const limit = isCv && firstSec.length ? Math.min(...firstSec) : 1e9;
  const at = (txt) => {
    if (!txt) return null;
    const w = document.createTreeWalker(tpl, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = w.nextNode())) {
      if (n.parentElement.closest('.cl-body')) continue;
      if (getComputedStyle(n.parentElement).visibility === 'hidden') continue;
      const v = n.nodeValue.replace(/[⁦-⁩]/g, '').trim();
      // the headline is its own text (an Arabic summary can START with the
      // same words); the e-mail may share its line with a label
      if (txt === title ? v === txt : v.includes(txt)) {
        const r = document.createRange(); r.selectNodeContents(n);
        const b = r.getBoundingClientRect();
        if (b.height && (b.top - T.top) < limit) return b.top - T.top;
      }
    }
    return null;
  };
  let band = null;
  for (let e = name; e && e !== tpl; e = e.parentElement) {
    const bg = getComputedStyle(e).backgroundColor;
    if (bg && !/rgba\(0, 0, 0, 0\)|transparent/.test(bg)) {
      const b = e.getBoundingClientRect();
      band = {top: b.top - T.top, height: b.height};
      break;
    }
  }
  const c = getComputedStyle(name);
  return {size: parseFloat(c.fontSize), weight: c.fontWeight, face: c.fontFamily,
          top: name.getBoundingClientRect().top - T.top, title: at(title), email: at(email), band};
}"""


@pytest.fixture(scope="module")
def page(browser):
    pg = browser.new_page(viewport={"width": 850, "height": 1100})
    yield pg
    pg.close()


def _measure(page, html, probe):
    page.set_content(html, wait_until="networkidle")
    fit = page.evaluate("window.ResumeAutofit.ready")
    return page.evaluate(_MEASURE, probe), (fit["density"], fit["typeScale"])


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("key", registry.ported_keys())
def test_the_letterhead_is_the_cvs_header(page, key, lang):
    data = LS.with_letter(lang)
    c = data["contact"]
    probe = [data.get("title") or "", c.get("email") or ""]
    cv, fit = _measure(page, document_html(data, key, for_pdf=True), probe + [True])
    lt, _ = _measure(page, letter.document_html(data, key, for_pdf=True, header_fit=fit),
                     probe + [False])
    assert (lt["size"], lt["weight"], lt["face"]) == (cv["size"], cv["weight"], cv["face"])
    for k in ("top", "title", "email"):
        if cv[k] is not None:
            assert lt[k] is not None, f"{k} missing on the letter"
            assert abs(lt[k] - cv[k]) <= PT, f"{k}: CV {cv[k]:.2f}px, letter {lt[k]:.2f}px"
    if cv["band"]:
        assert lt["band"], "the band the name stands on is gone"
        assert abs(lt["band"]["top"] - cv["band"]["top"]) <= PT
        # the band keeps the CV's height even where it held CV content (the
        # stat chips of modern-t8/t13 are hidden in place, not removed)
        assert abs(lt["band"]["height"] - cv["band"]["height"]) <= PT, (
            f"band height: CV {cv['band']['height']:.2f}px, "
            f"letter {lt['band']['height']:.2f}px")


def test_the_pdf_export_passes_the_cvs_fit_to_the_letter():
    """Through the real exporter: in "CV + letter" the name sits at the same
    height on both pages (an Arabic CV that the fit tightened included)."""
    import io
    import unicodedata

    from pypdf import PdfReader

    from concurrent.futures import ThreadPoolExecutor

    from app.exporters.pdf import render_pdf
    for key in ("ats-t3", "ats-t17", "modern-t4"):
        data = LS.with_letter("ar")
        name = unicodedata.normalize("NFKC", data["name"]).split()[0]
        # render_pdf is Playwright's sync API: from a worker thread inside a
        # --e2e run (memory: cover-letter-and-import)
        with ThreadPoolExecutor(1) as ex:
            blob = ex.submit(render_pdf, data, key, "both").result()
        reader = PdfReader(io.BytesIO(blob))
        ys = []
        for pg in reader.pages[:2]:
            found = []

            def visit(t, cm, tm, fd, fs, found=found):
                if name in unicodedata.normalize("NFKC", t):
                    found.append(tm[5] * cm[3] + cm[5])
            pg.extract_text(visitor_text=visit)
            ys.append(max(found) if found else None)
        assert None not in ys and abs(ys[0] - ys[1]) <= 1.0, (key, ys)
