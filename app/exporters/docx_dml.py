"""Portable design shapes: DrawingML first, the VML as its fallback (run 6).

The Word designs drew every shape in VML (v:roundrect, v:oval, v:arc, v:group,
page-anchored v:rect). Microsoft Word draws VML; LibreOffice, Google Docs and
WPS often do not - the user's LibreOffice showed t2's Arabic skill bars
missing, the sidebar short of the page foot and t22's rings without their
arcs. Word itself has written shapes as DrawingML (wps/wpg) inside
mc:AlternateContent since 2010, with VML in mc:Fallback for older readers;
this module does the same:

    <w:r><mc:AlternateContent>
      <mc:Choice Requires="wps|wpg"><w:drawing>... DrawingML ...</w:drawing></mc:Choice>
      <mc:Fallback><w:pict>... the existing VML, unchanged ...</w:pict></mc:Fallback>
    </mc:AlternateContent></w:r>

Callers describe each shape ONCE as a `Sp` (geometry, fill, line) in the
same numbers they give the VML, so the two cannot drift apart.

Coordinates: anchored shapes in points; group children in the group's own
coordinate units (as VML coordsize). 1 pt = 12700 EMU. DrawingML angles are
60000ths of a degree, clockwise from 3 o'clock.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

EMU = 12700
NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:v="urn:schemas-microsoft-com:vml" '
      'xmlns:o="urn:schemas-microsoft-com:office:office" '
      'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" '
      'xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"')
_URI_WPS = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
_URI_WPG = "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"
#: Word's VML z-index origin: z-index z <-> relativeHeight BASE + z
#: (negative z = behind the text, behindDoc).
_Z_BASE = 251658240

_ID = [0]


def _next_id() -> int:
    """docPr ids: unique in a document (Word repairs duplicates). Far above
    python-docx's picture ids (1, 2, ...)."""
    _ID[0] += 1
    return 100000 + _ID[0]


@dataclass
class Sp:
    """One shape. `prst`: rect | roundRect | ellipse | arc | custom.
    (x, y, w, h) in the container's units. `fill`/`line`: hex colour or None.
    `line_w`: points. `radius`: roundRect corner as a fraction of HALF the
    smaller side (VML arcsize). `start`/`end`: arc angles in degrees from
    12 o'clock, clockwise (the VML v:arc convention used here). `path`/`coords`:
    a VML path (m l qx qy x e) in `coords` units, for prst="custom"."""
    prst: str
    x: float
    y: float
    w: float
    h: float
    fill: str | None = None
    line: str | None = None
    line_w: float = 1.0
    radius: float | None = None
    start: float = 0.0
    end: float = 360.0
    path: str | None = None
    coords: tuple[float, float] | None = None
    extra: dict = field(default_factory=dict)


# ---- geometry ----------------------------------------------------------------------

_K = 0.5522847498          # cubic Bezier constant for a quarter circle


def _vml_path_to_dml(path: str, cw: float, ch: float) -> str:
    """The VML path subset the designs use - m, l, qx, qy, x, e - as an
    a:path. qx: an elliptical quadrant whose first segment is tangent to the x
    axis; qy: tangent to the y axis (each as one cubic Bezier)."""
    toks = re.findall(r"[a-z]+|-?\d+(?:\.\d+)?", path)
    out, i, cmd = [], 0, None
    cur = (0.0, 0.0)

    def pt_(x, y):
        return f'<a:pt x="{int(round(x))}" y="{int(round(y))}"/>'

    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t
            i += 1
            if cmd == "x":
                out.append("<a:close/>")
                continue
            if cmd == "e":
                break
            continue
        x, y = float(toks[i]), float(toks[i + 1])
        i += 2
        if cmd == "m":
            out.append(f"<a:moveTo>{pt_(x, y)}</a:moveTo>")
        elif cmd == "l":
            out.append(f"<a:lnTo>{pt_(x, y)}</a:lnTo>")
        elif cmd in ("qx", "qy"):
            x0, y0 = cur
            if cmd == "qx":
                c1, c2 = (x0 + _K * (x - x0), y0), (x, y - _K * (y - y0))
            else:
                c1, c2 = (x0, y0 + _K * (y - y0)), (x - _K * (x - x0), y)
            out.append(f"<a:cubicBezTo>{pt_(*c1)}{pt_(*c2)}{pt_(x, y)}</a:cubicBezTo>")
        cur = (x, y)
    return (f'<a:custGeom><a:avLst/><a:gdLst/><a:ahLst/><a:cxnLst/>'
            f'<a:rect l="0" t="0" r="r" b="b"/><a:pathLst>'
            f'<a:path w="{int(round(cw))}" h="{int(round(ch))}">{"".join(out)}</a:path>'
            f'</a:pathLst></a:custGeom>')


def _geom(sp: Sp) -> str:
    if sp.prst == "custom":
        cw, ch = sp.coords
        return _vml_path_to_dml(sp.path, cw, ch)
    if sp.prst == "roundRect":
        adj = int(round(min(1.0, sp.radius or 0) * 50000))
        return (f'<a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val {adj}"/>'
                f'</a:avLst></a:prstGeom>')
    if sp.prst == "arc":
        # 12 o'clock clockwise -> DrawingML: 3 o'clock clockwise, 270 deg offset
        a1 = int(round(((sp.start + 270) % 360) * 60000))
        a2 = int(round(((sp.end + 270) % 360) * 60000))
        return (f'<a:prstGeom prst="arc"><a:avLst><a:gd name="adj1" fmla="val {a1}"/>'
                f'<a:gd name="adj2" fmla="val {a2}"/></a:avLst></a:prstGeom>')
    return f'<a:prstGeom prst="{sp.prst}"><a:avLst/></a:prstGeom>'


def _sppr(sp: Sp, off: tuple[int, int], ext: tuple[int, int]) -> str:
    fill = (f'<a:solidFill><a:srgbClr val="{sp.fill}"/></a:solidFill>' if sp.fill
            else "<a:noFill/>")
    if sp.line:
        ln = (f'<a:ln w="{int(round(sp.line_w * EMU))}" cap="flat">'
              f'<a:solidFill><a:srgbClr val="{sp.line}"/></a:solidFill></a:ln>')
    else:
        ln = "<a:ln><a:noFill/></a:ln>"
    return (f'<wps:spPr><a:xfrm><a:off x="{off[0]}" y="{off[1]}"/>'
            f'<a:ext cx="{max(1, ext[0])}" cy="{max(1, ext[1])}"/></a:xfrm>'
            f'{_geom(sp)}{fill}{ln}</wps:spPr>')


def _wsp(sp: Sp, off, ext, *, in_group: bool, name: str) -> str:
    nv = f'<wps:cNvPr id="{_next_id()}" name="{name}"/>' if in_group else ""
    return (f'<wps:wsp>{nv}<wps:cNvSpPr/>{_sppr(sp, off, ext)}'
            f'<wps:bodyPr rot="0" vert="horz" wrap="square" lIns="0" tIns="0" rIns="0" '
            f'bIns="0" anchor="t" anchorCtr="0"><a:noAutofit/></wps:bodyPr></wps:wsp>')


# ---- the runs ----------------------------------------------------------------------

def _alt(drawing: str, pict: str, requires: str, rpr: str = "") -> str:
    return (f'<w:r {NS}>{rpr}<mc:AlternateContent><mc:Choice Requires="{requires}">'
            f'<w:drawing>{drawing}</w:drawing></mc:Choice>'
            f'<mc:Fallback><w:pict>{pict}</w:pict></mc:Fallback></mc:AlternateContent></w:r>')


def inline_group_run(name: str, w_pt: float, h_pt: float, cw: int, ch: int,
                     shapes: list[Sp], vml_group: str, rpr: str) -> str:
    """An inline group in the text line (skill bars, dot rows, sliders):
    `shapes` in the group's (cw, ch) units; `vml_group` is the v:group."""
    cx, cy = int(round(w_pt * EMU)), int(round(h_pt * EMU))
    kids = "".join(
        _wsp(s, (int(round(s.x)), int(round(s.y))), (int(round(s.w)), int(round(s.h))),
             in_group=True, name=f"{name}_{i}")
        for i, s in enumerate(shapes))
    drawing = (f'<wp:inline distT="0" distB="0" distL="0" distR="0">'
               f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
               f'<wp:docPr id="{_next_id()}" name="{name}"/><wp:cNvGraphicFramePr/>'
               f'<a:graphic><a:graphicData uri="{_URI_WPG}"><wpg:wgp><wpg:cNvGrpSpPr/>'
               f'<wpg:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/>'
               f'<a:chOff x="0" y="0"/><a:chExt cx="{cw}" cy="{ch}"/></a:xfrm></wpg:grpSpPr>'
               f'{kids}</wpg:wgp></a:graphicData></a:graphic></wp:inline>')
    return _alt(drawing, vml_group, "wpg", rpr)


#: VML mso-position-*-relative -> DrawingML relativeFrom
_REL_H = {"page": "page", "text": "column", "margin": "margin"}
_REL_V = {"page": "page", "line": "paragraph", "text": "paragraph", "margin": "margin"}


def anchored_run(name: str, sp: Sp, vml_shape: str, *, rel_h: str, rel_v: str, z: int,
                 in_cell: bool) -> str:
    """A shape positioned at (sp.x, sp.y) pt from its anchor's reference
    (page, or the text column and the paragraph), `sp.w` x `sp.h` pt. `z` is
    the VML z-index (negative: behind the text)."""
    cx, cy = int(round(sp.w * EMU)), int(round(sp.h * EMU))
    behind = 1 if z < 0 else 0
    rh = max(0, _Z_BASE + z) if z < 0 else _Z_BASE + 1024 + z
    drawing = (
        f'<wp:anchor distT="0" distB="0" distL="0" distR="0" simplePos="0" '
        f'relativeHeight="{rh}" behindDoc="{behind}" locked="0" '
        f'layoutInCell="{1 if in_cell else 0}" allowOverlap="1">'
        f'<wp:simplePos x="0" y="0"/>'
        f'<wp:positionH relativeFrom="{_REL_H[rel_h]}"><wp:posOffset>{int(round(sp.x * EMU))}'
        f'</wp:posOffset></wp:positionH>'
        f'<wp:positionV relativeFrom="{_REL_V[rel_v]}"><wp:posOffset>{int(round(sp.y * EMU))}'
        f'</wp:posOffset></wp:positionV>'
        f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
        f'<wp:wrapNone/><wp:docPr id="{_next_id()}" name="{name}"/><wp:cNvGraphicFramePr/>'
        f'<a:graphic><a:graphicData uri="{_URI_WPS}">'
        f'{_wsp(sp, (0, 0), (cx, cy), in_group=False, name=name)}'
        f'</a:graphicData></a:graphic></wp:anchor>')
    return _alt(drawing, vml_shape, "wps")
