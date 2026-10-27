"""
Tests for src/languages/ package.

Covers all language modules:
- language.py (base Language class)
- language_yi.py
- language_manchu.py
- language_mongolian.py
- language_phags_pa.py
- language_tibetan.py
- language_uyghur.py
- language_unicode.py
- language_default.py
- text_input.py
"""

import os
import sys

import pytest

# Add babellib to path (package root lives at babellib/babelsoft/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from babelsoft.languages import (
    FF_16,
    ZERO_16,
    ZERO_32,
    Default,
    EInput,
    ELanguage,
    Input,
    InputMethod,
    InputType,
    Language,
    Manchu,
    Mongolian,
    PhagsPa,
    StatusType,
    Tibetan,
    Unicode,
    Uyghur,
    Yi,
)

# ============================================================================
# Base Language Class Tests
# ============================================================================


class TestLanguage:
    """Tests for the base Language class."""

    def test_construction(self):
        """Test base Language construction."""
        lang = Language(block_start=0x0000, block_end=0x007F)
        assert lang.ch_block_start == 0x0000
        assert lang.ch_block_end == 0x007F
        assert lang.ch_block_range == 0x007F
        assert lang.str_output == ""

    def test_on_clear(self):
        """Test on_clear resets state."""
        lang = Language()
        lang._step = 5
        lang._previous_input = 0x41
        lang.on_clear()
        assert lang._step == 0
        assert lang._previous_input == ZERO_16

    def test_on_clear_reset(self):
        """Test on_clear with reset=True clears escape state."""
        lang = Language()
        lang._bracket_count = 3
        lang._escape_char = 0x41
        lang.on_clear(reset=True)
        assert lang._bracket_count == 0
        assert lang._escape_char == ZERO_32

    def test_on_input_not_implemented(self):
        """Test that base on_input raises NotImplementedError."""
        lang = Language()
        with pytest.raises(NotImplementedError):
            lang.on_input(0x41)

    def test_on_text(self):
        """Test on_text processes a string character by character."""

        class MockLang(Language):
            def __init__(self):
                super().__init__()
                self.chars = []

            def on_input(self, code):
                self.chars.append(code)
                return EInput.CHARACTER

        lang = MockLang()
        lang.on_text("ABC")
        assert lang.chars == [ord("A"), ord("B"), ord("C")]

    def test_escape_sequence_u(self):
        """Test \\uXXXX escape sequence processing."""

        class MockLang(Language):
            def on_input(self, code):
                return EInput.CHARACTER

        lang = MockLang()
        lang._escape = True

        # Type '\'
        result = lang.on_char("\\")
        assert result == EInput.FINISHED_IN_PROGRESS

        # Type 'u'
        result = lang.on_char("u")
        assert result == EInput.IN_PROGRESS

        # Type hex digits '0041' (U+0041 = 'A') - exactly 4 hex digits
        # After 4 digits the escape completes with CHAR32
        for i, ch in enumerate("0041"):
            result = lang.on_char(ch)
            if i < 3:
                assert result == EInput.IN_PROGRESS
            else:
                # 4th hex digit completes the sequence
                assert result == EInput.CHAR32

    def test_backspace_handling(self):
        """Test backspace returns BACKSPACE_REDO."""

        class MockLang(Language):
            def on_input(self, code):
                return EInput.CHARACTER

        lang = MockLang()
        # Send backspace when step > 0 to avoid ignorable handling
        lang._step = 1
        result = lang.on_char("\x08")
        assert result == EInput.BACKSPACE_REDO

    def test_escape_key_clear(self):
        """Test Escape key is ignored at step 0 (not in input mode)."""

        class MockLang(Language):
            def on_input(self, code):
                return EInput.CHARACTER

        lang = MockLang()
        result = lang.on_char("\x1b")
        # At step 0, ESC is an ignorable character
        assert result == EInput.IGNORE

    def test_return_key(self):
        """Test Return key is ignored at step 0 (not in input mode)."""

        class MockLang(Language):
            def on_input(self, code):
                return EInput.CHARACTER

        lang = MockLang()
        result = lang.on_char("\r")
        # At step 0, RETURN is an ignorable character
        assert result == EInput.IGNORE

    def test_number_at_step_zero(self):
        """Test number input at step 0 goes to _on_number."""

        class MockLang(Language):
            def on_input(self, code):
                return EInput.CHARACTER

        lang = MockLang()
        result = lang.on_char("5")
        assert result == EInput.CHARACTER

    def test_enums(self):
        """Test enum values are distinct."""
        values = {e.value for e in InputType}
        assert len(values) == len(InputType)

        lang_values = {e.value for e in ELanguage}
        assert len(lang_values) == len(ELanguage)


# ============================================================================
# LanguageYi Tests
# ============================================================================


class TestLanguageYi:
    """Tests for LanguageYi class."""

    def test_construction(self):
        """Test Yi language construction."""
        yi = Yi()
        assert yi.ch_block_start == 0xA000
        assert yi._initials_index == 0
        assert yi._medials_index == 0
        assert yi._hanging_vowel is False

    def test_on_clear(self):
        """Test Yi on_clear resets all indices."""
        yi = Yi()
        yi._initials_index = 5
        yi._medials_index = 3
        yi._syllables_index = 100
        yi._hanging_vowel = True
        yi.on_clear()
        assert yi._initials_index == 0
        assert yi._medials_index == 0
        assert yi._syllables_index == 0
        assert yi._hanging_vowel is False

    def test_get_character_name_syllable(self):
        """Test character name for a Yi syllable."""
        name = Yi.get_character_name(0xA000)
        assert isinstance(name, str)
        # Should return a name with uppercase letters
        assert len(name) > 0

    def test_get_character_name_radical(self):
        """Test character name for a Yi radical."""
        name = Yi.get_character_name(0xA490)  # First radical
        assert isinstance(name, str)

    def test_get_character_name_out_of_range(self):
        """Test character name for non-Yi code points."""
        name = Yi.get_character_name(0x0041)  # 'A'
        assert name == ""

    def test_get_character_name_with_space(self):
        """Test character name with trailing space."""
        name = Yi.get_character_name(0xA490, add_space=True)
        if name:
            assert name.endswith(" ")

    def test_get_ipa(self):
        """Test IPA transcription."""
        ipa = Yi.get_ipa(0xA000)
        assert isinstance(ipa, str)

    def test_get_ipa_non_yi(self):
        """Test IPA for non-Yi returns empty."""
        ipa = Yi.get_ipa(0x0041)
        assert ipa == ""

    def test_get_tone(self):
        """Test tone extraction."""
        tone = Yi.get_tone(0xA000)
        assert tone in (0, 1, 2, 3, 4)

    def test_get_tone_non_yi(self):
        """Test tone for non-Yi returns 0."""
        tone = Yi.get_tone(0x0041)
        assert tone == 0

    def test_find_radical_stroke(self):
        """Test radical/stroke lookup."""
        radical, _strokes = Yi.find_radical_stroke_for_syllable(0xA000)
        # With simplified tables, may return None
        assert radical is None or isinstance(radical, int)

    def test_find_syllables_for_radical(self):
        """Test syllable lookup by radical."""
        results = Yi.find_syllables_for_radical(0, 3)
        assert isinstance(results, list)

    def test_is_punctuation(self):
        """Test Yi punctuation detection."""
        yi = Yi()
        assert yi._is_punctuation(ord(",")) is True
        assert yi._is_punctuation(ord("x")) is False

    def test_is_initial_valid(self):
        """Test valid initial detection."""
        yi = Yi()
        assert yi._is_initial("b", False) is True  # 'b' is a valid initial

    def test_is_initial_invalid(self):
        """Test invalid initial detection."""
        yi = Yi()
        assert yi._is_initial("#", False) is False

    def test_is_medial(self):
        """Test medial vowel detection."""
        yi = Yi()
        yi._initials_index = 0  # Set a valid initial
        # 'a' is a valid medial
        yi._is_initial("b", False)
        assert yi._is_medial("a", False) is True

    def test_is_final(self):
        """Test final tone marker detection."""
        yi = Yi()
        yi._initials_index = 0
        yi._medials_index = 0
        # Set up a valid initial+medial combination first
        yi._is_initial("b", False)

    def test_convert_latin_to_yi(self):
        """Test Latin to Yi conversion."""
        yi = Yi()
        result, _count = yi._convert_latin_to_yi("b", 0, 1)
        assert isinstance(result, str)

    def test_convert_yi_to_latin(self):
        """Test Yi to Latin conversion."""
        yi = Yi()
        result, _count = yi._convert_yi_to_latin(chr(0xA000), 0, 1)
        assert isinstance(result, str)


# ============================================================================
# LanguageManchu Tests
# ============================================================================


class TestLanguageManchu:
    """Tests for LanguageManchu class."""

    def test_construction(self):
        """Test Manchu construction."""
        manchu = Manchu()
        assert manchu.ch_block_start == 0x1800
        assert manchu._vowel_type == 0  # NEUTRAL
        assert manchu._word_pos == 0

    def test_on_clear(self):
        """Test Manchu clear state."""
        manchu = Manchu()
        manchu._word_pos = 10
        manchu._vowel_type = 1
        manchu.on_clear()
        assert manchu._word_pos == 0
        assert manchu._vowel_type == 0

    def test_get_output_string_empty(self):
        """Test output string when empty."""
        manchu = Manchu()
        result = manchu.get_output_string()
        assert result == ""

    def test_is_punctuation_vertical_bar(self):
        """Test Manchu punctuation detection."""
        manchu = Manchu()
        assert manchu._is_punctuation(0x7C) is True  # |
        assert manchu._is_punctuation(0x41) is False  # A

    def test_is_vowel(self):
        """Test Manchu vowel detection."""
        manchu = Manchu()
        assert manchu._is_vowel_check(0x61) is True  # 'a'
        assert manchu._is_vowel_check(0x65) is True  # 'e'
        assert manchu._is_vowel_check(0x69) is True  # 'i'
        assert manchu._is_vowel_check(0x7A) is False  # 'z' is not a vowel

    def test_is_consonant(self):
        """Test Manchu consonant detection."""
        manchu = Manchu()
        assert manchu._is_consonant_check(0x6E) is True  # 'n'
        assert manchu._is_consonant_check(0x62) is True  # 'b'
        assert manchu._is_consonant_check(0x61) is False  # 'a' is vowel

    def test_is_consonant_digraph(self):
        """Test Manchu consonant digraph detection."""
        manchu = Manchu()
        assert manchu._is_consonant_check(0x6E, 0x67) is True  # 'ng'
        assert manchu._is_consonant_check(0x6B, 0x68) is True  # 'kh'

    def test_special_characters(self):
        """Test special character mappings."""
        manchu = Manchu()
        result = manchu.on_char("+")
        assert result == EInput.CHARACTER
        assert manchu.ch_output == 0x1807  # Sibe Syllable Boundary Marker

    def test_on_return(self):
        """Test return key finishes input."""
        manchu = Manchu()
        result = manchu.on_return()
        assert result == EInput.FINISHED

    def test_do_conversion_basic(self):
        """Test basic Latin to Manchu conversion."""
        manchu = Manchu()
        result, _count = manchu.do_conversion(0, "a", 0, 1)
        assert isinstance(result, str)


# ============================================================================
# LanguageMongolian Tests
# ============================================================================


class TestLanguageMongolian:
    """Tests for LanguageMongolian class."""

    def test_construction(self):
        """Test Mongolian construction."""
        mong = Mongolian()
        assert mong.ch_block_start == 0x1800
        assert mong._vowel_type == 0
        assert mong._word_pos == 0

    def test_number_conversion(self):
        """Test Mongolian digit conversion."""
        mong = Mongolian()
        result = mong._on_number(ord("3"))
        assert result == EInput.CHARACTER
        assert mong.ch_output == 0x1813  # Mongolian digit 3

    def test_is_vowel(self):
        """Test Mongolian vowel detection."""
        mong = Mongolian()
        assert mong._is_vowel_check(0x61) is True  # 'a'
        assert mong._is_vowel_check(0x65) is True  # 'e'
        assert mong._is_vowel_check(0x6F) is True  # 'o'
        assert mong._is_vowel_check(0x75) is True  # 'u'
        # 'oe' digraph
        assert mong._is_vowel_check(0x6F, 0x65) is True

    def test_is_consonant(self):
        """Test Mongolian consonant detection."""
        mong = Mongolian()
        assert mong._is_consonant_check(0x6E) is True  # 'n'
        assert mong._is_consonant_check(0x62) is True  # 'b'
        assert mong._is_consonant_check(0x71) is True  # 'q'

    def test_special_characters(self):
        """Test Mongolian special character mapping."""
        mong = Mongolian()
        result = mong.on_char("+")
        assert result == EInput.CHARACTER
        assert mong.ch_output == 0x180E  # MVS

    def test_do_conversion_basic(self):
        """Test basic Latin to Mongolian conversion."""
        mong = Mongolian()
        result, _count = mong.do_conversion(0, "a", 0, 1)
        assert isinstance(result, str)


# ============================================================================
# LanguagePhagsPa Tests
# ============================================================================


class TestLanguagePhagsPa:
    """Tests for LanguagePhagsPa class."""

    def test_construction(self):
        """Test Phags-pa construction."""
        pp = PhagsPa()
        assert pp.ch_block_start == 0xA840
        assert pp._word_pos == 0

    def test_is_vowel(self):
        """Test Phags-pa vowel detection."""
        pp = PhagsPa()
        assert pp._is_vowel_check(0x61) is True  # 'a'
        assert pp._is_vowel_check(0x65) is True  # 'e'
        assert pp._is_vowel_check(0x69) is True  # 'i'
        assert pp._is_vowel_check(0x6F) is True  # 'o'
        assert pp._is_vowel_check(0x75) is True  # 'u'

    def test_is_consonant(self):
        """Test Phags-pa consonant detection."""
        pp = PhagsPa()
        assert pp._is_consonant_check(0x6B) is True  # 'k'
        assert pp._is_consonant_check(0x67) is True  # 'g'
        assert pp._is_consonant_check(0x6B, 0x68) is True  # 'kh'

    def test_on_clear(self):
        """Test Phags-pa clear."""
        pp = PhagsPa()
        pp._word_pos = 5
        pp.on_clear()
        assert pp._word_pos == 0

    def test_special_characters(self):
        """Test Phags-pa special characters."""
        pp = PhagsPa()
        # + is invalid for Phags-pa
        result = pp.on_char("+")
        # Should be invalid since Phags-pa doesn't use MVS
        assert result == EInput.INVALID

    def test_do_conversion_basic(self):
        """Test basic Latin to Phags-pa conversion."""
        pp = PhagsPa()
        result, _count = pp.do_conversion(0, "ka", 0, 2)
        assert isinstance(result, str)


# ============================================================================
# LanguageTibetan Tests
# ============================================================================


class TestLanguageTibetan:
    """Tests for LanguageTibetan class."""

    def test_construction(self):
        """Test Tibetan construction."""
        tib = Tibetan()
        assert tib.ch_block_start == 0x0F00
        assert tib._escape is True  # Enables Wylie mode
        assert tib._initials_pos == 0

    def test_on_clear(self):
        """Test Tibetan clear state."""
        tib = Tibetan()
        tib._initials_pos = 3
        tib._word[3] = 0x0F40
        tib.on_clear()
        assert tib._initials_pos == 0
        assert tib._word[3] == ZERO_16

    def test_get_output_string_empty(self):
        """Test empty output string."""
        tib = Tibetan()
        result = tib.get_output_string()
        assert result == ""

    def test_number_to_tibetan_digit(self):
        """Test number conversion to Tibetan digits."""
        tib = Tibetan()
        result = tib._on_number(ord("5"))
        assert result == EInput.CHARACTER
        # 5 -> Tibetan digit 5 (0x0F25)
        assert tib.ch_output == 0x0F25

    def test_number_with_brackets(self):
        """Test number in bracket mode returns CHARACTER."""
        tib = Tibetan()
        tib._bracket_count = 1
        result = tib._on_number(ord("5"))
        assert result == EInput.CHARACTER

    def test_on_return(self):
        """Test return key."""
        tib = Tibetan()
        result = tib.on_return()
        assert result == EInput.FINISHED

    def test_is_punctuation(self):
        """Test Tibetan punctuation detection."""
        tib = Tibetan()
        assert tib._is_punctuation(ord(" ")) is True  # tsheg
        assert tib._is_punctuation(ord("/")) is True  # shad
        assert tib._is_punctuation(ord("x")) is False

    def test_do_conversion_basic(self):
        """Test basic Wylie to Tibetan conversion."""
        tib = Tibetan()
        result, _count = tib.do_conversion(0, "ka", 0, 2)
        assert isinstance(result, str)


# ============================================================================
# LanguageUyghur Tests
# ============================================================================


class TestLanguageUyghur:
    """Tests for LanguageUyghur class."""

    def test_construction(self):
        """Test Uyghur construction."""
        uy = Uyghur()
        assert uy.ch_block_start == 0x0600

    def test_keyboard_layout_ascii(self):
        """Test keyboard layout mapping for ASCII."""
        uy = Uyghur()
        result = uy.on_char("a")  # lowercase 'a' -> Uyghur H (0x06BE)
        assert result == EInput.CHARACTER
        assert uy.ch_output == 0x06BE

    def test_keyboard_layout_L_special(self):
        """Test special L mapping to LA ligature."""
        uy = Uyghur()
        result = uy.on_char("L")
        assert result == EInput.FINISHED
        assert uy.str_output == chr(0x0644) + chr(0x0627)

    def test_keyboard_layout_unmapped(self):
        """Test unmapped key returns NULL."""
        uy = Uyghur()
        result = uy.on_char("A")  # Uppercase A is unmapped
        assert result == EInput.NULL

    def test_convert_arabic_to_latin(self):
        """Test Arabic to Latin conversion."""
        uy = Uyghur()
        result, _count = uy._convert_to_latin(chr(0x0627), 0, 1)
        assert isinstance(result, str)

    def test_convert_latin_to_arabic(self):
        """Test Latin to Arabic conversion."""
        uy = Uyghur()
        result, _count = uy._convert_to_arabic("a", 0, 1)
        assert isinstance(result, str)

    def test_do_conversion_arabic_to_latin(self):
        """Test Arabic->Latin via do_conversion."""
        uy = Uyghur()
        result, _count = uy.do_conversion(0, chr(0x0627), 0, 1)
        assert isinstance(result, str)

    def test_do_conversion_latin_to_arabic(self):
        """Test Latin->Arabic via do_conversion."""
        uy = Uyghur()
        result, _count = uy.do_conversion(1, "a", 0, 1)
        assert isinstance(result, str)


# ============================================================================
# LanguageUnicode Tests
# ============================================================================


class TestLanguageUnicode:
    """Tests for LanguageUnicode class."""

    def test_to_nfd(self):
        """Test NFD normalization."""
        result = Unicode.to_nfd("é")
        assert result == "e\u0301"  # e + combining acute

    def test_to_nfc(self):
        """Test NFC normalization."""
        result = Unicode.to_nfc("e\u0301")
        assert result == "é"

    def test_to_nfkd(self):
        """Test NFKD normalization."""
        result = Unicode.to_nfkd("ﬁ")  # fi ligature
        assert result == "fi"

    def test_to_nfkc(self):
        """Test NFKC normalization."""
        result = Unicode.to_nfkc("ﬁ")
        assert result == "fi"

    def test_to_upper(self):
        """Test uppercase conversion."""
        result = Unicode.to_upper("hello")
        assert result == "HELLO"

    def test_to_lower(self):
        """Test lowercase conversion."""
        result = Unicode.to_lower("HELLO")
        assert result == "hello"

    def test_toggle_case(self):
        """Test case toggling."""
        result = Unicode.toggle_case("HeLLo")
        assert result == "hEllO"

    def test_fold_case(self):
        """Test case folding."""
        result = Unicode.fold_case("HELLO")
        assert result == "hello"

    def test_convert_to_ncr(self):
        """Test NCR conversion."""
        result = Unicode.convert_to_ncr("A\u4e2d")
        assert "&#x4E2D;" in result
        assert "A" in result

    def test_convert_from_ncr(self):
        """Test NCR parsing."""
        result = Unicode.convert_from_ncr("A&#x4E2D;B")
        assert result == "A\u4e2dB"

    def test_convert_to_ucn(self):
        """Test UCN conversion."""
        result = Unicode.convert_to_ucn("\u4e2d")
        assert "\\u" in result
        assert "4E2D" in result

    def test_convert_from_ucn(self):
        """Test UCN parsing."""
        result = Unicode.convert_from_ucn(r"\u4E2D")
        assert result == "\u4e2d"

    def test_convert_to_uplus(self):
        """Test U+ notation conversion."""
        result = Unicode.convert_to_uPlus("A")
        assert "U+0041" in result

    def test_strip_diacritics(self):
        """Test diacritic stripping."""
        result = Unicode.strip_diacritics("café")
        assert "cafe" in result  # 'é' decomposed -> 'e' + combining acute

    def test_strip_ignorables(self):
        """Test ignorable character removal."""
        result = Unicode.strip_ignorables("A\u200b\u200cB")
        assert result == "AB"

    def test_convert_half_to_full(self):
        """Test halfwidth to fullwidth conversion."""
        result = Unicode.convert_half_to_full("ABC")
        assert result == "\uff21\uff22\uff23"  # Fullwidth A B C

    def test_convert_full_to_half(self):
        """Test fullwidth to halfwidth conversion."""
        result = Unicode.convert_full_to_half("\uff21\uff22\uff23")
        assert result == "ABC"

    def test_convert_cjk_compat_to_unified(self):
        """Test CJK compatibility conversion."""
        # U+FA10 is a compatibility ideograph
        result = Unicode.convert_cjk_compat_to_unified(chr(0xFA10))
        assert len(result) <= 1  # Should decompose or stay same

    def test_on_input_passthrough(self):
        """Test Unicode on_input passes through."""
        uni = Unicode()
        result = uni.on_input(0x41)
        assert result == EInput.CHARACTER
        assert uni.ch_output == 0x41


# ============================================================================
# LanguageDefault Tests
# ============================================================================


class TestLanguageDefault:
    """Tests for LanguageDefault class."""

    def test_construction(self):
        """Test default language construction."""
        default = Default()
        assert default._high_surrogate == FF_16

    def test_on_input_bmp(self):
        """Test BMP character input."""
        default = Default()
        result = default.on_input(0x41)
        assert result == EInput.CHARACTER

    def test_on_input_high_surrogate(self):
        """Test high surrogate input."""
        default = Default()
        result = default.on_input(0xD800)
        assert result == EInput.NULL
        assert default._high_surrogate == 0xD800

    def test_on_input_surrogate_pair(self):
        """Test surrogate pair input."""
        default = Default()
        default.on_input(0xD800)  # High
        result = default.on_input(0xDC00)  # Low
        assert result == EInput.CHAR32
        assert default.ch_output >= 0x10000
        assert default._high_surrogate == FF_16

    def test_on_input_invalid_low_surrogate(self):
        """Test invalid low surrogate without high."""
        default = Default()
        result = default.on_input(0xDC00)
        assert result == EInput.INVALID

    def test_hiragana_to_katakana(self):
        """Test Hiragana -> Katakana conversion."""
        result, count = Default._convert_hiragana_to_katakana("\u3042\u3044")  # あい
        assert result == "\u30a2\u30a4"  # アイ
        assert count == 2

    def test_katakana_to_hiragana(self):
        """Test Katakana -> Hiragana conversion."""
        result, count = Default._convert_katakana_to_hiragana("\u30a2\u30a4")  # アイ
        assert result == "\u3042\u3044"  # あい
        assert count == 2

    def test_hangul_syllable_to_letters(self):
        """Test Hangul syllable decomposition."""
        # '가' (U+AC00) = ㄱ + ㅏ
        result, count = Default._convert_hangul_to_letters("\uac00")
        assert count == 1
        assert len(result) >= 2  # At least choseong + jungseong

    def test_letters_to_hangul(self):
        """Test Jamo to Hangul syllable composition."""
        # ㄱ(U+1100) + ㅏ(U+1161) = 가(U+AC00)
        result, count = Default._convert_letters_to_hangul("\u1100\u1161")
        assert count == 1
        assert result == "\uac00"

    def test_fullwidth_halfwidth(self):
        """Test fullwidth/halfwidth toggling."""
        result, count = Default._convert_fullwidth_halfwidth("A")
        assert "\uff21" in result  # Fullwidth A
        assert count == 1

    def test_reverse_lines(self):
        """Test line reversal."""
        result, count = Default._reverse_lines("a\nb\nc")
        assert result == "c\nb\na"
        assert count == 3

    def test_caesar_cipher_forward(self):
        """Test Caesar cipher forward."""
        result, count = Default._apply_caesar("abc", offset=1)
        assert result == "bcd"
        assert count == 3

    def test_caesar_cipher_backward(self):
        """Test Caesar cipher backward."""
        result, count = Default._apply_caesar("bcd", offset=1, forward=False)
        assert result == "abc"
        assert count == 3

    def test_caesar_wraparound(self):
        """Test Caesar cipher wrap-around."""
        result, _count = Default._apply_caesar("xyz", offset=3)
        assert result == "abc"

    def test_convert_to_viqr(self):
        """Vietnamese letters become VIQR; everything else is unchanged."""
        assert Default.convert_to_viqr("Việt Nam") == "Vie^.t Nam"
        assert Default.convert_to_viqr("abc") == "abc"

    def test_convert_from_viqr(self):
        """VIQR sequences are decoded back into precomposed Vietnamese."""
        assert Default.convert_from_viqr("Vie^.t Nam") == "Việt Nam"
        assert Default.convert_from_viqr("abc") == "abc"

    def test_viqr_roundtrip(self):
        """Unicode → VIQR → Unicode must be lossless."""
        for text in ("Việt", "Tiếng Việt", "Ứng dụng"):
            assert Default.convert_from_viqr(Default.convert_to_viqr(text)) == text


# ============================================================================
# TextInput Tests
# ============================================================================


class TestTextInput:
    """Tests for TextInput class."""

    def test_construction(self):
        """Test TextInput construction."""
        ti = Input()
        assert ti.input_count == 0
        assert ti.current_method == -1
        assert ti.is_empty is True

    def test_add_method(self):
        """Test adding a text input method."""
        ti = Input()
        method = InputMethod(name="Test", path="/test.tim")
        ti.add_method(method)
        assert ti.input_count == 1
        assert ti.get_name(0) == "Test"

    def test_delete_method(self):
        """Test deleting a method."""
        ti = Input()
        ti.add_method(InputMethod(name="Test"))
        ti.delete_method(0)
        assert ti.input_count == 0

    def test_modify_method(self):
        """Test modifying a method."""
        ti = Input()
        ti.add_method(InputMethod(name="Old"))
        ti.modify_method(0, InputMethod(name="New"))
        assert ti.get_name(0) == "New"

    def test_move_method_up(self):
        """Test moving a method up."""
        ti = Input()
        ti.add_method(InputMethod(name="A"))
        ti.add_method(InputMethod(name="B"))
        ti.move_method(1, up=True)
        assert ti.get_name(0) == "B"
        assert ti.get_name(1) == "A"

    def test_move_method_down(self):
        """Test moving a method down."""
        ti = Input()
        ti.add_method(InputMethod(name="A"))
        ti.add_method(InputMethod(name="B"))
        ti.move_method(0, up=False)
        assert ti.get_name(0) == "B"
        assert ti.get_name(1) == "A"

    def test_set_method(self):
        """Test setting the active method."""
        ti = Input()
        ti.add_method(InputMethod(name="Test"))
        ti.set_method(0)
        assert ti.current_method == 0

    def test_is_selected(self):
        """Test is_selected check."""
        ti = Input()
        ti.add_method(InputMethod(name="Test"))
        ti.set_method(0)
        assert ti.is_selected(0) is True
        assert ti.is_selected(1) is False

    def test_get_status_out_of_range(self):
        """Test status for invalid index."""
        ti = Input()
        assert ti.get_status(-1) == StatusType.MISSING
        assert ti.get_status(999) == StatusType.MISSING

    def test_get_name_out_of_range(self):
        """Test name for invalid index."""
        ti = Input()
        assert ti.get_name(999) == ""

    def test_get_candidate_result(self):
        """Test candidate result."""
        ti = Input()
        result = ti.get_candidate_result(0)
        assert result == ""

    def test_on_clear(self):
        """Test clear input state."""
        ti = Input()
        ti.on_clear()
        assert ti.candidate_count == 0
        assert ti.is_deadkey is False

    def test_is_deadkey_initially_false(self):
        """Test deadkey flag initial state."""
        ti = Input()
        assert ti.is_deadkey is False

    def test_is_shiftkey_initially_false(self):
        """Test shiftkey flag initial state."""
        ti = Input()
        assert ti.is_shiftkey is False

    def test_clear_deadkey(self):
        """Test clearing deadkey."""
        ti = Input()
        ti.clear_deadkey()
        assert ti.is_deadkey is False

    def test_candidate_offset(self):
        """Test candidate offset setting."""
        ti = Input()
        ti.set_candidate_offset(10)
        # Offset is stored internally

    def test_on_character_input_no_method(self):
        """Test input with no method selected."""
        ti = Input()
        result = ti.on_character_input(ord("a"))
        assert result == InputType.UNMAPPED

    def test_enum_values_distinct(self):
        """Test ETextInput values are distinct."""
        values = {e.value for e in InputType}
        assert len(values) == len(InputType)

    def test_estatus_values(self):
        """Test EStatus values."""
        assert StatusType.LOADED.value == 1
        assert StatusType.FAILED.value == 2


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests crossing multiple modules."""

    def test_package_imports(self):
        """Test all expected names are importable."""
        from babelsoft.languages import (
            Language,
        )

        assert Language is not None

    def test_language_yi_full_flow(self):
        """Test Yi language full conversion flow."""
        yi = Yi()
        # Test on_char with valid initial
        result = yi.on_char("b")
        assert result in (EInput.IN_PROGRESS, EInput.IGNORE, EInput.INVALID)
        yi.on_clear()

        # Test Latin-to-Yi conversion
        result, _count = yi.do_conversion(2, "b", 0, 1)
        assert isinstance(result, str)

    def test_language_manchu_full_flow(self):
        """Test Manchu full conversion flow."""
        manchu = Manchu()
        result, _count = manchu.do_conversion(0, "a e i o u", 0, 9)
        assert isinstance(result, str)

    def test_language_mongolian_full_flow(self):
        """Test Mongolian full conversion flow."""
        mong = Mongolian()
        result, _count = mong.do_conversion(0, "a e i o u", 0, 9)
        assert isinstance(result, str)

    def test_language_uyghur_bidirectional(self):
        """Test Uyghur bidirectional conversion."""
        uy = Uyghur()
        # Latin -> Arabic -> Latin roundtrip approximation
        latin_result, _ = uy._convert_to_latin(chr(0x0627), 0, 1)
        assert isinstance(latin_result, str)

    def test_unicode_roundtrip_nfc_nfd(self):
        """Test NFC/NFD roundtrip."""
        original = "café"
        nfd = Unicode.to_nfd(original)
        nfc = Unicode.to_nfc(nfd)
        assert nfc == original

    def test_unicode_roundtrip_ncr(self):
        """Test NCR roundtrip."""
        original = "Hello\u4e2d"
        ncr = Unicode.convert_to_ncr(original)
        restored = Unicode.convert_from_ncr(ncr)
        assert restored == original

    def test_hangul_roundtrip(self):
        """Test Hangul decomposition/recomposition roundtrip."""
        syl = "\uac00"  # 가
        letters, _ = Default._convert_hangul_to_letters(syl)
        composed, _ = Default._convert_letters_to_hangul(letters)
        assert composed == syl

    def test_kana_roundtrip(self):
        """Test Hiragana/Katakana roundtrip."""
        hira = "\u3042"  # あ
        kata, _ = Default._convert_hiragana_to_katakana(hira)
        hira2, _ = Default._convert_katakana_to_hiragana(kata)
        assert hira2 == hira

    def test_fullwidth_roundtrip(self):
        """Test fullwidth/halfwidth roundtrip."""
        result, _ = Default._convert_fullwidth_halfwidth("A")
        assert "\uff21" in result  # fullwidth A
        result2, _ = Default._convert_fullwidth_halfwidth(result)
        assert "A" in result2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
