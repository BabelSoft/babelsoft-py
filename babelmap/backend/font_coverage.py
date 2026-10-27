"""Composite-font coverage analysis — the modern port of BabelMap's
``CDialogConfig`` (``Dialogs/DialogConfig.cpp``).

The original dialog presents a **per-block** view: one row per Unicode block,
showing how many characters the block holds, which font is currently mapped to
it, and how many real characters that font actually covers.  On top of that a
single **Auto** button walks every block, scores every font, and assigns the
best one — the "which font is best for this block" logic the UI inherits.

This module ports those two pieces:

* :func:`block_coverage` — per-block rows + the "fonts covering this block"
  list (``OnInitDialog`` fills the block list, ``OnNewBlock`` fills the per-block
  font list);
* :func:`auto_assign` — the font-scoring walk from ``OnConfigButtonAuto``.

Scoring (inherited verbatim from ``OnConfigButtonAuto``)
--------------------------------------------------------
For each block, every candidate font is scored on, in priority order:

1. **characters covered in this block** (``GetCharactersInBlock``) — but *capped
   to the block's real character count*, because a font that maps more than the
   block holds is usually unreliable (``bCapToBlockTotal = true``);
2. **weight** — the closest to Regular wins (``IsMostRegularFont``);
3. **distinct blocks covered** (``GetUnicodeBlocks``);
4. **total characters covered** (``GetUnicodeCharacters``).

A **preferred font** (``Unicode::PreferredFontPerBlock`` — the Windows font that
ships with the OS for that script) overrides the winner when it covers at least
as many characters in the block.

Fonts that are not a primary style, are rotated, or were flagged as unreliable
are skipped (``IsPrimaryStyle`` / ``IsRotatedFont`` / ``IsIgnoreFont``); PUA
blocks are reported with coverage 0 because "coverage" is meaningless there.
"""

from __future__ import annotations

import base64
import bisect
import logging
from functools import lru_cache

from babelmap.backend.errors import PROBE_ERRORS

logger = logging.getLogger(__name__)

# Blocks whose coverage is not meaningful (user-defined / private).
_PUA_BLOCKS = {
    "Private Use Area",
    "Supplementary Private Use Area-A",
    "Supplementary Private Use Area-B",
}

# How many characters a font may be short of a block's total and still have its
# script affinity count (see ``_pick_best``).  Small blocks are the common case
# for "belongs to the script but missing a few"; larger blocks allow a
# proportional gap so the rule behaves the same at every size.
_AFFINITY_SLACK = 16

# The Windows font the original picks for each block (Unicode::PreferredFontPerBlock,
# Unicode/Blocks.h).  Keyed by block name; "" means the original had no entry.
# Only the entries the original actually populated are listed — the modern port
# adds no new preferences, so "Auto" behaves the same way it always did.
PREFERRED_FONT_PER_BLOCK: dict[str, str] = {
    # Plane 0 — BMP
    "Basic Latin": "Cambria",
    "Latin-1 Supplement": "Cambria",
    "Latin Extended-A": "Cambria",
    "Latin Extended-B": "Cambria",
    "IPA Extensions": "Cambria",
    "Spacing Modifier Letters": "Cambria",
    "Combining Diacritical Marks": "Cambria",
    "Greek and Coptic": "Cambria",
    "Cyrillic": "Times New Roman",
    "Cyrillic Supplement": "Times New Roman",
    "Armenian": "Sylfaen",
    "Hebrew": "Times New Roman",
    "Arabic": "Microsoft Uighur",
    "Syriac": "Estrangelo Edessa",
    "Arabic Supplement": "Microsoft Uighur",
    "Thaana": "MV Boli",
    "NKo": "Ebrima",
    "Devanagari": "Mangal",
    "Bengali": "Vrinda",
    "Gurmukhi": "Raavi",
    "Gujarati": "Shruti",
    "Oriya": "Kalinga",
    "Tamil": "Vijaya",
    "Telugu": "Vani",
    "Kannada": "Tunga",
    "Malayalam": "Kartika",
    "Sinhala": "Iskoola Pota",
    "Thai": "Angsana New",
    "Lao": "Lao UI",
    "Tibetan": "Microsoft Himalaya",
    "Myanmar": "Myanmar Text",
    "Georgian": "Sylfaen",
}


# ── Unicode block / repertoire data ──────────────────────────────────


# Graphic + format only: Control (Cc), Surrogate (Cs), Private-use (Co) and
# Unassigned (Cn) are excluded; Format (Cf) *is* counted, as in the original
# ``Unicode::GetGraphicAndFormatCharactersPerBlock``.
_EXCLUDED_GC = {"Cc", "Cs", "Co", "Cn"}


def _gc_code(cp: int) -> str:
    """Two-letter general-category code for one code point.

    ``Unicode.get_general_category`` returns a ``GeneralCategory`` **enum**, not
    a string — comparing it against ``{"Cc", …}`` never matches, which would
    silently count every control character.  Its ``.name`` is the short code.
    """
    from babelsoft.unicode.core import Unicode

    gc = Unicode.get_general_category(cp)
    return getattr(gc, "name", None) or str(gc).split(".")[-1]


# Results of :func:`block_chars`, keyed by block name.  Computing one block is
# cheap per character but not per request: the dialog re-requests a block every
# time the user returns to it, and CJK Unified Ideographs is 20 992 chars × ~84
# candidate faces.  The scan itself is cached upstream (``font_overview``), so
# the only invalidation needed is a re-scan — one loader per process is enough
# for a single-user desktop app.
_CHARS_CACHE: dict[str, dict] = {}
_CHARS_CACHE_MAX = 24


@lru_cache(maxsize=1)
def _blocks() -> tuple[list[dict], list[int]]:
    """All Unicode blocks as sorted rows, plus the assigned-codepoint index.

    ``count`` is the number of *graphic + format* characters the block really
    holds — the same restriction the original applies (``Unicode::
    GetGraphicAndFormatCharactersPerBlock``).  Counting the control characters
    would make every block unreachable (no font maps U+0000–U+001F), so a block
    like Basic Latin would report 128 characters that no font can ever cover.
    """
    from babelsoft.unicode.core import Unicode

    table, names = Unicode._block_data()
    assigned = Unicode._assigned_codepoints()

    rows: list[dict] = []
    for start, end, idx in table:
        lo = bisect.bisect_left(assigned, start)
        hi = bisect.bisect_right(assigned, end)
        count = 0
        for cp in assigned[lo:hi]:
            if _gc_code(cp) not in _EXCLUDED_GC:
                count += 1
        rows.append(
            {
                "name": names[idx],
                "start": start,
                "end": end,
                "plane": start >> 16,
                "count": count,
            }
        )
    return rows, assigned


def blocks() -> list[dict]:
    """Every Unicode block with its real (graphic + format) character count."""
    return _blocks()[0]


# ── per-block coverage ───────────────────────────────────────────────


def _covered_in_block(cps: list[int], block: dict) -> int:
    """Characters from ``cps`` (sorted) that fall inside ``block``, capped.

    ``cps`` is the cmap — which also maps control, surrogate, private-use and
    unassigned code points.  ``block["count"]`` deliberately excludes those (see
    :func:`_blocks`), so counting them here would let a face claim more
    characters in a block than the block actually holds.  The cap hides that in
    the *count*, but not in the ordering of the candidate list, so filter here.
    """
    lo = bisect.bisect_left(cps, block["start"])
    hi = bisect.bisect_right(cps, block["end"])
    n = sum(1 for cp in cps[lo:hi] if _gc_code(cp) not in _EXCLUDED_GC)
    return min(n, block["count"]) if block["count"] else n


def block_chars(block_name: str, scan: dict | None = None, *, all_styles: bool = False) -> dict | None:
    """Every character of one block, annotated with per-font support.

    This feeds the dialog's preview grid: the grid shows **all** of the block's
    characters (not a sample), and when the user picks a font the cells that
    font does *not* map are greyed out — so a font's real coverage of the block
    can be judged at a glance.

    Returns ``{name, start, end, plane, total, cps, fonts, masks}``:

    * ``cps`` — the block's code points, ascending;
    * ``fonts`` — ``[faceIndex, …]``, the candidate faces that cover *something*
      in this block, in the same order as ``masks`` rows;
    * ``masks`` — one **base64 bitset** per entry of ``fonts``, bit ``i`` set
      when that face maps ``cps[i]``.

    The obvious shape — a ``supported_by`` index list per character — is what
    this endpoint used to return, and it does not scale: CJK Unified Ideographs
    has 20 992 characters with ~84 covering faces each (**1.77 M** integers,
    ~7 MB of JSON, ~4 s to serialise).  The bitset form is ~400 KB and encodes
    the same information, since membership is a yes/no per (font, character)
    pair.

    ``None`` when the block name is unknown.
    """
    rows, assigned = _blocks()
    block = next((b for b in rows if b["name"] == block_name), None)
    if block is None:
        return None

    cached = _CHARS_CACHE.get(block_name)
    if cached is not None:
        return cached

    # The block's real characters: graphic + format only, same rule as the count.
    lo = bisect.bisect_left(assigned, block["start"])
    hi = bisect.bisect_right(assigned, block["end"])
    cps = [cp for cp in assigned[lo:hi] if _gc_code(cp) not in _EXCLUDED_GC]

    faces = _load_faces(scan, all_styles)
    indexes: list[int] = []
    masks: list[str] = []
    for f in faces:
        # Per-face membership set, then one bit per character of the block.
        owned = set(f["_all_cps"])
        bits = bytearray((len(cps) + 7) // 8)
        hits = 0
        for i, cp in enumerate(cps):
            if cp in owned:
                bits[i >> 3] |= 1 << (i & 7)
                hits += 1
        if hits:  # faces covering nothing in this block are not worth sending
            indexes.append(f["index"])
            masks.append(base64.b64encode(bytes(bits)).decode("ascii"))

    result = {
        "name": block["name"],
        "start": block["start"],
        "end": block["end"],
        "plane": block["plane"],
        "total": block["count"],
        "cps": cps,
        "fonts": indexes,
        "masks": masks,
    }
    if len(_CHARS_CACHE) >= _CHARS_CACHE_MAX:
        _CHARS_CACHE.clear()
    _CHARS_CACHE[block_name] = result
    return result


def block_coverage(
    scan: dict | None = None,
    *,
    block_name: str | None = None,
    all_styles: bool = False,
) -> dict:
    """Per-block font-coverage report — the modern port of the dialog's block list.

    Body:

    * ``blocks`` — one row per Unicode block: ``{name, start, end, plane, total,
      best_font, best_covered, best_ratio, fonts, covered_blocks}`` where
      ``fonts`` is the "fonts covering this block" list from ``OnNewBlock``
      (sorted by covered desc) and ``best_font`` is the Auto winner;
    * ``summary`` — ``{total_blocks, covered_blocks, total_chars,
      covered_chars, ratio}`` — the two status lines ``UpdateCoverage()`` fills;
    * ``imported`` — how many faces were analysed.

    ``scan`` is a ready-made ``{"fonts": [...]}`` payload (from
    ``font_overview.scan_fonts``); when omitted the directories are scanned.
    Passing ``block_name`` returns just that one row (much cheaper to render).
    """
    faces = _load_faces(scan, all_styles)
    rows, _ = _blocks()
    wanted = [b for b in rows if block_name is None or b["name"] == block_name]

    out_rows = []
    covered_blocks = 0
    covered_chars = 0
    total_chars = 0
    for b in wanted:
        if b["count"] == 0:
            continue
        total_chars += b["count"]
        fonts = []
        for f in faces:
            n = _covered_in_block(f["_all_cps"], b)
            if n > 0:
                fonts.append(
                    {
                        "index": f["index"],
                        "family": f["family"],
                        "subfamily": f["subfamily"],
                        "weight": f["weight"],
                        "covered": n,
                        "total": b["count"],
                        "ratio": round(n / b["count"], 4) if b["count"] else 0.0,
                        "preferred": f["family"] == PREFERRED_FONT_PER_BLOCK.get(b["name"], ""),
                    }
                )
        fonts.sort(key=lambda e: (-e["covered"], e["family"].lower()))
        best = _pick_best(b, fonts, faces)
        covered = best["covered"] if best else 0
        is_pua = b["name"] in _PUA_BLOCKS
        eff = 0 if is_pua else covered
        if not is_pua:
            covered_chars += eff
            if eff >= b["count"]:
                covered_blocks += 1
        out_rows.append(
            {
                "name": b["name"],
                "start": b["start"],
                "end": b["end"],
                "plane": b["plane"],
                "total": b["count"],
                "covered": eff,
                "ratio": round(eff / b["count"], 4) if b["count"] else 0.0,
                "best_font": best["family"] if best else "",
                "best_subfamily": best["subfamily"] if best else "",
                "best_index": best["index"] if best else -1,
                "best_weight": best["weight"] if best else 0,
                "preferred_font": PREFERRED_FONT_PER_BLOCK.get(b["name"], ""),
                "pua": is_pua,
                # The COMPLETE list of fonts covering this block — the dialog
                # shows all of them, in coverage order, so nothing is hidden.
                "fonts": fonts,
                "font_count": len(fonts),
                # A short preview string of this block's own characters — the
                # dialog renders it in the winning font so the block's look can
                # be judged without leaving the table.
                "preview": _preview_for(b, best, faces),
            }
        )

    return {
        "blocks": out_rows,
        "summary": {
            "total_blocks": len([b for b in rows if b["count"] > 0]),
            "covered_blocks": covered_blocks,
            "total_chars": total_chars,
            "covered_chars": covered_chars,
            "ratio": round(covered_chars / total_chars, 6) if total_chars else 0.0,
        },
        "imported": len(faces),
    }


def _preview_for(block: dict, best: dict | None, faces: list[dict]) -> str:
    """A short sample string of this block's own characters.

    Prefers characters the winning font actually covers, so the preview never
    renders as tofu in the very font the row recommends.  Control characters and
    unassigned gaps are skipped; long blocks are thinned out so the sample still
    spans the block's range instead of showing only its first few characters.

    ``best`` is a row from the per-block ``fonts`` list (it carries an ``index``,
    not the code points), so the face is looked up in ``faces`` for the cmap.
    """
    from babelsoft.unicode.core import Unicode

    cps: list[int] = []
    if best is not None:
        face = next((f for f in faces if f["index"] == best.get("index")), None)
        if face is not None:
            cps = face["_all_cps"]
    if not cps:
        return ""
    lo = bisect.bisect_left(cps, block["start"])
    hi = bisect.bisect_right(cps, block["end"])
    inside = cps[lo:hi]
    if not inside:
        return ""
    limit = 24
    if len(inside) > limit:
        # Even stride across the block so the sample is representative.
        stride = len(inside) / limit
        inside = [inside[int(i * stride)] for i in range(limit)]
    out = []
    for cp in inside:
        if 0xD800 <= cp <= 0xDFFF:
            continue
        try:
            if Unicode.get_general_category(cp).name in ("Cc", "Cs", "Cn"):
                continue
            out.append(chr(cp))
        except PROBE_ERRORS:
            logger.debug("_preview_for: skipping unreadable entry", exc_info=True)
            continue
    return "".join(out)


def _load_faces(scan: dict | None, all_styles: bool = False) -> list[dict]:
    """Normalise a font scan into the flat face list the analysis needs.

    Only faces the original would consider are kept: primary style (the regular
    face of a family, not the bold/italic companions) and not rotated.  Each
    face carries ``_all_cps`` — every code point its cmap maps — which is what
    makes per-block counting cheap.

    ``all_styles`` is the Fonts ▸ List All Styles of Fonts toggle: when set,
    every face of a family participates instead of only its primary style, so
    "Arial Bold" can win a block on its own.
    """
    if scan is None:
        from babelmap.backend.font_overview import scan_fonts

        scan = {"fonts": scan_fonts()}
    src = scan.get("fonts") if isinstance(scan, dict) else scan
    out: list[dict] = []
    for i, f in enumerate(src or []):
        if not _is_candidate(f, all_styles):
            continue
        cps = f.get("_all_cps")
        if cps is None:
            # ``_all_cps`` is dropped from the cached scan (too large), so
            # rebuild it from a range list.  ``_all_ranges`` is the faithful,
            # unfiltered one; ``_cps_ranges`` is restricted to the script
            # repertoires and would silently drop every block whose characters
            # lie outside them (e.g. Combining Diacritical Marks, U+0300-036F),
            # reporting "0 fonts cover this block".  Only fall back to it for
            # scans produced before ``_all_ranges`` existed.
            cps = _cps_from_ranges(f.get("_all_ranges") or f.get("_cps_ranges") or [])
        out.append(
            {
                "index": i,
                "family": f.get("family") or f.get("file") or "",
                "subfamily": f.get("subfamily") or "Regular",
                "weight": int(f.get("weight") or 400),
                "path": f.get("path"),
                "file": f.get("file"),
                "face_index": f.get("face_index", 0),
                # The font's own primary writing system — the "does this font
                # actually belong to this block's script" signal.
                "main_script": f.get("main_script") or "",
                "_all_cps": cps,
            }
        )
    return out if all_styles else _primary_style_only(out)


def _is_candidate(f: dict, all_styles: bool = False) -> bool:
    """Faces the original would consider (``IsPrimaryStyle`` / ``IsRotatedFont``).

    The subfamily test below is only a pre-filter: variants like ``Bold`` /
    ``Italic`` are dropped here, and the remaining faces are then reduced to
    **one per family** by :func:`_primary_style_only` — which is what
    ``IsPrimaryStyle()`` actually means (a per-family, not per-face, decision).

    With ``all_styles`` set both of those steps are skipped, leaving one entry
    per physical face.
    """
    if not all_styles:
        sub = (f.get("subfamily") or "Regular").lower()
        if any(k in sub for k in ("bold", "italic", "oblique", "light", "thin", "black", "semibold")):
            return False
        if f.get("italic"):
            return False
    # Rotated fonts (the original's IsRotatedFont) are vertical-only designs.
    return not f.get("rotated")


def _primary_style_only(faces: list[dict]) -> list[dict]:
    """Keep one face per family — the one closest to Regular.

    Implements ``CFontData::IsPrimaryStyle``: within a family only the primary
    (regular) face participates, otherwise "Bold"/"Light" companions would win
    blocks by covering the same characters.  Ties break on subfamily name so the
    choice is stable.
    """
    best: dict[str, dict] = {}
    for f in faces:
        key = (f["family"] or "").lower()
        cur = best.get(key)
        if cur is None or _most_regular(cur["weight"], f["weight"]):
            best[key] = f
    return list(best.values())


def _cps_from_ranges(ranges: list) -> list[int]:
    out: list[int] = []
    for r in ranges:
        if isinstance(r, (list, tuple)) and len(r) == 2:
            out.extend(range(r[0], r[1] + 1))
        elif isinstance(r, int):
            out.append(r)
    return out


# ── Auto: pick the best font per block ───────────────────────────────


def _pick_best(block: dict, fonts: list[dict], faces: list[dict]) -> dict | None:
    """The best font for one block — the ``OnConfigButtonAuto`` scoring loop.

    ``fonts`` are the pre-computed per-block rows; ``faces`` carry the global
    counts the tie-breakers need.  Returns the winning font row (with the extra
    ``blocks``/``chars`` fields) or ``None``.

    One criterion is added on top of the original's, because the modern scan
    sees far more fonts than the original's GDI enumeration did: among fonts
    that cover **essentially the whole block**, one whose primary writing system
    is the block's own script wins (a Tai Tham font is not a Latin font, even
    though it maps all of Basic Latin).  The original got this for free from
    ``IsUnicodeBlock`` + GDI's per-script enumeration — this only makes that
    implicit rule explicit.

    Affinity deliberately does **not** outrank coverage in general: a font that
    truly belongs to the script but has real gaps (98/128) must not beat one that
    covers the block completely.  So affinity only applies once a candidate is
    within :data:`_AFFINITY_SLACK` characters of the block total.
    """
    by_index = {f["index"]: f for f in faces}
    preferred_name = PREFERRED_FONT_PER_BLOCK.get(block["name"], "")
    block_script = _block_main_script(block)

    winner: dict | None = None
    w_chars = 0
    w_blocks = 0
    w_total = 0
    w_weight = 0
    w_affinity = 0
    pref: dict | None = None

    for row in fonts:
        f = by_index.get(row["index"])
        if f is None:
            continue
        chars = row["covered"]
        blocks_n = f.get("_blocks", 0)
        total = len(f["_all_cps"])
        weight = f["weight"]
        # Only count affinity for a font that actually covers the block; a font
        # with holes is judged on its coverage instead.
        affinity = (
            1
            if block_script
            and f.get("main_script") == block_script
            and chars >= max(1, block["count"] - _AFFINITY_SLACK)
            else 0
        )

        if row["family"] == preferred_name and (pref is None or chars >= pref["covered"]):
            pref = row

        # 00. a font that belongs to this script beats one that merely covers it
        if affinity > w_affinity:
            win = True
        elif affinity < w_affinity:
            win = False
        # 1. more characters in THIS block wins
        elif chars > w_chars:
            win = True
        elif chars == w_chars:
            # 2. closest to Regular
            if _most_regular(w_weight, weight) or blocks_n > w_blocks:
                win = True
            elif blocks_n == w_blocks:
                # 4. more total characters
                win = total > w_total
            else:
                win = False
        else:
            win = False

        if win:
            winner = row
            w_chars = chars
            w_blocks = blocks_n
            w_total = total
            w_weight = weight
            w_affinity = affinity

    # The preferred (OS-provided) font overrides when it covers at least as much.
    if pref is not None and (winner is None or pref["covered"] >= w_chars):
        winner = pref

    return winner


@lru_cache(maxsize=1)
def _block_script_map() -> dict[str, str]:
    """Block name → the ISO 15924 tag of the script that dominates it.

    Derived from the UCD (each block's characters are looked up in Scripts.txt
    and the majority script wins), so no table is hand-maintained here.
    Common/Inherited are skipped so a shared block (Latin, digits, punctuation)
    does not get a meaningless ``Common`` answer — and so Latin letters inside a
    block still resolve to ``Latn``.
    """
    from babelsoft.unicode.core import Unicode

    # ``get_script`` returns a long name ("Common", "Latin"); the scan reports
    # tags ("Zyyy", "Latn").  Both spellings are normalised away here.
    shared = {"Common", "Inherited", "Unknown", "Zyyy", "Zinh", "Zzzz"}

    rows, assigned = _blocks()
    out: dict[str, str] = {}
    for b in rows:
        lo = bisect.bisect_left(assigned, b["start"])
        hi = bisect.bisect_right(assigned, b["end"])
        counts: dict[str, int] = {}
        for cp in assigned[lo:hi]:
            try:
                sc = Unicode.get_script(cp)
            except PROBE_ERRORS:
                logger.debug("_block_script_map: skipping unreadable entry", exc_info=True)
                continue
            if sc and sc not in shared:
                counts[sc] = counts.get(sc, 0) + 1
        if counts:
            name = max(counts.items(), key=lambda kv: kv[1])[0]
            out[b["name"]] = _script_tag(name)
    return out


@lru_cache(maxsize=1)
def _script_name_to_tag() -> dict[str, str]:
    """``{"Latin": "Latn", …}`` — the long script name → ISO 15924 tag."""
    try:
        from babelmap.backend.font_overview import SCRIPTS
    except PROBE_ERRORS:
        return {}
    # SCRIPTS is keyed by tag; each entry carries a ``label`` (the long name).
    return {v.get("label", ""): k for k, v in SCRIPTS.items() if v.get("label")}


def _script_tag(name: str) -> str:
    """Long script name → tag, falling back to the name itself."""
    if not name:
        return ""
    # Already a tag (3–4 chars, mixed case like "Latn").
    if len(name) in (3, 4) and name[0].isupper() and name[1:].islower():
        return name
    return _script_name_to_tag().get(name, name)


def _block_main_script(block: dict) -> str:
    return _block_script_map().get(block["name"], "")


def _most_regular(w1: int, w2: int) -> bool:
    """``CFontData::IsMostRegularFont`` — is weight ``w2`` closer to Regular?

    The original prefers the *lowest* weight that is still ≥ normal (400); a
    plain 400 beats 700, and 300 beats 700 too (lighter is closer to text).
    """
    if w1 == 0:
        return True
    return abs(w2 - 400) < abs(w1 - 400)


def auto_assign(scan: dict | None = None, *, all_styles: bool = False) -> dict:
    """Assign the best font to every block — the dialog's **Auto** button.

    Returns ``{assignments, summary, imported}`` where each assignment is
    ``{block, start, end, font, index, covered, total, ratio, reason}`` —
    ``reason`` records which criterion decided it, so the UI can explain the
    choice instead of just showing a name.
    """
    faces = _load_faces(scan, all_styles)
    # Pre-compute each face's global counters once (the tie-breakers need them).
    block_rows, _ = _blocks()
    for f in faces:
        cps = f["_all_cps"]
        f["_blocks"] = sum(1 for b in block_rows if b["count"] and _covered_in_block(cps, b) > 0)

    assignments = []
    covered_blocks = 0
    for b in block_rows:
        if b["count"] == 0:
            continue
        fonts = []
        for f in faces:
            n = _covered_in_block(f["_all_cps"], b)
            if n > 0:
                fonts.append(
                    {
                        "index": f["index"],
                        "family": f["family"],
                        "subfamily": f["subfamily"],
                        "weight": f["weight"],
                        "covered": n,
                        "total": b["count"],
                        "ratio": round(n / b["count"], 4),
                        "preferred": False,
                    }
                )
        best = _pick_best(b, fonts, faces)
        is_pua = b["name"] in _PUA_BLOCKS
        if best and not is_pua and best["covered"] >= b["count"]:
            covered_blocks += 1
        reason = _reason_for(b, best, fonts)
        assignments.append(
            {
                "block": b["name"],
                "start": b["start"],
                "end": b["end"],
                "plane": b["plane"],
                "font": best["family"] if best else "",
                "subfamily": best["subfamily"] if best else "",
                "index": best["index"] if best else -1,
                "covered": best["covered"] if best else 0,
                "total": b["count"],
                "ratio": round(best["covered"] / b["count"], 4) if best and b["count"] else 0.0,
                "pua": is_pua,
                "reason": reason,
            }
        )

    assigned = [a for a in assignments if a["font"]]
    return {
        "assignments": assignments,
        "summary": {
            "total_blocks": len(assignments),
            "assigned_blocks": len(assigned),
            "covered_blocks": covered_blocks,
            "unassigned_blocks": len(assignments) - len(assigned),
        },
        "imported": len(faces),
    }


def _reason_for(block: dict, best: dict | None, fonts: list[dict]) -> str:
    """Why this font won — the scoring criterion that decided it."""
    if best is None:
        return "no font covers this block"
    pref = PREFERRED_FONT_PER_BLOCK.get(block["name"], "")
    if pref and best["family"] == pref:
        return f"preferred font for {block['name']}"
    if best["covered"] >= block["count"]:
        return "full block coverage"
    same = [f for f in fonts if f["covered"] == best["covered"]]
    if len(same) > 1:
        return f"most characters in block ({best['covered']}), closest to Regular"
    return f"most characters in block ({best['covered']}/{block['count']})"
