"""BabelMap Python Backend — FastAPI server. Start: python backend/server.py"""

from __future__ import annotations
import base64, io, json, os, sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="BabelMap Backend", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

GRID_ROWS, GRID_COLS = 8, 16
VALID_PLANES = [0, 1, 2, 3, 14, 15, 16]

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
    except:
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
    except:
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
    return [b for b in _ALL_BLOCKS if b["plane"] in VALID_PLANES]


@app.get("/api/blocks/{plane}")
def list_blocks_for_plane(plane: int):
    return _blocks_by_plane.get(plane, [])


@app.get("/api/grid/{plane}")
def get_grid(plane: int, scroll: int = Query(0, ge=0)):
    if plane not in VALID_PLANES:
        return JSONResponse({"error": f"Invalid plane {plane}"}, 400)
    from src.unicode.core import Unicode

    ps = plane * 0x10000
    pe = min(ps + 0xFFFF, 0x10FFFF)
    base = ps + scroll * GRID_COLS
    if base > pe:
        base = max(ps, pe - GRID_ROWS * GRID_COLS + 1)
    blk = _find_block_fast(base)
    bn, bs, be = blk["name"], blk["start"], blk["end"]
    ba = blk.get("assigned", be - bs + 1)
    cells: list[list[dict]] = []
    row_bases: list[int] = []
    block_boundaries: list[int] = []
    prev_bn = bn
    row_offset = 0  # how many rows we've collected
    probe = base
    max_probe = pe - GRID_COLS + 1

    while row_offset < GRID_ROWS and probe <= max_probe:
        row_start = probe
        rb = _find_block_fast(row_start)
        if rb["name"] != prev_bn:
            block_boundaries.append(row_offset)
            prev_bn = rb["name"]
        rd: list[dict] = []
        has_assigned = False
        for c in range(GRID_COLS):
            cp = row_start + c
            if cp > pe or cp > 0x10FFFF or (0xD800 <= cp <= 0xDFFF):
                rd.append({"codepoint": -1, "char_name": None})
            elif not _is_assigned(cp):
                rd.append({"codepoint": cp, "char_name": None, "reserved": True})
            else:
                rd.append({"codepoint": cp, "char_name": _safe_name(Unicode, cp)})
                has_assigned = True
        if has_assigned:
            if row_offset == 0:
                # First actual row: update block info
                blk = rb
                bn, bs, be = blk["name"], blk["start"], blk["end"]
                ba = blk.get("assigned", be - bs + 1)
                prev_bn = bn
            cells.append(rd)
            row_bases.append(row_start - ps)
            row_offset += 1
        probe += GRID_COLS

    # If we couldn't fill 8 rows, pad with empty
    while row_offset < GRID_ROWS:
        probe = max(ps, pe - (GRID_ROWS - row_offset) * GRID_COLS)
        rd = [{"codepoint": -1, "char_name": None} for _ in range(GRID_COLS)]
        cells.append(rd)
        row_bases.append(probe - ps)
        row_offset += 1

    return {
        "plane": plane,
        "block_name": bn,
        "block_start": bs,
        "block_end": be,
        "block_count": be - bs + 1,
        "block_assigned": ba,
        "scroll_position": scroll,
        "max_scroll": _max_scroll_by_plane.get(plane, (pe - ps) // GRID_COLS),
        "cells": cells,
        "row_bases": row_bases,
        "block_boundaries": block_boundaries,
    }


def _safe_name(Unicode, cp: int) -> str | None:
    try:
        n = Unicode.get_character_name(cp)
        if n and not n.startswith("<"):
            return n
    except Exception:
        pass
    # Algorithmic names for CJK / Tangut / Nushu / Hangul
    blk = _find_block(cp)
    if blk:
        bn = blk["name"]
        h = f"{cp:04X}" if cp <= 0xFFFF else f"{cp:05X}"
        if "CJK Unified Ideograph" in bn:
            return f"CJK UNIFIED IDEOGRAPH-{h}"
        if "CJK Compatibility Ideograph" in bn:
            return f"CJK COMPATIBILITY IDEOGRAPH-{h}"
        if "Tangut Ideograph" in bn or ("Tangut" in bn and "Ideograph" in bn):
            return f"TANGUT IDEOGRAPH-{h}"
        if "Tangut Component" in bn:
            return f"TANGUT COMPONENT-{h}"
        if "Nushu" in bn:
            return f"NUSHU CHARACTER-{h}"
        if "Hangul Syllable" in bn:
            return f"HANGUL SYLLABLE-{h}"
    return None


@app.get("/api/grid/{plane}/goto/{cp}")
def grid_goto(plane: int, cp: int):
    return get_grid(plane, max(0, (cp - plane * 0x10000) // GRID_COLS))


@app.get("/api/grid/{plane}/block/{name:path}")
def grid_block(plane: int, name: str):
    for b in _ALL_BLOCKS:
        if b["name"] == name:
            return get_grid(plane, max(0, (b["start"] - plane * 0x10000) // GRID_COLS))
    return JSONResponse({"error": "Not found"}, 404)


@app.get("/api/grid/{plane}/navigate")
def grid_nav(plane: int, scroll: int = 0, direction: str = "page_next"):
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
    return get_grid(plane, ns)


@app.get("/api/codepoint/{cp}")
def codepoint_info(cp: int):
    from src.unicode.core import Unicode

    if not Unicode.is_valid_code_point(cp) or Unicode.is_surrogate(cp):
        return JSONResponse({"error": "Invalid"}, 400)
    try:
        n = Unicode.get_character_name(cp)
    except:
        n = f"U+{cp:04X}"
    try:
        gc = str(Unicode.get_general_category(cp))
    except:
        gc = "Cn"
    try:
        sc = str(Unicode.get_script(cp))
    except:
        sc = "Unknown"
    blk = _find_block(cp)
    bn = blk["name"] if blk else "Unknown"
    info = {"codepoint": cp, "name": n, "general_category": gc, "script": sc, "block": bn}
    try:
        from src.cjkv.cjk import CJK

        cjk = CJK(cp)
        if cjk.is_cjk_ideograph():
            try:
                info["pinyin"] = cjk.get_pinyin_for_char(cp) or []
            except:
                pass
            try:
                info["radical_stroke"] = str(cjk.primary_radical_stroke())
            except:
                pass
    except:
        pass
    return info


@app.get("/api/glyph/{cp}")
def glyph(cp: int, font: str = "Arial", size: int = 16):
    return {"codepoint": cp, "glyph_b64": _render_glyph(cp, font, size)}


# Fast search: only scan codepoints that have names in the UCD
_search_cache: list[tuple[int, str]] | None = None


def _build_search_cache():
    global _search_cache
    if _search_cache is not None:
        return
    from src.unicode.core import Unicode

    _search_cache = []
    for cp in range(0x0000, 0x10000):
        if Unicode.is_surrogate(cp) or not Unicode.is_valid_code_point(cp):
            continue
        try:
            n = Unicode.get_character_name(cp)
            if n and not n.startswith("<"):
                _search_cache.append((cp, n))
        except:
            pass


@app.get("/api/search/name")
def search_by_name(q: str = Query(..., min_length=1)):
    _build_search_cache()
    results = []
    qu = q.upper()
    for cp, n in _search_cache:
        if qu in n.upper():
            results.append({"codepoint": cp, "name": n})
            if len(results) >= 100:
                break
    return results


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

    uvicorn.run(app, host="127.0.0.1", port=17890)
