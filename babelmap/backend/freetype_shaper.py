"""FreeType raw cmap shaping for the OpenType Test Framework.

FreeType does not perform OpenType GSUB/GPOS shaping — this maps each code
point straight through the font's cmap (with a nominal advance), giving a
"no shaping" baseline to compare against HarfBuzz / Uniscribe / DirectWrite.

Requires:  pip install freetype-py
"""

from __future__ import annotations

import ctypes

_FT_LOAD_NO_HINTING = 2


def shape_with_freetype(
    path_or_b64: str,
    text: str,
    *,
    is_b64: bool = False,
    direction: str = "auto",
    script: str = "",
    language: str = "",
    features: dict | None = None,
) -> dict:
    import base64
    import os
    import tempfile

    import freetype

    tmp_path = None
    try:
        if is_b64:
            with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as f:
                f.write(base64.b64decode(path_or_b64))
                tmp_path = f.name
            font_path = tmp_path
        else:
            font_path = path_or_b64

        face = freetype.Face(font_path)
        upem = int(face.units_per_EM) or 2048
        face.set_char_size(upem * 64)

        glyphs: list[dict] = []
        for i, ch in enumerate(text):
            try:
                face.load_char(ch, _FT_LOAD_NO_HINTING)
                gid = int(face.get_char_index(ord(ch)))
                adv = float(face.glyph.advance.x) / 64.0
            except Exception:
                gid = 0
                adv = 0.0
            glyphs.append(
                {
                    "g": gid,
                    "cl": i,
                    "dx": 0,
                    "dy": 0,
                    "ax": int(round(adv)),
                    "ay": 0,
                    "flags": 0,
                }
            )

        stage = {
            "m": "FreeType cmap (no shaping)",
            "glyphs": glyphs,
            "depth": 0,
            "effective": True,
        }
        return {
            "upem": upem,
            "glyph_count": int(face.num_glyphs),
            "stages": [stage],
            "final": glyphs,
            "messages": ["FreeType cmap (no shaping)"],
            "engine": "freetype",
        }
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
