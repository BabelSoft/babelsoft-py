from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from enum import Enum

from src.utils_.dirs import Dirs
from src.utils_.parser import TxtParser

DISCRIMINATED_CJK = {0xFA0E, 0xFA0F, 0xFA11, 0xFA13, 0xFA14, 0xFA1F, 0xFA21, 0xFA23, 0xFA24, 0xFA27, 0xFA28, 0xFA29}


class CodePoint(int):
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
    def from_(cls, value: int | str | CodePoint | CJK | None) -> CodePoint | None:
        if not value:
            return None
        if isinstance(value, int | CodePoint | CJK):
            return cls(value)
        value = value.strip()
        if len(value) == 1:
            return cls(ord(value))
        if value.upper().startswith("U+"):
            value = value[2:]
        if value.lower().startswith("0x"):
            value = value[2:]
        if re.fullmatch(r"[0-9A-Fa-f]{4,6}", value):
            return cls(int(value, 16))
        return None


@dataclass
class Block:
    start: CodePoint
    end: CodePoint
    name: str

    def __repr__(self) -> str:
        start_hex = hex(self.start).upper().replace("0X", "0x")
        end_hex = hex(self.end).upper().replace("0X", "0x")
        return f'Block("{self.name}", {start_hex}..{end_hex})'


@functools.lru_cache(maxsize=1)
def load_ucd_Blocks() -> list[Block]:
    blocks_dir = Dirs.UCD / "Blocks.txt"
    txt = TxtParser.get_txt(blocks_dir)
    txt = TxtParser.filter(txt, line_has_content)
    parsed = TxtParser.match(txt, re.compile(r"([\da-fA-F]+)\.\.([\da-fA-F]+); (.+)"))
    return [Block(int(s, 16), int(e, 16), name.strip()) for s, e, name in parsed]  # type: ignore


@functools.lru_cache(maxsize=1)
def load_charts_RSIndex() -> dict[RS, list[CJK]]:
    rs_index_file = Dirs.CHARTS / "RSIndex.txt"
    lines = TxtParser.filter(TxtParser.get_txt(rs_index_file), line_has_content)
    lines = [line.split("#")[0].rstrip() for line in lines]

    result = {}
    sep_pattern = re.compile(r"(\|+)\s*")

    def _add_entry(base_rs: RS, variant: int, data_str: str):
        if data_str:
            data_str = data_str.strip()
            rs_obj = RS(radical=Radical(base_rs.radical.rad, variant), residual_stroke=base_rs.residual_stroke)
            result[rs_obj] = [CJK.from_(val) for val in data_str.split()]

    for line in lines:
        rs_part, data_part = line.split("\t", maxsplit=1)
        base_rs = RS.from_unihan(rs_part)
        matches = list(sep_pattern.finditer(data_part))
        radical = data_part[: matches[0].start()].strip() if matches else data_part.strip()
        _add_entry(base_rs, 0, radical)

        for i, match in enumerate(matches):
            variant = len(match.group(1))
            end = matches[i + 1].start() if (i + 1 < len(matches)) else len(data_part)
            variant_data = data_part[match.end() : end].strip()
            _add_entry(base_rs, variant, variant_data)
    return result


@functools.lru_cache(maxsize=1)
def load_ucd_CJKRadicals() -> dict[RS, tuple[CJK, CJK]]:
    cjk_radicals_file = Dirs.UCD / "CJKRadicals.txt"
    lines = TxtParser.get_txt(cjk_radicals_file)
    lines = TxtParser.filter(lines, line_has_content)

    cjk_radicals_dict = {}
    for line in lines:
        matches = re.match(r"([\da-fA-F]+); ([\da-fA-F]+); ([\da-fA-F]+)", line)
        if matches:
            cjk_radicals_dict[RS.from_unihan(matches.group(1))] = (
                CJK.from_(matches.group(2)),
                CJK.from_(matches.group(3)),
            )
    return cjk_radicals_dict


BIG_NUMBER = 100


@dataclass(frozen=True)
class Radical:
    rad: int
    var: int = 0

    def __repr__(self) -> str:
        return f"Radical({self.rad}, {self.var})"

    def to_unihan(self) -> str:
        return f"{self.rad}{self.var * "'"}"

    def to_irg_radical(self) -> str:
        return f"{self.rad}.{self.var}"

    @classmethod
    def from_unihan(cls, text: str) -> Radical:
        radical = text.split(".")[0]
        for i in range(BIG_NUMBER, 0, -1):
            if radical.endswith("'" * i):
                rad, var = radical[:-i], i
                break
        else:
            rad, var = radical, 0
        return cls(int(rad), var)

    def __eq__(self, other: Radical):
        return (self.rad, self.var) == (other.rad, other.var)


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
        """
        >>> RS(radical=Radical(212, 3), residual_stroke=-1).to_unihan()
        "212'''.-1"
        """
        variant_map = {0: "", 1: "'", 2: "''", 3: "'''"}
        variant = variant_map.get(self.radical.var, "")
        return f"{self.radical.rad}{variant}.{self.residual_stroke}"

    def no_variant(self) -> RS:
        """
        >>> RS(radical=Radical(212, 3), residual_stroke=-1).no_variant()
        RS(radical=Radical(212, 0), residual_stroke=-1)
        """
        return RS(radical=Radical(self.radical.rad, 0), residual_stroke=self.residual_stroke)

    @classmethod
    def from_unihan(cls, text: str) -> RS:
        """
        >>> RS.from_unihan("212'''.6"), RS.from_unihan("212'''")
        (RS(radical=Radical(212, 3), residual_stroke=6), RS(radical=Radical(212, 3), residual_stroke=0))
        """
        radical_variant, *stroke = text.split(".")
        stroke = stroke[0] if stroke else 0
        for i in range(BIG_NUMBER, 0, -1):
            if radical_variant.endswith("'" * i):
                radical, variant = radical_variant[:-i], i
                break
        else:
            radical, variant = radical_variant, 0
        return cls(radical=Radical(int(radical), variant), residual_stroke=int(stroke))

    def to_irg_radical(self) -> str:
        """
        >>> RS(radical=Radical(212, 3), residual_stroke=6).to_irg_radical()
        '212.3'
        """
        return f"{self.radical.rad}.{self.radical.var}"

    @classmethod
    def from_irg_radical(cls, text: str) -> RS:
        """
        >>> RS.from_irg_radical("212.3"), RS.from_irg_radical("212.0")
        (RS(radical=Radical(212, 3), residual_stroke=0), RS(radical=Radical(212, 0), residual_stroke=0))
        """
        radical, variant = text.split(".")
        return cls(radical=Radical(int(radical), int(variant)), residual_stroke=0)

    def radical_char(self) -> CJK:
        """Use Kangxi radicals first."""
        data = load_ucd_CJKRadicals()
        radical_variant = RS(radical=self.radical, residual_stroke=0)
        if radical_variant not in data:
            raise ValueError(f"Radical variant {radical_variant} not found")
        if bad_radical := data[radical_variant][0]:
            return bad_radical
        return self.radical_char_normalized()

    def radical_char_normalized(self) -> CJK:
        """Use CJKUI radicals first."""
        data = load_ucd_CJKRadicals()
        radical_variant = RS(radical=self.radical, residual_stroke=0)
        if radical_variant not in data:
            raise ValueError(f"Radical variant {radical_variant} not found")
        return data[radical_variant][1]

    def ideographs(self) -> list[CJK]:
        return load_charts_RSIndex().get(self, [])


@dataclass
class IDS:
    ids: str


def line_has_content(line: str) -> bool:
    return bool(line.split("#")[0].rstrip())


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
        if len(parts) < 1:
            return None
        cjk = CJK(parts[0])
        ids_fields = [field for field in parts[2:] if field.startswith("^")]
        ids_list = [IDS(ids=ids.strip()) for ids in ids_fields]
        comment_fields = [field[1:] for field in parts[2:] if field.startswith("*")]
        comment = comment_fields[0].removeprefix("*") if comment_fields else ""
        return cls(cjk=cjk, ids_list=ids_list, comment=comment)

    def __repr__(self) -> str:
        return f"IDSInfo(cjk={self.cjk}, ids={self.ids_list}, comment={self.comment})"


@functools.lru_cache(maxsize=1)
def load_unihan_IRGSources() -> dict[CodePoint, dict[str, list[str]]]:
    lines = TxtParser.get_txt(Dirs.UNIHAN / "Unihan_IRGSources.txt")
    values: dict[CodePoint, dict[str, list[str]]] = {}
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.strip().split("\t")
        if len(parts) < 3:
            continue
        codepoint_text, field, data = parts[0], parts[1], "\t".join(parts[2:])
        codepoint = CodePoint.from_(codepoint_text)
        if codepoint is None:
            continue
        values.setdefault(codepoint, {}).setdefault(field, []).append(data)
    return values


@functools.lru_cache(maxsize=1)
def load_ucd_EquivalentUnifiedIdeograph() -> dict[CodePoint, CodePoint]:
    lines = TxtParser.get_txt(Dirs.UCD / "EquivalentUnifiedIdeograph.txt")
    lines = TxtParser.filter(lines, line_has_content)
    parsed = TxtParser.match(lines, re.compile(r"^\s*([0-9A-Fa-f]+)(?:\.\.([0-9A-Fa-f]+))?\s*;\s*([0-9A-Fa-f]+)"))
    equivalents: dict[CodePoint, CodePoint] = {}
    for start_hex, end_hex, target_hex in parsed:
        start = CodePoint.from_(start_hex)
        if not end_hex or end_hex == "None":
            end = start
        else:
            end = CodePoint.from_(end_hex)
        target = CodePoint.from_(target_hex)
        for codepoint in range(start, end + 1):  # type: ignore
            equivalents[codepoint] = target  # type: ignore
    return equivalents


@dataclass
class SrcRef:
    reference: str = ""

    @property
    def prefix(self) -> str:
        return self.reference.split("-")[0]

    @property
    def submitter(self) -> SrcRef.Submitter:
        return self.get_submitter_source(self.reference)

    def get_submitter_source(self, ref: str) -> SrcRef.Submitter:
        ref = ref.strip().upper()
        if ref.startswith("G"):
            return self.Submitter.CHINA_SINGAPORE
        if ref.startswith("H"):
            return self.Submitter.HONG_KONG_SAR
        if ref.startswith("T"):
            return self.Submitter.TCA
        if ref.startswith("J"):
            return self.Submitter.JAPAN
        if ref.startswith("KP"):
            return self.Submitter.DPRK
        if ref.startswith("K"):
            return self.Submitter.ROK
        if ref.startswith("MY"):
            return self.Submitter.MALAYSIA
        if ref.startswith("M"):
            return self.Submitter.MACAO_SAR
        if ref.startswith("SAT"):
            return self.Submitter.SAT
        if ref.startswith("UK"):
            return self.Submitter.UK
        if ref.startswith("UTC"):
            return self.Submitter.US_UTC
        assert ref.startswith("V"), f"Unknown submitter: {ref}"
        return self.Submitter.VIETNAM

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

    def find(self) -> CJK | None:
        for codepoint, fields in load_unihan_IRGSources().items():
            for value in fields.values():
                if self.reference in value:
                    return CJK(codepoint)
        return None

    def is_valid(self) -> bool:
        return self.find() is not None


class CJK(CodePoint):
    __hash__ = int.__hash__

    @classmethod
    def from_codepoint(cls, codepoint: CodePoint | None) -> CJK | None:
        if codepoint is None:
            return None
        return cls(codepoint)

    def __repr__(self):
        return f"CJK({CodePoint(self)}, {chr(self)})"

    def __eq__(self, other):
        if isinstance(other, (CJK, CodePoint, int)):
            return int(self) == int(other)
        return False

    def _is_cjk_unified_ideograph(self) -> bool:
        def _cjkui(b: Block) -> bool:
            return "CJK" in b.name and "Ideographs" in b.name and "Compatibility" not in b.name

        blocks = filter(_cjkui, load_ucd_Blocks())
        for block in blocks:
            if block.start <= self <= block.end:
                return True
        return False

    def _is_cjk_compatibility_ideograph(self) -> bool:
        def _compat(b: Block) -> bool:
            return "CJK" in b.name and "Ideographs" in b.name and "Compatibility" in b.name

        blocks = filter(_compat, load_ucd_Blocks())
        for block in blocks:
            if block.start <= self <= block.end:
                return True
        return False

    def is_cjk_ideograph(self, compatibility: bool = False) -> bool:
        if self._is_cjk_unified_ideograph():
            return True
        if self._is_cjk_compatibility_ideograph():
            if compatibility:
                return True
            return self in DISCRIMINATED_CJK
        return False

    def ids_babelsoft(self) -> IDSInfo | None:
        lines = TxtParser.get_txt(Dirs.BABELSTONE / "IDS.TXT")
        lines = TxtParser.filter(lines, line_has_content)
        ids_info_list = [IDSInfo.from_line(line) for line in lines]
        return next(filter(lambda x: x.cjk == self, ids_info_list), None)  # type: ignore

    def radical_strokes(self) -> list[RS]:
        sources = load_unihan_IRGSources().get(self)
        if not sources:
            return []
        values = []
        for data in sources.get("kRSUnicode", []):
            values.extend([RS.from_unihan(token) for token in data.split()])
        return values

    def primary_radical_stroke(self) -> RS:
        assert self.radical_strokes(), f"CJK {self} has no radical strokes"
        return self.radical_strokes()[0]

    @staticmethod
    def to_simplified() -> CJK | None:
        # TODO: the logic may be related to `kSimplifiedVariant` in the Unihan database.
        # Andrew have maintained the related data, but the data is quite different and
        # needs to be reviewed and merged into the Unihan database.
        ...

    @staticmethod
    def to_traditional() -> CJK | None:
        # TODO: the logic may be related to `kTraditionalVariant` in the Unihan database.
        # Andrew have maintained the related data, but the data is quite different and
        # needs to be reviewed and merged into the Unihan database.
        ...

    def to_equivalent(self) -> CJK | None:
        equivalents = load_ucd_EquivalentUnifiedIdeograph()
        target = equivalents.get(self)
        return CJK.from_codepoint(target)

    @staticmethod
    def to_shinjitai() -> CJK | None:
        # TODO: the data has been extract to `babelsoft/ShinjitaiMapping.yaml`.
        # We found multiple shinjitai mappings to multiple kyujitai, so the logic is complex.
        ...

    @staticmethod
    def to_kyujitai() -> CJK | None:
        # TODO: the data has been extract to `babelsoft/ShinjitaiMapping.yaml`.
        # We found multiple shinjitai mappings to multiple kyujitai, so the logic is complex.
        ...

    @staticmethod
    def to_xinzixing() -> CJK | None:
        # TODO: the data has been extract to `babelsoft/XinJiuMapping.yaml`.
        # The logic is simple.
        ...

    @staticmethod
    def to_jiuzixing() -> CJK | None:
        # TODO: the data has been extract to `babelsoft/XinJiuMapping.yaml`.
        # The logic is simple.
        ...

    def source_reference(self, *, submitter: SrcRef.Submitter | list[SrcRef.Submitter] | None = None) -> list[SrcRef]:
        data = load_unihan_IRGSources().get(self)
        if not data:
            return []
        submitters = [submitter] if isinstance(submitter, SrcRef.Submitter) else (submitter or list(SrcRef.Submitter))

        results = []
        for submitter in submitters:
            if result := data.get(f"kIRG_{submitter.value}Source", ""):
                results.append(SrcRef(result[0]))
        return results
