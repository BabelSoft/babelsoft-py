"""Tests for Character History (per-version codepoint/name changes)."""

import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent
sys.path.append(str(LIB_DIR))

from babelsoft.unicode import Unicode
from babelsoft.utils_.dirs import Dirs
from babelsoft.utils_.versions import VERSION_DIRS

from babelmap.backend.history import character_history

# Comparing releases needs every historical UCD snapshot, which the source
# checkout does not carry (see babellib/tools/sync_data.py --all).
_MISSING_SNAPSHOTS = [folder for _version, folder in VERSION_DIRS if not (Dirs.UNICODE / folder).is_dir()]
pytestmark = pytest.mark.skipif(
    bool(_MISSING_SNAPSHOTS),
    reason=(
        f"{len(_MISSING_SNAPSHOTS)} historical Unicode snapshot(s) not installed;"
        " run: python babellib/tools/sync_data.py --all"
    ),
)


class TestUnicode1Mappings:
    def test_tibetan_reverse(self):
        # TIBETAN LETTER KA: U+1000 (1.0) -> U+0F40 (2.0)
        assert Unicode.unicode1_codepoint(0x0F40) == 0x1000

    def test_hangul_reverse(self):
        # HANGUL SYLLABLE GA: U+3400 (1.0) -> U+AC00 (2.0)
        assert Unicode.unicode1_codepoint(0xAC00) == 0x3400
        # Hangul syllables beyond the 1.0 table are not mapped
        assert Unicode.unicode1_codepoint(0xD7A3) is None

    def test_greek_move(self):
        # GREEK NON-SPACING IOTA BELOW: U+0370 (1.0) -> U+0345
        assert Unicode.unicode1_codepoint(0x0345) == 0x0370

    def test_removed_and_moved_codepoints(self):
        # U+0371's 1.0 occupant (DASIA) was removed
        assert Unicode.is_unicode1_removed(0x0371)
        # U+0370's 1.0 occupant (IOTA BELOW) moved away
        assert Unicode.is_unicode1_moved(0x0370)
        # normal characters are unaffected
        assert not Unicode.is_unicode1_removed(0x0041)
        assert not Unicode.is_unicode1_moved(0x0041)


class TestCharacterHistory:
    def _row(self, h, version) -> dict:
        row = next((r for r in h["rows"] if r["version"] == version), None)
        assert row is not None, f"no history row for Unicode {version}"
        return row

    def test_tibetan_ka_move(self):
        h = character_history(0x0F40)
        r10 = self._row(h, "1.0.0")
        assert r10["present"] and r10["codepoint"] == 0x1000 and r10["name"] == "TIBETAN LETTER KA"
        assert r10["moved"] is True
        # Tibetan removed in 1.1, re-added at U+0F40 in 2.0
        assert not self._row(h, "1.1.5")["present"]
        r2 = self._row(h, "2.0.14")
        assert r2["present"] and r2["codepoint"] == 0x0F40 and r2["moved"] is False

    def test_hangul_move(self):
        h = character_history(0xAC00)
        r10 = self._row(h, "1.0.0")
        assert r10["present"] and r10["codepoint"] == 0x3400 and r10["name"] == "HANGUL SYLLABLE KIYEOK A"
        assert r10["moved"] is True

    def test_greek_move(self):
        h = character_history(0x0345)
        r10 = self._row(h, "1.0.0")
        assert r10["present"] and r10["codepoint"] == 0x0370 and r10["name"] == "GREEK NON-SPACING IOTA BELOW"

    def test_stable_character(self):
        h = character_history(0x0041)
        assert all(r["codepoint"] == 0x0041 for r in h["rows"] if r["present"])
        assert not any(r["moved"] for r in h["rows"])

    def test_full_property_columns(self):
        # present rows carry the full UCD columns (gc/ccc/bidi/...)
        h = character_history(0x0041)
        r17 = self._row(h, "17.0.0")
        assert r17["gc"] == "Lu" and r17["ccc"] == "0" and r17["bidi"] == "L"
        for k in ("gc", "ccc", "bidi", "decomp", "dec", "digit", "num", "mirrored", "uni1", "iso", "up", "lo", "ti"):
            assert k in r17

    def test_hangul_1_1_5_data(self):
        # B2C9 (HANGUL SYLLABLE NIG): in Unicode 1.1.5 it was at U+35A7 with data
        h = character_history(0xB2C9)
        r115 = self._row(h, "1.1.5")
        assert r115["present"] is True
        assert r115["codepoint"] == 0x35A7
        assert r115["name"] == "HANGUL SYLLABLE NIEUN I KIYEOK"
        assert r115["moved"] is True
        assert r115["gc"] == "Lo" and r115["ccc"] == "0"
        assert r115["decomp"]  # real decomposition present in the 1.1.5 file
        # by 2.0 it had moved to U+B2C9 and been renamed
        r20 = self._row(h, "2.0.14")
        assert r20["present"] and r20["codepoint"] == 0xB2C9 and r20["name"] == "HANGUL SYLLABLE NIG"
        # decomposition is algorithmic and present in every subsequent version
        assert r20["decomp"] == "1102 1175 11A8"
        assert self._row(h, "17.0.0")["decomp"] == "1102 1175 11A8"

    def test_all_versions_present(self):
        # every history has one row per Unicode version
        for cp in (0x0041, 0x0F40, 0xAC00, 0x4E00):
            h = character_history(cp)
            assert len(h["rows"]) == 36
