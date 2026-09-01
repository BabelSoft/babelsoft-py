from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from babelsoft.unicode import CodePoint, Unicode
from babelsoft.utils_.loader import CJKLoader
from babelsoft.utils_.parser import TxtParser, line_has_content

DISCRIMINATED_CJK = frozenset(
    (0xFA0E, 0xFA0F, 0xFA11, 0xFA13, 0xFA14, 0xFA1F, 0xFA21, 0xFA23, 0xFA24, 0xFA27, 0xFA28, 0xFA29)
)

# IDS.TXT entries look like:  ^⿰右回$(T)
_IDS_WRAPPER = re.compile(r"^\^(.+)\$\([^)]*\)\s*$")

# CJK Unified block shortcuts → (start, end), derived from the current release's
# Blocks.txt (via babelsoft.unicode.Unicode) so boundaries always match the UCD.
_CJK_SHORTCUT_BLOCK_NAMES = {
    "URO": "CJK Unified Ideographs",
    "A": "CJK Unified Ideographs Extension A",
    "B": "CJK Unified Ideographs Extension B",
    "C": "CJK Unified Ideographs Extension C",
    "D": "CJK Unified Ideographs Extension D",
    "E": "CJK Unified Ideographs Extension E",
    "F": "CJK Unified Ideographs Extension F",
    "G": "CJK Unified Ideographs Extension G",
    "H": "CJK Unified Ideographs Extension H",
    "I": "CJK Unified Ideographs Extension I",
    "COMP": "CJK Compatibility Ideographs",
    "COMPSUP": "CJK Compatibility Ideographs Supplement",
}


def _build_cjk_block_shortcuts() -> dict[str, tuple[int, int]]:
    """Map CJK shortcuts (URO, A, B, …) to (start, end) from Blocks.txt."""
    table, names = Unicode._block_data()
    by_name = {names[idx]: (s, e) for s, e, idx in table}
    return {key: by_name[blk] for key, blk in _CJK_SHORTCUT_BLOCK_NAMES.items() if blk in by_name}


CJK_BLOCK_SHORTCUTS: dict[str, tuple[int, int]] = _build_cjk_block_shortcuts()


@dataclass(frozen=True)
class Radical:
    rad: int
    var: int = 0

    def __repr__(self) -> str:
        return f"Radical({self.rad}, {self.var})"

    def to_unihan(self) -> str:
        return f"{self.rad}{'\'' * self.var}"

    def to_irg_radical(self) -> str:
        return f"{self.rad}.{self.var}"

    @classmethod
    def from_unihan(cls, text: str) -> Radical:
        var = text.count("'")
        rad = int(text.rstrip("'"))
        return cls(rad, var)


@dataclass
class RS:
    radical: Radical
    residual_stroke: int

    def __hash__(self):
        return hash((self.radical.rad, self.radical.var, self.residual_stroke))

    @property
    def variant(self) -> int:
        return self.radical.var

    def to_unihan(self) -> str:
        return f"{self.radical.rad}{'\'' * self.radical.var}.{self.residual_stroke}"

    def no_variant(self) -> RS:
        return RS(Radical(self.radical.rad), self.residual_stroke)

    @classmethod
    def from_unihan(cls, text: str) -> RS:
        parts = text.split(".", 1)
        radical_part = parts[0]
        stroke = int(parts[1]) if len(parts) > 1 else 0
        return cls(Radical.from_unihan(radical_part), stroke)

    def to_irg_radical(self) -> str:
        return self.radical.to_irg_radical()

    @classmethod
    def from_irg_radical(cls, text: str) -> RS:
        rad, var = text.split(".")
        return cls(Radical(int(rad), int(var)), 0)

    def radical_char(self) -> CJK:
        data = CJKLoader.load_ucd_CJKRadicals()
        key = (self.radical.rad, self.radical.var)
        if key not in data:
            raise ValueError(f"Radical variant {self} not found")
        cp = data[key][0] or self.radical_char_normalized()
        return CJK(cp)

    def radical_char_normalized(self) -> CJK:
        data = CJKLoader.load_ucd_CJKRadicals()
        key = (self.radical.rad, self.radical.var)
        if key not in data:
            raise ValueError(f"Radical variant {self} not found")
        return CJK(data[key][1])

    def ideographs(self) -> list[CJK]:
        data = CJKLoader.load_charts_RSIndex()
        key = (self.radical.rad, self.radical.var, self.residual_stroke)
        return [CJK(cp) for cp in data.get(key, [])]


@dataclass
class IDS:
    ids: str


@dataclass
class IDSInfo:
    cjk: CJK
    ids_list: list[IDS]
    comment: str = ""

    @classmethod
    def from_line(cls, line: str) -> IDSInfo | None:
        line = line.strip()
        if not line:
            return None
        parts = line.split("\t")
        cjk = CJK(parts[0])
        ids_list = [IDS(ids.strip()) for ids in parts[2:] if ids.startswith("^")]
        comment = next((f[1:] for f in parts[2:] if f.startswith("*")), "")
        return cls(cjk, ids_list, comment)

    def __repr__(self) -> str:
        return f"IDSInfo(cjk={self.cjk}, ids={self.ids_list}, comment={self.comment})"


@dataclass(frozen=True)
class _Src:
    """Metadata for a single IRG submitter source."""

    name: str
    label: str  # XML tag / C++ GetXmlData element, e.g. "HongKong"
    bit: int
    pattern: str
    field: str
    display: str = ""  # UI display name; falls back to `label`


@dataclass
class SrcRef:
    reference: str = ""

    class IRGSrc:
        """Central registry of IRG submitter sources."""

        G = _Src("CHINA_SINGAPORE", "China", 0x0001, " G", "kIRG_GSource")
        H = _Src("HONG_KONG_SAR", "HongKong", 0x0002, " H", "kIRG_HSource", "Hong Kong SAR")
        J = _Src("JAPAN", "Japan", 0x0004, " J", "kIRG_JSource")
        KP = _Src("DPRK", "DPRK", 0x0008, " KP", "kIRG_KPSource")
        K = _Src("ROK", "ROK", 0x0010, " K", "kIRG_KSource")
        M = _Src("MACAO_SAR", "Macau", 0x0020, " M", "kIRG_MSource", "Macao SAR")
        SG = _Src("SINGAPORE", "Singapore", 0x0800, " GS", "kIRG_GSource")
        S = _Src("SAT", "SAT", 0x0040, " S", "kIRG_SSource")
        T = _Src("TCA", "TCA", 0x0080, " T", "kIRG_TSource")
        UK = _Src("UK", "UK", 0x0100, " UK", "kIRG_UKSource")
        U = _Src("US_UTC", "UTC", 0x0200, " UTC", "kIRG_USource", "US & UTC")
        V = _Src("VIETNAM", "Vietnam", 0x0400, " V", "kIRG_VSource")
        MY = _Src("MALAYSIA", "Malaysia", 0x1000, " MY", "kIRG_MYSource", "Malaysia")

        _BY_CODE: ClassVar[dict[str, _Src]] = {
            "G": G,
            "H": H,
            "J": J,
            "KP": KP,
            "K": K,
            "M": M,
            "SG": SG,
            "S": S,
            "T": T,
            "UK": UK,
            "U": U,
            "V": V,
            "MY": MY,
        }

        # Display order — matches the CDialogCJKV / GetXmlData source list.
        _ORDER: ClassVar[list[str]] = [
            "G",
            "H",
            "M",
            "T",
            "J",
            "S",
            "K",
            "KP",
            "MY",
            "SG",
            "UK",
            "U",
            "V",
        ]

        _REF_PREFIX: ClassVar[dict[str, str | None]] = {
            "G": "G",
            "H": "H",
            "J": "J",
            "KP": "KP",
            "K": "K",
            "M": "M",
            "MY": None,
            "GS": "SG",  # Singapore (current, in kIRG_GSource)
            "SG": "SG",  # Singapore (future kIRG_SGSource)
            "SAT": "S",
            "T": "T",
            "UK": "UK",
            "UTC": "U",
            "V": "V",
        }

        @classmethod
        def by_code(cls, code: str) -> _Src:
            return cls._BY_CODE[code]

        @classmethod
        def all(cls) -> dict[str, _Src]:
            return cls._BY_CODE

        @classmethod
        def display_order(cls) -> list[tuple[str, _Src]]:
            """(code, source) pairs in display order."""
            return [(c, cls._BY_CODE[c]) for c in cls._ORDER if c in cls._BY_CODE]

        @classmethod
        def source_codes(cls) -> dict[str, str | None]:
            """{submitter code: Unihan source code}, e.g. 'SAT' → 'S', 'UTC' → 'U', 'SG' → 'G'."""
            out: dict[str, str | None] = {}
            for prefix, bykey in cls._REF_PREFIX.items():
                if bykey is None:
                    out[prefix] = None
                else:
                    out[prefix] = cls._BY_CODE[bykey].field.removeprefix("kIRG_").removesuffix("Source")
            return out

        @classmethod
        def matches(cls, codes, refs, submitter: str) -> bool:
            """Whether a character's Unihan sources (source codes + ref strings) belong to a submitter.

            Singapore ('SG') is identified by GS- / SG- references (they live under the
            G-source column in Unihan); 'G' (China) is every other G-source reference.
            """
            up = submitter.upper()
            is_sg = any(r.upper().startswith(("GS-", "SG-")) for r in refs)
            if up == "SG":
                return is_sg
            want = cls.source_codes().get(up)
            if not want:
                return False
            if up == "G":
                return want in codes and not is_sg
            return want in codes

    @property
    def prefix(self) -> str:
        return self.reference.split("-", 1)[0]

    @property
    def submitter(self) -> _Src | None:
        ref = self.reference.strip().upper()
        for prefix in sorted(SrcRef.IRGSrc._REF_PREFIX, key=len, reverse=True):
            if ref.startswith(prefix):
                code = SrcRef.IRGSrc._REF_PREFIX[prefix]
                return SrcRef.IRGSrc.by_code(code) if code else None
        return None

    def find(self) -> CJK | None:
        cp = CJKLoader.load_cjk_irg_reverse().get(self.reference)
        return CJK(cp) if cp else None

    def is_valid(self) -> bool:
        return self.find() is not None


# Derived convenience maps from SrcRef.IRGSource
SRC_PATTERN_MAP = {k: v.pattern for k, v in SrcRef.IRGSrc.all().items()}
SRC_BIT_MAP = {k: v.bit for k, v in SrcRef.IRGSrc.all().items()}
IRG_FIELD_TO_SOURCE = {v.field: k for k, v in SrcRef.IRGSrc.all().items()}


class CJKFlags(Enum):
    NOTHING = 0x0000
    IVS = 0x0001
    FANTI = FANTI_PLUS = 0x0002
    JIANTI = JIANTI_PLUS = 0x0004
    FANTI_JIANTI = 0x0008
    XINZIXING = 0x0010
    JIUZIXING = 0x0020
    SHINJITAI = 0x0040
    KYUJITAI = 0x0080
    PINYIN = 0x0100
    JYUTPING = 0x0200
    YALE_KOREAN = 0x0400
    QUOC_NGU = 0x0800
    ZHUANG = 0x1000
    SIP = 0x2000
    TIP = 0x4000


class CJK(CodePoint):
    __hash__ = int.__hash__

    def __repr__(self):
        return f"CJK({CodePoint(self)}, {chr(self)})"

    def __eq__(self, other):
        return isinstance(other, (CJK, CodePoint, int)) and int(self) == int(other)

    @classmethod
    def from_codepoint(cls, codepoint: CodePoint | None) -> CJK | None:
        return cls(codepoint) if codepoint else None

    def _in_blocks(self, keyword: str) -> bool:
        return any(keyword in b.name and b.start <= self <= b.end for b in CJKLoader.load_ucd_Blocks())

    def is_cjk_ideograph(self, compatibility: bool = False) -> bool:
        if self._in_blocks("Unified Ideograph"):
            return True
        if self._in_blocks("Compatibility Ideograph"):
            return compatibility or self in DISCRIMINATED_CJK
        return False

    def ids_babelsoft(self) -> IDSInfo | None:
        from babelsoft.utils_.dirs import Dirs

        lines = filter(line_has_content, TxtParser.get_txt(Dirs.BABELSTONE / "IDS.TXT"))
        return next((IDSInfo.from_line(line) for line in lines if IDSInfo.from_line(line).cjk == self), None)

    def radical_strokes(self) -> list[RS]:
        sources = CJKLoader.load_unihan_IRGSources().get(self, {})
        rs_list = []
        for data in sources.get("kRSUnicode", []):
            rs_list.extend(RS.from_unihan(token) for token in data.split())
        return rs_list

    def primary_radical_stroke(self) -> RS:
        rs = self.radical_strokes()
        if not rs:
            raise AssertionError(f"CJK {self} has no radical strokes")
        return rs[0]

    def to_equivalent(self) -> CJK | None:
        target = CJKLoader.load_ucd_EquivalentUnifiedIdeograph().get(self)
        return CJK.from_codepoint(target)

    def _raw_flags(self) -> int:
        return CJKLoader.load_flags().get(int(self), CJKFlags.NOTHING.value)

    def _has_flag(self, flag: int) -> bool:
        return (self._raw_flags() & flag) == flag

    def has_ivs(self) -> bool:
        return self._has_flag(CJKFlags.IVS.value)

    def is_traditional(self) -> bool:
        return self._has_flag(CJKFlags.FANTI.value)

    def is_simplified(self) -> bool:
        return self._has_flag(CJKFlags.JIANTI.value)

    def is_fanti_jianti(self) -> bool:
        return self._has_flag(CJKFlags.FANTI_JIANTI.value)

    def is_xinzixing(self) -> bool:
        return self._has_flag(CJKFlags.XINZIXING.value)

    def is_jiuzixing(self) -> bool:
        return self._has_flag(CJKFlags.JIUZIXING.value)

    def is_shinjitai(self) -> bool:
        return self._has_flag(CJKFlags.SHINJITAI.value)

    def is_kyujitai(self) -> bool:
        return self._has_flag(CJKFlags.KYUJITAI.value)

    def is_pinyin(self) -> bool:
        return self._has_flag(CJKFlags.PINYIN.value)

    def is_jyutping(self) -> bool:
        return self._has_flag(CJKFlags.JYUTPING.value)

    def is_yale_korean(self) -> bool:
        return self._has_flag(CJKFlags.YALE_KOREAN.value)

    def is_quoc_ngu(self) -> bool:
        return self._has_flag(CJKFlags.QUOC_NGU.value)

    def is_zhuang(self) -> bool:
        return self._has_flag(CJKFlags.ZHUANG.value)

    def filter_traditional(self) -> bool:
        return not self._has_flag(CJKFlags.JIANTI.value)

    def filter_simplified(self) -> bool:
        return not self._has_flag(CJKFlags.FANTI.value)

    def source_refs(self) -> str:
        irg = self._irg_data()
        return irg[1] if irg else ""

    def readings(self) -> dict[str, str]:
        return CJKLoader.load_unihan_Readings().get(int(self), {})

    # ── IVD (Ideographic Variation Database) ──────────────────────────
    # These correspond to the C++ functions in Unicode.cpp.

    def ivs_sequences(self) -> list[tuple[int, str, str]]:
        """Return all IVS sequences for this character.
        Each is (vs_codepoint, collection, reference).
        """
        cp = int(self)
        return [(vs, coll, ref) for base, vs, coll, ref in CJKLoader.load_ivd_sequences() if base == cp]

    def get_ideographic_variant(self, vs_cp: int):
        """Look up a specific IVS for this base character + variation selector.
        Returns (collection, reference) or None.
        Corresponds to C++ Unicode::GetIdeographicVariant.
        """
        result = CJKLoader.get_ideographic_variant(int(self), vs_cp)
        if result is None:
            return None
        return (result[0], result[1])

    def to_simplified(self):
        return CJK.from_codepoint(self._get_simplified_mapping(int(self)))

    @classmethod
    def _get_simplified_mapping(cls, cp: int):
        entry = CJKLoader.load_mappings().get(cp)
        if not entry:
            return None
        target, direction = entry
        if direction == "fanti":
            return target
        if direction == "fanti_jianti":
            return cls._get_simplified_mapping(target)
        return None

    def to_traditional(self):
        return CJK.from_codepoint(self._get_traditional_mapping(int(self)))

    @classmethod
    def _get_traditional_mapping(cls, cp: int):
        entry = CJKLoader.load_mappings().get(cp)
        if not entry:
            return None
        target, direction = entry
        if direction in ("jianti", "fanti_jianti"):
            return target
        return None

    def to_shinjitai(self):
        return CJK.from_codepoint(CJKLoader.load_shinjitai_maps()[1].get(int(self))) if self.is_kyujitai() else None

    def to_kyujitai(self):
        return CJK.from_codepoint(CJKLoader.load_shinjitai_maps()[0].get(int(self))) if self.is_shinjitai() else None

    def to_xinzixing(self):
        return CJK.from_codepoint(CJKLoader.load_xinjiu_maps()[1].get(int(self))) if self.is_jiuzixing() else None

    def to_jiuzixing(self):
        return CJK.from_codepoint(CJKLoader.load_xinjiu_maps()[0].get(int(self))) if self.is_xinzixing() else None

    def _irg_data(self):
        return CJKLoader.load_cjk_irg_sources().get(int(self))

    def get_source_ref(self, source: str) -> str:
        """One IRG source reference ("" when absent); mirrors C++ CJK::GetSourceRef.

        Disambiguates K from KP the way the C++ does (replace " KP" with " XP"
        before searching for " K"), handles Singapore (GS- / SG- refs share the
        kIRG_GSource column with China), and returns "" for Malaysia (not yet a
        separate Unihan source).
        """
        if source == "MY":
            return ""
        if source == "SG":
            g = CJKLoader.load_unihan_IRGSources().get(self, {}).get("kIRG_GSource", [])
            return next((r for r in g if r.startswith(("GS-", "SG-"))), "")
        irg = self._irg_data()
        if not irg or source not in irg[0]:
            return ""
        refs = irg[1]
        if source == "KP":
            pattern = " KP"
        elif source == "K":
            refs = refs.replace(" KP", " XP")
            pattern = " K"
        else:
            pattern = SRC_PATTERN_MAP.get(source, f" {source}")
        ref_str = f" {refs},"
        idx = ref_str.find(pattern)
        if idx == -1:
            return ""
        end = ref_str.find(",", idx + 1)
        return ref_str[idx + 1 : end].strip() if end != -1 else ref_str[idx + 1 :].strip()

    @staticmethod
    def find_source_ref(ref: str, *, exact: bool = True):
        rev_map = CJKLoader.load_cjk_irg_reverse()
        if exact:
            return CJK.from_codepoint(rev_map.get(ref.strip()))
        for rs, cp in rev_map.items():
            if ref.strip() in rs:
                return CJK(cp)
        return None

    def is_source(
        self,
        sources: int,
        match: int = 0,
        inverse: bool = False,
        unified_only: bool = False,
        source_ref: str | None = None,
    ):
        irg = self._irg_data()
        if not irg:
            return False, ""
        if unified_only and not self._in_blocks("Unified Ideograph"):
            return False, ""
        src_list, refs = irg
        mask = sum(SRC_BIT_MAP[s] for s in src_list if s in SRC_BIT_MAP)

        if match == 0:
            ok = (mask & sources) != 0
        elif match == 1:
            ok = (mask & sources) == sources
        else:
            ok = mask == sources

        if inverse:
            ok = not ok
        if ok and source_ref and source_ref.strip() not in refs:
            ok = False
        return ok, refs if ok else ""

    @staticmethod
    def get_radical_glyph(index: int):
        rad_map = CJKLoader.load_radical_mappings()
        return CJK(rad_map[index][0]) if 0 <= index < len(rad_map) else None

    @staticmethod
    def get_radical_number(index: int) -> int:
        rad_map = CJKLoader.load_radical_mappings()
        return rad_map[index][1] if 0 <= index < len(rad_map) else 0

    @staticmethod
    def get_radical_flag(index: int) -> int:
        rad_map = CJKLoader.load_radical_mappings()
        return rad_map[index][2] if 0 <= index < len(rad_map) else 0

    @staticmethod
    def find_ideographs_for_radical(
        radical: int, flag: int = 0, strokes: int = -1, *, fuzzy: bool = False, all_strokes: bool = False
    ):
        data = CJKLoader.load_radical_data().get((radical, flag), [])
        if all_strokes:
            return [CJK(cp) for _, cp in data]
        if strokes < 0:
            return []
        min_s, max_s = (max(0, strokes - 1), strokes + 1) if fuzzy else (strokes, strokes)
        return [CJK(cp) for s, cp in data if min_s <= s <= max_s]

    def to_equivalent_extended(self):
        return self.to_equivalent() or CJK.from_codepoint(CJKLoader.load_radical_equivs().get(int(self)))

    def adjust_simplified(self, prev=None, next=None):
        return self._adjust(CJKLoader.load_simp_adjustments(), prev, next)

    def adjust_traditional(self, prev=None, next=None):
        return self._adjust(CJKLoader.load_trad_adjustments(), prev, next)

    def _adjust(self, table: dict[int, list[tuple[int, int, int]]], prev: CJK | None, next: CJK | None) -> CJK | None:
        rules = table.get(int(self))
        if not rules:
            return None
        pc = int(prev) if prev else 0xFFFF
        nc = int(next) if next else 0xFFFF
        for rp, rn, target in rules:
            if (rp == 0xFFFF or rp == pc) and (rn == 0xFFFF or rn == nc):
                return CJK(target)
        return None

    def get_mappings(self):
        ct = cs = cj = None
        if self.is_traditional():
            ct, cs = self, self.to_simplified()
        if self.is_kyujitai():
            ct, cj = self, self.to_shinjitai()
        if self.is_simplified():
            cs = self
            t = self.to_traditional()
            if t:
                ct, cj = t, t.to_shinjitai()
        if self.is_shinjitai():
            cj = self
            t = self.to_kyujitai()
            if t:
                ct, cs = t, t.to_simplified()
        return ct, cs, cj

    @staticmethod
    def _glyph(cjk: CJK | None) -> dict | None:
        """{cp, char} for a related character, or None."""
        if cjk is None:
            return None
        cp = int(cjk)
        return {"cp": cp, "char": chr(cp)}

    def _primary_ids(self) -> str:
        """Primary IDS sequence ("" when none)."""
        info = self.ids_babelsoft()
        if not info or not info.ids_list:
            return ""
        m = _IDS_WRAPPER.match(info.ids_list[0].ids)
        return m.group(1) if m else info.ids_list[0].ids.strip()

    def ideographic_properties(self) -> dict:
        """Ideographic (CJKV) properties — mirrors the C++ CDialogCJKV dialog.

        Returns {} when this is not a CJK ideograph. Source order/labels come
        from :class:`SrcRef.IRGSrc` (display_order / display).
        """
        if not self.is_cjk_ideograph():
            return {}

        radical_glyph = None
        radical_strokes = ""
        radical_type = ""
        rs_list = self.radical_strokes()
        if rs_list:
            rs = rs_list[0]
            radical_strokes = rs.to_unihan()
            radical_type = (
                ["Traditional", "Simplified", "Japanese", "Vietnamese"][rs.variant] if rs.variant <= 3 else ""
            )
            try:
                radical_glyph = self._glyph(rs.radical_char_normalized())
            except ValueError:
                radical_glyph = None

        ct, cs, cj = self.get_mappings()
        readings = self.readings()

        return {
            "radical": {"glyph": radical_glyph, "strokes": radical_strokes, "type": radical_type},
            "ids": self._primary_ids(),
            "related": {
                "traditional": self._glyph(ct),
                "simplified_chinese": self._glyph(cs),
                "simplified_japanese": self._glyph(cj),
            },
            "readings": {
                "mandarin": readings.get("kMandarin", ""),
                "cantonese": readings.get("kCantonese", ""),
                "korean": readings.get("kKorean", ""),
                "vietnamese": readings.get("kVietnamese", ""),
            },
            "sources": [
                [src.display or src.label, self.get_source_ref(code)] for code, src in SrcRef.IRGSrc.display_order()
            ],
        }

    @staticmethod
    def get_codepoint(block: int, ch16: int) -> int:
        """Get the Unicode codepoint for a given CJK block index and 16-bit offset.

        Equivalent to C++ CJK::GetCodepoint(block, ch16).
        The block index selects a CJK Unified Ideograph block (0=main, 1=compat,
        2=Ext-A, ..., 12=Ext-J) and ch16 is the offset within that block.
        """
        offsets = CJKLoader.load_cjk_ui_offsets()
        if 0 <= block < len(offsets):
            return offsets[block] + ch16
        return 0

    def get_xml_data(self, indent: bool = False) -> str:
        _RTYPES = {0: "Traditional", 1: "Simplified", 2: "Japanese", 3: "Vietnamese"}
        char = ET.Element("Character", cp=f"{int(self):04X}", unicode=chr(self))

        rs_elem = ET.SubElement(char, "RadicalStrokes")
        if rsl := self.radical_strokes():
            rs = rsl[0]
            rg = rs.radical_char() if rs.variant == 0 else rs.radical_char_normalized()
            rad = ET.SubElement(
                rs_elem,
                "Radical",
                cp=f"{int(rg):04X}",
                index=str(rs.radical.rad),
                type=_RTYPES.get(rs.variant, "Traditional"),
            )
            rad.text = chr(rg)
            ET.SubElement(rs_elem, "RadicalStrokeCodes").text = rs.to_unihan()

        if (ii := self.ids_babelsoft()) and ii.ids_list:
            ET.SubElement(char, "IDS").text = ii.ids_list[0].ids

        rc_elem = ET.SubElement(char, "RelatedChars")
        t, sc, sj = self.get_mappings()
        if t:
            ET.SubElement(rc_elem, "Traditional", cp=f"{int(t):04X}").text = chr(t)
        if sc:
            ET.SubElement(rc_elem, "SimplifiedChinese", cp=f"{int(sc):04X}").text = chr(sc)
        if sj:
            ET.SubElement(rc_elem, "SimplifiedJapanese", cp=f"{int(sj):04X}").text = chr(sj)

        # Readings from Unihan
        rd = self.readings()
        if rd:
            r_elem = ET.SubElement(char, "Readings")
            for field, tag in (
                ("kMandarin", "Mandarin"),
                ("kCantonese", "Cantonese"),
                ("kKorean", "Korean"),
                ("kVietnamese", "Vietnamese"),
                ("kZhuang", "Zhuang"),
            ):
                if val := rd.get(field):
                    ET.SubElement(r_elem, tag).text = val

        # Source references from IRG
        src_data = {v.label: self.get_source_ref(k) for k, v in SrcRef.IRGSrc.all().items()}
        if any(src_data.values()):
            sr_elem = ET.SubElement(char, "SourceReferences")
            for tag, ref in src_data.items():
                if ref:
                    ET.SubElement(sr_elem, tag).text = ref

        ET.indent(char, space="\t")
        raw = ET.tostring(char, encoding="unicode")
        lines = raw.rstrip().split("\n")
        if indent:
            lines = ["\t\t" + line for line in lines]
        return "\r\n".join(lines)

    def source_reference(self, *, submitter: _Src | list[_Src] | None = None) -> list[SrcRef]:
        data = CJKLoader.load_unihan_IRGSources().get(self, {})
        if isinstance(submitter, _Src):
            submitters = [submitter]
        else:
            submitters = submitter or list(SrcRef.IRGSrc.all().values())
        seen: set[str] = set()
        out: list[SrcRef] = []
        for src in submitters:
            # Singapore shares the kIRG_GSource column with China — dedupe by
            # field so it isn't reported twice; when queried alone, return only
            # its GS- / SG- references.
            if src.field in seen:
                continue
            seen.add(src.field)
            refs = data.get(src.field, [])
            if src.name == "SINGAPORE":
                sg = [r for r in refs if r.startswith(("GS-", "SG-"))]
                if sg:
                    out.append(SrcRef(sg[0]))
            elif refs:
                out.append(SrcRef(refs[0]))
        return out
