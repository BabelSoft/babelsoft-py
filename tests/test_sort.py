"""Tests for src/sort/ package — all sorter implementations."""

import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent
sys.path.append(str(LIB_DIR))

from src.sort import (  # noqa: E402
    SortConfig,
    SortDirection,
    SorterCustom,
    SorterGlyphs,
    SorterHexadecimal,
    SorterLength,
    SorterNumeric,
    SorterUCA,
    SorterUnicode,
    SorterWindows,
)

# ═════════════════════  SorterUnicode  ═════════════════════


class TestSorterUnicode:
    def test_equal(self):
        s = SorterUnicode()
        assert s.compare("a", "a") == 0

    def test_less(self):
        s = SorterUnicode()
        assert s.compare("a", "b") < 0

    def test_greater(self):
        s = SorterUnicode()
        assert s.compare("b", "a") > 0

    def test_sort(self):
        s = SorterUnicode()
        assert s.sort(["c", "a", "b"]) == ["a", "b", "c"]

    def test_sort_descending(self):
        cfg = SortConfig(direction=SortDirection.DESCENDING)
        s = SorterUnicode(cfg)
        assert s.sort(["c", "a", "b"]) == ["c", "b", "a"]

    def test_length_difference(self):
        s = SorterUnicode()
        assert s.compare("ab", "abc") < 0
        assert s.compare("abc", "ab") > 0


# ═════════════════════  SorterHexadecimal  ═════════════════════


class TestSorterHexadecimal:
    def test_equal(self):
        s = SorterHexadecimal()
        assert s.compare("A", "A") == 0

    def test_less(self):
        s = SorterHexadecimal()
        assert s.compare("A", "FF") < 0

    def test_sort(self):
        s = SorterHexadecimal()
        # int("A",16)=10, int("10",16)=16, int("FF",16)=255
        assert s.sort(["FF", "A", "10"]) == ["A", "10", "FF"]

    def test_invalid_fallback(self):
        s = SorterHexadecimal()
        # Both "XYZ" and "!!!" are invalid hex and parse to 0
        assert s.compare("XYZ", "!!!") == 0


# ═════════════════════  SorterLength  ═════════════════════


class TestSorterLength:
    def test_sort_by_length(self):
        s = SorterLength()
        assert s.sort(["aaa", "a", "aa"]) == ["a", "aa", "aaa"]

    def test_same_length_fallback(self):
        s = SorterLength()
        assert s.sort(["bb", "aa"]) == ["aa", "bb"]


# ═════════════════════  SorterNumeric  ═════════════════════


class TestSorterNumeric:
    def test_natural_sort(self):
        s = SorterNumeric()
        assert s.sort(["item10", "item2", "item1"]) == ["item1", "item2", "item10"]

    def test_pure_numbers(self):
        s = SorterNumeric()
        assert s.sort(["100", "20", "3"]) == ["3", "20", "100"]

    def test_mixed(self):
        s = SorterNumeric()
        assert s.sort(["v1.10", "v1.2", "v1.1"]) == ["v1.1", "v1.2", "v1.10"]


# ═════════════════════  SorterGlyphs  ═════════════════════


class TestSorterGlyphs:
    def test_with_order(self):
        s = SorterGlyphs(["c", "a", "b"])
        assert s.sort(["a", "b", "c"]) == ["c", "a", "b"]

    def test_unknown_at_end(self):
        s = SorterGlyphs(["x"])
        assert s.sort(["y", "x", "z"]) == ["x", "y", "z"]


# ═════════════════════  SorterCustom  ═════════════════════


class TestSorterCustom:
    def test_custom_order(self):
        s = SorterCustom("cba")
        assert s.sort(["a", "b", "c"]) == ["c", "b", "a"]

    def test_unknown_after_known(self):
        s = SorterCustom("AB")
        assert s.sort(["C", "A", "B"]) == ["A", "B", "C"]

    def test_set_order(self):
        s = SorterCustom()
        s.set_custom_order("zyx")
        assert s.sort(["x", "y", "z"]) == ["z", "y", "x"]


# ═════════════════════  SorterUCA  ═════════════════════


class TestSorterUCA:
    def test_basic_compare(self):
        s = SorterUCA()
        assert s.compare("a", "b") < 0
        assert s.compare("b", "a") > 0
        assert s.compare("a", "a") == 0

    def test_sort(self):
        s = SorterUCA()
        result = s.sort(["c", "a", "b"])
        assert result == ["a", "b", "c"]

    def test_sort_key(self):
        s = SorterUCA()
        key = s.sort_key("a")
        assert isinstance(key, bytes)
        assert len(key) > 0


# ═════════════════════  SorterWindows  ═════════════════════


class TestSorterWindows:
    def test_fallback_compare(self):
        s = SorterWindows()
        result = s.compare("a", "b")
        assert result < 0

    def test_sort_fallback(self):
        s = SorterWindows()
        assert s.sort(["c", "a", "b"]) == ["a", "b", "c"]
