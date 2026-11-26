"""The download lock: every approved PDF / Word download, frozen.
(feature/download-lock, 2026-11-25)

Approved downloads are locked. A change may only touch templates the task
names. Run the download-lock test before every commit. Never update the lock
without the owner's approval.

    python tools/lock_downloads.py check            # tier 1: fingerprints (every commit)
    python tools/lock_downloads.py check --images   # tier 2: + page images, PDF and REAL Word (merges)
    python tools/lock_downloads.py update KEYS --approved "who approved what, when"
    python tools/lock_downloads.py sheets [OUT] [--keys KEYS]   # preview | PDF | Word, for approval
    python tools/lock_downloads.py rebuild-images [--keys KEYS]  # refill the image store from git
    python tools/lock_downloads.py init --approved NOTE          # once: the first lock

The matrix is the word audit's (tools/word_audit.py): every template x EN/AR x
Letter/A4 x cv/letter/both, for the demo and sample CVs, plus "photo" (the demo
with a magenta test photo) for the templates with a photo slot.

Tier 1 - fingerprints (tests/golden/downloads/<template>.json, in git):
  pdf   sha256 of exactly what the printer is given: the CV's HTML, the
        letter's HTML (at no fit and at a fixed fit - the letterhead takes the
        CV's fit), the paper and the faces checked before printing. Fonts, CSS
        and autofit.js are inlined in that HTML, so they are covered. The
        printer itself (Chromium's version) is recorded in _printer.json.
  docx  sha256 of every part of the .docx, with the two process-wide drawing
        id counters reset before each file (docx_dml._ID, docx_design._SHAPE_N)
        and docProps masked (timestamps). Embedded fonts are hashed
        DE-obfuscated and fontTable.xml with its random fontKey blanked: the
        random key is masked, a changed font is not.
Tier 2 - page images at 100 DPI, outside git (the image store; default
  ~/cvstand-download-lock, or CVSTAND_LOCK_DIR): pdf/<name>-pN.png from
  Chromium, word/<name>.word-pN.png from REAL Word (own process only,
  tools/word_com.ps1). Their sha256s are in the template's json, and the store
  can be rebuilt exactly from the commit that last changed that json.
  Compared with the pixel gate's tolerance (8/255 per channel, 50 pixels).

Every failure names template / cv / language / paper / part / PDF|Word, and
writes before | after | diff images to tests/e2e/artifacts/download-lock/.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
#: the fingerprints (in git); CVSTAND_LOCK_FILES points a throwaway copy elsewhere (tests)
LOCK = Path(os.environ.get("CVSTAND_LOCK_FILES") or ROOT / "tests" / "golden" / "downloads")
ARTIFACTS = ROOT / "tests" / "e2e" / "artifacts" / "download-lock"
sys.path.insert(0, str(ROOT))
from tools import word_audit as wa  # noqa: E402  (the audit's matrix and machinery)

SRCS = ("demo", "sample", "photo")
LANGS = ("en", "ar")
PAPERS = ("letter", "a4")
PARTS = ("cv", "letter", "both")
DPI = 100
WIDTH = {"letter": 850, "a4": 827}          # 8.5in / 8.27in at 100 DPI
FIXED_FIT = (0.9, 0.95)                     # any fit != None: covers the letter's fit path
CHANNEL_TOLERANCE = 8                       # tests/test_golden_pixels.py
MAX_DIFFERING_PIXELS = 50
PDF_RASTER_TRIES = 3                        # a failing PDF page is rasterised again (the rasteriser is noisy)
MAX_UPDATE = 5                              # templates per update call
WORD_DIFF_CAP = 40                          # Word files converted for diff images on a tier-1 failure


def _boot() -> Path:
    """Our OWN data dir (the test photo lives there, never in the user's
    data/uploads), set before the app is imported; worker processes inherit
    it. Returns the test photo."""
    if not os.environ.get("CVSTAND_LOCK_DATA"):
        d = tempfile.mkdtemp(prefix="cvstand-lockdata-")
        os.environ["CVSTAND_LOCK_DATA"] = d
        os.environ["CVSTAND_DATA_DIR"] = d
    return _photo()


def _photo() -> Path:
    from PIL import Image
    data = Path(os.environ["CVSTAND_LOCK_DATA"])
    (data / "uploads").mkdir(parents=True, exist_ok=True)
    p = data / "uploads" / "audit-photo.png"
    if not p.exists():
        Image.new("RGB", (600, 600), wa.PHOTO_RGB).save(p)
    os.chdir(ROOT)
    return p


def store() -> Path:
    return Path(os.environ.get("CVSTAND_LOCK_DIR") or Path.home() / "cvstand-download-lock")


def variants(key: str):
    """(src, lang, paper, part) of every download of `key`."""
    for src in SRCS:
        if src == "photo" and key not in wa.PHOTO_KEYS:
            continue
        for lang in LANGS:
            for paper in PAPERS:
                for part in PARTS:
                    yield src, lang, paper, part


def vname(src, lang, paper, part) -> str:
    return wa.SEP.join((src, lang, paper, part))


def label(key, v: str, kind: str) -> str:
    src, lang, paper, part = v.split(wa.SEP)
    return f"{key} · {src} · {lang.upper()} · {paper} · {part} · {kind}"


def all_keys() -> list[str]:
    from app import registry
    return sorted(registry.ported_keys())


# ------------------------------------------------------------ fingerprints

def _h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:24]


def docx_parts(blob: bytes) -> dict:
    """{part: sha} of a .docx, timestamps masked and fonts de-obfuscated."""
    from app.exporters.docx_font_embed import obfuscate
    z = zipfile.ZipFile(io.BytesIO(blob))
    names = sorted(z.namelist())
    keys = {}            # font part -> its GUID key
    if "word/fontTable.xml" in names:
        ft = z.read("word/fontTable.xml").decode("utf-8")
        rels = {}
        if "word/_rels/fontTable.xml.rels" in names:
            for el in re.findall(r"<Relationship\s[^>]*>",
                                 z.read("word/_rels/fontTable.xml.rels").decode("utf-8")):
                rid, tgt = re.search(r'Id="([^"]+)"', el), re.search(r'Target="([^"]+)"', el)
                if rid and tgt:
                    rels[rid.group(1)] = "word/" + tgt.group(1)
        for rid, guid in re.findall(r'r:id="([^"]+)"\s+w:fontKey="([^"]+)"', ft):
            if rid in rels:
                keys[rels[rid]] = guid
    out = {}
    for n in names:
        if n.startswith("docProps/"):
            continue
        data = z.read(n)
        if n == "word/fontTable.xml":
            data = re.sub(rb'w:fontKey="[^"]*"', b'w:fontKey=""', data)
        elif n.endswith(".odttf"):
            if n not in keys:
                raise RuntimeError(f"embedded font {n} has no key in fontTable.xml")
            data = obfuscate(data, keys[n])
            if data[:4] not in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
                raise RuntimeError(f"embedded font {n} did not de-obfuscate to a font")
        out[n] = _h(data)
    return out


def _fingerprint_key(args):
    """Worker: the downloads of one template and one CV -> {variant: {pdf, docx}}."""
    key, src_only = args
    photo = _photo()
    from app import letter as L
    from app.exporters import docx_design, docx_dml
    from app.exporters.docx import render_docx
    from app.exporters.pdf import chosen_faces
    from app.paper import paper_of
    from app.rendering import document_html
    out = {}
    for src in (src_only,):
        for lang in LANGS:
            for paper in PAPERS:
                dw = wa._cv(src, lang, photo, False)
                dp = wa._cv(src, lang, photo, True)
                if paper == "a4":
                    dw["paper"] = dp["paper"] = "a4"
                pp = paper_of(dp)
                head = json.dumps([pp.key, chosen_faces(dp)]).encode()
                cv = document_html(dp, key, for_pdf=True).encode()
                lt = (L.document_html(dp, key, for_pdf=True).encode() + b"\0"
                      + L.document_html(dp, key, for_pdf=True, header_fit=FIXED_FIT).encode())
                pdf = {"cv": _h(head + b"\0cv\0" + cv),
                       "letter": _h(head + b"\0letter\0" + cv + b"\0" + lt),
                       "both": _h(head + b"\0both\0" + cv + b"\0" + lt)}
                for part in PARTS:
                    docx_dml._ID[0] = 0
                    docx_design._SHAPE_N[0] = 0
                    parts = docx_parts(render_docx(dw, key, part))
                    out[vname(src, lang, paper, part)] = {
                        "pdf": pdf[part],
                        "docx": _h(json.dumps(parts, sort_keys=True).encode()),
                        "docx_parts": parts}
    return key, out


def fingerprints(keys, jobs: int | None = None, reverse: bool = False) -> dict:
    """{key: {variant: {...}}} for `keys`, in `jobs` processes (one task per
    template and CV, the photo CVs first: the slowest)."""
    tasks = [(k, s) for s in ("photo", "demo", "sample") for k in sorted(keys, reverse=reverse)
             if s != "photo" or k in wa.PHOTO_KEYS]
    jobs = jobs or min(8, os.cpu_count() or 4)
    if jobs <= 1:
        res = [_fingerprint_key(t) for t in tasks]
    else:
        with ProcessPoolExecutor(jobs) as ex:
            res = list(ex.map(_fingerprint_key, tasks))
    out = {k: {} for k in keys}
    for k, part in res:
        out[k].update(part)
    return {k: dict(sorted(v.items())) for k, v in sorted(out.items())}


def printer() -> dict:
    from importlib.metadata import version
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        v = b.version
        b.close()
    return {"playwright": version("playwright"), "chromium": v, "word": word_version()}


def word_version() -> str:
    """WINWORD.EXE's product version (the file, not a running Word)."""
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                        r"$p = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Winword.exe'"
                        " -ErrorAction SilentlyContinue).'(default)'; if ($p) { (Get-Item $p).VersionInfo.ProductVersion }"],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return ("Microsoft Word " + r.stdout.strip()) if r.stdout.strip() else "no Word"


# ------------------------------------------------------------ the lock files

def lock_path(key: str) -> Path:
    return LOCK / f"{key}.json"


def read_lock(key: str) -> dict | None:
    p = lock_path(key)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def write_lock(key: str, fp: dict, images: dict | None, meta: dict) -> None:
    doc = {"_meta": meta, "downloads": {}}
    for v, x in sorted(fp.items()):
        e = {"pdf": x["pdf"], "docx": x["docx"], "docx_parts": x["docx_parts"]}
        if images and v in images:
            e.update(images[v])
        doc["downloads"][v] = e
    lock_path(key).write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def write_index() -> None:
    """LOCK.md: who approved each template's lock, when, from what."""
    pr = json.loads((LOCK / "_printer.json").read_text(encoding="utf-8"))
    rows = []
    for p in sorted(LOCK.glob("*.json")):
        if p.name.startswith("_"):
            continue
        m = json.loads(p.read_text(encoding="utf-8"))["_meta"]
        rows.append(f"| {p.stem} | {m['date']} | {m['based_on']} | {m['approved']} |")
    (LOCK / "LOCK.md").write_text(
        "# Download lock\n\n"
        "Approved downloads are locked. A change may only touch templates the task names. "
        "Run the download-lock test before every commit. Never update the lock without the "
        "owner's approval.\n\n"
        "Generated by `tools/lock_downloads.py`; do not edit by hand. The lock is the CURRENT "
        "approved state, not a perfect one: known issues are in docs/KNOWN_TEMPLATE_ISSUES.md.\n\n"
        f"Printer: Chromium {pr['chromium']} (Playwright {pr['playwright']}). "
        f"Word: {pr.get('word', '?')}.\n\n"
        "| Template | Locked | From commit | Approval |\n|---|---|---|---|\n"
        + "\n".join(rows) + "\n", encoding="utf-8")


def _git(*a) -> str:
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL).stdout.strip()


# ------------------------------------------------------------ compare

def compare(fp: dict) -> list[dict]:
    """Differences between fresh fingerprints and the lock."""
    out = []
    for key, got in sorted(fp.items()):
        lk = read_lock(key)
        if lk is None:
            out.append({"key": key, "v": "", "kind": "lock", "detail": "no lock for this template"})
            continue
        want = lk["downloads"]
        for v in sorted(set(want) | set(got)):
            if v not in got or v not in want:
                out.append({"key": key, "v": v, "kind": "lock",
                            "detail": "download " + ("removed" if v not in got else "added")})
                continue
            if got[v]["pdf"] != want[v]["pdf"]:
                out.append({"key": key, "v": v, "kind": "PDF", "detail": "the printed HTML changed"})
            if got[v]["docx"] != want[v]["docx"]:
                a, b = want[v]["docx_parts"], got[v]["docx_parts"]
                parts = sorted(n for n in set(a) | set(b) if a.get(n) != b.get(n))
                out.append({"key": key, "v": v, "kind": "Word",
                            "detail": "changed parts: " + ", ".join(parts[:8])})
    return out


def report(diffs: list[dict]) -> str:
    return "\n".join(f"  {label(d['key'], d['v'], d['kind']) if d['v'] else d['key']}: {d['detail']}"
                     for d in diffs)


# ------------------------------------------------------------ images

def _gen_pdf_group(args):
    """Worker: the PDFs of one (src, lang, paper) for `keys` into work/pdf."""
    work, src, lang, paper, keys = args
    work = Path(work)
    photo = _photo()
    from app import letter as letter_mod
    from app.exporters.pdf import _print, chosen_faces
    from app.paper import paper_of
    from app.rendering import document_html
    d = wa._cv(src, lang, photo, True)
    if paper == "a4":
        d["paper"] = "a4"
    docs, labels = [], []
    for k in keys:
        docs.append((document_html(d, k, for_pdf=True), True))
        docs.append((lambda fit, k=k: letter_mod.document_html(d, k, for_pdf=True, header_fit=fit), True))
        labels += [(k, "cv"), (k, "letter")]
    for (k, part), blob in zip(labels, _print(docs, chosen_faces(d), paper_of(d))):
        (work / "pdf" / (wa.name_of(src, k, lang, paper, part) + ".pdf")).write_bytes(blob)
    return len(labels)


def gen_pdfs(work: Path, keys, only=None, jobs: int | None = None):
    """Chromium PDFs (cv + letter; "both" is the two joined) of `keys`;
    `only` = a set of (src, key, lang, paper) to restrict to.
    `jobs` Chromium processes: default 2 (CVSTAND_LOCK_PDF_JOBS). 4 got the
    tier-2 run killed for low memory on 2026-11-25 (16 GB PC, browser open)."""
    jobs = jobs or int(os.environ.get("CVSTAND_LOCK_PDF_JOBS") or 2)
    (work / "pdf").mkdir(parents=True, exist_ok=True)
    groups = []
    for src in SRCS:
        for lang in LANGS:
            for paper in PAPERS:
                ks = [k for k in keys if (src != "photo" or k in wa.PHOTO_KEYS)
                      and (only is None or (src, k, lang, paper) in only)]
                if ks:
                    groups.append((str(work), src, lang, paper, ks))
    with ProcessPoolExecutor(jobs) as ex:
        list(ex.map(_gen_pdf_group, groups))


def gen_docx(work: Path, keys, only=None):
    """.docx files of `keys` into work/docx (only = set of (src, key, lang, paper, part))."""
    photo = _photo()
    from app.exporters import docx_design, docx_dml
    from app.exporters.docx import render_docx
    (work / "docx").mkdir(parents=True, exist_ok=True)
    for key in keys:
        for src, lang, paper, part in variants(key):
            if only is not None and (src, key, lang, paper, part) not in only:
                continue
            d = wa._cv(src, lang, photo, False)
            if paper == "a4":
                d["paper"] = "a4"
            docx_dml._ID[0] = 0
            docx_design._SHAPE_N[0] = 0
            (work / "docx" / (wa.name_of(src, key, lang, paper, part) + ".docx")).write_bytes(
                render_docx(d, key, part))


def raster(pdfs: list[Path], out: Path):
    """Every page of `pdfs` -> out/<stem>-pN.png at 100 DPI (per paper width)."""
    out.mkdir(parents=True, exist_ok=True)
    for paper in PAPERS:
        todo = [p for p in pdfs if wa.split_name(p.name.split(".")[0])["paper"] == paper]
        for i in range(0, len(todo), 300):
            lst = out / f"_raster_{paper}.txt"
            lst.write_text("\n".join(str(p.resolve()) for p in todo[i:i + 300]), encoding="utf-8")
            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                            "-File", str(ROOT / "tools" / "pdf_raster.ps1"), str(lst), str(out.resolve()),
                            str(WIDTH[paper])], capture_output=True, text=True, stdin=subprocess.DEVNULL)
            lst.unlink()


def pages(folder: Path, stem: str) -> list[Path]:
    out, i = [], 1
    while (folder / f"{stem}-p{i}.png").exists():
        out.append(folder / f"{stem}-p{i}.png")
        i += 1
    return out


def file_sha(p: Path) -> str:
    return _h(p.read_bytes())


def build_images(work: Path, keys, only=None, word: bool = True) -> None:
    """PDF (and Word) page images of `keys` into work/png."""
    t = time.time()
    gen_pdfs(work, keys, only={(s, k, l, p) for s, k, l, p, _ in only} if only else None)
    raster(sorted((work / "pdf").glob("*.pdf")), work / "png")
    print(f"  PDF images: {time.time() - t:.0f}s", flush=True)
    if word:
        t = time.time()
        gen_docx(work, keys, only)
        wa.word(work)
        raster(sorted((work / "word").glob("*.word.pdf")), work / "png")
        print(f"  Word images: {time.time() - t:.0f}s", flush=True)


def image_entry(work: Path, key: str) -> dict:
    """{variant: {pdf_png: [sha], word_png: [sha]}} from work/png."""
    out = {}
    for src, lang, paper, part in variants(key):
        n = wa.name_of(src, key, lang, paper, part)
        if part == "both":
            pdf = (pages(work / "png", wa.name_of(src, key, lang, paper, "cv"))
                   + pages(work / "png", wa.name_of(src, key, lang, paper, "letter")))
        else:
            pdf = pages(work / "png", n)
        out[vname(src, lang, paper, part)] = {
            "pdf_png": [file_sha(p) for p in pdf],
            "word_png": [file_sha(p) for p in pages(work / "png", n + ".word")]}
    return out


def copy_to_store(work: Path, key: str) -> None:
    st = store()
    for kind in ("pdf", "word"):
        (st / kind).mkdir(parents=True, exist_ok=True)
        for old in (st / kind).glob(f"*{wa.SEP}{key}{wa.SEP}*.png"):
            old.unlink()
    for p in (work / "png").glob(f"*{wa.SEP}{key}{wa.SEP}*.png"):
        shutil.copy2(p, st / ("word" if ".word-" in p.name else "pdf") / p.name)


def store_pages(name: str, kind: str, part: str) -> list[Path]:
    """The locked page images of one download (name = full audit name)."""
    st = store() / kind
    if kind == "pdf" and part == "both":
        s = wa.split_name(name)
        return (pages(st, wa.name_of(s["src"], s["key"], s["lang"], s["paper"], "cv"))
                + pages(st, wa.name_of(s["src"], s["key"], s["lang"], s["paper"], "letter")))
    return pages(st, name if kind == "pdf" else name + ".word")


def differing_pixels(a, b) -> int:
    from PIL import ImageChops
    d = ImageChops.difference(a, b)
    r, g, bl = d.split()
    m = ImageChops.lighter(ImageChops.lighter(r, g), bl)
    return m.point(lambda v: 255 if v > CHANNEL_TOLERANCE else 0).histogram()[255]


def diff_pages(before: list[Path], after: list[Path], out: Path, title: str) -> list[str]:
    """Compare page lists; on a difference write <title>-pN.png = before|after|diff."""
    from PIL import Image, ImageChops, ImageDraw
    problems = []
    if len(before) != len(after):
        problems.append(f"{len(before)} locked pages, now {len(after)}")
    for i in range(max(len(before), len(after))):
        a = Image.open(before[i]).convert("RGB") if i < len(before) else None
        b = Image.open(after[i]).convert("RGB") if i < len(after) else None
        if a is not None and b is not None and a.size == b.size:
            n = differing_pixels(a, b)
            if n <= MAX_DIFFERING_PIXELS:
                continue
            problems.append(f"page {i + 1}: {n} pixels differ")
            diff = ImageChops.difference(a, b).point(lambda v: min(255, v * 8))
        else:
            if a is not None and b is not None:
                problems.append(f"page {i + 1}: size {a.size} -> {b.size}")
            diff = None
        w = max(x.size[0] for x in (a, b) if x is not None)
        h = max(x.size[1] for x in (a, b) if x is not None)
        sheet = Image.new("RGB", (3 * w + 40, h + 30), "white")
        dr = ImageDraw.Draw(sheet)
        for j, (cap, im) in enumerate((("locked (before)", a), ("now (after)", b), ("difference x8", diff))):
            dr.text((j * (w + 20) + 4, 6), cap, fill="black")
            if im is not None:
                sheet.paste(im, (j * (w + 20), 30))
            else:
                dr.text((j * (w + 20) + 4, 40), "no page", fill="red")
        out.mkdir(parents=True, exist_ok=True)
        sheet.save(out / f"{title}-p{i + 1}.png")
    return problems


def word_available() -> bool:
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                        "[bool](Get-ItemProperty 'Registry::HKEY_CLASSES_ROOT\\Word.Application\\CLSID' "
                        "-ErrorAction SilentlyContinue)"], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL)
    return r.stdout.strip().lower() == "true"


def image_diffs(diffs: list[dict], out: Path = ARTIFACTS) -> list[str]:
    """For the downloads that failed tier 1: render them now, compare with the
    locked images, write before|after|diff. Returns notes."""
    notes = []
    if not diffs:
        return notes
    if not store().exists():
        return [f"no image store at {store()}: run `tools/lock_downloads.py rebuild-images`"]
    shutil.rmtree(out, ignore_errors=True)
    only_pdf, only_word = set(), set()
    for d in diffs:
        if not d["v"]:
            continue
        src, lang, paper, part = d["v"].split(wa.SEP)
        if d["kind"] == "PDF":
            only_pdf.add((src, d["key"], lang, paper))
        elif d["kind"] == "Word":
            only_word.add((src, d["key"], lang, paper, part))
    work = Path(tempfile.mkdtemp(prefix="cvstand-lockdiff-"))
    try:
        keys = sorted({k for _, k, *_ in only_pdf | only_word})
        if only_pdf:
            gen_pdfs(work, keys, only=only_pdf)
            raster(sorted((work / "pdf").glob("*.pdf")), work / "png")
        if only_word:
            if len(only_word) > WORD_DIFF_CAP:
                notes.append(f"{len(only_word)} Word files changed: diff images for the first {WORD_DIFF_CAP}")
                only_word = set(sorted(only_word)[:WORD_DIFF_CAP])
            if word_available():
                gen_docx(work, keys, only_word)
                wa.word(work)
                raster(sorted((work / "word").glob("*.word.pdf")), work / "png")
            else:
                notes.append("Microsoft Word is not installed: no Word diff images (the changed XML parts are listed)")
                only_word = set()
        for d in diffs:
            if not d["v"] or d["kind"] not in ("PDF", "Word"):
                continue
            src, lang, paper, part = d["v"].split(wa.SEP)
            name = wa.name_of(src, d["key"], lang, paper, part)
            kind = "pdf" if d["kind"] == "PDF" else "word"
            if kind == "word" and (src, d["key"], lang, paper, part) not in only_word:
                continue
            if kind == "pdf" and part == "both":
                now = (pages(work / "png", wa.name_of(src, d["key"], lang, paper, "cv"))
                       + pages(work / "png", wa.name_of(src, d["key"], lang, paper, "letter")))
            else:
                now = pages(work / "png", name if kind == "pdf" else name + ".word")
            probs = diff_pages(store_pages(name, kind, part), now, out, f"{name}.{kind}")
            d["detail"] += "; " + ("; ".join(probs) if probs else "pixels the same (a change Word/Chromium does not draw)")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return notes


def check_images(keys) -> list[dict]:
    """Tier 2: render everything, compare every page with the image store."""
    work = Path(tempfile.mkdtemp(prefix="cvstand-lockimg-"))
    fails = []
    try:
        build_images(work, keys, word=True)
        for key in keys:
            lk = read_lock(key)["downloads"]
            for src, lang, paper, part in variants(key):
                name = wa.name_of(src, key, lang, paper, part)
                v = vname(src, lang, paper, part)
                for kind in ("pdf", "word"):
                    if kind == "pdf" and part == "both":
                        now = (pages(work / "png", wa.name_of(src, key, lang, paper, "cv"))
                               + pages(work / "png", wa.name_of(src, key, lang, paper, "letter")))
                    else:
                        now = pages(work / "png", name if kind == "pdf" else name + ".word")
                    locked = store_pages(name, kind, part)
                    if len(locked) != len(lk[v].get(f"{kind}_png", [])):
                        fails.append({"key": key, "v": v, "kind": kind.upper(),
                                      "detail": "image store incomplete: run rebuild-images"})
                        continue
                    probs = diff_pages(locked, now, ARTIFACTS, f"{name}.{kind}")
                    tries = 1
                    while probs and kind == "pdf" and tries < PDF_RASTER_TRIES:
                        # The rasteriser (tools/pdf_raster.ps1) is not deterministic: the SAME
                        # PDF file gave 0, 0, 71 px against the lock (2026-11-26, ats-t20). Raster
                        # the same PDFs again; a real change fails every try.
                        tries += 1
                        again = work / f"retry{tries}"
                        stems = ([wa.name_of(src, key, lang, paper, p) for p in ("cv", "letter")]
                                 if part == "both" else [name])
                        raster([work / "pdf" / (s + ".pdf") for s in stems], again)
                        now = [pg for s in stems for pg in pages(again, s)]
                        probs = diff_pages(locked, now, ARTIFACTS, f"{name}.{kind}")
                    if probs and tries > 1:
                        probs.append(f"(every one of {tries} rasterisations)")
                    if probs:
                        fails.append({"key": key, "v": v, "kind": "PDF" if kind == "pdf" else "Word",
                                      "detail": "; ".join(probs)})
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return fails


# ------------------------------------------------------------ commands

def _parse_keys(arg: str) -> list[str]:
    keys = [k.strip() for k in arg.split(",") if k.strip()]
    known = set(all_keys())
    if not keys:
        sys.exit("name the templates to update, e.g. modern-t20,ats-t5")
    if any(k.lower() == "all" or any(c in k for c in "*?[") for k in keys):
        sys.exit("refused: the lock is updated only for templates the task names - never all at once")
    bad = [k for k in keys if k not in known]
    if bad:
        sys.exit(f"unknown template(s): {bad}")
    if len(keys) > MAX_UPDATE:
        sys.exit(f"refused: {len(keys)} templates in one update (max {MAX_UPDATE}); "
                 "name only the templates the owner approved")
    return keys


def cmd_check(images: bool, keys=None) -> int:
    keys = keys or all_keys()
    t = time.time()
    fp = fingerprints(keys)
    diffs = compare(fp)
    t1 = time.time() - t
    pr = json.loads((LOCK / "_printer.json").read_text(encoding="utf-8"))
    notes = []
    if images:
        now = printer()
        if now["chromium"] != pr["chromium"]:
            notes.append(f"printer changed: Chromium {pr['chromium']} -> {now['chromium']}")
    if diffs:
        notes += image_diffs(diffs)
    print(f"tier 1 (fingerprints): {len(keys)} templates, "
          f"{sum(len(v) for v in fp.values())} downloads x PDF+Word in {t1:.0f}s")
    fails = list(diffs)
    if images:
        t = time.time()
        fails += check_images(keys)
        print(f"tier 2 (page images, PDF + real Word): {time.time() - t:.0f}s")
    for n in notes:
        print("note:", n)
    if fails:
        print(f"DOWNLOAD LOCK: {len(fails)} difference(s)\n" + report(fails))
        print(f"before | after | diff images: {ARTIFACTS}")
        return 1
    print("download lock: every download matches")
    return 0


def _lock_templates(keys, note: str, require_new: bool) -> None:
    for k in keys:
        if require_new and lock_path(k).exists():
            sys.exit(f"refused: {k} is already locked; use `update` with the owner's approval")
    t = time.time()
    fp = fingerprints(keys)
    print(f"fingerprints: {time.time() - t:.0f}s")
    work = Path(tempfile.mkdtemp(prefix="cvstand-lockinit-"))
    try:
        build_images(work, keys, word=True)
        missing = [wa.name_of(s, k, l, p, pt) for k in keys for s, l, p, pt in variants(k)
                   if not pages(work / "png", wa.name_of(s, k, l, p, pt) + ".word")]
        if missing:
            sys.exit(f"refused: {len(missing)} Word files did not convert, e.g. {missing[:3]}")
        meta = {"date": _dt.date.today().isoformat(), "approved": note,
                "based_on": _git("rev-parse", "--short", "HEAD")
                + (" + working tree" if _git("status", "--porcelain", "--", "app") else "")}
        before = {p.name: p.read_bytes() for p in LOCK.glob("*.json") if p.stem not in keys}
        for k in keys:
            old = read_lock(k)
            copy_to_store(work, k)
            write_lock(k, fp[k], image_entry(work, k), meta)
            if old is not None:
                n_pdf = sum(1 for v, e in fp[k].items() if old["downloads"].get(v, {}).get("pdf") != e["pdf"])
                n_doc = sum(1 for v, e in fp[k].items() if old["downloads"].get(v, {}).get("docx") != e["docx"])
                print(f"{k}: {n_pdf} PDF and {n_doc} Word downloads changed")
            else:
                print(f"{k}: locked ({len(fp[k])} downloads)")
        after = {p.name: p.read_bytes() for p in LOCK.glob("*.json") if p.stem not in keys}
        assert before == after, "another template's lock changed"
        write_index()
    finally:
        shutil.rmtree(work, ignore_errors=True)


def cmd_rebuild_images(keys=None) -> None:
    """Refill the image store from the commit that last changed each lock."""
    keys = keys or [p.stem for p in sorted(LOCK.glob("*.json")) if not p.stem.startswith("_")]
    by_commit = {}
    for k in keys:
        c = _git("log", "-1", "--format=%H", "--", f"tests/golden/downloads/{k}.json")
        if not c:
            sys.exit(f"{k}: its lock is not committed yet; nothing to rebuild from")
        by_commit.setdefault(c, []).append(k)
    for commit, ks in by_commit.items():
        tree = Path(tempfile.mkdtemp(prefix="cvstand-lockrebuild-")) / "tree"
        subprocess.run(["git", "worktree", "add", "--detach", str(tree), commit], cwd=ROOT,
                       check=True, capture_output=True, stdin=subprocess.DEVNULL)
        try:
            work = tree.parent / "work"
            subprocess.run([sys.executable, str(tree / "tools" / "lock_downloads.py"), "_images",
                            str(work), ",".join(ks)], cwd=tree, check=True, stdin=subprocess.DEVNULL)
            for k in ks:
                want = read_lock(k)["downloads"]
                got = image_entry(work, k)
                same = sum(1 for v in want for kind in ("pdf_png", "word_png")
                           if want[v].get(kind) == got[v][kind])
                total = sum(1 for v in want for kind in ("pdf_png", "word_png"))
                copy_to_store(work, k)
                # Word pages come back bit-identical; a Chromium PDF page can
                # differ by a few anti-aliased pixels (measured: 8 px, ats-t1
                # EN A4) - tier 2 compares with tolerance, not by hash
                print(f"{k}: {same}/{total} page sets identical to the locked hashes "
                      "(a PDF set may differ by anti-aliasing only; run check --images)")
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(tree)], cwd=ROOT,
                           capture_output=True, stdin=subprocess.DEVNULL)
            shutil.rmtree(tree.parent, ignore_errors=True)


def cmd_sheets(out: Path, keys=None) -> None:
    """One sheet per template: rows = cv/language/paper, columns =
    preview | PDF | Word for the CV, the letter and CV + letter."""
    from PIL import Image, ImageDraw
    keys = keys or all_keys()
    out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="cvstand-sheets-"))
    try:
        photo = _photo()
        from playwright.sync_api import sync_playwright
        from app import letter as L
        from app.rendering import document_html
        prev = work / "preview"
        prev.mkdir()
        with sync_playwright() as p:
            b = p.chromium.launch(args=["--no-sandbox"])
            for key in keys:
                for src in SRCS:
                    if src == "photo" and key not in wa.PHOTO_KEYS:
                        continue
                    for lang in LANGS:
                        for paper in PAPERS:
                            d = wa._cv(src, lang, photo, True)
                            if paper == "a4":
                                d["paper"] = "a4"
                            for part, html in (("cv", document_html(d, key, for_pdf=True)),
                                               ("letter", L.document_html(d, key, for_pdf=True))):
                                pg = b.new_page(viewport={"width": 850, "height": 1202 if paper == "a4" else 1100})
                                pg.set_content(html, wait_until="networkidle")
                                pg.evaluate("window.ResumeAutofit ? window.ResumeAutofit.ready : null")
                                pg.screenshot(path=str(prev / (wa.name_of(src, key, lang, paper, part) + ".png")),
                                              full_page=False)
                                pg.close()
            b.close()
        miss = [k for k in keys if not list((store() / "pdf").glob(f"*{wa.SEP}{k}{wa.SEP}*"))]
        if miss:
            print(f"rendering images for {len(miss)} templates missing from the store")
            build_images(work, miss)
        cols = [("Preview CV", "prev", "cv", 1), ("PDF CV", "pdf", "cv", 1), ("Word CV", "word", "cv", 1),
                ("Preview letter", "prev", "letter", 1), ("PDF letter", "pdf", "letter", 1),
                ("Word letter", "word", "letter", 1),
                ("Word CV+letter p1", "word", "both", 1), ("Word CV+letter p2", "word", "both", 2)]
        tw, lab = 170, 120
        th = int(tw * 1169 / 827)
        for key in keys:
            rows = [(s, l, p) for s in SRCS if s != "photo" or key in wa.PHOTO_KEYS
                    for l in LANGS for p in PAPERS]
            sheet = Image.new("RGB", (lab + len(cols) * (tw + 8), 40 + len(rows) * (th + 8)), "white")
            dr = ImageDraw.Draw(sheet)
            dr.text((6, 6), key, fill="black")
            for j, (title, *_r) in enumerate(cols):
                dr.text((lab + j * (tw + 8) + 4, 22), title, fill="black")
            for i, (src, lang, paper) in enumerate(rows):
                y = 40 + i * (th + 8)
                dr.text((6, y + 6), f"{src}\n{lang.upper()} {paper}", fill="black")
                for j, (title, kind, part, page) in enumerate(cols):
                    n = wa.name_of(src, key, lang, paper, part)
                    if kind == "prev":
                        cand = [prev / f"{n}.png"]
                    else:
                        cand = [store() / kind / (f"{n}-p{page}.png" if kind == "pdf" else f"{n}.word-p{page}.png"),
                                work / "png" / (f"{n}-p{page}.png" if kind == "pdf" else f"{n}.word-p{page}.png")]
                    x = lab + j * (tw + 8)
                    f = next((c for c in cand if c.exists()), None)
                    if f:
                        im = Image.open(f).convert("RGB")
                        im.thumbnail((tw, th))
                        sheet.paste(im, (x, y))
                        dr.rectangle([x - 1, y - 1, x + im.size[0], y + im.size[1]], outline="#bbb")
                    else:
                        dr.text((x + 4, y + 4), "missing", fill="red")
            sheet.save(out / f"{key}.png")
        links = "".join(f"<li><a href='{k}.png'>{k}</a></li>" for k in keys)
        (out / "index.html").write_text(
            "<!doctype html><meta charset=utf-8><title>Download lock review</title>"
            "<style>body{font:14px system-ui;margin:16px}</style>"
            "<h1>Downloads for approval: preview | PDF | Word</h1>"
            f"<p>{len(keys)} templates. Known issues: docs/KNOWN_TEMPLATE_ISSUES.md.</p><ul>{links}</ul>",
            encoding="utf-8")
        print("sheets ->", out)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    _boot()

    def opt(name, default=None):
        if name in args:
            i = args.index(name)
            v = args[i + 1]
            del args[i:i + 2]
            return v
        return default
    keys_arg = opt("--keys")
    note = opt("--approved")
    images = "--images" in args
    if images:
        args.remove("--images")
    if not args:
        print(__doc__)
        return 2
    cmd = args[0]
    keys = keys_arg.split(",") if keys_arg else None
    if cmd == "check":
        return cmd_check(images, keys)
    if cmd == "fingerprints":          # determinism checks: fingerprints OUT.json [--reverse]
        fp = fingerprints(keys or all_keys(), reverse="--reverse" in args)
        Path(args[1]).write_text(json.dumps(fp, sort_keys=True), encoding="utf-8")
        return 0
    if cmd == "update":
        if len(args) < 2:
            sys.exit("name the templates to update, e.g. update modern-t20,ats-t5 --approved NOTE")
        ks = _parse_keys(args[1])
        if not note or len(note.strip()) < 8:
            sys.exit("refused: --approved \"<the owner's approval: who, what, when>\" is required")
        _lock_templates(ks, note.strip(), require_new=False)
        return 0
    if cmd == "init":
        if not note:
            sys.exit("refused: --approved NOTE is required")
        if any(p for p in LOCK.glob("*.json") if not p.stem.startswith("_")):
            sys.exit("refused: a lock already exists; use `update KEYS --approved NOTE`")
        LOCK.mkdir(parents=True, exist_ok=True)
        pr = printer()
        (LOCK / "_printer.json").write_text(json.dumps(pr, indent=1) + "\n", encoding="utf-8")
        ks = keys or all_keys()
        _lock_templates(ks, note, require_new=True)
        return 0
    if cmd == "_images":               # used by rebuild-images inside a worktree of the lock's commit
        work = Path(args[1])
        build_images(work, args[2].split(","), word=True)
        return 0
    if cmd == "rebuild-images":
        cmd_rebuild_images(keys)
        return 0
    if cmd == "sheets":
        out = Path(args[1]) if len(args) > 1 else (
            Path.home() / "Desktop" / f"review-download-lock-{_dt.date.today().isoformat()}")
        cmd_sheets(out, keys)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
