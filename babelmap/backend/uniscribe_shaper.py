"""Uniscribe (USP10) text shaping for the OpenType Test Framework.

Uses the ``pyusp`` package (``pip install pyusp``) — a PyO3/abi3 extension
(``cp39-abi3-*``) that runs the shaping **in-process**, so no GDI DC / HFONT /
ctypes boilerplate is needed and the font is passed as raw bytes.

Two engine flavours are exposed through ``backend=``:

* ``backend="usp10"``  — Microsoft Uniscribe (Windows only).  The wheel
  bundles a version-pinned app-local ``usp10.dll`` (dev/test) and falls back
  to the system copy.  Uniscribe has no per-lookup callback, so only a single
  whole-run stage is returned.
* ``backend="wineusp"`` — Wine's open-source Uniscribe reimplementation
  (``dlls/gdi32/uniscribe``, LGPL 2.1+), bundled per platform as
  ``wineusp.dll`` / ``libwineusp.so`` / ``libwineusp.dylib``.  Cross-platform
  (Windows/Linux/macOS) and — unlike native Uniscribe — it exposes a real
  per-lookup trace when ``trace=True`` (the DirectWrite/HarfRust analogue).
"""

from __future__ import annotations


def shape_with_uniscribe(
    data: bytes,
    text: str,
    *,
    direction: str = "auto",
    script: str = "",
    language: str = "",
    features: dict | None = None,
    backend: str = "usp10",
    trace: bool = False,
) -> dict:
    """Shape ``text`` with a Uniscribe engine and return the final glyph run.

    Returns the full babelsoft ``/api/opentype/shape`` dict (``upem``,
    ``glyph_count``, ``stages``, ``final``, ``messages``, ``engine``) — the
    shape is compatible with ``shape_trace()``.

    ``backend`` selects the engine (``"usp10"`` native / ``"wineusp"`` Wine,
    see the module docstring).  ``trace=True`` requests a real per-lookup
    trace timeline from the Wine engine (native ``usp10`` has no trace hook
    and ignores it).  ``features`` uses the same ``{tag: bool}`` convention
    as the HarfBuzz/HarfRust engines; Uniscribe only recognises legacy
    OpenType script tags (e.g. ``deva``, not ``dev2``).
    """
    try:
        import pyusp
    except ImportError:
        raise ImportError(
            "The Uniscribe engine requires the 'pyusp' package "
            "(a Uniscribe per-lookup shaper). Install it with: "
            "pip install pyusp"
        )
    return pyusp.shape_with_uniscribe(
        data,
        text,
        direction=direction,
        script=script,
        language=language,
        features=features,
        backend=backend,
        trace=bool(trace),
    )
