"""Core Unicode classes: CodePoint and Block."""

from __future__ import annotations

import re
from dataclasses import dataclass


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
    def from_(cls, value: int | str | CodePoint | None = None) -> CodePoint | None:
        if not value:
            return None
        if isinstance(value, int):  # catches CodePoint and CJK subclasses too
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
