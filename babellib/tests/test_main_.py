"""Tests for src/main_/ package — BabelString, SCSU, CharList, SymbolMappings, PostScriptNames."""

import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent
sys.path.append(str(LIB_DIR))

from babelsoft.main_ import BabelString, CharList, SCSU  # noqa: E402
from babelsoft.main_.symbol_mappings import SymbolMappings  # noqa: E402
from babelsoft.main_.postscript_names import PostScriptNames  # noqa: E402

# ═════════════════════  BabelString  ═════════════════════


class TestBabelString:
    # ── codepoint iteration ──

    def test_number_of_characters_ascii(self):
        assert BabelString.number_of_characters("Hello") == 5

    def test_number_of_characters_empty(self):
        assert BabelString.number_of_characters("") == 0

    def test_codepoints_ascii(self):
        assert BabelString.codepoints("AB") == [0x41, 0x42]

    def test_codepoints_supplementary(self):
        cps = BabelString.codepoints("\U00010000")
        assert len(cps) == 1
        assert cps[0] == 0x10000

    def test_from_codepoints(self):
        assert BabelString.from_codepoints([0x41, 0x42]) == "AB"

    def test_from_codepoints_supplementary(self):
        s = BabelString.from_codepoints([0x10000])
        assert s == "\U00010000"
        assert len(s) == 1  # single character, not surrogate pair

    def test_roundtrip(self):
        original = "Hello \U00010000 World"
        cps = BabelString.codepoints(original)
        restored = BabelString.from_codepoints(cps)
        assert restored == original

    # ── character access ──

    def test_get_at(self):
        assert BabelString.get_at("ABC", 0) == 0x41
        assert BabelString.get_at("ABC", 2) == 0x43

    def test_get_at_out_of_range(self):
        assert BabelString.get_at("ABC", 5) == 0

    def test_get_before(self):
        assert BabelString.get_before("ABC", 0) == 0

    def test_get_after(self):
        assert BabelString.get_after("ABC", 0) == 0x42

    # ── line navigation ──

    def test_is_line_break(self):
        assert BabelString.is_line_break(0x000A) is True
        assert BabelString.is_line_break(0x000D) is True
        assert BabelString.is_line_break(0x0041) is False

    def test_go_start_of_line(self):
        text = "hello\nworld"
        pos = BabelString.go_start_of_line(text, 7)
        assert pos == 6  # right after \n

    def test_go_end_of_line(self):
        text = "hello\nworld"
        pos = BabelString.go_end_of_line(text, 0)
        assert pos == 5  # position of \n

    # ── word navigation ──

    def test_goto_next_word(self):
        text = "hello world"
        pos = BabelString.goto_next_word(text, 0)
        assert pos == 6

    def test_goto_prev_word(self):
        text = "hello world"
        pos = BabelString.goto_prev_word(text, 7)
        assert pos == 6

    # ── grapheme cluster ──

    def test_goto_start_of_grapheme_cluster(self):
        # 'e' + combining acute
        text = "e\u0301"
        pos = BabelString.goto_start_of_grapheme_cluster(text, 2)
        assert pos == 0

    def test_goto_end_of_grapheme_cluster(self):
        text = "e\u0301"
        pos = BabelString.goto_end_of_grapheme_cluster(text, 0)
        assert pos == 2

    # ── search ──

    def test_find(self):
        assert BabelString.find("hello world", "world") == 6

    def test_find_not_found(self):
        assert BabelString.find("hello", "xyz") == -1

    def test_find_codepoint(self):
        assert BabelString.find("ABC", 0x42) == 1

    # ── compare ──

    def test_compare_equal(self):
        assert BabelString.compare("abc", "abc") == 0

    def test_compare_less(self):
        assert BabelString.compare("abc", "abd") == -1

    def test_compare_greater(self):
        assert BabelString.compare("abd", "abc") == 1

    # ── case ──

    def test_make_upper(self):
        assert BabelString.make_upper("hello") == "HELLO"

    def test_make_lower(self):
        assert BabelString.make_lower("HELLO") == "hello"

    def test_make_reverse(self):
        assert BabelString.make_reverse("abc") == "cba"

    # ── substring ──

    def test_left(self):
        assert BabelString.left("hello", 2) == "he"

    def test_mid(self):
        assert BabelString.mid("hello", 1, 3) == "ell"

    def test_right(self):
        assert BabelString.right("hello", 2) == "lo"

    # ── utility ──

    def test_remove_duplicates(self):
        assert BabelString.remove_duplicates("aabbcc") == "abc"

    def test_convert_ucn(self):
        assert BabelString.convert_ucn("\\u0041") == "A"

    def test_convert_ncr(self):
        assert BabelString.convert_ncr("&#x41;") == "A"
        assert BabelString.convert_ncr("&#65;") == "A"


# ═════════════════════  SCSU  ═════════════════════


class TestSCSU:
    def test_encode_ascii(self):
        s = SCSU()
        enc = s.encode("Hello World!")
        assert enc == b"Hello World!"

    def test_decode_ascii(self):
        s = SCSU()
        dec = s.decode(b"Hello World!")
        assert dec == "Hello World!"

    def test_roundtrip_ascii(self):
        s = SCSU()
        original = "Hello, World! 123"
        assert s.decode(s.encode(original)) == original

    def test_encode_empty(self):
        s = SCSU()
        assert s.encode("") == b""

    def test_decode_empty(self):
        s = SCSU()
        assert s.decode(b"") == ""

    def test_roundtrip_latin1(self):
        s = SCSU()
        original = "Caf\u00e9"  # Café
        assert s.decode(s.encode(original)) == original

    def test_roundtrip_mixed(self):
        s = SCSU()
        original = "Hello \u00e9\u00e0\u00eb world"
        assert s.decode(s.encode(original)) == original

    def test_strip_bom(self):
        s = SCSU(strip_bom=True)
        dec = s.decode(b"\xfe\xffHello")
        assert dec == "Hello"

    def test_no_strip_bom(self):
        s = SCSU(strip_bom=False)
        dec = s.decode(b"\xfe\xffHello")
        assert len(dec) > 0


# ═════════════════════  CharList  ═════════════════════


class TestCharList:
    def test_insert(self):
        cl = CharList()
        assert cl.insert(0x41) is True
        assert cl.insert(0x41) is False  # duplicate
        assert cl.count == 1

    def test_append(self):
        cl = CharList()
        assert cl.append(0x41) is True
        assert cl.append(0x42) is True

    def test_remove(self):
        cl = CharList([0x41, 0x42, 0x43])
        assert cl.remove(0x42) is True
        assert cl.remove(0x42) is False
        assert cl.count == 2

    def test_is_in_list(self):
        cl = CharList([0x41, 0x42])
        assert cl.is_in_list(0x41) is True
        assert cl.is_in_list(0x99) is False

    def test_contains(self):
        cl = CharList([0x41, 0x42])
        assert 0x41 in cl
        assert 0x99 not in cl

    def test_get_at(self):
        cl = CharList([0x41, 0x43, 0x42])  # auto-sorted
        assert cl.get_at(0) == 0x41
        assert cl.get_at(1) == 0x42
        assert cl.get_at(2) == 0x43
        assert cl.get_at(5) == 0

    def test_to_list(self):
        cl = CharList([0x43, 0x41])
        assert cl.to_list() == [0x41, 0x43]

    def test_to_string(self):
        cl = CharList([0x41, 0x42])
        assert cl.to_string() == "AB"

    def test_len(self):
        cl = CharList([0x41, 0x42, 0x43])
        assert len(cl) == 3

    def test_iter(self):
        cl = CharList([0x42, 0x41])
        assert list(cl) == [0x41, 0x42]

    def test_init_empty(self):
        cl = CharList()
        assert cl.count == 0

    def test_init_with_none(self):
        cl = CharList(None)
        assert cl.count == 0


# ═════════════════════  SymbolMappings  ═════════════════════


class TestSymbolMappings:
    def test_get_symbol_mapping_for_ascii(self):
        assert SymbolMappings.get_symbol_mapping_for_ascii(0x41) == 0xF041  # 'A'
        assert SymbolMappings.get_symbol_mapping_for_ascii(0x20) == 0xF020  # space

    def test_get_symbol_mapping_for_ascii_below_range(self):
        assert SymbolMappings.get_symbol_mapping_for_ascii(0x10) == 0x10  # unchanged

    def test_get_symbol_mapping_for_ascii_above_range(self):
        assert SymbolMappings.get_symbol_mapping_for_ascii(0x0100) == 0x0100  # unchanged

    def test_get_ascii_mapping_for_symbol(self):
        assert SymbolMappings.get_ascii_mapping_for_symbol(0xF041) == 0x41
        assert SymbolMappings.get_ascii_mapping_for_symbol(0xF020) == 0x20

    def test_get_ascii_mapping_for_non_symbol(self):
        assert SymbolMappings.get_ascii_mapping_for_symbol(0x0041) == 0x0041

    def test_get_symbol_font_mapping(self):
        # space -> space glyph
        assert SymbolMappings.get_symbol_font_mapping(0) == 0x0020
        # '!' -> 0x0021
        assert SymbolMappings.get_symbol_font_mapping(1) == 0x0021

    def test_get_symbol_font_mapping_out_of_range(self):
        assert SymbolMappings.get_symbol_font_mapping(999) == 0

    def test_get_symbol_font_mapping_count(self):
        assert SymbolMappings.get_symbol_font_mapping_count() == 224


# ═════════════════════  PostScriptNames  ═════════════════════


class TestPostScriptNames:
    def test_get_name_for_codepoint(self):
        assert PostScriptNames.get_name_for_codepoint(0x0041) == "A"
        assert PostScriptNames.get_name_for_codepoint(0x0020) == "space"
        assert PostScriptNames.get_name_for_codepoint(0x00E9) == "eacute"

    def test_get_name_for_codepoint_not_found(self):
        assert PostScriptNames.get_name_for_codepoint(0x4E00) == ""  # CJK

    def test_get_codepoint_for_name(self):
        assert PostScriptNames.get_codepoint_for_name("A") == 0x0041
        assert PostScriptNames.get_codepoint_for_name("space") == 0x0020
        assert PostScriptNames.get_codepoint_for_name("copyright") == 0x00A9

    def test_get_codepoint_for_name_not_found(self):
        assert PostScriptNames.get_codepoint_for_name("nonexistent") == 0

    def test_get_name_for_glyph_id(self):
        assert PostScriptNames.get_name_for_glyph_id(3) == "space"
        assert PostScriptNames.get_name_for_glyph_id(68) == "a"

    def test_get_name_for_glyph_id_out_of_range(self):
        assert PostScriptNames.get_name_for_glyph_id(999) == ""

    def test_get_codepoint_for_glyph_id(self):
        assert PostScriptNames.get_codepoint_for_glyph_id(68) == 0x0061  # 'a'
        assert PostScriptNames.get_codepoint_for_glyph_id(3) == 0x0020  # space

    def test_get_standard_names_count(self):
        assert PostScriptNames.get_standard_names_count() == 196

    def test_all_names(self):
        names = PostScriptNames.all_names()
        assert len(names) == 196
        assert names[3] == ("space", 0x0020)
        assert names[-1] == ("periodcentered", 0x2219)


# ═════════════════════  BabelString — extended  ═════════════════════


class TestBabelStringExtended:
    """Tests for newly added BabelString methods."""

    # ── Cursor movement ──
    def test_go_left(self):
        assert BabelString.go_left("AB", 2) == 1
        assert BabelString.go_left("AB", 1) == 0
        assert BabelString.go_left("AB", 0) == 0

    def test_go_right(self):
        assert BabelString.go_right("AB", 0) == 1
        assert BabelString.go_right("AB", 1) == 2
        assert BabelString.go_right("AB", 2) == 2

    def test_go_up_down(self):
        text = "line1\nline2\nline3"
        pos_end_l1 = 5  # position at end of "line1"
        result = BabelString.go_down(text, 2)
        assert result > 0  # moved down

    # ── Backspace / Delete ──
    def test_backspace(self):
        new_text, new_pos = BabelString.backspace("AB", 1)
        assert new_text == "B"
        assert new_pos == 0

    def test_delete_at(self):
        assert BabelString.delete_at("ABC", 1, 1) == "AC"
        assert BabelString.delete_at("ABC", 0, 2) == "C"

    def test_delete_line_break(self):
        text, pos, length = BabelString.delete_line_break("A\nB", 1, before=False)
        assert text == "AB"
        assert length == 1

    # ── Search ──
    def test_find_string(self):
        assert BabelString.find_string("hello world", "world") == 6
        assert BabelString.find_string("hello", "x") == -1

    def test_find_string_reverse(self):
        assert BabelString.find_string_reverse("abab", "ab", start=3) == 2

    def test_is_same_wild(self):
        assert BabelString.is_same_wild("hello", "hello") is True
        assert BabelString.is_same_wild("hello", "h.llo") is False  # no regex, exact match
        assert BabelString.is_same_wild("hello", "world") is False

    # ── String operations ──
    def test_count(self):
        assert BabelString.count("hello", "l") == 2
        assert BabelString.count("hello", ord("l")) == 2

    def test_remove(self):
        assert BabelString.remove("hello", ord("l")) == "heo"

    def test_replace(self):
        assert BabelString.replace("hello", ord("l"), ord("w")) == "hewwo"

    def test_remove_trailing_whitespace(self):
        assert BabelString.remove_trailing_whitespace("hello   ") == "hello"

    # ── Conversion ──
    def test_add_comma(self):
        assert BabelString.add_comma(1234567) == "1,234,567"
        assert BabelString.add_comma("1234") == "1,234"

    def test_hex_string_to_unicode(self):
        assert BabelString.hex_string_to_unicode("0041") == 0x41
        assert BabelString.hex_string_to_unicode("1F600") == 0x1F600

    def test_string_to_integer(self):
        assert BabelString.string_to_integer("123") == 123
        assert BabelString.string_to_integer("") == 0

    # ── Selection ──
    def test_select_word(self):
        start, end = BabelString.select_word("hello world", 0)
        assert (start, end) == (0, 5)

    def test_get_next_word(self):
        word, wlen, pos = BabelString.get_next_word("hello world", 0)
        assert word == "hello"
        assert wlen == 5
