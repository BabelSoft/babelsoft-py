"""HarfRust step-by-step (per-lookup / per-stage) shaping trace.

Backed by ``pyharfrust2`` (github.com/Kushim-Jiang/pyharfrust2) — a PyO3
binding over a minimal harfrust fork that adds an optional per-stage trace
callback.  Its ``shape_trace`` returns raw (message, buffer-snapshot) rows
whose ``m`` strings match HarfBuzz's buffer messages; we run them through the
same Crowbar assembly (depth/effective/filter/cluster-remap) as the uharfbuzz
``opentype.shape_trace`` so the frontend renders both engines identically.

Requires:  pip install pyharfrust2
"""

from __future__ import annotations

import io


def _features_to_str(features) -> str | None:
    """Normalise ``{tag: bool|0|1}`` or an hb-shape feature string into a
    pyharfrust feature string (e.g. ``"+kern,-liga"``)."""
    if isinstance(features, str):
        s = features.strip()
        return s or None
    if not features:
        return None
    parts: list[str] = []
    for tag, val in features.items():
        tag = str(tag)
        if val is True or val == 1:
            parts.append(f"+{tag}")
        elif val is False or val == 0:
            parts.append(f"-{tag}")
        else:
            parts.append(f"{tag}={val}")
    return ",".join(parts) if parts else None


def _variations_to_str(variations) -> str | None:
    """Normalise ``{tag: value}`` into a pyharfrust variation string
    (e.g. ``"wght=700,wdth=85"``)."""
    if not variations:
        return None
    return ",".join(f"{tag}={value}" for tag, value in variations.items())


def shape_with_harfrust(
    data: bytes,
    text: str,
    *,
    direction: str = "auto",
    script: str = "",
    language: str = "",
    features=None,
    variations=None,
    show_all_lookups: bool = False,
    font_index: int = 0,
) -> dict:
    """Shape ``text`` with HarfRust and return a step-by-step trace.

    Result schema matches the HarfBuzz trace engine: ``upem``, ``glyph_count``,
    ``stages`` (each {m, glyphs, depth, effective}), ``final``, ``messages``,
    ``engine``.  Glyph names / font info / SVG are appended by the server.
    """
    from babelmap.backend.opentype import _build_trace_stages

    import pyharfrust2

    raw = pyharfrust2.shape_trace(
        bytes(data),
        text,
        direction=direction if direction and direction != "auto" else "auto",  # type: ignore[arg-type]
        script=script if script and script != "auto" else "",
        language=language or "",
        features=_features_to_str(features),
        variations=_variations_to_str(variations),
        face_index=int(font_index),
    )

    # Normalise the raw dump into rows matching the uharfbuzz path: the first
    # ("start of shaping") and last ("end of shaping") rows are effective;
    # intermediate message rows are not (the assembly pass fills them in when a
    # lookup actually changed the buffer).
    n = len(raw)
    rows: list[dict] = []
    for i, s in enumerate(raw):
        rows.append(
            {
                "m": s["m"],
                "glyphs": s.get("glyphs", []),
                "depth": 0,
                "effective": i == 0 or i == n - 1,
            }
        )

    filtered, final = _build_trace_stages(rows, show_all_lookups)

    # upem + glyph count from fontTools (cheap: head + maxp only).
    upem = 2048
    glyph_count = 0
    try:
        from fontTools.ttLib import TTFont

        tt = TTFont(io.BytesIO(data), fontNumber=int(font_index), lazy=True)
        upem = int(tt["head"].unitsPerEm)  # type: ignore[attr-defined]
        glyph_count = int(tt["maxp"].numGlyphs)
    except Exception:
        pass

    return {
        "upem": upem,
        "glyph_count": glyph_count,
        "stages": filtered,
        "final": final,
        "messages": [s["m"] for s in raw],
        "engine": "harfrust",
    }
