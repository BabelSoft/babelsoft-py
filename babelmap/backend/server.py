"""BabelMap Python Backend — FastAPI server. Start: python backend/server.py"""

from __future__ import annotations

import base64
import bisect
import io
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BABELLIB = REPO_ROOT / "babellib"
# Both roots must be on sys.path: the repo root (for `babelmap.*`, incl. the
# uvicorn reloader's `babelmap.backend.server:app`) and babellib/ (for `babelsoft.*`).
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BABELLIB))

import logging

from babelsoft.unicode.core import Unicode
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from babelmap.backend.errors import PROBE_ERRORS

logger = logging.getLogger(__name__)

app = FastAPI(title="BabelMap Backend", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

GRID_ROWS, GRID_COLS = 8, 16
VALID_PLANES = list(range(17))  # 0–16, all Unicode planes

# ── Blocks + assigned code points (reused from babelsoft/unicode/core.py) ──
_ASSIGNED_CPS = Unicode._assigned_codepoints()
_BLOCK_TABLE, _BLOCK_NAMES = Unicode._block_data()

_ALL_BLOCKS: list[dict] = []
for _s, _e, _idx in _BLOCK_TABLE:
    _ALL_BLOCKS.append(
        {
            "name": _BLOCK_NAMES[_idx],
            "start": _s,
            "end": _e,
            "count": _e - _s + 1,
            "plane": _s >> 16,
            "assigned": bisect.bisect_right(_ASSIGNED_CPS, _e) - bisect.bisect_left(_ASSIGNED_CPS, _s),
        }
    )

# Index: blocks_by_plane[p] = [blocks for plane p]
_blocks_by_plane: dict[int, list[dict]] = {}
for b in _ALL_BLOCKS:
    _blocks_by_plane.setdefault(b["plane"], []).append(b)

# Pre-compute max scroll per plane (last block end)
_max_scroll_by_plane: dict[int, int] = {}
for p, blks in _blocks_by_plane.items():
    _max_scroll_by_plane[p] = (blks[-1]["end"] - p * 0x10000) // GRID_COLS


def _is_assigned(cp: int) -> bool:
    """True if cp is an assigned character (reused src UnicodeData)."""
    i = bisect.bisect_left(_ASSIGNED_CPS, cp)
    return i < len(_ASSIGNED_CPS) and _ASSIGNED_CPS[i] == cp


def _find_block(cp: int) -> dict | None:
    """Binary search for the block containing cp. Returns None for gaps."""
    lo, hi = 0, len(_ALL_BLOCKS) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        b = _ALL_BLOCKS[mid]
        if cp < b["start"]:
            hi = mid - 1
        elif cp > b["end"]:
            lo = mid + 1
        else:
            return b
    return None


def _find_block_fast(cp: int) -> dict:
    """Like _find_block but never returns None — clamps to nearest."""
    b = _find_block(cp)
    if b is not None:
        return b
    # Fallback: return a synthetic block for unassigned ranges
    plane = cp >> 16
    return {
        "name": "Unassigned",
        "start": cp & ~0xF,
        "end": min((cp & ~0xF) + 15, plane * 0x10000 + 0xFFFF),
        "count": 16,
        "plane": plane,
    }


# ── Font helpers (kept for /api/glyph endpoint) ────────────────────
_font_cache: dict = {}


def _get_font(family: str, size: int):
    k = f"{family}:{size}"
    if k not in _font_cache:
        try:
            from PIL import ImageFont

            fp = _find_font_file(family)
            _font_cache[k] = ImageFont.truetype(fp, size) if fp else ImageFont.load_default()
        except PROBE_ERRORS:
            from PIL import ImageFont

            _font_cache[k] = ImageFont.load_default()
    return _font_cache[k]


def _find_font_file(family: str) -> str | None:
    try:
        if sys.platform == "win32":
            wd = Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts"
            for n in [
                f"{family}.ttf",
                f"{family}.otf",
                f"{family.replace(' ','')}.ttf",
                f"{family.lower()}.ttf",
                "Arial.ttf",
            ]:
                p = wd / n
                if p.exists():
                    return str(p)
        return None
    except PROBE_ERRORS:
        return None


def _render_glyph(cp: int, family: str, size: int = 16) -> str | None:
    try:
        from PIL import Image, ImageDraw

        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        f = _get_font(family, size)
        ch = chr(cp)
        bb = d.textbbox((0, 0), ch, font=f)
        d.text(
            ((32 - (bb[2] - bb[0])) / 2 - bb[0], (32 - (bb[3] - bb[1])) / 2 - bb[1]), ch, fill=(0, 0, 0, 255), font=f
        )
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except PROBE_ERRORS:
        return None


# ── API ──────────────────────────────────────────────────────────────


@app.get("/api/planes")
def list_planes():
    return [
        {
            "plane": p,
            "name": Unicode.get_plane_display_name(p),
            "abbreviation": Unicode.get_plane_abbreviation(p),
            "rangeStart": p * 0x10000,
            "rangeEnd": p * 0x10000 + 0xFFFF,
        }
        for p in VALID_PLANES
    ]


@app.get("/api/blocks")
def list_all_blocks():
    return [b for b in _ALL_BLOCKS if b["plane"] in VALID_PLANES and not (0xD800 <= b["start"] <= 0xDFFF)]


@app.get("/api/blocks/{plane}")
def list_blocks_for_plane(plane: int):
    return _blocks_by_plane.get(plane, [])


def _build_row(row_start: int, pe: int, Unicode) -> list[dict]:
    """Build one grid row starting at row_start."""
    rd: list[dict] = []
    for c in range(GRID_COLS):
        cp = row_start + c
        if cp > pe or cp > 0x10FFFF or (0xD800 <= cp <= 0xDFFF):
            rd.append({"codepoint": -1, "char_name": None})
        elif not _is_assigned(cp):
            rd.append({"codepoint": cp, "char_name": None, "reserved": True})
        else:
            rd.append({"codepoint": cp, "char_name": _safe_name(Unicode, cp)})
    return rd


# Pre-computed stitched rows per plane: all blocks concatenated, no gaps, +7 pad rows
# Cache keyed by (plane, filter_no_block)
_plane_rows: dict[tuple[int, bool], list[dict]] = {}
_plane_max_scroll: dict[tuple[int, bool], int] = {}
_plane_cp_to_scroll: dict[tuple[int, bool], dict[int, int]] = {}


def _build_plane_rows(plane: int, filter_no_block: bool = True):
    """Build the full stitched row list for a plane (cached).

    When filter_no_block=True (default): only assigned blocks, gaps removed.
    When filter_no_block=False: all rows from plane start to plane end.
    """
    key = (plane, filter_no_block)
    if key in _plane_rows:
        return
    from babelsoft.unicode.core import Unicode

    ps = plane * 0x10000
    pe = min(ps + 0xFFFF, 0x10FFFF)
    rows: list[dict] = []
    cp_map: dict[int, int] = {}
    blk_prev = ""

    if filter_no_block:
        # Current behavior: iterate only through assigned blocks
        for b in _ALL_BLOCKS:
            if b["plane"] != plane:
                continue
            # Skip surrogate blocks (U+D800-U+DFFF) — not real characters
            if 0xD800 <= b["start"] <= 0xDFFF:
                continue
            row_start = (b["start"] // GRID_COLS) * GRID_COLS
            end_aligned = (b["end"] // GRID_COLS) * GRID_COLS
            while row_start <= end_aligned:
                rd = _build_row(row_start, pe, Unicode)
                is_boundary = b["name"] != blk_prev
                rows.append(
                    {
                        "cells": rd,
                        "row_start": row_start,
                        "block_name": b["name"],
                        "block_start": b["start"],
                        "block_end": b["end"],
                        "block_assigned": b.get("assigned", b["end"] - b["start"] + 1),
                        "block_boundary": is_boundary,
                    }
                )
                # Map all codepoints in this row to this stitched scroll index
                scroll_idx = len(rows) - 1
                for c in range(GRID_COLS):
                    cp = row_start + c
                    if cp <= pe and cp <= 0x10FFFF and not (0xD800 <= cp <= 0xDFFF):
                        cp_map[cp] = scroll_idx
                blk_prev = b["name"]
                row_start += GRID_COLS
    else:
        # Full plane: all rows from ps to pe, no gaps
        TOTAL_ROWS = (pe - ps + 1) // GRID_COLS  # 4096 for full plane
        for ri in range(TOTAL_ROWS):
            row_start = ps + ri * GRID_COLS
            rd = _build_row(row_start, pe, Unicode)
            # Find which block this row belongs to
            row_mid = row_start + GRID_COLS // 2
            b = _find_block(row_mid)
            bn = b["name"] if b else "Unassigned"
            bs = b["start"] if b else 0
            be = b["end"] if b else 0
            ba = b.get("assigned", be - bs + 1) if b else 0
            is_boundary = bn != blk_prev
            rows.append(
                {
                    "cells": rd,
                    "row_start": row_start,
                    "block_name": bn,
                    "block_start": bs,
                    "block_end": be,
                    "block_assigned": ba,
                    "block_boundary": is_boundary,
                }
            )
            scroll_idx = len(rows) - 1
            for c in range(GRID_COLS):
                cp = row_start + c
                if cp <= pe and cp <= 0x10FFFF and not (0xD800 <= cp <= 0xDFFF):
                    cp_map[cp] = scroll_idx
            blk_prev = bn

    # Pad 7 empty rows at end
    for _ in range(7):
        rows.append(
            {
                "cells": [{"codepoint": -1, "char_name": None} for _ in range(GRID_COLS)],
                "row_start": -1,
                "block_name": "\u2014",
                "block_start": 0,
                "block_end": 0,
                "block_assigned": 0,
                "block_boundary": False,
            }
        )
    _plane_rows[key] = rows
    _plane_max_scroll[key] = max(0, len(rows) - GRID_ROWS)
    _plane_cp_to_scroll[key] = cp_map


@app.get("/api/grid/{plane}")
def get_grid(
    plane: int,
    scroll: int = Query(0, ge=0),
    filter_no_block: bool = Query(True),
    attrs: bool = Query(False),
):
    if plane not in VALID_PLANES:
        return JSONResponse({"error": f"Invalid plane {plane}"}, 400)
    key = (plane, filter_no_block)
    _build_plane_rows(plane, filter_no_block)
    rows = _plane_rows[key]
    scroll = max(0, min(scroll, _plane_max_scroll[key]))
    page = rows[scroll : scroll + GRID_ROWS]
    cells = [r["cells"] for r in page]
    if attrs:
        # Options ▸ Colour Coding needs the character's properties per cell.
        # Only 8×16 cells are sent, so this is computed on the page rather than
        # stored with every row of the plane (4096 rows × 16).
        cells = _with_cell_attrs(cells)
    row_bases = [(r["row_start"] - plane * 0x10000) if r["row_start"] >= 0 else -1 for r in page]
    block_boundaries = [i for i, r in enumerate(page) if r["block_boundary"]]
    first = page[0]
    return {
        "plane": plane,
        "block_name": first["block_name"],
        "block_start": first["block_start"],
        "block_end": first["block_end"],
        "block_count": first["block_end"] - first["block_start"] + 1 if first["block_start"] else 0,
        "block_assigned": first["block_assigned"],
        "scroll_position": scroll,
        "max_scroll": _plane_max_scroll[key],
        "cells": cells,
        "row_bases": row_bases,
        "block_boundaries": block_boundaries,
    }


def _safe_name(Unicode, cp: int) -> str | None:
    """Get character name, including algorithmic names (CJK, Tangut, etc.)."""
    n = Unicode.get_character_name(cp)
    return n if n else None


def _with_cell_attrs(cells: list[list[dict]]) -> list[list[dict]]:
    """Annotate one page of grid cells with the properties colour coding needs.

    The short codes match the tables the frontend indexes with — `gc` is the
    two-letter General Category, `bc` the Bidi Class, `dt` the Decomposition
    Type, `nt` the Numeric Type, `bm` the Bidi Mirrored flag, `sc` the ISO 15924
    script code and `ver` the Unicode version the character was introduced in.
    `Unicode.get_*` returns an *enum* for the category-like getters, so the
    name has to be taken from `.name` rather than the object itself.
    """
    from babelsoft.unicode.core import Unicode

    def code(fn, cp):
        try:
            v = fn(cp)
            if v is None:
                return ""
            return getattr(v, "name", None) or str(v)
        except PROBE_ERRORS:
            return ""

    out: list[list[dict]] = []
    for row in cells:
        nrow = []
        for cell in row:
            cp = cell.get("codepoint", -1)
            if cp is None or cp < 0:
                nrow.append(cell)
                continue
            c = dict(cell)
            c["gc"] = code(Unicode.get_general_category, cp)
            c["bc"] = code(Unicode.get_bidi_class, cp)
            c["dt"] = code(Unicode.get_decomposition_type, cp)
            c["nt"] = code(Unicode.get_numeric_type, cp)
            # NOTE: `get_script_code()` returns a 4-letter code that does not
            # match the character (it answers "Phag" for U+0040), so the long
            # script name from `get_script()` is used as the key instead.
            c["sc"] = code(Unicode.get_script, cp)
            c["bm"] = code(Unicode.get_bidi_mirrored, cp)
            age = code(Unicode.get_character_age, cp)
            c["ver"] = age.split(".")[0] if age[:1].isdigit() else age
            nrow.append(c)
        out.append(nrow)
    return out


@app.get("/api/grid/{plane}/goto/{cp}")
def grid_goto(plane: int, cp: int, filter_no_block: bool = Query(True)):
    key = (plane, filter_no_block)
    _build_plane_rows(plane, filter_no_block)
    found = cp in _plane_cp_to_scroll[key]
    scroll = _plane_cp_to_scroll[key].get(cp, max(0, (cp - plane * 0x10000) // GRID_COLS))
    result = get_grid(plane, scroll, filter_no_block)
    if not isinstance(result, dict):
        return result
    result["not_found"] = not found
    return result


@app.get("/api/grid/{plane}/block/{name:path}")
def grid_block(plane: int, name: str, filter_no_block: bool = Query(True)):
    for b in _ALL_BLOCKS:
        if b["name"] == name:
            return get_grid(plane, max(0, (b["start"] - plane * 0x10000) // GRID_COLS), filter_no_block)
    return JSONResponse({"error": "Not found"}, 404)


@app.get("/api/grid/{plane}/navigate")
def grid_nav(plane: int, scroll: int = 0, direction: str = "page_next", filter_no_block: bool = Query(True)):
    ps = plane * 0x10000
    pe = min(ps + 0xFFFF, 0x10FFFF)
    ms = (pe - ps) // GRID_COLS
    ns = scroll
    if direction == "plane_start":
        ns = 0
    elif direction == "plane_end":
        ns = ms
    elif direction == "page_prev":
        ns = max(0, scroll - GRID_ROWS)
    elif direction == "page_next":
        ns = min(ms, scroll + GRID_ROWS)
    elif direction in ("block_prev", "block_next"):
        dir_int = -1 if direction == "block_prev" else 1
        cp = ps + scroll * GRID_COLS
        cb = _find_block(cp)
        if cb:
            pblocks = _blocks_by_plane.get(plane, [])
            try:
                idx = pblocks.index(cb) + dir_int
                if 0 <= idx < len(pblocks):
                    ns = max(0, (pblocks[idx]["start"] - ps) // GRID_COLS)
                else:
                    ns = 0 if dir_int < 0 else ms
            except ValueError:
                ns = max(0, min(ms, scroll + dir_int * GRID_ROWS * 2))
        else:
            ns = max(0, min(ms, scroll + dir_int * GRID_ROWS * 2))
    return get_grid(plane, ns, filter_no_block)


@app.get("/api/readings/{cp}")
def codepoint_readings(
    cp: int,
    cjkv: str = "mandarin",
    tangut: str = "gong2008",
    upper: bool = False,
    tones: bool = False,
    tangut_tones: bool = False,
):
    """CJKV / Tangut readings for one code point — Options ▸ CJKV Readings.

    The original drives these through process-wide switches
    (`Lookup::UseUpperCaseReadings`, `UseToneNumbers`, `ConvertTones`), so the
    same three flags are applied here before reading.  Returns the strings the
    description line appends, already formatted:

    ``[reading]`` for CJKV, the Tangut reading, and the source-reference lists
    that Options ▸ Status Bar can hide.

    ``cjkv`` is one of mandarin / cantonese / korean / quoc_ngu / viqr / zhuang;
    ``tangut`` is one of gong2008 (Li Fanwen 2008) / kychanov / sofronov /
    nishida / miyake2012 / miyake2015.
    """
    from babelsoft.unicode.core import Unicode

    if not Unicode.is_valid_code_point(cp) or Unicode.is_surrogate(cp):
        return JSONResponse({"error": "Invalid"}, 400)

    out: dict = {"cjkv": "", "tangut": "", "cjk_refs": "", "tangut_refs": "", "cjk": False, "tangut_char": False}

    # The flags are global in the library, exactly as in the C++ (Lookup::…).
    try:
        from babelsoft.cjkv.jyutping import Jyutping
        from babelsoft.cjkv.korean import Korean
        from babelsoft.cjkv.pinyin import Pinyin
        from babelsoft.cjkv.vietnamese import Vietnamese
        from babelsoft.cjkv.zhuang import Zhuang

        for cls in (Pinyin, Jyutping, Korean, Vietnamese, Zhuang):
            cls.use_upper_case_readings(bool(upper))
            cls.use_tone_numbers(bool(tones))
    except PROBE_ERRORS:
        logger.debug("codepoint_readings: ignoring recoverable error", exc_info=True)

    # ── CJKV reading ────────────────────────────────────────────────
    try:
        from babelsoft.cjkv.cjk import CJK

        if CJK(cp).is_cjk_ideograph():
            out["cjk"] = True
            if cjkv == "cantonese":
                from babelsoft.cjkv.jyutping import Jyutping

                out["cjkv"] = Jyutping.get_jyutping_for_char(cp)
            elif cjkv == "korean":
                from babelsoft.cjkv.korean import Korean

                out["cjkv"] = Korean.get_korean_for_char(cp)
            elif cjkv in ("quoc_ngu", "viqr"):
                from babelsoft.cjkv.vietnamese import Vietnamese

                out["cjkv"] = Vietnamese.get_vietnamese_for_char(cp, use_viqr=(cjkv == "viqr"))
            elif cjkv == "zhuang":
                from babelsoft.cjkv.zhuang import Zhuang

                out["cjkv"] = Zhuang.get_zhuang_for_char(cp)
            else:
                from babelsoft.cjkv.pinyin import Pinyin

                out["cjkv"] = Pinyin.get_pinyin_for_char(cp)
    except PROBE_ERRORS:
        logger.debug("codepoint_readings: ignoring recoverable error", exc_info=True)

    # ── CJK source references (Options ▸ Status Bar) ────────────────
    try:
        from babelsoft.cjkv.cjk import CJK

        # `GetSourceRefs()` in the original: the IRG source list joined by
        # spaces ("G0-523B HB1-A440 J0-306C …"), skipping the empty ones.
        sources = (CJK(cp).ideographic_properties() or {}).get("sources") or []
        out["cjk_refs"] = " ".join(str(ref) for _label, ref in sources if ref)
    except PROBE_ERRORS:
        logger.debug("codepoint_readings: ignoring recoverable error", exc_info=True)

    # ── Tangut reading + references ─────────────────────────────────
    try:
        from babelsoft.scripts.tangut import Tangut

        if Tangut.is_tangut_ideograph(cp):
            out["tangut_char"] = True
            # Gonq Hwang-cherng (2008) is published from the Li Fanwen 2008
            # table, which is what babellib carries — see the menu label.
            if tangut == "kychanov":
                out["tangut"] = Tangut.get_kychanov_reading(cp, b_tone=tangut_tones)
            elif tangut == "sofronov":
                out["tangut"] = Tangut.get_sofronov_reading(cp, b_tone=tangut_tones)
            elif tangut == "nishida":
                out["tangut"] = Tangut.get_nishida_reading(cp, b_tone=tangut_tones)
            elif tangut == "miyake2012":
                out["tangut"] = Tangut.get_miyake_reading(cp, b_2012=True, b_tone=tangut_tones)
            elif tangut == "miyake2015":
                out["tangut"] = Tangut.get_miyake_reading(cp, b_2012=False, b_tone=tangut_tones)
            else:
                out["tangut"] = Tangut.get_li_fanwen_reading(cp, b_tone=tangut_tones)
            try:
                out["tangut_refs"] = Tangut.get_merged_source(cp) or ""
            except PROBE_ERRORS:
                out["tangut_refs"] = ""
    except PROBE_ERRORS:
        logger.debug("codepoint_readings: ignoring recoverable error", exc_info=True)

    return out


@app.get("/api/codepoint/{cp}")
def codepoint_info(cp: int):
    from babelsoft.unicode.core import Unicode

    if not Unicode.is_valid_code_point(cp) or Unicode.is_surrogate(cp):
        return JSONResponse({"error": "Invalid"}, 400)

    def _s(fn, default=""):
        try:
            v = fn(cp)
            return v if v not in (None, "") else default
        except PROBE_ERRORS:
            return default

    def _enum(fn):
        try:
            return fn(cp).name
        except PROBE_ERRORS:
            return ""

    _aliases = Unicode._name_alias_map_by_type().get(cp, [])
    info = {
        "codepoint": cp,
        "name": _s(Unicode.get_character_name),
        "block": _s(Unicode.get_block_name),
        "script": _s(Unicode.get_script),
        "age": _s(Unicode.get_character_age),
        "general_category": _enum(Unicode.get_general_category),
        "canonical_combining_class": _s(lambda c: str(Unicode.get_canonical_combining_class(c))),
        "bidi_class": _enum(Unicode.get_bidi_class),
        "bidi_mirrored": "Y" if Unicode.get_bidi_mirrored(cp) else "N",
        "line_break": _enum(Unicode.get_line_break),
        "east_asian_width": _enum(Unicode.get_east_asian_width),
        "decomposition_type": _enum(Unicode.get_decomposition_type),
        "decomposition": _s(Unicode.get_decomposition),
        "numeric_type": _enum(Unicode.get_numeric_type),
        "numeric_value": _s(Unicode.get_numeric_value),
        "unicode1_name": _s(Unicode.get_unicode1_name),
        "formal_aliases": [a for a, _t in _aliases if _t == "correction"],
        "abbreviation": ", ".join(a for a, _t in _aliases if _t == "abbreviation"),
        "joining_type": _enum(Unicode.get_joining_type),
        "joining_group": _s(Unicode.get_joining_group),
        "utf8": " ".join(f"{b:02X}" for b in chr(cp).encode("utf-8")),
    }
    try:
        u1 = Unicode.unicode1_codepoint(cp)
        info["unicode1_codepoint"] = u1 if u1 not in (None, 0) else None
    except PROBE_ERRORS:
        info["unicode1_codepoint"] = None
    # Simple case mappings (empty when identity).
    info["simple_uppercase"] = _mapping_str(Unicode.get_simple_uppercase(cp), cp)
    info["simple_lowercase"] = _mapping_str(Unicode.get_simple_lowercase(cp), cp)
    info["simple_titlecase"] = _mapping_str(Unicode.get_simple_titlecase(cp), cp)
    if cp == 0x03A3:  # GREEK CAPITAL LETTER SIGMA — final sigma special case
        info["simple_lowercase"] = "03C3 or 03C2 (final)"
    # Encodings.
    if cp <= 0xFFFF:
        info["utf16"] = f"{cp:04X}"
    else:
        hi, lo = Unicode.get_surrogates_from_unicode32(cp)
        info["utf16"] = f"{hi:04X} {lo:04X}"
    info["utf32"] = f"{cp:08X}"
    # Extra property areas: binary properties, NamesList, variants, named sequences.
    try:
        from babelsoft.unicode.extras import (
            binary_properties,
            emoji_variation_sequences,
            named_sequences_for,
            nameslist,
            standardized_variants,
        )

        info["binary_properties"] = binary_properties(cp)
        nl = nameslist(cp)
        info["nameslist"] = {"aliases": nl["aliases"], "notes": nl["notes"], "xrefs": nl["xrefs"]}
        info["standardized_variants"] = [[vs, desc] for vs, desc in standardized_variants(cp)]
        info["emoji_variants"] = [[vs, style] for vs, style in emoji_variation_sequences(cp)]
        info["named_sequences"] = [[name, list(cps)] for name, cps in named_sequences_for(cp)]
    except PROBE_ERRORS:
        info["binary_properties"] = []
        info["nameslist"] = {"aliases": [], "notes": [], "xrefs": []}
        info["standardized_variants"] = []
        info["emoji_variants"] = []
        info["named_sequences"] = []
    # Extended (XML-style) character properties + name aliases.
    try:
        from babelsoft.unicode.extended import extended_properties, name_aliases

        info["extended"] = extended_properties(cp)
        info["name_aliases"] = name_aliases(cp)
    except PROBE_ERRORS:
        info["extended"] = []
        info["name_aliases"] = []
    # Ideographic Variation Sequences (VS17..VS256) from IVD_Sequences.txt.
    try:
        from babelsoft.cjkv.cjk import CJK

        info["ideographic_variants"] = [[vs, collection, ref] for vs, collection, ref in CJK(cp).ivs_sequences()]
    except PROBE_ERRORS:
        info["ideographic_variants"] = []
    # CJK readings / radical-stroke (kept from before).
    try:
        from babelsoft.cjkv.cjk import CJK

        cjk = CJK(cp)
        if cjk.is_cjk_ideograph():
            try:
                readings = cjk.readings()
                pinyin = readings.get("kMandarin", "")
                info["pinyin"] = pinyin.split() if pinyin else []
            except PROBE_ERRORS:
                logger.debug("codepoint_info: ignoring recoverable error", exc_info=True)
            try:
                rs_list = cjk.radical_strokes()
                if rs_list:
                    info["radical_stroke"] = str(rs_list[0])
            except PROBE_ERRORS:
                logger.debug("codepoint_info: ignoring recoverable error", exc_info=True)
    except PROBE_ERRORS:
        logger.debug("codepoint_info: ignoring recoverable error", exc_info=True)
    # Ideographic (CJKV) properties — mirrors the C++ CDialogCJKV dialog.
    try:
        from babelsoft.cjkv.cjk import CJK

        info["ideographic"] = CJK(cp).ideographic_properties()
    except PROBE_ERRORS:
        info["ideographic"] = {}
    return info


def _mapping_str(v: int, src: int) -> str:
    """Format a simple case-mapping codepoint; empty string when identity."""
    if not v or v == src:
        return ""
    return f"{v:04X}"


@app.get("/api/glyph/{cp}")
def glyph(cp: int, font: str = "Arial", size: int = 16):
    return {"codepoint": cp, "glyph_b64": _render_glyph(cp, font, size)}


# ── Rasterised glyphs (Fonts ▸ Quality / Export Font Glyphs) ─────────
# These are the only endpoints that control *how* a glyph becomes pixels.
# CSS cannot select a rasteriser inside WebView2, so the grid keeps the
# system's rendering while these expose the seven LOGFONT.lfQuality modes.


@app.get("/api/glyphs/qualities")
def glyph_qualities():
    """The quality modes, in menu order (index == lfQuality value)."""
    from babelmap.backend.glyph_render import QUALITY_KEYS

    return {"qualities": [{"index": i, "key": k} for i, k in enumerate(QUALITY_KEYS)]}


@app.get("/api/glyphs/preview")
def glyph_preview(
    cp: int = 0x41,
    font: str = "Arial",
    style: str = "",
    size: int = 40,
    quality: int = 4,
    fg: str = "#000000",
    bg: str = "#ffffff",
    cell_w: int = 0,
    cell_h: int = 0,
    scale: int = 1,
    fmt: str = "png",
):
    """One code point, rasterised at the requested quality, as an image."""
    from fastapi.responses import Response

    from babelmap.backend.glyph_render import preview_png

    cell = (cell_w, cell_h) if cell_w > 0 and cell_h > 0 else None
    try:
        data = preview_png(
            cp=cp,
            family=font,
            style=style,
            size=size,
            quality=quality,
            fg=fg,
            bg=bg,
            cell=cell,
            scale=scale,
            fmt=fmt,
        )
    except KeyError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except PROBE_ERRORS as e:  # pragma: no cover - defensive
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)
    media = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "bmp": "image/bmp",
        "gif": "image/gif",
    }.get(fmt.lower(), "image/png")
    return Response(content=data, media_type=media)


@app.get("/api/glyphs/sample")
def glyph_sample(
    text: str = "Hamburgefonstiv 123",
    font: str = "Arial",
    style: str = "",
    size: int = 28,
    quality: int = 4,
    fg: str = "#000000",
    bg: str = "#ffffff",
    scale: int = 2,
):
    """A whole sample line at the requested quality (Font Quality dialog)."""
    from fastapi.responses import Response

    from babelmap.backend.glyph_render import text_png

    try:
        data = text_png(
            text=text,
            family=font,
            style=style,
            size=size,
            quality=quality,
            fg=fg,
            bg=bg,
            scale=scale,
        )
    except KeyError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except PROBE_ERRORS as e:  # pragma: no cover - defensive
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)
    return Response(content=data, media_type="image/png")


@app.post("/api/glyphs/export")
def glyph_export(payload: dict):
    """Zip of one image per code point — Fonts ▸ Export Font Glyphs."""
    from babelmap.backend.glyph_render import export_zip, parse_codepoints

    cps = payload.get("codepoints") or []
    if isinstance(cps, str):
        cps = parse_codepoints(cps)
    cps = [int(c) for c in cps if isinstance(c, int) or str(c).isdigit()][:20000]
    if not cps:
        return JSONResponse({"error": "No code points selected"}, status_code=400)
    fmt = str(payload.get("format") or "png").lower()
    cw, ch = int(payload.get("cell_w") or 0), int(payload.get("cell_h") or 0)
    try:
        data = export_zip(
            cps,
            family=str(payload.get("font") or "Arial"),
            style=str(payload.get("style") or ""),
            size=int(payload.get("size") or 32),
            quality=int(payload.get("quality") or 4),
            fg=str(payload.get("fg") or "#000000"),
            bg=str(payload.get("bg") or "#ffffff"),
            cell=(cw, ch) if cw > 0 and ch > 0 else None,
            fmt=fmt,
            scale=max(1, int(payload.get("scale") or 1)),
        )
    except KeyError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    name = (payload.get("name") or "glyphs").replace('"', "")
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}.zip"'},
    )


# ── Unified Search by Name ──────────────────────────────────────────
# All name searches go through the AST-based advanced search engine.
# Simple queries like "lisu" are parsed as name=lisu automatically.


@app.get("/api/search/name")
def search_by_name(
    q: str = Query(..., min_length=1),
    limit: int = Query(200, ge=1, le=1000),
    start_cp: int = Query(0, ge=0, le=0x10FFFF),
    filter_no_block: bool = Query(False, description="Filter out codepoints without an assigned block"),
):
    """Unified search-by-name endpoint. Always uses AST parser.
    Pass start_cp to search from the character after the current one."""
    from babelmap.backend.adv_search import normalize_query
    from babelmap.backend.adv_search import search as adv_search

    normalized = normalize_query(q)
    results = adv_search(q, _ALL_BLOCKS, limit, start_cp, filter_no_block)
    return {"query": normalized, "results": results, "filter_no_block": filter_no_block}


@app.get("/api/search/advanced")
def advanced_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(200, ge=1, le=1000),
    start_cp: int = Query(0, ge=0, le=0x10FFFF),
    filter_no_block: bool = Query(False, description="Filter out codepoints without an assigned block"),
):
    """Alias for /api/search/name — unified AST-based search."""
    return search_by_name(q, limit, start_cp, filter_no_block)


@app.get("/api/search/name/stream")
def search_by_name_stream(
    q: str = Query(..., min_length=1),
    limit: int = Query(200, ge=1, le=2000),
    start_cp: int = Query(0, ge=0, le=0x10FFFF),
    filter_no_block: bool = Query(False, description="Filter out codepoints without an assigned block"),
):
    """Streaming search: returns results via SSE as they are found.
    limit=0 means no limit (return all matches)."""
    from babelmap.backend.adv_search import search_stream_sse

    return StreamingResponse(
        search_stream_sse(q, _ALL_BLOCKS, limit, start_cp, filter_no_block),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/search/han_source")
def search_by_han_source(q: str = Query(..., min_length=1), limit: int = Query(50, ge=1, le=500)):
    """Search CJK ideographs by IRG source reference (substring match)."""
    results = []
    qu = q.upper().strip()
    try:
        from babelsoft.cjkv.cjk import CJKLoader

        reverse = CJKLoader.load_cjk_irg_reverse()
        for ref, cp in reverse.items():
            if qu in ref.upper():
                name = f"U+{cp:04X}" if cp <= 0xFFFF else f"U+{cp:05X}"
                results.append({"codepoint": cp, "name": name, "source": ref})
                if len(results) >= limit:
                    break
    except PROBE_ERRORS:
        logger.debug("search_by_han_source: ignoring recoverable error", exc_info=True)
    return results


@app.get("/api/search/properties")
def search_properties(q: str = Query("", min_length=0)):
    from babelmap.backend.adv_search import matching_properties

    return matching_properties(q)


@app.get("/api/emoji/search")
def emoji_search(q: str = Query("", max_length=80), limit: int = Query(80, ge=1, le=500)):
    """Emojipedia-style emoji search by name, keyword or codepoint."""
    from babelsoft.unicode.emoji import search as search_emoji

    try:
        results = [e.to_dict() for e in search_emoji(q, limit)]
    except PROBE_ERRORS:
        results = []
    return {"query": q, "results": results}


@app.get("/api/emoji/list")
def emoji_list(limit: int = Query(0, ge=0, le=6000)):
    """All RGI emoji in CLDR order (browse mode). limit=0 → all."""
    from babelsoft.unicode.emoji import all_emoji

    try:
        entries = all_emoji()
    except PROBE_ERRORS:
        entries = []
    if limit:
        entries = entries[:limit]
    return {"total": len(entries), "results": [e.to_dict() for e in entries]}


@app.get("/api/fonts")
def list_fonts():
    return [
        "Arial",
        "Courier New",
        "Times New Roman",
        "Segoe UI",
        "Consolas",
        "DejaVu Sans",
        "Noto Sans",
        "Microsoft YaHei",
        "SimSun",
        "MS Mincho",
        "MS Gothic",
        "Malgun Gothic",
        "Batang",
    ]


@app.get("/api/fonts/overview")
def fonts_overview(dirs: str = ""):
    """Full font overview: every font face across multiple font directories,
    with metadata, family and primary-writing-system (script) classification.

    ``dirs`` may be a ``|``-separated list of extra directories to scan in
    addition to the system + per-user font folders.
    """
    from babelmap.backend.font_overview import CHAPTERS, scan_fonts

    extra = [d.strip() for d in dirs.split("|") if d.strip()]
    return {
        "fonts": scan_fonts(extra_dirs=extra),
        "chapters": [CHAPTERS[num] for num in sorted(CHAPTERS)],
    }


@app.get("/api/fonts/overview/stream")
def fonts_overview_stream(dirs: str = ""):
    """Streaming font overview: SSE progress while scanning, then the payload.

    Events: ``data: SCAN {"done":…,"total":…,"file":…,"pct":…}`` per font file,
    then ``data: RESULT {fonts, chapters}``, then ``data: [DONE]``.
    """
    import json

    from babelmap.backend.font_overview import CHAPTERS, scan_fonts

    extra = [d.strip() for d in dirs.split("|") if d.strip()]

    def gen():
        import threading

        # scan_fonts is synchronous and CPU-bound, so run it on a worker thread
        # and pump the progress events its callback queues onto the SSE stream.
        pending: list[dict] = []
        box: dict = {}

        def progress(done: int, total: int, label: str, cached: bool):
            pending.append(
                {
                    "done": done,
                    "total": total,
                    "file": label,
                    "cached": cached,
                    "pct": round((done / total * 100.0) if total else 100.0, 1),
                }
            )

        def run():
            try:
                box["fonts"] = scan_fonts(extra_dirs=extra, progress=progress)
            except PROBE_ERRORS as exc:  # pragma: no cover - defensive
                box["error"] = str(exc)

        th = threading.Thread(target=run, daemon=True)
        th.start()
        emitted = 0
        while True:
            while emitted < len(pending):
                yield f"data: SCAN {json.dumps(pending[emitted])}\n\n"
                emitted += 1
            if not th.is_alive() and emitted >= len(pending):
                break
            th.join(timeout=0.05)

        if "error" in box:
            yield f"data: ERROR {json.dumps(box['error'])}\n\n"
        else:
            yield "data: RESULT " + json.dumps(
                {
                    "fonts": box.get("fonts") or [],
                    "chapters": [CHAPTERS[n] for n in sorted(CHAPTERS)],
                },
                ensure_ascii=False,
            ) + "\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/fonts/raw")
def fonts_raw(path: str = ""):
    """Serve a font file for @font-face (the variable-font preview needs a
    real web font so the browser interpolates its axes).  Only files inside
    the known font directories are served."""
    from fastapi.responses import FileResponse

    from babelmap.backend.font_overview import DEFAULT_DIRS

    if not path:
        return JSONResponse({"error": "missing path"}, status_code=400)
    if not os.path.isfile(path):
        return JSONResponse({"error": "no such file"}, status_code=404)
    norm = os.path.normcase(os.path.normpath(path))
    if not any(norm.startswith(os.path.normcase(os.path.normpath(d))) for d in DEFAULT_DIRS):
        return JSONResponse({"error": "not allowed"}, status_code=403)
    ext = os.path.splitext(path)[1].lower()
    media = "font/ttf" if ext in (".ttf", ".ttc") else "font/otf"
    return FileResponse(
        path,
        media_type=media,
        headers={"Cache-Control": "no-store"},
    )


# ── User font registry (fonts from *outside* the system font folders) ──
# The browser can resolve installed fonts via local("Name"), but a font the user
# downloads / points at elsewhere is unreachable, so it is uploaded here and
# served back for @font-face src: url(...).  See backend/font_registry.py.


@app.get("/api/fonts/user")
def user_fonts_list():
    """List every font the user has added (newest first)."""
    from babelmap.backend.font_registry import list_fonts

    return {"fonts": list_fonts()}


@app.post("/api/fonts/user")
def user_fonts_add(payload: dict):
    """Register an uploaded font.

    Body: ``{file_name, data_b64}`` (base64 payload) **or** ``{file_name,
    path}`` to import a file the backend can already read.  The font is copied
    into the managed ``var/user_fonts`` folder and returned with its metadata.
    """
    from babelmap.backend.font_registry import register

    file_name = str(payload.get("file_name") or "").strip()
    b64 = payload.get("data_b64")
    raw_path = payload.get("path")
    try:
        if b64:
            data = base64.b64decode(b64, validate=False)
            file_name = file_name or "font"
        elif raw_path:
            if not os.path.isfile(raw_path):
                return JSONResponse({"error": f"No such file: {raw_path}"}, status_code=404)
            with open(raw_path, "rb") as fh:
                data = fh.read()
            file_name = file_name or os.path.basename(raw_path)
        else:
            return JSONResponse({"error": "Provide data_b64 or path"}, status_code=400)
        entry = register(file_name, data)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except PROBE_ERRORS as e:
        return JSONResponse({"error": f"Could not register the font: {e}"}, status_code=400)
    return entry


@app.post("/api/fonts/user/remove")
def user_fonts_remove(payload: dict):
    """Unregister (and delete) a user font — the inverse of ``POST /api/fonts/user``."""
    from babelmap.backend.font_registry import unregister

    fid = str(payload.get("id") or "").strip()
    if not fid:
        return JSONResponse({"error": "Missing id"}, status_code=400)
    if not unregister(fid):
        return JSONResponse({"error": f"Unknown font id '{fid}'"}, status_code=404)
    return {"ok": True, "id": fid}


@app.get("/api/fonts/user_file")
def user_fonts_file(id: str = Query("", min_length=1)):
    """Serve a registered user font back to the browser for ``@font-face``."""
    from fastapi.responses import FileResponse

    from babelmap.backend.font_registry import media_type, resolve

    entry = resolve(id)
    if entry is None:
        return JSONResponse({"error": "unknown font id"}, status_code=404)
    path = entry["path"]
    if not os.path.isfile(path):
        return JSONResponse({"error": "font file is gone"}, status_code=404)
    return FileResponse(
        path,
        media_type=media_type(entry.get("ext", "")),
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/fonts/user/analyze")
def user_fonts_analyze(id: str = Query("", min_length=1)):
    """FontTools analysis of one registered font (identity, coverage, OpenType)."""
    from babelmap.backend.font_registry import analyze

    info = analyze(id)
    if info is None:
        return JSONResponse({"error": f"Unknown font id '{id}'"}, status_code=404)
    return info


@app.post("/api/fonts/composite/validate")
def composite_validate(payload: dict):
    """Compile-validate user-written composite-font CSS.

    Body: ``{css}``.  → ``{ok, errors, warnings, families, stats}`` where
    ``ok`` (no errors) is the "编译通过 / takes effect" signal.  See
    ``babelmap/backend/font_registry.py``.
    """
    from babelmap.backend.font_registry import validate_css

    css = str(payload.get("css") or "")
    # Feed the real installed family names so local("…") typos are caught.
    try:
        from babelmap.backend.font_overview import scan_fonts

        families = sorted({f.get("family") or "" for f in scan_fonts()} - {""})
    except PROBE_ERRORS:
        families = []
    return validate_css(css, known_families=families)


# ── Composite-font coverage (the port of CDialogConfig's block list + Auto) ──
# See babelmap/backend/font_coverage.py for the inherited scoring rules.


@app.get("/api/fonts/coverage")
def fonts_coverage(block: str = "", dirs: str = "", all_styles: bool = False):
    """Per-block font coverage: one row per Unicode block with every font that
    covers it, the best font, and the overall coverage summary.

    ``block`` limits the answer to one block (much cheaper to render);
    ``dirs`` adds extra font directories to the scan; ``all_styles`` enumerates
    every face of a family instead of only its primary style.
    """
    from babelmap.backend.font_coverage import block_coverage
    from babelmap.backend.font_overview import scan_fonts

    extra = [d.strip() for d in dirs.split("|") if d.strip()]
    scan = {"fonts": scan_fonts(extra_dirs=extra)}
    return block_coverage(scan, block_name=block or None, all_styles=all_styles)


@app.get("/api/fonts/coverage/stream")
def fonts_coverage_stream(block: str = "", dirs: str = "", all_styles: bool = False):
    """Streaming variant of ``/api/fonts/coverage``.

    The scan is the expensive part, so it reuses the same SSE shape as the
    font overview: ``data: SCAN {…}`` per font file, then ``data: RESULT
    {blocks, summary, imported}``, then ``data: [DONE]``.
    """
    import json

    from babelmap.backend.font_coverage import block_coverage
    from babelmap.backend.font_overview import scan_fonts

    extra = [d.strip() for d in dirs.split("|") if d.strip()]

    def gen():
        import threading

        pending: list[dict] = []
        box: dict = {}

        def progress(done: int, total: int, label: str, cached: bool):
            pending.append(
                {
                    "done": done,
                    "total": total,
                    "file": label,
                    "cached": cached,
                    "pct": round((done / total * 100.0) if total else 100.0, 1),
                }
            )

        def run():
            try:
                scan = {"fonts": scan_fonts(extra_dirs=extra, progress=progress)}
                box["result"] = block_coverage(scan, block_name=block or None, all_styles=all_styles)
            except PROBE_ERRORS as exc:  # pragma: no cover - defensive
                box["error"] = str(exc)

        th = threading.Thread(target=run, daemon=True)
        th.start()
        emitted = 0
        while True:
            while emitted < len(pending):
                yield f"data: SCAN {json.dumps(pending[emitted])}\n\n"
                emitted += 1
            if not th.is_alive() and emitted >= len(pending):
                break
            th.join(timeout=0.05)

        if "error" in box:
            yield f"data: ERROR {json.dumps(box['error'])}\n\n"
        else:
            yield "data: RESULT " + json.dumps(box.get("result") or {}, ensure_ascii=False) + "\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/fonts/coverage/auto")
def fonts_coverage_auto(dirs: str = "", all_styles: bool = False):
    """Run the **Auto** assignment: the best font for every block.

    → ``{assignments, summary, imported}``; each assignment explains which
    scoring criterion chose the font (``reason``).
    """
    from babelmap.backend.font_coverage import auto_assign
    from babelmap.backend.font_overview import scan_fonts

    extra = [d.strip() for d in dirs.split("|") if d.strip()]
    return auto_assign({"fonts": scan_fonts(extra_dirs=extra)}, all_styles=all_styles)


@app.get("/api/fonts/coverage/chars")
def fonts_coverage_chars(block: str = Query(..., min_length=1), dirs: str = "", all_styles: bool = False):
    """Every character of one block, annotated with the fonts that map it.

    → ``{name, start, end, plane, total, cps, fonts, masks}`` where ``fonts``
    are face indices and ``masks`` are base64 bitsets (bit *i* of row *j* = face
    ``fonts[j]`` maps ``cps[i]``).  Drives the dialog's preview grid, which shows
    the block in full and greys out the cells the selected font does not cover.

    The bitset shape replaces a per-character ``supported_by`` list, which cost
    ~7 MB of JSON and ~4 s for CJK Unified Ideographs (20 992 chars × 84 faces).
    """
    from babelmap.backend.font_coverage import block_chars
    from babelmap.backend.font_overview import scan_fonts

    extra = [d.strip() for d in dirs.split("|") if d.strip()]
    result = block_chars(block, {"fonts": scan_fonts(extra_dirs=extra)}, all_styles=all_styles)
    if result is None:
        return JSONResponse({"error": f"Unknown block '{block}'"}, status_code=404)
    return result


@app.get("/api/convert/edit")
def convert_edit(text: str = "", mode: str = "char"):
    if not text:
        return {"result": ""}
    a = list(text)
    if mode == "ncr_hex":
        r = "".join(f"&#x{ord(c):X};" for c in a if ord(c) > 0x20 or c == " ")
    elif mode == "ncr_dec":
        r = "".join(f"&#{ord(c)};" for c in a if ord(c) > 0x20 or c == " ")
    elif mode == "html":
        r = "".join(f"&#x{ord(c):X};" if ord(c) > 127 else c for c in a)
    elif mode == "ucn":
        r = "".join(f"\\u{ord(c):04X}" if ord(c) <= 0xFFFF else f"\\U{ord(c):08X}" for c in a)
    else:
        r = text
    return {"result": r}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/about")
def about():
    """Version block for Help ▸ About — the port of `CDialogAbout`.

    The original reads its numbers from the Windows version resource
    (`VersionInfo`); here they come from what this stack actually knows: the
    FastAPI app version, the Python runtime, and the newest Unicode release in
    the bundled data set.
    """
    import platform

    info: dict = {
        "backend": app.version,
        "python": platform.python_version(),
        "unicode": "",
        "unicode_versions": 0,
        "ivd": "",
        "emoji": "",
    }
    try:
        from babelmap.backend.version import all_versions

        vs = all_versions()
        info["unicode_versions"] = len(vs)
        info["unicode"] = vs[-1].get("version", "") if vs else ""
    except PROBE_ERRORS:
        logger.debug("about: ignoring recoverable error", exc_info=True)
    # The IVD date is the directory name under data/ivd (e.g. 2022-09-13), and
    # the emoji version is in the emoji-test.txt header — neither is exposed by
    # a library helper, so read them defensively.
    try:
        from babelsoft.utils_.dirs import Dirs

        ivd_dir = Dirs.DATA / "ivd"
        dates = sorted(p.name for p in ivd_dir.iterdir() if p.is_dir())
        info["ivd"] = dates[-1] if dates else ""
    except PROBE_ERRORS:
        logger.debug("about: ignoring recoverable error", exc_info=True)
    try:
        from babelsoft.utils_.dirs import Dirs

        text = (Dirs.DATA / "scripts" / "emoji-test.txt").read_text(encoding="utf-8", errors="replace")[:400]
        for line in text.splitlines():
            if line.startswith("# Version:"):
                info["emoji"] = line.split(":", 1)[1].strip()
                break
    except PROBE_ERRORS:
        logger.debug("about: ignoring recoverable error", exc_info=True)
    return info


@app.get("/api/unicode/versions")
def unicode_versions():
    """Unicode version history + per-version block lists."""
    from babelmap.backend.version import (
        all_versions,
        blocks_for_version,
        get_version_history,
    )

    versions = all_versions()
    blocks_by_version = {v["version"]: blocks_for_version(v["version"]) for v in versions}
    history = get_version_history()
    return {"versions": versions, "blocks_by_version": blocks_by_version, "history": history}


@app.get("/api/lookup")
def lookup(kind: str, q: str, tone: int = 0, strokes: int = -1, limit: int = 500):
    """Reverse lookups — the port of the Tools ▸ … Lookup dialogs.

    `CDialogMandarin`, `CDialogCantonese`, `CDialogZhuang`, `CDialogHanRadical`
    and `CDialogYiRadical` all answer the same question in a different domain:
    "which characters have this property?".  One endpoint serves them all
    because the answer shape is identical.

    * `kind=pinyin` / `jyutping` / `zhuang` — `q` is the syllable, `tone` the
      tone number (0 = any).
    * `kind=han_radical` — `q` is a Kangxi radical (a character, or its IRG
      radical number), `strokes` the extra strokes (−1 = every count).
    * `kind=yi_radical` — `q` is a Liangshan Yi radical (character or number).
    """
    kind = kind.strip().lower()
    q = q.strip()
    if not q:
        return {"kind": kind, "query": q, "count": 0, "results": []}

    cps: list[int] = []

    if kind in ("pinyin", "jyutping", "zhuang"):
        try:
            if kind == "pinyin":
                from babelsoft.cjkv.pinyin import Pinyin as _L
            elif kind == "jyutping":
                from babelsoft.cjkv.jyutping import Jyutping as _L
            else:
                from babelsoft.cjkv.zhuang import Zhuang as _L
            if kind == "pinyin":
                cps = list(_L.find_pinyin(q.lower(), tone))
            elif kind == "jyutping":
                cps = list(_L.find_jyutping(q.lower(), tone))
            else:
                cps = list(_L.find_zhuang(q.lower(), tone))
        except PROBE_ERRORS:
            cps = []

    elif kind == "han_radical":
        try:
            from babelsoft.cjkv.cjk import CJK, CJKLoader

            radical_no = 0
            flag = 0
            try:
                radical_no = int(q)
            except ValueError:
                ch = ord(q[0])
                # Kangxi radicals are numbered 1..214 from U+2F00, and the
                # radical-block characters map one-to-one, so a typed
                # "⽔"/U+2FB5 resolves without a table lookup.
                if 0x2F00 <= ch <= 0x2FD5:
                    radical_no = ch - 0x2F00 + 1
                else:
                    for rad_cp, number, fl in CJKLoader.load_radical_mappings():
                        if rad_cp == ch:
                            radical_no, flag = number, fl
                            break
                if not radical_no:
                    # An ordinary ideograph typed as the radical (水 for 85):
                    # its own ideographic data carries the radical number.
                    try:
                        strokes_text = str(CJK(ch).ideographic_properties()["radical"]["strokes"])
                        radical_no = int(float(strokes_text))
                    except PROBE_ERRORS:
                        radical_no = 0
            if radical_no:
                found = CJK.find_ideographs_for_radical(
                    radical_no,
                    flag,
                    strokes,
                    all_strokes=strokes < 0,
                )
                cps = [int(c) for c in found]
        except PROBE_ERRORS:
            cps = []

    elif kind == "yi_radical":
        try:
            from babelsoft.scripts.yi import RADICAL_FIRST, YiRadical

            radical_no = 0
            try:
                radical_no = int(q)
            except ValueError:
                ch = ord(q[0])
                if RADICAL_FIRST <= ch <= RADICAL_FIRST + 115:
                    radical_no = ch - RADICAL_FIRST + 1
                else:
                    radical_no = YiRadical.radical_number_for_glyph(ch) or 0
            if radical_no:
                # The Yi syllable block is 1 160 characters, so a scan beats
                # building an index that one dialog would use.
                for cp in range(0xA000, 0xA4D0):
                    try:
                        pairs = YiRadical.get_radical_stroke(cp)
                    except PROBE_ERRORS:
                        logger.debug("lookup: skipping unreadable entry", exc_info=True)
                        continue
                    if any(n == radical_no for n, _ in pairs):
                        cps.append(cp)
        except PROBE_ERRORS:
            cps = []

    cps = cps[: max(1, limit)]
    from babelsoft.unicode.core import Unicode

    results = []
    for cp in cps:
        name = ""
        try:
            name = Unicode.get_character_name(cp) or ""
        except PROBE_ERRORS:
            name = ""
        results.append({"cp": cp, "char": chr(cp), "name": name})
    return {"kind": kind, "query": q, "count": len(results), "results": results}


def _hex(cp: int) -> str:
    return f"{cp:04X}"


@app.get("/api/supplementary/{cp}")
def supplementary(cp: int):
    """Tools ▸ Supplementary Information.

    `OnToolsSupplementaryInformation` dispatches on the character's script and
    opens `CDialogCJKV`, `CDialogTangut` or `CDialogHieroglyph`.  They are three
    views of the same idea — "everything this character knows about itself that
    the property list does not show" — so one endpoint returns the same
    section/row shape for all three and the dialog just renders it.
    """
    from babelsoft.unicode.core import Unicode

    out: dict = {
        "cp": cp,
        "char": chr(cp) if Unicode.is_valid_code_point(cp) else "",
        "name": "",
        "kind": "none",
        "sections": [],
    }
    try:
        out["name"] = Unicode.get_character_name(cp) or ""
    except PROBE_ERRORS:
        logger.debug("supplementary: ignoring recoverable error", exc_info=True)

    def section(title: str, rows: list) -> None:
        rows = [[k, v] for k, v in rows if v not in (None, "", [])]
        if rows:
            out["sections"].append({"title": title, "rows": rows})

    # ── CJK ideographs: CDialogCJKV ──────────────────────────────────
    try:
        from babelsoft.cjkv.cjk import CJK

        if CJK(cp).is_cjk_ideograph():
            out["kind"] = "cjk"
            info = CJK(cp)
            props = {}
            try:
                props = info.ideographic_properties() or {}
            except PROBE_ERRORS:
                props = {}

            rad = props.get("radical") or {}
            glyph = (rad.get("glyph") or {}).get("char", "")
            strokes = rad.get("strokes", "")
            try:
                strokes = str(int(float(strokes)))
            except PROBE_ERRORS:
                logger.debug("supplementary: ignoring recoverable error", exc_info=True)
            section(
                "Radical & Strokes",
                [
                    ("Radical", f"{glyph} ({strokes})".strip() if rad else ""),
                    ("Type", rad.get("type", "")),
                    ("Equivalent", chr(equivalent) if (equivalent := info.to_equivalent()) else ""),
                ],
            )
            section("IDS", [("Ideographic Description", props.get("ids", ""))])

            rel = props.get("related") or {}
            section(
                "Variants",
                [
                    ("Simplified Chinese", rel.get("simplified_chinese") or ""),
                    ("Traditional Chinese", rel.get("traditional") or ""),
                    ("Simplified Japanese", rel.get("simplified_japanese") or ""),
                    ("To simplified", chr(simplified) if (simplified := info.to_simplified()) else ""),
                    ("To traditional", chr(traditional) if (traditional := info.to_traditional()) else ""),
                ],
            )

            readings = props.get("readings") or {}
            section(
                "Readings",
                [
                    ("Mandarin", readings.get("mandarin", "")),
                    ("Cantonese", readings.get("cantonese", "")),
                    ("Korean", readings.get("korean", "")),
                    ("Vietnamese", readings.get("vietnamese", "")),
                    ("Zhuang", readings.get("zhuang", "")),
                ],
            )

            try:
                # `ideographic_properties()["sources"]` is the same table the
                # status bar's ref column is built from; `source_refs()` only
                # covers entries that carry an explicit reference object.
                sources = props.get("sources") or []
                section(
                    "Source References",
                    [(row[0], row[1]) for row in sources if len(row) >= 2],
                )
            except PROBE_ERRORS:
                logger.debug("supplementary: ignoring recoverable error", exc_info=True)
            try:
                ivs = CJK(cp).ivs_sequences() or []
                section(
                    "Variation Sequences",
                    [("IVS", " ".join(f"U+{_hex(vs)}" for vs, _coll, _ref in ivs) if ivs else "")],
                )
            except PROBE_ERRORS:
                logger.debug("supplementary: ignoring recoverable error", exc_info=True)
            return out
    except PROBE_ERRORS:
        logger.debug("supplementary: ignoring recoverable error", exc_info=True)

    # ── Tangut: CDialogTangut ───────────────────────────────────────
    try:
        from babelsoft.scripts.tangut import Tangut

        if Tangut.is_tangut_ideograph(cp):
            out["kind"] = "tangut"
            section(
                "Radical & Strokes",
                [
                    (
                        "Radical",
                        f"{chr(Tangut.get_radical_for_character(cp))} ({Tangut.get_radical_number(cp)})",
                    ),
                    ("Radical strokes", Tangut.get_radical_stroke(cp)),
                    ("Total strokes", Tangut.get_total_stroke_count(cp)),
                    ("Additional strokes", Tangut.get_additional_stroke_count(cp)),
                ],
            )
            section("IDS", [("Ideographic Description", Tangut.get_ids(cp))])
            section(
                "Readings",
                [
                    ("Gong Hwang-cherng (Li Fanwen 2008)", Tangut.get_li_fanwen_reading(cp)),
                    ("Kychanov (2006)", Tangut.get_kychanov_reading(cp)),
                    ("Sofronov (1968)", Tangut.get_sofronov_reading(cp)),
                    ("Nishida (1966)", Tangut.get_nishida_reading(cp)),
                ],
            )
            section(
                "Source References",
                [
                    ("Li Fanwen 2008", Tangut.get_li_fanwen_number(cp)),
                    ("Li Fanwen 1997", Tangut.get_li_fanwen_1997_number(cp)),
                    ("Kychanov 2006", Tangut.get_kychanov_number(cp)),
                    ("Sofronov 1968", Tangut.get_sofronov_number(cp)),
                    ("Nishida 1966", Tangut.get_nishida_reference(cp)),
                    ("Merged", Tangut.get_merged_source(cp)),
                ],
            )
            if Tangut.has_variants(cp):
                section("Variants", [("Variants", Tangut.get_variants(cp))])
            return out
    except PROBE_ERRORS:
        logger.debug("supplementary: ignoring recoverable error", exc_info=True)

    # ── Egyptian hieroglyphs: CDialogHieroglyph ─────────────────────
    try:
        from babelsoft.scripts.hieroglyphs import Hieroglyphs

        if Hieroglyphs.is_egyptian_hieroglyph(cp):
            out["kind"] = "hieroglyph"
            section(
                "Catalogs",
                [
                    ("Gardiner", Hieroglyphs.get_catalog(cp)),
                    ("Hieroglyphica", Hieroglyphs.get_hieroglyphica(cp)),
                    ("JSesh", Hieroglyphs.get_jsesh(cp)),
                    ("Unikemet", Hieroglyphs.get_unikemet(cp)),
                    ("IFAO", Hieroglyphs.get_ifao(cp)),
                ],
            )
            section(
                "Description",
                [
                    ("Description", Hieroglyphs.get_description(cp)),
                    ("Function", Hieroglyphs.get_function(cp)),
                    ("Function value", Hieroglyphs.get_function_value(cp)),
                ],
            )
            section(
                "Behaviour",
                [
                    ("Mirroring", "No" if Hieroglyphs.is_no_mirror(cp) else "Yes"),
                    ("Rotation", "No" if Hieroglyphs.is_no_rotate(cp) else "Yes"),
                    ("Alternate sequence", Hieroglyphs.get_alternate_sequence(cp)),
                ],
            )
            return out
    except PROBE_ERRORS:
        logger.debug("supplementary: ignoring recoverable error", exc_info=True)

    return out


# ── Tools ▸ Generate UCD data ────────────────────────────────────────
# `CDialogUCD` builds UnicodeData.txt-style lines for a range or a block set,
# and `OnToolsXMLData` writes a `ucd.nounihan.flat` XML file.  Both walk the
# same repertoire, so the field list lives here once.

UCD_FIELDS = [
    "Code Point",
    "Character Name",
    "General Category",
    "Canonical Combining Class",
    "Bidi Class",
    "Decomposition",
    "Numeric Value (1)",
    "Numeric Value (2)",
    "Numeric Value (3)",
    "Bidi Mirrored",
    "Unicode 1.0 Name",
    "ISO Comment",
    "Upper Case Mapping",
    "Lower Case Mapping",
    "Title Case Mapping",
]


def _ucd_row(cp: int) -> list[str]:
    """One row of the UCD table — the 15 columns of `Unicode::UCDFields`."""
    from babelsoft.unicode.core import Unicode

    def s(fn, default=""):
        try:
            v = fn(cp)
            return default if v is None else str(v)
        except PROBE_ERRORS:
            return default

    def enum(fn, default=""):
        try:
            v = fn(cp)
            return v.name if hasattr(v, "name") else str(v)
        except PROBE_ERRORS:
            return default

    def mapping(fn):
        try:
            v = fn(cp)
            # UnicodeData.txt leaves the field empty when the mapping is the
            # character itself (which is what every CJK/Hangul row would
            # otherwise echo back).
            if not v or int(v) == cp:
                return ""
            return f"{int(v):04X}"
        except PROBE_ERRORS:
            return ""

    decomp = ""
    try:
        # The raw UnicodeData field, e.g. "0041 0300" or "<compat> 0066 0069".
        raw = Unicode.get_decomposition(cp)
        tag, _, values = raw.partition(">")
        if values:
            tag = tag.lstrip("<")
        else:
            tag, values = "", raw
        body = " ".join(f"{int(token, 16):04X}" for token in values.split())
        decomp = f"<{tag.lower()}> {body}".strip() if tag else body
    except PROBE_ERRORS:
        decomp = ""

    num1 = s(Unicode.get_numeric_value_str)
    return [
        f"{cp:04X}",
        s(Unicode.get_character_name),
        enum(Unicode.get_general_category),
        s(Unicode.get_canonical_combining_class, "0"),
        enum(Unicode.get_bidi_class),
        decomp,
        num1,
        "",
        "",
        "Y" if Unicode.get_bidi_mirrored(cp) else "N",
        s(Unicode.get_unicode1_name),
        "",
        mapping(Unicode.get_simple_uppercase),
        mapping(Unicode.get_simple_lowercase),
        mapping(Unicode.get_simple_titlecase),
    ]


def _ucd_repertoire(start: int, end: int, all_cjk: bool, all_hangul: bool) -> list[tuple[int, str]]:
    """Walk a range as `CDialogUCD` does.

    Returns `(codepoint, name_override)` pairs.  `UnicodeData.txt` abbreviates
    the algorithmic runs as `<CJK Ideograph, First>` / `<CJK Ideograph, Last>`
    pairs unless every character is asked for, and the dialog's two checkboxes
    are exactly that switch.
    """
    from babelsoft.unicode.core import Unicode

    out: list[tuple[int, str]] = []
    run: str | None = None
    run_start = 0
    last_cp = -1

    def close_run() -> None:
        nonlocal run
        if run is not None:
            out.append((run_start, f"<{run}, First>"))
            out.append((last_cp, f"<{run}, Last>"))
            run = None

    for cp in range(max(0, start), min(0x10FFFF, end) + 1):
        if Unicode.is_surrogate(cp):
            close_run()
            continue
        try:
            assigned = _is_assigned(cp)
            name = (Unicode.get_character_name(cp) or "") if assigned else ""
        except PROBE_ERRORS:
            assigned, name = False, ""
        if not assigned:
            close_run()
            continue

        kind = None
        if name.startswith("CJK UNIFIED IDEOGRAPH-"):
            kind = "CJK Ideograph"
        elif name.startswith("HANGUL SYLLABLE "):
            kind = "Hangul Syllable"

        abbreviate = kind is not None and (
            (kind == "CJK Ideograph" and not all_cjk) or (kind == "Hangul Syllable" and not all_hangul)
        )
        if abbreviate:
            if run != kind:
                close_run()
                run = kind
                run_start = cp
            last_cp = cp
            continue

        close_run()
        out.append((cp, ""))
    close_run()
    return out


def _ucd_rows_for(
    start: int,
    end: int,
    all_cjk: bool,
    all_hangul: bool,
    limit: int,
) -> tuple[int, list[list[str]]]:
    reps = _ucd_repertoire(start, end, all_cjk, all_hangul)
    rows: list[list[str]] = []
    for cp, override in reps[: max(1, limit)]:
        row = _ucd_row(cp)
        if override:
            row[1] = override
        rows.append(row)
    return len(reps), rows


@app.get("/api/ucd/fields")
def ucd_fields():
    return {"fields": UCD_FIELDS}


@app.get("/api/ucd/generate")
def ucd_generate(
    start: int = 0,
    end: int = 0xFFFF,
    all_cjk: bool = False,
    all_hangul: bool = False,
    limit: int = 20000,
):
    """UCD rows for a range — `CDialogUCD`'s Generate button."""
    total, rows = _ucd_rows_for(start, end, all_cjk, all_hangul, limit)
    return {"total": total, "shown": len(rows), "rows": rows}


@app.get("/api/ucd/xml")
def ucd_xml(start: int = 0, end: int = 0xFFFF, all_cjk: bool = False, all_hangul: bool = False):
    """`ucd.nounihan.flat`-style XML — Tools ▸ Generate Full UCD XML Data."""
    from babelsoft.unicode.core import Unicode
    from fastapi.responses import PlainTextResponse

    cps = _ucd_repertoire(start, end, all_cjk, all_hangul)
    parts = ['<?xml version="1.0" encoding="UTF-8"?>', f'<ucd version="{_uv()}">']
    escape = lambda t: t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for cp, override in cps:
        name = override
        gc = ""
        try:
            if not override:
                name = Unicode.get_character_name(cp) or ""
            gc = Unicode.get_general_category(cp).name
        except PROBE_ERRORS:
            logger.debug("ucd_xml: ignoring recoverable error", exc_info=True)
        parts.append(f'  <char cp="{cp:04X}" na="{escape(name)}" gc="{gc}"/>')
    parts.append("</ucd>")
    return PlainTextResponse("\n".join(parts), media_type="application/xml")


def _uv() -> str:
    """Latest Unicode version the bundled data covers ("" when unknown)."""
    try:
        from babelmap.backend.version import all_versions

        vs = all_versions()
        return vs[-1].get("version", "") if vs else ""
    except PROBE_ERRORS:
        return ""


@app.get("/api/unicode/scripts")
def unicode_scripts():
    """List of scripts (ISO 15924 code, name, chars, version) in the latest UCD."""
    from babelmap.backend.scripts import script_summary

    return {"scripts": script_summary()}


@app.get("/api/unicode/scripts/blocks")
def unicode_script_blocks(code: str = Query(..., min_length=1)):
    """Per-block character breakdown for one script in the latest release."""
    from babelmap.backend.scripts import script_blocks

    return {"code": code, "blocks": script_blocks(code)}


@app.get("/api/unicode/planes")
def unicode_planes():
    """Per-plane stats (Plane / Name / Abbrev / Blocks / Characters / Unassigned)."""
    from babelmap.backend.planes import plane_summary

    return {"planes": plane_summary()}


@app.get("/api/unicode/planes/{plane}/blocks")
def unicode_plane_blocks(plane: int):
    """Blocks contained in one plane of the latest release."""
    if not 0 <= plane <= 16:
        return JSONResponse({"error": f"Invalid plane {plane}"}, 400)
    from babelmap.backend.planes import plane_blocks

    return {"plane": plane, "blocks": plane_blocks(plane)}


@app.get("/api/unicode/blocks")
def unicode_blocks(version: str = Query(None, min_length=1)):
    """Block table for a Unicode version (defaults to the latest release)."""
    from babelmap.backend.version import all_versions, blocks_for_version

    if not version:
        version = all_versions()[-1]["version"]
    blocks = [
        dict(b, code_points=b["end"] - b["start"] + 1)
        for b in blocks_for_version(version)
        if not (0xD800 <= b["start"] <= 0xDFFF)
    ]
    return {"version": version, "blocks": blocks}


@app.get("/api/unicode/blocks/{name:path}/characters")
def unicode_block_characters(name: str, version: str = Query(None, min_length=1)):
    """Assigned characters inside one block of a Unicode version (defaults to latest)."""
    from babelmap.backend.version import (
        all_versions,
        assigned_codepoints_for,
        blocks_for_version,
    )

    if not version:
        version = all_versions()[-1]["version"]
    block = next((b for b in blocks_for_version(version) if b["name"] == name), None)
    if block is None:
        return JSONResponse({"error": "Block not found"}, 404)
    from babelsoft.unicode.core import Unicode

    cps = assigned_codepoints_for(version)
    lo = bisect.bisect_left(cps, block["start"])
    hi = bisect.bisect_right(cps, block["end"])
    characters = [{"codepoint": cp, "char": chr(cp), "name": _safe_name(Unicode, cp) or ""} for cp in cps[lo:hi]]
    return {"version": version, "block": name, "characters": characters}


@app.get("/api/unicode/blocks/{name:path}/unicodedata")
def unicode_block_unicodedata(name: str, version: str = Query(None, min_length=1)):
    """UnicodeData rows (codepoint + name + all UCD fields) for every assigned
    character in one block of a Unicode version (defaults to latest)."""
    from babelmap.backend.history import block_unicodedata
    from babelmap.backend.version import all_versions

    if not version:
        version = all_versions()[-1]["version"]
    rows = block_unicodedata(version, name)
    if rows is None:
        return JSONResponse({"error": "Block not found"}, 404)
    return {"version": version, "block": name, "rows": rows}


# ── OpenType Test Framework (HarfBuzz shaping) ────────────────────────


def _payload_font_bytes(payload: dict) -> bytes | None:
    """Font bytes from a request body — ``font_b64`` wins over ``font_path``.

    Returns ``None`` when the body carries no font (callers turn that into a 400).
    """
    from babelmap.backend.opentype import font_bytes, font_bytes_from_b64

    b64 = payload.get("font_b64")
    fpath = payload.get("font_path")
    if b64:
        return font_bytes_from_b64(b64)
    if fpath:
        return font_bytes(fpath)
    return None


@app.get("/api/opentype/fonts")
def opentype_fonts():
    """System fonts for the OpenType Test Framework."""
    from babelmap.backend.opentype import list_system_fonts

    return {"fonts": list_system_fonts()}


@app.post("/api/opentype/font_faces")
def opentype_font_faces(payload: dict):
    """Faces inside a font file, for the dialog's face picker.

    Body: {font_b64?|font_path?}

    → {container, container_label, is_collection, face_count, faces: [{index,
    label, family, subfamily, full_name, glyph_count, outlines}],
    flatten_supported, note, size}

    Collections (TTC/OTC) list every face; WOFF/WOFF2 report their single face.
    """
    from babelmap.backend.font_source import describe

    try:
        data = _payload_font_bytes(payload)
    except PROBE_ERRORS:
        return JSONResponse({"error": "Font could not be loaded"}, 400)
    if not data:
        return JSONResponse({"error": "No font provided (font_b64 or font_path)"}, 400)
    try:
        return describe(data)
    except PROBE_ERRORS as e:
        return JSONResponse({"error": f"Font inspection failed: {e}"}, 400)


@app.get("/api/opentype/meta")
def opentype_meta():
    """Full ISO 15924 script list + common OpenType language tags."""
    from babelmap.backend.opentype import languages_list, scripts_list

    return {"scripts": scripts_list(), "languages": languages_list()}


@app.post("/api/opentype/shape")
def opentype_shape(payload: dict):
    """Shape text with a font (HarfBuzz via uharfbuzz) and return the shaping
    trace (Crowbar-style stages), final glyph run, GSUB/GPOS feature tags and
    optionally a rendered SVG.

    Body: {font_b64?, font_path?, font_face? (index into a TTC/OTC; default 0),
    font_delivery? ("auto" | "flatten" | "raw", default "auto"), text,
    direction?, script?, language?, cluster?, flags?: [..], features? (dict or
    string), variations?, show_all_lookups?, glyph_mode?, render?: bool,
    size?: int, color?}

    The font source layer (babelmap/backend/font_source.py) turns TTC/OTC and
    WOFF/WOFF2 input into a single-face sfnt before the engines see it; the
    response reports what it did in ``font_source``.
    """
    from babelmap.backend.opentype import (
        feature_tags,
        font_bytes,
        font_bytes_from_b64,
        font_info,
        render_svg,
        shape_flat,
        shape_trace,
    )

    data = None
    b64 = payload.get("font_b64")
    fpath = payload.get("font_path")
    try:
        if b64:
            data = font_bytes_from_b64(b64)
        elif fpath:
            data = font_bytes(fpath)
    except PROBE_ERRORS:
        return JSONResponse({"error": "Font could not be loaded"}, 400)
    if not data:
        return JSONResponse({"error": "No font provided (font_b64 or font_path)"}, 400)

    # ── Font source: TTC/OTC + WOFF/WOFF2 → single-face sfnt for the engines ──
    # The engines disagree about container support (Yudit refuses TTC outright;
    # DWriteCore/Uniscribe/Graphite/ICU/FreeType cannot be told which face to
    # use), so normalise once here and use these bytes for everything below —
    # engines *and* the fontTools-based metadata/render helpers.
    # See babelmap/backend/font_source.py.
    from babelmap.backend.font_source import FaceNotFound, prepare

    try:
        src = prepare(
            data,
            delivery=str(payload.get("font_delivery", "auto")),
            face_index=int(payload.get("font_face", payload.get("font_index", 0)) or 0),
        )
    except FaceNotFound as e:
        return JSONResponse({"error": f"Face selection failed: {e}"}, 400)
    data, font_index = src.data, src.face_index
    # The fontTools-based helpers below (feature tags, glyph names, outlines) can
    # only read a single face, so give them one even when the engine itself got
    # the raw collection (delivery="raw").
    meta_data = data
    if not src.flattened and src.container not in ("sfnt", "unknown"):
        from babelmap.backend.font_source import FontSourceError, flatten

        try:
            meta_data = flatten(src.original, src.requested_face)
        except FontSourceError:
            pass

    try:
        engine = payload.get("engine", "harfbuzz")
        if engine in ("uniscribe", "directwrite") and os.name != "nt":
            # These are the Windows-native shaping APIs (usp10 / DWriteCore);
            # on other platforms the engine is simply not available (the app
            # itself stays cross-platform).  The Wine variants
            # (uniscribe_wine / directwrite_wine) run everywhere and are not
            # gated here — see babelmap/README.md.
            return JSONResponse({"error": f"'{engine}' engine is Windows-only"}, 400)
        if engine in ("uniscribe", "uniscribe_wine"):
            from babelmap.backend.uniscribe_shaper import shape_with_uniscribe

            result = shape_with_uniscribe(
                data,
                payload.get("text", ""),
                direction=payload.get("direction", "auto"),
                script=payload.get("script", ""),
                language=payload.get("language", ""),
                features=payload.get("features"),
                # usp10 = native Microsoft Uniscribe (single run); wineusp =
                # Wine's Uniscribe reimplementation with a real per-lookup trace.
                # NB (pyusp 0.6.0): `features` now really applies on usp10 and
                # *replaces* the run's default GSUB set; the Wine port cannot
                # apply feature records, so pyusp raises and the dialog shows the
                # "Shaping failed: features …" body instead of an ignored toggle.
                backend="usp10" if engine == "uniscribe" else "wineusp",
                trace=engine == "uniscribe_wine",
            )
        elif engine == "freetype":
            from babelmap.backend.freetype_shaper import shape_with_freetype

            result = shape_with_freetype(
                b64 or fpath or "",
                payload.get("text", ""),
                is_b64=bool(b64),
                direction=payload.get("direction", "auto"),
                script=payload.get("script", ""),
                language=payload.get("language", ""),
                features=payload.get("features"),
            )
        elif engine in ("directwrite", "directwrite_wine"):
            from babelmap.backend.dwriteshape_shaper import shape_with_dwrite

            result = shape_with_dwrite(
                data,
                payload.get("text", ""),
                direction=payload.get("direction", "auto"),
                script=payload.get("script", ""),
                language=payload.get("language", ""),
                features=payload.get("features"),
                show_all_lookups=bool(payload.get("show_all_lookups")),
                # dwcore = native DWriteCore (full trace); winedwrite = Wine
                # DWrite port (cross-platform, full trace).
                backend="dwcore" if engine == "directwrite" else "winedwrite",
            )
        elif engine == "graphite":
            from babelmap.backend.graphite_shaper import shape_with_graphite

            result = shape_with_graphite(
                data,
                payload.get("text", ""),
                direction=payload.get("direction", "auto"),
                script=payload.get("script", ""),
                language=payload.get("language", ""),
                features=payload.get("features"),
            )
        elif engine == "icu":
            from babelmap.backend.icu_shaper import shape_with_icu

            result = shape_with_icu(
                data,
                payload.get("text", ""),
                direction=payload.get("direction", "auto"),
                script=payload.get("script", ""),
                language=payload.get("language", ""),
                features=payload.get("features"),
            )
        elif engine == "babelscript":
            from babelmap.backend.babelscript_shaper import shape_with_babelscript

            result = shape_with_babelscript(
                data,
                payload.get("text", ""),
                direction=payload.get("direction", "auto"),
                script=payload.get("script", ""),
                language=payload.get("language", ""),
                features=payload.get("features"),
            )
        elif engine == "harfrust":
            from babelmap.backend.harfrust_shaper import shape_with_harfrust

            result = shape_with_harfrust(
                data,
                payload.get("text", ""),
                direction=payload.get("direction", "auto"),
                script=payload.get("script", ""),
                language=payload.get("language", ""),
                features=payload.get("features"),
                variations=payload.get("variations"),
                show_all_lookups=bool(payload.get("show_all_lookups")),
                font_index=font_index,
            )
        elif engine == "yudit":
            from babelmap.backend.yudit_shaper import shape_with_yudit

            result = shape_with_yudit(
                data,
                payload.get("text", ""),
                direction=payload.get("direction", "auto"),
                script=payload.get("script", ""),
                language=payload.get("language", ""),
                features=payload.get("features"),
                variations=payload.get("variations"),
                show_all_lookups=bool(payload.get("show_all_lookups")),
                font_index=font_index,
            )
        elif engine == "harfbuzz_fallback":
            result = shape_flat(
                data,
                payload.get("text", ""),
                shapers=["fallback"],
                direction=payload.get("direction", "auto"),
                script=payload.get("script", "auto"),
                language=payload.get("language", ""),
                cluster_level=payload.get("cluster", "monotone_graphemes"),
                flags=payload.get("flags") or [],
                features=payload.get("features"),
                font_index=font_index,
            )
        else:
            result = shape_trace(
                data,
                payload.get("text", ""),
                direction=payload.get("direction", "auto"),
                script=payload.get("script", "auto"),
                language=payload.get("language", ""),
                cluster_level=payload.get("cluster", "monotone_graphemes"),
                flags=payload.get("flags") or [],
                features=payload.get("features"),
                variations=payload.get("variations"),
                show_all_lookups=bool(payload.get("show_all_lookups")),
                glyph_mode=bool(payload.get("glyph_mode")),
                font_index=font_index,
            )
    except PROBE_ERRORS as e:
        return JSONResponse({"error": f"Shaping failed: {e}"}, 400)

    result["features"] = feature_tags(meta_data)
    result["font_info"] = font_info(meta_data)
    # What the font source layer did (container, chosen face, delivery) — the
    # dialog shows it and uses `faces` for the face picker.
    result["font_source"] = src.info

    # Glyph names (shape_trace already provides them; Uniscribe path needs them)
    if "glyph_names" not in result:
        from babelmap.backend.opentype import _glyph_names, used_glyph_ids

        result["glyph_names"] = _glyph_names(
            meta_data, used_glyph_ids(result.get("stages", []), result.get("final", []))
        )

    if payload.get("render"):
        try:
            result["svg"] = render_svg(
                meta_data,
                result["final"],
                result["upem"],
                size=int(payload.get("size", 128)),
                color=payload.get("color", "#1f2937"),
                variations=payload.get("variations"),
            )
        except PROBE_ERRORS as e:
            result["svg_error"] = str(e)
    return result


@app.post("/api/opentype/render")
def opentype_render(payload: dict):
    """Render an arbitrary glyph run as SVG (for hover / partial-trace views).

    Body: {font_b64?|font_path?, font_face?, font_delivery?, glyphs:
    [{g, ax, dx, dy, cl}], upem, size?, color?, highlight_cl?, highlight_color?,
    variations?} — the glyph ids come from ``/api/opentype/shape``, so the same
    ``font_face`` the shape used has to be requested here as well.
    """
    from babelmap.backend.font_source import FaceNotFound, FontSourceError, flatten
    from babelmap.backend.opentype import render_svg

    try:
        raw = _payload_font_bytes(payload)
    except PROBE_ERRORS:
        return JSONResponse({"error": "Font could not be loaded"}, 400)
    if not raw:
        return JSONResponse({"error": "No font provided"}, 400)
    # Outlines must come from the very same face the shape used, otherwise the
    # glyph ids would not match.  Rendering reads them through fontTools, which
    # only understands a single face, so this always flattens (the delivery mode
    # only matters for the shaping engines).
    face = int(payload.get("font_face", payload.get("font_index", 0)) or 0)
    try:
        data = flatten(raw, face)
    except FaceNotFound as e:
        return JSONResponse({"error": f"Face selection failed: {e}"}, 400)
    except FontSourceError:
        data = raw
    try:
        svg = render_svg(
            data,
            payload.get("glyphs") or [],
            int(payload.get("upem", 2048)),
            size=int(payload.get("size", 128)),
            color=payload.get("color", "#1f2937"),
            highlight_cl=int(payload.get("highlight_cl", -1)),
            highlight_color=payload.get("highlight_color", "#e23d3d"),
            variations=payload.get("variations"),
        )
    except PROBE_ERRORS as e:
        return JSONResponse({"error": f"Render failed: {e}"}, 400)
    return {"svg": svg}


@app.get("/api/unicode/diff")
def unicode_diff(
    from_version: str = Query(..., alias="from", min_length=1), to_version: str = Query(..., alias="to", min_length=1)
):
    """Changes between two Unicode versions: blocks added/removed + character counts."""
    from babelmap.backend.version import assigned_codepoints_for, blocks_for_version

    a_blocks = blocks_for_version(from_version)
    b_blocks = blocks_for_version(to_version)
    a_names = {b["name"] for b in a_blocks}
    b_names = {b["name"] for b in b_blocks}
    added_blocks = [dict(b, code_points=b["end"] - b["start"] + 1) for b in b_blocks if b["name"] not in a_names]
    removed_blocks = [dict(b, code_points=b["end"] - b["start"] + 1) for b in a_blocks if b["name"] not in b_names]

    a_cps = set(assigned_codepoints_for(from_version))
    b_cps = set(assigned_codepoints_for(to_version))
    added_cps = sorted(b_cps - a_cps)
    removed_cps = sorted(a_cps - b_cps)

    per_block_added: list[dict] = []
    for b in b_blocks:
        lo = bisect.bisect_left(added_cps, b["start"])
        hi = bisect.bisect_right(added_cps, b["end"])
        if hi > lo:
            per_block_added.append(
                {
                    "name": b["name"],
                    "start": b["start"],
                    "end": b["end"],
                    "added": hi - lo,
                    "version": b.get("version"),
                }
            )
    per_block_added.sort(key=lambda x: x["added"], reverse=True)

    return {
        "from": from_version,
        "to": to_version,
        "added_blocks": added_blocks,
        "removed_blocks": removed_blocks,
        "added_characters": len(added_cps),
        "removed_characters": len(removed_cps),
        "per_block_added": per_block_added,
    }


@app.get("/api/unicode/history")
def unicode_character_history(cp: int):
    """Character History — codepoint/name of one character across versions."""
    from babelmap.backend.history import character_history

    if not Unicode.is_valid_code_point(cp) or Unicode.is_surrogate(cp):
        return JSONResponse({"error": "Invalid"}, 400)
    return character_history(cp)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "babelmap.backend.server:app",
        host="127.0.0.1",
        port=18080,
        log_level="warning",
        reload=True,
        reload_dirs=[str(BABELLIB / "babelsoft"), str(REPO_ROOT / "babelmap")],
    )
