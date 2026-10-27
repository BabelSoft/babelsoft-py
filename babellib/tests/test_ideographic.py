"""Tests for the ideographic (CJKV) properties on the CJK class (src/cjkv/cjk.py)."""

import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent
sys.path.append(str(LIB_DIR))

from babelsoft.cjkv.cjk import CJK


def ideographic_properties(cp: int) -> dict:
    return CJK(cp).ideographic_properties()


class TestIdeographicProperties:
    def test_non_ideograph_empty(self):
        assert ideographic_properties(0x41) == {}
        assert ideographic_properties(0x20000) != {}  # Extension B ideograph

    def test_u2a850(self):
        """𪡐 — mirrors the C++ CDialogCJKV output the user pasted."""
        d = ideographic_properties(0x2A850)
        assert d["radical"]["glyph"]["char"] == "口"
        assert d["radical"]["glyph"]["cp"] == 0x53E3
        assert d["radical"]["strokes"] == "30.8"
        assert d["ids"] == "⿰右回"
        # No related characters, no readings for this char.
        assert d["related"] == {
            "traditional": None,
            "simplified_chinese": None,
            "simplified_japanese": None,
        }
        assert all(v == "" for v in d["readings"].values())
        # Only the TCA source is present.
        by_label = dict(d["sources"])
        assert by_label["TCA"] == "TC-5358"
        assert all(v == "" for k, v in by_label.items() if k != "TCA")

    def test_u4e00(self):
        d = ideographic_properties(0x4E00)
        assert d["radical"]["strokes"] == "1.0"
        assert d["readings"]["mandarin"] == "yī"
        by_label = dict(d["sources"])
        assert by_label["China"] == "G0-523B"
        assert by_label["Japan"] == "J0-306C"
        assert by_label["ROK"] == "K0-6C69"  # K must not match the KP ref
        assert by_label["DPRK"] == "KP0-FCD6"
        assert by_label["Vietnam"] == "V1-4A21"

    def test_u9f99_related(self):
        """龙 — simplified char maps to traditional 龍 and Japanese 竜."""
        d = ideographic_properties(0x9F99)
        assert d["related"]["traditional"]["char"] == "龍"
        assert d["related"]["traditional"]["cp"] == 0x9F8D
        assert d["related"]["simplified_chinese"]["char"] == "龙"
        assert d["related"]["simplified_japanese"]["char"] == "竜"

    def test_u6c49_related(self):
        """汉 — simplified char maps to traditional 漢."""
        d = ideographic_properties(0x6C49)
        assert d["related"]["traditional"]["char"] == "漢"
        assert d["related"]["traditional"]["cp"] == 0x6F22
        assert d["related"]["simplified_chinese"]["char"] == "汉"

    def test_source_labels(self):
        """All 13 labels match the user's dump, in order."""
        d = ideographic_properties(0x2A850)
        labels = [row[0] for row in d["sources"]]
        assert labels == [
            "China",
            "Hong Kong SAR",
            "Macao SAR",
            "TCA",
            "Japan",
            "SAT",
            "ROK",
            "DPRK",
            "Malaysia",
            "Singapore",
            "UK",
            "US & UTC",
            "Vietnam",
        ]
