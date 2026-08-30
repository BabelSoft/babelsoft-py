"""DirectWrite text shaping for the OpenType Test Framework.

Uses the official microsoft/DWriteShapePy package (``pip install
dwriteshapepy``) — a Cython wrapper over DirectWrite's IDWriteTextAnalyzer,
modeled after uharfbuzz.  This works on systems where hand-rolled comtypes
DirectWrite bindings fail (e.g. factory/face quirks), because the extension is
compiled against the real DirectWrite headers and uses the correct factory
path.

Like Uniscribe, DirectWrite has no buffer-message callback → we only produce
the *final* glyph run (no step-by-step trace).
"""

from __future__ import annotations


def shape_with_dwrite(
    data: bytes,
    text: str,
    *,
    direction: str = "auto",
    script: str = "",
    language: str = "",
    features: dict | None = None,
) -> dict:
    """Shape text with DirectWrite (via dwriteshapepy). Returns the final glyph
    run in a shape_trace-compatible structure."""
    try:
        import dwriteshapepy as dw
    except ImportError:
        raise ImportError(
            "The DirectWrite engine requires the 'dwriteshapepy' package "
            "(a Cython wrapper over IDWriteTextAnalyzer). Install it with: "
            "pip install dwriteshapepy"
        )

    face = dw.Face(data)
    font = dw.Font(face)
    upem = int(font.upem) or 2048

    buf = dw.Buffer()
    buf.add_str(text)
    if language:
        try:
            buf.language = language
        except Exception:
            pass

    feat = {}
    if features:
        for tag, val in features.items():
            if isinstance(val, bool):
                feat[str(tag)] = val
            elif val in (1, 0):
                feat[str(tag)] = bool(val)

    dw.shape(font, buf, feat)

    infos = list(buf.glyph_infos)
    poss = list(buf.glyph_positions)
    glyphs: list[dict] = []
    used: set[int] = set()
    for gi, po in zip(infos, poss):
        gid = int(gi.codepoint)
        used.add(gid)
        glyphs.append(
            {
                "g": gid,
                "cl": int(gi.cluster),
                "dx": int(round(getattr(po, "x_offset", 0) or 0)),
                "dy": int(round(getattr(po, "y_offset", 0) or 0)),
                "ax": int(round(getattr(po, "x_advance", 0) or 0)),
                "ay": int(round(getattr(po, "y_advance", 0) or 0)),
                "flags": 0,
            }
        )

    # Glyph names (font.glyph_to_string)
    names = {}
    for gid in used:
        try:
            n = font.glyph_to_string(gid)
            if n:
                names[gid] = n
        except Exception:
            pass

    stage = {
        "m": "DirectWrite shaping",
        "glyphs": glyphs,
        "depth": 0,
        "effective": True,
    }
    return {
        "upem": upem,
        "glyph_count": len(glyphs),
        "stages": [stage],
        "final": glyphs,
        "messages": ["DirectWrite shaping"],
        "glyph_names": names,
        "engine": "directwrite",
    }
