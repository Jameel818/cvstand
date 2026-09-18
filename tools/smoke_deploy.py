"""Smoke-test a DEPLOYED CVStand against DEPLOY.md's Phase C6 checklist.

    venv/Scripts/python tools/smoke_deploy.py https://xxxx.up.railway.app

Stdlib only, on purpose: this is the one script that may need to run somewhere
that is not this venv, and a deploy check that first needs its own install is a
deploy check nobody runs.

WHY THIS EXISTS RATHER THAN THE MANUAL LIST
    C6 says "Download PDF" and a human reading that clicks the button on the
    builder page. That is the right instinct and the wrong test, because the
    interesting failure is server-side and has a friendly-looking front:

      * With CVSTAND_SERVER_STORE=0, `GET /export/pdf` does NOT render anything.
        `_export_subject()` raises `_ExportNeedsPost` and the route answers 405
        with `Allow: POST`. Anyone smoke-testing by pasting /export/pdf into the
        address bar gets a tidy JSON refusal, sees no traceback, and concludes
        the export works. Chromium was never launched. Only a POST carrying the
        document in the body reaches `render_pdf`.

      * A 200 is not enough either. A Chromium that failed to start can still
        produce an error page rendered to a perfectly valid, perfectly empty
        PDF. So the PDF check asserts the magic bytes AND a floor on the size.

    The C6 items a script genuinely cannot judge -- "the preview updates as you
    type", "the Arabic reads correctly" -- are printed at the end as the short
    list of things still left for your eyes.

EXIT CODE
    Set, but do not trust it alone. This project has a four-session history of
    a green exit code over a red run (see RESUME_HERE.md). Read the VERDICT.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "data" / "sample_resume.json"

TIMEOUT = 180  # A cold container plus a Chromium launch is genuinely slow.

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  -- ' + detail if detail else ''}")
    return ok


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Make urlopen surface a 3xx instead of quietly following it.

    urllib follows redirects by default, which cost this script two false
    failures the first time it ran: the /lang/ar check saw the FINAL 200 and
    the landing page's headers, so both the status assertion and the
    Set-Cookie assertion failed against an app that was behaving perfectly.
    Returning None here turns the 3xx into an HTTPError, which `fetch` already
    unpacks into a normal (status, headers, body) triple.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirect)


def fetch(url: str, *, method: str = "GET", body: dict | None = None,
          headers: dict | None = None, follow: bool = True):
    """Return (status, headers, bytes). Never raises on an HTTP error status."""
    data = json.dumps(body).encode() if body is not None else None
    hdrs = {"User-Agent": "cvstand-smoke/1"}
    if data is not None:
        hdrs["Content-Type"] = "application/json"
    hdrs.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    opener = urllib.request.urlopen if follow else _NO_REDIRECT_OPENER.open
    try:
        with opener(req, timeout=TIMEOUT) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def main(base: str) -> int:
    base = base.rstrip("/")
    if not base.startswith("http"):
        base = "https://" + base
    print(f"\nSmoke-testing {base}\n")

    # ---- the app is up and is branded -------------------------------------
    print("Landing")
    status, _, raw = fetch(base + "/")
    html = raw.decode("utf-8", "replace")
    check("GET / is 200", status == 200, f"got {status}")
    check("wordmark reads CVStand", "CVStand" in html)
    check("footer carries info@cvstand.com", "info@cvstand.com" in html)
    check("no stale ResumeCraft anywhere", "ResumeCraft" not in html,
          "rename leaked" if "ResumeCraft" in html else "")

    # ---- all 49 templates survived the image ------------------------------
    print("\nTemplates")
    status, _, raw = fetch(base + "/templates")
    page = raw.decode("utf-8", "replace")
    check("GET /templates is 200", status == 200, f"got {status}")
    try:
        sys.path.insert(0, str(ROOT))
        from app import registry
        keys = registry.ported_keys()
        present = [k for k in keys if k in page]
        check(f"all {len(keys)} ported templates render",
              len(present) == len(keys),
              f"{len(present)}/{len(keys)} found")
    except Exception as exc:  # running detached from the repo is fine
        check("template count (skipped -- no local repo)", True, str(exc)[:60])

    # ---- the Arabic interface -------------------------------------------—
    print("\nArabic interface")
    status, hdrs, _ = fetch(base + "/lang/ar?next=/", follow=False)
    cookie = hdrs.get("Set-Cookie", "")
    check("GET /lang/ar redirects", status in (301, 302), f"got {status}")
    check("sets the ui_lang cookie", "ui_lang=ar" in cookie, cookie[:60])
    _, _, raw = fetch(base + "/", headers={"Cookie": "ui_lang=ar"})
    ar = raw.decode("utf-8", "replace")
    check('landing flips to dir="rtl"', 'dir="rtl"' in ar)
    check("landing renders Arabic script",
          any("؀" <= ch <= "ۿ" for ch in ar))

    # ---- is the DEPLOYED build actually the current one? ------------------
    #
    # Everything above passes against a container built from any commit, so
    # the whole script stayed green while the running image was eight commits
    # behind and served 49 English template names to Arabic readers. A local
    # check cannot see that: localhost is always current, which is exactly why
    # it was mistaken for proof about the live site.
    #
    # These two are staleness detectors, not feature tests. They read the same
    # two surfaces from the DEPLOYED origin and fail when the image predates
    # the work, which is a deploy problem wearing a translation costume.
    print("\nDeployed build is current (staleness, not features)")
    _, _, raw = fetch(base + "/templates", headers={"Cookie": "ui_lang=ar"})
    gallery = raw.decode("utf-8", "replace")
    names = re.findall(r"<h3>([^<]*)</h3>", gallery)
    latin = [n for n in names if re.search(r"[A-Za-z]{2,}", n)]
    check("template names are translated",
          bool(names) and not latin,
          f"{len(latin)} of {len(names)} still Latin, e.g. {latin[:3]}"
          if latin else f"all {len(names)} in Arabic")

    # The form is generated in the browser, so its labels ship inside the JS
    # rather than in any rendered page. A stale asset here means an Arabic
    # user gets an Arabic page with English buttons on it.
    _, _, raw = fetch(base + "/static/js/builder.js")
    js = raw.decode("utf-8", "replace")
    check("builder.js carries its labels through T()",
          'T("Bullet points")' in js,
          "" if 'T("Bullet points")' in js
          else "stale asset -- form buttons stay English in Arabic")

    # ---- the multi-visitor switch, on BOTH routes that honour it ----------
    print("\nCVSTAND_SERVER_STORE=0  (two visitors must not share one document)")
    status, _, _ = fetch(base + "/api/resume", method="PUT", body={})
    check("PUT /api/resume is 403", status == 403,
          f"got {status} -- server is storing ONE resume for everyone"
          if status != 403 else "")
    status, hdrs, _ = fetch(base + "/export/pdf")
    check("GET /export/pdf is 405", status == 405, f"got {status}")
    # Case-INSENSITIVE, because HTTP header names are. Railway's edge
    # (`Server: railway-hikari`) hands them back lowercased, HTTP/2 style, so
    # `hdrs.get("Allow")` found nothing and this reported "no Allow header"
    # against a deployment that was sending `allow: POST` correctly. A check
    # that fails on a healthy service is worse than no check: it trains the
    # reader to discount the whole report.
    allow = next((v for k, v in hdrs.items() if k.lower() == "allow"), "")
    check("  ...and says Allow: POST", "POST" in allow,
          allow or "no Allow header")

    # ---- Chromium. the one most likely to fail in a container ------------
    print("\nPDF export  (launches a real Chromium -- the top deploy risk)")
    if not SAMPLE.exists():
        check("sample resume available", False, f"missing {SAMPLE}")
        return report()
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    t0 = time.time()
    status, hdrs, pdf = fetch(base + "/export/pdf", method="POST",
                              body={"data": sample})
    secs = time.time() - t0
    check("POST /export/pdf is 200", status == 200,
          f"got {status}: {pdf[:200].decode('utf-8', 'replace')}"
          if status != 200 else f"{secs:.1f}s")
    if status == 200:
        check("content-type is application/pdf",
              "application/pdf" in (hdrs.get("Content-Type") or ""),
              hdrs.get("Content-Type") or "")
        check("body is a real PDF (%PDF magic)", pdf[:4] == b"%PDF",
              repr(pdf[:16]))
        # A Chromium that failed to start can still render an error page to a
        # structurally valid PDF. A one-page resume is tens of KB.
        check("PDF is not a near-empty error page", len(pdf) > 15_000,
              f"{len(pdf):,} bytes")

    # ---- Word export -----------------------------------------------------
    print("\nWord export")
    status, hdrs, docx = fetch(base + "/export/docx", method="POST",
                               body={"data": sample})
    check("POST /export/docx is 200", status == 200, f"got {status}")
    if status == 200:
        check("body is a real .docx (PK zip magic)", docx[:2] == b"PK",
              repr(docx[:8]))

    # ---- PWA surfaces ----------------------------------------------------
    print("\nPWA")
    status, _, raw = fetch(base + "/manifest.webmanifest")
    check("GET /manifest.webmanifest is 200", status == 200, f"got {status}")
    if status == 200:
        try:
            check('manifest name is "CVStand"',
                  json.loads(raw).get("name") == "CVStand",
                  json.loads(raw).get("name", "?"))
        except json.JSONDecodeError:
            check("manifest is valid JSON", False, raw[:80].decode("utf-8", "replace"))
    status, _, _ = fetch(base + "/sw.js")
    check("GET /sw.js is 200", status == 200, f"got {status}")

    status, _, _ = fetch(base + "/builder")
    check("GET /builder is 200", status == 200, f"got {status}")

    return report()


def report() -> int:
    failed = [(n, d) for n, ok, d in results if not ok]
    print("\n" + "=" * 66)
    if failed:
        print(f"VERDICT: {len(failed)} FAILED of {len(results)}")
        for name, detail in failed:
            print(f"  - {name}{'  -- ' + detail if detail else ''}")
    else:
        print(f"VERDICT: all {len(results)} checks passed")
    print("=" * 66)
    print("""
STILL YOURS TO EYEBALL -- a script cannot judge these:
  - /builder: type a name, confirm the preview updates as you type
  - the Arabic pages actually read correctly, not merely right-to-left
  - open it on a PHONE (the 2026-09-14 bug was invisible above 900px)

AND THE ONE THAT NEEDS A REDEPLOY:
  - sign up, redeploy from the Railway dashboard, sign in again.
    Success proves the /data volume is really mounted. If the account is
    gone, the volume is not mounted and every deploy is deleting every
    user -- silently, with no error anywhere.
""")
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
