"""Core Unicode classes — ported from c/Unicode/.

CodePoint, Block, and the Unicode class with all property lookups.
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass

from src.unicode.enums import (
    BidiClass,
    DecompositionType,
    EastAsianWidth,
    GeneralCategory,
    JoiningType,
    LineBreak,
)
from src.utils_.dirs import Dirs
from src.utils_.parser import TxtParser, line_has_content

UCD = Dirs.UCD


# ═══════════════════════════════════════════════════════════════════════
#  CodePoint
# ═══════════════════════════════════════════════════════════════════════


class CodePoint(int):
    """Unicode codepoint (0x0000–0x10FFFF)."""

    def __repr__(self) -> str:
        return f"0x{self:04X}"

    def to_unicode(self) -> str:
        return f"U+{self:04X}"

    def __new__(cls, value: int | str):
        if isinstance(value, str):
            codepoint = cls.from_(value)
            if codepoint is None:
                raise ValueError(f"Invalid codepoint: {value}")
            value = int(codepoint)
        if not isinstance(value, int):
            raise TypeError(f"CodePoint value must be int or str, not {type(value).__name__}")
        if value < 0 or value > 0x10FFFF:
            raise ValueError(f"Invalid codepoint: {value}")
        return int.__new__(cls, value)

    @classmethod
    def from_(cls, value: int | str | CodePoint | None = None) -> CodePoint | None:
        if not value:
            return None
        if isinstance(value, int):
            return cls(value)
        value = value.strip()
        if len(value) == 1:
            return cls(ord(value))
        if value.upper().startswith("U+"):
            value = value[2:]
        if value.lower().startswith("0x"):
            value = value[2:]
        if re.fullmatch(r"[0-9A-Fa-f]{1,6}", value):
            return cls(int(value, 16))
        return None


# ═══════════════════════════════════════════════════════════════════════
#  Block
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class Block:
    start: CodePoint
    end: CodePoint
    name: str

    def __repr__(self) -> str:
        return f'Block("{self.name}", {self.start:#06X}..{self.end:#06X})'


# ═══════════════════════════════════════════════════════════════════════
#  Unicode class — ported from c/Unicode/Unicode.h
# ═══════════════════════════════════════════════════════════════════════


class Unicode:
    """Static Unicode property lookups and constants — mirrors C++ Unicode class."""

    # ── Constants ────────────────────────────────────────────────────

    # Special characters
    BACKSPACE = 0x0008
    DELETE = 0x007F
    NEL = 0x0085
    TAB = 0x0009
    SPACE = 0x0020
    NBSP = 0x00A0
    ZWSP = 0x200B
    ZWNJ = 0x200C
    ZWJ = 0x200D
    NNBSP = 0x202F
    IDEOGRAPHIC_SPACE = 0x3000
    LINE_SEPARATOR = 0x2028
    PARA_SEPARATOR = 0x2029
    LINE_FEED = 0x000A
    CARRIAGE_RETURN = 0x000D
    REPLACEMENT_CHAR = 0xFFFD
    BYTE_ORDER_MARK = 0xFEFF
    WHITE_SQUARE = 0x25A1

    # Surrogates
    SUR_HIGH_START = 0xD800
    SUR_HIGH_END = 0xDBFF
    SUR_LOW_START = 0xDC00
    SUR_LOW_END = 0xDFFF

    # Limits
    MAX_16 = 0xFFFF
    MAX_32 = 0x10FFFF
    OVERFLOW_16 = 0x10000

    # Variation selectors
    VS_MIN = 0xFE00
    VS_MAX = 0xFE0F
    IVS_MIN = 0xE0100

    # Planes
    TOTAL_PLANES = 17
    CODE_POINTS_PER_PLANE = 65536

    # CJK
    CJK_START = 0x4E00
    CJK_LAST = 0x9FFF
    CJK_A_START = 0x3400
    CJK_A_LAST = 0x4DBF
    CJK_B_START = 0x20000
    CJK_B_LAST = 0x2A6DF
    CJK_C_START = 0x2A700
    CJK_C_LAST = 0x2B73F
    CJK_D_START = 0x2B740
    CJK_D_LAST = 0x2B81D
    CJK_E_START = 0x2B820
    CJK_E_LAST = 0x2CEAD
    CJK_F_START = 0x2CEB0
    CJK_F_LAST = 0x2EBE0
    CJK_G_START = 0x30000
    CJK_G_LAST = 0x3134A
    CJK_H_START = 0x31350
    CJK_H_LAST = 0x323AF
    CJK_I_START = 0x2EBF0
    CJK_I_LAST = 0x2EE5D
    CJK_COMPAT_START = 0xF900
    CJK_COMPAT_LAST = 0xFAD9
    CJK_COMPAT_SUPP_START = 0x2F800
    CJK_COMPAT_SUPP_LAST = 0x2FA1D
    KANGXI_RADICALS_START = 0x2F00

    # Tangut
    TANGUT_START = 0x17000
    TANGUT_LAST = 0x187FF
    TANGUT_COMPS_START = 0x18800
    TANGUT_COMPS_LAST = 0x18AFF

    # Khitan
    KHITAN_SMALL_START = 0x18B00
    KHITAN_SMALL_LAST = 0x18CD5

    # Nushu
    NUSHU_START = 0x1B170
    NUSHU_LAST = 0x1B2FB

    # Egyptian Hieroglyphs
    EGYPTIAN_FIRST = 0x13000
    EGYPTIAN_LAST = 0x1342F
    EGYPTIAN_EXT_A_FIRST = 0x13460
    EGYPTIAN_EXT_A_LAST = 0x143FA

    # Hangul
    HANGUL_FIRST = 0xAC00
    HANGUL_LAST = 0xD7A3

    # IDC
    IDC_START = 0x2FF0
    IDC_END = 0x2FFB

    # ── Surrogate helpers ──────────────────────────────────────────

    @staticmethod
    def is_surrogate(ch: int) -> bool:
        return 0xD7FF < ch < 0xE000

    @staticmethod
    def is_high_surrogate(ch: int) -> bool:
        return 0xD800 <= ch <= 0xDBFF

    @staticmethod
    def is_low_surrogate(ch: int) -> bool:
        return 0xDC00 <= ch <= 0xDFFF

    @staticmethod
    def char_length(ch: int) -> int:
        return 2 if ch > 0xFFFF else 1

    @staticmethod
    def is_bmp(ch: int) -> bool:
        return ch <= 0xFFFF

    @staticmethod
    def plane(ch: int) -> int:
        return ch // 65536

    # ==================================================================
    #  Internal: data parsing
    # ==================================================================

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _unicodedata() -> list[dict]:
        entries: list[dict] = []
        for line in TxtParser.get_txt(UCD / "UnicodeData.txt"):
            if not line.strip() or line.startswith("#"):
                continue
            p = line.split(";")
            if len(p) < 15:
                continue
            try:
                cp = int(p[0], 16)
            except ValueError:
                continue
            entries.append(
                {
                    "cp": cp,
                    "name": p[1],
                    "gc": p[2],
                    "ccc": p[3],
                    "bidi": p[4],
                    "decomp": p[5],
                    "dec": p[6],
                    "digit": p[7],
                    "num": p[8],
                    "mirrored": p[9],
                    "uni1": p[10],
                    "iso": p[11],
                    "up": p[12],
                    "lo": p[13],
                    "ti": p[14],
                }
            )
        return entries

    @staticmethod
    def _binary_search(table: list[tuple[int, int, int]], cp: int, default: int = 0) -> int:
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
        return default

    @staticmethod
    def _compress_ranges(entries: list[dict], val_fn) -> list[tuple[int, int, int]]:
        table: list[tuple[int, int, int]] = []
        rs, prev_cp, prev_val = -1, -2, -1
        for e in entries:
            v = val_fn(e)
            if e["cp"] == prev_cp + 1 and v == prev_val:
                prev_cp = e["cp"]
            else:
                if rs >= 0:
                    table.append((rs, prev_cp, prev_val))
                rs = prev_cp = e["cp"]
                prev_val = v
        if rs >= 0:
            table.append((rs, prev_cp, prev_val))
        return table

    @staticmethod
    def _build_range_table(filename: str, value_map: dict[str, int]) -> list[tuple[int, int, int]]:
        table: list[tuple[int, int, int]] = []
        for line in filter(line_has_content, TxtParser.get_txt(UCD / filename)):
            parts = line.split(";")
            if len(parts) < 2:
                continue
            val = parts[1].strip().split("#")[0].strip()
            v = value_map.get(val)
            if v is None:
                continue
            rp = parts[0].strip()
            if ".." in rp:
                s_str, e_str = rp.split("..")
                s, e = int(s_str, 16), int(e_str, 16)
            else:
                s = e = int(rp, 16)
            table.append((s, e, v))
        table.sort()
        return table

    # ==================================================================
    #  General Category
    # ==================================================================

    _GC_MAP = {
        "Lu": 1,
        "Ll": 2,
        "Lt": 3,
        "Lm": 4,
        "Lo": 5,
        "Mn": 6,
        "Mc": 7,
        "Me": 8,
        "Nd": 9,
        "Nl": 10,
        "No": 11,
        "Zs": 12,
        "Zl": 13,
        "Zp": 14,
        "Cc": 15,
        "Cf": 16,
        "Cs": 17,
        "Co": 18,
        "Pc": 20,
        "Pd": 21,
        "Ps": 22,
        "Pe": 23,
        "Pi": 24,
        "Pf": 25,
        "Po": 26,
        "Sm": 27,
        "Sc": 28,
        "Sk": 29,
        "So": 30,
    }

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _gc_table() -> list[tuple[int, int, int]]:
        return Unicode._compress_ranges(Unicode._unicodedata(), lambda e: Unicode._GC_MAP.get(e["gc"], 0))

    @staticmethod
    def get_general_category(cp: int) -> GeneralCategory:
        return GeneralCategory(Unicode._binary_search(Unicode._gc_table(), cp, 0))

    # ==================================================================
    #  Character Name
    # ==================================================================

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _name_map() -> dict[int, str]:
        return {e["cp"]: e["name"] for e in Unicode._unicodedata() if e["name"]}

    @staticmethod
    def get_character_name(cp: int) -> str:
        return Unicode._name_map().get(cp, "")

    @staticmethod
    def get_unicode1_name(cp: int) -> str:
        m = {e["cp"]: e["uni1"] for e in Unicode._unicodedata() if e["uni1"].strip()}
        return m.get(cp, "")

    # ==================================================================
    #  Numeric
    # ==================================================================

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _numeric_map() -> dict[int, tuple[str, str, str]]:
        return {
            e["cp"]: (e["dec"], e["digit"], e["num"])
            for e in Unicode._unicodedata()
            if e["dec"].strip() or e["digit"].strip() or e["num"].strip()
        }

    @staticmethod
    def get_numeric_value(cp: int) -> str:
        m = Unicode._numeric_map().get(cp)
        return (m[0] or m[1] or m[2]) if m else ""

    @staticmethod
    def get_numeric_type(cp: int) -> str:
        m = Unicode._numeric_map().get(cp)
        if not m:
            return ""
        if m[0]:
            return "Decimal"
        if m[1]:
            return "Digit"
        return "Numeric"

    @staticmethod
    def is_decimal_digit(cp: int) -> bool:
        m = Unicode._numeric_map().get(cp)
        return bool(m and m[0])

    # ==================================================================
    #  Canonical Combining Class
    # ==================================================================

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _ccc_table() -> list[tuple[int, int, int]]:
        return Unicode._compress_ranges(Unicode._unicodedata(), lambda e: int(e["ccc"]) if e["ccc"].strip() else 0)

    @staticmethod
    def get_canonical_combining_class(cp: int) -> int:
        return Unicode._binary_search(Unicode._ccc_table(), cp, 0)

    # ==================================================================
    #  Bidi Class
    # ==================================================================

    _BIDI_MAP = {
        "L": 0,
        "R": 1,
        "AL": 2,
        "EN": 3,
        "ES": 4,
        "ET": 5,
        "AN": 6,
        "CS": 7,
        "NSM": 8,
        "BN": 9,
        "B": 10,
        "S": 11,
        "WS": 12,
        "ON": 13,
        "LRE": 14,
        "LRO": 15,
        "RLE": 16,
        "RLO": 17,
        "PDF": 18,
        "LRI": 19,
        "RLI": 20,
        "FSI": 21,
        "PDI": 22,
    }

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _bidi_table() -> list[tuple[int, int, int]]:
        def fn(e):
            v = Unicode._BIDI_MAP.get(e["bidi"])
            return v if v is not None else 0

        return Unicode._compress_ranges(Unicode._unicodedata(), fn)

    @staticmethod
    def get_bidi_class(cp: int) -> BidiClass:
        return BidiClass(Unicode._binary_search(Unicode._bidi_table(), cp, 0))

    # ==================================================================
    #  Decomposition
    # ==================================================================

    _DT_MAP = {
        "": 1,
        "<font>": 2,
        "<noBreak>": 3,
        "<initial>": 4,
        "<medial>": 5,
        "<final>": 6,
        "<isolated>": 7,
        "<circle>": 8,
        "<super>": 9,
        "<sub>": 10,
        "<vertical>": 11,
        "<wide>": 12,
        "<narrow>": 13,
        "<small>": 14,
        "<square>": 15,
        "<fraction>": 16,
        "<compat>": 17,
    }

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _decomp_table() -> list[tuple[int, int, int]]:
        entries = Unicode._unicodedata()
        table: list[tuple[int, int, int]] = []
        for e in entries:
            d = e["decomp"].strip()
            if not d:
                continue
            dt = 1
            if d.startswith("<"):
                end = d.index(">")
                dt = Unicode._DT_MAP.get(d[: end + 1], 17)
                d = d[end + 1 :].strip()
            fm = d.split()[0] if d else ""
            try:
                mcp = int(fm, 16) if fm else e["cp"]
            except ValueError:
                mcp = e["cp"]
            table.append((e["cp"], e["cp"], (dt << 24) | mcp))
        return table

    @staticmethod
    def get_decomposition_type(cp: int) -> DecompositionType:
        v = Unicode._binary_search(Unicode._decomp_table(), cp, -1)
        return DecompositionType.None_ if v < 0 else DecompositionType(v >> 24)

    @staticmethod
    def get_decomposition_mapping(cp: int) -> int:
        v = Unicode._binary_search(Unicode._decomp_table(), cp, -1)
        return cp if v < 0 else (v & 0xFFFFFF)

    # ==================================================================
    #  Script
    # ==================================================================

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _script_data() -> tuple[list[tuple[int, int, int]], list[str]]:
        sid: dict[str, int] = {}
        raw: list[tuple[int, int, str]] = []
        for line in filter(line_has_content, TxtParser.get_txt(UCD / "Scripts.txt")):
            parts = line.split(";")
            if len(parts) < 2:
                continue
            sc = parts[1].strip().split("#")[0].strip()
            rp = parts[0].strip()
            s, e = (
                (int(rp, 16), int(rp, 16))
                if ".." not in rp
                else (int(rp.split("..")[0], 16), int(rp.split("..")[1], 16))
            )
            raw.append((s, e, sc))
        raw.sort()
        table, names = [], [""]
        for s, e, sc in raw:
            if sc not in sid:
                sid[sc] = len(names)
                names.append(sc)
            table.append((s, e, sid[sc]))
        return table, names

    @staticmethod
    def get_script(cp: int) -> str:
        table, names = Unicode._script_data()
        v = Unicode._binary_search(table, cp, 0)
        return names[v] if v < len(names) else "Unknown"

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _script_ext_map() -> dict[int, list[str]]:
        m: dict[int, list[str]] = {}
        for line in filter(line_has_content, TxtParser.get_txt(UCD / "ScriptExtensions.txt")):
            parts = line.split(";")
            if len(parts) < 2:
                continue
            try:
                cp = int(parts[0].strip(), 16)
                m[cp] = [x.strip() for x in parts[1].strip().split("#")[0].split()]
            except ValueError:
                continue
        return m

    @staticmethod
    def get_script_extensions(cp: int) -> list[str]:
        return Unicode._script_ext_map().get(cp, [])

    # ==================================================================
    #  Block
    # ==================================================================

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _block_data() -> tuple[list[tuple[int, int, int]], list[str]]:
        table: list[tuple[int, int, int]] = []
        names, nid = [""], {}
        for line in filter(line_has_content, TxtParser.get_txt(UCD / "Blocks.txt")):
            parts = line.split(";")
            if len(parts) < 2:
                continue
            name = parts[1].strip()
            s_str, e_str = parts[0].strip().split("..")
            s, e = int(s_str, 16), int(e_str, 16)
            if name not in nid:
                nid[name] = len(names)
                names.append(name)
            table.append((s, e, nid[name]))
        table.sort()
        return table, names

    @staticmethod
    def get_block_name(cp: int) -> str:
        table, names = Unicode._block_data()
        v = Unicode._binary_search(table, cp, 0)
        return names[v] if v < len(names) else "No_Block"

    @staticmethod
    def get_block_range(cp: int) -> tuple[int, int]:
        table, _ = Unicode._block_data()
        lo, hi = 0, len(table) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            s, e, _ = table[mid]
            if cp < s:
                hi = mid - 1
            elif cp > e:
                lo = mid + 1
            else:
                return (s, e)
        return (0, 0)

    # ==================================================================
    #  East Asian Width
    # ==================================================================

    _EAW_MAP = {"N": 0, "A": 1, "H": 2, "W": 3, "F": 4, "Na": 5}

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _eaw_table() -> list[tuple[int, int, int]]:
        return Unicode._build_range_table("EastAsianWidth.txt", Unicode._EAW_MAP)

    @staticmethod
    def get_east_asian_width(cp: int) -> EastAsianWidth:
        return EastAsianWidth(Unicode._binary_search(Unicode._eaw_table(), cp, 0))

    # ==================================================================
    #  Line Break
    # ==================================================================

    _LB_MAP = {
        "XX": 0,
        "AI": 1,
        "AL": 2,
        "B2": 3,
        "BA": 4,
        "BB": 5,
        "BK": 6,
        "CB": 7,
        "CJ": 8,
        "CL": 9,
        "CM": 10,
        "CP": 11,
        "CR": 12,
        "EB": 13,
        "EM": 14,
        "EX": 15,
        "GL": 16,
        "H2": 17,
        "H3": 18,
        "HL": 19,
        "HY": 20,
        "ID": 21,
        "IN": 22,
        "IS": 23,
        "JL": 24,
        "JV": 25,
        "JT": 26,
        "LF": 27,
        "NL": 28,
        "NS": 29,
        "NU": 30,
        "OP": 31,
        "PO": 32,
        "PR": 33,
        "QU": 34,
        "RI": 35,
        "SA": 36,
        "SG": 37,
        "SP": 38,
        "SY": 39,
        "WJ": 40,
        "ZW": 41,
        "ZWJ": 42,
    }

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _lb_table() -> list[tuple[int, int, int]]:
        return Unicode._build_range_table("LineBreak.txt", Unicode._LB_MAP)

    @staticmethod
    def get_line_break(cp: int) -> LineBreak:
        return LineBreak(Unicode._binary_search(Unicode._lb_table(), cp, 0))

    # ==================================================================
    #  Vertical Orientation
    # ==================================================================

    _VO_MAP = {"R": 0, "U": 1, "Tu": 2, "Tr": 3}

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _vo_table() -> list[tuple[int, int, int]]:
        return Unicode._build_range_table("VerticalOrientation.txt", Unicode._VO_MAP)

    @staticmethod
    def get_vertical_orientation(cp: int) -> str:
        v = Unicode._binary_search(Unicode._vo_table(), cp, 0)
        return {0: "R", 1: "U", 2: "Tu", 3: "Tr"}.get(v, "R")

    # ==================================================================
    #  Arabic Joining
    # ==================================================================

    _JT_MAP = {"U": 0, "C": 1, "D": 2, "R": 3, "L": 4, "T": 5}

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _joining_data() -> tuple[list[tuple[int, int, int]], dict[int, str]]:
        table: list[tuple[int, int, int]] = []
        groups: dict[int, str] = {}
        for line in filter(line_has_content, TxtParser.get_txt(UCD / "ArabicShaping.txt")):
            parts = line.split(";")
            if len(parts) < 4:
                continue
            try:
                cp = int(parts[0].strip(), 16)
            except ValueError:
                continue
            jt = Unicode._JT_MAP.get(parts[2].strip(), 0)
            jg = parts[3].strip().split("#")[0].strip()
            table.append((cp, cp, jt))
            if jg:
                groups[cp] = jg
        table.sort()
        return table, groups

    @staticmethod
    def get_joining_type(cp: int) -> JoiningType:
        table, _ = Unicode._joining_data()
        return JoiningType(Unicode._binary_search(table, cp, 0))

    @staticmethod
    def get_joining_group(cp: int) -> str:
        _, groups = Unicode._joining_data()
        return groups.get(cp, "")

    # ==================================================================
    #  Bidi Mirroring
    # ==================================================================

    @staticmethod
    def get_bidi_mirrored(cp: int) -> bool:
        for e in Unicode._unicodedata():
            if e["cp"] == cp:
                return e["mirrored"] == "Y"
        return False

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _mirroring_map() -> dict[int, int]:
        m: dict[int, int] = {}
        for line in filter(line_has_content, TxtParser.get_txt(UCD / "BidiMirroring.txt")):
            parts = line.split(";")
            if len(parts) < 2:
                continue
            try:
                s = int(parts[0].strip(), 16)
                t = int(parts[1].strip().split("#")[0].strip(), 16)
                m[s] = t
            except ValueError:
                continue
        return m

    @staticmethod
    def get_bidi_mirroring_glyph(cp: int) -> int:
        return Unicode._mirroring_map().get(cp, cp)

    # ==================================================================
    #  Bidi Brackets
    # ==================================================================

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _bidi_brackets() -> tuple[dict, dict]:
        pairs: dict[int, int] = {}
        types: dict[int, str] = {}
        for line in filter(line_has_content, TxtParser.get_txt(UCD / "BidiBrackets.txt")):
            parts = line.split(";")
            if len(parts) < 3:
                continue
            try:
                a = int(parts[0].strip(), 16)
                b = int(parts[1].strip(), 16)
                bt = parts[2].strip().split("#")[0].strip()
                if bt == "o":
                    pairs[a] = b
                    types[a] = "o"
                    types[b] = "c"
                elif bt == "c":
                    pairs[b] = a
                    types[b] = "o"
                    types[a] = "c"
            except ValueError:
                continue
        return pairs, types

    @staticmethod
    def get_bidi_paired_bracket(cp: int) -> int:
        pairs, _ = Unicode._bidi_brackets()
        return pairs.get(cp, cp)

    @staticmethod
    def get_bidi_bracket_type(cp: int) -> str:
        _, types = Unicode._bidi_brackets()
        return types.get(cp, "n")

    # ==================================================================
    #  Case Mapping
    # ==================================================================

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _case_table(which: str) -> list[tuple[int, int, int]]:
        field = {"lower": "lo", "upper": "up", "title": "ti"}[which]
        entries = Unicode._unicodedata()
        table: list[tuple[int, int, int]] = []
        for e in entries:
            v = e[field].strip()
            if not v:
                continue
            try:
                t = int(v, 16)
            except ValueError:
                continue
            if t != e["cp"]:
                table.append((e["cp"], e["cp"], t))
        table.sort()
        return table

    @staticmethod
    def get_simple_lowercase(cp: int) -> int:
        return Unicode._binary_search(Unicode._case_table("lower"), cp, cp)

    @staticmethod
    def get_simple_uppercase(cp: int) -> int:
        return Unicode._binary_search(Unicode._case_table("upper"), cp, cp)

    @staticmethod
    def get_simple_titlecase(cp: int) -> int:
        return Unicode._binary_search(Unicode._case_table("title"), cp, cp)

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _casefold_map() -> dict[int, int]:
        m: dict[int, int] = {}
        for line in filter(line_has_content, TxtParser.get_txt(UCD / "CaseFolding.txt")):
            parts = line.split(";")
            if len(parts) < 3:
                continue
            if parts[1].strip() not in ("C", "F"):
                continue
            try:
                s = int(parts[0].strip(), 16)
                t = int(parts[2].strip().split("#")[0].strip(), 16)
                m[s] = t
            except ValueError:
                continue
        return m

    @staticmethod
    def get_case_folding(cp: int) -> int:
        return Unicode._casefold_map().get(cp, cp)

    # ==================================================================
    #  Binary Properties
    # ==================================================================

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _binary_props() -> dict[str, list[tuple[int, int]]]:
        props: dict[str, list[tuple[int, int]]] = {}
        for fname in ("PropList.txt", "DerivedCoreProperties.txt"):
            for line in filter(line_has_content, TxtParser.get_txt(UCD / fname)):
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

    @staticmethod
    def has_binary_property(cp: int, prop_name: str) -> bool:
        ranges = Unicode._binary_props().get(prop_name, [])
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

    @staticmethod
    def is_whitespace(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "White_Space")

    @staticmethod
    def is_default_ignorable(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Default_Ignorable_Code_Point")

    @staticmethod
    def is_math(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Math")

    @staticmethod
    def is_alphabetic(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Alphabetic")

    @staticmethod
    def is_lowercase(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Lowercase")

    @staticmethod
    def is_uppercase(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Uppercase")

    @staticmethod
    def is_case_ignorable(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Case_Ignorable")

    @staticmethod
    def is_cased(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Cased")

    @staticmethod
    def is_changes_when_casefolded(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Changes_When_Casefolded")

    @staticmethod
    def is_id_start(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "ID_Start")

    @staticmethod
    def is_id_continue(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "ID_Continue")

    @staticmethod
    def is_xid_start(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "XID_Start")

    @staticmethod
    def is_xid_continue(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "XID_Continue")

    @staticmethod
    def is_pattern_whitespace(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Pattern_White_Space")

    @staticmethod
    def is_pattern_syntax(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Pattern_Syntax")

    @staticmethod
    def is_emoji(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Emoji")

    @staticmethod
    def is_emoji_presentation(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Emoji_Presentation")

    @staticmethod
    def is_emoji_modifier(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Emoji_Modifier")

    @staticmethod
    def is_emoji_modifier_base(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Emoji_Modifier_Base")

    @staticmethod
    def is_emoji_component(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Emoji_Component")

    @staticmethod
    def is_extended_pictographic(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Extended_Pictographic")

    @staticmethod
    def is_dash(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Dash")

    @staticmethod
    def is_diacritic(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Diacritic")

    @staticmethod
    def is_extender(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Extender")

    @staticmethod
    def is_hex_digit(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Hex_Digit")

    @staticmethod
    def is_terminal_punctuation(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Terminal_Punctuation")

    @staticmethod
    def is_quotation_mark(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Quotation_Mark")

    @staticmethod
    def is_soft_dotted(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Soft_Dotted")

    @staticmethod
    def is_bidi_control(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Bidi_Control")

    @staticmethod
    def is_join_control(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Join_Control")

    @staticmethod
    def is_regional_indicator(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Regional_Indicator")

    @staticmethod
    def is_logical_order_exception(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Logical_Order_Exception")

    @staticmethod
    def is_noncharacter_code_point(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Noncharacter_Code_Point")

    @staticmethod
    def is_variation_selector(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Variation_Selector")

    @staticmethod
    def is_deprecated(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "Deprecated")

    @staticmethod
    def is_ids_binary_operator(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "IDS_Binary_Operator")

    @staticmethod
    def is_ids_trinary_operator(cp: int) -> bool:
        return Unicode.has_binary_property(cp, "IDS_Trinary_Operator")

    # ==================================================================
    #  Normalization
    # ==================================================================

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _full_decomp_map() -> dict[int, list[int]]:
        m: dict[int, list[int]] = {}
        for line in filter(line_has_content, TxtParser.get_txt(UCD / "UnicodeData.txt")):
            p = line.split(";")
            if len(p) < 6:
                continue
            try:
                cp = int(p[0], 16)
            except ValueError:
                continue
            d = p[5].strip()
            if not d:
                continue
            result: list[int] = []
            for part in d.split():
                if part.startswith("<"):
                    continue
                try:
                    result.append(int(part, 16))
                except ValueError:
                    continue
            if result:
                m[cp] = result
        return m

    @staticmethod
    def _decompose(cp: int, compat: bool) -> list[int]:
        fm = Unicode._full_decomp_map()
        dt = Unicode.get_decomposition_type(cp)
        if dt == DecompositionType.None_:
            return [cp]
        if not compat and dt != DecompositionType.Canon:
            return [cp]
        if cp not in fm:
            return [cp]
        result: list[int] = []
        for sc in fm[cp]:
            result.extend(Unicode._decompose(sc, compat))
        return result

    @staticmethod
    def _reorder(cps: list[int]) -> list[int]:
        for i in range(1, len(cps)):
            ccc_i = Unicode.get_canonical_combining_class(cps[i])
            if ccc_i == 0:
                continue
            j = i
            while j > 0:
                ccc_prev = Unicode.get_canonical_combining_class(cps[j - 1])
                if ccc_prev == 0 or ccc_prev <= ccc_i:
                    break
                cps[j], cps[j - 1] = cps[j - 1], cps[j]
                j -= 1
        return cps

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _composition_map() -> dict[tuple[int, int], int]:
        m: dict[tuple[int, int], int] = {}
        for line in filter(line_has_content, TxtParser.get_txt(UCD / "UnicodeData.txt")):
            p = line.split(";")
            if len(p) < 6:
                continue
            try:
                cp = int(p[0], 16)
            except ValueError:
                continue
            d = p[5].strip()
            if not d or d.startswith("<"):
                continue
            parts = d.split()
            if len(parts) == 2:
                try:
                    a, b = int(parts[0], 16), int(parts[1], 16)
                    m[(a, b)] = cp
                except ValueError:
                    continue
        return m

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _composition_exclusions() -> set[int]:
        ex: set[int] = set()
        for line in filter(line_has_content, TxtParser.get_txt(UCD / "CompositionExclusions.txt")):
            try:
                ex.add(int(line.strip().split("#")[0].strip(), 16))
            except ValueError:
                continue
        return ex

    @staticmethod
    def _compose_pair(a: int, b: int) -> int:
        cm = Unicode._composition_map()
        exc = Unicode._composition_exclusions()
        r = cm.get((a, b))
        if r is None or r in exc:
            return 0
        return r

    @staticmethod
    def _compose(cps: list[int]) -> list[int]:
        if len(cps) <= 1:
            return cps
        result = [cps[0]]
        for cp in cps[1:]:
            cp_ccc = Unicode.get_canonical_combining_class(cp)
            while result:
                last = result[-1]
                last_ccc = Unicode.get_canonical_combining_class(last)
                if last_ccc >= cp_ccc and cp_ccc > 0:
                    break
                composed = Unicode._compose_pair(last, cp)
                if composed:
                    cp = composed
                    result.pop()
                else:
                    break
            result.append(cp)
        return result

    @staticmethod
    def get_nfd(text: str) -> str:
        result: list[int] = []
        for ch in text:
            result.extend(Unicode._decompose(ord(ch), False))
        return "".join(chr(c) for c in Unicode._reorder(result))

    @staticmethod
    def get_nfc(text: str) -> str:
        cps = [c for ch in text for c in Unicode._decompose(ord(ch), False)]
        return "".join(chr(c) for c in Unicode._compose(cps))

    @staticmethod
    def get_nfkd(text: str) -> str:
        result: list[int] = []
        for ch in text:
            result.extend(Unicode._decompose(ord(ch), True))
        return "".join(chr(c) for c in Unicode._reorder(result))

    @staticmethod
    def get_nfkc(text: str) -> str:
        cps = [c for ch in text for c in Unicode._decompose(ord(ch), True)]
        return "".join(chr(c) for c in Unicode._compose(cps))

    # ==================================================================
    #  Normalization QC
    # ==================================================================

    @staticmethod
    def is_nfc_qc(cp: int) -> str:
        """Quick check for NFC. Returns 'Y' (yes), 'N' (no), 'M' (maybe)."""
        dt = Unicode.get_decomposition_type(cp)
        if dt == DecompositionType.None_:
            return "Y"
        dm = Unicode.get_decomposition_mapping(cp)
        if dm != cp:
            return "N"
        return "Y"

    @staticmethod
    def is_nfd_qc(cp: int) -> str:
        """Quick check for NFD."""
        dt = Unicode.get_decomposition_type(cp)
        if dt == DecompositionType.Canon:
            return "N"
        return "Y"

    @staticmethod
    def is_nfkc_qc(cp: int) -> str:
        dt = Unicode.get_decomposition_type(cp)
        if dt == DecompositionType.None_:
            return "Y"
        if dt != DecompositionType.Canon:
            return "N"
        return "Y"

    @staticmethod
    def is_nfkd_qc(cp: int) -> str:
        dt = Unicode.get_decomposition_type(cp)
        if dt == DecompositionType.None_:
            return "Y"
        return "N"

    # ==================================================================
    #  Script functions
    # ==================================================================

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _script_names_map() -> dict[int, str]:
        """Map script index to script name."""
        names: dict[int, str] = {}
        table, names_list = Unicode._script_data()
        for s, e, idx in table:
            if idx not in names:
                names[idx] = names_list[idx]
        return names

    @staticmethod
    def get_script_name(script_idx: int) -> str:
        _, names = Unicode._script_data()
        return names[script_idx] if 0 < script_idx < len(names) else "Unknown"

    @staticmethod
    def get_script_code(script_idx: int) -> str:
        name = Unicode.get_script_name(script_idx)
        if len(name) == 4:
            return name
        return name[:4] if name else "Zzzz"

    @staticmethod
    def get_script_for_character(cp: int) -> str:
        return Unicode.get_script(cp)

    # ==================================================================
    #  Plane functions
    # ==================================================================

    _PLANE_NAMES = [
        "Basic Multilingual Plane (BMP)",
        "Supplementary Multilingual Plane (SMP)",
        "Supplementary Ideographic Plane (SIP)",
        "Tertiary Ideographic Plane (TIP)",
        "Plane 4 (Unassigned)",
        "Plane 5 (Unassigned)",
        "Plane 6 (Unassigned)",
        "Plane 7 (Unassigned)",
        "Plane 8 (Unassigned)",
        "Plane 9 (Unassigned)",
        "Plane 10 (Unassigned)",
        "Plane 11 (Unassigned)",
        "Plane 12 (Unassigned)",
        "Plane 13 (Unassigned)",
        "Supplementary Special-purpose Plane (SSP)",
        "Supplementary Private Use Area-A (PUA-A)",
        "Supplementary Private Use Area-B (PUA-B)",
    ]

    _PLANE_ABBREV = [
        "BMP",
        "SMP",
        "SIP",
        "TIP",
        "P4",
        "P5",
        "P6",
        "P7",
        "P8",
        "P9",
        "P10",
        "P11",
        "P12",
        "P13",
        "SSP",
        "SPUA-A",
        "SPUA-B",
    ]

    @staticmethod
    def get_plane_name(plane: int, with_abbrev: bool = False) -> str:
        if 0 <= plane < 17:
            name = Unicode._PLANE_NAMES[plane]
            if with_abbrev:
                return f"{Unicode._PLANE_ABBREV[plane]}: {name}"
            return name
        return f"Plane {plane}"

    @staticmethod
    def get_plane_abbreviation(plane: int) -> str:
        return Unicode._PLANE_ABBREV[plane] if 0 <= plane < 17 else ""

    @staticmethod
    def get_plane_start(plane: int) -> int:
        return plane * 65536

    @staticmethod
    def get_plane_end(plane: int) -> int:
        return plane * 65536 + 65535

    @staticmethod
    def get_plane_from_block(block_name: str) -> int:
        for line in filter(line_has_content, TxtParser.get_txt(UCD / "Blocks.txt")):
            parts = line.split(";")
            if len(parts) < 2:
                continue
            if parts[1].strip() == block_name:
                s = int(parts[0].strip().split("..")[0], 16)
                return s // 65536
        return 0

    @staticmethod
    def is_plane_reserved(plane: int) -> bool:
        return plane in (4, 5, 6, 7, 8, 9, 10, 11, 12, 13)

    @staticmethod
    def is_valid_code_point(cp: int) -> bool:
        return 0 <= cp <= 0x10FFFF and not (0xD800 <= cp <= 0xDFFF)

    # ==================================================================
    #  Block functions
    # ==================================================================

    @staticmethod
    def get_block_start(block_name: str) -> int:
        for line in filter(line_has_content, TxtParser.get_txt(UCD / "Blocks.txt")):
            parts = line.split(";")
            if len(parts) < 2:
                continue
            if parts[1].strip() == block_name:
                return int(parts[0].strip().split("..")[0], 16)
        return 0

    @staticmethod
    def get_block_end(block_name: str) -> int:
        for line in filter(line_has_content, TxtParser.get_txt(UCD / "Blocks.txt")):
            parts = line.split(";")
            if len(parts) < 2:
                continue
            if parts[1].strip() == block_name:
                return int(parts[0].strip().split("..")[1], 16)
        return 0

    @staticmethod
    def get_block_from_name(name: str) -> str:
        # Returns the canonical block name if found
        for line in filter(line_has_content, TxtParser.get_txt(UCD / "Blocks.txt")):
            parts = line.split(";")
            if len(parts) < 2:
                continue
            if parts[1].strip().lower() == name.lower():
                return parts[1].strip()
        return ""

    @staticmethod
    def get_block_range_for_character(cp: int) -> tuple[int, int]:
        return Unicode.get_block_range(cp)

    @staticmethod
    def get_characters_per_block(block_name: str) -> int:
        s = Unicode.get_block_start(block_name)
        e = Unicode.get_block_end(block_name)
        if s and e:
            return e - s + 1
        return 0

    # ==================================================================
    #  Character lookup
    # ==================================================================

    @staticmethod
    def get_character_from_name(name: str) -> int:
        """Find a Unicode codepoint by its name."""
        nm = Unicode._name_map()
        # Direct lookup
        for cp, n in nm.items():
            if n.upper() == name.upper():
                return cp
        # Approximate match
        name_upper = name.upper().replace(" ", "_").replace("-", "_")
        for cp, n in nm.items():
            if n.upper().replace(" ", "_").replace("-", "_") == name_upper:
                return cp
        return 0

    @staticmethod
    def find_character_name(
        search: str,
        start_cp: int = 0,
        forwards: bool = True,
        whole_words: bool = False,
    ) -> int:
        """Find a character by name substring."""
        nm = Unicode._name_map()
        cps = sorted(nm.keys())
        if not forwards:
            cps.reverse()

        search_upper = search.upper()
        for cp in cps:
            if cp < start_cp:
                continue
            name = nm[cp].upper()
            if whole_words:
                import re

                if re.search(r"\b" + re.escape(search_upper) + r"\b", name):
                    return cp
            elif search_upper in name:
                return cp
        return 0

    @staticmethod
    def parse_code_point(text: str) -> int:
        """Parse a codepoint from various string formats."""
        text = text.strip()
        if text.upper().startswith("U+"):
            text = text[2:]
        elif text.upper().startswith("0X"):
            text = text[2:]
        if len(text) <= 6 and all(c in "0123456789ABCDEFabcdef" for c in text):
            return int(text, 16)
        if len(text) == 1:
            return ord(text)
        return 0

    # ==================================================================
    #  UTF-8 / Surrogates
    # ==================================================================

    @staticmethod
    def get_utf8(cp: int, escaped: bool = False, octal: bool = False) -> str:
        """Get UTF-8 bytes (as string or escaped)."""
        if cp > 0x10FFFF:
            return ""
        try:
            b = chr(cp).encode("utf-8")
        except (UnicodeEncodeError, ValueError):
            return ""
        if escaped:
            if octal:
                return "".join(f"\\{byte:03o}" for byte in b)
            return "".join(f"\\x{byte:02X}" for byte in b)
        return b.decode("latin-1")  # Return raw bytes as string

    @staticmethod
    def get_unicode32_from_surrogates(hi: int, lo: int) -> int:
        """Combine surrogate pair into a single codepoint."""
        if 0xD800 <= hi <= 0xDBFF and 0xDC00 <= lo <= 0xDFFF:
            return 0x10000 + ((hi - 0xD800) << 10) + (lo - 0xDC00)
        return 0

    @staticmethod
    def get_surrogates_from_unicode32(cp: int) -> tuple[int, int]:
        """Split a supplementary codepoint into surrogates."""
        if cp > 0xFFFF:
            cp -= 0x10000
            return (0xD800 | (cp >> 10), 0xDC00 | (cp & 0x3FF))
        return (0, 0)

    # ==================================================================
    #  Word boundary detection (ported from Unicode.h)
    # ==================================================================

    @staticmethod
    def is_word_starter(cp: int) -> bool:
        """Check if a codepoint can start a word. Equivalent to C++ IsWordStarter."""
        cat = Unicode.get_general_category(cp)
        return cat in (
            GeneralCategory.Lu,
            GeneralCategory.Ll,
            GeneralCategory.Lt,
            GeneralCategory.Lm,
            GeneralCategory.Lo,
            GeneralCategory.Nd,
            GeneralCategory.Nl,
            GeneralCategory.No,
        )

    @staticmethod
    def is_word_boundary(before: int, current: int, after: int) -> bool:
        """Check if there is a word boundary at current.

        Equivalent to C++ IsWordBoundary.
        """
        before_cat = Unicode.get_general_category(before) if before else GeneralCategory.Cn
        after_cat = Unicode.get_general_category(after) if after else GeneralCategory.Cn

        # Word boundary between a letter/digit and non-letter/digit
        c1 = before_cat in (
            GeneralCategory.Lu,
            GeneralCategory.Ll,
            GeneralCategory.Lt,
            GeneralCategory.Lm,
            GeneralCategory.Lo,
            GeneralCategory.Nd,
            GeneralCategory.Nl,
            GeneralCategory.No,
        )
        c2 = after_cat in (
            GeneralCategory.Lu,
            GeneralCategory.Ll,
            GeneralCategory.Lt,
            GeneralCategory.Lm,
            GeneralCategory.Lo,
            GeneralCategory.Nd,
            GeneralCategory.Nl,
            GeneralCategory.No,
        )
        return c1 != c2

    @staticmethod
    def is_cjk_ideograph_static(cp: int) -> bool:
        """Check if a codepoint is a CJK Unified or Compatibility Ideograph.

        Equivalent to C++ Unicode::IsCJKIdeograph (static version).
        """
        try:
            from src.cjkv.cjk import CJK

            return CJK(cp).is_cjk_ideograph()
        except (ValueError, TypeError):
            return False

    # ==================================================================
    #  Line/word break helpers
    # ==================================================================

    @staticmethod
    def is_new_line(cp: int) -> bool:
        return cp in (0x000A, 0x000D, 0x0085, 0x2028, 0x2029)

    @staticmethod
    def is_hard_line_break(cp: int) -> bool:
        return cp in (0x000A, 0x000D, 0x0085, 0x2028, 0x2029)

    @staticmethod
    def is_control_character(cp: int) -> bool:
        gc = Unicode.get_general_category(cp)
        return gc == GeneralCategory.Cc

    @staticmethod
    def is_whitespace_simple(cp: int) -> bool:
        return cp in (
            0x0009,
            0x000A,
            0x000B,
            0x000C,
            0x000D,
            0x0020,
            0x0085,
            0x00A0,
            0x2000,
            0x2001,
            0x2002,
            0x2003,
            0x2004,
            0x2005,
            0x2006,
            0x2007,
            0x2008,
            0x2009,
            0x200A,
            0x2028,
            0x2029,
            0x202F,
            0x205F,
            0x3000,
        )

    @staticmethod
    def is_hex_digit_char(cp: int) -> bool:
        return (
            (0x0030 <= cp <= 0x0039)
            or (0x0041 <= cp <= 0x0046)
            or (0x0061 <= cp <= 0x0066)
            or Unicode.has_binary_property(cp, "Hex_Digit")
        )

    @staticmethod
    def is_dec_digit(cp: int) -> bool:
        return 0x0030 <= cp <= 0x0039

    # ==================================================================
    #  Script-specific helpers
    # ==================================================================

    @staticmethod
    def is_latin_letter(cp: int) -> bool:
        return (
            (0x0041 <= cp <= 0x005A)
            or (0x0061 <= cp <= 0x007A)
            or (0x00C0 <= cp <= 0x024F)
            or cp == 0x00D7
            or cp == 0x00F7
        )

    @staticmethod
    def is_greek_letter(cp: int) -> bool:
        return (0x0370 <= cp <= 0x03FF) or (0x1F00 <= cp <= 0x1FFF)

    @staticmethod
    def is_cyrillic_letter(cp: int) -> bool:
        return 0x0400 <= cp <= 0x052F

    @staticmethod
    def is_hebrew_letter(cp: int) -> bool:
        return 0x0590 <= cp <= 0x05FF

    @staticmethod
    def is_armenian_letter(cp: int) -> bool:
        return 0x0530 <= cp <= 0x058F

    @staticmethod
    def is_georgian_letter(cp: int) -> bool:
        return (0x10A0 <= cp <= 0x10FF) or (0x1C90 <= cp <= 0x1CBF)

    @staticmethod
    def is_arabic_digit(cp: int) -> bool:
        return 0x0660 <= cp <= 0x0669

    @staticmethod
    def is_fullwidth_letter(cp: int) -> bool:
        return 0xFF21 <= cp <= 0xFF5A

    @staticmethod
    def is_fullwidth_digit(cp: int) -> bool:
        return 0xFF10 <= cp <= 0xFF19

    # ==================================================================
    #  CJK / Ideographic helpers
    # ==================================================================

    @staticmethod
    def is_cjk_ideograph(cp: int) -> bool:
        return (
            (0x4E00 <= cp <= 0x9FFF)
            or (0x3400 <= cp <= 0x4DBF)
            or (0x20000 <= cp <= 0x2A6DF)
            or (0x2A700 <= cp <= 0x2B73F)
            or (0x2B740 <= cp <= 0x2B81D)
            or (0x2B820 <= cp <= 0x2CEAD)
            or (0x2CEB0 <= cp <= 0x2EBE0)
            or (0x30000 <= cp <= 0x3134A)
            or (0x31350 <= cp <= 0x323AF)
            or (0x2EBF0 <= cp <= 0x2EE5D)
            or (0xF900 <= cp <= 0xFAD9)
            or (0x2F800 <= cp <= 0x2FA1D)
        )

    @staticmethod
    def is_han_ideograph(cp: int, include_iteration_mark: bool = True) -> bool:
        """Check if codepoint is a Han (CJK) ideograph."""
        return Unicode.is_cjk_ideograph(cp)

    @staticmethod
    def is_tangut_ideograph(cp: int, include_iteration_mark: bool = True) -> bool:
        return (0x17000 <= cp <= 0x187FF) or (0x18D00 <= cp <= 0x18D7F) or (include_iteration_mark and cp == 0x16FE0)

    @staticmethod
    def is_yi_syllable(cp: int, include_iteration_mark: bool = True) -> bool:
        return 0xA000 <= cp <= 0xA48C or (include_iteration_mark and cp == 0xA015)

    @staticmethod
    def is_nushu_character(cp: int, include_iteration_mark: bool = True) -> bool:
        return 0x1B170 <= cp <= 0x1B2FB or (include_iteration_mark and cp == 0x16FE1)

    @staticmethod
    def is_khitan_small_script(cp: int, include_iteration_mark: bool = True) -> bool:
        return 0x18B00 <= cp <= 0x18CD5 or (include_iteration_mark and cp == 0x18B00)

    @staticmethod
    def is_hiragana(cp: int, include_iteration_mark: bool = True) -> bool:
        return 0x3040 <= cp <= 0x309F

    @staticmethod
    def is_katakana(cp: int, include_iteration_mark: bool = True) -> bool:
        return (0x30A0 <= cp <= 0x30FF) or (0xFF66 <= cp <= 0xFF9F)

    @staticmethod
    def is_idc_operand(cp: int) -> bool:
        """Check if codepoint is a valid IDC (Ideographic Description Character) operand."""
        gc = Unicode.get_general_category(cp)
        return gc in (
            GeneralCategory.Lo,
            GeneralCategory.Lu,
            GeneralCategory.Ll,
            GeneralCategory.Lt,
            GeneralCategory.Lm,
            GeneralCategory.Mc,
            GeneralCategory.Mn,
            GeneralCategory.Nd,
            GeneralCategory.Nl,
        )

    # ==================================================================
    #  Conversion: NCR, UCN, Unicode Plus
    # ==================================================================

    @staticmethod
    def convert_to_char_ref(cp: int, char_ref: int = 0, convert_basic_latin: bool = False) -> str:
        """Convert codepoint to NCR/character reference format."""
        if cp <= 0x7F and not convert_basic_latin:
            return chr(cp)
        if char_ref == 0:
            return f"&#x{cp:X};"
        elif char_ref == 1:
            return f"&#{cp};"
        else:
            return f"U+{cp:04X}"

    @staticmethod
    def convert_to_unicode_plus(cp: int) -> str:
        """Convert codepoint to U+XXXX format."""
        if cp > 0xFFFF:
            return f"U+{cp:05X}"
        return f"U+{cp:04X}"

    @staticmethod
    def convert_to_unicode_name(cp: int) -> str:
        """Get 'U+XXXX NAME' string."""
        name = Unicode.get_character_name(cp)
        uplus = Unicode.convert_to_unicode_plus(cp)
        return f"{uplus} {name}" if name else uplus

    @staticmethod
    def get_hex_value(ch: str) -> int:
        """Get hex value of a single hex digit character."""
        cp = ord(ch) if ch else 0
        if 0x30 <= cp <= 0x39:
            return cp - 0x30
        if 0x41 <= cp <= 0x46:
            return cp - 0x41 + 10
        if 0x61 <= cp <= 0x66:
            return cp - 0x61 + 10
        return -1

    @staticmethod
    def convert_from_ncr(text: str) -> tuple[int, int]:
        """Convert NCR at start of text to codepoint. Returns (cp, chars_consumed)."""
        import re

        m = re.match(r"&#x([0-9A-Fa-f]+);", text)
        if m:
            return int(m.group(1), 16), len(m.group(0))
        m = re.match(r"&#(\d+);", text)
        if m:
            return int(m.group(1)), len(m.group(0))
        return 0, 0

    @staticmethod
    def convert_from_ucn(text: str) -> tuple[int, int]:
        """Convert UCN at start of text. Returns (cp, chars_consumed)."""
        import re

        m = re.match(r"\\[Uu]\+?([0-9A-Fa-f]{4,8})", text)
        if m:
            return int(m.group(1), 16), len(m.group(0))
        return 0, 0

    # ==================================================================
    #  Numeric helpers
    # ==================================================================

    @staticmethod
    def get_hexadecimal_value(s: str) -> int:
        """Parse hex string to integer."""
        s = s.strip()
        if s.upper().startswith("0X"):
            s = s[2:]
        try:
            return int(s, 16)
        except ValueError:
            return 0

    @staticmethod
    def get_numeric_value_str(s: str) -> float:
        """Parse numeric string (may include fractions like '1/2')."""
        s = s.strip()
        if "/" in s:
            parts = s.split("/")
            if len(parts) == 2:
                try:
                    return float(parts[0]) / float(parts[1])
                except (ValueError, ZeroDivisionError):
                    pass
        try:
            return float(s)
        except ValueError:
            return 0.0

    @staticmethod
    def is_decimal_number(s: str) -> bool:
        """Check if string represents a decimal number."""
        return s.strip().isdigit()

    # ==================================================================
    #  Grapheme link
    # ==================================================================

    @staticmethod
    def is_grapheme_link(cp: int) -> bool:
        """Check if character extends a grapheme cluster."""
        ccc = Unicode.get_canonical_combining_class(cp)
        if ccc > 0:
            return True
        gc = Unicode.get_general_category(cp)
        return gc in (GeneralCategory.Mc, GeneralCategory.Me)

    # ==================================================================
    #  Variation selectors / standardized variants
    # ==================================================================

    @staticmethod
    def is_variation_sequence_base(cp: int) -> bool:
        """Check if cp can be the base of a variation sequence."""
        if Unicode.is_surrogate(cp) or not Unicode.is_valid_code_point(cp):
            return False
        gc = Unicode.get_general_category(cp)
        # Not controls or default ignorables
        return gc not in (GeneralCategory.Cc, GeneralCategory.Cs, GeneralCategory.Cn, GeneralCategory.Cf)

    @staticmethod
    def is_variation_sequence(base: int, vs: int) -> bool:
        """Check if (base, vs) forms a valid variation sequence."""
        return 0xFE00 <= vs <= 0xFE0F or 0xE0100 <= vs <= 0xE01EF

    # ==================================================================
    #  Tag / Regional indicator
    # ==================================================================

    @staticmethod
    def is_tag(cp: int) -> bool:
        return 0xE0000 <= cp <= 0xE007F

    @staticmethod
    def is_regional_indicator_cp(cp: int) -> bool:
        return 0x1F1E6 <= cp <= 0x1F1FF

    # ==================================================================
    #  CCC as string
    # ==================================================================

    @staticmethod
    def get_ccc_as_string(ccc: int) -> str:
        if ccc == 0:
            return "0 (Not Reordered)"
        if ccc == 1:
            return "1 (Overlay)"
        if 7 <= ccc <= 9:
            return f"{ccc} (Nukta)"
        if 10 <= ccc <= 199:
            return f"{ccc} (Attached Below)"
        if ccc == 200:
            return "200 (Attached Below Left)"
        if 202 <= ccc <= 214:
            return f"{ccc} (Attached Below)"
        if 216 <= ccc <= 220:
            return f"{ccc} (Attached Above)"
        if ccc == 222:
            return "222 (Attached Above Right)"
        if 224 <= ccc <= 232:
            return f"{ccc} (Attached Above)"
        if ccc == 233:
            return "233 (Double Below)"
        if ccc == 234:
            return "234 (Double Above)"
        if ccc == 240:
            return "240 (Iota Subscript)"
        return str(ccc)

    # ==================================================================
    #  Letter / word helpers
    # ==================================================================

    @staticmethod
    def is_letter(cp: int) -> bool:
        gc = Unicode.get_general_category(cp)
        return gc in (
            GeneralCategory.Lu,
            GeneralCategory.Ll,
            GeneralCategory.Lt,
            GeneralCategory.Lm,
            GeneralCategory.Lo,
        )

    @staticmethod
    def is_common_script_but_letter(cp: int) -> bool:
        sc = Unicode.get_script(cp)
        if sc in ("Common", "Inherited", "Unknown"):
            return Unicode.is_letter(cp)
        return False

    # ==================================================================
    #  Iteration marks
    # ==================================================================

    _ITERATION_MARKS = [
        (0x3005, "Han"),  # 々
        (0x303B, "Han"),  # 〻
        (0x309D, "Hiragana"),  # ゝ
        (0x309E, "Hiragana"),  # ゞ
        (0x30FD, "Katakana"),  # ヽ
        (0x30FE, "Katakana"),  # ヾ
        (0xA015, "Yi"),  # ꀕ
        (0x16FE0, "Tangut"),  # 𖿠
        (0x16FE1, "Nushu"),  # 𖿡
        (0x18B00, "Khitan"),  # 𘬀
    ]

    @staticmethod
    def get_iteration_mark_count() -> int:
        return len(Unicode._ITERATION_MARKS)

    @staticmethod
    def get_iteration_mark(index: int) -> tuple[int, str]:
        if 0 <= index < len(Unicode._ITERATION_MARKS):
            return Unicode._ITERATION_MARKS[index]
        return (0, "")

    # ==================================================================
    #  Block-based letter count
    # ==================================================================

    @staticmethod
    def letters_in_block(block_name: str) -> tuple[int, int, int]:
        """Return (count, first_letter, last_letter) for a block."""
        s = Unicode.get_block_start(block_name)
        e = Unicode.get_block_end(block_name)
        count = 0
        first = 0
        last = 0
        for cp in range(s, min(e + 1, s + 65536)):
            if Unicode.is_letter(cp):
                if count == 0:
                    first = cp
                last = cp
                count += 1
        return count, first, last
