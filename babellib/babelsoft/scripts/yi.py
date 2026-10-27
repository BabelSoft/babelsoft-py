"""Yi radical/stroke lookups — Python implementation of c/Languages/LanguageYi.cpp
radical tables.

Each Yi syllable maps to a radical number (1-26) and a residual stroke count.
The radical glyphs live in the Yi Radicals block (U+A490..U+A4C6); a radical
*number* maps to a specific glyph.  The data is hand-maintained in BabelMap's
C++ (not in the UCD) and was extracted to data/scripts/yi_radicals.tsv.
"""

from __future__ import annotations

import functools

from babelsoft.utils_.loader import ScriptsLoader

RADICAL_FIRST = 0xA490
RADICAL_LAST = 0xA4C6

# The Yi radical number → glyph codepoint map (index 0 unused).
# Matches the C++ YiRadicals[] array.
_YI_RADICAL_GLYPHS: tuple[int, ...] = (
    0x0000,
    0xA490,
    0xA491,
    0xA493,
    0xA494,
    0xA495,
    0xA496,
    0xA497,
    0xA499,
    0xA49A,
    0xA49C,
    0xA49F,
    0xA4A1,
    0xA4A4,
    0xA4A7,
    0xA4A8,
    0xA4A9,
    0xA4AA,
    0xA4AC,
    0xA4B0,
    0xA4B3,
    0xA4B8,
    0xA4BC,
    0xA4BE,
    0xA4C0,
    0xA4C4,
    0xA4C6,
)


class YiRadical:
    """Yi radical/stroke data lookups."""

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _data() -> dict[int, list[tuple[int, int]]]:
        return ScriptsLoader.load_yi_radicals()

    @staticmethod
    def get_radical_stroke(cp: int) -> list[tuple[int, int]]:
        """Return all (radical_number, stroke_count) pairs for a Yi syllable."""
        return YiRadical._data().get(cp, [])

    @staticmethod
    def syllables() -> dict[int, list[tuple[int, int]]]:
        """The whole syllable → [(radical_number, stroke_count)] table (read-only)."""
        return YiRadical._data()

    @staticmethod
    def radical_number_for_glyph(cp: int) -> int | None:
        """Return the radical number for a Yi radical glyph codepoint, or None."""
        if not (RADICAL_FIRST <= cp <= RADICAL_LAST):
            return None
        for n, glyph in enumerate(_YI_RADICAL_GLYPHS):
            if glyph == cp:
                return n
        return None

    @staticmethod
    def get_radical_codepoint(number: int) -> int:
        """Return the radical glyph codepoint for a radical number (1-26)."""
        if 1 <= number < len(_YI_RADICAL_GLYPHS):
            return _YI_RADICAL_GLYPHS[number]
        return 0
