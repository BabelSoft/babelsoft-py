"""Tests for extra per-character properties (src/unicode/extras.py).

Binary properties, NamesList (aliases/notes/cross-references), standardized
variation sequences, emoji variation sequences, and named sequences.
"""

import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent
sys.path.append(str(LIB_DIR))

from src.unicode.extras import (  # noqa: E402
    binary_properties,
    emoji_variation_sequences,
    has_binary_property,
    named_sequences_for,
    nameslist,
    standardized_variants,
)


class TestBinaryProperties:
    def test_dash(self):
        assert has_binary_property(0x2014, "Dash")  # EM DASH
        assert not has_binary_property(0x41, "Dash")

    def test_emoji_from_emoji_data(self):
        # Emoji properties come from emoji/emoji-data.txt (merged in extras).
        assert has_binary_property(0x1F600, "Emoji")
        assert has_binary_property(0x1F600, "Emoji_Presentation")

    def test_binary_list(self):
        props = binary_properties(0x23)  # NUMBER SIGN
        assert "Emoji" in props
        assert "Pattern_Syntax" in props
        assert "Emoji_Component" in props


class TestNamesList:
    def test_control_alias(self):
        nl = nameslist(0x0000)
        assert "NULL" in nl["aliases"]

    def test_note(self):
        nl = nameslist(0x000E)  # SHIFT OUT
        assert "SHIFT OUT" in nl["aliases"]
        assert any("LOCKING-SHIFT ONE" in n for n in nl["notes"])

    def test_hash_aliases_and_xrefs(self):
        nl = nameslist(0x0023)  # NUMBER SIGN
        assert any("hashtag" in a for a in nl["aliases"])
        assert any("octothorpe" in a for a in nl["aliases"])
        assert any("numero sign" in x for x in nl["xrefs"])

    def test_no_annotations(self):
        nl = nameslist(0x41)
        assert nl == {"aliases": [], "notes": [], "xrefs": []}


class TestVariationSequences:
    def test_standardized_variant(self):
        vs = standardized_variants(0x2205)  # EMPTY SET
        assert any("diagonal stroke" in desc for _, desc in vs)
        assert all(0xFE00 <= v <= 0xFE0F or 0xE0100 <= v <= 0xE01EF for v, _ in vs)

    def test_emoji_variants(self):
        vs = emoji_variation_sequences(0x2764)  # HEAVY BLACK HEART
        styles = [s for _, s in vs]
        assert "text style" in styles
        assert "emoji style" in styles

    def test_no_variants(self):
        assert standardized_variants(0x41) == []
        assert emoji_variation_sequences(0x41) == []


class TestNamedSequences:
    def test_keycap(self):
        ns = named_sequences_for(0x0023)
        assert any(name == "KEYCAP NUMBER SIGN" and cps == (0x23, 0xFE0F, 0x20E3) for name, cps in ns)

    def test_none(self):
        assert named_sequences_for(0x41) == []
