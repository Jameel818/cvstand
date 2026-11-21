"""Is every piece of a PDF's content on its page?  (feature/defects, 2026-11-20)

Reads the REAL exported PDF - not the browser layout, because the defect this
guards against happens in Chromium's print step, after layout: an RTL document
printed with scale < 1 came out shifted left by 850 x (1 - scale) px and cut off
(app/exporters/pdf.py RTL_PRINT_ROOT). No layout measurement can see that.

Two checks per page, with pypdf only (no rasteriser, so it runs anywhere):

1. CANVAS - every filled rectangle at least 90% of the page wide is a page-wide
   background (html/body, the template canvas `.tpl`, a full-bleed band). Each
   must start at x = 0 and end at the page width, +-TOL. A shifted canvas is a
   page-wide rectangle that starts at x < 0.
2. TEXT - every text-showing operation's origin (Tm x CTM) lies inside the
   media box, +-TOL. Text cut off at an edge has its origin past that edge.

    python tools/pdf_bounds.py file.pdf [...]      # prints problems, exit 1 if any
    python tools/pdf_bounds.py --sweep [--cv demo|sample] [--json out.json] [keys...]
        # prints the CV AND the cover letter of every template (or `keys`), in
        # English and Arabic, on Letter and A4, through the exporter's own
        # print path (app/exporters/pdf._print, one Chromium per language x
        # paper), and checks each page. Exit 1 if any page has a problem.
        # tests/e2e/test_pdf_bounds.py runs this in a SUBPROCESS: the test
        # process may enter sync_playwright() only once (tests/conftest.py).
"""
from __future__ import annotations

import io
import sys

from pypdf import PdfReader
from pypdf.generic import ContentStream

TOL = 0.5          # pt
BLEED = 0.75       # pt: one CSS px at the A4 factor (see the canvas check)


def _mul(a, b):
    """3x3 affine product of two PDF matrices [a b c d e f]: a then b."""
    return [a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3],
            a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
            a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5]]


def _pt(m, x, y):
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


_ID = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]


def _walk(stream_owner, resources, ctm, reader, rects, texts, depth=0):
    """Collect filled rects (device-space boxes) and text origins."""
    if depth > 8:
        return
    if hasattr(stream_owner, "get_contents"):          # a page
        content = stream_owner.get_contents()
        if content is None:
            return
    else:                                              # a form XObject
        content = ContentStream(stream_owner, reader)
    if resources is not None and hasattr(resources, "get_object"):
        resources = resources.get_object()
    stack: list[list[float]] = []
    cm = list(ctm)
    pending: list[tuple] = []          # rects of the current path
    tm = list(_ID); tlm = list(_ID); leading = 0.0
    xobjs = (resources or {}).get("/XObject") if resources else None
    for operands, op in content.operations:
        if op == b"q":
            stack.append(list(cm))
        elif op == b"Q":
            cm = stack.pop() if stack else list(ctm)
        elif op == b"cm":
            cm = _mul([float(v) for v in operands], cm)
        elif op == b"re":
            x, y, w, h = (float(v) for v in operands)
            pts = [_pt(cm, x, y), _pt(cm, x + w, y), _pt(cm, x, y + h), _pt(cm, x + w, y + h)]
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            pending.append((min(xs), min(ys), max(xs), max(ys)))
        elif op in (b"f", b"F", b"f*", b"B", b"B*", b"b", b"b*"):
            rects.extend(pending); pending = []
        elif op in (b"n", b"S", b"s", b"W", b"W*"):
            if op != b"W" and op != b"W*":
                pending = []
        elif op == b"BT":
            tm = list(_ID); tlm = list(_ID)
        elif op == b"Tm":
            tm = [float(v) for v in operands]; tlm = list(tm)
        elif op in (b"Td", b"TD"):
            tx, ty = float(operands[0]), float(operands[1])
            if op == b"TD":
                leading = -ty
            tlm = _mul([1, 0, 0, 1, tx, ty], tlm); tm = list(tlm)
        elif op == b"TL":
            leading = float(operands[0])
        elif op == b"T*":
            tlm = _mul([1, 0, 0, 1, 0, -leading], tlm); tm = list(tlm)
        elif op in (b"Tj", b"TJ", b"'", b'"'):
            if op in (b"'", b'"'):
                tlm = _mul([1, 0, 0, 1, 0, -leading], tlm); tm = list(tlm)
            texts.append(_pt(_mul(tm, cm), 0, 0))
        elif op == b"Do" and xobjs is not None:
            xo = xobjs.get(operands[0])
            xo = xo.get_object() if xo is not None else None
            if xo is not None and xo.get("/Subtype") == "/Form":
                m = [float(v) for v in xo.get("/Matrix", _ID)]
                _walk(xo, xo.get("/Resources") or resources, _mul(m, cm), reader,
                      rects, texts, depth + 1)


def problems(pdf: bytes, label: str = "") -> list[str]:
    """Every off-page canvas or text origin in this PDF, as readable lines."""
    reader = PdfReader(io.BytesIO(pdf))
    out = []
    for n, page in enumerate(reader.pages, 1):
        box = page.mediabox
        x0, y0, x1, y1 = (float(box.left), float(box.bottom), float(box.right), float(box.top))
        w = x1 - x0
        rects: list[tuple] = []; texts: list[tuple] = []
        _walk(page, page.get("/Resources"), _ID, reader, rects, texts)
        where = f"{label} p{n}".strip()
        for (rx0, ry0, rx1, ry1) in rects:
            if rx1 - rx0 < 0.9 * w:
                continue
            # A fill that starts exactly at the page edge may run up to one
            # layout px past the right edge: that is the ROOT background, which
            # Chromium paints over its whole layout width (851px on A4, 850 on
            # Letter) and the media box clips. A canvas 1px+ too wide, or one
            # that starts anywhere but x = 0, is still reported.
            if abs(rx0 - x0) > TOL or rx1 < x1 - TOL or rx1 > x1 + BLEED:
                out.append(f"{where}: page-wide fill at x {rx0:.2f}..{rx1:.2f}, page {x0:.2f}..{x1:.2f}")
        for (tx, ty) in texts:
            if not (x0 - TOL <= tx <= x1 + TOL and y0 - TOL <= ty <= y1 + TOL):
                out.append(f"{where}: text origin ({tx:.2f}, {ty:.2f}) outside "
                           f"{x0:.2f},{y0:.2f}..{x1:.2f},{y1:.2f}")
    return out


def counts(pdf: bytes) -> tuple[int, int]:
    """(page-wide fills, text runs) found - so a caller can prove the walk saw content."""
    reader = PdfReader(io.BytesIO(pdf))
    nr = nt = 0
    for page in reader.pages:
        w = float(page.mediabox.right) - float(page.mediabox.left)
        rects: list[tuple] = []; texts: list[tuple] = []
        _walk(page, page.get("/Resources"), _ID, reader, rects, texts)
        nr += sum(1 for r in rects if r[2] - r[0] >= 0.9 * w)
        nt += len(texts)
    return nr, nt


def _cv(cv: str, lang: str) -> dict:
    import copy
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    sfx = "_ar" if lang == "ar" else ""
    d = json.loads((root / "data" / f"{cv}_resume{sfx}.json").read_text(encoding="utf-8"))
    letter = json.loads((root / "data" / f"demo_letter{sfx}.json").read_text(encoding="utf-8"))
    letter["date"] = "18 October 2026" if lang == "en" else "١٨ أكتوبر ٢٠٢٦"
    d["cover_letter"] = copy.deepcopy(letter)
    return d


def sweep(keys: list[str] | None = None, cv: str = "demo") -> list[dict]:
    """One row per printed document: key, lang, paper, part, problems, counts."""
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app import letter as letter_mod
    from app import registry
    from app.exporters.pdf import _print, chosen_faces
    from app.paper import paper_of
    from app.rendering import document_html

    keys = keys or sorted(registry.ported_keys())
    rows = []
    for lang in ("en", "ar"):
        for paper in ("letter", "a4"):
            d = _cv(cv, lang)
            d["paper"] = paper
            docs, labels = [], []
            for key in keys:
                docs.append((document_html(d, key, for_pdf=True), True))
                docs.append((lambda fit, k=key: letter_mod.document_html(
                    d, k, for_pdf=True, header_fit=fit), True))
                labels += [(key, "cv"), (key, "letter")]
            pdfs = _print(docs, chosen_faces(d), paper_of(d))
            for (key, part), pdf in zip(labels, pdfs):
                rows.append({"key": key, "lang": lang, "paper": paper, "part": part, "cv": cv,
                             "problems": problems(pdf, f"{key} {lang} {paper} {part}"),
                             "counts": counts(pdf)})
    return rows


if __name__ == "__main__":
    if sys.argv[1:2] == ["--sweep"]:
        import json
        args = sys.argv[2:]
        cv, out = "demo", None
        if "--cv" in args:
            i = args.index("--cv"); cv = args[i + 1]; del args[i:i + 2]
        if "--json" in args:
            i = args.index("--json"); out = args[i + 1]; del args[i:i + 2]
        rows = sweep(args or None, cv)
        if out:
            open(out, "w", encoding="utf-8").write(json.dumps(rows, ensure_ascii=False, indent=1))
        bad = [r for r in rows if r["problems"]]
        for r in bad:
            print(r["key"], r["lang"], r["paper"], r["part"], len(r["problems"]), r["problems"][0])
        print(f"{len(rows)} documents, {len(bad)} with content off the page")
        sys.exit(1 if bad else 0)
    bad = 0
    for f in sys.argv[1:]:
        data = open(f, "rb").read()
        ps = problems(data, f)
        print(f, "fills/texts", counts(data), "OK" if not ps else f"{len(ps)} problem(s)")
        for p in ps[:12]:
            print("  ", p)
        bad += bool(ps)
    sys.exit(1 if bad else 0)
