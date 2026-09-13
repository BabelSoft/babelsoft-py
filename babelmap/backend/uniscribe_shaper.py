"""Uniscribe (USP10) text shaping for the OpenType Test Framework.

Uses the ``pyusp`` package (``pip install pyusp``) — a PyO3/abi3 extension
(``cp39-abi3-*``) that runs the shaping **in-process**, so no GDI DC / HFONT /
ctypes boilerplate is needed and the font is passed as raw bytes.
``pyusp.__version__`` reports the native module version (handy when a fix seems
to have no effect — a stale wheel is the usual cause).

Two engine flavours are exposed through ``backend=``:

* ``backend="usp10"``  — Microsoft Uniscribe (Windows only).  The *published*
  wheel bundles only ``wineusp.dll``; the native backend drives the system
  ``usp10.dll`` (a dev/test wheel may pin an app-local copy, which the loader
  prefers when present).  Uniscribe has no per-lookup callback, so only a
  single whole-run stage is returned.
* ``backend="wineusp"`` — Wine's open-source Uniscribe reimplementation
  (``dlls/gdi32/uniscribe``, LGPL 2.1+), bundled per platform as
  ``wineusp.dll`` / ``libwineusp.so`` / ``libwineusp.dylib``.  Cross-platform
  (Windows/Linux/macOS) and — unlike native Uniscribe — it exposes a real
  per-lookup trace when ``trace=True`` (the DirectWrite/HarfRust analogue).

Feature records (``features=``) — since pyusp 0.6.0 the tags are packed in the
Uniscribe ``OPENTYPE_TAG`` byte order, so they finally *match* the font (0.5.0
and earlier byte-reversed them, which silently dropped every requested
feature).  Two consequences matter here:

* the list **replaces** the run's default GSUB feature set (system usp10 range
  semantics), it does not add to it — ``{"liga": True}`` applies exactly
  ``liga``;
* it is **refused** (``RuntimeError``) for ``backend="wineusp"``: the Wine port's
  ``ScriptShapeOpenType`` logs ``FIXME("Ranges not supported yet")`` and drops
  the records, so pyusp fails loudly instead of returning a shape that ignored
  them.  Toggling a feature therefore errors on the *Uniscribe (Wine)* engine —
  use ``uniscribe`` (native) for feature selection.

pyusp also ships a Windows-only ``backend="textshaping"`` (native
per-application trace from the system ``TextShaping.dll``, gated to validated
builds); BabelMap does not expose it, ``wineusp`` is the per-lookup tracer.
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
    as the HarfBuzz/HarfRust engines, but see the module docstring: it
    **replaces** the default feature set for the run, and a non-empty list on
    the ``wineusp`` engine raises (the Wine port cannot apply it).  Uniscribe
    only recognises legacy OpenType script tags (e.g. ``deva``, not ``dev2``).
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
