"""Graphite text shaping via SIL's libgraphite2 (graphite2.dll).

Graphite is SIL's *independent* OpenType-alternative shaping engine, driven by
the ``Silf`` table embedded in Graphite-enabled fonts (e.g. SIL's Charis SIL /
Andika / Padauk).  This gives a shaping result that differs from HarfBuzz,
DirectWrite, Uniscribe and FreeType.

The DLLs live in ``babelmap/backend/vendor/graphite2/`` — the MSYS2
``mingw-w64-x86_64-graphite2`` package, with its matching runtime DLLs
(``libgcc_s_seh-1.dll`` / ``libstdc++-6.dll`` / ``libwinpthread-1.dll``) copied
alongside (from MSYS2 ``gcc-libs`` / ``libwinpthread``) so the folder is
self-contained.  See ``vendor/graphite2/README.md`` for versions / how to update.

Only fonts with a ``Silf`` table will shape meaningfully; for other fonts
``gr_make_file_face`` fails and we raise.

Graphite has no buffer-message callback → only the final glyph run is produced.

Implementation notes (learned while porting):
- ``gr_make_face`` (memory pointer + table callback) is fiddly over ctypes and
  crashes; ``gr_make_file_face`` (read straight from a file) is what the
  bundled ``gr2fonttest`` uses and works — we write the font to a temp file.
- ``gr_make_seg`` has 8 params: (font, face, script, pFeats, enc, pStart,
  nChars, dir); enc is gr_encform (gr_utf8=1, gr_utf16=2, gr_utf32=4).  We pass
  UTF-32 codepoints (enc=4) like ``gr2fonttest -codes``.
- ``gr_engine_version`` takes 3 output pointers (major/minor/bugfix) — calling
  it as a no-arg "returns uint32" crashes.  We don't call it.
- ``gr_slot_advance_X/Y`` crash on some slots in this build; ``gr2fonttest``
  doesn't use them either.  We read ``gr_slot_origin_X/Y`` and derive advances
  from consecutive origin deltas (last = seg_advance_X − last origin).
"""

from __future__ import annotations

import ctypes
import os
import tempfile
from ctypes import POINTER, c_char_p, c_float, c_int, c_size_t, c_uint32, c_void_p

_VENDOR_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor", "graphite2")
# Self-contained dir (DLL + matching runtime). Keep a list so extra fallbacks
# can be added later if needed.
_CANDIDATE_DIRS = [_VENDOR_ROOT]


def _load():
    if _load.cache is None:
        last_err = None
        for _d in _CANDIDATE_DIRS:
            if not os.path.isdir(_d):
                continue
            try:
                os.add_dll_directory(_d)
                _load.cache = ctypes.WinDLL(os.path.join(_d, "libgraphite2.dll"))
                _load.dir = _d
                break
            except OSError as _e:
                last_err = _e
                continue
        if _load.cache is None:
            raise RuntimeError(f"Could not load libgraphite2.dll: {last_err}")
    return _load.cache


_load.cache = None
_load.dir = None


def _bind(gr, name, restype, argtypes):
    f = getattr(gr, name)
    f.restype = restype
    f.argtypes = argtypes
    return f


def shape_with_graphite(
    data: bytes,
    text: str,
    *,
    direction: str = "auto",
    script: str = "",
    language: str = "",
    features: dict | None = None,
) -> dict:
    """Shape text with Graphite.

    Prefers HarfBuzz's built-in ``graphite2`` shaper (fully cross-platform) when
    the installed uharfbuzz was compiled with graphite2 support; otherwise falls
    back to the vendored ``libgraphite2`` DLL (Windows-only)."""
    try:
        return _shape_with_uharfbuzz(data, text, direction)
    except Exception:
        return _shape_with_dll(data, text, direction=direction, script=script, language=language, features=features)


def _shape_with_uharfbuzz(data: bytes, text: str, direction: str) -> dict:
    """Graphite shaping through uharfbuzz's graphite2 shaper (cross-platform).

    Raises if the installed HarfBuzz was built without graphite2 support."""
    import uharfbuzz as hb

    face = hb.Face(data)
    font = hb.Font(face)
    font.scale = (face.upem, face.upem)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    if direction == "rtl":
        buf.direction = "rtl"
    hb.shape(font, buf, None, ["graphite2"])

    glyphs: list[dict] = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        glyphs.append(
            {
                "g": int(info.codepoint),
                "cl": int(info.cluster),
                "dx": int(pos.x_offset),
                "dy": int(pos.y_offset),
                "ax": int(pos.x_advance),
                "ay": int(pos.y_advance),
                "flags": 0,
            }
        )
    stage = {"m": "Graphite shaping (uharfbuzz graphite2)", "glyphs": glyphs, "depth": 0, "effective": True}
    return {
        "upem": int(face.upem),
        "glyph_count": len(glyphs),
        "stages": [stage],
        "final": glyphs,
        "messages": ["Graphite shaping (uharfbuzz graphite2)"],
        "engine": "graphite",
    }


def _shape_with_dll(
    data: bytes,
    text: str,
    *,
    direction: str = "auto",
    script: str = "",
    language: str = "",
    features: dict | None = None,
) -> dict:
    """Graphite shaping via the vendored libgraphite2 DLL (Windows)."""
    gr = _load()

    gr_make_file_face = _bind(gr, "gr_make_file_face", c_void_p, [c_char_p, c_uint32])
    gr_face_destroy = _bind(gr, "gr_face_destroy", None, [c_void_p])
    gr_make_font = _bind(gr, "gr_make_font", c_void_p, [c_float, c_void_p])
    gr_font_destroy = _bind(gr, "gr_font_destroy", None, [c_void_p])
    gr_make_seg = _bind(
        gr,
        "gr_make_seg",
        c_void_p,
        [c_void_p, c_void_p, c_uint32, c_void_p, c_int, c_void_p, c_size_t, c_int],
    )
    gr_seg_destroy = _bind(gr, "gr_seg_destroy", None, [c_void_p])
    gr_seg_first_slot = _bind(gr, "gr_seg_first_slot", c_void_p, [c_void_p])
    gr_slot_next = _bind(gr, "gr_slot_next_in_segment", c_void_p, [c_void_p])
    gr_slot_gid = _bind(gr, "gr_slot_gid", c_uint32, [c_void_p])
    gr_slot_original = _bind(gr, "gr_slot_original", c_uint32, [c_void_p])
    gr_slot_origin_X = _bind(gr, "gr_slot_origin_X", c_float, [c_void_p])
    gr_slot_origin_Y = _bind(gr, "gr_slot_origin_Y", c_float, [c_void_p])
    gr_seg_advance_X = _bind(gr, "gr_seg_advance_X", c_float, [c_void_p])

    # upem from the font (origin/advance will be in font units when size = upem)
    import io
    from fontTools.ttLib import TTFont

    tt = TTFont(io.BytesIO(data), lazy=True)
    upem = tt["head"].unitsPerEm or 2048
    tt.close()

    # gr_make_face (memory ptr + table callback) is unreliable over ctypes; use the
    # file-based face exactly like the bundled gr2fonttest. Write bytes to a temp file.
    fd, tmp_path = tempfile.mkstemp(suffix=".ttf")
    os.close(fd)
    try:
        with open(tmp_path, "wb") as fh:
            fh.write(data)

        face = gr_make_file_face(tmp_path.encode("utf-8"), 0)
        if not face:
            raise ValueError("Font has no Graphite (Silf) table — Graphite engine requires a Graphite font")

        try:
            font = gr_make_font(float(upem), face)
            if not font:
                raise ValueError("gr_make_font failed")
            try:
                # gr_make_seg(font, face, script, pFeats, enc, pStart, nChars, dir)
                # enc = gr_utf32 (4); pStart = array of UTF-32 codepoints
                cps = [ord(ch) for ch in text]
                arr = (c_uint32 * max(1, len(cps)))(*cps)
                rtl = 1 if direction == "rtl" else 0
                seg = gr_make_seg(font, face, 0, None, 4, ctypes.cast(arr, c_void_p), len(cps), rtl)
                if not seg:
                    raise ValueError("gr_make_seg failed")
                try:
                    # Collect slot origins; derive per-glyph advances from deltas
                    # (gr2fonttest layout). gr_slot_advance_X/Y crash on some slots.
                    slots = []
                    slot = gr_seg_first_slot(seg)
                    while slot:
                        slots.append(
                            {
                                "g": int(gr_slot_gid(slot)),
                                "cl": int(gr_slot_original(slot)),
                                "ox": float(gr_slot_origin_X(slot)),
                                "oy": float(gr_slot_origin_Y(slot)),
                            }
                        )
                        slot = gr_slot_next(slot)

                    total_adv = float(gr_seg_advance_X(seg))
                    glyphs: list[dict] = []
                    for i, s in enumerate(slots):
                        ax = (
                            int(round(slots[i + 1]["ox"] - s["ox"]))
                            if i + 1 < len(slots)
                            else int(round(total_adv - s["ox"]))
                        )
                        glyphs.append(
                            {
                                "g": s["g"],
                                "cl": s["cl"],
                                "dx": int(round(s["ox"])),
                                "dy": int(round(s["oy"])),
                                "ax": ax,
                                "ay": 0,
                                "flags": 0,
                            }
                        )
                finally:
                    gr_seg_destroy(seg)
            finally:
                gr_font_destroy(font)
        finally:
            gr_face_destroy(face)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    stage = {"m": "Graphite shaping", "glyphs": glyphs, "depth": 0, "effective": True}
    return {
        "upem": upem,
        "glyph_count": len(glyphs),
        "stages": [stage],
        "final": glyphs,
        "messages": ["Graphite shaping"],
        "engine": "graphite",
    }
