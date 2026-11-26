"""The download lock (feature/download-lock, 2026-11-25).

Approved downloads are locked. A change may only touch templates the task
names. Run the download-lock test before every commit. Never update the lock
without the owner's approval.

    pytest tests/test_download_lock.py                   # tier 1, ~3.5 min: every commit
    pytest --lock-images tests/test_download_lock.py     # + tier 2, page images: before merges

Tier 1 regenerates every download (49 templates x demo/sample/photo CV x EN/AR
x Letter/A4 x cv/letter/both = 1368, PDF and Word) and compares its fingerprint
with tests/golden/downloads/<template>.json. A difference fails, naming
template, CV, language, paper, part and PDF|Word, and writes before | after |
diff images to tests/e2e/artifacts/download-lock/ (from the image store; Word
through REAL Word, its own process only).

Tier 2 renders every page (Chromium, and real Word) and compares it with the
locked page images at the pixel gate's tolerance.

The lock is the CURRENT approved state - docs/KNOWN_TEMPLATE_ISSUES.md lists
what is known to be wrong in it. Updating it is one explicit command, for the
templates the owner approved, never all at once:
    python tools/lock_downloads.py update <templates> --approved "<who, what, when>"
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "lock_downloads.py"
LOCK = ROOT / "tests" / "golden" / "downloads"
sys.path.insert(0, str(ROOT))


def _run(*args, timeout=None, env=None):
    return subprocess.run([sys.executable, str(TOOL), *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", stdin=subprocess.DEVNULL, timeout=timeout,
                          env={**os.environ, **(env or {})})


# ------------------------------------------------------------ the gate

def test_every_download_matches_the_lock():
    """Tier 1: all 1368 downloads, PDF and Word, against the locked fingerprints."""
    r = _run("check")
    assert r.returncode == 0, (
        "A download changed. If the task named this template and the owner approved the new "
        "look, update ONLY that template: tools/lock_downloads.py update <template> --approved "
        "\"...\". Otherwise the change touched a template it must not.\n" + r.stdout[-6000:]
        + r.stderr[-2000:])


@pytest.mark.lock_images
def test_every_download_page_matches_the_locked_images():
    """Tier 2: every page, PDF (Chromium) and Word (real Word), against the image store."""
    r = _run("check", "--images")
    assert r.returncode == 0, r.stdout[-6000:] + r.stderr[-2000:]


# ------------------------------------------------------------ the lock itself

def test_the_lock_covers_every_template_and_download():
    from app import registry
    from tools import lock_downloads as L
    keys = sorted(registry.ported_keys())
    locked = sorted(p.stem for p in LOCK.glob("*.json") if not p.stem.startswith("_"))
    assert locked == keys
    for k in keys:
        lk = json.loads((LOCK / f"{k}.json").read_text(encoding="utf-8"))
        want = {L.vname(*v) for v in L.variants(k)}
        assert set(lk["downloads"]) == want, k
        assert lk["_meta"]["approved"], k
        for v, e in lk["downloads"].items():
            # the page images are locked too (their hashes; the PNGs live in the store)
            n = 2 if v.endswith("both") else 1
            assert len(e["pdf_png"]) == n and len(e["word_png"]) == n, (k, v)
    assert (LOCK / "LOCK.md").exists() and (LOCK / "_printer.json").exists()


# ------------------------------------------------------------ the update command

@pytest.mark.parametrize("args, why", [
    (["update"], "name the templates"),
    (["update", "all", "--approved", "owner said so"], "never all at once"),
    (["update", "modern-t*", "--approved", "owner said so"], "never all at once"),
    (["update", "modern-t1,modern-t2,modern-t3,modern-t4,modern-t5,modern-t6",
      "--approved", "owner said so"], "max 5"),
    (["update", "modern-t1"], "--approved"),
    (["update", "modern-t1", "--approved", "ok"], "--approved"),
    (["update", "modern-t99", "--approved", "owner said so"], "unknown template"),
    (["init", "--approved", "again"], "a lock already exists"),
])
def test_the_update_command_refuses(args, why, tmp_path):
    before = {p.name: p.read_bytes() for p in LOCK.iterdir()}
    r = _run(*args, timeout=120, env={"CVSTAND_LOCK_DIR": str(tmp_path)})
    assert r.returncode != 0
    assert why in (r.stdout + r.stderr)
    assert {p.name: p.read_bytes() for p in LOCK.iterdir()} == before


# ------------------------------------------------------------ the fingerprint's masks

def _docx():
    # no photo here, so no lock data dir (the session's CVSTAND_DATA_DIR stays)
    from app.exporters.docx import render_docx
    from tests import letter_samples as LS
    return render_docx(LS.with_letter("en"), "modern-t20", "cv")


def _rezip(blob, change):
    zin = zipfile.ZipFile(io.BytesIO(blob))
    parts = {n: zin.read(n) for n in zin.namelist()}
    change(parts)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in parts.items():
            z.writestr(n, b)
    return out.getvalue()


def _keys(parts):
    ft = parts["word/fontTable.xml"].decode()
    return re.findall(r'r:id="rIdFont(\d+)"\s+w:fontKey="([^"]+)"', ft)


def test_a_new_font_key_is_not_a_change():
    """Word's font obfuscation key is random: re-keying the same fonts is the same file."""
    from app.exporters.docx_font_embed import obfuscate
    from tools import lock_downloads as L
    blob = _docx()

    def rekey(parts):
        for n, guid in _keys(parts):
            new = "{11111111-2222-3333-4444-%012d}" % int(n)
            f = f"word/fonts/font{n}.odttf"
            parts[f] = obfuscate(obfuscate(parts[f], guid), new)
            parts["word/fontTable.xml"] = parts["word/fontTable.xml"].replace(guid.encode(), new.encode())
    assert L.docx_parts(_rezip(blob, rekey)) == L.docx_parts(blob)


def test_a_swapped_font_is_a_change():
    """The fonts are masked against the random key only: a different face fails."""
    from app.exporters.docx_font_embed import obfuscate
    from tools import lock_downloads as L
    blob = _docx()

    def swap(parts):
        (n1, g1), (n2, g2) = _keys(parts)[:2]
        a, b = f"word/fonts/font{n1}.odttf", f"word/fonts/font{n2}.odttf"
        parts[a] = obfuscate(obfuscate(parts[b], g2), g1)       # face 2 under face 1's key
    before, after = L.docx_parts(blob), L.docx_parts(_rezip(blob, swap))
    assert [n for n in before if before[n] != after[n]] == ["word/fonts/font1.odttf"]


def test_timestamps_are_not_a_change():
    from tools import lock_downloads as L
    blob = _docx()

    def touch(parts):
        parts["docProps/core.xml"] += b"<!-- saved again -->"
        parts["docProps/app.xml"] += b"<!-- saved again -->"
    assert L.docx_parts(_rezip(blob, touch)) == L.docx_parts(blob)
