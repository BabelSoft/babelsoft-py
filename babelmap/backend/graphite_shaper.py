"""Graphite text shaping — cross-platform via the ``pygraphite2`` package.

Graphite is SIL's *independent* OpenType-alternative shaping engine, driven by
the ``Silf`` table embedded in Graphite-enabled fonts (e.g. SIL's Charis SIL /
Andika / Padauk).  This gives a shaping result that differs from HarfBuzz,
DirectWrite, Uniscribe and FreeType.

Shaping is delegated to the ``pygraphite2`` package (installed from PyPI), which
wraps SIL's official ctypes binding and discovers the native ``libgraphite2``
at runtime (no compilation, no temp files).  Since pygraphite2 **0.4.0** the
native library is bundled inside the wheel (``pygraphite2/_lib/``), so no
system install or vendored DLL is required on any platform:

1. ``pygraphite2.configure(path)`` / ``PYGRAPHITE2_LIBRARY_PATH``
2. system library (``find_library("graphite2")`` — apt/conda/brew)
3. wheel-bundled ``_lib/`` (shipped since 0.4.0)

So the same code path works on Windows, Linux and macOS.  uharfbuzz's own
graphite2 shaper is tried first (when the installed wheel bundles graphite2);
otherwise we fall back to ``pygraphite2``.
"""

from __future__ import annotations

import pygraphite2


def _upem_of(data: bytes) -> int:
    return int(pygraphite2.upem_from_ttf(data))


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
    back to ``pygraphite2`` (PyPI package — also cross-platform)."""
    try:
        return _shape_with_uharfbuzz(data, text, direction)
    except Exception:
        return _shape_with_pygraphite2(
            data, text, direction=direction, script=script, language=language, features=features
        )


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


def _shape_with_pygraphite2(
    data: bytes,
    text: str,
    *,
    direction: str = "auto",
    script: str = "",
    language: str = "",
    features: dict | None = None,
) -> dict:
    """Graphite shaping via ``pygraphite2`` (PyPI — cross-platform).

    The native ``libgraphite2`` is discovered at runtime by ``pygraphite2``
    (env var → system → bundled/vendored).  Script is auto-detected by
    pygraphite2; lang/features are passed through when provided.
    """
    glyphs_raw = pygraphite2.shape(
        data,
        text,
        direction="rtl" if direction == "rtl" else "ltr",
        lang=language or None,
        features=features or None,
    )
    glyphs: list[dict] = [
        {
            "g": g.gid,
            "cl": g.cluster,
            "dx": int(round(g.x_offset)),
            "dy": int(round(g.y_offset)),
            "ax": int(round(g.x_advance)),
            "ay": int(round(g.y_advance)),
            "flags": 0,
        }
        for g in glyphs_raw
    ]
    stage = {"m": "Graphite shaping", "glyphs": glyphs, "depth": 0, "effective": True}
    return {
        "upem": _upem_of(data),
        "glyph_count": len(glyphs),
        "stages": [stage],
        "final": glyphs,
        "messages": [pygraphite2.library_info()],
        "engine": "graphite",
    }
