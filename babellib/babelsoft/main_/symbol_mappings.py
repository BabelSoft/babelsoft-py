"""
SymbolMappings — Symbol font ↔ ASCII mapping (ported from c/Main/SymbolMappings.h)

Provides conversion between the Symbol font encoding (U+F020-U+F0FF PUA range
used by the classic Symbol font) and standard ASCII/Unicode characters.
"""

from __future__ import annotations

from typing import ClassVar


class SymbolMappings:
    """Symbol font encoding ↔ Unicode mapping.

    The classic Symbol font maps ASCII bytes to symbols in the PUA range
    U+F020–U+F0FF. This class provides bidirectional conversion between
    the two encodings.
    """

    SYMBOL_MAPPING_START = 0xF020
    SYMBOL_MAPPING_END = 0xF0FF
    SYMBOL_MAPPING_COUNT = 224

    # Symbol font PUA codepoint mapping table (U+F020–U+F0FF).
    # Each entry corresponds to an ASCII byte 0x20–0xFF mapped to a
    # Unicode codepoint representing the glyph actually displayed.
    _SYMBOL_FONT_MAPPING: ClassVar[list[int]] = [
        0x0020,
        0x0021,
        0x2200,
        0x0023,
        0x2203,
        0x0025,
        0x0026,
        0x220B,  # 0x20-0x27
        0x0028,
        0x0029,
        0x2217,
        0x002B,
        0x002C,
        0x2212,
        0x002E,
        0x002F,  # 0x28-0x2F
        0x0030,
        0x0031,
        0x0032,
        0x0033,
        0x0034,
        0x0035,
        0x0036,
        0x0037,  # 0x30-0x37
        0x0038,
        0x0039,
        0x003A,
        0x003B,
        0x003C,
        0x003D,
        0x003E,
        0x003F,  # 0x38-0x3F
        0x2245,
        0x0391,
        0x0392,
        0x03A7,
        0x0394,
        0x0395,
        0x03A6,
        0x0393,  # 0x40-0x47
        0x0397,
        0x0399,
        0x03D1,
        0x039A,
        0x039B,
        0x039C,
        0x039D,
        0x039F,  # 0x48-0x4F
        0x03A0,
        0x0398,
        0x03A1,
        0x03A3,
        0x03A4,
        0x03A5,
        0x03C2,
        0x03A9,  # 0x50-0x57
        0x039E,
        0x03A8,
        0x0396,
        0x005B,
        0x2234,
        0x005D,
        0x22A5,
        0x005F,  # 0x58-0x5F
        0x00AF,
        0x03B1,
        0x03B2,
        0x03C7,
        0x03B4,
        0x03B5,
        0x03C6,
        0x03B3,  # 0x60-0x67
        0x03B7,
        0x03B9,
        0x03D5,
        0x03BA,
        0x03BB,
        0x03BC,
        0x03BD,
        0x03BF,  # 0x68-0x6F
        0x03C0,
        0x03B8,
        0x03C1,
        0x03C3,
        0x03C4,
        0x03C5,
        0x03D6,
        0x03C9,  # 0x70-0x77
        0x03BE,
        0x03C8,
        0x03B6,
        0x007B,
        0x007C,
        0x007D,
        0x223C,
        0x007F,  # 0x78-0x7F
        # 0x80-0xFF: continuation
        0x00A0,
        0x00A1,
        0x00A2,
        0x00A3,
        0x2044,
        0x00A5,
        0x0192,
        0x00A7,  # 0x80-0x87
        0x00A8,
        0x00A9,
        0x2194,
        0x00AB,
        0x2190,
        0x2191,
        0x2192,
        0x2193,  # 0x88-0x8F
        0x00B0,
        0x00B1,
        0x2033,
        0x2264,
        0x00D7,
        0x221D,
        0x2202,
        0x2022,  # 0x90-0x97
        0x00F7,
        0x2260,
        0x2261,
        0x2248,
        0x2026,
        0x23D0,
        0x23AF,
        0x21B5,  # 0x98-0x9F
        0x2135,
        0x2111,
        0x211C,
        0x2118,
        0x2297,
        0x2295,
        0x2205,
        0x2229,  # 0xA0-0xA7
        0x222A,
        0x2283,
        0x2287,
        0x2284,
        0x2282,
        0x2286,
        0x2208,
        0x2209,  # 0xA8-0xAF
        0x2220,
        0x2207,
        0x00AE,
        0x00A9,
        0x2122,
        0x220F,
        0x221A,
        0x22C5,  # 0xB0-0xB7
        0x00AC,
        0x2227,
        0x2228,
        0x21D4,
        0x21D0,
        0x21D1,
        0x21D2,
        0x21D3,  # 0xB8-0xBF
        0x25C7,
        0x2329,
        0x00AE,
        0x00A9,
        0x2122,
        0x2211,
        0x239B,
        0x239C,  # 0xC0-0xC7
        0x239D,
        0x23A1,
        0x23A2,
        0x23A3,
        0x23A7,
        0x23A8,
        0x23A9,
        0x23AA,  # 0xC8-0xCF
        0x00D0,
        0x232A,
        0x222B,
        0x2320,
        0x23AE,
        0x2321,
        0x239E,
        0x239F,  # 0xD0-0xD7
        0x23A0,
        0x23A4,
        0x23A5,
        0x23A6,
        0x23AB,
        0x23AC,
        0x23AD,
        0x00DF,  # 0xD8-0xDF
        0x00E0,
        0x00E1,
        0x00E2,
        0x00E3,
        0x00E4,
        0x00E5,
        0x00E6,
        0x00E7,  # 0xE0-0xE7
        0x00E8,
        0x00E9,
        0x00EA,
        0x00EB,
        0x00EC,
        0x00ED,
        0x00EE,
        0x00EF,  # 0xE8-0xEF
        0x00F0,
        0x00F1,
        0x00F2,
        0x00F3,
        0x00F4,
        0x00F5,
        0x00F6,
        0x00F7,  # 0xF0-0xF7
        0x00F8,
        0x00F9,
        0x00FA,
        0x00FB,
        0x00FC,
        0x00FD,
        0x00FE,
        0x00FF,  # 0xF8-0xFF
    ]

    @staticmethod
    def get_symbol_mapping_for_ascii(cp: int) -> int:
        """Map an ASCII codepoint to its Symbol font PUA equivalent.

        Equivalent to C++ SymbolMappings::GetSymbolMappingForAscii.
        If cp is in range 0x20–0xFF, returns the corresponding PUA
        codepoint (U+F020 + offset). Otherwise returns cp unchanged.
        """
        if 0x20 <= cp <= 0xFF:
            return SymbolMappings.SYMBOL_MAPPING_START + (cp - 0x20)
        return cp

    @staticmethod
    def get_ascii_mapping_for_symbol(cp: int) -> int:
        """Map a Symbol font PUA codepoint back to its ASCII byte value.

        Equivalent to C++ SymbolMappings::GetAsciiMappingForSymbol.
        If cp is in the Symbol PUA range U+F020–U+F0FF, returns the
        corresponding ASCII byte. Otherwise returns cp unchanged.
        """
        if SymbolMappings.SYMBOL_MAPPING_START <= cp <= SymbolMappings.SYMBOL_MAPPING_END:
            return 0x20 + (cp - SymbolMappings.SYMBOL_MAPPING_START)
        return cp

    @staticmethod
    def get_symbol_font_mapping(index: int) -> int:
        """Get the Unicode codepoint that a Symbol font glyph actually displays.

        Equivalent to C++ SymbolMappings::GetSymbolFontMapping.
        Index 0 corresponds to U+F020, index 223 to U+F0FF.
        Returns the actual Unicode codepoint for that glyph.
        """
        if 0 <= index < SymbolMappings.SYMBOL_MAPPING_COUNT:
            return SymbolMappings._SYMBOL_FONT_MAPPING[index]
        return 0

    @staticmethod
    def get_symbol_font_mapping_count() -> int:
        """Return the number of entries in the symbol font mapping table."""
        return SymbolMappings.SYMBOL_MAPPING_COUNT
