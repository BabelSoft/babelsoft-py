"""
Nüshu script data - Python implementation of c/Scripts/Nushu.cpp

Provides lookup functions for Nüshu characters:
- Character identification
- Primary readings
- Duben reference numbers
"""

from __future__ import annotations

from babelsoft.utils_.loader import ScriptsLoader

NUSHU_FIRST = 0x1B170
NUSHU_LAST = 0x1B2FB


class Nushu:
    """Nüshu script character data and lookups."""

    @staticmethod
    def is_nushu_character(ch: int) -> bool:
        return NUSHU_FIRST <= ch <= NUSHU_LAST

    @staticmethod
    def get_primary_reading(ch: int) -> str:
        if not Nushu.is_nushu_character(ch):
            return ""
        readings, _ = ScriptsLoader.load_nushu()
        return readings.get(ch, "")

    @staticmethod
    def get_duben_reference(ch: int) -> str:
        if not Nushu.is_nushu_character(ch):
            return ""
        _, refs = ScriptsLoader.load_nushu()
        return refs.get(ch, "")
