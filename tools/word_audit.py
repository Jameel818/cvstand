"""Audit every Word download against the PDF of the same CV, in REAL Word.
(feature/word-audit, 2026-11-24)

    python tools/word_audit.py all    WORKDIR [--keys k1,k2] [--src demo,sample,photo]
    python tools/word_audit.py gen    WORKDIR ...   # .docx (Word) + .pdf (Chromium)
    python tools/word_audit.py word   WORKDIR       # real Word -> <name>.word.pdf
    python tools/word_audit.py raster WORKDIR       # every PDF page -> PNG, 850px wide
    python tools/word_audit.py check  WORKDIR       # -> failures.csv / results.json
    python tools/word_audit.py sheets WORKDIR OUT   # contact sheets + index.html

The matrix: every template x EN/AR x Letter/A4 x cv/letter/both, for the demo
and sample CVs; plus "photo" (the demo with a solid magenta test photo) for the
templates with a photo slot. The reference for each Word page is the PDF page
of the same CV: cv -> the PDF CV, letter -> the PDF letter, both -> CV + letter.

Checks (every one compares Word with the PDF; images on the same 850px grid):
  pages     cv 1, letter 1, both 2 pages (Word's own count and its PDF's).
  fill      large colour areas (text removed by a median filter): a region where
            Word's fill differs from the PDF's - a sidebar / band / box that
            stops early, overruns, is missing or a different size.
            "foot" = the region touches the page's last 4%: the column does not
            reach (or overruns) the page bottom.
  lines     thin rules / dashes Word draws that the PDF does not (stray), and
            rules the PDF draws that Word does not (missing).
  text      every word of the PDF page is on the same Word page: missing =
            cut off, on another page = moved. Plus any text placed off the page
            (tools/pdf_bounds.problems).
  photo     (photo CVs) the photo's box and shape (fill ratio) in Word = PDF,
            and identical in the CV and the cover letter.
  letter    where the PDF letter and PDF CV look the same (the letterhead, the
            side column, the bands, the photo frame), the Word letter and the
            Word CV must look the same too; the name stands at the same place
            and size.

Word is driven only through tools/word_com.ps1 (own process only, never the
user's Word). Rasters by tools/pdf_raster.ps1 (Windows.Data.Pdf).
"""
from __future__ import annotations

import base64
import csv
import io
import json
import os
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
SEP = "~"
PARTS = ("cv", "letter", "both")
#: templates whose Word design draws a photo / photo placeholder
PHOTO_KEYS = tuple(f"modern-t{n}" for n in (2, 3, 4, 5, 7, 8, 10, 11, 14, 15, 16, 17, 18, 20, 21, 24))
PHOTO_RGB = (255, 0, 255)
W = 850


def name_of(src, key, lang, paper, part):
    return SEP.join((src, key, lang, paper, part))


def split_name(name):
    src, key, lang, paper, part = name.split(SEP)
    return dict(src=src, key=key, lang=lang, paper=paper, part=part)


# ---------------------------------------------------------------- generate

def _setup(work: Path):
    """Bind the app's data dir to WORKDIR/data (the test photo lives there,
    never in the user's data/uploads) - before the app is imported."""
    data = work / "data"
    (data / "uploads").mkdir(parents=True, exist_ok=True)
    os.environ["CVSTAND_DATA_DIR"] = str(data)
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    from PIL import Image
    p = data / "uploads" / "audit-photo.png"
    if not p.exists():
        Image.new("RGB", (600, 600), PHOTO_RGB).save(p)
    return p


def _cv(src: str, lang: str, photo: Path | None, for_pdf: bool) -> dict:
    from tests import letter_samples as LS
    if src == "sample":
        d = json.load(open(ROOT / "data" / ("sample_resume.json" if lang == "en"
                                            else "sample_resume_ar.json"), encoding="utf-8"))
    else:
        d = LS.with_letter(lang)
    d = dict(d)
    d.pop("paper", None)
    if src == "photo":
        if for_pdf:
            # the PDF is printed from set_content() with no base URL: an
            # /uploads/ path would not load, so the reference gets the SAME
            # image inline (the Word side reads it from the uploads dir)
            d["photo_url"] = "data:image/png;base64," + base64.b64encode(photo.read_bytes()).decode()
        else:
            d["photo_url"] = "/uploads/" + photo.name
    return d


def gen(work: Path, keys=None, srcs=("demo", "sample", "photo"), pdf=True, docx=True):
    photo = _setup(work)
    from app import registry
    from app import letter as letter_mod
    from app.exporters import docx_design, docx_dml
    from app.exporters.docx import render_docx
    from app.exporters.pdf import _print, chosen_faces
    from app.paper import paper_of
    from app.rendering import document_html
    all_keys = sorted(registry.ported_keys())
    keys = [k for k in all_keys if not keys or k in keys]
    (work / "docx").mkdir(exist_ok=True)
    (work / "pdf").mkdir(exist_ok=True)
    for src in srcs:
        ks = [k for k in keys if src != "photo" or k in PHOTO_KEYS]
        if not ks:
            continue
        for lang in ("en", "ar"):
            for paper in ("letter", "a4"):
                if docx:
                    d = _cv(src, lang, photo, False)
                    if paper == "a4":
                        d["paper"] = "a4"
                    for k in ks:
                        for part in PARTS:
                            out = work / "docx" / (name_of(src, k, lang, paper, part) + ".docx")
                            docx_dml._ID[0] = 0
                            docx_design._SHAPE_N[0] = 0
                            out.write_bytes(render_docx(d, k, part))
                if pdf:
                    d = _cv(src, lang, photo, True)
                    if paper == "a4":
                        d["paper"] = "a4"
                    docs, labels = [], []
                    for k in ks:
                        docs.append((document_html(d, k, for_pdf=True), True))
                        docs.append((lambda fit, k=k, d=d: letter_mod.document_html(
                            d, k, for_pdf=True, header_fit=fit), True))
                        labels += [(k, "cv"), (k, "letter")]
                    for (k, part), blob in zip(labels, _print(docs, chosen_faces(d), paper_of(d))):
                        (work / "pdf" / (name_of(src, k, lang, paper, part) + ".pdf")).write_bytes(blob)
                print("gen", src, lang, paper, len(ks), flush=True)


# ---------------------------------------------------------------- real Word

def word(work: Path, batch: int = 120, timeout_s: int = 1500):
    """Every .docx without a .word.pdf -> real Word, in batches (a fresh Word
    per batch, inside Start-Job; a batch that hangs is stopped by OUR pid)."""
    out = work / "word"
    out.mkdir(exist_ok=True)
    csv_path = work / "word_pages.csv"
    todo = sorted(p for p in (work / "docx").glob("*.docx")
                  if not (out / (p.stem + ".word.pdf")).exists())
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        lst = work / "word_batch.txt"
        lst.write_text("\n".join(str(p) for p in chunk), encoding="utf-8")
        ps = (f"$j = Start-Job -FilePath '{TOOLS / 'word_com.ps1'}' -ArgumentList "
              f"'{lst.resolve()}','{out.resolve()}','{csv_path.resolve()}'; "
              f"if (-not (Wait-Job $j -Timeout {timeout_s})) {{ "
              f"  foreach ($id in ((Get-Content '{csv_path}.pid') -split ';')) {{ "
              f"    if ($id) {{ Stop-Process -Id ([int]$id) -Force -ErrorAction SilentlyContinue }} }}; "
              f"  'TIMEOUT' }}; Remove-Job $j -Force")
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
        done = sum(1 for p in chunk if (out / (p.stem + ".word.pdf")).exists())
        print(f"word batch {i // batch + 1}: {done}/{len(chunk)} {r.stdout.strip()[:80]}", flush=True)


def word_pages(work: Path) -> dict:
    pages = {}
    p = work / "word_pages.csv"
    if p.exists():
        for row in csv.reader(open(p, encoding="utf-8-sig")):
            if len(row) >= 2 and row[0] != "REFUSED":
                pages[row[0]] = row[1]
    return pages


# ---------------------------------------------------------------- rasters

def raster(work: Path):
    png = work / "png"
    png.mkdir(exist_ok=True)
    todo = [p for p in sorted((work / "pdf").glob("*.pdf")) + sorted((work / "word").glob("*.word.pdf"))
            if not (png / (p.name[:-4] + "-p1.png")).exists()]
    for i in range(0, len(todo), 300):
        lst = work / "raster_batch.txt"
        lst.write_text("\n".join(str(p) for p in todo[i:i + 300]), encoding="utf-8")
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                        "-File", str(TOOLS / "pdf_raster.ps1"), str(lst), str(png), str(W)],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
        print("raster", min(i + 300, len(todo)), "/", len(todo), flush=True)


# ---------------------------------------------------------------- image checks

def _img(path: Path):
    from PIL import Image
    return Image.open(path).convert("RGB")


def fill_map(img):
    """Large colour areas only: half size, then a median filter that removes
    text strokes (dark on light and light on dark alike)."""
    from PIL import Image, ImageFilter
    w, h = img.size
    return img.resize((w // 2, h // 2), Image.BILINEAR).filter(ImageFilter.MedianFilter(7))


def _mismatch_blocks(a, b, thr=36, block=8, frac=0.5):
    """Block grid (list of rows of bool) where a and b differ in colour on at
    least `frac` of the block's pixels."""
    from PIL import Image, ImageChops
    if a.size != b.size:
        b = b.resize(a.size, Image.BILINEAR)
    d = ImageChops.difference(a, b)
    r, g, bl = d.split()
    m = ImageChops.lighter(ImageChops.lighter(r, g), bl).point(lambda v: 255 if v > thr else 0)
    gw, gh = max(1, a.size[0] // block), max(1, a.size[1] // block)
    small = m.resize((gw, gh), Image.BOX)
    px = small.load()
    return [[px[x, y] >= 255 * frac for x in range(gw)] for y in range(gh)]


def _regions(grid, min_blocks):
    gh, gw = len(grid), len(grid[0]) if grid else 0
    seen = [[False] * gw for _ in range(gh)]
    out = []
    for y in range(gh):
        for x in range(gw):
            if grid[y][x] and not seen[y][x]:
                stack, cells = [(x, y)], []
                seen[y][x] = True
                while stack:
                    cx, cy = stack.pop()
                    cells.append((cx, cy))
                    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                        if 0 <= nx < gw and 0 <= ny < gh and grid[ny][nx] and not seen[ny][nx]:
                            seen[ny][nx] = True
                            stack.append((nx, ny))
                if len(cells) >= min_blocks:
                    xs = [c[0] for c in cells]
                    ys = [c[1] for c in cells]
                    out.append((min(xs), min(ys), max(xs) + 1, max(ys) + 1, len(cells), gw, gh))
    return out


def _region_txt(reg):
    x0, y0, x1, y1, n, gw, gh = reg
    return f"x {100 * x0 / gw:.0f}-{100 * x1 / gw:.0f}% y {100 * y0 / gh:.0f}-{100 * y1 / gh:.0f}%"


def check_fill(word_img, pdf_img, min_blocks=6):
    """Generic colour-area diff (for the eye only: text reflows between Word
    and Chromium, so it is not a failure by itself)."""
    a, b = fill_map(word_img), fill_map(pdf_img)
    return [("fill", _region_txt(reg)) for reg in _regions(_mismatch_blocks(a, b), min_blocks)]


def column_ends(img, bucket=8, white=30, tall=0.30):
    """Per x-bucket (half a bucket apart, on the fill map): (top, bottom) in
    page px of the longest vertical run of colour - a side column, a band, a
    card - when that run is at least `tall` of the page; else None. Text is
    gone after the median filter, so a run is a filled area, and where it
    ends is what "the sidebar reaches the page foot" means."""
    f = fill_map(img).convert("RGB")
    w, h = f.size
    px = f.load()
    out = []
    step = max(1, bucket // 4)
    for x in range(step, w, step * 2):
        best, start = None, None
        for y in range(h + 1):
            on = y < h and max(255 - c for c in px[x, y]) > white
            if on and start is None:
                start = y
            elif not on and start is not None:
                if best is None or y - start > best[1] - best[0]:
                    best = (start, y)
                start = None
        out.append((2 * best[0], 2 * best[1]) if best and best[1] - best[0] >= tall * h else None)
    return out


def _runs(flags, min_len):
    out, s = [], None
    for i, f in enumerate(list(flags) + [False]):
        if f and s is None:
            s = i
        elif not f and s is not None:
            if i - s >= min_len:
                out.append((s, i))
            s = None
    return out


def check_columns(word_img, pdf_img, tol_px=14, min_buckets=6,
                  label=("fill-bottom", "fill-top"), other="PDF"):
    """Every tall column/band must start and end where the PDF's does."""
    we, pe = column_ends(word_img), column_ends(pdf_img)
    W, H = word_img.size
    n = min(len(we), len(pe))
    per = W / max(1, n)
    out = []
    for idx, name in ((1, label[0]), (0, label[1])):
        bad = []
        for i in range(n):
            a, b = we[i], pe[i]
            if a is None and b is None:
                bad.append(False)
            elif a is None or b is None:
                bad.append(True)
            else:
                bad.append(abs(a[idx] - b[idx]) > tol_px)
        for s0, e0 in _runs(bad, min_buckets):
            mid = (s0 + e0) // 2
            a, b = we[mid], pe[mid]
            wa = "none" if a is None else f"{100 * a[idx] / H:.1f}%"
            pb = "none" if b is None else f"{100 * b[idx] / H:.1f}%"
            verb = "ends" if idx else "starts"
            out.append((name, f"x {100 * s0 * per / W:.0f}-{100 * e0 * per / W:.0f}%: Word {verb} "
                              f"at {wa}, {other} at {pb}"))
    return out


def _line_mask(gray, step=4, t_hi=16, t_lo=10):
    from PIL import ImageChops
    up = ImageChops.offset(gray, 0, step)
    dn = ImageChops.offset(gray, 0, -step)
    d1 = ImageChops.difference(gray, up).point(lambda v: 255 if v > t_hi else 0)
    d2 = ImageChops.difference(gray, dn).point(lambda v: 255 if v > t_hi else 0)
    d3 = ImageChops.difference(up, dn).point(lambda v: 255 if v < t_lo else 0)
    return ImageChops.multiply(ImageChops.multiply(d1, d2), d3)


_SOLID = re.compile(rb"\xff{36,}")
_SHORT = re.compile(rb"\xff{2,16}")


def lines(img):
    """[(kind, orient, pos, a, b)]: thin solid rules >= 36px and dashed rows,
    horizontal (pos = y) and vertical (pos = x), merged across adjacent rows."""
    from PIL import Image
    g = img.convert("L")
    found = []
    for orient, im in (("h", g), ("v", g.transpose(Image.Transpose.TRANSPOSE))):
        m = _line_mask(im)
        w, h = m.size
        data = m.tobytes()
        raw = []
        for y in range(4, h - 4):
            row = data[y * w:(y + 1) * w]
            for mt in _SOLID.finditer(row):
                raw.append(("solid", y, mt.start(), mt.end()))
            short = [(mt.start(), mt.end()) for mt in _SHORT.finditer(row)]
            if len(short) >= 8:
                # a run of equal dashes at an even pitch (text strokes vary)
                for i in range(len(short) - 7):
                    win = short[i:i + 8]
                    lens = [e - s for s, e in win]
                    gaps = [win[j + 1][0] - win[j][1] for j in range(7)]
                    if (max(lens) - min(lens) <= 2 and max(gaps) - min(gaps) <= 2
                            and win[-1][1] - win[0][0] >= 70):
                        raw.append(("dash", y, win[0][0], win[-1][1]))
                        break
        raw.sort(key=lambda r: (r[0], r[2], r[1]))
        merged = []
        for kind, y, a, b in raw:
            for mm in merged:
                if mm[0] == kind and abs(mm[2] - y) <= 3 and a < mm[4] and b > mm[3]:
                    mm[2] = y
                    mm[3], mm[4] = min(mm[3], a), max(mm[4], b)
                    break
            else:
                merged.append([kind, orient, y, a, b])
        # a "dash" lying on a solid rule is the rule's antialiasing
        solid = [m for m in merged if m[0] == "solid"]
        merged = [m for m in merged if m[0] == "solid" or not any(
            abs(sm[2] - m[2]) <= 3 and sm[3] <= m[3] + 4 and sm[4] >= m[4] - 4 for sm in solid)]
        found += [tuple(m) for m in merged]
    return found


def check_lines(word_img, pdf_img, ywin=120, rel=0.8):
    """Thin rules and dashed rows: each one in Word needs a PDF one of the same
    kind, orientation and span (>= 80% overlap both ways) within +-ywin px
    across it (the text above it reflows a little); and the reverse for PDF
    rules of 60px or more."""
    wl, pl = lines(word_img), lines(pdf_img)

    def matched(l, others):
        kind, o, pos, a, b = l
        for k2, o2, p2, a2, b2 in others:
            if o2 != o or k2 != kind:
                continue
            if o == "h":
                # a rule: same x span, the text above it may move it down/up
                ov = min(b, b2) - max(a, a2)
                # (a leader starts after its heading, whose width differs)
                if abs(p2 - pos) <= ywin and ov >= 0.6 * min(b - a, b2 - a2):
                    return True
            else:
                # a rail/divider: same x, about the same length, its y span
                # moves with the text it runs beside
                ln, ln2 = b - a, b2 - a2
                if (abs(p2 - pos) <= 8 and abs(a2 - a) <= ywin
                        and abs(ln - ln2) <= max(24, 0.35 * max(ln, ln2))):
                    return True
        return False
    out = []
    for l in wl:
        kind, o, pos, a, b = l
        if not matched(l, pl):
            out.append(("line-stray" if kind == "solid" else "dash-stray",
                        f"{o} at {pos}px, {a}-{b}px"))
    for l in pl:
        kind, o, pos, a, b = l
        if kind == "solid" and b - a >= 60 and not matched(l, wl):
            out.append(("line-missing", f"{o} at {pos}px, {a}-{b}px"))
    return out


def photo_box(img):
    """(bbox, fill ratio) of the magenta test photo, or None."""
    r, g, b = img.split()
    m = r.point(lambda v: 255 if v > 200 else 0)
    from PIL import ImageChops
    m = ImageChops.multiply(m, g.point(lambda v: 255 if v < 70 else 0))
    m = ImageChops.multiply(m, b.point(lambda v: 255 if v > 200 else 0))
    box = m.getbbox()
    if not box:
        return None
    area = m.histogram()[255]
    bw, bh = box[2] - box[0], box[3] - box[1]
    if area < 200:
        return None
    return box, area / float(bw * bh)


def _photo_txt(p):
    if p is None:
        return "none"
    (x0, y0, x1, y1), ratio = p
    return f"{x1 - x0}x{y1 - y0} at ({x0},{y0}) fill {ratio:.2f}"


def _photo_same(p, q, tol=4, rtol=0.05):
    if p is None or q is None:
        return p is None and q is None
    return (all(abs(a - b) <= tol for a, b in zip(p[0], q[0])) and abs(p[1] - q[1]) <= rtol)


# ---------------------------------------------------------------- text checks

_DROP = dict.fromkeys(map(ord, "‎‏‪‫‬‭‮⁦⁧⁨⁩ـ"))
_SPLIT = re.compile(r"[\s·•|,;:()\[\]\"'“”‘’/\\—–\-+]+")


def _tokens(text: str) -> list[str]:
    t = unicodedata.normalize("NFKC", text).translate(_DROP)
    t = "".join(ch for ch in t if not ("ً" <= ch <= "ْ"))
    out = []
    for tok in _SPLIT.split(t):
        tok = tok.strip(".!?،؛")
        if sum(ch.isalnum() for ch in tok) < 2:
            continue
        # visual-order extraction may reverse Arabic: key by its letters
        out.append("".join(sorted(tok)) if any("؀" <= ch <= "ۿ" for ch in tok) else tok.lower())
    return out


def pdf_texts(path: Path) -> list:
    """Per page: (token counts, the page's text lower-cased with no spaces -
    letter-spaced headings extract as "S U M M A R Y")."""
    from pypdf import PdfReader
    try:
        out = []
        for p in PdfReader(str(path)).pages:
            t = p.extract_text() or ""
            flat = re.sub(r"\s+", "", unicodedata.normalize("NFKC", t).translate(_DROP)).lower()
            out.append((Counter(_tokens(t)), flat))
        return out
    except Exception:  # noqa: BLE001
        return []


#: the PDF's empty photo frame carries a label Word's placeholder does not
#: draw (no photo uploaded): never a missing word
PLACEHOLDER_WORDS = ("الصورة", "صورة", "portraitplaceholder", "photo")

_ARABIC_DIGITS = str.maketrans("\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669",
                                "0123456789")


def letters(page) -> Counter:
    """The page's letters and digits (Arabic folded: NFKC, no tatweel or
    diacritics, Arabic-Indic digits as ASCII)."""
    flat = page[1].translate(_ARABIC_DIGITS)
    for w in PLACEHOLDER_WORDS:
        flat = flat.replace(w, "")
    return Counter(ch for ch in flat if ch.isalnum() and not ("\u064b" <= ch <= "\u0652"))


def _absent(tok, page) -> bool:
    cnt, flat = page
    if tok in cnt or tok in ("photo", "portrait", "placeholder"):
        return False
    if any("\u0600" <= ch <= "\u06ff" for ch in tok):
        return True
    return tok not in flat


def name_box(path: Path, page: int = 0):
    """(x, y, size) in pt of the largest text in the page's top 40% (the name)."""
    from pypdf import PdfReader
    r = PdfReader(str(path))
    if page >= len(r.pages):
        return None
    pg = r.pages[page]
    H = float(pg.mediabox.height)
    best = [None]

    def visit(text, cm, tm, font, size):
        if not (text or "").strip():
            return
        a, b, c, d, e, f = [float(v) for v in tm]
        A, B, C, D, E, F = [float(v) for v in cm]
        X, Y = e * A + f * C + E, e * B + f * D + F          # text origin, page space
        s = abs(size * (d or 1.0) * (D or 1.0))               # rendered size
        if Y > H * 0.6 and (best[0] is None or s > best[0][2] + 0.01):
            best[0] = (X, H - Y, s)
    pg.extract_text(visitor_text=visit)
    return best[0]


# ---------------------------------------------------------------- the check

def _pages_of(work, stem):
    out, i = [], 1
    while (work / "png" / f"{stem}-p{i}.png").exists():
        out.append(work / "png" / f"{stem}-p{i}.png")
        i += 1
    return out


def check(work: Path, only=None):
    sys.path.insert(0, str(ROOT))
    from tools.pdf_bounds import problems as off_page
    wpages = word_pages(work)
    fails = []
    names = sorted(p.stem for p in (work / "docx").glob("*.docx"))
    if only:
        names = [n for n in names if split_name(n)["key"] in only]
    groups = {}
    for n in names:
        s = split_name(n)
        groups.setdefault((s["src"], s["key"], s["lang"], s["paper"]), {})[s["part"]] = n
    for (src, key, lang, paper), parts in sorted(groups.items()):
        base = dict(src=src, key=key, lang=lang, paper=paper)

        def fail(part, page, check, detail):
            fails.append({**base, "part": part, "page": page, "check": check, "detail": detail})
        ref = {pt: name_of(src, key, lang, paper, pt) for pt in ("cv", "letter")}
        ref_png = {pt: _pages_of(work, ref[pt]) for pt in ref}
        ref_txt = {pt: pdf_texts(work / "pdf" / (ref[pt] + ".pdf")) for pt in ref}
        for pt in ("cv", "letter"):
            if len(ref_png[pt]) != 1:
                fail(pt, 0, "pdf-pages", f"the PDF {pt} has {len(ref_png[pt])} pages")
        word_png = {}
        for part, n in parts.items():
            want = 2 if part == "both" else 1
            wp = wpages.get(n)
            pngs = _pages_of(work, n + ".word")
            word_png[part] = pngs
            if wp is None or wp == "ERR" or not pngs:
                fail(part, 0, "word", f"no Word output ({wp})")
                continue
            if int(wp) != want or len(pngs) != want:
                fail(part, 0, "pages", f"{wp} pages in Word, want {want}")
            wtxt = pdf_texts(work / "word" / (n + ".word.pdf"))
            probs = [str(x) for x in off_page((work / "word" / (n + ".word.pdf")).read_bytes(), n)
                     if "page-wide fill" not in str(x)]
            for prob in probs[:3]:
                fail(part, 0, "text-offpage", prob[:120])
            refs = ["cv", "letter"] if part == "both" else [part]
            for i, rp in enumerate(refs):
                if i >= len(pngs) or not ref_png[rp]:
                    continue
                wi, pi = _img(pngs[i]), _img(ref_png[rp][0])
                for c, d in check_columns(wi, pi):
                    fail(part, i + 1, c, d)
                for c, d in check_lines(wi, pi):
                    fail(part, i + 1, c, d)
                # text: every PDF word on the same Word page
                if ref_txt[rp] and i < len(wtxt) and lang == "ar":
                    # Arabic: letters missing from this Word page (cut off) or
                    # found on another Word page (moved), by count
                    want, got = letters(ref_txt[rp][0]), letters(wtxt[i])
                    short = sum((want - got).values())
                    if short > max(24, 0.025 * sum(want.values())):
                        other = Counter()
                        for j in range(len(wtxt)):
                            if j != i:
                                other += letters(wtxt[j])
                        moved = sum(((want - got) & other).values()) if part == "both" else 0
                        fail(part, i + 1, "text-moved" if moved > short / 2 else "text-missing",
                             f"{short} of {sum(want.values())} letters not on this Word page")
                elif ref_txt[rp] and i < len(wtxt):
                    missing = Counter({t: k for t, k in (ref_txt[rp][0][0] - wtxt[i][0]).items()
                                       if _absent(t, wtxt[i])})
                    if missing:
                        moved = [t for t in missing if any(not _absent(t, wtxt[j])
                                                           for j in range(len(wtxt)) if j != i)]
                        cut = [t for t in missing if t not in moved]
                        if moved:
                            fail(part, i + 1, "text-moved", f"{len(moved)} words on another page: {moved[:4]}")
                        if cut:
                            fail(part, i + 1, "text-missing", f"{sum(missing[t] for t in cut)} words: {cut[:4]}")
                if src == "photo":
                    pw, pp = photo_box(wi), photo_box(pi)
                    if not _photo_same(pw, pp):
                        fail(part, i + 1, "photo", f"Word {_photo_txt(pw)} vs PDF {_photo_txt(pp)}")
        # the letter against the CV, where the two PDFs agree
        cvw, lw = word_png.get("cv"), word_png.get("letter")
        if cvw and lw and ref_png["cv"] and ref_png["letter"]:
            fa = {k: fill_map(_img(p)) for k, p in (("wc", cvw[0]), ("wl", lw[0]),
                                                      ("pc", ref_png["cv"][0]), ("pl", ref_png["letter"][0]))}
            agree = _mismatch_blocks(fa["pc"], fa["pl"], frac=0.1)
            differ = _mismatch_blocks(fa["wc"], fa["wl"])
            # the letterhead band only (the top quarter): below it the body
            # differs by design, and Word's text reflows
            top = len(differ) // 4
            # ...and where the Word CV draws what its PDF does (text that
            # reflows - a highlight - moves both)
            cv_ok = _mismatch_blocks(fa["wc"], fa["pc"], frac=0.1)
            grid = [[differ[y][x] and not agree[y][x] and not cv_ok[y][x] and y < top
                     for x in range(len(differ[0]))] for y in range(len(differ))]
            for reg in _regions(grid, 6):
                fail("letter", 1, "letterhead-fill", "Word letter's head differs from the Word CV's "
                     "where the PDFs agree: " + _region_txt(reg))
            # the letter's columns run as the CV's do (where the PDFs agree)
            if not check_columns(_img(ref_png["letter"][0]), _img(ref_png["cv"][0])):
                for c, d in check_columns(_img(lw[0]), _img(cvw[0]), other="Word CV",
                                          label=("letter-col-bottom", "letter-col-top")):
                    fail("letter", 1, c, d)
            nc = name_box(work / "word" / (parts["cv"] + ".word.pdf"))
            nl = name_box(work / "word" / (parts["letter"] + ".word.pdf"))
            if nc and nl and (abs(nc[0] - nl[0]) > 3 or abs(nc[1] - nl[1]) > 3
                              or abs(nc[2] - nl[2]) > max(0.5, nc[2] * 0.03)):
                fail("letter", 1, "letterhead", f"name CV ({nc[0]:.0f},{nc[1]:.0f}) {nc[2]:.1f}pt vs "
                     f"letter ({nl[0]:.0f},{nl[1]:.0f}) {nl[2]:.1f}pt")
            if src == "photo":
                pc, pl_ = photo_box(_img(cvw[0])), photo_box(_img(lw[0]))
                if pc is not None and not _photo_same(pc, pl_, tol=2, rtol=0.02):
                    fail("letter", 1, "photo-letter", f"CV {_photo_txt(pc)} vs letter {_photo_txt(pl_)}")
        print("check", src, key, lang, paper, sum(1 for f in fails if f["key"] == key and f["src"] == src
                                                   and f["lang"] == lang and f["paper"] == paper),
              flush=True)
    out = work / "failures.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=["key", "src", "lang", "paper", "part", "page", "check", "detail"])
        wr.writeheader()
        wr.writerows(fails)
    (work / "results.json").write_text(json.dumps(fails, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(fails), "failures in", len(groups), "groups ->", out)
    return fails


# ---------------------------------------------------------------- contact sheets

def sheets(work: Path, out: Path, tw=170):
    from PIL import Image, ImageDraw
    out.mkdir(parents=True, exist_ok=True)
    fails = json.loads((work / "results.json").read_text(encoding="utf-8"))
    bad = {}
    for f in fails:
        bad.setdefault((f["src"], f["key"], f["lang"], f["paper"], f["part"], f["page"]), []).append(f)
    names = sorted(p.stem for p in (work / "docx").glob("*.docx"))
    keys = sorted({split_name(n)["key"] for n in names})
    cols = [("PDF CV", "pdf", "cv", 1), ("Word CV", "word", "cv", 1), ("Word both p1", "word", "both", 1),
            ("PDF letter", "pdf", "letter", 1), ("Word letter", "word", "letter", 1),
            ("Word both p2", "word", "both", 2)]
    for key in keys:
        rows = sorted({(s["src"], s["lang"], s["paper"]) for s in map(split_name, names) if s["key"] == key})
        th = int(tw * 1202 / 850)
        lab = 150
        sheet = Image.new("RGB", (lab + len(cols) * (tw + 8), 30 + len(rows) * (th + 8)), "white")
        dr = ImageDraw.Draw(sheet)
        for j, (title, *_r) in enumerate(cols):
            dr.text((lab + j * (tw + 8) + 4, 8), title, fill="black")
        for i, (src, lang, paper) in enumerate(rows):
            y = 30 + i * (th + 8)
            dr.text((6, y + 6), f"{src}\n{lang} {paper}", fill="black")
            for j, (title, kind, part, page) in enumerate(cols):
                n = name_of(src, key, lang, paper, part)
                stem = n if kind == "pdf" else n + ".word"
                p = work / "png" / f"{stem}-p{page}.png"
                x = lab + j * (tw + 8)
                if p.exists():
                    im = Image.open(p).convert("RGB")
                    im.thumbnail((tw, th))
                    sheet.paste(im, (x, y))
                    if kind == "word" and bad.get((src, key, lang, paper, part, page)) or (
                            kind == "word" and bad.get((src, key, lang, paper, part, 0))):
                        dr.rectangle([x - 3, y - 3, x + im.size[0] + 2, y + im.size[1] + 2], outline="red", width=3)
                else:
                    dr.rectangle([x, y, x + tw, y + 40], outline="grey")
                    dr.text((x + 4, y + 4), "missing", fill="grey")
        sheet.save(out / f"{key}.png")
    with open(out / "failures.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=["key", "src", "lang", "paper", "part", "page", "check", "detail"])
        wr.writeheader()
        wr.writerows(fails)
    import html as H
    by_key = Counter(f["key"] for f in fails)
    rows = "".join(f"<tr><td><a href='{H.escape(f['key'])}.png'>{H.escape(f['key'])}</a></td>"
                   + "".join(f"<td>{H.escape(str(f[c]))}</td>" for c in
                             ("src", "lang", "paper", "part", "page", "check", "detail")) + "</tr>"
                   for f in fails)
    summary = "".join(f"<li><a href='{k}.png'>{k}</a>: {by_key.get(k, 0)}</li>" for k in keys)
    (out / "index.html").write_text(
        "<!doctype html><meta charset=utf-8><title>Word audit</title>"
        "<style>body{font:14px system-ui;margin:16px}td{border-bottom:1px solid #ddd;padding:2px 6px}</style>"
        f"<h1>Word audit</h1><p>{len(fails)} failures, {len(by_key)} of {len(keys)} templates.</p>"
        f"<ul>{summary}</ul><table><tr><th>template<th>cv<th>lang<th>paper<th>part<th>page<th>check<th>detail"
        f"{rows}</table>", encoding="utf-8")
    print("sheets ->", out)


# ---------------------------------------------------------------- main

if __name__ == "__main__":
    args = sys.argv[1:]
    keys = srcs = None
    if "--keys" in args:
        i = args.index("--keys"); keys = args[i + 1].split(","); del args[i:i + 2]
    if "--src" in args:
        i = args.index("--src"); srcs = tuple(args[i + 1].split(",")); del args[i:i + 2]
    ref = None
    if "--ref" in args:
        # re-audit after a Word fix: new .docx only; the PDFs (and their
        # page images) are taken from an earlier run's work folder
        i = args.index("--ref"); ref = Path(args[i + 1]).resolve(); del args[i:i + 2]
    cmd, work = args[0], Path(args[1]).resolve()
    work.mkdir(parents=True, exist_ok=True)
    if cmd in ("gen", "all"):
        gen(work, keys, srcs or ("demo", "sample", "photo"), pdf=ref is None)
        if ref is not None:
            import shutil
            for sub, pat in (("pdf", "*.pdf"), ("png", "*.png")):
                (work / sub).mkdir(exist_ok=True)
                for f in (ref / sub).glob(pat):
                    s_ = split_name(f.name.split("-p")[0] if sub == "png" else f.stem)
                    if ".word" in f.name or (keys and s_["key"] not in keys):
                        continue
                    if srcs and s_["src"] not in srcs:
                        continue
                    shutil.copy2(f, work / sub / f.name)
    if cmd in ("word", "all"):
        word(work)
    if cmd in ("raster", "all"):
        raster(work)
    if cmd in ("check", "all"):
        check(work, keys)
    if cmd == "sheets":
        sheets(work, Path(args[2]))
