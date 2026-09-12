"""OpenType Test Framework — HarfBuzz shaping, ported from the C++ BabelMap
``CDialogOpenTypeTest`` (which used Uniscribe) and inspired by the Crowbar
web tool (corvelsoftware.co.uk/crowbar) which uses HarfBuzz.

Uses the ``uharfbuzz`` HarfBuzz binding for shaping and ``fontTools`` for
glyph outlines (SVG rendering) and font metadata.  Exposes:

- :func:`list_system_fonts` — Windows system fonts with family names.
- :func:`shape` — shape text with a font; returns the glyph run + the HarfBuzz
  shaping trace (lookups applied / skipped, like Crowbar's "Show All Lookups").
- :func:`render_svg` — compose the shaped glyph run into an SVG.
"""

from __future__ import annotations

import base64
import glob
import io
import os
import re

FONT_DIRS = [
    r"C:\Windows\Fonts",
]

# Font containers the picker offers (shaping normalises them, see
# backend/font_source.py — collections and WOFF/WOFF2 included).
FONT_EXTS = ("*.ttf", "*.otf", "*.ttc", "*.otc", "*.woff", "*.woff2")

# HarfBuzz buffer flags exposed in the UI (name → BufferFlags member).
BUFFER_FLAGS = [
    "BOT",
    "EOT",
    "PRESERVE_DEFAULT_IGNORABLES",
    "REMOVE_DEFAULT_IGNORABLES",
    "DO_NOT_INSERT_DOTTED_CIRCLE",
    "VERIFY",
    "PRODUCE_UNSAFE_TO_CONCAT",
    "PRODUCE_SAFE_TO_INSERT_TATWEEL",
]

# Cluster levels exposed in the UI (name → BufferClusterLevel member).
CLUSTER_LEVELS = {
    "monotone_graphemes": "MONOTONE_GRAPHEMES",
    "monotone_characters": "MONOTONE_CHARACTERS",
    "characters": "CHARACTERS",
    "graphemes": "GRAPHEMES",
}

# Trace rows that still carry *unicode codepoints* rather than glyph ids: the ones
# an engine reports before its cmap step (HarfBuzz: "Start of shaping" and
# "start preprocess-text").  Crowbar marks exactly these with `glyphs: false`, and
# we flag them per row with `cps: True` so the UI can label them U+XXXX instead of
# looking up a meaningless glyph name for a codepoint.  Engine-specific pre-cmap
# rows are marked by the shaper that knows them (see yudit_shaper).
UNICODE_ROWS = frozenset({"Start of shaping", "start of shaping", "start preprocess-text", "start of text"})

# Common scripts for the dropdown (ISO 15924 tags).
COMMON_SCRIPTS = [
    "latn",
    "grek",
    "cyrl",
    "hebr",
    "arab",
    "syrc",
    "thaa",
    "deva",
    "beng",
    "guru",
    "gujr",
    "orya",
    "taml",
    "telu",
    "knda",
    "mlym",
    "sinh",
    "thai",
    "lao",
    "tibt",
    "myan",
    "geor",
    "hang",
    "ethi",
    "cher",
    "cans",
    "ogam",
    "runr",
    "khmr",
    "mong",
    "hira",
    "kana",
    "bopo",
    "hanb",
    "cakm",
    "tale",
    "mymr",
    "cari",
    "lyci",
    "lydi",
    "hans",
    "hant",
    "latn",
]


def _font_family(path: str) -> str:
    """Best-effort family name from a font file."""
    try:
        from fontTools.ttLib import TTFont

        tt = TTFont(path, fontNumber=0, lazy=True)
        for nid in (4, 1):
            n = tt["name"].getDebugName(nid)
            if n:
                return n
    except Exception:
        pass
    return os.path.basename(path)


def _face_count(path: str) -> int:
    """Faces in a font file — 1 unless it is a TTC/OTC collection."""
    try:
        from babelmap.backend.font_source import face_count

        with open(path, "rb") as f:
            head = f.read(4096)  # a ttcf header is tiny; this is enough
        return face_count(head)
    except Exception:
        return 1


def list_system_fonts() -> list[dict]:
    """Enumerate system font files → [{path, name, file, face_count}]."""
    out: list[dict] = []
    seen: set[str] = set()
    for d in FONT_DIRS:
        if not os.path.isdir(d):
            continue
        paths: list[str] = []
        for ext in FONT_EXTS:
            paths += glob.glob(os.path.join(d, ext))
        for p in sorted(paths):
            key = os.path.basename(p).lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "path": p,
                    "name": _font_family(p),
                    "file": os.path.basename(p),
                    "face_count": _face_count(p),
                }
            )
    return out


def _load_face(data: bytes, font_index: int = 0):
    import uharfbuzz as hb

    face = hb.Face(data, font_index)
    if face.glyph_count == 0:
        raise ValueError("No glyphs in font")
    return face


def _snapshot(buf) -> list[dict]:
    """Capture the buffer's glyph run at the current moment of shaping."""
    infos = buf.glyph_infos or []
    poss = buf.glyph_positions or []
    out: list[dict] = []
    for i, gi in enumerate(infos):
        gp = poss[i] if i < len(poss) else None
        out.append(
            {
                "g": gi.codepoint,
                "cl": gi.cluster,
                "dx": gp.x_offset if gp else 0,
                "dy": gp.y_offset if gp else 0,
                "ax": gp.x_advance if gp else 0,
                "ay": gp.y_advance if gp else 0,
                "flags": int(gi.flags),
            }
        )
    return out


def _parse_features(features) -> dict | None:
    """Accept a dict {tag: bool} or a HarfBuzz feature string
    (e.g. "+liga,-kern,frac=2").  Returns {tag: 0/1/..} or None (defaults)."""
    if isinstance(features, str):
        features = features.strip()
        if not features:
            return None
        out = {}
        for item in features.split(","):
            item = item.strip()
            if not item:
                continue
            m = re.match(r"^([+-]?)([A-Za-z0-9]{1,4})(?:=(\d+))?$", item)
            if not m:
                continue
            sign, tag, val = m.groups()
            out[tag] = int(val) if val is not None else (1 if sign == "+" else 0)
        return out or None
    if not features:
        return None
    out = {}
    for tag, val in features.items():
        if isinstance(val, bool):
            out[str(tag)] = 1 if val else 0
        elif val in (1, 0):
            out[str(tag)] = val
    return out or None


def _remap_clusters(stages: list[dict], clustermap: list[int] | None = None) -> list[int]:
    """Sequential cluster ids (Crowbar remapClusters) — preserve original in
    ``offset``, remap ``cl`` to a 0-based index for colouring.  Pass a shared
    ``clustermap`` so rows + final buffer agree on indices."""
    if clustermap is None:
        clustermap = []
    for st in stages:
        for g in st.get("glyphs", []):
            if "offset" not in g:
                g["offset"] = g["cl"]
            if g["offset"] not in clustermap:
                clustermap.append(g["offset"])
            g["cl"] = clustermap.index(g["offset"])
    return clustermap


def _build_trace_stages(rows: list[dict], show_all_lookups: bool = False) -> tuple[list[dict], list[dict]]:
    """Crowbar-style assembly of raw (message, buffer snapshot) rows into trace stages.

    Shared by the HarfBuzz (uharfbuzz) and HarfRust-trace (pyharfrust2) engines so
    the frontend renders both identically:

    1. compute per-lookup ``depth`` and ``effective`` (buffer changed inside a lookup);
    2. apply the default filtering (skip glyph-op noise, blank ``start table`` rows);
    3. remap clusters to a 0-based index for colouring.

    Returns ``(stages, final_glyphs)``.
    """
    import json as _json

    # ── Depths + effective (buffer changed inside a lookup) — Crowbar logic ──
    depth = 0
    start_ids: list[int] = []
    start_bufs: list[str] = []
    for ix, r in enumerate(rows):
        m = r["m"]
        if m.startswith("start lookup") or m.startswith("recursing to lookup"):
            depth += 1
            start_ids.append(ix)
            start_bufs.append(_json.dumps(r["glyphs"]))
        r["depth"] = depth
        if m.startswith("end lookup") or m.startswith("recursed to lookup"):
            depth -= 1
            if start_ids:
                sid = start_ids.pop()
                if start_bufs.pop() != _json.dumps(r["glyphs"]):
                    for i in range(sid, ix + 1):
                        rows[i]["effective"] = True

    # ── Filter (unless show_all_lookups) — Crowbar logic ──
    filtered: list[dict] = []
    last_buf = ""
    for r in rows:
        m = r["m"]
        if "start table" in m:
            r["glyphs"] = []
            filtered.append(r)
            continue
        if not show_all_lookups and any(w in m for w in ("attaching", "replacing", "multiplying", "kerning")):
            continue
        if show_all_lookups or _json.dumps(r["glyphs"]) != last_buf or r["effective"]:
            last_buf = _json.dumps(r["glyphs"])
            filtered.append(r)

    # Flag pre-cmap rows (still codepoints, not glyph ids) — Crowbar's
    # `glyphs: false`.  Shapers with their own pre-cmap stage names mark their
    # rows before calling this (the flag survives the filtering above).
    for r in filtered:
        if r["m"] in UNICODE_ROWS:
            r["cps"] = True

    _remap_clusters(filtered)
    final = filtered[-1]["glyphs"] if filtered else (rows[-1]["glyphs"] if rows else [])
    return filtered, final


def shape_trace(
    data: bytes,
    text: str,
    *,
    direction: str = "auto",
    script: str = "auto",
    language: str = "",
    cluster_level: str = "monotone_graphemes",
    flags: list[str] | None = None,
    features=None,
    variations: dict | None = None,
    show_all_lookups: bool = False,
    glyph_mode: bool = False,
    font_index: int = 0,
) -> dict:
    """Shape text with a font and return the full shaping trace.

    Replicates Crowbar's ``shapeWithTrace``: HarfBuzz's buffer message callback
    is invoked at every shaping step (start/end of tables and lookups, glyph
    operations), and we snapshot the buffer at each message → one row per step.
    """
    import uharfbuzz as hb

    face = _load_face(data, font_index)
    font = hb.Font(face)
    buf = hb.Buffer()

    if glyph_mode:
        buf.add_codepoints([int(t, 0) for t in text.split()])
    else:
        buf.add_str(text)

    # Guess direction/script/language from the text, then override explicitly
    # (Crowbar: guessSegmentProperties() first, then the drawer overrides).
    buf.guess_segment_properties()
    if direction and direction != "auto":
        buf.direction = direction
    if script and script != "auto":
        buf.script = script
    if language:
        try:
            buf.language = language
        except Exception:
            pass
    level = CLUSTER_LEVELS.get(cluster_level, "MONOTONE_GRAPHEMES")
    buf.cluster_level = getattr(hb.BufferClusterLevel, level)

    flags_val = 0
    for f in flags or []:
        member = getattr(hb.BufferFlags, f, None)
        if member is not None:
            flags_val |= int(member)
    buf.flags = flags_val

    if variations:
        try:
            font.set_variations(variations)
        except Exception:
            pass

    preshape = _snapshot(buf)

    stages: list[tuple[str, list[dict]]] = []
    buf.set_message_func(lambda blob: (stages.append((blob, _snapshot(buf))), True)[1])
    try:
        hb.shape(font, buf, features=_parse_features(features))
    finally:
        buf.set_message_func(None)

    # ── Assemble rows (message + buffer snapshot) ──
    rows: list[dict] = [{"m": "Start of shaping", "glyphs": preshape, "depth": 0, "effective": True}]
    for msg, snap in stages:
        rows.append({"m": msg, "glyphs": snap, "depth": 0, "effective": False})
    rows.append({"m": "End of shaping", "glyphs": _snapshot(buf), "depth": 0, "effective": True})

    filtered, final = _build_trace_stages(rows, show_all_lookups)

    used = used_glyph_ids(filtered, final)

    return {
        "upem": face.upem,
        "glyph_count": face.glyph_count,
        "stages": filtered,
        "final": final,
        "messages": [s[0] for s in stages],
        "glyph_names": _glyph_names(data, used),
    }


def used_glyph_ids(stages: list[dict], final: list[dict] | None = None) -> set[int]:
    """Glyph ids the UI needs names for.

    Pre-cmap rows (``cps`` — Crowbar's ``glyphs: false``) hold *codepoints*, not
    glyph ids, so they are skipped: looking a codepoint up in the glyph order
    would only produce a bogus name, while the dialog labels those rows
    ``U+XXXX`` itself.
    """
    used: set[int] = set()
    for st in stages:
        if st.get("cps"):
            continue
        for g in st.get("glyphs", []):
            used.add(g["g"])
    for g in final or []:
        used.add(g["g"])
    return used


def shape_flat(
    data: bytes,
    text: str,
    *,
    shapers: list[str] | None = None,
    direction: str = "auto",
    script: str = "auto",
    language: str = "",
    cluster_level: str = "monotone_graphemes",
    flags: list[str] | None = None,
    features=None,
    font_index: int = 0,
) -> dict:
    """Shape text with HarfBuzz using an explicit shaper list, returning only
    the final buffer (single stage — no trace).

    Used by the ``fallback`` (cmap-only, no GSUB/GPOS) engine for comparison.
    """
    import uharfbuzz as hb

    face = _load_face(data, font_index)
    font = hb.Font(face)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    if direction and direction != "auto":
        buf.direction = direction
    if script and script != "auto":
        buf.script = script
    if language:
        try:
            buf.language = language
        except Exception:
            pass
    level = CLUSTER_LEVELS.get(cluster_level, "MONOTONE_GRAPHEMES")
    buf.cluster_level = getattr(hb.BufferClusterLevel, level)

    flags_val = 0
    for f in flags or []:
        member = getattr(hb.BufferFlags, f, None)
        if member is not None:
            flags_val |= int(member)
    buf.flags = flags_val

    hb.shape(font, buf, features=_parse_features(features), shapers=shapers or ["ot"])

    glyphs = _snapshot(buf)
    stage = {
        "m": f"HarfBuzz {shapers[0] if shapers else 'ot'} shaping",
        "glyphs": glyphs,
        "depth": 0,
        "effective": True,
    }
    _remap_clusters([stage])
    used = used_glyph_ids([stage])
    return {
        "upem": face.upem,
        "glyph_count": face.glyph_count,
        "stages": [stage],
        "final": stage["glyphs"],
        "messages": [],
        "glyph_names": _glyph_names(data, used),
        "engine": shapers[0] if shapers else "ot",
    }


def _glyph_names(data: bytes, gids: set[int]) -> dict[int, str]:
    """Map glyph ids → display names (post names, or gid# for synthetic)."""
    try:
        from fontTools.ttLib import TTFont

        tt = TTFont(io.BytesIO(data), lazy=True)
        order = tt.getGlyphOrder()
        out: dict[int, str] = {}
        for gid in gids:
            if 0 <= gid < len(order):
                n = order[gid]
                if not n or n.startswith(("glyph", "gid")):
                    n = f"gid{gid}"
                out[gid] = n
        return out
    except Exception:
        return {}


def _parse_debg(data: bytes) -> dict | None:
    """Best-effort parse of fontmake's ``Debg`` table (lookup debug info)."""
    try:
        from fontTools.ttLib import TTFont

        import json
        import struct

        tt = TTFont(io.BytesIO(data), lazy=True)
        if "Debg" not in tt.reader.tables:
            return None
        raw = tt.reader["Debg"]
        try:
            n = struct.unpack(">L", raw[:4])[0]
            blob = raw[4 : 4 + n]
        except Exception:
            blob = raw[4:]
        return json.loads(blob.decode("utf-8", "replace"))
    except Exception:
        return None


def font_info(data: bytes) -> dict:
    """Font metadata for the Crowbar drawer: variation axes, supported
    scripts/languages (from GSUB/GPOS), HarfBuzz version and Debg table."""
    import uharfbuzz as hb

    info: dict = {
        "hb_version": hb.version_string(),
        "axes": [],
        "supported_scripts": [],
        "supported_languages": [],
        "debg": None,
    }
    try:
        face = _load_face(data)
        axes = []
        for a in face.axis_infos:
            axes.append({"tag": a.tag, "min": a.min_value, "default": a.default_value, "max": a.max_value})
        info["axes"] = axes
    except Exception:
        pass
    try:
        from fontTools.ttLib import TTFont

        tt = TTFont(io.BytesIO(data), lazy=True)
        scripts: set[str] = set()
        langs: set[str] = set()
        for table in ("GSUB", "GPOS"):
            try:
                sl = tt[table].table.ScriptList
                for rec in sl.ScriptRecord:
                    scripts.add(rec.ScriptTag.lower())
                    ss = rec.Script
                    if ss and getattr(ss, "LangSysRecord", None):
                        for lr in ss.LangSysRecord:
                            langs.add(lr.LangSysTag)
            except Exception:
                pass
        info["supported_scripts"] = sorted(scripts)
        info["supported_languages"] = sorted(langs)
    except Exception:
        pass
    info["debg"] = _parse_debg(data)
    return info


def scripts_list() -> list[dict]:
    """Full ISO 15924 script list from data/scripts/iso15924.tsv."""
    from babelsoft.utils_.dirs import Dirs
    from babelsoft.utils_.parser import TsvParser

    out: list[dict] = []
    for row in TsvParser.get_tsv(Dirs.DATA / "scripts" / "iso15924.tsv"):
        if len(row) >= 3 and row[0].strip() and row[2].strip():
            out.append({"tag": row[0].strip().lower(), "label": row[2].strip()})
    return out


# Common OpenType language tags (label, tag) — Crowbar's opentypeLanguages
# would be far too large to inline; this covers the common ones.
LANGUAGES: list[dict] = [
    {"tag": "ARA", "label": "Arabic"},
    {"tag": "ASM", "label": "Assamese"},
    {"tag": "AZE", "label": "Azerbaijani"},
    {"tag": "BEL", "label": "Belarusian"},
    {"tag": "BEN", "label": "Bengali"},
    {"tag": "BGR", "label": "Bulgarian"},
    {"tag": "CAT", "label": "Catalan"},
    {"tag": "CHN", "label": "Chinese (Simplified)"},
    {"tag": "ZHS", "label": "Chinese (Simplified)"},
    {"tag": "ZHT", "label": "Chinese (Traditional)"},
    {"tag": "CSY", "label": "Czech"},
    {"tag": "DAN", "label": "Danish"},
    {"tag": "DEU", "label": "German"},
    {"tag": "ELL", "label": "Greek"},
    {"tag": "ENG", "label": "English"},
    {"tag": "ESP", "label": "Spanish"},
    {"tag": "FAR", "label": "Persian"},
    {"tag": "FIN", "label": "Finnish"},
    {"tag": "FRA", "label": "French"},
    {"tag": "GUR", "label": "Gurmukhi"},
    {"tag": "GUJ", "label": "Gujarati"},
    {"tag": "HEB", "label": "Hebrew"},
    {"tag": "HIN", "label": "Hindi"},
    {"tag": "HUN", "label": "Hungarian"},
    {"tag": "IND", "label": "Indonesian"},
    {"tag": "ITA", "label": "Italian"},
    {"tag": "JPN", "label": "Japanese"},
    {"tag": "KAN", "label": "Kannada"},
    {"tag": "KAT", "label": "Georgian"},
    {"tag": "KHM", "label": "Khmer"},
    {"tag": "KOR", "label": "Korean"},
    {"tag": "LAT", "label": "Latin"},
    {"tag": "LTH", "label": "Lithuanian"},
    {"tag": "MAR", "label": "Marathi"},
    {"tag": "MLT", "label": "Maltese"},
    {"tag": "MNG", "label": "Mongolian"},
    {"tag": "NEP", "label": "Nepali"},
    {"tag": "NLD", "label": "Dutch"},
    {"tag": "NOR", "label": "Norwegian"},
    {"tag": "ORI", "label": "Oriya"},
    {"tag": "PAN", "label": "Punjabi"},
    {"tag": "PLK", "label": "Polish"},
    {"tag": "PTG", "label": "Portuguese"},
    {"tag": "ROM", "label": "Romanian"},
    {"tag": "RUS", "label": "Russian"},
    {"tag": "SAN", "label": "Sanskrit"},
    {"tag": "SIN", "label": "Sinhala"},
    {"tag": "SKY", "label": "Slovak"},
    {"tag": "SLV", "label": "Slovenian"},
    {"tag": "SQI", "label": "Albanian"},
    {"tag": "SRB", "label": "Serbian"},
    {"tag": "SWA", "label": "Swahili"},
    {"tag": "SVE", "label": "Swedish"},
    {"tag": "TAM", "label": "Tamil"},
    {"tag": "TEL", "label": "Telugu"},
    {"tag": "THA", "label": "Thai"},
    {"tag": "TRK", "label": "Turkish"},
    {"tag": "UKR", "label": "Ukrainian"},
    {"tag": "URD", "label": "Urdu"},
    {"tag": "VIT", "label": "Vietnamese"},
]


def languages_list() -> list[dict]:
    return LANGUAGES


def feature_tags(data: bytes) -> dict:
    """GSUB/GPOS feature tags from a font (for the feature toggle list)."""
    from fontTools.ttLib import TTFont

    tt = TTFont(io.BytesIO(data), lazy=True)
    out: dict = {"gsub": [], "gpos": []}
    for table in ("GSUB", "GPOS"):
        try:
            recs = tt[table].table.FeatureList.FeatureRecord
            out[table.lower()] = sorted({r.FeatureTag for r in recs})
        except Exception:
            out[table.lower()] = []
    return out


def _glyph_advance(tt, gname: str, upem: int) -> int:
    """Font's own horizontal advance for a glyph (font units).

    Used as a fallback in render_svg: GSUB intermediate stages have no
    HarfBuzz positions (ax == 0), so we lay the glyphs out with their real
    advance widths to keep the preview visible (matching Crowbar's intent).

    Zero-width glyphs (Mongolian FVS variation selectors, combining marks)
    get a nominal advance so every glyph keeps a visible slot in the trace.
    """
    try:
        adv = tt["hmtx"].metrics[gname][0]
        if adv:
            return adv
    except Exception:
        pass
    return max(1, upem // 10)


def render_svg(
    data: bytes,
    glyphs: list[dict],
    upem: int,
    size: int = 128,
    color: str = "#1f2937",
    highlight_cl: int = -1,
    highlight_color: str = "#e23d3d",
    variations: dict | None = None,
) -> str:
    """Compose a shaped glyph run into an SVG string (glyph outlines via fontTools).

    Glyphs whose ``cl`` equals ``highlight_cl`` are drawn highlighted (fill +
    outline in ``highlight_color``, which the caller normally derives from the
    cluster palette so it matches the trace-table chip borders).

    Advances: use the HarfBuzz ``ax`` when present; for intermediate shaping
    stages (GSUB, no positions) fall back to the font's own advance so the
    glyphs remain visible instead of piling up at x=0.
    """
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.ttLib import TTFont

    tt = TTFont(io.BytesIO(data), lazy=True)
    if variations:
        try:
            tt.set_variations(variations)
        except Exception:
            pass
    gs = tt.getGlyphSet()
    order = tt.getGlyphOrder()
    scale = size / upem
    parts: list[str] = []
    x = 0.0
    baseline = size * 0.82
    for g in glyphs:
        gid = g["g"]
        if gid < 0 or gid >= len(order):
            x += g.get("ax", 0) * scale
            continue
        gname = order[gid]
        adv = g.get("ax", 0) or _glyph_advance(tt, gname, upem)
        pen = SVGPathPen(gs)
        try:
            gs[gname].draw(pen)
        except Exception:
            x += adv * scale
            continue
        d = pen.getCommands()
        tx = x + g.get("dx", 0) * scale
        ty = g.get("dy", 0) * scale
        hl = g.get("cl") == highlight_cl
        fill = highlight_color if hl else color
        if not d:
            # Empty glyph (e.g. Mongolian FVS variation selector): draw a
            # placeholder rule so it stays visible in the trace.
            parts.append(
                f'<g transform="translate({tx:.2f} {baseline + ty:.2f})" '
                f'stroke="{highlight_color if hl else color}" '
                f'stroke-width="{max(1, upem / 200):.2f}" '
                f'fill="none" opacity="{0.9 if hl else 0.55}"><path d="M0 {upem * 0.75} '
                f'H {max(adv, 1)}"/></g>'
            )
            x += adv * scale
            continue
        box = (
            f'<rect x="-40" y="-1450" width="{max(adv, 1) + 80}" height="1600" '
            f'fill="none" stroke="{highlight_color}" stroke-width="30"/>'
            if hl
            else ""
        )
        parts.append(
            f'<g transform="translate({tx:.2f} {baseline + ty:.2f}) '
            f'scale({scale:.6f} {-scale:.6f})" fill="{fill}"><path d="{d}"/>{box}</g>'
        )
        x += adv * scale
    width = max(1.0, x)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.2f}" height="{size:.2f}" '
        f'viewBox="0 0 {width:.2f} {size:.2f}">{"".join(parts)}</svg>'
    )


def font_bytes(path: str) -> bytes:
    """Read a font file's bytes (for shaping)."""
    with open(path, "rb") as f:
        return f.read()


def font_bytes_from_b64(b64: str) -> bytes:
    return base64.b64decode(b64)
