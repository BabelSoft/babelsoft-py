"""Character History — how a character's codepoint/name/properties changed
across Unicode versions.

Ported from C++ ``CDialogHistory`` (c/Dialogs/DialogHistory.cpp) which fills a
row per version with the character's full UCD fields as they were in that
version (Version + Code Point + Name + General Category + CCC + Bidi +
Decomposition + Decimal/Digit/Numeric + Mirrored + Unicode 1.0 Name + ISO
Comment + Upper/Lower/Title).

The interesting part is the early history: Unicode 1.0/1.1 used different
codepoints for whole scripts (Tibetan U+1000-104F, Hangul syllables U+3400-4DFF)
and assorted single characters (Greek, Arabic presentation forms, CJK symbols,
...).  Those moves/removals are hand-maintained in BabelMap's C++ (NOT in any
UCD file); the data now lives in ``data/scripts/unicode_1_0_mappings.tsv`` and
is parsed by ``src.unicode.core.Unicode``.
"""

from __future__ import annotations

import bisect
import functools

from src.unicode.core import Unicode

from babelmap.backend.version import (
    all_versions,
    name_for_version,
    props_for_version,
    raw_codepoints_for,
)

# Modern Hangul syllables (Unicode 2.0+).  In Unicode 1.0/1.1 they were at
# U+3400..U+3D2D (1.0.0) / U+3400..U+4DFF (1.1.5) — see HANGUL_1_0_LAST.
HANGUL_S_FIRST = 0xAC00
HANGUL_S_LAST = 0xD7A3
HANGUL_1_0_LAST = 0x3D2D

_VERSIONS: list[dict] | None = None

# UCD property columns (UnicodeData field order, minus codepoint).
_FIELDS = ("gc", "ccc", "bidi", "decomp", "dec", "digit", "num", "mirrored", "uni1", "iso", "up", "lo", "ti")


def _version_rows() -> list[dict]:
    global _VERSIONS
    if _VERSIONS is None:
        _VERSIONS = all_versions()
    return _VERSIONS


def _present_raw(version: str, cp: int) -> bool:
    cps = raw_codepoints_for(version)
    i = bisect.bisect_left(cps, cp)
    return i < len(cps) and cps[i] == cp


def _is_modern_hangul(cp: int) -> bool:
    return HANGUL_S_FIRST <= cp <= HANGUL_S_LAST


def _row(version: str, date: str, present: bool, cp: int | None, moved: bool, name: str) -> dict:
    r: dict = {"version": version, "date": date, "present": present, "codepoint": cp, "moved": moved, "name": name}
    for k in _FIELDS:
        r[k] = ""
    return r


def _current_props(cp: int) -> dict:
    """Synthesize UCD props for range-encoded chars (Hangul, CJK, ...) whose
    per-codepoint entry does not exist in UnicodeData, using the current release
    (and the algorithmic Hangul decomposition)."""
    out: dict = {k: "" for k in _FIELDS}
    try:
        out["gc"] = Unicode.get_general_category(cp).name
    except Exception:
        pass
    try:
        out["ccc"] = str(Unicode.get_canonical_combining_class(cp))
    except Exception:
        pass
    try:
        out["bidi"] = Unicode.get_bidi_class(cp).name
    except Exception:
        pass
    try:
        out["mirrored"] = "Y" if Unicode.get_bidi_mirrored(cp) else "N"
    except Exception:
        pass
    # Hangul syllables decompose algorithmically into jamo — available in every
    # version even though UnicodeData range-encodes them (no per-cp entry).
    out["decomp"] = Unicode._hangul_decomposition(cp)
    return out


def _full_row(version: str, date: str, modern_cp: int, srcver: str, srccp: int) -> dict:
    """A present row with full per-version UCD properties.

    Properties come from the version's own UnicodeData at ``srccp`` (the code
    point the character occupied in that version, which may be an old 1.0/1.1
    codepoint).  ``modern_cp`` is the character's current codepoint, used to
    flag rows where the codepoint differs (moved).  Range-encoded characters
    (CJK, Hangul, ...) have no per-codepoint entry — fall back to the current
    release's values for the property columns.
    """
    e = props_for_version(srcver, srccp) or {}
    # Range placeholders (e.g. `<Hangul Syllable, First>`) have gc/ccc but no
    # per-codepoint data — fall back to synthesized props for those.
    if not e or e.get("name", "").startswith("<"):
        e = _current_props(modern_cp)
    name = e.get("name", "")
    if not name or name.startswith("<"):
        name = Unicode.get_character_name(modern_cp)
    r = _row(version, date, True, srccp, srccp != modern_cp, name)
    for k in _FIELDS:
        r[k] = e.get(k, "")
    return r


def character_history(cp: int) -> dict:
    """Return per-version history for one codepoint.

    Each row carries the character's state in that version: ``present``,
    ``codepoint`` (the codepoint it occupied then), ``name`` plus the UCD
    property columns (``gc``, ``ccc``, ``bidi``, ``decomp``, ``dec``, ``digit``,
    ``num``, ``mirrored``, ``uni1``, ``iso``, ``up``, ``lo``, ``ti``).
    """
    rows: list[dict] = []
    for v in _version_rows():
        ver = v["version"]
        date = v.get("date", "")

        # ── Unicode 1.0.0 / 1.0.1 — only codepoint + name (as in C++) ──
        if ver in ("1.0.0", "1.0.1"):
            u1 = Unicode.unicode1_codepoint(cp)
            if u1 is not None:
                # Hangul syllables beyond the 1.0.0 range weren't encoded yet
                if _is_modern_hangul(cp) and u1 > HANGUL_1_0_LAST:
                    continue
                n = name_for_version(ver, u1) or Unicode.get_character_name(u1)
                rows.append(_row(ver, date, True, u1, u1 != cp, n))
                continue
            if Unicode.is_unicode1_removed(cp) or Unicode.is_unicode1_moved(cp):
                continue  # this codepoint's 1.0 occupant moved/removed — no row
            if _present_raw(ver, cp):
                n = name_for_version(ver, cp) or Unicode.get_character_name(cp)
                rows.append(_row(ver, date, True, cp, False, n))
            else:
                rows.append(_row(ver, date, False, None, False, ""))
            continue

        # ── 1.1.5 — Hangul was still at its old U+3400-4DFF codepoints ──
        if ver == "1.1.5" and _is_modern_hangul(cp):
            u1 = Unicode.unicode1_codepoint(cp)
            if u1 is not None and _present_raw(ver, u1):
                rows.append(_full_row(ver, date, cp, ver, u1))
                continue

        # ── all other versions — full properties at the current codepoint ──
        if _present_raw(ver, cp):
            rows.append(_full_row(ver, date, cp, ver, cp))
        else:
            rows.append(_row(ver, date, False, None, False, ""))

    return {
        "cp": cp,
        "char": chr(cp),
        "name": Unicode.get_character_name(cp),
        "rows": rows,
    }


def block_unicodedata(version: str, block_name: str) -> list[dict] | None:
    """UnicodeData rows (codepoint + name + all UCD fields) for every assigned
    character in one block of a Unicode version.  Returns None for an unknown
    block.

    Mirrors the per-character UCD fields used by the Character History dialog
    (gc/ccc/bidi/decomp/dec/digit/num/mirrored/uni1/iso/up/lo/ti);
    range-encoded characters (Hangul, CJK, …) fall back to the current
    release's synthesized properties.
    """
    from babelmap.backend.version import assigned_codepoints_for, blocks_for_version

    block = next((b for b in blocks_for_version(version) if b["name"] == block_name), None)
    if block is None:
        return None
    cps = assigned_codepoints_for(version)
    lo = bisect.bisect_left(cps, block["start"])
    hi = bisect.bisect_right(cps, block["end"])
    rows: list[dict] = []
    for cp in cps[lo:hi]:
        e = props_for_version(version, cp) or {}
        if not e or e.get("name", "").startswith("<"):
            e = _current_props(cp)
        name = e.get("name", "")
        if not name or name.startswith("<"):
            name = Unicode.get_character_name(cp) or ""
        r = {"codepoint": cp, "name": name}
        for k in _FIELDS:
            r[k] = e.get(k, "")
        rows.append(r)
    return rows


@functools.lru_cache(maxsize=1)
def _self_test() -> None:
    """Sanity checks mirroring known BabelMap cases."""
    # TIBETAN LETTER KA — moved U+1000 → U+0F40
    h = character_history(0x0F40)
    row10 = next((r for r in h["rows"] if r["version"] == "1.0.0"), None)
    assert row10 and row10["codepoint"] == 0x1000 and row10["name"] == "TIBETAN LETTER KA", h["rows"][:3]
    # HANGUL SYLLABLE GA — moved U+3400 → U+AC00
    h = character_history(0xAC00)
    row10 = next((r for r in h["rows"] if r["version"] == "1.0.0"), None)
    assert row10 and row10["codepoint"] == 0x3400, h["rows"][:3]
    # GREEK NON-SPACING IOTA BELOW → COMBINING GREEK YPOGEGRAMMENI (U+0345)
    h = character_history(0x0345)
    row10 = next((r for r in h["rows"] if r["version"] == "1.0.0"), None)
    assert row10 and row10["codepoint"] == 0x0370, h["rows"][:3]
