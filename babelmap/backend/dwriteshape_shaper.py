"""DirectWrite text shaping for the OpenType Test Framework.

Uses the ``pydwshape`` package (``pip install pydwshape``) — a PyO3/abi3
extension that shapes entirely **in-process**, with no subprocess and no
hand-rolled COM/ctypes bindings.

Two engine flavours are exposed through ``backend=``:

* ``backend="dwcore"`` — native Microsoft **DWriteCore** (Windows only;
  ``pydwshape`` is only shipped as a ``cp39-abi3-win_amd64`` wheel).  It uses
  a bundled, app-local DWriteCore (version-pinned; no system ``dwrite.dll`` /
  ``TextShaping.dll`` is loaded, so there is no DLL-hijack surface).  A
  process-local per-lookup hook returns the *full* babelsoft
  ``/api/opentype/shape`` trace (the DirectWrite analogue of the HarfRust
  engine).
* ``backend="winedwrite"`` — the standalone **Wine DWrite port**
  (cross-platform).  Since pydwshape 0.4.0 every wheel bundles it
  (``winedwrite.dll`` on Windows, ``libwinedwrite.so`` / ``.dylib``
  elsewhere); ``WDWRITE_LIB`` still overrides for a manual build.  Script is
  auto-detected from the text; Mongolian converges byte-identically to
  DWriteCore (other scripts can differ — that is the point of comparing).
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
    show_all_lookups: bool = False,
    backend: str = "dwcore",
) -> dict:
    """Shape text with DirectWrite (via pydwshape).

    Returns the full per-lookup trace dict in the babelsoft
    ``/api/opentype/shape`` schema (``upem``, ``glyph_count``, ``stages``,
    ``final``, ``messages``, ``engine``).  ``backend`` selects the engine
    (``"dwcore"`` native DWriteCore / ``"winedwrite"`` Wine DWrite port).
    ``features`` uses the same ``{tag: bool}`` convention as the
    HarfBuzz/HarfRust engines; DWriteCore applies script-required features
    unconditionally, so toggles only affect *optional* features.  Glyph
    names are appended by the server.
    """
    try:
        import pydwshape
    except ImportError:
        raise ImportError(
            "The DirectWrite engine requires the 'pydwshape' package "
            "(a DWriteCore per-lookup shaper). Install it with: "
            "pip install pydwshape"
        )
    return pydwshape.shape_with_dwrite(
        data,
        text,
        direction=direction,
        script=script,
        language=language,
        features=features,
        show_all_lookups=bool(show_all_lookups),
        backend=backend,
    )
