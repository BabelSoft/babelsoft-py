"""
Khitan small script data - Python implementation of c/Scripts/Khitan.cpp

Provides lookup functions for Khitan small script characters:
- Character identification
- Readings and meanings
"""

from __future__ import annotations

from babelsoft.utils_.loader import ScriptsLoader

KHITAN_SMALL_START = 0x18B00
KHITAN_SMALL_LAST = 0x18CD5
KHITAN_SMALL_BLANK = 0x18CFF


class Khitan:
    """Khitan small script character data and lookups."""

    @staticmethod
    def is_khitan_small_script(ch: int) -> bool:
        return KHITAN_SMALL_START <= ch <= KHITAN_SMALL_LAST

    @staticmethod
    def get_reading(ch: int) -> str:
        if not Khitan.is_khitan_small_script(ch):
            return ""
        readings, _ = ScriptsLoader.load_khitan()
        return readings.get(ch, "")

    @staticmethod
    def get_meaning(ch: int) -> str:
        if not Khitan.is_khitan_small_script(ch):
            return ""
        _, meanings = ScriptsLoader.load_khitan()
        return meanings.get(ch, "")

    @staticmethod
    def get_reading_and_meaning(ch: int) -> str:
        reading = Khitan.get_reading(ch)
        meaning = Khitan.get_meaning(ch)
        result = ""
        if reading:
            result += f" [{reading}]"
        if meaning:
            result += f" ({meaning})"
        return result
