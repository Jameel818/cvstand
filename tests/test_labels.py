"""The label catalogue (phase 3 of the bilingual work).

WHAT THIS PROTECTS
    Before this, ~400 fixed strings were hardcoded across the 49 templates, so
    an Arabic resume rendered Arabic CONTENT under English HEADINGS. They now
    all go through `app.labels.t()`.

    The golden HTML gate proves the English output did not move. It cannot
    prove the other three things that have to stay true, which is what this
    file is for:

      * every msgid the templates pass has an Arabic string behind it,
      * no label got MISSED (a new template with a hardcoded heading would
        render English inside an Arabic document, silently),
      * nothing shadows the `t` global, which would turn `t('Tools')` into a
        call on a string.

    All three are the same failure shape this project keeps finding: output
    that is wrong rather than absent, with nothing raised.
"""
from __future__ import annotations

import ast
import collections
import json
import re
from pathlib import Path

import pytest

from app import labels as labels_mod
from app import registry
from app.labels import (
    _AR, _UI_AR, _as_html, _key, _MARKUP_MSGIDS, join_labels, reset_lang, set_lang,
    t, ui_t,
)
from app.rendering import canvas_html

ROOT = Path(__file__).resolve().parent.parent
TPL_DIR = ROOT / "app" / "templates" / "resumes"

COMMENT = re.compile(r"<!--.*?-->|\{#.*?#\}", re.S)
EXPR = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.S)
LIT = re.compile("\"([^\"]*)\"|'([^']*)'")
NODE = re.compile(r">([^<>]*?)<")
# `(?<![\w.])` matters: without it this also matches the `t(` at the end of
# `opts.get('name_css')`, and every macro option key is reported as an
# untranslated label.
T_CALL = re.compile(r"""(?<![\w.])t\(\s*(?:"([^"]*)"|'([^']*)')\s*\)""")
# Same guard, for asking "is the literal I just found already inside a t(...)".
IS_T_CALL = re.compile(r"(?<![\w.])t\(\s*$")
SENTINEL = "\x00"

# --- the dead-row scan's instruments ---------------------------------------
# Anchored on the call so that an apostrophe in prose cannot shift the quote
# pairing. Unlike T_CALL above these do NOT require a closing paren: the
# builder concatenates onto its error prefixes, as in
# `T("... (server error ") + res.status`.
T_CALL_OPEN = re.compile(r"""(?<![\w.])t\(\s*(?:"([^"]*)"|'([^']*)')""")
UI_T_CALL = re.compile(r"""\bui_t\(\s*(?:"([^"]*)"|'([^']*)')""")
JS_T_CALL = re.compile(r"""(?<![\w.])T\(\s*(?:"([^"]*)"|'([^']*)')""")
# Python joins adjacent literals, so a long msgid wrapped over two lines is
# not present verbatim anywhere. `app/auth.py:102` does exactly this, and
# without unwrapping it the scan reports a live string as dead.
_WRAP = re.compile(r"""["']\s*\n\s*["']""")


def _unwrap(src: str) -> str:
    return _WRAP.sub("", src)

# A static fragment is a label candidate if it is word-shaped.
#
# ACCENT-AWARE, and that is the whole point: the ASCII-only version of this
# pattern could not see any string containing "résumé", which is most of the
# shell's prose. It is the same trap as `grep -i resumecraft` failing to find
# `Résumé<b>Craft</b>` (NAMING.md section 3) -- an ASCII pattern aimed at text
# that is not ASCII -- and it was living inside the test written to catch
# exactly that class of miss.
#
# The two holes in the Latin-1 letter range are deliberate: U+00D7 MULTIPLY
# and U+00F7 DIVIDE are the only non-letters in it, and `builder.html` uses
# `×` as its close-button glyph. A single symbol is not a label; the button
# carries a real aria-label beside it.
LETTER = r"A-Za-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u024F"
WORDY = re.compile(rf"^[{LETTER}][{LETTER} .,:&'/-]*$")

# modern/t22.j2 spells "RESUME" as six separately-kerned <span> letters on a
# rotated rail. Arabic is cursive: six isolated glyphs are not a word, so this
# needs a layout change (phase 5), not a string swap. Excluded deliberately,
# and it is the ONLY exclusion - anything else the scan finds is a real miss.
EXCLUDED_NODES = {("modern/t22.j2", ch) for ch in "RESUM"}
# The interface language switcher. "EN" and "العربية" are autonyms -- a
# language names itself the same way whoever is reading -- which is the same
# convention builder.js uses for DOC_LANG_NAMES. Translating "EN" into Arabic
# would leave an Arabic reader no way to find English.
EXCLUDED_NODES |= {("base.html", "EN")}

# `{{ current_user['email'] }}` is a dict subscript, not a label, but "email"
# folds to a real catalogue key so the bare-literal scan flags it. The test
# below skips a literal whose quote is opened by `[`.
SUBSCRIPT = re.compile(r"\[\s*$")

# --- attribute-borne labels -------------------------------------------
# The scan above reads TEXT NODES and Jinja literals. A string can also
# reach a reader through an attribute, and that is a real hole rather
# than a theoretical one: `base.html`'s `<meta name="description">` was
# hardcoded English while the manifest's description was translated, and
# widening the glob did NOT catch it, because a meta description is not a
# text node. These are the attributes a human actually reads.
HUMAN_ATTRS = re.compile(
    r"""\b(content|placeholder|title|aria-label|alt)\s*=\s*"([^"]*)\""""
)
# Machine-readable `content=` values live on the same attribute name as
# the human-readable one, so they are excluded by the meta they belong
# to rather than by shape.
MACHINE_META = re.compile(
    r"""<meta[^>]*\bname\s*=\s*"(viewport|theme-color|color-scheme|robots)\""""
)
# Two words, at least one of them a real word. Accent-aware ON PURPOSE:
# `WORDY` above is ASCII-only, so every string containing "résumé" is
# invisible to it -- the same accent trap that hid the wordmark from
# `grep -i resumecraft` (NAMING.md section 3), living inside the test
# that is supposed to catch it.
ATTR_WORDY = re.compile(
    r"^[A-Za-z\u00C0-\u024F][A-Za-z\u00C0-\u024F0-9 .,:&'/()!?-]*$"
)
REAL_WORD = re.compile(r"[A-Za-z\u00C0-\u024F]{3,}")


# The app shell -- the header, footer, landing page, gallery, builder chrome
# and the account pages. It was outside this gate entirely until 2026-09-14,
# and not for the reason the plan assumed: the miss is not "wrong extension
# and wrong depth" but a wrong DIRECTORY. `TPL_DIR` is templates/resumes, and
# the shell sits in its PARENT. That is how `base.html`'s hardcoded English
# `<meta name="description">` survived every run of this file.
SHELL_DIR = TPL_DIR.parent


def _template_files():
    return (
        sorted(TPL_DIR.glob("*/*.j2"))
        + [TPL_DIR / "_macros.j2"]
        + sorted(SHELL_DIR.glob("*.html"))
    )


# The builder's form does not exist in any .j2 or .html file -- `builder.js`
# generates it in the browser. So `_template_files()` has never been able to
# see it, and five reader-visible English strings ("Remove" twice, "Bullet
# points", "+ Add bullet" and the "+ Add <thing>" verb) sat there in English
# through every run of this file, shown to Arabic readers for eight sessions.
def _script_files():
    return sorted(ROOT.joinpath("app", "static", "js").glob("*.js"))


#: A JS template literal, which is where this file builds its HTML.
TEMPLATE_LITERAL = re.compile(r"`([^`]*)`", re.S)
#: `${...}` inside one. Replaced with SENTINEL for the same reason Jinja
#: expressions are: blanking would fuse the text on either side into a run
#: that is not in the file.
INTERP = re.compile(r"\$\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.S)
JS_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)


def _rel(f: Path) -> str:
    if f.parent == SHELL_DIR:
        return f.name
    return f"{f.parent.name}/{f.name}" if f.parent.name != "resumes" else f.name


def _msgids(files) -> dict[str, list[str]]:
    """Every string these templates pass to t(), and where."""
    found: dict[str, list[str]] = collections.defaultdict(list)
    for f in files:
        src = f.read_text(encoding="utf-8")
        for m in T_CALL.finditer(src):
            found[m.group(1) if m.group(1) is not None else m.group(2)].append(_rel(f))
    return found


# `t` IS TWO DIFFERENT FUNCTIONS, and which one you get depends on which
# template you are in. This is the fact that makes one flat msgid list wrong:
#
#   * In the resume templates it is `labels.t`, which reads `_AR` and follows
#     the DOCUMENT's language (set_lang / reset_lang).
#   * In the app shell it is `i18n.register`'s lambda, which is
#     `ui_t(s, lang)` -- it reads `_UI_AR` first, falls back to `_AR`, and
#     follows the READER's ui_lang cookie.
#
# The two catalogues are also cased differently (`_UI_AR` holds the string as
# written, `_AR` holds it folded -- labels.py:551), so a shell msgid checked
# against `_AR` reports as missing while rendering perfectly. Before the split
# below, widening the glob failed 2 tests for exactly that reason and neither
# failure was a real defect.
RESUME_FILES = sorted(TPL_DIR.glob("*/*.j2")) + [TPL_DIR / "_macros.j2"]
SHELL_FILES = sorted(SHELL_DIR.glob("*.html"))

MSGIDS = _msgids(RESUME_FILES)
SHELL_MSGIDS = _msgids(SHELL_FILES)


def test_the_templates_actually_use_the_catalogue():
    """A guard on the guards: if the scan finds nothing, every other test here
    passes vacuously."""
    assert len(MSGIDS) >= 60, f"only {len(MSGIDS)} distinct msgids found"
    assert sum(len(v) for v in MSGIDS.values()) >= 350
    # The shell was outside this file entirely until 2026-09-14. These numbers
    # are what it actually carries, so a future refactor that quietly drops
    # the shell out of the scan again fails here instead of going unnoticed.
    assert len(SHELL_MSGIDS) >= 100, f"only {len(SHELL_MSGIDS)} shell msgids"
    assert len(SHELL_FILES) >= 5, f"only {len(SHELL_FILES)} shell templates"


def test_english_returns_the_msgid_verbatim():
    """The whole English-safety argument: t() is the identity in English.

    This is what makes the golden gate's byte-identity cheap to trust - there
    is no English table that could be wrong, so no English string can drift.
    """
    for msgid in MSGIDS:
        assert t(msgid) == msgid, msgid
    # `ui_t` returns Markup and escapes `&`, `<`, `>` and `"` on the way out
    # (labels.py:509 -- deliberately NOT the apostrophe, so "it's free" keeps
    # its bytes). So the shell's identity property is "the escaped msgid", not
    # the msgid: `Modern & ATS-friendly` comes back `Modern &amp; ATS-friendly`.
    # Still the same claim -- there is no English table that could drift.
    for msgid in SHELL_MSGIDS:
        assert ui_t(msgid, "en") == _as_html(msgid), msgid


def test_every_msgid_has_an_arabic_translation():
    missing = sorted(m for m in MSGIDS if _key(m) not in _AR)
    assert not missing, (
        "labels with no Arabic string (they would render English inside an "
        f"Arabic resume): {[(m, MSGIDS[m][:2]) for m in missing]}"
    )


def test_every_shell_msgid_has_an_arabic_translation():
    """The same coverage question for the app shell, against the catalogue the
    shell actually reads. `ui_t` resolves `_UI_AR` first and `_AR` second."""
    missing = sorted(
        m for m in SHELL_MSGIDS
        if m not in _UI_AR and _key(m) not in _UI_AR and _key(m) not in _AR
    )
    assert not missing, (
        "shell labels with no Arabic string (they would render English inside "
        f"an Arabic interface): {[(m, SHELL_MSGIDS[m][:2]) for m in missing]}"
    )


def test_the_catalogue_has_no_dead_rows():
    """The reverse of the test above, which only ever checked one direction.

    A row nothing renders is invisible to every other gate here, so a string
    deleted from a template leaves its translation behind forever. That is how
    `"Résumé Builder"` outlived the page that used it, and how four rows from
    the server-side template switcher survived the move to localStorage.

    TWO SCANS, AND A ROW IS ONLY DEAD IF BOTH MISS IT
        Neither scan is sound alone, and each is unsound in a different place,
        so the union is the honest test:

        * The CALL scan is anchored on `t(` / `ui_t(` / the builder's `T(`,
          which makes it immune to the apostrophe drift that wrecks a naive
          quote scan -- one `don't` in prose and every following pair is
          shifted. It misses strings composed at runtime (the auth errors are
          returned through variables, and `builder.js` concatenates a status
          code onto its error prefixes).
        * The TEXT scan is a plain substring sweep, which sees those. It in
          turn misses nothing that is present verbatim, but a literal wrapped
          across two source lines by Python's implicit concatenation is not
          verbatim -- hence `_unwrap`.

        A row absent from both is one no reader can reach. Weaker than a
        runtime instrument (which would mean driving every error path), but it
        does not cry wolf, and it caught four real rows on the day it landed.

    WHY NOT SCAN `t(...)` CALLS ALONE
        The catalogue has a second consumer: the builder pulls
        `ui_catalogue(lang)` into JavaScript and looks rows up by folded key
        (`labels.py:543`), so a row can be live without any `t()` naming it.
    """
    roots = [
        *ROOT.joinpath("app", "templates").glob("*.html"),
        *TPL_DIR.glob("*/*.j2"),
        *TPL_DIR.glob("*.j2"),
        *ROOT.joinpath("app").rglob("*.py"),
        *ROOT.joinpath("app", "static", "js").glob("*.js"),
    ]
    # labels.py DEFINES the rows, so leaving it in makes every key match
    # itself and the whole test pass vacuously. Caught by mutation: a row
    # named "Zombie Row Nothing Renders" was accepted before this line.
    roots = [f for f in roots if f.name != "labels.py"]

    called: set[str] = set()
    texts: list[str] = []
    for f in roots:
        src = f.read_text(encoding="utf-8")
        texts.append(_unwrap(src))
        for pat in (T_CALL_OPEN, UI_T_CALL, JS_T_CALL):
            for m in pat.finditer(src):
                lit = m.group(1) if m.group(1) is not None else m.group(2)
                if lit:
                    called.add(_key(lit))
    blob = chr(10).join(texts)

    dead = sorted(
        k for cat in (_AR, _UI_AR) for k in cat
        if _key(k) not in called and k not in blob
    )
    assert not dead, (
        "catalogue rows nothing can reach - delete them, or the next reader "
        f"maintains a translation for a page that no longer exists: {dead}"
    )


def test_no_catalogue_key_is_defined_twice():
    """A dict literal accepts a repeated key and keeps the LAST silently.

    Both catalogues are long, hand-maintained and grouped by page, so the same
    string is easy to add twice under two headings. Python reports nothing; the
    row that renders is simply whichever sits lower in the file.

    That is not theoretical. `Modern` was defined twice and `ATS-Friendly`
    three times, and the third said "أنظمة التتبع" where the other two said
    "أنظمة التوظيف" -- one term for ATS on the landing page and a different one
    on the gallery cards, decided by line number.

    Has to be read from the SOURCE: by the time the module is imported the
    duplicate has already collapsed and is unrecoverable.
    """
    tree = ast.parse(Path(labels_mod.__file__).read_text(encoding="utf-8"))
    dupes = []
    for node in ast.walk(tree):
        value = getattr(node, "value", None)
        if not isinstance(value, ast.Dict):
            continue
        target = node.targets[0] if isinstance(node, ast.Assign) else getattr(node, "target", None)
        name = getattr(target, "id", None)
        if name not in ("_AR", "_UI_AR"):
            continue
        seen: dict[str, int] = {}
        for k in value.keys:
            if not isinstance(k, ast.Constant) or not isinstance(k.value, str):
                continue
            if k.value in seen:
                dupes.append(f"{name}[{k.value!r}] at lines {seen[k.value]} and {k.lineno}")
            seen[k.value] = k.lineno
    assert not dupes, (
        "a catalogue key is defined twice - the lower one wins silently:\n  "
        + "\n  ".join(dupes)
    )


def test_arabic_differs_from_english_for_every_msgid():
    """A catalogue row that accidentally holds the English text would pass the
    coverage test above and still render an English heading."""
    token = set_lang("ar")
    try:
        same = sorted(m for m in MSGIDS if t(m) == m)
    finally:
        reset_lang(token)
    assert not same, f"msgids whose 'Arabic' is still the English string: {same}"


# Strings that are deliberately identical in both scripts. "PDF" is a file
# format, not a word; Arabic writes it Latin. Anything else here needs a
# reason written beside it.
SAME_IN_BOTH_SCRIPTS = {"PDF"}


def test_arabic_differs_from_english_for_every_shell_msgid():
    same = sorted(
        m for m in SHELL_MSGIDS
        if ui_t(m, "ar") == _as_html(m) and m not in SAME_IN_BOTH_SCRIPTS
    )
    assert not same, (
        f"shell msgids whose 'Arabic' is still the English string: {same}"
    )


def test_no_label_is_still_hardcoded():
    """The miss detector.

    Two shapes, because the templates use two: a bare text node
    (`<div>Experience</div>`) and a bare string literal passed to a heading
    helper (`{{ dh("Experience") }}`). The second is how 15 ATS templates write
    theirs, and a text-node scan alone does not see it.
    """
    findings = []
    for f in _template_files():
        rel = _rel(f)
        src = f.read_text(encoding="utf-8")
        blanked = COMMENT.sub(lambda m: " " * len(m.group(0)), src)

        # Replace each Jinja expression with a SENTINEL rather than blanking it
        # to spaces: blanking merges the static text on either side into one
        # run and invents strings that are not in the file.
        for m in NODE.finditer(EXPR.sub(SENTINEL, blanked)):
            for frag in m.group(1).split(SENTINEL):
                frag = frag.replace("&nbsp;", " ").strip()
                if frag and WORDY.match(frag) and (rel, frag) not in EXCLUDED_NODES:
                    findings.append(f"{rel}: text node {frag!r}")

        for m in EXPR.finditer(blanked):
            seg = m.group(0)
            for lm in LIT.finditer(seg):
                s = lm.group(1) if lm.group(1) is not None else lm.group(2)
                before = seg[:lm.start()]
                if (s and _key(s) in _AR and not IS_T_CALL.search(before)
                        and not SUBSCRIPT.search(before)):
                    line = src.count("\n", 0, m.start()) + 1
                    findings.append(f"{rel}:{line}: bare literal {s!r}")

    assert not findings, (
        "labels not routed through t() - these render English inside an "
        "Arabic resume:\n  " + "\n  ".join(findings)
    )


def test_no_label_is_hardcoded_in_the_generated_form():
    """The third shape: an English text node inside a JS template literal.

    `test_no_label_is_still_hardcoded` walks `_template_files()`, which is
    Jinja and HTML only. The builder's entire form is assembled in
    `builder.js`, so that gate could never reach it -- and did not, while five
    English strings shipped to Arabic readers.

    Deliberately narrower than the Jinja scan: it flags only a text node whose
    folded key IS in a catalogue. A JS file is full of prose that is not a
    label (comments are stripped, but selectors, class names and console text
    are not), and a gate that cries wolf gets its findings pasted into an
    exclusion list until it means nothing.
    """
    findings = []
    for f in _script_files():
        rel = f.name
        src = f.read_text(encoding="utf-8")
        blanked = JS_COMMENT.sub(lambda m: " " * len(m.group(0)), src)
        for lit in TEMPLATE_LITERAL.finditer(blanked):
            body = INTERP.sub(SENTINEL, lit.group(1))
            for m in NODE.finditer(body):
                for frag in m.group(1).split(SENTINEL):
                    frag = frag.replace("&nbsp;", " ").strip()
                    # `WORDY` requires a leading LETTER, so the add buttons
                    # ("+ Add bullet") slipped past it while the two beside
                    # them were caught. Found by mutation, not by reading.
                    probe = frag[1:].strip() if frag.startswith("+") else frag
                    if not probe or not WORDY.match(probe):
                        continue
                    if _key(frag) in _AR or frag in _UI_AR:
                        line = src.count(chr(10), 0, lit.start()) + 1
                        findings.append(f"{rel}:{line}: text node {frag!r}")
    assert not findings, (
        "labels hardcoded in generated markup - these stay English in an "
        "Arabic interface, and no .j2 scan can see them:" + chr(10) + "  "
        + (chr(10) + "  ").join(findings)
    )


def test_no_label_hides_in_an_attribute():
    """The other half of the miss detector.

    `test_no_label_is_still_hardcoded` reads text nodes and Jinja literals, so
    a string that reaches the reader through an attribute is invisible to it.
    That is not hypothetical: it is exactly how `base.html`'s meta description
    shipped hardcoded English to Arabic readers while the manifest's
    description (routes.py:387) was correctly translated. Widening the glob
    did not catch it either -- a meta description is not a text node.
    """
    findings = []
    for f in _template_files():
        rel = _rel(f)
        src = f.read_text(encoding="utf-8")
        blanked = COMMENT.sub(lambda m: " " * len(m.group(0)), src)
        for m in HUMAN_ATTRS.finditer(blanked):
            value = m.group(2).strip()
            tag_start = blanked.rfind("<", 0, m.start())
            tag = blanked[tag_start:m.end()]
            if MACHINE_META.search(tag):
                continue
            if not value or "{{" in value or "{%" in value:
                continue
            if ATTR_WORDY.match(value) and REAL_WORD.search(value):
                line = src.count(chr(10), 0, m.start()) + 1
                findings.append(f"{rel}:{line}: {m.group(1)}={value!r}")
    assert not findings, (
        "reader-visible text sitting in an attribute, never routed through "
        "t() - these stay English in an Arabic interface:" + chr(10) + "  "
        + (chr(10) + "  ").join(findings)
    )


def test_no_template_shadows_the_t_global():
    """`{% for t in r.tools %}` or `{% macro head(t) %}` rebinds `t` to a
    string, so a `t('Tools')` in that scope raises "str object is not
    callable". Ten sites did this before phase 3; `ats/t5.j2` had a label and a
    shadowing loop on the SAME line and survived only because the label
    happened to sit before the loop opened.
    """
    patterns = [
        re.compile(r"\{%\s*for\s+t\s+in\b"),
        re.compile(r"\{%\s*set\s+t\s*="),
        re.compile(r"\{%\s*macro\s+\w+\([^)]*\bt\b\s*[,)]"),
    ]
    offenders = [
        f"{_rel(f)}:{src.count(chr(10), 0, m.start()) + 1}"
        for f in _template_files()
        for src in [f.read_text(encoding="utf-8")]
        for p in patterns
        for m in p.finditer(src)
    ]
    assert not offenders, f"templates binding a local named 't': {offenders}"


ARABIC_SAMPLE = json.loads(
    (ROOT / "data" / "sample_resume_ar.json").read_text(encoding="utf-8")
)

# The headings a reader would notice immediately if they stayed English.
ENGLISH_LABEL = re.compile(
    r"\b(Experience|EXPERIENCE|Skills|SKILLS|Education|EDUCATION|Summary|SUMMARY"
    r"|Tools|TOOLS|Languages|LANGUAGES|Contact|CONTACT|Certifications"
    r"|CERTIFICATIONS|GPA|Recognition|References|Portfolio|Profile)\b"
)


@pytest.mark.parametrize("key", registry.ported_keys())
def test_arabic_render_emits_no_english_label(key: str):
    html = canvas_html(ARABIC_SAMPLE, key)
    text = re.sub(r"<[^>]+>", " ", html)
    leaked = sorted(set(ENGLISH_LABEL.findall(text)))
    assert not leaked, f"{key} still shows English labels in an Arabic resume: {leaked}"


def test_join_labels_reproduces_the_english_the_templates_wrote():
    """Three ATS templates compose a trailing heading from a list. Their
    English forms differ - ats/t4 joins with the word "and" where ats/t12 and
    ats/t14 use "&" - and both have to survive verbatim.
    """
    assert join_labels(["Certifications", "Tools", "Languages"]) == \
        "Certifications, Tools & Languages"
    assert join_labels(["Recognition", "Education", "Languages"], "and") == \
        "Recognition, Education and Languages"
    assert join_labels(["Tools", "Languages"]) == "Tools & Languages"
    assert join_labels(["Tools"]) == "Tools"
    assert join_labels([]) == ""
    assert join_labels(["Tools", "", "Languages"]) == "Tools & Languages"


def test_join_labels_translates_the_punctuation_too():
    """Arabic joins with an Arabic comma and "و". Translating only the WORDS
    would leave a heading in two scripts.
    """
    token = set_lang("ar")
    try:
        joined = join_labels([t("Certifications"), t("Tools"), t("Languages")])
    finally:
        reset_lang(token)
    assert "،" in joined, "expected an Arabic comma"
    assert " و " in joined, "expected the Arabic conjunction"
    assert "&" not in joined and "," not in joined


def test_markup_labels_keep_their_line_break():
    """Three headings carry a <br> INSIDE the phrase. They cannot be two t()
    calls - Arabic puts the break elsewhere - so t() returns Markup for them
    and autoescape must not turn the tag into visible text.
    """
    assert _MARKUP_MSGIDS
    for msgid in MSGIDS:
        if _key(msgid) in _MARKUP_MSGIDS:
            assert hasattr(t(msgid), "__html__"), f"{msgid} would be escaped"
    assert "&lt;br&gt;" not in canvas_html({"name": "A", "title": "B"}, "modern-t15")


def test_lookup_folds_case_and_whitespace():
    """Arabic has no case, so the templates' ~40 casing variants share one row."""
    token = set_lang("ar")
    try:
        assert t("SKILLS") == t("Skills") == t("skills")
        assert t("Work  Experience") == t("Work Experience")
    finally:
        reset_lang(token)


def test_an_untranslated_msgid_renders_english_and_never_raises():
    """A resume must not 500 because a label was not translated - the same rule
    that produced normalize()'s degrade paths. Coverage is a TEST failure
    (above), not a render failure.
    """
    token = set_lang("ar")
    try:
        assert t("Nonexistent Heading") == "Nonexistent Heading"
    finally:
        reset_lang(token)


def test_a_failed_render_does_not_leave_the_language_set(monkeypatch):
    """canvas_html() resets the language in a `finally`. Without it, one
    template raising would leave every LATER render in this thread Arabic -
    a whole English resume silently relabelled.

    The failure has to happen INSIDE the try. An unknown template key does not
    work: `_template_path()` raises before `set_lang()` is ever called, so that
    version of this test passed with the `finally` deleted. `normalize()` is
    evaluated as an argument to `tpl.render()`, which is inside it.
    """
    import app.rendering as rendering

    def boom(_data):
        raise RuntimeError("normalize exploded mid-render")

    monkeypatch.setattr(rendering, "normalize", boom)
    with pytest.raises(RuntimeError):
        canvas_html({"name": "A", "title": "B", "lang": "ar"}, "modern-t1")
    assert t("Skills") == "Skills", "the language leaked out of a failed render"


def test_the_gpa_prefix_is_translated():
    """`GPA <value>` appears in 32 templates and is NOT a heading, so no
    heading-shaped scan found it. Neither golden scenario set a gpa either,
    which is why the `gpa` scenario was added to tools/golden.py.
    """
    data = dict(ARABIC_SAMPLE)
    data["education"] = [dict(e, gpa="3.8") for e in ARABIC_SAMPLE.get("education", [])]
    assert data["education"], "the Arabic sample has no education entries to test"
    html = canvas_html(data, "ats-t3")
    assert "GPA 3.8" not in html
    assert _AR["gpa"] in html
