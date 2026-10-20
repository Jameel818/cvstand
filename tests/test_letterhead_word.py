"""The cover letter's letterhead in Word IS the CV's header (user,
2026-10-20), for every template, English and Arabic:

    NAME        the name's run: size, face, bold - identical to the CV's (an
                Arabic CV that took a type step to fit its page drew its name
                3-11% smaller than an unfitted letter did)
    PAGE        the letter's page: size, margins, header distance - the CV's
    POSITION    everything above the name - and the name's own paragraph -
                spaced exactly as on the CV, so the name stands at the same
                height; an ATS letter's whole letterhead (every paragraph up to
                the body) is the CV's own
    NO STRIP    in "CV + letter", the letter's page header takes no room: its
                default paragraph (a line tall) pushed the whole letter down -
                the white strip over the letterhead the user saw in all 49

What Word actually DRAWS is checked in real Word by the run's scratch tool;
this file checks the document, everywhere, on every run.
"""
from __future__ import annotations

import io
import re
import zipfile

import pytest
from lxml import etree

from app import registry
from app.exporters.docx import render_docx
from tests import letter_samples as LS

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
KEYS = registry.ported_keys()


def _parts(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        return {n: z.read(n) for n in z.namelist()}


def _text(el):
    return "".join(t.text or "" for t in el.iter(f"{W}t"))


def _name_run(doc):
    for r in doc.iter(f"{W}r"):
        st = r.find(f"{W}rPr/{W}rStyle")
        if st is not None and st.get(f"{W}val") == "CVName" and _text(r).strip():
            rpr = r.find(f"{W}rPr")
            return etree.tostring(rpr)
    return None


def _psig(p):
    """A paragraph's placing properties: its spacing as numbers (compared
    within 1pt = 20 twips, the user's tolerance), indent, borders, shading,
    alignment and run sizes exactly."""
    ppr = p.find(f"{W}pPr")
    sp = ppr.find(f"{W}spacing") if ppr is not None else None
    spacing = tuple(int(sp.get(f"{W}{a}", 0)) for a in ("before", "after", "line")) if sp is not None else (0, 0, 240)
    out = [spacing]
    for tag in ("ind", "pBdr", "shd", "jc"):
        el = ppr.find(f"{W}{tag}") if ppr is not None else None
        out.append(etree.tostring(el) if el is not None else b"")
    sizes = tuple(s.get(f"{W}val") for s in p.iter(f"{W}sz"))
    return tuple(out) + (sizes,)


def _same(a, b) -> bool:
    """Equal, spacing numbers within 20 twips (1pt)."""
    if isinstance(a, tuple) and len(a) == 3 and all(isinstance(x, int) for x in a):
        return isinstance(b, tuple) and len(b) == 3 and all(abs(x - y) <= 20 for x, y in zip(a, b))
    if isinstance(a, (tuple, list)):
        return isinstance(b, (tuple, list)) and len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    return a == b


def _paras_to_name(doc):
    """What places the name: the page section, then for the name's own box
    (a cell, or the body) every paragraph above it there, and for each table
    it stands in, the rows above its row (their heights and paragraphs)."""
    name = next(p for p in doc.iter(f"{W}p")
                if any(s.get(f"{W}val") == "CVName" for s in p.iter(f"{W}rStyle")) and _text(p).strip())
    out = [_psig(name)]
    box = name.getparent()
    for sib in box:
        if sib is name:
            break
        out.append(("before", [_psig(x) for x in sib.iter(f"{W}p")]))
    for tr in (a for a in name.iterancestors() if a.tag == f"{W}tr"):
        tbl = tr.getparent()
        for row in tbl.findall(f"{W}tr"):
            if row is tr:
                break
            h = row.find(f"{W}trPr/{W}trHeight")
            out.append(("row", etree.tostring(h) if h is not None else b"",
                        [_psig(x) for x in row.iter(f"{W}p")]))
        for el in tbl.itersiblings(preceding=True):
            out.append(("above", [_psig(x) for x in el.iter(f"{W}p")]))
    return out


@pytest.fixture(scope="module")
def files():
    out = {}
    for key in KEYS:
        for lang in ("en", "ar"):
            d = LS.with_letter(lang)
            out[(key, lang)] = {part: _parts(render_docx(d, key, part))
                                for part in ("cv", "letter", "both")}
    return out


def _doc(parts):
    return etree.fromstring(parts["word/document.xml"])


def _sect(doc, i=-1):
    return doc.findall(f".//{W}sectPr")[i]


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("key", KEYS)
def test_the_letters_name_is_the_cvs(files, key, lang):
    f = files[(key, lang)]
    cv, lt = _doc(f["cv"]), _doc(f["letter"])
    assert _name_run(lt) == _name_run(cv)


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("key", KEYS)
def test_the_letters_page_is_the_cvs(files, key, lang):
    f = files[(key, lang)]
    a, b = _sect(_doc(f["cv"])), _sect(_doc(f["letter"]))
    for tag in ("pgSz", "pgMar"):
        assert etree.tostring(b.find(f"{W}{tag}")) == etree.tostring(a.find(f"{W}{tag}")), tag


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("key", KEYS)
def test_the_name_stands_where_the_cvs_does(files, key, lang):
    f = files[(key, lang)]
    assert _same(_paras_to_name(_doc(f["letter"])), _paras_to_name(_doc(f["cv"])))


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("key", [k for k in KEYS if k.startswith("ats-")])
def test_an_ats_letterhead_is_the_cvs_own_paragraphs(files, key, lang):
    """Every paragraph above the letter's body (the date) is the CV's own
    paragraph, in the same place - spacing, borders, shading, runs."""
    from app import letter
    f = files[(key, lang)]
    date = letter.letter_of(LS.with_letter(lang))["date"]
    lt = list(_doc(f["letter"]).iter(f"{W}p"))
    cv = list(_doc(f["cv"]).iter(f"{W}p"))
    n = next(i for i, p in enumerate(lt) if date and date in _text(p))
    assert n >= 1

    def sig(p):
        p = etree.fromstring(etree.tostring(p))
        for k in p.iter(f"{W}keepNext"):
            k.getparent().remove(k)
        return etree.tostring(p)
    for a, b in zip(cv[:n], lt[:n]):
        assert sig(b) == sig(a), _text(a)[:40]


R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def _headers(parts, sect):
    """{(kind, type): header/footer part XML with ids masked} of a section."""
    rels = etree.fromstring(parts["word/_rels/document.xml.rels"])
    target = {r.get("Id"): r.get("Target") for r in rels}
    out = {}
    for kind in ("header", "footer"):
        for ref in sect.findall(f"{W}{kind}Reference"):
            xml = parts["word/" + target[ref.get(f"{R}id")]]
            xml = re.sub(rb'(r:embed|r:id|w14:paraId|w14:textId|id|o:spid)="[^"]*"', rb'="#"', xml)
            xml = re.sub(rb'name="[^"]*"', b'name="#"', xml)
            out[(kind, ref.get(f"{W}type"))] = xml
    return out


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize("key", KEYS)
def test_cv_plus_letter_has_no_strip_over_the_letterhead(files, key, lang):
    """The letter's section in "CV + letter" is the standalone letter's page:
    the same margins, and exactly its header (a Modern design's page shapes);
    a letter with no header of its own (ATS) gets one that takes no room -
    Word's default header paragraph pushed the letter 13.4pt down (ats-t7)."""
    both, alone = files[(key, lang)]["both"], files[(key, lang)]["letter"]
    bs, als = _sect(_doc(both), -1), _sect(_doc(alone))
    assert etree.tostring(bs.find(f"{W}pgMar")) == etree.tostring(als.find(f"{W}pgMar"))
    hb, ha = _headers(both, bs), _headers(alone, als)
    for k, xml in hb.items():
        if k in ha:
            assert xml == ha[k], f"{k}: not the letter's own header"
        else:
            part = etree.fromstring(xml)
            for p in part.iter(f"{W}p"):
                sp = p.find(f"{W}pPr/{W}spacing")
                assert sp is not None and sp.get(f"{W}line") == "60", f"{k}: a header line takes room"
