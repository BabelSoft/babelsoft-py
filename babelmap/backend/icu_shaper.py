"""Arabic text reshaping for the OpenType Test Framework.

ICU's ``u_shapeArabic`` performed Arabic joining/reshaping of the input text
(only affects Arabic-script text; other scripts pass through unchanged).

We now use the pure-Python ``arabic-reshaper`` package instead — its output
matches ICU's u_shapeArabic (e.g. ``سلام`` → ``ﺳﻼﻡ`` with the lam-alef ligature
U+FEB3) and needs no vendored DLL, so the engine is fully cross-platform.

Unlike a full shaping engine, this does not produce glyph ids — it returns a
*reshaped Unicode string*.  We then map each code point through the font's cmap
(like the FreeType raw engine) to obtain a glyph run for display.
"""

from __future__ import annotations


def shape_with_icu(
    data: bytes,
    text: str,
    *,
    direction: str = "auto",
    script: str = "",
    language: str = "",
    features: dict | None = None,
) -> dict:
    """Shape text with Arabic reshaping (arabic-reshaper) + cmap. Returns the
    final glyph run in a shape_trace-compatible structure."""
    import arabic_reshaper
    import freetype

    reshaped = arabic_reshaper.reshape(text)

    import io
    from fontTools.ttLib import TTFont

    tt = TTFont(io.BytesIO(data), lazy=True)
    upem = tt["head"].unitsPerEm or 2048
    tt.close()

    # temporary file for freetype (freetype-py needs a path or buffer via memory face?)
    import tempfile
    import os

    tmp = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as f:
            f.write(data)
            tmp = f.name
        face = freetype.Face(tmp)
        face.set_char_size(upem * 64)
        glyphs: list[dict] = []
        for i, ch in enumerate(reshaped):
            try:
                face.load_char(ch, 2)  # FT_LOAD_NO_HINTING
                gid = int(face.get_char_index(ord(ch)))
                adv = float(face.glyph.advance.x) / 64.0
            except Exception:
                gid = 0
                adv = 0.0
            glyphs.append({"g": gid, "cl": i, "dx": 0, "dy": 0, "ax": int(round(adv)), "ay": 0, "flags": 0})
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    stage = {"m": "Arabic reshape shaping", "glyphs": glyphs, "depth": 0, "effective": True}
    return {
        "upem": upem,
        "glyph_count": len(glyphs),
        "stages": [stage],
        "final": glyphs,
        "messages": [f"Arabic reshaped {len(text)} -> {len(reshaped)} chars"],
        "engine": "icu",
    }
