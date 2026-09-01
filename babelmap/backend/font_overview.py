"""Font Overview — enumerate every installed font across multiple font
directories, group them by font family and by primary writing system
(script), and expose full metadata for a modern overview UI.

Metadata is read lazily with fontTools (``name`` / ``OS/2`` / ``head`` /
``maxp`` / ``cmap`` / ``fvar``).  Per-file results are cached keyed on
(mtime, size) so repeat scans are cheap.

Public API:
- :func:`scan_fonts` — scan directories → list of font-face entries.
"""

from __future__ import annotations

import bisect
import logging
import os
import re
import struct
import warnings
from datetime import datetime, timezone

# fontTools logs noisy "timestamp seems very low" warnings when reading some
# fonts' head.created/modified fields; they're harmless, so keep them quiet.
logging.getLogger("fontTools.ttLib.tables._h_e_a_d").setLevel(logging.ERROR)

try:  # pragma: no cover - import guard
    from fontTools.ttLib import TTFont

    HAS_FONTTOOLS = True
except Exception:  # pragma: no cover
    TTFont = None
    HAS_FONTTOOLS = False

# ── Font directories (multiple) ──────────────────────────────────────
# Default sources: the system Fonts folder plus per-user installed fonts.
# Callers may pass extra directories to :func:`scan_fonts`.


def _default_dirs() -> list[str]:
    dirs: list[str] = []
    windir = os.environ.get("WINDIR", r"C:\Windows")
    sysdir = os.path.join(windir, "Fonts")
    if os.path.isdir(sysdir):
        dirs.append(sysdir)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        userdir = os.path.join(local, "Microsoft", "Windows", "Fonts")
        if os.path.isdir(userdir):
            dirs.append(userdir)
    return dirs


DEFAULT_DIRS = _default_dirs()

EXTENSIONS = (".ttf", ".otf", ".ttc")

# ── Writing-system (script) data ─────────────────────────────────────
# Ranges are derived from the UCD via ``babelsoft.unicode.core.Unicode`` —
# Scripts.txt for real scripts, Blocks.txt for the symbol category, and the
# RGI emoji list (UTS #51 emoji-test.txt) for emoji.  No hex ranges are
# hand-maintained here, so coverage always tracks the current Unicode data.

# "Symbols" is not a Unicode Script (symbols are Script=Common), so it is
# defined by General_Category = Sm | Sc | Sk | So — the Unicode Standard's
# authoritative definition of Symbol — read from Unicode._gc_table().
_SYMBOL_GC = frozenset({"Sm", "Sc", "Sk", "So"})


def _short_label(name: str, tag: str) -> str:
    """Short display label from an ISO 15924 name by stripping parenthetical
    annotations (e.g. 'Han (Hanzi, Kanji, Hanja)' → 'Han').  Zsye keeps its
    full name so it stays distinct from Zsym ('Symbols')."""
    if not name:
        return tag
    if tag == "zsye":
        return name
    return name.split(" (")[0].strip()


# Private Use areas.  ISO 15924 reserves the Qaaa–Qabx range ("Reserved for
# private use") for exactly this purpose, so PUA / SPUA-A / SPUA-B are
# associated with the Qaaa code and count toward coverage.
_PUA_RANGES = (
    (0xE000, 0xF8FF),  # Private Use Area
    (0xF0000, 0xFFFFD),  # Supplementary Private Use Area-A
    (0x100000, 0x10FFFD),  # Supplementary Private Use Area-B
)


def _merge_ranges(points: list[int]) -> list[tuple[int, int]]:
    """Merge sorted codepoints into disjoint [start, end] ranges."""
    out: list[tuple[int, int]] = []
    for cp in points:
        if out and cp == out[-1][1] + 1:
            out[-1] = (out[-1][0], cp)
        else:
            out.append((cp, cp))
    return out


def _subtract_ranges(ranges: list[tuple[int, int]], points: list[int]) -> list[tuple[int, int]]:
    """Remove the given (sorted) codepoints from the ranges (keeps disjoint)."""
    if not points:
        return list(ranges)
    out: list[tuple[int, int]] = []
    for s, e in ranges:
        cur = s
        for p in points:
            if p > e:
                break
            if p >= cur:
                if cur < p:
                    out.append((cur, p - 1))
                cur = p + 1
        if cur <= e:
            out.append((cur, e))
    return [r for r in out if r[0] <= r[1]]


def _build_scripts() -> dict[str, dict]:
    """SCRIPTS = {tag: {label, ranges}}.  Tags and labels come from the ISO
    15924 table; ranges come from the UCD (Scripts.txt / General Category /
    RGI emoji).  Nothing is hand-maintained here."""
    from babelsoft.unicode.core import Unicode
    from babelsoft.utils_.dirs import Dirs
    from babelsoft.utils_.parser import TsvParser

    # 1. Every ISO 15924 tag + label (data/scripts/iso15924.tsv).
    iso_labels: dict[str, str] = {}
    try:
        for row in TsvParser.get_tsv(Dirs.DATA / "scripts" / "iso15924.tsv"):
            if len(row) >= 3 and row[0].strip() and row[2].strip():
                iso_labels[row[0].strip().lower()] = row[2].strip()
    except Exception:
        iso_labels = {}

    # 2. Real-script ranges from Scripts.txt, keyed by ISO 15924 tag.
    table, full_names = Unicode._script_data()
    by_iso: dict[str, list[tuple[int, int]]] = {}
    for s, e, idx in table:
        iso = Unicode.get_script_iso_code(full_names[idx]) or full_names[idx]
        by_iso.setdefault(iso.lower(), []).append((s, e))

    # 3. Emoji codepoints from the RGI emoji list (UTS #51 emoji-test.txt);
    #    skip ASCII (keycap bases), ZWJ/ZWNJ and variation selectors.
    emoji_cps: set[int] = set()
    try:
        from babelsoft.unicode.emoji import all_emoji

        for emo in all_emoji():
            emoji_cps.update(cp for cp in emo.codepoints if cp >= 0xA0 and cp not in (0x200C, 0x200D, 0xFE0E, 0xFE0F))
    except Exception:
        emoji_cps = set()
    emoji_ranges = _merge_ranges(sorted(emoji_cps))

    # 4. Track every ISO 15924 script (unioned with Scripts.txt so a script
    #    is never missed even if the table lags a Unicode release).  Non-
    #    writing-system categories (Common / Inherited / Unknown) carry ISO
    #    names of the form "Code for ... script" and get no ranges.  Zsym /
    #    Zsye are computed last so they can be kept disjoint from the real
    #    scripts.
    tags = sorted(set(iso_labels) | set(by_iso))
    scripts: dict[str, dict] = {}
    for tag in tags:
        if tag in ("zsym", "zsye"):
            continue  # added after the real-script ranges are known
        raw = iso_labels.get(tag, "")
        ranges = by_iso.get(tag, []) if not raw.startswith("Code for") else []
        scripts[tag] = {"label": _short_label(raw, tag), "ranges": ranges}

    # 4b. Private Use areas (PUA / SPUA-A / SPUA-B) are associated with the
    #     ISO 15924 private-use code Qaaa ("Reserved for private use").  They
    #     are not writing systems, but mapping them lets a font's Private Use
    #     content be counted and shown in per-script coverage.
    if "qaaa" in scripts:
        scripts["qaaa"]["ranges"] = list(_PUA_RANGES)

    # 5. Symbols (Zsym) = General_Category Sm|Sc|Sk|So from the UCD, minus the
    #    emoji codepoints AND minus every real-script codepoint.  Some
    #    codepoints are both a real script and a symbol (e.g. Yi Radicals are
    #    Script=Yi and gc=Other_Symbol); keeping Symbols disjoint from the
    #    real scripts means those codepoints count toward their script (Yi),
    #    so per-script coverage sums exactly to the face's coverage.
    script_pts = sorted(cp for spec in scripts.values() for s, e in spec["ranges"] for cp in range(s, e + 1))
    gc_vals = {Unicode._GC_MAP[k] for k in _SYMBOL_GC}
    sym_ranges = [(s, e) for s, e, gc in Unicode._gc_table() if gc in gc_vals]
    sym_ranges = _subtract_ranges(sym_ranges, sorted(emoji_cps))
    sym_ranges = _subtract_ranges(sym_ranges, script_pts)
    scripts["zsym"] = {"label": _short_label(iso_labels.get("zsym", ""), "zsym"), "ranges": sym_ranges}
    scripts["zsye"] = {"label": _short_label(iso_labels.get("zsye", ""), "zsye"), "ranges": emoji_ranges}
    return scripts


SCRIPTS: dict[str, dict] = _build_scripts()

# Union of every sample range — the "common repertoire" used for the overall
# coverage percentage.
_RANGE_TOTAL = sum((e - s + 1) for spec in SCRIPTS.values() for s, e in spec["ranges"])

# Combined writing systems (the special CJK families) plus a display name.
GROUP_LABELS: dict[str, str] = {tag: spec["label"] for tag, spec in SCRIPTS.items()}
GROUP_LABELS.update(
    {
        "jpan": "Japanese",
        "kore": "Korean",
        "hani": "Chinese (Han)",
        "hang": "Korean (Hangul)",
        "hira": "Japanese (Kana)",
        "kana": "Japanese (Kana)",
        "zsye": "Emoji",
        "zzzz": "Other / Unknown",
        "qaaa": "Private Use (PUA)",
    }
)

# Scripts that form the special combined CJK groups.
_CJK = ("hira", "kana", "hani", "hang")


# ── Unicode Core Specification chapters ──────────────────────────────
# Every ISO 15924 code maps to the chapter of the Unicode Core Specification
# that documents its script (data/scripts/core_spec_chapters.tsv), so the
# writing-system tags cover the whole of ISO 15924.  One color is assigned per
# chapter, taken from a Pantone color series (classic / Color of the Year
# colors) in chapter order — chapter 6 = Writing Systems & Punctuation …
# chapter 22 = Symbols.
_CHAPTER_PALETTE = [
    "#767676",  # 6  Writing Systems & Punctuation — Pantone 17-4005 Steel Gray
    "#34558b",  # 7  Europe-I                  — Pantone 19-4052 Classic Blue
    "#5b5ea6",  # 8  Europe-II                 — Pantone 18-3943 Blue Iris
    "#6667ab",  # 9  Middle East-I             — Pantone 17-3938 Very Peri
    "#5b4fa3",  # 10 Middle East-II            — Pantone 18-3838 Ultra Violet
    "#955251",  # 11 Cuneiform & Hieroglyphs   — Pantone 18-1438 Marsala
    "#bf1932",  # 12 South & Central Asia-I    — Pantone 19-1664 True Red
    "#bb2649",  # 13 South & Central Asia-II   — Pantone 18-1750 Viva Magenta
    "#ff6f61",  # 14 South & Central Asia-III  — Pantone 16-1546 Living Coral
    "#cc5500",  # 15 South & Central Asia-IV   — Pantone 18-1355 Burnt Orange
    "#009473",  # 16 Southeast Asia-I          — Pantone 17-5641 Emerald
    "#45b5aa",  # 17 Southeast Asia-II         — Pantone 15-5519 Turquoise
    "#006a6e",  # 18 East Asia                 — Pantone 19-5232 Deep Lagoon
    "#88b04b",  # 19 Africa                    — Pantone 15-0343 Greenery
    "#fe840e",  # 20 Americas                  — Pantone 16-0843 Turmeric
    "#f2a900",  # 21 Notational Systems        — Pantone 14-0957 Yolk Yellow
    "#7a4b32",  # 22 Symbols                   — Pantone 19-1029 Chestnut
]


def _build_chapters() -> tuple[dict[str, int], dict[int, dict]]:
    """Chapter of each ISO 15924 code from the Core Specification.

    Loaded from ``data/scripts/core_spec_chapters.tsv`` (columns: chapter,
    chapter label, script name, ISO 15924 code).  Returns ``{iso_code_lower:
    chapter_num}`` and ``{chapter_num: {num, label, color}}`` — one color per
    chapter, assigned in chapter-number order.
    """
    from babelsoft.utils_.dirs import Dirs
    from babelsoft.utils_.parser import TsvParser

    code_chapter: dict[str, int] = {}
    chapter_label: dict[int, str] = {}
    try:
        for row in TsvParser.get_tsv(Dirs.DATA / "scripts" / "core_spec_chapters.tsv"):
            if len(row) < 4 or not row[0].strip() or not row[3].strip():
                continue
            try:
                num = int(row[0].strip())
            except ValueError:
                continue
            chapter_label.setdefault(num, row[1].strip())
            code_chapter[row[3].strip().lower()] = num
    except Exception:
        pass

    chapters: dict[int, dict] = {}
    for i, num in enumerate(sorted(chapter_label)):
        chapters[num] = {
            "num": num,
            "label": chapter_label[num],
            "color": _CHAPTER_PALETTE[i % len(_CHAPTER_PALETTE)],
        }
    return code_chapter, chapters


SCRIPT_CHAPTER, CHAPTERS = _build_chapters()


# Per-script Unicode-block breakdown, reused from ``Unicode._block_data`` (the
# same Blocks.txt data that drives the Blocks dialog).  This is the "list of
# blocks" a script maps to; a script's coverage statistics can be expanded
# into these per-block range statistics.
def _range_overlap(ranges: list[tuple[int, int]], qs: int, qe: int) -> int:
    """Count of codepoints in sorted ``ranges`` that fall inside [qs, qe]."""
    n = 0
    for s, e in ranges:
        if e < qs:
            continue
        if s > qe:
            break
        n += min(e, qe) - max(s, qs) + 1
    return n


def _build_script_blocks() -> dict[str, list[dict]]:
    from babelsoft.unicode.core import Unicode

    table, names = Unicode._block_data()
    out: dict[str, list[dict]] = {}
    for tag, spec in SCRIPTS.items():
        blocks: list[dict] = []
        for s, e, idx in table:
            if 0xD800 <= s <= 0xDFFF:  # surrogates are not characters
                continue
            n = _range_overlap(spec["ranges"], s, e)
            if n:
                blocks.append({"name": names[idx], "start": s, "end": e, "chars": n})
        out[tag] = blocks
    return out


SCRIPT_BLOCKS: dict[str, list[dict]] = _build_script_blocks()

# Pre-merged sorted range table for fast per-face script counting.
_ALL_RANGES = sorted((s, e, tag) for tag, spec in SCRIPTS.items() for s, e in spec["ranges"])
_RANGE_STARTS = [r[0] for r in _ALL_RANGES]
_RANGE_ENDS = [r[1] for r in _ALL_RANGES]
_RANGE_TAGS = [r[2] for r in _ALL_RANGES]


# ── Hyper-family grouping ────────────────────────────────────────────
# A hyper family groups font families that are naming variants of one design
# (script / plane / numbered / variant-word suffixes).  There is no
# authoritative data source for this — foundries name variants inconsistently
# — so a conservative suffix-stripping rule derives a canonical base name:
#
#   TH-Tshyn-P16     → TH-Tshyn      (plane suffix)
#   TH-Times_cyrl    → TH-Times      (script suffix)
#   Iosevka Fixed    → Iosevka       (variant word)
#   Wingdings 2      → Wingdings     (numbered variant)
_HYPER_VARIANT_WORDS = (
    "Fixed",
    "Term",
    "Var",
    "Variable",
    "Pro",
    "Std",
    "Plus",
    "Rounded",
    "LGC",
    "SC",
    "TC",
    "JP",
    "KR",
    "HK",
)
_HYPER_SUFFIX_PATTERNS = (
    re.compile(r"[- ]?P\d+$", re.IGNORECASE),
    re.compile(r"_([A-Za-z]{2,6})$"),
    re.compile(r"[- ]?\d+$"),
    re.compile(r"[- ](?:%s)$" % "|".join(_HYPER_VARIANT_WORDS), re.IGNORECASE),
)

# Curated hyper-family series — naming variants of one design that suffix
# stripping cannot infer (foundry conventions).  Keys are the family name
# normalized (lowercase, spaces/hyphens/underscores removed); values are the
# hyper-family display name.
_HYPER_RULES: list[tuple[str, str]] = [
    ("msmingliu", "MingLiU"),
    ("microsoftjhenghei", "Microsoft JhengHei"),
    ("microsoftyahei", "Microsoft YaHei"),
    ("microsoftyinghei", "Microsoft YingHei"),
    ("fzxiaobiaosong", "FZXiaoBiaoSong"),
    ("twcenmt", "TW Cen MT"),
    ("franklingothic", "Franklin Gothic"),
    ("copperplate", "Copperplate Gothic"),
    ("gillsans", "Gill Sans MT"),
    ("segoe", "Segoe UI"),
    ("century", "Century"),
    ("gentium", "Gentium"),
    ("lucida", "Lucida"),
    ("nirmala", "Nirmala UI"),
    ("twsung", "TW-Sung"),
    ("twkai", "TW-Kai"),
    ("cascadia", "Cascadia"),
    ("eras", "Eras ITC"),
    ("helsinki", "Helsinki"),
    ("inkpen", "Inkpen"),
    ("mingliu", "MingLiU"),
    ("simsun", "SimSun"),
    ("opus", "Opus"),
    ("reprise", "Reprise"),
    ("wp", "WP"),
    ("code200", "Code"),
]


def _norm_name(name: str) -> str:
    """Lowercase name with spaces/hyphens/underscores removed (for rules)."""
    return re.sub(r"[\s\-_]", "", name.strip().lower())


def _hyper_family(family: str) -> str:
    """Canonical hyper-family base name for a font family."""
    norm = _norm_name(family)
    for prefix, hyper in _HYPER_RULES:
        if norm.startswith(prefix):
            return hyper
    key = family.strip()
    prev = None
    while prev != key:
        prev = key
        for pat in _HYPER_SUFFIX_PATTERNS:
            key = pat.sub("", key)
    return key.strip()


# ── Per-file cache ────────────────────────────────────────────────────
# key = (abspath, mtime_ns, size) → entry
_cache: dict[tuple, dict] = {}


def _source_label(path: str) -> str:
    norm = os.path.normcase(os.path.normpath(path))
    sysdir = os.path.normcase(os.path.normpath(DEFAULT_DIRS[0])) if DEFAULT_DIRS else None
    for d in DEFAULT_DIRS:
        dnorm = os.path.normcase(os.path.normpath(d))
        if norm.startswith(dnorm):
            return "System" if sysdir and dnorm == sysdir else "User"
    return "Custom"


# ── fontTools helpers ─────────────────────────────────────────────────


def _iter_faces(path: str):
    """Yield one ``TTFont`` per face in a file (handles .ttc)."""
    if not HAS_FONTTOOLS:
        return
    if path.lower().endswith(".ttc"):
        try:
            with open(path, "rb") as f:
                tag = f.read(4)
                if tag != b"ttcf":
                    yield TTFont(path, lazy=True)
                    return
                f.seek(8)
                num = struct.unpack(">L", f.read(4))[0]
            for i in range(max(0, min(num, 64))):
                yield TTFont(path, fontNumber=i, lazy=True)
        except Exception:
            try:
                yield TTFont(path, lazy=True)
            except Exception:
                return
    else:
        try:
            yield TTFont(path, lazy=True)
        except Exception:
            return


def _name(tt, *ids) -> str | None:
    """First non-empty name record among the given name IDs (preferring the
    newest / typographic records)."""
    try:
        nt = tt["name"]
        for nid in ids:
            v = nt.getDebugName(nid)
            if v and v.strip():
                return v.strip()
    except Exception:
        pass
    return None


# ── localized name-table metadata ──────────────────────────────────────────
# (platform, langID) → display language name.  The mapping is DATA, not code:
# it is loaded from ``data/scripts/name_lang.tsv``, which is derived from the
# authoritative references the OpenType 'name' table spec points to —
#   platform 1 (Macintosh): Apple TrueType Reference Manual, 'name' table
#   platform 3 (Windows):   [MS-LCID] Windows Language Code Identifier (LCID)
#                           Reference
# Sublanguage variants of one language (US/UK/AU English, zh-Hant/zh-Hans …)
# all carry the same display label in the TSV, so they merge into a single
# metadata block.
_NAME_LANG_TSV = "scripts/name_lang.tsv"


def _load_name_lang() -> dict[tuple[int, int], str]:
    from babelsoft.utils_.dirs import Dirs
    from babelsoft.utils_.parser import TsvParser

    out: dict[tuple[int, int], str] = {}
    try:
        for row in TsvParser.get_tsv(Dirs.DATA / _NAME_LANG_TSV):
            if len(row) < 4 or not row[0].strip() or not row[1].strip() or not row[3].strip():
                continue
            try:
                platform = int(row[0].strip())
                raw = row[1].strip()
                lang = int(raw, 16) if raw.lower().startswith("0x") else int(raw)
            except ValueError:
                continue
            out[(platform, lang)] = row[3].strip()
    except Exception:
        pass
    return out


_NAME_LANG: dict[tuple[int, int], str] = _load_name_lang()


def _lang_label(platform_id: int, lang_id: int) -> str | None:
    """Human-readable language name for a name-table (platform, langID)."""
    return _NAME_LANG.get((platform_id, lang_id & 0xFFFF))


# name IDs that make up the metadata panel
_META_NAME_IDS = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17}


def _read_name_langs(tt) -> list[dict]:
    """Localized name-table strings grouped by language.

    Returns one entry per language that declares any of the metadata name
    IDs, ordered by first appearance in the ``name`` table; the first entry
    is the font's primary (default) language — the one the flat metadata
    fields are read from.  Entries whose content is identical to the primary
    language (e.g. the same strings re-encoded for the Macintosh platform)
    are dropped.  Each entry:
      {label, family, subfamily, full_name, ps_name, version, copyright,
       manufacturer, designer, designer_url, license, license_url, trademark,
       description}
    """
    try:
        nt = tt["name"]
    except Exception:
        return []
    groups: dict[str, dict] = {}
    order: list[str] = []
    for rec in nt.names:
        if rec.nameID not in _META_NAME_IDS:
            continue
        try:
            text = rec.toUnicode().strip()
        except Exception:
            continue
        if not text:
            continue
        label = _lang_label(rec.platformID, rec.langID) or f"Lang {rec.langID:04X}"
        if label not in groups:
            groups[label] = {}
            order.append(label)
        groups[label].setdefault(rec.nameID, text)

    out: list[dict] = []
    for label in order:
        d = groups[label]
        out.append(
            {
                "label": label,
                "family": d.get(16) or d.get(1) or "",
                "subfamily": d.get(17) or d.get(2) or "",
                "full_name": d.get(4) or "",
                "ps_name": d.get(6) or "",
                "version": d.get(5) or "",
                "copyright": d.get(0) or "",
                "manufacturer": d.get(8) or "",
                "designer": d.get(9) or "",
                "designer_url": d.get(11) or d.get(12) or "",
                "license": d.get(13) or "",
                "license_url": d.get(14) or "",
                "trademark": d.get(7) or "",
                "description": d.get(10) or "",
            }
        )
    if out:
        sig = {k: v for k, v in out[0].items() if k != "label"}
        kept = [out[0]]
        for e in out[1:]:
            if {k: v for k, v in e.items() if k != "label"} != sig:
                kept.append(e)
        out = kept
    return out


def _longdt(seconds: int | None) -> str | None:
    """head 'longdatetime' (seconds since 1904-01-01) → ISO date string."""
    if seconds is None or seconds <= 0:
        return None
    try:
        return datetime.fromtimestamp(seconds - 2082844800, tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return None


def _read_cmap(tt) -> set[int] | None:
    """Merged set of covered codepoints across all Unicode cmap subtables."""
    try:
        if "cmap" not in tt:
            return None
        cps: set[int] = set()
        for t in tt["cmap"].tables:
            if t.isUnicode():
                cps.update(t.cmap.keys())
        return cps
    except Exception:
        return None


def _count_scripts(cps: set[int] | None) -> dict[str, int]:
    counts = {tag: 0 for tag in SCRIPTS}
    if not cps:
        return counts
    for cp in cps:
        i = bisect.bisect_right(_RANGE_STARTS, cp) - 1
        if i >= 0 and cp <= _RANGE_ENDS[i]:
            counts[_RANGE_TAGS[i]] += 1
    return counts


def _covered_ranges(cps: list[int]) -> list[tuple[int, int]]:
    """Merged disjoint [start, end] ranges of ``cps`` that fall inside the
    common repertoire (any script range) — the face's distinct covered
    characters.  Script ranges are pairwise disjoint, so each code point maps
    to at most one script."""
    if not cps:
        return []
    out: list[tuple[int, int]] = []
    for cp in cps:
        i = bisect.bisect_right(_RANGE_STARTS, cp) - 1
        if i >= 0 and cp <= _RANGE_ENDS[i]:
            if out and cp == out[-1][1] + 1:
                out[-1] = (out[-1][0], cp)
            else:
                out.append((cp, cp))
    return out


def _union_range_count(lists: list[list[tuple[int, int]]]) -> int:
    """Size of the union of disjoint range lists — shared code points across
    faces of one design count once."""
    pts = [r for rs in lists for r in rs]
    if not pts:
        return 0
    pts.sort()
    total = 0
    cs, ce = pts[0]
    for s, e in pts[1:]:
        if s <= ce + 1:
            if e > ce:
                ce = e
        else:
            total += ce - cs + 1
            cs, ce = s, e
    total += ce - cs + 1
    return total


def _read_ot_langs(tt) -> set[str]:
    """Language-system tags declared in GSUB/GPOS (e.g. JAN, ZHS, KOR).

    These are a strong signal for disambiguating CJK fonts that all share
    the Han block: a Chinese font declares ``ZHS``/``ZHT``/``CHN``, a
    Japanese font declares ``JAN`` and a Korean font declares ``KOR``.
    """
    langs: set[str] = set()
    for table in ("GSUB", "GPOS"):
        try:
            sl = tt[table].table.ScriptList
            for rec in sl.ScriptRecord:
                ss = rec.Script
                if ss and getattr(ss, "LangSysRecord", None):
                    for lr in ss.LangSysRecord:
                        tag = (lr.LangSysTag or "").strip()
                        if tag:
                            langs.add(tag)
        except Exception:
            pass
    return langs


def _read_ot_features(tt) -> list[str]:
    """OpenType Layout feature tags declared in GSUB/GPOS (e.g. liga, kern,
    ccmp, smcp, ss01…), sorted for display."""
    tags: set[str] = set()
    for table in ("GSUB", "GPOS"):
        try:
            fl = tt[table].table.FeatureList
            for rec in fl.FeatureRecord:
                tag = (rec.FeatureTag or "").strip()
                if tag:
                    tags.add(tag)
        except Exception:
            pass
    return sorted(tags)


def _resolve_main(counts: dict[str, int], symbol: bool, langs: set[str]) -> tuple[str, str]:
    """Pick the face's primary writing system.

    CJK fonts are special-cased so that Japanese fonts land under 'jpan',
    Korean fonts under 'kore' and Chinese fonts under 'hani', instead of
    everything collapsing into the huge Han block.  The GSUB/GPOS language
    systems are preferred when present and consistent with coverage; the
    coverage heuristics are the fallback.
    """
    hira = counts.get("hira", 0)
    kana = counts.get("kana", 0)
    hani = counts.get("hani", 0)
    hang = counts.get("hang", 0)
    latn = counts.get("latn", 0)
    emoji = counts.get("zsye", 0)
    zsym = counts.get("zsym", 0)

    if symbol:
        return "zsym", GROUP_LABELS["zsym"]
    L = {t.strip() for t in langs}
    if (L & {"ZHS", "ZHT", "CHN"}) and hani >= 500:
        return "hani", GROUP_LABELS["hani"]
    if "JAN" in L and hira + kana >= 80:
        return "jpan", GROUP_LABELS["jpan"]
    if "KOR" in L and hang >= 1500:
        return "kore", GROUP_LABELS["kore"]
    # Coverage fallback.  A Han-dominant font is Chinese even when it also
    # carries kana (Chinese fonts routinely include kana glyphs) — the kana
    # only wins as the primary when Han is not dominant.  Kana still shows as
    # a secondary tag (see ``tags``).
    if hang >= 1500 and hang >= hani:
        return "kore", GROUP_LABELS["kore"]
    if hani >= 500:
        return "hani", GROUP_LABELS["hani"]
    if hira + kana >= 80:
        return "jpan", GROUP_LABELS["jpan"]
    if emoji >= 300 and emoji >= latn and emoji >= zsym:
        return "zsye", GROUP_LABELS["zsye"]
    if zsym >= 300 and zsym >= latn:
        return "zsym", GROUP_LABELS["zsym"]

    # Private Use is not a writing system, so Qaaa never becomes the primary
    # script (a pure-PUA font falls through to Other / Unknown).
    best = max((k for k in counts if k not in _CJK and k != "qaaa"), key=lambda k: counts[k], default=None)
    if best is None or counts[best] <= 0:
        return "zzzz", GROUP_LABELS["zzzz"]
    return best, GROUP_LABELS[best]


def _script_summary(counts: dict[str, int], sorted_cps: list[int]) -> list[dict]:
    """Top scripts by coverage, as {tag, label, covered, total, ratio, blocks}.

    ``blocks`` reuses the script→blocks list (``SCRIPT_BLOCKS``) so each
    script's statistics can be expanded into per-block range statistics
    ({name, start, end, covered, total}).
    """
    out = []
    for tag, n in counts.items():
        total = sum(e - s + 1 for s, e in SCRIPTS[tag]["ranges"])
        # Every script with any covered code point is shown, so the panel's
        # per-script sum always equals the face's total coverage figure.
        if total <= 0 or n <= 0:
            continue
        blocks: list[dict] = []
        sranges = SCRIPTS[tag]["ranges"]
        for b in SCRIPT_BLOCKS.get(tag, []):
            # Only count the face's codepoints that belong to THIS script
            # (blocks mix scripts — e.g. CJK Symbols & Punctuation holds both
            # Common and Han codepoints), so per-block totals sum to counts[tag].
            cov = 0
            for r_s, r_e in sranges:
                if r_e < b["start"]:
                    continue
                if r_s > b["end"]:
                    break
                lo = bisect.bisect_left(sorted_cps, max(r_s, b["start"]))
                hi = bisect.bisect_right(sorted_cps, min(r_e, b["end"]))
                cov += hi - lo
            # Skip blocks the face covers no characters in — only blocks with
            # real per-face coverage are shown.
            if cov:
                blocks.append(
                    {
                        "name": b["name"],
                        "start": b["start"],
                        "end": b["end"],
                        "covered": cov,
                        "total": b["chars"],
                    }
                )
        out.append(
            {
                "tag": tag,
                "label": SCRIPTS[tag]["label"],
                "chapter": SCRIPT_CHAPTER.get(tag),
                "covered": n,
                "total": total,
                "ratio": round(n / total, 4),
                "blocks": blocks,
            }
        )
    out.sort(key=lambda d: d["ratio"], reverse=True)
    return out


# Tags: scripts the face genuinely supports (multi-script labels).  Latin,
# Symbols and Unassigned/Private-Use are universal — they are only tagged when
# they are the primary script, so they do not drown out the meaningful writing
# systems.  Ratio alone penalizes huge scripts (Han ≈ 90k code points), so a
# script is also tagged on absolute coverage (≥ 500) even when its ratio is low.
_TAG_MIN_RATIO = 0.2
_TAG_MIN_COUNT = 20
_TAG_ABS_COVER = 500
_TAG_SKIP = frozenset({"latn", "zsym", "zzzz", "qaaa"})


def _script_tags(counts: dict[str, int], main_tag: str) -> list[dict]:
    """Every script the face genuinely covers, as {tag, label, chapter} tags
    (primary first).  There is no cap, and the primary script is always
    reported even when its coverage is thin, so every face carries at least
    one tagged writing system (and thus a chapter color)."""
    cands = []
    for tag, n in counts.items():
        if tag in _TAG_SKIP and tag != main_tag:
            continue
        total = sum(e - s + 1 for s, e in SCRIPTS[tag]["ranges"])
        if total <= 0 or n < _TAG_MIN_COUNT:
            continue
        ratio = n / total
        if ratio < _TAG_MIN_RATIO and n < _TAG_ABS_COVER:
            continue
        cands.append({"tag": tag, "label": SCRIPTS[tag]["label"], "ratio": round(ratio, 4)})
    cands.sort(key=lambda d: d["ratio"], reverse=True)
    cands.sort(key=lambda d: d["tag"] != main_tag)  # primary script first
    tags = [
        {
            "tag": d["tag"],
            "label": d["label"],
            "chapter": SCRIPT_CHAPTER.get(d["tag"]),
        }
        for d in cands
    ]
    if not tags:
        tags = [
            {
                "tag": main_tag,
                "label": SCRIPTS[main_tag]["label"],
                "chapter": SCRIPT_CHAPTER.get(main_tag),
            }
        ]
    return tags


def _is_symbol_font(tt) -> bool:
    """True for legacy symbol fonts (Wingdings, Marlett, Symbol…): they ship
    a (3,0) symbol cmap and no standard (3,1) Unicode cmap."""
    try:
        cm = tt["cmap"]
        has30 = any(t.platformID == 3 and t.platEncID == 0 for t in cm.tables)
        has31 = any(t.platformID == 3 and t.platEncID == 1 for t in cm.tables)
        return has30 and not has31
    except Exception:
        return False


def _axis_step(mn: float, dv: float, mx: float) -> float:
    """Slider step for an fvar axis: 1 for integer-valued axes (e.g. wght),
    else a fractional step (1/1000 of the range, at least 0.001)."""
    if all(float(v).is_integer() for v in (mn, dv, mx)):
        return 1
    step = (mx - mn) / 1000
    return max(round(step, 3), 0.001)


def _face_entry(path: str, index: int, source: str) -> dict | None:
    """Extract metadata for one face (already opened) → entry dict."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tt = TTFont(path, fontNumber=index, lazy=True)
    except Exception:
        return None

    # OS/2
    weight, width, italic, symbol, fs_type = 400, 5, False, False, 0
    panose: list[int] = []
    try:
        o = tt["OS/2"]
        weight = o.usWeightClass or 400
        width = o.usWidthClass or 5
        fs = o.fsSelection
        italic = bool(fs & 0x01)
        fs_type = o.fsType or 0
        panose = list(getattr(o, "panose", None) or [])
    except Exception:
        pass
    symbol = _is_symbol_font(tt)

    # head
    upem, created, modified = 2048, None, None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            hd = tt["head"]
            upem = hd.unitsPerEm or 2048
            created = _longdt(hd.created)
            modified = _longdt(hd.modified)
    except Exception:
        pass

    # maxp
    glyphs = 0
    try:
        glyphs = tt["maxp"].numGlyphs or 0
    except Exception:
        pass

    # Glyph count by glyph name (distinct names in the glyph order) — the
    # glyphs figure the overview shows is counted this way.
    glyph_count = glyphs
    glyph_names: frozenset = frozenset()
    try:
        names = tt.getGlyphOrder()
        if names:
            glyph_count = len(set(names))
            glyph_names = frozenset(names)
    except Exception:
        pass

    # fvar → variable font axes
    axes: list[dict] = []
    try:
        fv = tt["fvar"]
        axes = [
            {
                "tag": a.axisTag,
                "min": round(a.minValue, 3),
                "default": round(a.defaultValue, 3),
                "max": round(a.maxValue, 3),
                "step": _axis_step(a.minValue, a.defaultValue, a.maxValue),
            }
            for a in fv.axes
        ]
    except Exception:
        pass

    # tables present
    try:
        tables = sorted(tt.reader.keys()) if tt.reader else []
    except Exception:
        tables = []

    cps = _read_cmap(tt)
    counts = _count_scripts(cps)
    ot_langs = sorted(_read_ot_langs(tt))
    main_tag, main_label = _resolve_main(counts, symbol, set(ot_langs))
    # "Coverage" is the number of code points inside the common repertoire
    # (the union of every script's sample ranges): summing the per-script
    # counts excludes PUA / format / unassigned code points that a cmap may
    # also map, so the count and the "% of the common repertoire" agree with
    # the per-script breakdown.
    coverage = sum(counts.values()) if cps else 0
    coverage_pct = round(coverage / _RANGE_TOTAL, 4) if coverage else 0.0
    sorted_cps = sorted(cps) if cps else []
    # Compact merged ranges of the covered characters, kept for the hyper
    # family's character union (faces of one design overlap heavily, so
    # summing per-script counts would double-count the shared repertoires).
    cps_ranges = _covered_ranges(sorted_cps)

    family = _name(tt, 16, 1) or os.path.basename(path)
    subfamily = _name(tt, 17, 2) or "Regular"

    return {
        "path": path,
        "file": os.path.basename(path),
        "ext": os.path.splitext(path)[1].lstrip(".").lower(),
        "face_index": index,
        "source": source,
        "family": family,
        "hyper_family": _hyper_family(family),
        "subfamily": subfamily,
        "full_name": _name(tt, 4) or f"{family} {subfamily}",
        "ps_name": _name(tt, 6) or "",
        "version": _name(tt, 5) or "",
        "copyright": _name(tt, 0) or "",
        "manufacturer": _name(tt, 8) or "",
        "designer": _name(tt, 9) or "",
        "designer_url": _name(tt, 11) or "",
        "license": _name(tt, 13) or "",
        "license_url": _name(tt, 14) or "",
        "trademark": _name(tt, 7) or "",
        "weight": weight,
        "width": width,
        "italic": italic,
        "symbol": symbol,
        "fs_type": fs_type,
        "panose": panose,
        "upem": upem,
        "glyphs": glyphs,
        "glyph_count": glyph_count,
        "_glyph_names": glyph_names,
        "created": created,
        "modified": modified,
        "variable": bool(axes),
        "axes": axes,
        "tables": tables,
        "file_size": os.path.getsize(path) if os.path.exists(path) else 0,
        "main_script": main_tag,
        "main_label": main_label,
        "coverage": coverage,
        "coverage_pct": coverage_pct,
        "scripts": _script_summary(counts, sorted_cps),
        "tags": _script_tags(counts, main_tag),
        "_counts": counts,
        "_cps_ranges": cps_ranges,
        "ot_langs": ot_langs,
        "ot_features": _read_ot_features(tt),
        "meta_langs": _read_name_langs(tt),
    }


def _scan_file(path: str, source: str, reuse_cache: bool = True) -> list[dict]:
    """Scan one file (may hold several TTC faces).  Cache-safe."""
    try:
        st = os.stat(path)
        key = (os.path.normcase(path), st.st_mtime_ns, st.st_size)
    except OSError:
        return []
    if reuse_cache and key in _cache:
        return _cache[key]

    entries: list[dict] = []
    faces = list(_iter_faces(path))
    for i, _tt in enumerate(faces):
        e = _face_entry(path, i, source)
        if e:
            entries.append(e)
        if i >= 64:
            break
    # Cache the entries WITHOUT the heavy per-face glyph-name sets — they are
    # only needed transiently to compute the hyper-family glyph unions (the
    # union RESULT is cached separately).  The returned entries keep the name
    # sets for this scan's aggregation pass.
    if entries:
        cached = []
        for e in entries:
            c = dict(e)
            c.pop("_glyph_names", None)
            cached.append(c)
        _cache[key] = cached
    return entries


# Cache of hyper-family glyph-name union sizes, keyed by the sorted tuple of
# member face signatures (normpath, mtime_ns, size, face_index).  Computing a
# union needs every member's glyph names (~0.5 GB transient on a cold scan),
# so the RESULT is cached and the heavy per-face name sets are freed after
# aggregation — warm scans never re-open the fonts.
_glyph_union_cache: dict[tuple, int] = {}


def _face_signature(f: dict) -> tuple:
    """Stable identity for one face: path + mtime + size + collection index."""
    try:
        st = os.stat(f["path"])
        return (os.path.normcase(f["path"]), st.st_mtime_ns, st.st_size, f.get("face_index") or 0)
    except OSError:
        return (os.path.normcase(f["path"]), -1, f.get("file_size") or 0, f.get("face_index") or 0)


def _read_glyph_names(path: str, index: int) -> frozenset:
    """Glyph names of a face, read from disk (fallback when a cached entry
    carries no name sets — e.g. first warm scan after an upgrade)."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tt = TTFont(path, fontNumber=index, lazy=True)
        return frozenset(tt.getGlyphOrder())
    except Exception:
        return frozenset()


def _apply_hyper_classification(faces: list[dict]) -> None:
    """Move the writing-system classification from the face to the hyper family.

    Every face of a hyper family is stamped with the SAME aggregated
    ``main_script`` / ``main_label`` / ``tags``, computed from the summed
    coverage of all its member faces — the classification unit is the hyper
    family, not the individual font family.  ``_counts`` is an internal field
    used for this aggregation (kept so cached entries stay reusable).
    """
    groups: dict[str, list[dict]] = {}
    for f in faces:
        groups.setdefault(f["hyper_family"], []).append(f)
    for members in groups.values():
        agg: dict[str, int] = {}
        for f in members:
            for tag, n in (f.get("_counts") or {}).items():
                agg[tag] = agg.get(tag, 0) + n
        langs: set[str] = set()
        for f in members:
            langs.update(f.get("ot_langs") or [])
        # A hyper family is a symbol family only if EVERY member is a pure
        # symbol font (e.g. Wingdings, Webdings); mixed groups like Segoe UI
        # keep their text classification.
        symbol = all(f.get("symbol") for f in members)
        main_tag, main_label = _resolve_main(agg, symbol, langs)
        tags = _script_tags(agg, main_tag)
        # Hyper-level counts (stamped identically on every member face):
        #  - scripts: distinct scripts with real coverage in the hyper family;
        #  - characters: the TRUE character union across member faces (shared
        #    code points count once) — summing per-script counts would
        #    double-count the huge overlapping repertoires of style variants
        #    (Microsoft YaHei's 6 faces each cover ~29.5k Han → a sum claims
        #    ~110k instead of the real ~30k);
        #  - glyphs: glyphs counted by glyph name.  For a multi-face family the
        #    count is the UNION of every member face's glyph names — multi-plane
        #    families ship one font per plane, each with its own glyphs, so the
        #    largest single face would badly under-count (TH-Tshyn: 61k vs a
        #    211k union).  The result is cached by member signature so warm
        #    scans don't re-read the fonts; the transient name sets are freed
        #    here (and never kept in the file cache).
        hyper_scripts = sum(1 for tag, n in agg.items() if n >= _TAG_MIN_COUNT)
        hyper_chars = _union_range_count([f.get("_cps_ranges") or [] for f in members])
        if len(members) > 1:
            sig = tuple(sorted(_face_signature(f) for f in members))
            union = _glyph_union_cache.get(sig)
            if union is None:
                merged: set = set()
                for f in members:
                    ns = f.get("_glyph_names")
                    if ns:
                        merged |= ns
                    else:
                        merged |= _read_glyph_names(f["path"], f.get("face_index") or 0)
                union = len(merged)
                _glyph_union_cache[sig] = union
            hyper_glyphs = union
        else:
            hyper_glyphs = max((f.get("glyph_count") or 0) for f in members)
        for f in members:
            f["main_script"] = main_tag
            f["main_label"] = main_label
            f["tags"] = tags
            f["hyper_scripts"] = hyper_scripts
            f["hyper_chars"] = hyper_chars
            f["hyper_glyphs"] = hyper_glyphs
            f.pop("_glyph_names", None)


def scan_fonts(extra_dirs: list[str] | None = None) -> list[dict]:
    """Enumerate every font face across the default directories plus any
    ``extra_dirs``.  Returns a flat list of face entries (grouping by family
    and script happens on the client)."""
    dirs = list(DEFAULT_DIRS)
    for d in extra_dirs or []:
        if d and os.path.isdir(d) and d not in dirs:
            dirs.append(d)

    out: list[dict] = []
    seen_paths: set[str] = set()
    for d in dirs:
        source = _source_label(d)
        if not os.path.isdir(d):
            continue
        try:
            files = sorted(f for f in os.listdir(d) if f.lower().endswith(EXTENSIONS))
        except OSError:
            continue
        for f in files:
            p = os.path.join(d, f)
            key = os.path.normcase(p)
            if key in seen_paths:
                continue
            seen_paths.add(key)
            out.extend(_scan_file(p, source))

    out.sort(key=lambda e: (e["family"].lower(), e["subfamily"].lower()))
    _apply_hyper_classification(out)
    return out


def clear_cache() -> None:
    _cache.clear()
    _glyph_union_cache.clear()
