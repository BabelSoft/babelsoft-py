"""Uniscribe (USP10) text shaping for the OpenType Test Framework.

Windows-only, second shaping engine next to HarfBuzz.  Uniscribe is the older
Windows native shaping API (GDI-era); on this machine DirectWrite's COM layer
is unusable (DWriteCreateFactory returns E_NOINTERFACE for IDWriteFactory), so
we drive USP10's exported functions directly via ctypes.

Like DirectWrite, Uniscribe has no buffer-message callback → we can only
produce the *final* glyph run, not a step-by-step trace.
"""

from __future__ import annotations

import ctypes
from ctypes import (
    POINTER,
    Structure,
    byref,
    c_byte,
    c_int,
    c_uint32,
    c_ushort,
    c_void_p,
    c_wchar_p,
    create_unicode_buffer,
)

_gdi32 = ctypes.WinDLL("gdi32")
_usp10 = ctypes.WinDLL("usp10")


# ---------------------------------------------------------------------------
# Structures
# ---------------------------------------------------------------------------
class LOGFONTW(Structure):
    _fields_ = [
        ("lfHeight", c_int),
        ("lfWidth", c_int),
        ("lfEscapement", c_int),
        ("lfOrientation", c_int),
        ("lfWeight", c_int),
        ("lfItalic", c_byte),
        ("lfUnderline", c_byte),
        ("lfStrikeOut", c_byte),
        ("lfCharSet", c_byte),
        ("lfOutPrecision", c_byte),
        ("lfClipPrecision", c_byte),
        ("lfQuality", c_byte),
        ("lfPitchAndFamily", c_byte),
        ("lfFaceName", ctypes.c_wchar * 32),
    ]


class SCRIPT_STATE(Structure):
    _fields_ = [("uBidiLevel", c_ushort)]


class SCRIPT_ANALYSIS(Structure):
    _fields_ = [("script", c_ushort), ("fFlags", c_ushort), ("s", SCRIPT_STATE)]


class SCRIPT_ITEM(Structure):
    _fields_ = [("iCharPos", c_int), ("a", SCRIPT_ANALYSIS)]


class SCRIPT_CONTROL(Structure):
    _fields_ = [("uFlags", c_uint32)]


class SCRIPT_VISATTR(Structure):
    _fields_ = [("uFlags", c_ushort)]


class GOFFSET(Structure):
    _fields_ = [("du", c_int), ("dv", c_int)]


# ---------------------------------------------------------------------------
# GDI prototypes
# ---------------------------------------------------------------------------
_gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
_gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
_gdi32.CreateFontIndirectW.restype = ctypes.c_void_p
_gdi32.CreateFontIndirectW.argtypes = [POINTER(LOGFONTW)]
_gdi32.SelectObject.restype = ctypes.c_void_p
_gdi32.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_gdi32.DeleteDC.restype = ctypes.c_int
_gdi32.DeleteDC.argtypes = [ctypes.c_void_p]
_gdi32.DeleteObject.restype = ctypes.c_int
_gdi32.DeleteObject.argtypes = [ctypes.c_void_p]

# ---------------------------------------------------------------------------
# Uniscribe prototypes
# ---------------------------------------------------------------------------
_usp10.ScriptItemize.restype = ctypes.c_int
_usp10.ScriptItemize.argtypes = [
    c_wchar_p,
    c_int,
    c_int,
    POINTER(SCRIPT_CONTROL),
    POINTER(SCRIPT_STATE),
    POINTER(SCRIPT_ITEM),
    POINTER(c_int),
]
_usp10.ScriptShape.restype = ctypes.c_int
_usp10.ScriptShape.argtypes = [
    ctypes.c_void_p,
    POINTER(c_void_p),
    c_wchar_p,
    c_int,
    c_int,
    POINTER(SCRIPT_ANALYSIS),
    POINTER(c_ushort),
    POINTER(c_ushort),
    POINTER(SCRIPT_VISATTR),
    POINTER(c_int),
]
_usp10.ScriptPlace.restype = ctypes.c_int
_usp10.ScriptPlace.argtypes = [
    ctypes.c_void_p,
    POINTER(c_void_p),
    POINTER(c_ushort),
    c_int,
    POINTER(SCRIPT_VISATTR),
    POINTER(SCRIPT_ANALYSIS),
    POINTER(c_int),
    POINTER(GOFFSET),
    POINTER(c_void_p),
]
_usp10.ScriptFreeCache.restype = ctypes.c_int
_usp10.ScriptFreeCache.argtypes = [POINTER(c_void_p)]

SCRIPT_MONGOLIAN = 62
DEFAULT_CHARSET = 1
UPEM = 2048


def _make_hdc(font_path: str) -> tuple[ctypes.c_void_p, ctypes.c_void_p]:
    """Create a memory DC with the font selected. Returns (hdc, hfont)."""
    # Real face name from the font's name table (filename != family name).
    face = None
    try:
        from fontTools.ttLib import TTFont

        tt = TTFont(font_path, lazy=True)
        face = tt["name"].getDebugName(1) or tt["name"].getDebugName(16)
        tt.close()
    except Exception:
        face = None
    if not face:
        import os

        face = os.path.splitext(os.path.basename(font_path))[0]

    hdc = _gdi32.CreateCompatibleDC(None)
    lf = LOGFONTW()
    lf.lfHeight = -UPEM
    lf.lfWeight = 400
    lf.lfCharSet = DEFAULT_CHARSET
    try:
        lf.lfFaceName = face[:31]
    except Exception:
        lf.lfFaceName = "Arial"
    hfont = _gdi32.CreateFontIndirectW(byref(lf))
    if not hfont:
        _gdi32.DeleteDC(hdc)
        raise ValueError(f"CreateFontIndirect failed for {face!r}")
    _gdi32.SelectObject(hdc, hfont)
    return hdc, hfont


def shape_with_uniscribe(
    path_or_b64: str,
    text: str,
    *,
    is_b64: bool = False,
    direction: str = "auto",
    script: str = "",
    language: str = "",
    features: dict | None = None,
) -> dict:
    """Shape text with Uniscribe. Returns the final glyph run.

    Result shape is compatible with shape_trace():
    {upem, glyph_count, stages:[{m, depth, effective, glyphs}], final,
     messages, engine}
    """
    import base64
    import os
    import tempfile

    tmp_path = None
    try:
        if is_b64:
            with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as f:
                f.write(base64.b64decode(path_or_b64))
                tmp_path = f.name
            font_path = tmp_path
        else:
            font_path = path_or_b64

        hdc, hfont = _make_hdc(font_path)

        buf = create_unicode_buffer(text, len(text) + 1)
        n = len(text)

        # itemize
        max_items = max(16, n // 2 + 16)
        items = (SCRIPT_ITEM * (max_items + 1))()
        n_items = c_int(0)
        ctrl = SCRIPT_CONTROL()
        state = SCRIPT_STATE()
        if direction == "rtl":
            state.uBidiLevel = 1
        hr = _usp10.ScriptItemize(buf, n, max_items, byref(ctrl), byref(state), items, byref(n_items))
        if hr != 0:
            raise ValueError(f"ScriptItemize failed: 0x{hr & 0xFFFFFFFF:08X}")
        item_count = int(n_items.value)
        if item_count == 0:
            raise ValueError("ScriptItemize produced no items")

        all_glyphs: list[dict] = []
        all_messages: list[str] = []
        for it in range(item_count):
            item = items[it]
            start = int(item.iCharPos)
            end = int(items[it + 1].iCharPos) if it + 1 < item_count else n
            seg = text[start:end]
            seg_buf = create_unicode_buffer(seg, len(seg) + 1)

            sc = c_void_p()
            max_glyphs = max(16, len(seg) * 4 + 8)
            out_glyphs = (c_ushort * max_glyphs)()
            log_clust = (c_ushort * max_glyphs)()
            vis = (SCRIPT_VISATTR * max_glyphs)()
            c_glyphs = c_int(0)
            hr = _usp10.ScriptShape(
                hdc,
                byref(sc),
                seg_buf,
                len(seg),
                max_glyphs,
                byref(item.a),
                out_glyphs,
                log_clust,
                vis,
                byref(c_glyphs),
            )
            if hr != 0:
                # fall back to "no shaping" — emit the raw cmap glyphs via ScriptShape with dummy
                raise ValueError(f"ScriptShape failed: 0x{hr & 0xFFFFFFFF:08X}")
            gcount = int(c_glyphs.value)

            adv = (c_int * max_glyphs)()
            goff = (GOFFSET * max_glyphs)()
            hr = _usp10.ScriptPlace(
                hdc,
                byref(sc),
                out_glyphs,
                gcount,
                vis,
                byref(item.a),
                adv,
                goff,
                None,
            )
            if hr != 0:
                raise ValueError(f"ScriptPlace failed: 0x{hr & 0xFFFFFFFF:08X}")

            # cluster: char index (within segment) → first glyph index
            glyph_to_char: dict[int, int] = {}
            for ci in range(len(seg)):
                gi = int(log_clust[ci])
                glyph_to_char.setdefault(gi, ci)

            for gi in range(gcount):
                cl = start + glyph_to_char.get(gi, 0)
                all_glyphs.append(
                    {
                        "g": int(out_glyphs[gi]),
                        "cl": cl,
                        "dx": int(goff[gi].du),
                        "dy": int(goff[gi].dv),
                        "ax": int(adv[gi]),
                        "ay": 0,
                        "flags": 0,
                    }
                )
            all_messages.append(f"Uniscribe item {it}: script {int(item.a.script)} chars {start}..{end}")

            _usp10.ScriptFreeCache(byref(sc))

        _gdi32.DeleteObject(hfont)
        _gdi32.DeleteDC(hdc)

        stage = {
            "m": "Uniscribe shaping",
            "glyphs": all_glyphs,
            "depth": 0,
            "effective": True,
        }
        return {
            "upem": UPEM,
            "glyph_count": len(all_glyphs),
            "stages": [stage],
            "final": all_glyphs,
            "messages": all_messages,
            "engine": "uniscribe",
        }
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
