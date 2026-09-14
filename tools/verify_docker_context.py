"""Does .dockerignore exclude anything the running app needs?

WHY THIS EXISTS
    A .dockerignore mistake does not fail the build. It produces an image that
    starts fine and then 500s the first time someone exports a .docx, or
    renders every résumé in a fallback font because `app/static/fonts/` never
    made it in. The failure is at runtime, on a user, in production.

    `data/` is the sharp edge: it holds local state (the working résumé, the
    accounts database) AND shipped content (the two showcase samples the
    landing hero renders). Excluding the directory wholesale is the obvious
    move and it is wrong.

    Run:  venv/Scripts/python tools/verify_docker_context.py
"""
from __future__ import annotations

import fnmatch
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Everything the container must be able to open. Derived from app/config.py
# and the exporters, not guessed.
REQUIRED_GLOBS = [
    "requirements.txt",
    "Dockerfile",
    "app/*.py",
    "app/exporters/*.py",
    "app/templates/*.html",
    "app/templates/resumes/_macros.j2",
    "app/templates/resumes/*/*.j2",
    "app/static/css/app.css",
    "app/static/js/*.js",
    "app/static/fonts/fonts.css",
    "app/static/fonts/*.woff2",
    "app/static/icons/*.png",
    # The showcase samples the landing hero and gallery cards render.
    "data/sample_resume.json",
    "data/sample_resume_ar.json",
    # The DOCX export's master documents (app/config.py::WORD_MASTERS_DIR).
    "word_masters/*.docx",
]

# Paths that MUST NOT ship: local state and developer material.
FORBIDDEN_GLOBS = [
    "data/resume.json",
    "data/*.db",
    "tests/*.py",
    "venv/*",
]


def _rules(path: Path) -> list[tuple[str, bool]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        negated = line.startswith("!")
        out.append((line[1:] if negated else line, negated))
    return out


def ignored(rel: str, rules) -> bool:
    """Docker semantics: last matching rule wins, `!` re-includes."""
    state = False
    for pattern, negated in rules:
        pat = pattern.rstrip("/")
        hit = (
            fnmatch.fnmatch(rel, pat)
            or fnmatch.fnmatch(rel, pat + "/*")
            or any(fnmatch.fnmatch(part, pat) for part in rel.split("/")[:-1])
            or fnmatch.fnmatch(rel, pat.replace("**/", ""))
        )
        if hit:
            state = not negated
    return state


def main() -> int:
    rules = _rules(ROOT / ".dockerignore")
    missing, leaked = [], []

    for pattern in REQUIRED_GLOBS:
        matches = sorted(ROOT.glob(pattern))
        if not matches:
            missing.append(f"{pattern} -- matches NOTHING on disk")
            continue
        for f in matches:
            rel = f.relative_to(ROOT).as_posix()
            if ignored(rel, rules):
                missing.append(f"{rel} (via {pattern})")

    for pattern in FORBIDDEN_GLOBS:
        for f in sorted(ROOT.glob(pattern)):
            rel = f.relative_to(ROOT).as_posix()
            if not ignored(rel, rules):
                leaked.append(rel)

    for label, items in (("EXCLUDED BUT NEEDED", missing),
                         ("SHIPPED BUT SHOULD NOT BE", leaked)):
        if items:
            print(f"--- {label}: {len(items)}")
            for i in items[:20]:
                print("   ", i)
            if len(items) > 20:
                print(f"    ... and {len(items) - 20} more")

    if not missing and not leaked:
        kept = sum(len(list(ROOT.glob(p))) for p in REQUIRED_GLOBS)
        print(f"OK - {kept} required files survive .dockerignore; "
              f"no local state ships")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
