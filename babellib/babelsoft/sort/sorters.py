"""
Sort module — Unicode string sorting (ported from c/Sort/)

Provides sorters: Unicode codepoint, hexadecimal, length-based,
numeric, glyph-based, custom, and UCA.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum

from babelsoft.unicode.uca import SortOptions


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

    def sort_key(self, text: str) -> tuple | bytes:
        """Return a sortable key for the string (a tuple or an opaque byte key)."""
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
        from babelsoft.unicode.uca import collation_compare

        return collation_compare(a, b, self._sort_options)

    def sort_key(self, text: str) -> bytes:
        from babelsoft.unicode.uca import collation_sort_key

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


# ═══════════════════════════════════════════════════════════════════════
#  Static CompareStrings helpers (mirroring C++ signatures)
# ═══════════════════════════════════════════════════════════════════════


class CompareStrings:
    """Static comparison helpers corresponding to C++ SorterXxx::CompareStrings.

    Each static method compares two strings with specific sort options,
    returning -1, 0, or 1.
    """

    @staticmethod
    def unicode(a: str, b: str, config: SortConfig | None = None) -> int:
        """Compare strings by Unicode codepoint values."""
        return SorterUnicode(config).compare(a, b)

    @staticmethod
    def hexadecimal(a: str, b: str, config: SortConfig | None = None) -> int:
        """Compare strings as hexadecimal values."""
        return SorterHexadecimal(config).compare(a, b)

    @staticmethod
    def length(a: str, b: str, config: SortConfig | None = None) -> int:
        """Compare strings by length."""
        return SorterLength(config).compare(a, b)

    @staticmethod
    def numeric(a: str, b: str, config: SortConfig | None = None) -> int:
        """Compare strings with natural numeric ordering."""
        return SorterNumeric(config).compare(a, b)

    @staticmethod
    def glyphs(a: str, b: str, order: list[str] | None = None, config: SortConfig | None = None) -> int:
        """Compare strings using glyph order."""
        return SorterGlyphs(order, config).compare(a, b)

    @staticmethod
    def custom(a: str, b: str, custom_order: str = "", config: SortConfig | None = None) -> int:
        """Compare strings using custom character order."""
        return SorterCustom(custom_order, config).compare(a, b)

    @staticmethod
    def uca(a: str, b: str, sort_options: SortOptions | None = None, config: SortConfig | None = None) -> int:
        """Compare strings using UCA collation."""
        return SorterUCA(sort_options, config).compare(a, b)

    @staticmethod
    def windows(a: str, b: str, locale_name: str = "", config: SortConfig | None = None) -> int:
        """Compare strings using locale-aware collation."""
        return SorterWindows(locale_name, config).compare(a, b)


# ═══════════════════════════════════════════════════════════════════════
#  Enhanced Sorter base with subrange and equal-range iteration
# ═══════════════════════════════════════════════════════════════════════


class SorterWithRange(Sorter):
    """Extended sorter supporting subrange sort and equal-range iteration.

    Mirrors the C++ Sorter::Sort(int firstLine, int lastLine)
    and Sorter::GetNextEqualRange APIs.
    """

    def sort_range(self, items: list[str], first: int = 0, last: int = -1) -> list[str]:
        """Sort a subrange of items. Items outside [first, last] are unchanged.

        Equivalent to C++ Sorter::Sort(int nFirstLine, int nLastLine).
        """
        if last < 0:
            last = len(items) - 1
        if first >= len(items) or last < first:
            return items

        import functools

        subset = items[first : last + 1]
        sorted_subset = sorted(
            subset,
            key=functools.cmp_to_key(self.compare),
            reverse=(self._config.direction == SortDirection.DESCENDING),
        )
        result = items[:first] + sorted_subset + items[last + 1 :]
        return result

    def get_next_equal_range(self, items: list[str], start: int) -> tuple[int, int] | None:
        """Find the next range of equal items starting from start.

        Equivalent to C++ Sorter::GetNextEqualRange(int& nFirstEqualLine, int& nLastEqualLine).
        Returns (first_equal, last_equal) or None if at end.
        """
        if start >= len(items):
            return None

        first = start
        last = start
        while last + 1 < len(items) and self.compare(items[last], items[last + 1]) == 0:
            last += 1
        return (first, last)


# ═══════════════════════════════════════════════════════════════════════
#  Sorter factory
# ═══════════════════════════════════════════════════════════════════════


def create_sorter(sort_type: str, **kwargs) -> Sorter:
    """Create a sorter instance by type name.

    Args:
        sort_type: One of 'unicode', 'hexadecimal', 'length',
                   'numeric', 'glyphs', 'custom', 'uca', 'windows'.
        **kwargs: Passed to the sorter constructor.

    Returns:
        A Sorter instance.
    """
    sorters: dict[str, type[Sorter]] = {
        "unicode": SorterUnicode,
        "hexadecimal": SorterHexadecimal,
        "length": SorterLength,
        "numeric": SorterNumeric,
        "glyphs": SorterGlyphs,
        "custom": SorterCustom,
        "uca": SorterUCA,
        "windows": SorterWindows,
    }
    cls = sorters.get(sort_type)
    if cls is None:
        raise ValueError(f"Unknown sort type: {sort_type}. Available: {list(sorters.keys())}")
    return cls(**kwargs)
