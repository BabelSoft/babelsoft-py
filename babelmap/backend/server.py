"""BabelMap Python Backend — FastAPI server. Start: python backend/server.py"""

from __future__ import annotations

import base64
import io
import json
import os
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse, StreamingResponse  # noqa: E402

app = FastAPI(title="BabelMap Backend", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

GRID_ROWS, GRID_COLS = 8, 16
VALID_PLANES = list(range(17))  # 0–16, all Unicode planes

# ── Load pre-built blocks data ─────────────────────────────────────
_BLOCKS_JSON = Path(__file__).parent / "blocks.json"
_ALL_BLOCKS: list[dict] = json.loads(_BLOCKS_JSON.read_text(encoding="utf-8"))

# Index: blocks_by_plane[p] = [blocks for plane p]
_blocks_by_plane: dict[int, list[dict]] = {}
for b in _ALL_BLOCKS:
    p = b["start"] >> 16
    _blocks_by_plane.setdefault(p, []).append(b)

# Pre-compute max scroll per plane (last block end)
_max_scroll_by_plane: dict[int, int] = {}
for p, blks in _blocks_by_plane.items():
    _max_scroll_by_plane[p] = (blks[-1]["end"] - p * 0x10000) // GRID_COLS

# ── Load assigned codepoint ranges ─────────────────────────────────
_ASSIGNED_JSON = Path(__file__).parent / "assigned_ranges.json"
_ASSIGNED_RANGES: list[list[int]] = json.loads(_ASSIGNED_JSON.read_text(encoding="utf-8"))


def _is_assigned(cp: int) -> bool:
    """Binary search through assigned ranges. Returns True if cp is an assigned character."""
    lo, hi = 0, len(_ASSIGNED_RANGES) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        s, e = _ASSIGNED_RANGES[mid]
        if cp < s:
            hi = mid - 1
        elif cp > e:
            lo = mid + 1
        else:
            return True
    return False


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

# Plane metadata (hardcoded, no Unicode import needed)
_PLANE_NAMES = {
    0: "Basic Multilingual Plane",
    1: "Supplementary Multilingual Plane",
    2: "Supplementary Ideographic Plane",
    3: "Tertiary Ideographic Plane",
    14: "Supplementary Special-purpose Plane",
    15: "Private Use Area-A",
    16: "Private Use Area-B",
}
_PLANE_ABBREV = {0: "BMP", 1: "SMP", 2: "SIP", 3: "TIP", 14: "SSP", 15: "PUA-A", 16: "PUA-B"}


@app.get("/api/planes")
def list_planes():
    return [
        {
            "plane": p,
            "name": _PLANE_NAMES[p],
            "abbreviation": _PLANE_ABBREV[p],
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
    from src.unicode.core import Unicode

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
    from src.unicode.core import Unicode

    if not Unicode.is_valid_code_point(cp) or Unicode.is_surrogate(cp):
        return JSONResponse({"error": "Invalid"}, 400)
    try:
        n = Unicode.get_character_name(cp)
    except Exception:
        n = f"U+{cp:04X}"
    try:
        gc = str(Unicode.get_general_category(cp))
    except Exception:
        gc = "Cn"
    try:
        sc = str(Unicode.get_script(cp))
    except Exception:
        sc = "Unknown"
    blk = _find_block(cp)
    bn = blk["name"] if blk else "Unknown"
    info = {"codepoint": cp, "name": n, "general_category": gc, "script": sc, "block": bn}
    try:
        from src.cjkv.cjk import CJK

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
    return info


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
        from src.cjkv.cjk import CJKLoader

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "babelmap.backend.server:app",
        host="127.0.0.1",
        port=18080,
        log_level="warning",
        reload=True,
        reload_dirs=[str(PROJECT_ROOT / "src"), str(PROJECT_ROOT / "babelmap")],
    )
