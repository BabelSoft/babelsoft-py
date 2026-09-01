"""Tests for the extended (XML-style) character properties
(src/unicode/extended.py) — mirrors the C++ CDialogXmlProperties output."""

import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent
sys.path.append(str(LIB_DIR))

from babelsoft.unicode.extended import extended_properties, name_aliases  # noqa: E402


class TestExtendedProperties:
    def test_row_count_and_order(self):
        rows = extended_properties(0x10400)
        assert len(rows) == 117
        assert rows[0] == ["Code Point Type", "Character"]
        assert rows[1] == ["Code Point", "10400"]
        assert rows[-1][0] == "Indic Conjunct Break"

    def test_deseret_u10400_values(self):
        rows = dict(extended_properties(0x10400))
        assert rows["General Category"] == "Lu [Letter, Uppercase]"
        assert rows["Canonical Combining Class"] == "0 [Not Reordered]"
        assert rows["Bidi Class"] == "L [Left-to-Right]"
        assert rows["Script"] == "Dsrt [Deseret]"
        assert rows["Simple Lowercase Mapping"] == "10428"
        assert rows["Changes When NFKC Casefolded"] == "Yes"
        assert rows["NFC Quick Check"] == "Yes"
        assert rows["Alphabetic"] == "Yes"
        assert rows["Uppercase"] == "Yes"
        assert rows["Grapheme Base"] == "Yes"

    def test_latin_a(self):
        rows = dict(extended_properties(0x41))
        assert rows["Name"] == "LATIN CAPITAL LETTER A"
        assert rows["Simple Lowercase Mapping"] == "0061"
        assert rows["Uppercase Mapping"] == "0041"
        assert rows["Alphabetic"] == "Yes"
        assert rows["Lowercase"] == "No"
        assert rows["Hangul Syllable Type"] == "NA [Not Applicable]"

    def test_name_aliases(self):
        assert name_aliases(0x41) == []
        aliases = name_aliases(0)
        assert ["control", "NULL"] in aliases
        assert ["abbreviation", "NUL"] in aliases
