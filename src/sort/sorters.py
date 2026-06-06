"""
Sort module — Unicode string sorting (ported from c/Sort/)

Provides sorters: Unicode codepoint, hexadecimal, length-based,
numeric, glyph-based, custom, and UCA.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum

from src.unicode.uca import SortOptions


class SortDirection(IntEnum):
    ASCENDING = 0
    DESCENDING = 1


@dataclass
class SortConfig:
    direction: SortDirection = SortDirection.ASCENDING
    case_sensitive: bool = True
    ignore_diacritics: bool = False
    ignore_width: bool = False


# ═══════════════════════════════════════════════════════════════════════
#  Sorter base class
# ═══════════════════════════════════════════════════════════════════════


class Sorter(ABC):
    """Abstract base for all sorters."""

    def __init__(self, config: SortConfig | None = None) -> None:
        self._config = config or SortConfig()

    @abstractmethod
    def compare(self, a: str, b: str) -> int:
        """Compare two strings. Returns <0, 0, or >0."""
        ...

    def sort(self, items: list[str]) -> list[str]:
        """Sort a list of strings."""
        import functools

        return sorted(
            items, key=functools.cmp_to_key(self.compare), reverse=(self._config.direction == SortDirection.DESCENDING)
        )

    def sort_key(self, text: str) -> tuple:
        """Return a sortable key for the string."""
        return (text,)


# ═══════════════════════════════════════════════════════════════════════
#  Unicode codepoint sorter
# ═══════════════════════════════════════════════════════════════════════


class SorterUnicode(Sorter):
    """Sort by Unicode codepoint values."""

    def compare(self, a: str, b: str) -> int:
        ca = [ord(c) for c in a]
        cb = [ord(c) for c in b]
        for x, y in zip(ca, cb):
            if x < y:
                return -1
            if x > y:
                return 1
        if len(ca) < len(cb):
            return -1
        if len(ca) > len(cb):
            return 1
        return 0


# ═══════════════════════════════════════════════════════════════════════
#  Hexadecimal sorter
# ═══════════════════════════════════════════════════════════════════════


class SorterHexadecimal(Sorter):
    """Sort by hexadecimal codepoint value (interpreted as hex string)."""

    def compare(self, a: str, b: str) -> int:
        try:
            va = int(a, 16)
        except ValueError:
            va = 0
        try:
            vb = int(b, 16)
        except ValueError:
            vb = 0
        if va < vb:
            return -1
        if va > vb:
            return 1
        return 0


# ═══════════════════════════════════════════════════════════════════════
#  Length sorter
# ═══════════════════════════════════════════════════════════════════════


class SorterLength(Sorter):
    """Sort by string length (codepoint count)."""

    def compare(self, a: str, b: str) -> int:
        la = len(a)
        lb = len(b)
        if la < lb:
            return -1
        if la > lb:
            return 1
        # Fall back to codepoint order
        return SorterUnicode().compare(a, b)


# ═══════════════════════════════════════════════════════════════════════
#  Numeric sorter
# ═══════════════════════════════════════════════════════════════════════


class SorterNumeric(Sorter):
    """Natural numeric sort."""

    @staticmethod
    def _split(text: str) -> list:
        """Split text into numeric and non-numeric parts."""
        import re

        parts = re.split(r"(\d+)", text)
        result = []
        for p in parts:
            if p.isdigit():
                result.append(int(p))
            else:
                result.append(p)
        return result

    def compare(self, a: str, b: str) -> int:
        pa = self._split(a)
        pb = self._split(b)
        for x, y in zip(pa, pb):
            tx, ty = type(x), type(y)
            if tx is int and ty is int:
                if x < y:
                    return -1
                if x > y:
                    return 1
            elif tx is int:
                return -1
            elif ty is int:
                return 1
            else:
                if x < y:
                    return -1
                if x > y:
                    return 1
        if len(pa) < len(pb):
            return -1
        if len(pa) > len(pb):
            return 1
        return 0


# ═══════════════════════════════════════════════════════════════════════
#  Glyph sorter
# ═══════════════════════════════════════════════════════════════════════


class SorterGlyphs(Sorter):
    """Sort using a user-defined glyph order list."""

    def __init__(self, glyph_order: list[str] | None = None, config: SortConfig | None = None) -> None:
        super().__init__(config)
        self._order: dict[str, int] = {}
        if glyph_order:
            for i, g in enumerate(glyph_order):
                self._order[g] = i

    def set_glyph_order(self, glyphs: list[str]) -> None:
        self._order = {g: i for i, g in enumerate(glyphs)}

    def compare(self, a: str, b: str) -> int:
        idx_a = self._order.get(a, len(self._order))
        idx_b = self._order.get(b, len(self._order))
        if idx_a < idx_b:
            return -1
        if idx_a > idx_b:
            return 1
        return 0


# ═══════════════════════════════════════════════════════════════════════
#  Custom sorter
# ═══════════════════════════════════════════════════════════════════════


class SorterCustom(Sorter):
    """Sort using custom comparison rules."""

    def __init__(self, custom_order: str | None = None, config: SortConfig | None = None) -> None:
        super().__init__(config)
        self._custom_order = custom_order or ""
        self._build_map()

    def _build_map(self) -> None:
        self._order_map: dict[str, int] = {}
        for i, ch in enumerate(self._custom_order):
            self._order_map[ch] = i

    def set_custom_order(self, order: str) -> None:
        self._custom_order = order
        self._build_map()

    def compare(self, a: str, b: str) -> int:
        for ca, cb in zip(a, b):
            oa = self._order_map.get(ca, 0x110000)
            ob = self._order_map.get(cb, 0x110000)
            if oa < ob:
                return -1
            if oa > ob:
                return 1
        if len(a) < len(b):
            return -1
        if len(a) > len(b):
            return 1
        return 0


# ═══════════════════════════════════════════════════════════════════════
#  UCA sorter
# ═══════════════════════════════════════════════════════════════════════


class SorterUCA(Sorter):
    """Sort using the Unicode Collation Algorithm."""

    def __init__(self, sort_options: SortOptions | None = None, config: SortConfig | None = None) -> None:
        super().__init__(config)
        self._sort_options = sort_options or SortOptions()

    def compare(self, a: str, b: str) -> int:
        from src.unicode.uca import collation_compare

        return collation_compare(a, b, self._sort_options)

    def sort_key(self, text: str) -> bytes:
        from src.unicode.uca import collation_sort_key

        return collation_sort_key(text, self._sort_options)


# ═══════════════════════════════════════════════════════════════════════
#  Windows sorter (fallback)
# ═══════════════════════════════════════════════════════════════════════


class SorterWindows(Sorter):
    """Sort using locale-aware comparison (Python locale module)."""

    def __init__(self, locale_name: str = "", config: SortConfig | None = None) -> None:
        super().__init__(config)
        self._locale_name = locale_name

    def compare(self, a: str, b: str) -> int:
        import locale

        try:
            old = locale.getlocale(locale.LC_COLLATE)
            if self._locale_name:
                locale.setlocale(locale.LC_COLLATE, self._locale_name)
            result = locale.strcoll(a, b)
            locale.setlocale(locale.LC_COLLATE, old)
            return result
        except locale.Error:
            # Fall back to codepoint compare
            return SorterUnicode().compare(a, b)
