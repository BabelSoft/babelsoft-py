"""BabelMap Python Backend — FastAPI server. Start: python backend/server.py"""

from __future__ import annotations

import base64
import bisect
import io
import os
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BABELLIB = REPO_ROOT / "babellib"
# Both roots must be on sys.path: the repo root (for `babelmap.*`, incl. the
# uvicorn reloader's `babelmap.backend.server:app`) and babellib/ (for `babelsoft.*`).
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BABELLIB))

from fastapi import FastAPI, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse, StreamingResponse  # noqa: E402
from babelsoft.unicode.core import Unicode  # noqa: E402

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
        except Exception:
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
    except Exception:
        return None


def _render_glyph(cp: int, family: str, size: int = 16) -> Optional[str]:
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
    except Exception:
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
def get_grid(plane: int, scroll: int = Query(0, ge=0), filter_no_block: bool = Query(True)):
    if plane not in VALID_PLANES:
        return JSONResponse({"error": f"Invalid plane {plane}"}, 400)
    key = (plane, filter_no_block)
    _build_plane_rows(plane, filter_no_block)
    rows = _plane_rows[key]
    scroll = max(0, min(scroll, _plane_max_scroll[key]))
    page = rows[scroll : scroll + GRID_ROWS]
    cells = [r["cells"] for r in page]
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


@app.get("/api/codepoint/{cp}")
def codepoint_info(cp: int):
    from babelsoft.unicode.core import Unicode

    if not Unicode.is_valid_code_point(cp) or Unicode.is_surrogate(cp):
        return JSONResponse({"error": "Invalid"}, 400)

    def _s(fn, default=""):
        try:
            v = fn(cp)
            return v if v not in (None, "") else default
        except Exception:
            return default

    def _enum(fn):
        try:
            return fn(cp).name
        except Exception:
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
    except Exception:
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
    except Exception:
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
    except Exception:
        info["extended"] = []
        info["name_aliases"] = []
    # Ideographic Variation Sequences (VS17..VS256) from IVD_Sequences.txt.
    try:
        from babelsoft.cjkv.cjk import CJK

        info["ideographic_variants"] = [[vs, collection, ref] for vs, collection, ref in CJK(cp).ivs_sequences()]
    except Exception:
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
            except Exception:
                pass
            try:
                info["radical_stroke"] = str(cjk.primary_radical_stroke())
            except Exception:
                pass
    except Exception:
        pass
    # Ideographic (CJKV) properties — mirrors the C++ CDialogCJKV dialog.
    try:
        from babelsoft.cjkv.cjk import CJK

        info["ideographic"] = CJK(cp).ideographic_properties()
    except Exception:
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
    except Exception:
        pass
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
    except Exception:
        results = []
    return {"query": q, "results": results}


@app.get("/api/emoji/list")
def emoji_list(limit: int = Query(0, ge=0, le=6000)):
    """All RGI emoji in CLDR order (browse mode). limit=0 → all."""
    from babelsoft.unicode.emoji import all_emoji

    try:
        entries = all_emoji()
    except Exception:
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


@app.get("/api/unicode/versions")
def unicode_versions():
    """Unicode version history + per-version block lists."""
    from babelmap.backend.version import all_versions, blocks_for_version, get_version_history

    versions = all_versions()
    blocks_by_version = {v["version"]: blocks_for_version(v["version"]) for v in versions}
    history = get_version_history()
    return {"versions": versions, "blocks_by_version": blocks_by_version, "history": history}


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


@app.get("/api/opentype/fonts")
def opentype_fonts():
    """System fonts for the OpenType Test Framework."""
    from babelmap.backend.opentype import list_system_fonts

    return {"fonts": list_system_fonts()}


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

    Body: {font_b64?, font_path?, text, direction?, script?, language?,
    cluster?, flags?: [..], features? (dict or string), variations?,
    show_all_lookups?, glyph_mode?, render?: bool, size?: int,
    font_index?: int, color?}
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
    except Exception:
        return JSONResponse({"error": "Font could not be loaded"}, 400)
    if not data:
        return JSONResponse({"error": "No font provided (font_b64 or font_path)"}, 400)

    try:
        engine = payload.get("engine", "harfbuzz")
        if engine in ("uniscribe", "directwrite") and os.name != "nt":
            # These are Windows-native shaping APIs; on other platforms the
            # engine is simply not available (the app itself stays cross-platform).
            return JSONResponse({"error": f"'{engine}' engine is Windows-only"}, 400)
        if engine == "uniscribe":
            from babelmap.backend.uniscribe_shaper import shape_with_uniscribe

            result = shape_with_uniscribe(
                b64 or fpath or "",
                payload.get("text", ""),
                is_b64=bool(b64),
                direction=payload.get("direction", "auto"),
                script=payload.get("script", ""),
                language=payload.get("language", ""),
                features=payload.get("features"),
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
        elif engine == "directwrite":
            from babelmap.backend.dwriteshape_shaper import shape_with_dwrite

            result = shape_with_dwrite(
                data,
                payload.get("text", ""),
                direction=payload.get("direction", "auto"),
                script=payload.get("script", ""),
                language=payload.get("language", ""),
                features=payload.get("features"),
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
                font_index=int(payload.get("font_index", 0)),
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
                font_index=int(payload.get("font_index", 0)),
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
                font_index=int(payload.get("font_index", 0)),
            )
    except Exception as e:
        return JSONResponse({"error": f"Shaping failed: {e}"}, 400)

    result["features"] = feature_tags(data)
    result["font_info"] = font_info(data)

    # Glyph names (shape_trace already provides them; Uniscribe path needs them)
    if "glyph_names" not in result:
        from babelmap.backend.opentype import _glyph_names

        used: set[int] = set()
        for st in result.get("stages", []):
            for g in st.get("glyphs", []):
                used.add(g["g"])
        for g in result.get("final", []):
            used.add(g["g"])
        result["glyph_names"] = _glyph_names(data, used)

    if payload.get("render"):
        try:
            result["svg"] = render_svg(
                data,
                result["final"],
                result["upem"],
                size=int(payload.get("size", 128)),
                color=payload.get("color", "#1f2937"),
                variations=payload.get("variations"),
            )
        except Exception as e:
            result["svg_error"] = str(e)
    return result


@app.post("/api/opentype/render")
def opentype_render(payload: dict):
    """Render an arbitrary glyph run as SVG (for hover / partial-trace views).

    Body: {font_b64?|font_path?, glyphs: [{g, ax, dx, dy, cl}], upem,
    size?, color?, highlight_cl?, highlight_color?, variations?}
    """
    from babelmap.backend.opentype import font_bytes, font_bytes_from_b64, render_svg

    data = None
    b64 = payload.get("font_b64")
    fpath = payload.get("font_path")
    try:
        if b64:
            data = font_bytes_from_b64(b64)
        elif fpath:
            data = font_bytes(fpath)
    except Exception:
        return JSONResponse({"error": "Font could not be loaded"}, 400)
    if not data:
        return JSONResponse({"error": "No font provided"}, 400)
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
    except Exception as e:
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
