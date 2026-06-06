"""Tests for src/main_/ package — BabelString, SCSU, CharList."""

import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent
sys.path.append(str(LIB_DIR))

from src.main_ import BabelString, CharList, SCSU  # noqa: E402

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
