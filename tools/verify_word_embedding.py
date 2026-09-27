"""Prove, in real Microsoft Word, that the Word exports use their embedded
fonts and break across pages cleanly (typography step 6).

    venv/Scripts/python tools/verify_word_embedding.py [keys...] [--out DIR]

Windows + Word only (COM); exits 0 with a note elsewhere. For every template
(or the keys given), in English and Arabic, it exports the sample résumé,
has Word open it, lay it out and save it as PDF, then checks:

  flow     where Word ACTUALLY breaks the pages. One or two pages are both
           fine (user decision, 2026-09-27: content flows, it is never
           squeezed). A failure is "Exactly" line spacing (clips glyphs,
           overlaps lines), a section heading whose next paragraph starts on
           a later page (orphaned), or a job title whose company/date line
           starts on a later page. tests/test_docx_flow.py checks the same
           rules in the XML; this checks them against Word's real breaks.
  fonts    every font Word drew with. Word renames embedded fonts in its PDFs
           (`___WRD_EMBED_SUB_46`), so each is IDENTIFIED by comparing its
           advance widths with the built TTFs: a real use of the embedded
           font matches one exactly. Anything else Word drew with is listed,
           so a substitution cannot pass silently.

WHY THIS MACHINE COUNTS: none of the typography fonts is installed here
(checked), so Word can only draw them from the file. Spec §7.8 still asks
for the same check by hand on another PC; this is the automated half.

OFFICE CLOUD FONTS (found 2026-09-27): Microsoft 365 downloads some free
families itself when a document names them - Anton, IBM Plex Mono,
Merriweather, Montserrat, Open Sans, Playfair Display, Poppins on this PC
(%LOCALAPPDATA%/Microsoft/FontCache/4/CloudFonts). For those, Word PREFERS
Microsoft's copy to the embedded one, keeps the real name in its PDF, and
the widths can differ slightly from our file (Open Sans' comma). So a font
that is not our embedded file but IS one of these families is reported as
"cloud", not as a failure - and not as proof of embedding either. Embedding
is what serves every other family, and every reader without Microsoft 365.

WORD COM TRAP: `New-Object -ComObject Word.Application` can attach to an
instance that is still quitting and hang for good. One fresh Word per file,
started only once no WINWORD is left, is reliable.
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import registry  # noqa: E402
from app.exporters.docx import render_docx  # noqa: E402
from app.typography import built_faces  # noqa: E402
from app.typography.faces import FONT_DIR  # noqa: E402

SAMPLES = {"en": ROOT / "data" / "sample_resume.json",
           "ar": ROOT / "data" / "sample_resume_ar.json"}

#: System faces Word may use for glyphs a CV font lacks: list bullets
#: (Symbol) and the skill dots ●○ (Arial). Any OTHER font that draws visible
#: text is a finding; one that draws only spaces is not (Word sets the spaces
#: beside Arial's skill dots in Calibri, its theme font - nothing shows).
SYSTEM_OK = {"SymbolMT", "Symbol", "ArialMT", "Arial"}


def cloud_families() -> set[str]:
    """Families Office has fetched as cloud fonts on this machine."""
    import os
    d = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "FontCache" / "4" / "CloudFonts"
    return {x.name for x in d.iterdir() if x.is_dir()} if d.is_dir() else set()


def drawn_text(pdf: bytes) -> dict[str, str]:
    """Font name (subset tag removed) -> all the text the PDF draws in it."""
    from collections import defaultdict
    from pypdf import PdfReader
    got: dict[str, str] = defaultdict(str)

    def visit(text, _cm, _tm, fd, _fs):
        if fd and text:
            got[str(fd.get("/BaseFont", "")).lstrip("/").split("+", 1)[-1]] += text

    for page in PdfReader(io.BytesIO(pdf)).pages:
        page.extract_text(visitor_text=visit)
    return dict(got)

# Per non-empty paragraph: page of its first and last character, its line
# spacing rule, the character style of its first character, and a snippet.
_PS = r"""
param($src, $pdf)
$ErrorActionPreference = 'Stop'
$w = New-Object -ComObject Word.Application
$w.Visible = $false; $w.DisplayAlerts = 0
try {
  $d = $w.Documents.Open($src, $false, $true)
  Write-Output ("PAGES`t" + $d.Content.Information(4))
  foreach ($p in $d.Paragraphs) {
    $t = $p.Range.Text.Trim()
    if ($t.Length -eq 0) { continue }
    $s = $p.Range.Characters(1).Information(3)
    $e = $p.Range.Characters($p.Range.Characters.Count).Information(3)
    $cs = $p.Range.Characters(1).CharacterStyle.NameLocal
    $snip = $t.Substring(0, [Math]::Min(30, $t.Length)) -replace "`t", " "
    Write-Output ("P`t$s`t$e`t$($p.Format.LineSpacingRule)`t$cs`t$snip")
  }
  $d.ExportAsFixedFormat($pdf, 17)
  $d.Close(0)
} finally { $w.Quit() }
"""
WD_LINE_SPACE_EXACTLY = 4


def _word_running() -> bool:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq WINWORD.EXE"],
                         capture_output=True, text=True).stdout
    return "WINWORD.EXE" in out


def word_layout(docx: Path, pdf: Path, timeout: int = 240) -> tuple[int | None, list[dict]]:
    """(page count, paragraphs as Word laid them out), and the PDF written."""
    for _ in range(40):
        if not _word_running():
            break
        time.sleep(0.5)
    script = docx.parent / "_probe.ps1"
    script.write_text(_PS, encoding="utf-8")
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                              "-File", str(script), str(docx), str(pdf)],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, []
    pages, paras = None, []
    for line in res.stdout.splitlines():
        f = line.split("\t")
        if f[0] == "PAGES" and len(f) > 1:
            pages = int(f[1])
        elif f[0] == "P" and len(f) >= 6:
            paras.append({"start": int(f[1]), "end": int(f[2]), "rule": int(f[3]),
                          "style": f[4], "text": f[5]})
    return pages, paras


def flow_problems(paras: list[dict]) -> list[str]:
    """The user's rules for a page break (see "flow" above)."""
    out = []
    for i, p in enumerate(paras):
        if p["rule"] == WD_LINE_SPACE_EXACTLY:
            out.append(f"exact line spacing: {p['text']!r}")
        nxt = paras[i + 1] if i + 1 < len(paras) else None
        if nxt and nxt["start"] > p["end"]:
            if p["style"] == "CV Heading":
                out.append(f"orphaned heading {p['text']!r} (page {p['end']})")
            elif p["style"] == "CV Role":
                out.append(f"job title {p['text']!r} split from its line (page {p['end']})")
    return out


# ---- font identification -------------------------------------------------------

def _widths(font) -> dict[int, float]:
    cm, hm, upm = font.getBestCmap() or {}, font["hmtx"], font["head"].unitsPerEm
    return {cp: hm[g][0] / upm for cp, g in cm.items() if g in hm.metrics}


_CANDIDATES: dict | None = None


def _candidates() -> dict:
    global _CANDIDATES
    if _CANDIDATES is None:
        from fontTools.ttLib import TTFont
        _CANDIDATES = {k: _widths(TTFont(FONT_DIR / f["ttf"], lazy=True))
                       for k, f in built_faces().items()}
    return _CANDIDATES


def identify(program: bytes) -> tuple[tuple[str, int] | None, float]:
    from fontTools.ttLib import TTFont
    got = _widths(TTFont(io.BytesIO(program)))
    best, err = None, 1.0
    for key, ref in _candidates().items():
        common = [cp for cp in got if cp in ref]
        if len(common) < 5:
            continue
        e = sum(abs(got[cp] - ref[cp]) for cp in common) / len(common)
        if e < err:
            best, err = key, e
    return best, err


def pdf_fonts(pdf: bytes) -> list[dict]:
    from pypdf import PdfReader
    out, seen = [], set()

    def walk(res):
        if not res:
            return
        res = res.get_object()
        for fo in (res.get("/Font") or {}).values():
            fo = fo.get_object()
            base = str(fo.get("/BaseFont", "")).lstrip("/")
            name = base.split("+", 1)[-1]
            if base in seen:
                continue
            seen.add(base)
            entry = {"pdf_name": name, "face": None, "error": None}
            desc = (fo["/DescendantFonts"][0].get_object().get("/FontDescriptor")
                    if "/DescendantFonts" in fo else fo.get("/FontDescriptor"))
            prog = desc.get_object().get("/FontFile2") if desc else None
            if prog is not None:
                try:
                    face, err = identify(prog.get_object().get_data())
                    if face and err < 1e-3:
                        entry["face"] = list(face)
                    entry["error"] = round(err, 5)
                except Exception as exc:  # noqa: BLE001
                    entry["error"] = f"unreadable: {exc.__class__.__name__}"
            out.append(entry)
        for x in (res.get("/XObject") or {}).values():
            walk(x.get_object().get("/Resources"))

    for page in PdfReader(io.BytesIO(pdf)).pages:
        walk(page.get("/Resources"))
    return out


def main(argv: list[str]) -> int:
    if sys.platform != "win32":
        print("SKIP: needs Windows + Microsoft Word (COM)")
        return 0
    out_dir = Path(argv[argv.index("--out") + 1]) if "--out" in argv else \
        Path(tempfile.mkdtemp(prefix="cvstand-word-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    keys = [a for a in argv[1:] if a in registry.ported_keys()] or registry.ported_keys()
    samples = {lang: json.loads(p.read_text(encoding="utf-8")) for lang, p in SAMPLES.items()}
    report, bad = [], 0
    for key in keys:
        for lang, data in samples.items():
            stem = f"{key}-{lang}"
            blob = render_docx(data, key)
            docx, pdf = out_dir / f"{stem}.docx", out_dir / f"{stem}.pdf"
            docx.write_bytes(blob)
            pages, paras = word_layout(docx, pdf)
            fonts = pdf_fonts(pdf.read_bytes()) if pdf.exists() else []
            text = drawn_text(pdf.read_bytes()) if pdf.exists() else {}
            cloud_fams = cloud_families()
            unmatched = [f for f in fonts if not f["face"]
                         and f["pdf_name"].split(",")[0] not in SYSTEM_OK
                         and text.get(f["pdf_name"], "").strip()]
            cloud = sorted({f["pdf_name"] for f in unmatched
                            if any(f["pdf_name"].startswith(c) for c in cloud_fams)})
            unknown = [f["pdf_name"] for f in unmatched if f["pdf_name"] not in cloud]
            flow = flow_problems(paras) if paras else ["Word laid out no text"]
            ok = pages is not None and not flow and not unknown and pdf.exists()
            bad += not ok
            report.append({"key": key, "lang": lang, "pages": pages, "kb": len(blob) // 1024,
                           "flow": flow, "cloud": cloud,
                           "faces": sorted({tuple(f["face"]) for f in fonts if f["face"]}),
                           "system": sorted({f["pdf_name"] for f in fonts
                                             if not f["face"] and f not in unknown}),
                           "unknown": unknown})
            print(f"{'OK  ' if ok else 'FAIL'} {stem:16s} pages={pages} {len(blob) // 1024:5d} KB"
                  + (f"  UNIDENTIFIED {unknown}" if unknown else "")
                  + (f"  FLOW {flow}" if flow else ""), flush=True)
    (out_dir / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    two = sum(1 for r in report if r["pages"] == 2)
    print(f"\n{len(report) - bad}/{len(report)} pass (clean page breaks, only embedded or "
          f"allowed system fonts); {two} flow to 2 pages; report: {out_dir / 'report.json'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
