"""Tests for src/unicode/ package."""

import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent
sys.path.append(str(LIB_DIR))

from babelsoft.unicode import (  # noqa: E402
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

    def test_full_canonical(self):
        # Á = A + combining acute: "0041 0301" (À = A + grave: "0041 0300")
        assert Unicode.get_decomposition(0xC1) == "0041 0301"
        assert Unicode.get_decomposition(0xC0) == "0041 0300"

    def test_full_compat(self):
        # ① (circled one) = <circled> 0031
        assert Unicode.get_decomposition(0x2460).endswith("0031")

    def test_full_none(self):
        assert Unicode.get_decomposition(0x41) == ""


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


# ═════════════════════  UCA  ═════════════════════


class TestUCA:
    """Tests for UCA (Unicode Collation Algorithm)."""

    def test_compare_less(self):
        from babelsoft.unicode.uca import collation_compare

        assert collation_compare("a", "b") < 0

    def test_compare_greater(self):
        from babelsoft.unicode.uca import collation_compare

        assert collation_compare("b", "a") > 0

    def test_compare_equal(self):
        from babelsoft.unicode.uca import collation_compare

        assert collation_compare("a", "a") == 0

    def test_get_sort_key(self):
        from babelsoft.unicode.uca import UCA

        uca = UCA()
        uca.set_string("a")
        key = uca.get_sort_key()
        assert key.startswith("[")
        assert key.endswith("]")

    def test_get_sort_key_bytes(self):
        from babelsoft.unicode.uca import UCA

        uca = UCA()
        uca.set_string("a")
        key = uca.get_sort_key_bytes()
        assert isinstance(key, bytes)
        assert len(key) > 0

    def test_compare_method(self):
        from babelsoft.unicode.uca import UCA

        u1 = UCA()
        u2 = UCA()
        u1.set_string("a")
        u2.set_string("b")
        assert u1.compare(u2) < 0
        assert u2.compare(u1) > 0

    def test_compare_equal_method(self):
        from babelsoft.unicode.uca import UCA

        u1 = UCA()
        u2 = UCA()
        u1.set_string("a")
        u2.set_string("a")
        assert u1.compare(u2) == 0

    def test_sort_options_default(self):
        from babelsoft.unicode.uca import SortOptions, SortType, Locale

        so = SortOptions()
        assert so.sort_type == SortType.UCA
        assert so.locale == Locale.NEUTRAL

    def test_empty_string(self):
        from babelsoft.unicode.uca import collation_compare

        assert collation_compare("", "") == 0
        assert collation_compare("", "a") < 0
        assert collation_compare("a", "") > 0

    def test_constants(self):
        from babelsoft.unicode.uca import COLLATE_EQUAL, COLLATE_GREATER_THAN, COLLATE_LESS_THAN

        assert COLLATE_LESS_THAN < 0
        assert COLLATE_EQUAL == 0
        assert COLLATE_GREATER_THAN > 0


# ═════════════════════  New Unicode methods  ═════════════════════


class TestNewUnicodeMethods:
    """Tests for newly added Unicode core methods (P0)."""

    # ── plane ──

    def test_get_plane_name(self):
        name = Unicode.get_plane_name(0, True)
        assert "BMP" in name

    def test_get_plane_start(self):
        assert Unicode.get_plane_start(0) == 0x0000
        assert Unicode.get_plane_start(1) == 0x10000

    def test_is_plane_reserved(self):
        assert Unicode.is_plane_reserved(4) is True
        assert Unicode.is_plane_reserved(0) is False

    def test_is_valid_code_point(self):
        assert Unicode.is_valid_code_point(0x10FFFF) is True
        assert Unicode.is_valid_code_point(0x110000) is False
        assert Unicode.is_valid_code_point(0xD800) is False

    # ── block ──

    def test_get_block_start(self):
        assert Unicode.get_block_start("Basic Latin") == 0x0000

    def test_get_block_start_invalid(self):
        assert Unicode.get_block_start("NonexistentBlock") == 0

    def test_get_block_end(self):
        assert Unicode.get_block_end("Basic Latin") == 0x007F

    # ── cjk ──

    def test_is_cjk_ideograph(self):
        assert Unicode.is_cjk_ideograph(0x4E00) is True
        assert Unicode.is_cjk_ideograph(0x0041) is False
        assert Unicode.is_cjk_ideograph(0x3400) is True  # Ext-A
        assert Unicode.is_cjk_ideograph(0x20000) is True  # Ext-B

    def test_is_tangut_ideograph(self):
        assert Unicode.is_tangut_ideograph(0x17000) is True
        assert Unicode.is_tangut_ideograph(0x41) is False

    def test_is_hiragana(self):
        assert Unicode.is_hiragana(0x3042) is True
        assert Unicode.is_hiragana(0x41) is False

    def test_is_katakana(self):
        assert Unicode.is_katakana(0x30A2) is True
        assert Unicode.is_katakana(0x41) is False

    # ── script helpers ──

    def test_is_latin_letter(self):
        assert Unicode.is_latin_letter(0x0041) is True
        assert Unicode.is_latin_letter(0x0061) is True

    def test_is_greek_letter(self):
        assert Unicode.is_greek_letter(0x0391) is True

    def test_is_cyrillic_letter(self):
        assert Unicode.is_cyrillic_letter(0x0410) is True

    # ── conversion ──

    def test_convert_to_unicode_plus(self):
        assert Unicode.convert_to_unicode_plus(0x4E00) == "U+4E00"
        assert Unicode.convert_to_unicode_plus(0x10000) == "U+10000"

    def test_convert_to_char_ref(self):
        assert Unicode.convert_to_char_ref(0x4E00) == "&#x4E00;"

    def test_convert_to_unicode_name(self):
        result = Unicode.convert_to_unicode_name(0x41)
        assert "U+0041" in result
        assert "LATIN" in result.upper()

    # ── newline ──

    def test_is_new_line(self):
        assert Unicode.is_new_line(0x000A) is True
        assert Unicode.is_new_line(0x0041) is False

    # ── iteration marks ──

    def test_iteration_mark_count(self):
        assert Unicode.get_iteration_mark_count() > 0

    def test_get_iteration_mark(self):
        cp, script = Unicode.get_iteration_mark(0)
        assert cp > 0
        assert len(script) > 0

    # ── nfc qc ──

    def test_is_nfc_qc(self):
        assert Unicode.is_nfc_qc(0x41) == "Y"  # 'A', already NFC

    def test_is_nfd_qc(self):
        assert Unicode.is_nfd_qc(0x00C0) == "N"  # À = A + grave

    # ── ccc string ──

    def test_get_ccc_as_string(self):
        assert "Not Reordered" in Unicode.get_ccc_as_string(0)

    # ── surrogates ──

    def test_unicode32_from_surrogates(self):
        cp = Unicode.get_unicode32_from_surrogates(0xD800, 0xDC00)
        assert cp == 0x10000

    def test_surrogates_from_unicode32(self):
        hi, lo = Unicode.get_surrogates_from_unicode32(0x10000)
        assert hi == 0xD800
        assert lo == 0xDC00

    # ── is_letter ──

    def test_is_letter(self):
        assert Unicode.is_letter(0x41) is True
        assert Unicode.is_letter(0x30) is False

    # ── letters_in_block ──

    def test_letters_in_block(self):
        count, first, last = Unicode.letters_in_block("Basic Latin")
        assert count > 0
        assert first > 0

    # ── Word boundary (new) ──

    def test_is_word_starter(self):
        assert Unicode.is_word_starter(0x41) is True  # 'A'
        assert Unicode.is_word_starter(0x20) is False  # space not a word character

    def test_is_word_boundary(self):
        # Between 'A' and space = word boundary (letter→non-letter)
        assert Unicode.is_word_boundary(0x41, 0x20, 0x20) is True
        # Both letters, no boundary
        assert Unicode.is_word_boundary(0x41, 0x42, 0x43) is False
        # Both non-letters, no boundary
        assert Unicode.is_word_boundary(0x20, 0x2C, 0x2E) is False

    # ── CJK static check (new) ──

    def test_is_cjk_ideograph_static(self):
        assert Unicode.is_cjk_ideograph_static(0x4E00) is True
        assert Unicode.is_cjk_ideograph_static(0x41) is False
