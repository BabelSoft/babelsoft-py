"""
Egyptian Hieroglyphs data - Python implementation of c/Scripts/Hieroglyphs.cpp
"""

from __future__ import annotations

from src.utils_.loader import ScriptsLoader

EGYPTIAN_FIRST = 0x13000
EGYPTIAN_LAST = 0x1342F
EGYPTIAN_EXT_A_FIRST = 0x13460
EGYPTIAN_EXT_A_LAST = 0x1346F


class Hieroglyphs:
    """Egyptian hieroglyph character data and lookups."""

    @staticmethod
    def is_egyptian_hieroglyph(ch: int) -> bool:
        return ((EGYPTIAN_FIRST <= ch <= EGYPTIAN_LAST) or
                (EGYPTIAN_EXT_A_FIRST <= ch <= EGYPTIAN_EXT_A_LAST))

    @staticmethod
    def get_description(ch: int) -> str:
        if not Hieroglyphs.is_egyptian_hieroglyph(ch):
            return ""
        return ScriptsLoader.load_hieroglyph_descriptions().get(ch, "")
