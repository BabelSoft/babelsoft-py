"""
Hieroglyphs — Egyptian Hieroglyph data (ported from c/Scripts/Hieroglyphs.cpp)

Provides full lookup for Gardiner catalog, function values,
transliteration sources (JSesh, UniKemet, Hieroglyphica, IFAO),
rotation/mirror flags, and alternate sequences.
"""

from __future__ import annotations

from babelsoft.utils_.loader import ScriptsLoader

EGYPTIAN_FIRST = 0x13000
EGYPTIAN_LAST = 0x1342F
EGYPTIAN_EXT_A_FIRST = 0x13460
EGYPTIAN_EXT_A_LAST = 0x143FA


class Hieroglyphs:
    """Egyptian hieroglyph character data and lookups."""

    # Shared cache for hieroglyph data (extend with TSV loader for real data)
    _data_cache: dict | None = None

    @classmethod
    def _get_data(cls) -> dict:
        """Lazily load hierarchical hieroglyph data (stub — extend with TSV loader)."""
        if cls._data_cache is None:
            cls._data_cache = {
                "catalog": {},
                "core": {},
                "function": {},
                "function_value": {},
                "unikemet": {},
                "jsesh": {},
                "hieroglyphica": {},
                "ifao": {},
                "no_mirror": set(),
                "no_rotate": set(),
                "alternate_sequence": {},
            }
        return cls._data_cache

    # ─── Identification ───────────────────────────────────────────

    @staticmethod
    def is_egyptian_hieroglyph(ch: int) -> bool:
        return (EGYPTIAN_FIRST <= ch <= EGYPTIAN_LAST) or (EGYPTIAN_EXT_A_FIRST <= ch <= EGYPTIAN_EXT_A_LAST)

    # ─── Gardiner Catalog ─────────────────────────────────────────

    @staticmethod
    def get_catalog(ch: int) -> str:
        """Get Gardiner catalog designation, e.g. 'A1'."""
        if not Hieroglyphs.is_egyptian_hieroglyph(ch):
            return ""
        data = Hieroglyphs._get_data()
        return data.get("catalog", {}).get(ch, "")

    @staticmethod
    def get_core(ch: int) -> str:
        """Get kEH_Core value (core glyph indicator)."""
        if not Hieroglyphs.is_egyptian_hieroglyph(ch):
            return ""
        data = Hieroglyphs._get_data()
        return data.get("core", {}).get(ch, "")

    # ─── Description ──────────────────────────────────────────────

    @staticmethod
    def get_description(ch: int) -> str:
        """Get kEH_Desc — English description of the hieroglyph."""
        if not Hieroglyphs.is_egyptian_hieroglyph(ch):
            return ""
        return ScriptsLoader.load_hieroglyph_descriptions().get(ch, "")

    # ─── Function ─────────────────────────────────────────────────

    @staticmethod
    def get_function(ch: int, convert_entities: bool = False) -> str:
        """Get kEH_Func — function/usage of the hieroglyph."""
        if not Hieroglyphs.is_egyptian_hieroglyph(ch):
            return ""
        data = Hieroglyphs._get_data()
        return data.get("function", {}).get(ch, "")

    @staticmethod
    def get_function_value(ch: int, convert_entities: bool = False) -> str:
        """Get kEH_FVal — function value of the hieroglyph."""
        if not Hieroglyphs.is_egyptian_hieroglyph(ch):
            return ""
        data = Hieroglyphs._get_data()
        return data.get("function_value", {}).get(ch, "")

    # ─── Transliteration sources ──────────────────────────────────

    @staticmethod
    def get_unikemet(ch: int) -> str:
        """Get kEH_UniK — UniKemet transliteration."""
        if not Hieroglyphs.is_egyptian_hieroglyph(ch):
            return ""
        data = Hieroglyphs._get_data()
        return data.get("unikemet", {}).get(ch, "")

    @staticmethod
    def get_jsesh(ch: int) -> str:
        """Get kEH_JSesh — JSesh transliteration code."""
        if not Hieroglyphs.is_egyptian_hieroglyph(ch):
            return ""
        data = Hieroglyphs._get_data()
        return data.get("jsesh", {}).get(ch, "")

    @staticmethod
    def get_hieroglyphica(ch: int) -> str:
        """Get kEH_HG — Hieroglyphica designation."""
        if not Hieroglyphs.is_egyptian_hieroglyph(ch):
            return ""
        data = Hieroglyphs._get_data()
        return data.get("hieroglyphica", {}).get(ch, "")

    @staticmethod
    def get_ifao(ch: int) -> str:
        """Get kEH_IFAO — IFAO catalog number."""
        if not Hieroglyphs.is_egyptian_hieroglyph(ch):
            return ""
        data = Hieroglyphs._get_data()
        return data.get("ifao", {}).get(ch, "")

    # ─── Flags ────────────────────────────────────────────────────

    @staticmethod
    def is_no_mirror(ch: int) -> bool:
        """Check if the hieroglyph should not be mirrored."""
        if not Hieroglyphs.is_egyptian_hieroglyph(ch):
            return False
        data = Hieroglyphs._get_data()
        return ch in data.get("no_mirror", set())

    @staticmethod
    def is_no_rotate(ch: int) -> bool:
        """Check if the hieroglyph should not be rotated."""
        if not Hieroglyphs.is_egyptian_hieroglyph(ch):
            return False
        data = Hieroglyphs._get_data()
        return ch in data.get("no_rotate", set())

    # ─── Alternate sequences ──────────────────────────────────────

    @staticmethod
    def get_alternate_sequence(ch: int) -> str:
        """Get alternate encoding sequence for the hieroglyph."""
        if not Hieroglyphs.is_egyptian_hieroglyph(ch):
            return ""
        data = Hieroglyphs._get_data()
        return data.get("alternate_sequence", {}).get(ch, "")

    # ─── XML ──────────────────────────────────────────────────────

    @staticmethod
    def get_xml_data(ch: int) -> str:
        """Get XML representation of hieroglyph data."""
        if not Hieroglyphs.is_egyptian_hieroglyph(ch):
            return ""
        parts = []
        catalog = Hieroglyphs.get_catalog(ch)
        if catalog:
            parts.append(f"<catalog>{catalog}</catalog>")
        desc = Hieroglyphs.get_description(ch)
        if desc:
            parts.append(f"<description>{desc}</description>")
        func = Hieroglyphs.get_function(ch)
        if func:
            parts.append(f"<function>{func}</function>")
        fval = Hieroglyphs.get_function_value(ch)
        if fval:
            parts.append(f"<function_value>{fval}</function_value>")
        return "\n".join(parts)
