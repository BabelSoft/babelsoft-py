"""Extended (XML-style) character properties — mirrors the C++ build.

Produces the ordered ``[label, value]`` property list and the name-aliases list
(``[type, alias]``) that the C++ ``CDialogXmlProperties`` renders from
``Unicode::GetXmlProperties()`` (a ``Property`` / ``Value`` table plus an
``Alias Type`` / ``Alias Value`` table parsed from ``<name-alias …/>``).

All data is parsed from the UCD tree (``data/unicode/<version>/ucd``).
"""

from __future__ import annotations

import functools

from babelsoft.unicode.core import Unicode
from babelsoft.unicode.extras import has_binary_property
from babelsoft.utils_.dirs import Dirs
from babelsoft.utils_.parser import TsvParser, TxtParser, line_has_content

UCD = Dirs.UCD


def _hex(cp: int) -> str:
    return f"{cp:04X}"


def _yes_no(b: bool) -> str:
    return "Yes" if b else "No"


# ── enumerated long-name maps (short code → long description) ─────────
# Labels match the C++ c/Unicode/Properties.h arrays.
GC_LONG = {
    "Lu": "Letter, Uppercase",
    "Ll": "Letter, Lowercase",
    "Lt": "Letter, Titlecase",
    "Lm": "Letter, Modifier",
    "Lo": "Letter, Other",
    "Mn": "Mark, Non-Spacing",
    "Mc": "Mark, Spacing Combining",
    "Me": "Mark, Enclosing",
    "Nd": "Number, Decimal",
    "Nl": "Number, Letter",
    "No": "Number, Other",
    "Pc": "Punctuation, Connector",
    "Pd": "Punctuation, Dash",
    "Ps": "Punctuation, Open",
    "Pe": "Punctuation, Close",
    "Pi": "Punctuation, Initial quote",
    "Pf": "Punctuation, Final quote",
    "Po": "Punctuation, Other",
    "Sm": "Symbol, Math",
    "Sc": "Symbol, Currency",
    "Sk": "Symbol, Modifier",
    "So": "Symbol, Other",
    "Zs": "Separator, Space",
    "Zl": "Separator, Line",
    "Zp": "Separator, Paragraph",
    "Cc": "Other, Control",
    "Cf": "Other, Format",
    "Cs": "Other, Surrogate",
    "Co": "Other, Private Use",
    "Cn": "Other, Not Assigned",
}
BIDI_LONG = {
    "L": "Left-to-Right",
    "LRE": "Left-to-Right Embedding",
    "LRO": "Left-to-Right Override",
    "R": "Right-to-Left",
    "AL": "Right-to-Left Arabic",
    "RLE": "Right-to-Left Embedding",
    "RLO": "Right-to-Left Override",
    "PDF": "Pop Directional Format",
    "EN": "European Number",
    "ES": "European Number Separator",
    "ET": "European Number Terminator",
    "AN": "Arabic Number",
    "CS": "Common Number Separator",
    "NSM": "Non-Spacing Mark",
    "BN": "Boundary Neutral",
    "B": "Paragraph Separator",
    "S": "Segment Separator",
    "WS": "Whitespace",
    "ON": "Other Neutrals",
    "LRI": "Left-To-Right Isolate",
    "RLI": "Right-To-Left Isolate",
    "FSI": "First Strong Isolate",
    "PDI": "Pop Directional Isolate",
}
LB_LONG = {
    "BK": "Mandatory Break",
    "CR": "Carriage Return",
    "LF": "Line Feed",
    "CM": "Attached Characters and Combining Marks",
    "NL": "Next Line",
    "SG": "Surrogates",
    "WJ": "Word Joiner",
    "ZW": "Zero Width Space",
    "GL": 'Non-breaking ("Glue")',
    "CB": "Contingent Break Opportunity",
    "SP": "Space",
    "B2": "Break Opportunity Before and After",
    "BA": "Break Opportunity After",
    "BB": "Break Opportunity Before",
    "HY": "Hyphen",
    "CL": "Closing Punctuation",
    "CP": "Closing Parenthesis",
    "EX": "Exclamation/Interrogation",
    "IN": "Inseparable",
    "NS": "Non Starter",
    "OP": "Opening Punctuation",
    "QU": "Ambiguous Quotation",
    "IS": "Infix Separator (Numeric)",
    "NU": "Numeric",
    "PO": "Postfix (Numeric)",
    "PR": "Prefix (Numeric)",
    "SY": "Symbols Allowing Breaks",
    "AI": "Ambiguous (Alphabetic or Ideographic)",
    "AL": "Ordinary Alphabetic and Symbol Characters",
    "H2": "Hangul LV Syllable",
    "H3": "Hangul LVT Syllable",
    "ID": "Ideographic",
    "JL": "Hangul L Jamo",
    "JV": "Hangul J Jamo",
    "JT": "Hangul T Jamo",
    "SA": "Complex Context (South East Asian)",
    "XX": "Unknown",
    "HL": "Hebrew Letter",
    "CJ": "Conditional Japanese Starter",
    "RI": "Regional Indicator",
    "ZWJ": "Zero Width Joiner",
    "EB": "Emoji Base",
    "EM": "Emoji Modifier",
}
CCC_LONG = {
    "0": "Not Reordered",
    "1": "Overlay",
    "6": "Han Reading",
    "7": "Nukta",
    "8": "Kana Voicing",
    "9": "Virama",
    "200": "Attached Below Left",
    "202": "Attached Below",
    "204": "Attached Bottom Right",
    "208": "Attached Left",
    "210": "Attached Right",
    "212": "Attached Top Left",
    "214": "Attached Above",
    "216": "Attached Above Right",
    "218": "Below Left",
    "220": "Below",
    "222": "Below Right",
    "224": "Left",
    "226": "Right",
    "228": "Above Left",
    "230": "Above",
    "232": "Above Right",
    "233": "Double Below",
    "234": "Double Above",
    "240": "Iota Subscript",
}
EAW_LONG = {
    "N": "Neutral",
    "A": "Ambiguous",
    "H": "Halfwidth",
    "W": "Wide",
    "F": "Fullwidth",
    "Na": "Narrow",
}
JT_LONG = {
    "U": "Non Joining",
    "C": "Join Causing",
    "D": "Dual Joining",
    "L": "Left Joining",
    "R": "Right Joining",
    "T": "Transparent",
}
HST_LONG = {
    "L": "Leading Jamo",
    "V": "Vowel Jamo",
    "T": "Trailing Jamo",
    "LV": "LV Syllable",
    "LVT": "LVT Syllable",
    "NA": "Not Applicable",
}
GCB_LONG = {
    "Other": "Other",
    "CR": "Carriage Return",
    "LF": "Line Feed",
    "Control": "Control",
    "Extend": "Extend",
    "ZWJ": "ZWJ",
    "Regional_Indicator": "Regional Indicator",
    "Prepend": "Prepend",
    "SpacingMark": "Spacing Mark",
    "L": "Hangul Syllable Type L",
    "V": "Hangul Syllable Type V",
    "T": "Hangul Syllable Type T",
    "LV": "Hangul Syllable Type LV",
    "LVT": "Hangul Syllable Type LVT",
    "E_Base": "Emoji Base",
    "E_Modifier": "Emoji Modifier",
    "Glue_After_Zwj": "Glue After ZWJ",
    "E_Base_GAZ": "Emoji Base Glue After ZWJ",
    "EBG": "Emoji Base Glue After ZWJ",
}
WB_LONG = {
    "Other": "Other",
    "CR": "CR",
    "LF": "LF",
    "Newline": "Newline",
    "Extend": "Extend",
    "ZWJ": "ZWJ",
    "Regional_Indicator": "Regional Indicator",
    "Format": "Format",
    "Katakana": "Katakana",
    "Hebrew_Letter": "Hebrew Letter",
    "ALetter": "ALetter",
    "Single_Quote": "Single Quote",
    "Double_Quote": "Double Quote",
    "MidNumLet": "MidNumLet",
    "MidLetter": "MidLetter",
    "MidNum": "MidNum",
    "Numeric": "Numeric",
    "ExtendNumLet": "ExtendNumLet",
    "WSegSpace": "WSegSpace",
}
SB_LONG = {
    "Other": "Other",
    "ATerm": "ATerm",
    "Close": "Close",
    "CR": "Carriage Return",
    "Extend": "Extend",
    "Format": "Format",
    "OLetter": "OLetter",
    "LF": "Line Feed",
    "Lower": "Lower",
    "Numeric": "Numeric",
    "SContinue": "SContinue",
    "Sep": "Separator",
    "SP": "SPace",
    "STerm": "Sentence Terminal",
    "Upper": "Upper",
}
DT_LONG = {
    "None_": "None",
    "None": "None",
    "Canonical": "Canonical",
    "Font": "Font",
    "NoBreak": "No Break",
    "Initial": "Initial",
    "Medial": "Medial",
    "Final": "Final",
    "Isolated": "Isolated",
    "Circle": "Circle",
    "Super": "Super",
    "Sub": "Sub",
    "Vertical": "Vertical",
    "Wide": "Wide",
    "Narrow": "Narrow",
    "Small": "Small",
    "Square": "Square",
    "Fraction": "Fraction",
    "Compat": "Compatibility",
}
NT_LONG = {"None": "None", "Decimal": "Decimal Digit", "Digit": "Digit", "Numeric": "Numeric"}
VO_LONG = {
    "U": "Upright",
    "R": "Rotated",
    "Tu": "Transformed typographically, with fallback to Upright",
    "Tr": "Transformed typographically, with fallback to Rotated",
}


def _fmt(short: str, long_map: dict[str, str]) -> str:
    """'short [long]' when they differ, else 'short' (matches C++ formatting)."""
    long = long_map.get(short, "")
    if long and long != short:
        return f"{short} [{long}]"
    return short


# ── range-file helpers ────────────────────────────────────────────────


def _load_ranges(filename: str, value_col: int = 1) -> list[tuple[int, int, str]]:
    table: list[tuple[int, int, str]] = []
    for line in filter(line_has_content, TxtParser.get_txt(UCD / filename)):
        parts = line.split(";")
        if len(parts) < value_col + 1:
            continue
        val = parts[value_col].strip().split("#")[0].strip()
        rp = parts[0].strip()
        s, e = (int(rp.split("..")[0], 16), int(rp.split("..")[1], 16)) if ".." in rp else (int(rp, 16), int(rp, 16))
        table.append((s, e, val))
    table.sort()
    return table


def _lookup(table: list[tuple[int, int, str]], cp: int) -> str:
    lo, hi = 0, len(table) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        s, e, v = table[mid]
        if cp < s:
            hi = mid - 1
        elif cp > e:
            lo = mid + 1
        else:
            return v
    return ""


# ── individual property parsers ──────────────────────────────────────


def _is_noncharacter(cp: int) -> bool:
    return (0xFDD0 <= cp <= 0xFDEF) or (cp & 0xFFFF) in (0xFFFE, 0xFFFF)


def _is_private_use(cp: int) -> bool:
    return (0xE000 <= cp <= 0xF8FF) or (0xF0000 <= cp <= 0xFFFFD) or (0x100000 <= cp <= 0x10FFFD)


def _codepoint_type(cp: int) -> str:
    if Unicode.is_surrogate(cp):
        return "Surrogate"
    if _is_noncharacter(cp):
        return "Noncharacter"
    if _is_private_use(cp):
        return "Private-Use"
    if cp in Unicode._assigned_codepoints():
        return "Character"
    return "Reserved"


@functools.lru_cache(maxsize=1)
def _jamo_short_map() -> dict[int, str]:
    m: dict[int, str] = {}
    for line in filter(line_has_content, TxtParser.get_txt(UCD / "Jamo.txt")):
        parts = line.split(";")
        if len(parts) < 4:
            continue
        try:
            cp = int(parts[0].strip(), 16)
        except ValueError:
            continue
        short = parts[3].strip().split("#")[0].strip()
        if short:
            m[cp] = short
    return m


@functools.lru_cache(maxsize=1)
def _script_name_map() -> dict[str, str]:
    """{ISO 15924 code: English name} from data/scripts/iso15924.tsv."""
    m: dict[str, str] = {}
    for row in TsvParser.get_tsv(Dirs.DATA / "scripts" / "iso15924.tsv"):
        if len(row) >= 3:
            m[row[0].strip()] = row[2].strip()
    return m


def _script_value(cp: int) -> str:
    return Unicode.get_script(cp)


@functools.lru_cache(maxsize=1)
def _special_casing() -> dict[int, dict[str, list[int]]]:
    m: dict[int, dict[str, list[int]]] = {}
    for line in filter(line_has_content, TxtParser.get_txt(UCD / "SpecialCasing.txt")):
        parts = line.split(";")
        if len(parts) < 4:
            continue
        try:
            cp = int(parts[0].strip(), 16)
        except ValueError:
            continue
        d = m.setdefault(cp, {})
        d["lower"] = [int(x, 16) for x in parts[1].strip().split()]
        d["title"] = [int(x, 16) for x in parts[2].strip().split()]
        d["upper"] = [int(x, 16) for x in parts[3].strip().split("#")[0].split()]
    return m


@functools.lru_cache(maxsize=1)
def _casefold_map() -> dict[int, dict[str, list[int]]]:
    m: dict[int, dict[str, list[int]]] = {}
    for line in filter(line_has_content, TxtParser.get_txt(UCD / "CaseFolding.txt")):
        parts = line.split(";")
        if len(parts) < 3:
            continue
        try:
            cp = int(parts[0].strip(), 16)
        except ValueError:
            continue
        status = parts[1].strip()
        m.setdefault(cp, {})[status] = [int(x, 16) for x in parts[2].strip().split("#")[0].split()]
    return m


def _full_mapping(cp: int, which: str) -> str:
    sc = _special_casing().get(cp)
    if sc and sc.get(which):
        return " ".join(_hex(x) for x in sc[which])
    simple = {
        "upper": Unicode.get_simple_uppercase(cp),
        "lower": Unicode.get_simple_lowercase(cp),
        "title": Unicode.get_simple_titlecase(cp),
    }[which]
    return _hex(simple)


def _casefold_simple(cp: int) -> int:
    cf = _casefold_map().get(cp, {})
    for st in ("C", "S"):
        seq = cf.get(st)
        if seq and len(seq) == 1:
            return seq[0]
    return cp


def _casefold_full(cp: int) -> list[int]:
    cf = _casefold_map().get(cp, {})
    return cf.get("F") or cf.get("C") or [cp]


@functools.lru_cache(maxsize=1)
def _composition_exclusions() -> set[int]:
    s: set[int] = set()
    for line in filter(line_has_content, TxtParser.get_txt(UCD / "CompositionExclusions.txt")):
        rp = line.split("#", 1)[0].strip()
        try:
            s.add(int(rp, 16))
        except ValueError:
            continue
    return s


@functools.lru_cache(maxsize=1)
def _derived_norm_ranges() -> dict[str, list[tuple[int, int, str]]]:
    out: dict[str, list[tuple[int, int, str]]] = {}
    for line in filter(line_has_content, TxtParser.get_txt(UCD / "DerivedNormalizationProps.txt")):
        parts = line.split(";")
        if len(parts) < 2:
            continue
        prop = parts[1].split("#")[0].strip()
        # Binary properties (XO_*, CWKCF, Full_Composition_Exclusion, …) have
        # no value column — presence alone means the property holds.
        val = ""
        if len(parts) >= 3:
            val = parts[2].strip().split("#")[0].strip()
        rp = parts[0].strip()
        s, e = (int(rp.split("..")[0], 16), int(rp.split("..")[1], 16)) if ".." in rp else (int(rp, 16), int(rp, 16))
        out.setdefault(prop, []).append((s, e, val))
    for prop, ranges in out.items():
        ranges.sort()
    return out


def _dn(cp: int, prop: str) -> str:
    for s, e, v in _derived_norm_ranges().get(prop, []):
        if s <= cp <= e:
            return v
        if cp < s:
            break
    return ""


def _dn_has(cp: int, prop: str) -> bool:
    """True if cp is covered by a DerivedNormalizationProps binary property
    (these rows have no value column — presence means the property holds)."""
    for s, e, _v in _derived_norm_ranges().get(prop, []):
        if s <= cp <= e:
            return True
        if cp < s:
            break
    return False


def _dn_seq(cp: int, prop: str) -> list[int] | None:
    v = _dn(cp, prop)
    if not v:
        return None
    try:
        return [int(x, 16) for x in v.split()]
    except ValueError:
        return None


def _full_comp_exclusion(cp: int) -> bool:
    return cp in _composition_exclusions() or _dn_has(cp, "Full_Composition_Exclusion")


def _nfkc_casefold(cp: int) -> str:
    seq = _dn_seq(cp, "NFKC_CF")
    if seq:
        return " ".join(_hex(x) for x in seq)
    s = "".join(chr(x) for x in _casefold_full(cp))
    return " ".join(_hex(ord(c)) for c in Unicode.get_nfkc(s)) or _hex(cp)


def _qc(cp: int, prop: str) -> str:
    # Unlisted codepoints default to "Yes" for the quick-check properties.
    return {"Y": "Yes", "N": "No", "M": "Maybe"}.get(_dn(cp, prop), "Yes")


def _binary(cp: int, prop: str) -> str:
    # Changes_When_NFKC_Casefolded is a DerivedNormalizationProps binary
    # property (data lines use the full property name).
    if prop == "Changes_When_NFKC_Casefolded":
        return _yes_no(_dn_has(cp, "Changes_When_NFKC_Casefolded"))
    return _yes_no(has_binary_property(cp, prop))


def _iso_comment(cp: int) -> str:
    for e in Unicode._unicodedata():
        if e["cp"] == cp:
            return e["iso"].strip()
    return ""


def _script_extensions(cp: int) -> str:
    ext = Unicode.get_script_extensions(cp)
    if not ext:
        # Script_Extensions defaults to the base script.
        code = Unicode.get_script_iso_code(Unicode.get_script(cp)) or Unicode.get_script(cp)
        ext = [code]
    return " ".join(ext)


# ── extended property list (C++ XML attribute order) ─────────────────


def extended_properties(cp: int) -> list[list[str]]:
    """Ordered [label, value] list matching the C++ GetXmlProperties output."""
    rows: list[list[str]] = []
    add = lambda label, value: rows.append([label, value])

    add("Code Point Type", _codepoint_type(cp))
    add("Code Point", _hex(cp))
    add("Age", Unicode.get_character_age(cp) or "Unassigned")
    add("Name", Unicode.get_character_name(cp))
    add("Jamo Short Name", _jamo_short_map().get(cp, ""))
    add("General Category", _fmt(Unicode.get_general_category(cp).name, GC_LONG))
    add("Canonical Combining Class", _fmt(str(Unicode.get_canonical_combining_class(cp)), CCC_LONG))
    dt = Unicode.get_decomposition_type(cp).name
    if dt == "None_":
        dt = "None"
    add("Decomposition Type", _fmt(dt, DT_LONG))
    add("Decomposition Mapping", Unicode.get_decomposition(cp).replace("<", "").replace(">", "") or _hex(cp))
    nt = Unicode.get_numeric_type(cp) or "None"
    add("Numeric Type", _fmt(nt, NT_LONG))
    add("Numeric Value", Unicode.get_numeric_value(cp) or "NaN")
    add("Bidi Class", _fmt(Unicode.get_bidi_class(cp).name, BIDI_LONG))
    add(
        "Bidi Paired Bracket Type",
        {"o": "Open", "c": "Close", "n": "None"}.get(Unicode.get_bidi_bracket_type(cp), "None"),
    )
    add("Bidi Paired Bracket", _hex(Unicode.get_bidi_paired_bracket(cp)))
    add("Bidi Mirrored", _yes_no(Unicode.get_bidi_mirrored(cp)))
    add("Bidi Mirroring Glyph", _hex(Unicode.get_bidi_mirroring_glyph(cp)) if cp in Unicode._mirroring_map() else "")
    add("Simple Uppercase Mapping", _hex(Unicode.get_simple_uppercase(cp)))
    add("Simple Lowercase Mapping", _hex(Unicode.get_simple_lowercase(cp)))
    add("Simple Titlecase Mapping", _hex(Unicode.get_simple_titlecase(cp)))
    add("Uppercase Mapping", _full_mapping(cp, "upper"))
    add("Lowercase Mapping", _full_mapping(cp, "lower"))
    add("Titlecase Mapping", _full_mapping(cp, "title"))
    add("Simple Case Folding", _hex(_casefold_simple(cp)))
    add("Case Folding", " ".join(_hex(x) for x in _casefold_full(cp)))
    add("Joining Type", _fmt(Unicode.get_joining_type(cp).name, JT_LONG))
    add("Joining Group", Unicode.get_joining_group(cp).replace("_", " ") or "No Joining Group")
    add("East Asian Width", _fmt(Unicode.get_east_asian_width(cp).name, EAW_LONG))
    add("Line Break", _fmt(Unicode.get_line_break(cp).name, LB_LONG))
    sc = _script_value(cp)
    sc_code = Unicode.get_script_iso_code(sc) or sc
    add("Script", _fmt(sc_code, {sc_code: sc}))
    add("Script Extensions", _script_extensions(cp))

    # Binary properties (block 1) + Hangul Syllable Type (C++ XML order).
    for prop, label in _BINARIES_A:
        add(label, _binary(cp, prop))
    add("Hangul Syllable Type", _fmt(_lookup(_hst_table(), cp), HST_LONG) or "NA [Not Applicable]")
    for prop, label in _BINARIES_B:
        add(label, _binary(cp, prop))

    add("Grapheme Cluster Break", _fmt(_lookup(_gcb_table(), cp) or "Other", GCB_LONG))
    add("Word Break", _fmt(_lookup(_wb_table(), cp) or "Other", WB_LONG))
    add("Sentence Break", _fmt(_lookup(_sb_table(), cp) or "Other", SB_LONG))

    add("Composition Exclusion", _yes_no(cp in _composition_exclusions()))
    add("Full Composition Exclusion", _yes_no(_full_comp_exclusion(cp)))
    add("NFC Quick Check", _qc(cp, "NFC_QC"))
    add("NFD Quick Check", _qc(cp, "NFD_QC"))
    add("NFKC Quick Check", _qc(cp, "NFKC_QC"))
    add("NFKD Quick Check", _qc(cp, "NFKD_QC"))
    add("Expands On NFC", _yes_no(_dn(cp, "XO_NFC") == "Y"))
    add("Expands On NFD", _yes_no(_dn(cp, "XO_NFD") == "Y"))
    add("Expands On NFKC", _yes_no(_dn(cp, "XO_NFKC") == "Y"))
    add("Expands On NFKD", _yes_no(_dn(cp, "XO_NFKD") == "Y"))
    seq = _dn_seq(cp, "FC_NFKC")
    add("FC NFKC Closure", " ".join(_hex(x) for x in seq) if seq else _hex(cp))

    for prop, label in _BINARIES_C:
        add(label, _binary(cp, prop))

    add("NFKC Casefold", _nfkc_casefold(cp))
    add("Indic Syllabic Category", _lookup(_insc_table(), cp).replace("_", " ") or "Other")
    add("Indic Positional Category", _lookup(_inpc_table(), cp).replace("_", " ") or "NA")
    add("Prepended Concatenation Mark", _yes_no(has_binary_property(cp, "Prepended_Concatenation_Mark")))
    add("Vertical Orientation", _fmt(Unicode.get_vertical_orientation(cp), VO_LONG))
    add("Regional Indicator", _yes_no(has_binary_property(cp, "Regional_Indicator")))
    add("Block", Unicode.get_block_name(cp))
    add("ISO Comment", _iso_comment(cp))
    add("Unicode 1 Name", Unicode.get_unicode1_name(cp))
    for prop, label in _BINARIES_D:
        add(label, _binary(cp, prop))
    add("NFKC Simple Casefold", _hex(_casefold_simple(cp)))
    for prop, label in _BINARIES_E:
        add(label, _binary(cp, prop))
    add("Indic Conjunct Break", _lookup(_incb_table(), cp).replace("_", " ") or "None")

    return rows


def name_aliases(cp: int) -> list[list[str]]:
    """[[type, alias], ...] — from NameAliases.txt, in file order."""
    return [[t, a] for a, t in Unicode._name_alias_map_by_type().get(cp, [])]


# Binary property blocks, in the order they appear in the C++ XML output.
_BINARIES_A = [
    ("Dash", "Dash"),
    ("White_Space", "White Space"),
    ("Hyphen", "Hyphen"),
    ("Quotation_Mark", "Quotation Mark"),
    ("Radical", "Radical"),
    ("Ideographic", "Ideographic"),
    ("Unified_Ideograph", "Unified Ideograph"),
    ("IDS_Binary_Operator", "IDS Binary Operator"),
    ("IDS_Trinary_Operator", "IDS Trinary Operator"),
]
_BINARIES_B = [
    ("Default_Ignorable_Code_Point", "Default Ignorable Code Point"),
    ("Other_Default_Ignorable_Code_Point", "Other Default Ignorable Code Point"),
    ("Alphabetic", "Alphabetic"),
    ("Other_Alphabetic", "Other Alphabetic"),
    ("Uppercase", "Uppercase"),
    ("Other_Uppercase", "Other Uppercase"),
    ("Lowercase", "Lowercase"),
    ("Other_Lowercase", "Other Lowercase"),
    ("Math", "Math"),
    ("Other_Math", "Other Math"),
    ("Hex_Digit", "Hex Digit"),
    ("ASCII_Hex_Digit", "ASCII Hex Digit"),
    ("Noncharacter_Code_Point", "Noncharacter Code Point"),
    ("Variation_Selector", "Variation Selector"),
    ("Bidi_Control", "Bidi Control"),
    ("Join_Control", "Join Control"),
    ("Grapheme_Base", "Grapheme Base"),
    ("Grapheme_Extend", "Grapheme Extend"),
    ("Other_Grapheme_Extend", "Other Grapheme Extend"),
    ("Grapheme_Link", "Grapheme Link"),
    ("Sentence_Terminal", "Sentence Terminal"),
    ("Extender", "Extender"),
    ("Terminal_Punctuation", "Terminal Punctuation"),
    ("Diacritic", "Diacritic"),
    ("Deprecated", "Deprecated"),
    ("ID_Start", "ID Start"),
    ("Other_ID_Start", "Other ID Start"),
    ("XID_Start", "XID Start"),
    ("ID_Continue", "ID Continue"),
    ("Other_ID_Continue", "Other ID Continue"),
    ("XID_Continue", "XID Continue"),
    ("Soft_Dotted", "Soft Dotted"),
    ("Logical_Order_Exception", "Logical Order Exception"),
    ("Pattern_White_Space", "Pattern White Space"),
    ("Pattern_Syntax", "Pattern Syntax"),
]
_BINARIES_C = [
    ("Case_Ignorable", "Case Ignorable"),
    ("Cased", "Cased"),
    ("Changes_When_Casefolded", "Changes When Casefolded"),
    ("Changes_When_Casemapped", "Changes When Casemapped"),
    ("Changes_When_NFKC_Casefolded", "Changes When NFKC Casefolded"),
    ("Changes_When_Lowercased", "Changes When Lowercased"),
    ("Changes_When_Titlecased", "Changes When Titlecased"),
    ("Changes_When_Uppercased", "Changes When Uppercased"),
]
_BINARIES_D = [
    ("Emoji", "Emoji"),
    ("Emoji_Presentation", "Emoji Presentation"),
    ("Emoji_Modifier", "Emoji Modifier"),
    ("Emoji_Modifier_Base", "Emoji Base"),
    ("Emoji_Component", "Emoji Component"),
    ("Extended_Pictographic", "Extended Pictographic"),
]
_BINARIES_E = [
    ("ID_Compat_Math_Start", "ID Compatibility Math Start"),
    ("ID_Compat_Math_Continue", "ID Compatibility Math Continue"),
    ("IDS_Unary_Operator", "IDS Unary Operator"),
]


@functools.lru_cache(maxsize=1)
def _hst_table():
    return _load_ranges("HangulSyllableType.txt")


@functools.lru_cache(maxsize=1)
def _gcb_table():
    return _load_ranges("auxiliary/GraphemeBreakProperty.txt")


@functools.lru_cache(maxsize=1)
def _wb_table():
    return _load_ranges("auxiliary/WordBreakProperty.txt")


@functools.lru_cache(maxsize=1)
def _sb_table():
    return _load_ranges("auxiliary/SentenceBreakProperty.txt")


@functools.lru_cache(maxsize=1)
def _insc_table():
    return _load_ranges("IndicSyllabicCategory.txt")


@functools.lru_cache(maxsize=1)
def _inpc_table():
    return _load_ranges("IndicPositionalCategory.txt")


@functools.lru_cache(maxsize=1)
def _incb_table():
    # IndicConjunctBreak.txt is not shipped with every UCD tree — degrade to [].
    if not (UCD / "IndicConjunctBreak.txt").exists():
        return []
    return _load_ranges("IndicConjunctBreak.txt")
