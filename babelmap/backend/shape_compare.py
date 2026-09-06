"""Cross-engine shaping comparison / diagnostic CLI.

Shapes a piece of text with a font through every shaping engine and prints,
for each engine, the final glyph run plus its trace/log.  The point is to
spot engine differences (HarfBuzz vs HarfRust vs Uniscribe vs DirectWrite vs
BabelScript vs …) on a given font + text — e.g. complex scripts where one
engine reshapes/reorders and another does not.

Run from the repo root (so ``babelmap`` is importable):

    .\\.venv\\Scripts\\python.exe -m babelmap.backend.shape_compare \\
        --font <font-path> --text <text>           # any font/text
    .\\.venv\\Scripts\\python.exe -m babelmap.backend.shape_compare  # default

Default case (no args): shapes ``र्कि`` (RA + VIRAMA + KA + i-matra — a classic
Indic shaping probe) with the local Adobe Devanagari font if it exists.

Note: pass text via ``--text`` only when your shell survives non-ASCII argv
(PowerShell 5.1 mangles it; there just run without ``--text`` or call this
module from Python instead).  Only the freetype engine takes a font path; all
the others (incl. uniscribe / directwrite and their Wine variants) take
in-memory font bytes.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

# Default probe: Devanagari "rk-ka-i" — catches whether an engine does Indic
# reordering / GSUB at all (correct shaping collapses the 4 codepoints to 2).
DEFAULT_FONT = Path(r"C:\Softwares\Acrobat\main\Acrobat DC\Resource\Font\AdobeDevanagari-Regular.otf")
DEFAULT_TEXT = "\u0930\u094d\u0915\u093f"  # र्कि

# engine key → (display label, needs font path rather than bytes)
ENGINES: dict[str, tuple[str, bool]] = {
    "harfbuzz": ("harfbuzz  (uharfbuzz OT, full step trace)", False),
    "harfbuzz_fallback": ("harfbuzz_fallback  (cmap direct)", False),
    "harfrust": ("harfrust  (pyharfrust2)", False),
    "babelscript": ("babelscript  (pure GSUB/GPOS)", False),
    "graphite": ("graphite  (graphite2)", False),
    "icu": ("icu  (arabic-reshaper)", False),
    "freetype": ("freetype  (cmap only)", True),
    "uniscribe": ("uniscribe  (usp10, single run)", False),
    "uniscribe_wine": ("uniscribe_wine  (Wine usp10, per-lookup trace)", False),
    "directwrite": ("directwrite  (DWriteCore, full trace)", False),
    "directwrite_wine": ("directwrite_wine  (Wine DWrite, full trace)", False),
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Glyph-name context, filled by load_font() (fontTools, independent of shapers).
_order: list[str] = []
_upem = 0
_family = "?"


def load_font(data: bytes) -> None:
    """Fill the module-level glyph-order context from fontTools."""
    global _order, _upem, _family
    try:
        from fontTools.ttLib import TTFont

        tt = TTFont(io.BytesIO(data), lazy=True)
        _order = tt.getGlyphOrder()
        _upem = int(tt["head"].unitsPerEm)
        _family = tt["name"].getDebugName(1) or tt["name"].getDebugName(4) or "?"
    except Exception as e:  # pragma: no cover - font is expected to be valid
        print(f"fontTools failed: {e}")
        raise


def gname(gid: int) -> str:
    if 0 <= gid < len(_order):
        n = _order[gid]
        if n and not n.startswith(("glyph", "gid")):
            return n
    return f"gid{gid}"


def fmt_glyphs(glyphs: list[dict]) -> str:
    return " | ".join(f"{gname(g['g'])}({g['g']}) cl={g.get('cl')} ax={g.get('ax')}" for g in glyphs)


def _shape(key: str, data: bytes, path: Path, text: str) -> dict:
    """Dispatch one engine call.  Raises on engine failure."""
    if key == "harfbuzz":
        from babelmap.backend.opentype import shape_trace

        return shape_trace(data, text)
    if key == "harfbuzz_fallback":
        from babelmap.backend.opentype import shape_flat

        return shape_flat(data, text, shapers=["fallback"])
    if key == "harfrust":
        from babelmap.backend.harfrust_shaper import shape_with_harfrust

        return shape_with_harfrust(data, text)
    if key == "babelscript":
        from babelmap.backend.babelscript_shaper import shape_with_babelscript

        return shape_with_babelscript(data, text)
    if key == "graphite":
        from babelmap.backend.graphite_shaper import shape_with_graphite

        return shape_with_graphite(data, text)
    if key == "icu":
        from babelmap.backend.icu_shaper import shape_with_icu

        return shape_with_icu(data, text)
    if key == "freetype":
        from babelmap.backend.freetype_shaper import shape_with_freetype

        return shape_with_freetype(str(path), text, is_b64=False)
    if key == "uniscribe":
        from babelmap.backend.uniscribe_shaper import shape_with_uniscribe

        return shape_with_uniscribe(data, text, backend="usp10")
    if key == "uniscribe_wine":
        from babelmap.backend.uniscribe_shaper import shape_with_uniscribe

        return shape_with_uniscribe(data, text, backend="wineusp", trace=True)
    if key == "directwrite":
        from babelmap.backend.dwriteshape_shaper import shape_with_dwrite

        return shape_with_dwrite(data, text, backend="dwcore")
    if key == "directwrite_wine":
        from babelmap.backend.dwriteshape_shaper import shape_with_dwrite

        return shape_with_dwrite(data, text, backend="winedwrite")
    raise KeyError(key)


def run_engine(key: str, label: str, data: bytes, path: Path, text: str) -> dict:
    """Shape with one engine and print its detail block."""
    print(f"\n{'=' * 78}\n  {label}\n{'=' * 78}")
    try:
        r = _shape(key, data, path, text)
    except Exception as e:  # engine failure (e.g. no Silf for graphite)
        print(f"  !! {type(e).__name__}: {e}")
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    print(f"  upem={r.get('upem')}  glyph_count={r.get('glyph_count')}")
    final = r.get("final") or []
    print(f"  FINAL ({len(final)}):\n    {fmt_glyphs(final)}")
    stages = r.get("stages") or []
    msgs = r.get("messages") or []
    if stages:
        rows = []
        for s in stages:
            m = s.get("m") or ""
            gs = s.get("glyphs") or []
            if m:
                rows.append(m)
            if m in ("Start of shaping", "End of shaping") or s.get("effective"):
                rows.append(f"      glyphs: {fmt_glyphs(gs)}")
        print(f"  TRACE/stages ({len(stages)}):")
        for line in rows:
            print(f"    {line}")
    else:
        print(f"  MESSAGES ({len(msgs)}):")
        for i, m in enumerate(msgs):
            print(f"    [{i}] {m}")
    return {"ok": True, "gids": [g["g"] for g in final], "nstages": len(stages)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m babelmap.backend.shape_compare",
        description="Shape text across every shaping engine and compare results.",
    )
    ap.add_argument("--font", default=str(DEFAULT_FONT), help="Font file (.ttf/.otf).")
    ap.add_argument("--text", default=DEFAULT_TEXT, help="Text to shape (default: र्कि).")
    ap.add_argument(
        "--engines",
        default=",".join(ENGINES),
        help=f"Comma-separated subset of: {', '.join(ENGINES)} (default: all).",
    )
    args = ap.parse_args(argv)

    font = Path(args.font)
    if not font.exists():
        print(
            f"font not found: {font}\n"
            "Pass an existing font with --font (the default assumes the local "
            "Acrobat Adobe Devanagari font).",
            file=sys.stderr,
        )
        return 1
    text = args.text
    wanted = [e.strip() for e in args.engines.split(",") if e.strip()]
    bad = [e for e in wanted if e not in ENGINES]
    if bad:
        print(f"unknown engine(s): {bad}", file=sys.stderr)
        return 1

    data = font.read_bytes()
    load_font(data)
    print(f"font: {font}\nfamily: {_family}  upem={_upem}  glyphs={len(_order)}")
    print(f"text: {text}  =  " + " ".join(f"U+{ord(c):04X}" for c in text))

    summary: dict[str, dict] = {}
    for key in wanted:
        label, _ = ENGINES[key]
        summary[key] = run_engine(key, label, data, font, text)

    # ── One-line comparison summary ──────────────────────────────────────
    print(f"\n{'=' * 78}\n  SUMMARY  (final glyph ids per engine)\n{'=' * 78}")
    for key in wanted:
        s = summary[key]
        if s["ok"]:
            print(f"  {key:18} -> {len(s['gids'])} glyph  {s['gids']}  ({s['nstages']} stages)")
        else:
            print(f"  {key:18} -> ERROR  {s['error']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
