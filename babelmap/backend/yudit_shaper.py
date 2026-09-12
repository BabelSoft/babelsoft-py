"""Yudit step-by-step shaping trace (decompose → reorder → GSUB → GPOS).

Backed by ``pyyudit`` (github.com/Kushim-Jiang/pyyudit) — ctypes bindings over
the shaping engine that the **Yudit** Unicode editor (Gaspar Sinai) uses for
complex scripts.  What the trace looks like depends on the script, because
``pyyudit`` reports whatever Yudit's pipeline emits:

* **Arabic / Syriac / Latin** (since 0.2.0) — a real OpenType trace::

      input → split → join → gindex → rlig / calt / liga / kern / mark / mkmk
      → reorder → shaped

  with per-lookup rows (``start lookup N feature 'rlig'`` / ``skipped lookup …
  because no glyph matches`` / ``end lookup``), exactly the shape the HarfBuzz
  and HarfRust engines produce — so Arabic joining + RTL ordering now match
  HarfBuzz glyph-for-glyph.

* **Indic** — Yudit's own (non-OTL) pipeline::

      input → decompose → reorder → gindex → nukt / akhn / rphf / blwf / half /
      vatu / pres / abvs / blws / psts / haln → clean → abvm / blwm / dist /
      gpos_final → shaped

  These substitutions need the font to register the **first-version** Indic tags
  (``deva`` / ``beng`` / ``gujr`` / ``guru`` / ``knda`` / ``mlym`` / ``orya`` /
  ``taml`` / ``telu``).  A font that only registers the second-version tags
  (``dev2`` / ``bng2`` / … — Nirmala UI registers ``dev2 bng2 gjr2 gur2 knd2
  mlm2 ory2 tel2 tml2`` plus ``sinh``) matches **no** feature for those scripts:
  the buffer comes back unchanged and the trace shows **0 ``start lookup``
  rows**, which is correct behaviour, not a failure.  Applying the ``…2``
  features is deliberately not done — their feature order differs, so forcing
  them would produce *wrong* glyphs rather than merely different ones.  With a
  font that does have ``deva`` (e.g. NotoSansDevanagari) Yudit shapes
  ``नमस्ते`` glyph-for-glyph like HarfBuzz (67 lookup rows).

  Two situations that the trace already distinguishes, so "why did nothing
  happen?" is answerable from the output alone: **0 ``start lookup`` rows** =
  the font has no feature for that script tag; **``skipped lookup N feature
  'x' because no glyph matches``** = the feature was found and ran, the text
  just did not hit it.

  Because HarfBuzz reaches Indic through ``dev2`` while Yudit uses ``deva``,
  the two engines are applying *different* shaping models — a ``dev2``-only font
  like Nirmala UI is therefore not a meaningful A/B comparison for Indic.

Either way the engine supplies a real ``effective`` flag per stage (did the
buffer change?), and the rows are pushed through the shared Crowbar assembly
(:func:`babelmap.backend.opentype._build_trace_stages`) so the frontend renders
Yudit exactly like the other engines; the pipeline is flat, so every row ends up
at ``depth = 0``.

Version notes (measured against Nirmala UI / Segoe UI, 0.2.0 → 0.3.0):
``0.2.0`` brought Arabic/Syriac joining, RTL ordering and a real per-lookup OTL
trace; ``0.3.0`` fixed the position fields — ``dx`` is a genuine x offset again
(it used to repeat the previous glyph's advance, ``dx[i] == ax[i-1]``), Indic
advances are positive, and Latin/Arabic advance+offset runs now match HarfBuzz
exactly (identical rendered glyph x positions).

Rows before Yudit's ``gindex`` (cmap) step hold **codepoints**, not glyph ids:
``input`` / ``split`` / ``join`` / ``decompose`` and the Indic ``reorder``.  They
are flagged ``cps`` on the row — the same idea as Crowbar's ``glyphs: false``
flag on its pre-shaping row — so :func:`babelmap.backend.opentype.used_glyph_ids`
leaves them out of the glyph-name lookup and the dialog labels them ``U+XXXX``
(and skips outline rendering for them).  Informative in its own right: Arabic
``join`` shows the presentation-form codepoints Yudit chose, e.g. ``U+FEE3``.

Yudit has no per-call script / direction / language / feature selection API — it
segments and scripts the text itself (like Uniscribe and DWriteCore), so those
parameters are accepted for interface parity and ignored.

Native library: ``pyyudit`` ships per-platform wheels (``win_amd64`` /
``manylinux`` / ``macosx``) that bundle the matching ``yudit_shaper.dll`` /
``libyudit_shaper.so`` / ``libyudit_shaper.dylib`` in ``pyyudit/_lib/``.  For a
``py3-none-any`` install (or an unsupported platform) the library has to come
from ``PYYUDIT_LIBRARY_PATH`` / ``pyyudit.configure(path)``, or be built with
CMake from github.com/Kushim-Jiang/pyyudit; ``shape_with_yudit`` then raises
``LibraryNotFound`` carrying that hint.  Since 0.1.1 the wheels also install
Yudit's property maps under ``pyyudit/_lib/data/`` (``indic.my``,
``charclass.my``, ``cluster.my``, ``shape.my``, …), which the pipeline reads for
Indic reordering / Arabic joining — 0.1.0 shipped neither those maps nor a
Windows/macOS library, and 0.1.x never applied Arabic joining at all, hence the
``pyyudit>=0.3.0`` floor in ``pyproject.toml``.

Fonts must be **single-face** sfnt files: Yudit's ``SFontTTF`` rejects TrueType
/OpenType collections (``ttcf``), which ``shape_with_yudit`` turns into a clear
``FontError`` instead of a bare ``error code -2``.  The HTTP API never hits that
path — ``babelmap.backend.font_source`` flattens the requested face first, and
only ``font_delivery="raw"`` skips the flattening and surfaces this error.  Note
also that Yudit's first stage (``input``) carries *codepoints*, not glyph ids —
the frontend's glyph-name lookup therefore cannot label that one row.

Requires:  pip install "pyyudit>=0.3.0"
"""

from __future__ import annotations

import io

# Engine key reported in the trace dict — the frontend draws its badge from it.
_ENGINE = "yudit"

_BUILD_HINT = (
    "yudit_shaper native library not found. pyyudit's platform wheels bundle it "
    "in pyyudit/_lib/, so this interpreter/platform is probably running a "
    "py3-none-any install: either install a platform wheel, point "
    "PYYUDIT_LIBRARY_PATH / pyyudit.configure() at a yudit_shaper.dll / "
    "libyudit_shaper.so / libyudit_shaper.dylib, or build one with CMake from "
    "github.com/Kushim-Jiang/pyyudit (needs the Yudit 3.1.0 sources)."
)

# 'ttcf' — TrueType/OpenType Collection.
_TTC_MAGIC = b"ttcf"


def _library_hint() -> str:
    """Actionable message for a missing / unloadable native library."""
    try:
        import pyyudit

        info = pyyudit.library_info()
    except Exception:  # pragma: no cover - pyyudit itself is broken
        return _BUILD_HINT
    order = info.get("search_order")
    if not isinstance(order, (list, tuple)):
        return _BUILD_HINT
    return f"{_BUILD_HINT} Searched: {', '.join(str(step) for step in order)}."


def _fallback_metrics(data: bytes, font_index: int) -> tuple[int, int]:
    """``(upem, glyph_count)`` from fontTools when the engine does not report them."""
    upem, glyph_count = 0, 0
    try:
        from fontTools.ttLib import TTFont

        tt = TTFont(io.BytesIO(data), fontNumber=int(font_index), lazy=True)
        upem = int(tt["head"].unitsPerEm)  # type: ignore[attr-defined]
        glyph_count = int(tt["maxp"].numGlyphs)  # type: ignore[attr-defined]
    except Exception:
        pass
    return upem or 2048, glyph_count


def shape_with_yudit(
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
    """Shape ``text`` with Yudit and return a step-by-step trace.

    Result schema matches the other trace engines (``upem``, ``glyph_count``,
    ``stages`` (each {m, glyphs, depth, effective}), ``final``, ``messages``,
    ``engine``); glyph names / font info / SVG are appended by the server.

    ``direction`` / ``script`` / ``language`` / ``features`` / ``variations`` are
    accepted for interface parity and ignored — Yudit derives all of them from
    the text and the font.
    """
    from babelmap.backend.opentype import _build_trace_stages

    import pyyudit

    if not pyyudit.is_available():
        raise pyyudit.LibraryNotFound(_library_hint())

    if bytes(data[:4]) == _TTC_MAGIC:
        # Yudit's SFontTTF only reads single-face sfnt files; without this check
        # the failure surfaces as "BAD TTF file ... sfntVersion=74746366" on
        # stderr plus a bare "error code -2".
        raise pyyudit.FontError(
            "Yudit's font loader cannot open TrueType/OpenType collections "
            "(TTC/OTC). Extract the face first (fontTools: "
            "TTFont(path, fontNumber=N).save(out)) or pass a .ttf/.otf."
        )

    # Module-level helper: reads the font bytes, opens a YuditFont and runs the
    # traced shaping in one call.
    trace = pyyudit.shape_trace(bytes(data), text)

    # Yudit reports neither UPEM nor glyph count through the trace, so take both
    # from fontTools (cheap: head + maxp only) — face-aware for TTCs.
    upem, glyph_count = _fallback_metrics(data, font_index)

    # Yudit's own pipeline stages → the shared (message, buffer) row shape.  The
    # engine's `effective` flag is authoritative here, so pass it straight on:
    # the assembly pass only *adds* effective rows for nested lookup messages,
    # which Yudit does not emit.
    #
    # Everything before Yudit's `gindex` (= cmap) step holds *codepoints*, not
    # glyph ids — `input` / `split` / `join` / `decompose` and the Indic
    # `reorder`.  Those rows are flagged `cps` (Crowbar's `glyphs: false`) so the
    # UI shows U+XXXX for them instead of a bogus glyph name.
    pre_cmap = True
    rows: list[dict] = []
    for stage in trace.stages:
        if stage.m == "gindex":
            pre_cmap = False
        row = {
            "m": stage.m,
            "glyphs": [dict(g._asdict()) for g in stage.glyphs],
            "depth": 0,
            "effective": bool(stage.effective),
        }
        if pre_cmap:
            row["cps"] = True
        rows.append(row)

    filtered, final = _build_trace_stages(rows, show_all_lookups)
    if not final and rows:
        final = rows[-1]["glyphs"]
    if not filtered and rows:  # only when every stage was filtered away
        filtered = rows

    return {
        "upem": upem,
        "glyph_count": glyph_count,
        "stages": filtered,
        "final": final,
        "messages": [stage.m for stage in trace.stages],
        "engine": _ENGINE,
    }
