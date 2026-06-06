"""Tests for src/unicode/ package."""

import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent
sys.path.append(str(LIB_DIR))

from src.unicode import (  # noqa: E402
    BidiClass,
    Block,
    CodePoint,
    DecompositionType,
    GeneralCategory,
    Unicode,
)


class TestCodePoint:
    def test_from_int(self):
        assert CodePoint(0x41) == 0x41

    def test_from_str(self):
        assert CodePoint("U+0041") == 0x41
        assert CodePoint("0041") == 0x41
        assert CodePoint("0x41") == 0x41

    def test_from_char(self):
        assert CodePoint("A") == 0x41

    def test_repr(self):
        assert repr(CodePoint(0x41)) == "0x0041"

    def test_to_unicode(self):
        assert CodePoint(0x41).to_unicode() == "U+0041"

    def test_invalid(self):
        with pytest.raises(ValueError):
            CodePoint("not a cp")

    def test_from_none(self):
        assert CodePoint.from_(None) is None

    def test_out_of_range(self):
        with pytest.raises(ValueError):
            CodePoint(0x110000)


class TestBlock:
    def test_construction(self):
        b = Block(CodePoint(0x4E00), CodePoint(0x9FFF), "CJK Unified Ideographs")
        assert b.start == 0x4E00
        assert b.end == 0x9FFF

    def test_repr(self):
        assert "Basic Latin" in repr(Block(CodePoint(0), CodePoint(0x7F), "Basic Latin"))


class TestSurrogates:
    def test_is_surrogate(self):
        assert Unicode.is_surrogate(0xD800)
        assert Unicode.is_surrogate(0xDFFF)
        assert not Unicode.is_surrogate(0x41)

    def test_is_high(self):
        assert Unicode.is_high_surrogate(0xD800)
        assert not Unicode.is_high_surrogate(0xDC00)

    def test_is_low(self):
        assert Unicode.is_low_surrogate(0xDC00)
        assert not Unicode.is_low_surrogate(0xD800)

    def test_char_length(self):
        assert Unicode.char_length(0x41) == 1
        assert Unicode.char_length(0x10000) == 2

    def test_is_bmp(self):
        assert Unicode.is_bmp(0x41)
        assert not Unicode.is_bmp(0x10000)

    def test_plane(self):
        assert Unicode.plane(0x41) == 0
        assert Unicode.plane(0x10000) == 1


class TestGeneralCategory:
    def test_lu(self):
        assert Unicode.get_general_category(0x41) == GeneralCategory.Lu

    def test_ll(self):
        assert Unicode.get_general_category(0x61) == GeneralCategory.Ll

    def test_lo(self):
        assert Unicode.get_general_category(0x4E00) == GeneralCategory.Lo

    def test_nd(self):
        assert Unicode.get_general_category(0x30) == GeneralCategory.Nd

    def test_zs(self):
        assert Unicode.get_general_category(0x20) == GeneralCategory.Zs

    def test_cc(self):
        assert Unicode.get_general_category(0x00) == GeneralCategory.Cc

    def test_cn(self):
        assert Unicode.get_general_category(0x378) == GeneralCategory.Cn

    def test_cs(self):
        assert Unicode.get_general_category(0xD800) == GeneralCategory.Cs


class TestScript:
    def test_latin(self):
        assert Unicode.get_script(0x41) == "Latin"

    def test_han(self):
        assert Unicode.get_script(0x4E00) == "Han"

    def test_hiragana(self):
        assert Unicode.get_script(0x3042) == "Hiragana"

    def test_common(self):
        assert Unicode.get_script(0x20) == "Common"


class TestCCC:
    def test_nonspacing(self):
        assert Unicode.get_canonical_combining_class(0x300) == 230

    def test_none(self):
        assert Unicode.get_canonical_combining_class(0x41) == 0


class TestBidiClass:
    def test_ltr(self):
        assert Unicode.get_bidi_class(0x41) == BidiClass.L

    def test_rtl(self):
        assert Unicode.get_bidi_class(0x5D0) == BidiClass.R


class TestCaseMapping:
    def test_lower(self):
        assert Unicode.get_simple_lowercase(0x41) == 0x61

    def test_upper(self):
        assert Unicode.get_simple_uppercase(0x61) == 0x41

    def test_title(self):
        assert Unicode.get_simple_titlecase(0x61) == 0x41

    def test_no_lower(self):
        assert Unicode.get_simple_lowercase(0x4E00) == 0x4E00

    def test_roundtrip(self):
        assert Unicode.get_simple_lowercase(Unicode.get_simple_uppercase(0x61)) == 0x61


class TestDecomposition:
    def test_none(self):
        assert Unicode.get_decomposition_type(0x41) == DecompositionType.None_

    def test_canon(self):
        assert Unicode.get_decomposition_type(0xC0) == DecompositionType.Canon

    def test_mapping(self):
        assert Unicode.get_decomposition_mapping(0xC0) == 0x41


class TestNormalization:
    def test_nfc(self):
        assert Unicode.get_nfc("A\u0300") == "\u00c0"

    def test_nfc_no_change(self):
        assert Unicode.get_nfc("ABC") == "ABC"

    def test_nfd(self):
        assert Unicode.get_nfd("\u00c0") == "A\u0300"

    def test_nfkd(self):
        assert Unicode.get_nfkd("\ufb01") == "fi"

    def test_nfkc(self):
        assert Unicode.get_nfkc("\ufb01") == "fi"


class TestNumeric:
    def test_decimal(self):
        assert Unicode.get_numeric_value(0x30) == "0"
        assert Unicode.get_numeric_type(0x30) == "Decimal"
        assert Unicode.is_decimal_digit(0x30)

    def test_non(self):
        assert Unicode.get_numeric_value(0x41) == ""


class TestBidiMirrored:
    def test_paren(self):
        assert Unicode.get_bidi_mirrored(0x28)
        assert Unicode.get_bidi_mirroring_glyph(0x28) == 0x29


class TestCharacterName:
    def test_name(self):
        assert Unicode.get_character_name(0x41) == "LATIN CAPITAL LETTER A"

    def test_unknown(self):
        assert Unicode.get_character_name(0x378) == ""


class TestBlockLookup:
    def test_basic_latin(self):
        assert Unicode.get_block_name(0x41) == "Basic Latin"

    def test_cjk(self):
        assert "CJK" in Unicode.get_block_name(0x4E00)

    def test_range(self):
        s, e = Unicode.get_block_range(0x41)
        assert s == 0
        assert e == 0x7F


class TestConstants:
    def test_max(self):
        assert Unicode.MAX_32 == 0x10FFFF

    def test_hangul(self):
        assert Unicode.HANGUL_FIRST == 0xAC00
        assert Unicode.HANGUL_LAST == 0xD7A3
