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
