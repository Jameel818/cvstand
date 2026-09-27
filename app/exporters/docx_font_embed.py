"""Embed the fonts a Word file uses into the file itself (spec §6.3, step 6).

A .docx is opened on a machine this project does not control, where Cairo,
Montserrat or Open Sans are usually not installed. Without embedding, Word
substitutes a face of its own; with it, the document carries the TTFs and
looks the same everywhere, and the recipient can keep typing in the same
font (the FULL script-subset TTF is embedded, never a per-character subset,
and `w:saveSubsetFonts` is never written).

    embed_fonts(docx_bytes, faces) -> docx_bytes

`faces` is every (family, weight) the document's text draws - collected
from the document by docx_theme.faces_drawn(), not guessed. Each face must
be BUILT (build.json): its Word name, bold flag and fsType come from there.

WHAT CHANGES IN THE PACKAGE (ECMA-376 Part 1, §17.8)
    word/settings.xml      <w:embedTrueTypeFonts/>, at its schema position
    word/fonts/fontN.odttf one per face, OBFUSCATED (below)
    word/fontTable.xml     one <w:font w:name=...> per Word family name, with
                           embedRegular / embedBold -> the part + its key
    word/_rels/fontTable.xml.rels   one font relationship per part
    [Content_Types].xml    Default odttf -> ...obfuscatedFont

OBFUSCATION: a fresh GUID per face; its 32 hex digits read as 16 bytes in
REVERSED order are the key; the first 32 bytes of the TTF are XORed with the
key (repeating); everything after byte 32 is the TTF unchanged.

ONE FACE PER NAME: Word matches an embedded font by (w:name, regular|bold).
Two different faces for one slot - Archivo 900 and the Archivo Black family
are both "Archivo Black" - would let Word pick either, so it is an error
here (docx_theme resolves it before this ever runs).

Every element is inserted in schema order: out-of-order children are what
once made Word refuse the masters outright ("unreadable content").
"""
from __future__ import annotations

import io
import logging
import uuid
import zipfile
from functools import lru_cache

from lxml import etree

log = logging.getLogger(__name__)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
FONT_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"
ODTTF_TYPE = "application/vnd.openxmlformats-officedocument.obfuscatedFont"
FONT_TABLE_TYPE = ("application/vnd.openxmlformats-officedocument."
                   "wordprocessingml.fontTable+xml")


def _w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


#: CT_Settings children that come BEFORE w:embedTrueTypeFonts.
SETTINGS_BEFORE = ("writeProtection", "view", "zoom", "removePersonalInformation",
                   "removeDateAndTime", "doNotDisplayPageBoundaries",
                   "displayBackgroundShape", "printPostScriptOverText",
                   "printFractionalCharacterWidth", "printFormsData")
#: CT_Font child order.
FONT_ORDER = ("altName", "panose1", "charset", "family", "notTrueType", "pitch", "sig",
              "embedRegular", "embedBold", "embedItalic", "embedBoldItalic")
EMBEDDABLE_FS_TYPE = (0, 8)
_WORD_FAMILY = {"serif": "roman", "sans-serif": "swiss", "monospace": "modern"}


class FontEmbedError(RuntimeError):
    pass


# ---- obfuscation -------------------------------------------------------------

def font_key(guid: str) -> bytes:
    """The 16-byte key of a `{XXXXXXXX-XXXX-...}` GUID: its hex digits as
    bytes, in reverse order (ECMA-376 Part 1 §17.8.1)."""
    hex32 = guid.strip("{}").replace("-", "")
    if len(hex32) != 32:
        raise ValueError(f"not a GUID: {guid!r}")
    return bytes(int(hex32[30 - 2 * i: 32 - 2 * i], 16) for i in range(16))


def obfuscate(data: bytes, guid: str) -> bytes:
    """XOR the first 32 bytes with the key; the same call de-obfuscates."""
    key = font_key(guid)
    head = bytes(b ^ key[i % 16] for i, b in enumerate(data[:32]))
    return head + data[32:]


def new_guid() -> str:
    return "{" + str(uuid.uuid4()).upper() + "}"


# ---- the faces -----------------------------------------------------------------

@lru_cache(maxsize=None)
def _ttf(rel: str) -> bytes:
    from ..typography.faces import FONT_DIR
    return (FONT_DIR / rel).read_bytes()


@lru_cache(maxsize=None)
def _os2(rel: str) -> dict:
    """What fontTable.xml's matching hints need, read from the file itself."""
    from fontTools.ttLib import TTFont
    font = TTFont(io.BytesIO(_ttf(rel)), lazy=True)
    os2 = font["OS/2"]
    p = os2.panose
    panose = bytes([p.bFamilyType, p.bSerifStyle, p.bWeight, p.bProportion, p.bContrast,
                    p.bStrokeVariation, p.bArmStyle, p.bLetterForm, p.bMidline,
                    p.bXHeight]).hex().upper()
    return {"fs_type": os2.fsType, "panose": panose,
            "usb": [os2.ulUnicodeRange1, os2.ulUnicodeRange2, os2.ulUnicodeRange3,
                    os2.ulUnicodeRange4],
            "csb": [getattr(os2, "ulCodePageRange1", 0), getattr(os2, "ulCodePageRange2", 0)]}


def plan(faces) -> dict[str, dict[str, dict]]:
    """{Word name: {"regular"|"bold": build.json face}}, refusing a face that
    may not be embedded and two faces in one slot."""
    from ..typography import face as built
    out: dict[str, dict[str, dict]] = {}
    for family, weight in sorted(faces):
        f = built(family, weight)
        if f is None:
            raise FontEmbedError(f"{family} {weight} is not built - nothing to embed")
        fs = _os2(f["ttf"])["fs_type"]
        if fs not in EMBEDDABLE_FS_TYPE:
            log.error("refusing to embed %s %s: fsType %s", family, weight, fs)
            raise FontEmbedError(f"{family} {weight}: fsType {fs} forbids embedding")
        slot = "bold" if f["word_bold"] else "regular"
        entry = out.setdefault(f["word_family_name"], {})
        if slot in entry and entry[slot]["ttf"] != f["ttf"]:
            raise FontEmbedError(
                f"two faces for Word font {f['word_family_name']!r} ({slot}): "
                f"{entry[slot]['family']} {entry[slot]['weight']} and {family} {weight}")
        entry[slot] = f
    return out


# ---- the package ---------------------------------------------------------------

def _insert_ordered(parent, el, order: tuple[str, ...]) -> None:
    local = etree.QName(el).localname
    later = order[order.index(local) + 1:]
    for i, child in enumerate(parent):
        if isinstance(child.tag, str) and etree.QName(child).localname in later:
            parent.insert(i, el)
            return
    parent.append(el)


def _settings(xml: bytes) -> bytes:
    root = etree.fromstring(xml)
    if root.find(_w("embedTrueTypeFonts")) is None:
        el = etree.Element(_w("embedTrueTypeFonts"))
        for i, child in enumerate(root):
            if isinstance(child.tag, str) and etree.QName(child).localname not in SETTINGS_BEFORE:
                root.insert(i, el)
                break
        else:
            root.append(el)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def _font_el(name: str, slots: dict[str, dict], keys: dict[str, tuple[str, str]]):
    from ..typography.registry import any_font
    sample = slots.get("regular") or slots["bold"]
    hints = _os2(sample["ttf"])
    generic = any_font(sample["family"]).generic
    arabic = _is_arabic(sample["family"])

    font = etree.Element(_w("font"), {_w("name"): name})

    def child(tag, attrs):
        el = etree.SubElement(font, _w(tag))
        for k, v in attrs.items():
            el.set(k, v)

    child("panose1", {_w("val"): hints["panose"]})
    child("charset", {_w("val"): "B2" if arabic else "00"})
    child("family", {_w("val"): _WORD_FAMILY.get(generic, "auto")})
    child("pitch", {_w("val"): "fixed" if generic == "monospace" else "variable"})
    child("sig", {_w("usb0"): f"{hints['usb'][0]:08X}", _w("usb1"): f"{hints['usb'][1]:08X}",
                  _w("usb2"): f"{hints['usb'][2]:08X}", _w("usb3"): f"{hints['usb'][3]:08X}",
                  _w("csb0"): f"{hints['csb'][0]:08X}", _w("csb1"): f"{hints['csb'][1]:08X}"})
    for slot, tag in (("regular", "embedRegular"), ("bold", "embedBold")):
        if slot in keys:
            rid, guid = keys[slot]
            child(tag, {f"{{{R_NS}}}id": rid, _w("fontKey"): guid})
    return font


def _is_arabic(family: str) -> bool:
    from ..typography import OFFERED
    return any(family in fams for (lang, _r), fams in OFFERED.items() if lang == "ar")


def embed_fonts(docx: bytes, faces) -> bytes:
    """A NEW package with `faces` embedded. `faces` empty: returned as-is."""
    slots = plan(faces)
    if not slots:
        return docx
    src = zipfile.ZipFile(io.BytesIO(docx))
    names = src.namelist()

    table = etree.fromstring(src.read("word/fontTable.xml"))
    rels_name = "word/_rels/fontTable.xml.rels"
    rels = (etree.fromstring(src.read(rels_name)) if rels_name in names
            else etree.Element(f"{{{PKG_REL_NS}}}Relationships", nsmap={None: PKG_REL_NS}))
    used_ids = {r.get("Id") for r in rels}
    parts: dict[str, bytes] = {}
    n = 0
    for wname, entry in slots.items():
        for old in table.findall(_w("font")):
            if old.get(_w("name")) == wname:
                table.remove(old)
        keys = {}
        for slot in ("regular", "bold"):
            if slot not in entry:
                continue
            n += 1
            rid = f"rIdFont{n}"
            while rid in used_ids:
                n += 1
                rid = f"rIdFont{n}"
            guid = new_guid()
            part = f"fonts/font{n}.odttf"
            parts[f"word/{part}"] = obfuscate(_ttf(entry[slot]["ttf"]), guid)
            etree.SubElement(rels, f"{{{PKG_REL_NS}}}Relationship",
                             {"Id": rid, "Type": FONT_REL_TYPE, "Target": part})
            used_ids.add(rid)
            keys[slot] = (rid, guid)
        table.append(_font_el(wname, entry, keys))

    ct = etree.fromstring(src.read("[Content_Types].xml"))
    if not any(d.get("Extension") == "odttf" for d in ct.findall(f"{{{CT_NS}}}Default")):
        el = etree.Element(f"{{{CT_NS}}}Default",
                           {"Extension": "odttf", "ContentType": ODTTF_TYPE})
        # Defaults precede Overrides in CT_Types.
        first_override = ct.find(f"{{{CT_NS}}}Override")
        (first_override.addprevious(el) if first_override is not None else ct.append(el))
    if not any(o.get("PartName") == "/word/fontTable.xml"
               for o in ct.findall(f"{{{CT_NS}}}Override")):
        etree.SubElement(ct, f"{{{CT_NS}}}Override",
                         {"PartName": "/word/fontTable.xml", "ContentType": FONT_TABLE_TYPE})

    def xml(el) -> bytes:
        return etree.tostring(el, xml_declaration=True, encoding="UTF-8", standalone=True)

    replaced = {
        "word/settings.xml": _settings(src.read("word/settings.xml")),
        "word/fontTable.xml": xml(table),
        rels_name: xml(rels),
        "[Content_Types].xml": xml(ct),
    }
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        # [Content_Types].xml first, as Word itself writes it.
        order = ["[Content_Types].xml"] + [x for x in names if x != "[Content_Types].xml"]
        for name in order:
            dst.writestr(name, replaced.pop(name) if name in replaced else src.read(name))
        for name, data in list(replaced.items()) + list(parts.items()):
            dst.writestr(name, data)
    return out.getvalue()
