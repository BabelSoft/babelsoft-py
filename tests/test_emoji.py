"""Tests for the Emojipedia-style emoji data + search (src/unicode/emoji.py)."""

import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent
sys.path.append(str(LIB_DIR))

from src.unicode.emoji import Emoji, all_emoji, search  # noqa: E402


class TestEmojiData:
    def test_loads_many_emoji(self):
        all_e = all_emoji()
        assert len(all_e) > 3000  # Unicode 17 has ~3800 RGI emoji
        assert all(isinstance(e, Emoji) for e in all_e)

    def test_fields_present(self):
        for e in all_emoji()[:200]:
            assert e.name
            assert e.group
            assert e.subgroup
            assert e.codepoints
            assert e.version

    def test_first_is_grinning_face(self):
        # CLDR order starts with Smileys & Emotion → face-smiling → grinning face
        e = all_emoji()[0]
        assert e.codepoints == (0x1F600,)
        assert e.name == "grinning face"

    def test_display_filter_excludes_unqualified_dupes(self):
        # heart exclamation has a fully-qualified (2763 FE0F) and an unqualified
        # (2763) variant; the picker should only show the fully-qualified one.
        hits = [e for e in all_emoji() if e.name == "heart exclamation"]
        assert len(hits) == 1
        assert hits[0].codepoints == (0x2763, 0xFE0F)

    def test_text_reconstructs_glyph(self):
        e = all_emoji()[0]
        assert e.text == "\U0001f600"  # 😀


class TestEmojiSearch:
    def test_search_by_name(self):
        hits = search("grinning")
        names = [e.name for e in hits]
        assert "grinning face" in names
        assert "grinning cat" in names

    def test_search_by_codepoint(self):
        hits = search("1f600")
        assert [e.codepoints for e in hits] == [(0x1F600,)]
        assert hits[0].name == "grinning face"

    def test_search_by_codepoint_uppercase_uplus(self):
        hits = search("U+1F600")
        assert hits and hits[0].codepoints == (0x1F600,)

    def test_search_by_sequence_codepoints(self):
        hits = search("2763 FE0F")
        assert any(e.codepoints == (0x2763, 0xFE0F) for e in hits)

    def test_search_synonym(self):
        hits = search("smile")
        assert len(hits) >= 10
        assert any("grinning" in e.name or "smiling" in e.name for e in hits)

    def test_search_keyword_substring(self):
        hits = search("heart")
        assert any("heart" in e.name for e in hits)

    def test_search_word_prefix(self):
        # "grin" should match "grinning face" via word-prefix
        hits = search("grin")
        assert any(e.name == "grinning face" for e in hits)

    def test_search_empty_returns_browse_start(self):
        hits = search("")
        assert hits[0].name == "grinning face"

    def test_search_no_match(self):
        assert search("zzzzqqqq") == []

    def test_search_ranking_exact_first(self):
        hits = search("grinning face")
        assert hits[0].name == "grinning face"
