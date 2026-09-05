"""DirectWrite text shaping for the OpenType Test Framework.

Uses the ``pydwshape`` package (``pip install pydwshape``) — a Windows-only
PyO3/abi3 extension (``cp39-abi3-win_amd64``) that shapes entirely with a
bundled, app-local **DWriteCore** (version-pinned; no system ``dwrite.dll`` /
``TextShaping.dll`` is loaded, so there is no DLL-hijack surface, and no
subprocess is spawned).

Unlike hand-rolled COM/ctypes DirectWrite bindings — and unlike the old
``dwriteshapepy`` Cython wrapper, which had no buffer-message callback — the
extension installs a process-local per-lookup hook and returns the *full*
babelsoft ``/api/opentype/shape`` trace (the DirectWrite analogue of the
HarfRust engine).  DirectWrite therefore now reports per-stage glyph
mutations instead of only the final run.
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
) -> dict:
    """Shape text with DirectWrite (via pydwshape / bundled DWriteCore).

    Returns the full per-lookup trace dict in the babelsoft
    ``/api/opentype/shape`` schema (``upem``, ``glyph_count``, ``stages``,
    ``final``, ``messages``, ``engine``).  ``features`` uses the same
    ``{tag: bool}`` convention as the HarfBuzz/HarfRust engines; DWriteCore
    applies script-required features unconditionally, so toggles only affect
    *optional* features.  Glyph names are appended by the server.
    """
    try:
        import pydwshape
    except ImportError:
        raise ImportError(
            "The DirectWrite engine requires the 'pydwshape' package "
            "(a Windows-only DWriteCore per-lookup shaper). Install it with: "
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
    )
