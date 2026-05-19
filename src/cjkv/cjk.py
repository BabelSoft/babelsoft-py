from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from ..utils_.paths import DATA_UCD_DIR
from ..utils_.txt_parser import TxtParser

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


@dataclass
class Block:
    start: int
    end: int
    name: str

    def __repr__(self) -> str:
        start_hex = hex(self.start).upper().replace("0X", "0x")
        end_hex = hex(self.end).upper().replace("0X", "0x")
        return f'Block("{self.name}", {start_hex}..{end_hex})'

    @staticmethod
    def get_blocks() -> list[Block]:
        blocks_dir = DATA_UCD_DIR / "Blocks.txt"
        blocks_lines = TxtParser.get_txt_lines(blocks_dir)
        regex = re.compile(r"([\da-fA-F]+)\.\.([\da-fA-F]+); (.+)")
        parsed = TxtParser.parse_txt_lines(blocks_lines, regex)
        return [
            Block(int(start, 16), int(end, 16), name.strip())
            for start, end, name in parsed
        ]


@dataclass
class RS:
    radical: int
    radical_variant: int
    stroke: int

    def to_unihan(self) -> str:
        variant_map = {0: "", 1: "'", 2: "''", 3: "'''"}
        variant = variant_map.get(self.radical_variant, "")
        return f"{self.radical}{variant}.{self.stroke}"

    def to_irg_radical(self) -> str:
        return f"{self.radical}.{self.radical_variant}"

    def radical_char(self) -> str: ...

    def radical_char_normalized(self) -> str: ...


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


class CJK:
    def __init__(self, item: int | str):
        if isinstance(item, int):
            self.codepoint = item
        else:
            assert len(item) == 1, "Input string must be a single character"
            self.codepoint = ord(item)

    def __repr__(self):
        return f"CJK(U+{self.codepoint:04X}, {chr(self.codepoint)})"

    def __eq__(self, other):
        if isinstance(other, CJK):
            return self.codepoint == other.codepoint
        return False

    @property
    def is_cjk_unified_ideograph(self) -> bool:
        for block in [
            blk
            for blk in Block.get_blocks()
            if "CJK" in blk.name
            and "Ideographs" in blk.name
            and "Compatibility" not in blk.name
        ]:
            if block.start <= self.codepoint <= block.end:
                return True
        return False

    @property
    def is_cjk_compatibility_ideograph(self) -> bool:
        for block in [
            block
            for block in Block.get_blocks()
            if "CJK" in block.name
            and "Ideographs" in block.name
            and "Compatibility" in block.name
        ]:
            if block.start <= self.codepoint <= block.end:
                return True
        return False

    @property
    def is_cjk_ideograph(self) -> bool:
        if self.is_cjk_unified_ideograph:
            return True
        if self.is_cjk_compatibility_ideograph:
            return self.codepoint in DISCRIMINATED_IDEOGRAPHS
        return False

    @staticmethod
    def to_simplified(text: str) -> str: ...

    @staticmethod
    def to_traditional(text: str) -> str: ...

    @staticmethod
    def to_equivalent(text: str) -> str: ...

    @staticmethod
    def to_shinjitai(text: str) -> str: ...

    @staticmethod
    def to_kyujitai(text: str) -> str: ...

    @staticmethod
    def to_xinzixing(text: str) -> str: ...

    @staticmethod
    def to_jiuzixing(text: str) -> str: ...


def get_ids(zi: CJK, level: int = 0) -> list[str]: ...


def get_radical_data(zi: CJK) -> RS: ...


def get_all_radical_strokes(zi: CJK) -> list[RS]: ...


def find_ideographs_by_radical_stroke(
    radical: int, stroke: int) -> list[CJK]: ...


def get_source_references(
    zi: CJK, *, submitter: Submitter) -> list[SrcRef]: ...
