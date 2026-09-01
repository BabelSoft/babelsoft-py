"""Extra per-character data for the Character Properties dialog.

All data-driven from the UCD (reuses the ``data/unicode/<version>/ucd`` tree):

* **Binary properties** — PropList.txt + DerivedCoreProperties.txt + emoji-data.txt
* **Notes / Aliases / Cross-References** — NamesList.txt (``=`` aliases, ``*`` notes,
  ``x`` cross-references — exactly like the C++ ``GetNamesListAlias/Note/XRef``)
* **Standardized variation sequences** — StandardizedVariants.txt
* **Emoji variation sequences** — emoji/emoji-variation-sequences.txt
* **Named sequences** — NamedSequences.txt
"""

from __future__ import annotations

import functools
import re

from babelsoft.utils_.dirs import Dirs
from babelsoft.utils_.parser import TxtParser, line_has_content

# ── Binary properties ────────────────────────────────────────────────


@functools.lru_cache(maxsize=1)
def _binary_prop_ranges() -> dict[str, list[tuple[int, int]]]:
    props: dict[str, list[tuple[int, int]]] = {}
    for fname in ("PropList.txt", "DerivedCoreProperties.txt", "emoji/emoji-data.txt"):
        for line in filter(line_has_content, TxtParser.get_txt(Dirs.UCD / fname)):
            parts = line.split(";")
            if len(parts) < 2:
                continue
            prop = parts[1].strip().split("#")[0].strip()
            rp = parts[0].strip()
            if ".." in rp:
                s_str, e_str = rp.split("..")
                s, e = int(s_str, 16), int(e_str, 16)
            else:
                s = e = int(rp, 16)
            props.setdefault(prop, []).append((s, e))
    return props


def has_binary_property(cp: int, prop: str) -> bool:
    ranges = _binary_prop_ranges().get(prop, [])
    lo, hi = 0, len(ranges) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        s, e = ranges[mid]
        if cp < s:
            hi = mid - 1
        elif cp > e:
            lo = mid + 1
        else:
            return True
    return False


# Core binary properties shown in the dialog (mirrors C++ StrCoreProperties).
BINARY_PROPS: tuple[str, ...] = (
    "Dash",
    "Hyphen",
    "Quotation_Mark",
    "Terminal_Punctuation",
    "Other_Math",
    "Hex_Digit",
    "ASCII_Hex_Digit",
    "Other_Alphabetic",
    "Ideographic",
    "Diacritic",
    "Extender",
    "Other_Lowercase",
    "Other_Uppercase",
    "Noncharacter_Code_Point",
    "Default_Ignorable_Code_Point",
    "Deprecated",
    "Soft_Dotted",
    "Logical_Order_Exception",
    "Other_Grapheme_Extend",
    "IDS_Binary_Operator",
    "IDS_Trinary_Operator",
    "Radical",
    "Unified_Ideograph",
    "Pattern_Syntax",
    "Pattern_White_Space",
    "Variation_Selector",
    "Math",
    "Alphabetic",
    "Lowercase",
    "Uppercase",
    "Cased",
    "Case_Ignorable",
    "Changes_When_Lowercased",
    "Changes_When_Uppercased",
    "Changes_When_Titlecased",
    "Changes_When_Casefolded",
    "Changes_When_Casemapped",
    "ID_Start",
    "ID_Continue",
    "XID_Start",
    "XID_Continue",
    "Emoji",
    "Emoji_Presentation",
    "Emoji_Modifier",
    "Emoji_Modifier_Base",
    "Emoji_Component",
    "Extended_Pictographic",
    "Regional_Indicator",
    "Prepended_Concatenation_Mark",
    "White_Space",
    "Bidi_Control",
    "Join_Control",
)


def binary_properties(cp: int) -> list[str]:
    """List of binary properties that hold for a codepoint."""
    return [p for p in BINARY_PROPS if has_binary_property(cp, p)]


# ── Notes / Aliases / Cross-References (NamesList.txt) ───────────────

_ENTRY_RE = re.compile(r"^([0-9A-F]{4,6})\s+")


@functools.lru_cache(maxsize=1)
def _nameslist() -> dict[int, dict[str, list[str]]]:
    result: dict[int, dict[str, list[str]]] = {}
    cur: int | None = None
    for line in TxtParser.get_txt(Dirs.UCD / "NamesList.txt"):
        s = line.rstrip("\n")
        m = _ENTRY_RE.match(s)
        if m:
            cur = int(m.group(1), 16)
            result.setdefault(cur, {"aliases": [], "notes": [], "xrefs": []})
            continue
        if cur is None:
            continue
        t = s.lstrip()
        if t.startswith("="):
            result[cur]["aliases"].append(t[1:].strip())
        elif t.startswith("*"):
            result[cur]["notes"].append(t[1:].strip())
        elif t.startswith("x"):
            result[cur]["xrefs"].append(t[1:].strip())
    return result


def nameslist(cp: int) -> dict[str, list[str]]:
    """NamesList annotations: {'aliases': [...], 'notes': [...], 'xrefs': [...]}."""
    return _nameslist().get(cp, {"aliases": [], "notes": [], "xrefs": []})


# ── Standardized variation sequences ─────────────────────────────────


@functools.lru_cache(maxsize=1)
def _std_variants() -> dict[int, list[tuple[int, str]]]:
    result: dict[int, list[tuple[int, str]]] = {}
    for line in filter(line_has_content, TxtParser.get_txt(Dirs.UCD / "StandardizedVariants.txt")):
        parts = line.split(";")
        if len(parts) < 2:
            continue
        cps = parts[0].strip().split()
        if len(cps) < 2:
            continue
        try:
            base, vs = int(cps[0], 16), int(cps[1], 16)
        except ValueError:
            continue
        result.setdefault(base, []).append((vs, parts[1].strip()))
    return result


def standardized_variants(cp: int) -> list[tuple[int, str]]:
    """List of (variation-selector, description) for a base codepoint."""
    return _std_variants().get(cp, [])


# ── Emoji variation sequences ────────────────────────────────────────


@functools.lru_cache(maxsize=1)
def _emoji_variants() -> dict[int, list[tuple[int, str]]]:
    result: dict[int, list[tuple[int, str]]] = {}
    for line in filter(line_has_content, TxtParser.get_txt(Dirs.UCD / "emoji" / "emoji-variation-sequences.txt")):
        parts = line.split(";")
        if len(parts) < 2:
            continue
        cps = parts[0].strip().split()
        if len(cps) < 2:
            continue
        try:
            base, vs = int(cps[0], 16), int(cps[1], 16)
        except ValueError:
            continue
        result.setdefault(base, []).append((vs, parts[1].strip()))
    return result


def emoji_variation_sequences(cp: int) -> list[tuple[int, str]]:
    """List of (variation-selector, 'text style' | 'emoji style') for a base."""
    return _emoji_variants().get(cp, [])


# ── Named sequences ──────────────────────────────────────────────────


@functools.lru_cache(maxsize=1)
def _named_sequences() -> dict[tuple[int, ...], str]:
    result: dict[tuple[int, ...], str] = {}
    for line in filter(line_has_content, TxtParser.get_txt(Dirs.UCD / "NamedSequences.txt")):
        name, sep, cps_str = line.partition(";")
        if not sep:
            continue
        try:
            cps = tuple(int(x, 16) for x in cps_str.split())
        except ValueError:
            continue
        if cps:
            result[cps] = name.strip()
    return result


def named_sequences_for(cp: int) -> list[tuple[str, tuple[int, ...]]]:
    """Named sequences whose first element is this codepoint.

    Returns [(name, codepoints), ...] — e.g. U+0023 → ('KEYCAP NUMBER SIGN', (0x23, 0xFE0F, 0x20E3)).
    """
    return [(name, cps) for cps, name in _named_sequences().items() if cps and cps[0] == cp]
