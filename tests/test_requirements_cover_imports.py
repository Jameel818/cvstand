"""Every package app/ imports must be installed by requirements.txt.

WHY THIS FILE EXISTS
    The Docker image installs requirements.txt and nothing else. This venv
    holds more than that (the font build tools, for one), so a test run here
    cannot notice a runtime import the image lacks. That shipped once:
    app/exporters/docx_font_embed.py imports fontTools, which was missing from
    requirements.txt, and every Word download on the live site answered 500
    (2026-09-28) while the full suite passed.

WHAT IT CHECKS
    Every top-level, non-stdlib import anywhere under app/ -- including the
    ones inside functions, which is where fontTools was -- must belong to a
    distribution that requirements.txt pins, or that one of those pins
    requires (transitively, extras excluded). lxml arrives with python-docx,
    jinja2 with Flask: that is what pip will install in the image too.
"""
from __future__ import annotations

import ast
import re
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _pinned() -> set[str]:
    out = set()
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line and not line.startswith("-"):
            out.add(_norm(re.split(r"[\s<>=!~;\[]", line, maxsplit=1)[0]))
    return out


def _closure(names: set[str]) -> set[str]:
    """The distributions pip installs for `names`, extras left out."""
    seen, todo = set(), list(names)
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        try:
            requires = metadata.requires(name) or []
        except metadata.PackageNotFoundError:
            continue
        for req in requires:
            if "extra ==" in req.replace('"', "").replace("'", ""):
                continue
            todo.append(_norm(re.split(r"[\s<>=!~;\[(]", req, maxsplit=1)[0]))
    return seen


def _imports() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for path in (ROOT / "app").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                top = name.split(".")[0]
                if top != "app" and top not in sys.stdlib_module_names:
                    found.setdefault(top, set()).add(str(path.relative_to(ROOT)))
    return found


def test_every_app_import_is_installed_by_requirements_txt():
    installed = _closure(_pinned())
    owners = metadata.packages_distributions()
    missing = []
    for module, files in sorted(_imports().items()):
        dists = {_norm(d) for d in owners.get(module, [])}
        if not dists:
            missing.append(f"{module} (not installed here either) <- {sorted(files)}")
        elif not dists & installed:
            missing.append(f"{module} (from {sorted(dists)}) <- {sorted(files)}")
    assert not missing, "requirements.txt does not install:\n  " + "\n  ".join(missing)


def test_the_check_sees_imports_inside_functions():
    # fontTools is imported inside a function; a module-level-only scan
    # would have passed the broken requirements.txt.
    assert "fontTools" in _imports()


def test_the_check_would_have_caught_the_missing_fonttools():
    assert "fonttools" not in _closure(_pinned() - {"fonttools"})
