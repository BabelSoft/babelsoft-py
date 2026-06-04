from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum

from src.unicode.class_ import CodePoint
from src.utils_.loader import CJKLoader, DISCRIMINATED_CJK, _SRC_BIT_MAP, _SRC_PATTERN_MAP
from src.utils_.parser import TxtParser, line_has_content


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


@dataclass
class SrcRef:
    reference: str = ""

    class Submitter(Enum):
        CHINA_SINGAPORE = "G"
        HONG_KONG_SAR = "H"
        JAPAN = "J"
        ROK = "K"
        DPRK = "KP"
        MACAO_SAR = "M"
        MALAYSIA = "MY"
        SAT = "SAT"
        TCA = "T"
        UK = "UK"
        US_UTC = "UTC"
        VIETNAM = "V"

        def __repr__(self):
            return self.name

    @property
    def prefix(self) -> str:
        return self.reference.split("-", 1)[0]

    @property
    def submitter(self) -> SrcRef.Submitter:
        ref = self.reference.strip().upper()
        mapping = {
            "G": self.Submitter.CHINA_SINGAPORE,
            "H": self.Submitter.HONG_KONG_SAR,
            "T": self.Submitter.TCA,
            "J": self.Submitter.JAPAN,
            "KP": self.Submitter.DPRK,
            "K": self.Submitter.ROK,
            "MY": self.Submitter.MALAYSIA,
            "M": self.Submitter.MACAO_SAR,
            "UK": self.Submitter.UK,
            "UTC": self.Submitter.US_UTC,
            "V": self.Submitter.VIETNAM,
        }
        for key, val in mapping.items():
            if ref.startswith(key):
                return val
        raise ValueError(f"Unknown submitter: {ref}")

    def find(self) -> CJK | None:
        cp = CJKLoader.load_cjk_irg_reverse().get(self.reference)
        return CJK(cp) if cp else None

    def is_valid(self) -> bool:
        return self.find() is not None


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
            return compatibility and self in DISCRIMINATED_CJK
        return False

    def ids_babelsoft(self) -> IDSInfo | None:
        from src.utils_.dirs import Dirs

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

    def to_simplified(self):
        return CJK.from_codepoint(self._get_simplified_mapping(int(self)))

    @classmethod
    def _get_simplified_mapping(cls, cp: int):
        mapping = CJKLoader.load_mappings().get(cp)
        if not mapping:
            return None
        flags = CJKLoader.load_flags().get(cp, 0)
        if flags & CJKFlags.FANTI.value:
            return mapping
        if flags & CJKFlags.FANTI_JIANTI.value:
            return cls._get_simplified_mapping(mapping)
        return None

    def to_traditional(self):
        return CJK.from_codepoint(self._get_traditional_mapping(int(self)))

    @classmethod
    def _get_traditional_mapping(cls, cp: int):
        mapping = CJKLoader.load_mappings().get(cp)
        if not mapping:
            return None
        flags = CJKLoader.load_flags().get(cp, 0)
        if flags & (CJKFlags.JIANTI.value | CJKFlags.FANTI_JIANTI.value):
            return mapping
        return None

    def to_shinjitai(self):
        return CJK.from_codepoint(CJKLoader.load_shinjitai_maps()[0].get(int(self))) if self.is_kyujitai() else None

    def to_kyujitai(self):
        return CJK.from_codepoint(CJKLoader.load_shinjitai_maps()[1].get(int(self))) if self.is_shinjitai() else None

    def to_xinzixing(self):
        return CJK.from_codepoint(CJKLoader.load_xinjiu_maps()[0].get(int(self))) if self.is_jiuzixing() else None

    def to_jiuzixing(self):
        return CJK.from_codepoint(CJKLoader.load_xinjiu_maps()[1].get(int(self))) if self.is_xinzixing() else None

    def _irg_data(self):
        return CJKLoader.load_cjk_irg_sources().get(int(self))

    def get_source_ref(self, source: str) -> str:
        irg = self._irg_data()
        if not irg or source not in irg[0]:
            return ""
        pattern = _SRC_PATTERN_MAP.get(source, f" {source}")
        ref_str = f" {irg[1]},"
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
        mask = sum(_SRC_BIT_MAP[s] for s in src_list if s in _SRC_BIT_MAP)

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

    def get_xml_data(self, indent: bool = False) -> str:
        char = ET.Element("Character", cp=f"{int(self):04X}", unicode=chr(self))

        rs_elem = ET.SubElement(char, "RadicalStrokes")
        if rsl := self.radical_strokes():
            rs = rsl[0]
            rg = rs.radical_char() if rs.variant == 0 else rs.radical_char_normalized()
            rad = ET.SubElement(rs_elem, "Radical", cp=f"{int(rg):04X}", index=str(rs.radical.rad), type="Traditional")
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

        ET.indent(char, space="\t")
        raw = ET.tostring(char, encoding="unicode")
        lines = raw.rstrip().split("\n")
        if indent:
            lines = ["\t\t" + line for line in lines]
        return "\r\n".join(lines)

    def source_reference(self, *, submitter: SrcRef.Submitter | list[SrcRef.Submitter] | None = None) -> list[SrcRef]:
        data = CJKLoader.load_unihan_IRGSources().get(self, {})
        submitters = [submitter] if isinstance(submitter, SrcRef.Submitter) else (submitter or list(SrcRef.Submitter))
        return [SrcRef(data[f"kIRG_{s.value}Source"][0]) for s in submitters if data.get(f"kIRG_{s.value}Source")]
