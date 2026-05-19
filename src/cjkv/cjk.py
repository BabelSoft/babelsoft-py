from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from src.utils_.parser import TxtParser
from src.utils_.paths import DATA_BABELSTONE_DIR, DATA_UCD_DIR, DATA_UNIHAN_DIR

DISCRIMINATED_IDEOGRAPHS = {
    0xFA0E,
    0xFA0F,
    0xFA11,
    0xFA13,
    0xFA14,
    0xFA1F,
    0xFA21,
    0xFA23,
    0xFA24,
    0xFA27,
    0xFA28,
    0xFA29,
}


class CodePoint(int):
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
    def from_(cls, value: int | str) -> CodePoint:
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
def load_Blocks() -> list[Block]:
    blocks_dir = DATA_UCD_DIR / "Blocks.txt"
    txt = TxtParser.get_txt_lines(blocks_dir)
    txt = TxtParser.filter(txt, line_has_content)
    parsed = TxtParser.match(txt, re.compile(r"([\da-fA-F]+)\.\.([\da-fA-F]+); (.+)"))
    return [Block(int(start, 16), int(end, 16), name.strip()) for start, end, name in parsed]


@dataclass
class RS:
    radical: int
    variant: int
    stroke: int

    def to_unihan(self) -> str:
        variant_map = {0: "", 1: "'", 2: "''", 3: "'''"}
        variant = variant_map.get(self.variant, "")
        return f"{self.radical}{variant}.{self.stroke}"

    @classmethod
    def from_unihan(cls, text: str) -> RS:
        radical_variant, stroke = text.split(".")
        if radical_variant.endswith("'''"):
            radical, variant = radical_variant[:-3], 3
        elif radical_variant.endswith("''"):
            radical, variant = radical_variant[:-2], 2
        elif radical_variant.endswith("'"):
            radical, variant = radical_variant[:-1], 1
        else:
            radical, variant = radical_variant, 0
        return cls(radical=int(radical), variant=variant, stroke=int(stroke))

    def to_irg_radical(self) -> str:
        return f"{self.radical}.{self.variant}"

    def from_irg_radical(cls, text: str) -> tuple[int, int]:
        radical, variant = text.split(".")
        return int(radical), int(variant)

    def radical_char(self) -> str: ...

    def radical_char_normalized(self) -> str: ...


@dataclass
class IDS:
    ids: str


def line_has_content(line: str) -> bool:
    return bool(line.split("#")[0].strip())


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

    @classmethod
    def from_dir(cls, dir_path: Path) -> list[IDSInfo]:
        lines = TxtParser.get_txt_lines(dir_path / "IDS.TXT")
        lines = TxtParser.filter(lines, line_has_content)
        return [cls.from_line(line) for line in lines]

    def __repr__(self) -> str:
        return f"IDSInfo(cjk={self.cjk}, ids_list={self.ids_list}, comment={self.comment})"


@functools.lru_cache(maxsize=1)
def load_Unihan_IRGSources() -> dict[CodePoint, dict[str, list[str]]]:
    lines = TxtParser.get_txt_lines(DATA_UNIHAN_DIR / "Unihan_IRGSources.txt")
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
def load_EquivalentUnifiedIdeograph() -> dict[CodePoint, CodePoint]:
    lines = TxtParser.get_txt_lines(DATA_UCD_DIR / "EquivalentUnifiedIdeograph.txt")
    lines = TxtParser.filter(lines, line_has_content)
    parsed = TxtParser.match(
        lines, re.compile(r"^\s*([0-9A-Fa-f]{4,6})(?:\.\.([0-9A-Fa-f]{4,6}))?\s*;\s*([0-9A-Fa-f]{4,6})")
    )
    equivalents: dict[CodePoint, CodePoint] = {}
    for start_hex, end_hex, target_hex in parsed:
        start = CodePoint.from_(start_hex)
        if not end_hex or end_hex == "None":
            end = start
        else:
            end = CodePoint.from_(end_hex)
        target = CodePoint.from_(target_hex)
        for codepoint in range(start, end + 1):
            equivalents[codepoint] = target
    return equivalents


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


@dataclass
class SrcRef:
    submitter: Submitter
    reference: str

    @staticmethod
    def get_submitter_source(ref: str) -> Submitter:
        ref = ref.strip().upper()
        if ref.startswith("KP"):
            return Submitter.DPRK
        elif ref.startswith("K"):
            return Submitter.ROK
        elif ref.startswith("G"):
            return Submitter.CHINA_SINGAPORE
        elif ref.startswith("H"):
            return Submitter.HONG_KONG_SAR
        elif ref.startswith("J"):
            return Submitter.JAPAN
        elif ref.startswith("MY"):
            return Submitter.MALAYSIA
        elif ref.startswith("M"):
            return Submitter.MACAO_SAR
        elif ref.startswith("SAT"):
            return Submitter.SAT
        elif ref.startswith("T"):
            return Submitter.TCA
        elif ref.startswith("UK"):
            return Submitter.UK
        elif ref.startswith("UTC"):
            return Submitter.US_UTC
        assert ref.startswith("V"), f"Unknown submitter: {ref}"
        return Submitter.VIETNAM


class CJK(CodePoint):
    __hash__ = int.__hash__

    def __repr__(self):
        return f"CJK(U+{self:04X}, {chr(self)})"

    def __eq__(self, other):
        if isinstance(other, (CJK, CodePoint, int)):
            return int(self) == int(other)
        return False

    @property
    def is_cjk_unified_ideograph(self) -> bool:
        def _cjkui(b: Block) -> bool:
            return "CJK" in b.name and "Ideographs" in b.name and "Compatibility" not in b.name

        blocks = filter(_cjkui, load_Blocks())
        for block in blocks:
            if block.start <= self <= block.end:
                return True
        return False

    @property
    def is_cjk_compatibility_ideograph(self) -> bool:
        def _compat(b: Block) -> bool:
            return "CJK" in b.name and "Ideographs" in b.name and "Compatibility" in b.name

        blocks = filter(_compat, load_Blocks())
        for block in blocks:
            if block.start <= self <= block.end:
                return True
        return False

    def is_cjk_ideograph(self, compatibility: bool = False) -> bool:
        if self.is_cjk_unified_ideograph:
            return True
        if self.is_cjk_compatibility_ideograph:
            if compatibility:
                return True
            return self in DISCRIMINATED_IDEOGRAPHS
        return False

    def ids_babelsoft(self) -> IDSInfo | None:
        ids_info_list = IDSInfo.from_dir(DATA_BABELSTONE_DIR)
        return next(filter(lambda x: x.cjk == self, ids_info_list), None)

    def radical_strokes(self) -> list[RS]:
        sources = load_Unihan_IRGSources().get(self)
        if not sources:
            return []
        values = []
        for data in sources.get("kRSUnicode", []):
            values.extend([RS.from_unihan(token) for token in data.split()])
        return values

    @staticmethod
    def to_simplified(text: str) -> str: ...

    @staticmethod
    def to_traditional(text: str) -> str: ...

    def to_equivalent(self) -> CJK | None:
        equivalents = load_EquivalentUnifiedIdeograph()
        target = equivalents.get(self)
        if target is None:
            return None
        return CJK.from_(target)

    @staticmethod
    def to_shinjitai(text: str) -> str: ...

    @staticmethod
    def to_kyujitai(text: str) -> str: ...

    @staticmethod
    def to_xinzixing(text: str) -> str: ...

    @staticmethod
    def to_jiuzixing(text: str) -> str: ...


def find_ideographs_by_radical_stroke(radical: int, stroke: int) -> list[CJK]: ...


def get_source_references(zi: CJK, *, submitter: Submitter) -> list[SrcRef]: ...
