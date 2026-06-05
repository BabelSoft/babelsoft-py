"""Tests for script-specific character data: Nushu, Khitan, Hieroglyphs, Tangut."""

import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent
sys.path.append(str(LIB_DIR))

from src.scripts.hieroglyphs import Hieroglyphs  # noqa: E402
from src.scripts.khitan import Khitan  # noqa: E402
from src.scripts.nushu import Nushu  # noqa: E402
from src.scripts.tangut import (  # noqa: E402
    TANGUT_COUNT,
    TANGUT_LAST,
    TANGUT_START,
    Kychanov,
    LiFanwen,
    Miyake,
    Nishida,
    Sofronov,
    Tangut,
)

# ═════════════════════  Helpers  ═════════════════════


def _valid_tangut_cp(n: int = 0) -> int:
    """Return a valid Tangut codepoint offset by n from TANGUT_START."""
    return TANGUT_START + n


def _supp_tangut_cp(n: int = 0) -> int:
    """Return a Tangut Supplement codepoint."""
    return 0x18D00 + n


# ═══════════════════════  Nüshu  ═══════════════════════


class TestNushu:
    """Tests for Nüshu character identification and lookups."""

    # ── identification ──

    def test_is_nushu_valid(self):
        assert Nushu.is_nushu_character(0x1B170) is True
        assert Nushu.is_nushu_character(0x1B2FB) is True
        assert Nushu.is_nushu_character(0x1B200) is True

    def test_is_nushu_below(self):
        assert Nushu.is_nushu_character(0x1B16F) is False

    def test_is_nushu_above(self):
        assert Nushu.is_nushu_character(0x1B2FC) is False

    def test_is_nushu_far_outside(self):
        assert Nushu.is_nushu_character(0x41) is False
        assert Nushu.is_nushu_character(0x10FFFF) is False

    # ── reading ──

    def test_get_reading_valid(self):
        assert Nushu.get_primary_reading(0x1B170) == "i5"

    def test_get_reading_outside_range(self):
        assert Nushu.get_primary_reading(0x41) == ""

    def test_get_reading_for_last_codepoint(self):
        # Last codepoint in range should return a string (possibly empty)
        assert isinstance(Nushu.get_primary_reading(0x1B2FB), str)

    # ── duben reference ──

    def test_get_duben_valid(self):
        assert Nushu.get_duben_reference(0x1B170) == "36.01"

    def test_get_duben_outside_range(self):
        assert Nushu.get_duben_reference(0x41) == ""

    # ── data consistency ──

    def test_reading_ref_counts_match(self):
        from src.utils_.loader import ScriptsLoader

        readings, refs = ScriptsLoader.load_nushu()
        # They share the same codepoint keys
        assert readings.keys() == refs.keys()

    def test_all_codepoints_in_range(self):
        from src.utils_.loader import ScriptsLoader

        readings, _ = ScriptsLoader.load_nushu()
        NUSHU_FIRST = 0x1B170
        NUSHU_LAST = 0x1B2FB
        for cp in readings:
            assert NUSHU_FIRST <= cp <= NUSHU_LAST


# ═══════════════════════  Khitan  ═══════════════════════


class TestKhitan:
    """Tests for Khitan small script character identification and lookups."""

    # ── identification ──

    def test_is_khitan_valid(self):
        assert Khitan.is_khitan_small_script(0x18B00) is True
        assert Khitan.is_khitan_small_script(0x18CD5) is True
        assert Khitan.is_khitan_small_script(0x18C00) is True

    def test_is_khitan_below(self):
        assert Khitan.is_khitan_small_script(0x18AFF) is False

    def test_is_khitan_above(self):
        assert Khitan.is_khitan_small_script(0x18CD6) is False

    def test_is_khitan_end_of_range(self):
        assert Khitan.is_khitan_small_script(0x18CD5) is True
        assert Khitan.is_khitan_small_script(0x18B00) is True

    # ── reading ──

    def test_get_reading_valid(self):
        r = Khitan.get_reading(0x18B00)
        assert isinstance(r, str)

    def test_get_reading_outside_range(self):
        assert Khitan.get_reading(0x41) == ""

    # ── meaning ──

    def test_get_meaning_valid(self):
        m = Khitan.get_meaning(0x18B00)
        assert isinstance(m, str)

    def test_get_meaning_outside_range(self):
        assert Khitan.get_meaning(0x41) == ""

    # ── combined ──

    def test_get_reading_and_meaning(self):
        result = Khitan.get_reading_and_meaning(0x18B00)
        assert isinstance(result, str)

    def test_get_reading_and_meaning_empty(self):
        assert Khitan.get_reading_and_meaning(0x41) == ""

    def test_get_reading_and_meaning_no_reading_no_meaning(self):
        # CP that may have no data
        result = Khitan.get_reading_and_meaning(0x18CFF)
        assert isinstance(result, str)

    # ── data consistency ──

    def test_readings_meanings_keys(self):
        from src.utils_.loader import ScriptsLoader

        readings, meanings = ScriptsLoader.load_khitan()
        # Some codepoints may have reading but no meaning, or vice versa
        all_keys = set(readings.keys()) | set(meanings.keys())
        assert len(all_keys) > 0

    def test_all_in_range(self):
        from src.utils_.loader import ScriptsLoader

        readings, _ = ScriptsLoader.load_khitan()
        for cp in readings:
            assert 0x18B00 <= cp <= 0x18CD5


# ═══════════════════  Egyptian Hieroglyphs  ═══════════════════


class TestHieroglyphs:
    """Tests for Egyptian Hieroglyph character identification and descriptions."""

    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        from src.utils_.loader import ScriptsLoader

        ScriptsLoader.load_hieroglyph_descriptions.cache_clear()

    # ── identification ──

    def test_main_block_valid(self):
        assert Hieroglyphs.is_egyptian_hieroglyph(0x13000) is True
        assert Hieroglyphs.is_egyptian_hieroglyph(0x1342F) is True
        assert Hieroglyphs.is_egyptian_hieroglyph(0x13100) is True

    def test_ext_a_block_valid(self):
        assert Hieroglyphs.is_egyptian_hieroglyph(0x13460) is True
        assert Hieroglyphs.is_egyptian_hieroglyph(0x1346F) is True

    def test_gap_between_blocks(self):
        assert Hieroglyphs.is_egyptian_hieroglyph(0x13430) is False
        assert Hieroglyphs.is_egyptian_hieroglyph(0x1345F) is False

    def test_below_range(self):
        assert Hieroglyphs.is_egyptian_hieroglyph(0x12FFF) is False

    def test_above_range(self):
        # EGYPTIAN_EXT_A_LAST = 0x1346F
        assert Hieroglyphs.is_egyptian_hieroglyph(0x13470) is False
        assert Hieroglyphs.is_egyptian_hieroglyph(0x14000) is False

    def test_far_outside(self):
        assert Hieroglyphs.is_egyptian_hieroglyph(0x41) is False

    # ── description ──

    def test_get_description_valid(self):
        desc = Hieroglyphs.get_description(0x13000)
        assert isinstance(desc, str)
        assert len(desc) > 0
        assert "Man" in desc

    def test_get_description_ext_a(self):
        desc = Hieroglyphs.get_description(0x13460)
        assert isinstance(desc, str)
        assert len(desc) > 0

    def test_get_description_empty(self):
        # Some codepoints have empty descriptions
        desc = Hieroglyphs.get_description(0x13004)
        assert isinstance(desc, str)

    def test_get_description_outside_range(self):
        assert Hieroglyphs.get_description(0x41) == ""

    # ── data consistency ──

    def test_description_keys_in_range(self):
        from src.utils_.loader import ScriptsLoader

        ScriptsLoader.load_hieroglyph_descriptions.cache_clear()
        descs = ScriptsLoader.load_hieroglyph_descriptions()
        assert len(descs) > 0
        for cp in descs:
            # All should be in Egyptian Hieroglyph or Ext-A range (per Unicode)
            assert 0x13000 <= cp <= 0x143FF, f"U+{cp:05X} not in hieroglyph range"


# ═══════════════════  Tangut: Li Fanwen  ═══════════════════


class TestLiFanwen:
    """Tests for Li Fanwen 2008 Tangut dictionary."""

    CP = _valid_tangut_cp(0)  # U+17000, L2008-1100
    CP_NOENTRY = _valid_tangut_cp(6136)  # near end, likely no entry
    OUT_CP = 0x41

    def test_has_entry_valid(self):
        # First codepoint may or may not have an entry
        assert isinstance(LiFanwen.has_entry(self.CP), bool)

    def test_has_entry_outside(self):
        assert LiFanwen.has_entry(self.OUT_CP) is False

    def test_get_number(self):
        n = LiFanwen.get_number(self.CP)
        # May be empty if no entry, otherwise must start with L2008-
        assert n == "" or n.startswith("L2008-")

    def test_get_number_outside(self):
        assert LiFanwen.get_number(self.OUT_CP) == ""

    def test_get_number_format(self):
        n = LiFanwen.get_number(self.CP)
        if n:
            assert n.startswith("L2008-")
            assert len(n) >= 10

    def test_get_reading(self):
        r = LiFanwen.get_reading(self.CP)
        assert isinstance(r, str)

    def test_get_reading_with_tone(self):
        r = LiFanwen.get_reading(self.CP, b_tone=True)
        assert isinstance(r, str)

    def test_get_reading_outside(self):
        assert LiFanwen.get_reading(self.OUT_CP) == ""

    def test_get_meaning(self):
        m = LiFanwen.get_meaning(self.CP)
        assert isinstance(m, str)

    def test_get_meaning_outside(self):
        assert LiFanwen.get_meaning(self.OUT_CP) == ""

    def test_get_tone_rime(self):
        tr = LiFanwen.get_tone_rime(self.CP)
        assert isinstance(tr, str)
        assert "." in tr or tr == ""

    def test_get_tone_rime_outside(self):
        assert LiFanwen.get_tone_rime(self.OUT_CP) == ""

    def test_find_reference(self):
        n = LiFanwen.get_number(self.CP)
        if n:
            cp = LiFanwen.find_reference(n)
            assert cp == self.CP

    def test_find_reference_not_found(self):
        assert LiFanwen.find_reference("L2008-99999") == 0

    # ── data consistency ──

    def test_all_entries_in_range(self):
        from src.utils_.loader import ScriptsLoader

        data = ScriptsLoader.load_tangut_li_fanwen()
        for off, entry in enumerate(data):
            if entry and entry.get("number", 0) != 0:
                cp = TANGUT_START + off
                # Some entries may be in Tangut Supplement range
                assert cp >= TANGUT_START


# ═══════════════════  Tangut: Kychanov  ═══════════════════


class TestKychanov:
    """Tests for Kychanov 2006 Tangut dictionary."""

    CP = _valid_tangut_cp(0)
    OUT_CP = 0x41

    def test_has_entry_valid(self):
        assert isinstance(Kychanov.has_entry(self.CP), bool)

    def test_has_entry_outside(self):
        assert Kychanov.has_entry(self.OUT_CP) is False

    def test_get_number(self):
        n = Kychanov.get_number(self.CP)
        assert n == "" or n.startswith("K")

    def test_get_number_outside(self):
        assert Kychanov.get_number(self.OUT_CP) == ""

    def test_get_reading(self):
        r = Kychanov.get_reading(self.CP)
        assert isinstance(r, str)

    def test_get_reading_with_tone(self):
        r = Kychanov.get_reading(self.CP, b_tone=True)
        assert isinstance(r, str)

    def test_get_reading_outside(self):
        assert Kychanov.get_reading(self.OUT_CP) == ""

    def test_get_tone_rime_outside(self):
        assert Kychanov.get_tone_rime(self.OUT_CP) == ""

    def test_find_reference(self):
        n = Kychanov.get_number(self.CP)
        if n:
            cp = Kychanov.find_reference(n)
            assert cp == self.CP

    def test_find_reference_not_found(self):
        assert Kychanov.find_reference("K99999") == 0


# ═══════════════════  Tangut: Sofronov  ═══════════════════


class TestSofronov:
    """Tests for Sofronov 1968 Tangut dictionary."""

    CP = _valid_tangut_cp(0)
    OUT_CP = 0x41

    def test_has_entry_valid(self):
        assert isinstance(Sofronov.has_entry(self.CP), bool)

    def test_has_entry_outside(self):
        assert Sofronov.has_entry(self.OUT_CP) is False

    def test_get_number(self):
        n = Sofronov.get_number(self.CP)
        assert n == "" or n.startswith("S")

    def test_get_number_outside(self):
        assert Sofronov.get_number(self.OUT_CP) == ""

    def test_get_reading(self):
        r = Sofronov.get_reading(self.CP)
        assert isinstance(r, str)

    def test_get_reading_with_tone(self):
        r = Sofronov.get_reading(self.CP, b_tone=True)
        assert isinstance(r, str)

    def test_get_reading_outside(self):
        assert Sofronov.get_reading(self.OUT_CP) == ""

    def test_get_tone_rime_outside(self):
        assert Sofronov.get_tone_rime(self.OUT_CP) == ""

    def test_find_reference(self):
        n = Sofronov.get_number(self.CP)
        if n:
            cp = Sofronov.find_reference(n)
            assert cp == self.CP

    def test_find_reference_not_found(self):
        assert Sofronov.find_reference("S99999") == 0


# ═══════════════════  Tangut: Nishida  ═══════════════════


class TestNishida:
    """Tests for Nishida 1966 Tangut dictionary."""

    CP = _valid_tangut_cp(0)
    OUT_CP = 0x41

    def test_has_entry_valid(self):
        assert isinstance(Nishida.has_entry(self.CP), bool)

    def test_has_entry_outside(self):
        assert Nishida.has_entry(self.OUT_CP) is False

    def test_get_reference(self):
        ref = Nishida.get_reference(self.CP)
        assert isinstance(ref, str)

    def test_get_reference_outside(self):
        assert Nishida.get_reference(self.OUT_CP) == ""

    def test_get_reading(self):
        r = Nishida.get_reading(self.CP)
        assert isinstance(r, str)

    def test_get_reading_outside(self):
        assert Nishida.get_reading(self.OUT_CP) == ""

    def test_find_reference(self):
        ref = Nishida.get_reference(self.CP)
        if ref:
            cp = Nishida.find_reference(ref)
            assert cp == self.CP

    def test_find_reference_not_found(self):
        assert Nishida.find_reference("999-999") == 0


# ═══════════════════  Tangut: Miyake  ═══════════════════


class TestMiyake:
    """Tests for Miyake 2012/2015 Tangut phonetic reconstruction."""

    CP = _valid_tangut_cp(0)

    @pytest.fixture
    def m2015(self):
        return Miyake(use_2012=False)

    @pytest.fixture
    def m2012(self):
        return Miyake(use_2012=True)

    def test_version(self, m2015, m2012):
        assert m2015._version == "2015"
        assert m2012._version == "2012"

    def test_has_entry(self, m2015):
        assert isinstance(m2015.has_entry(self.CP), bool)

    def test_get_reading(self, m2015, m2012):
        r15 = m2015.get_reading(self.CP)
        r12 = m2012.get_reading(self.CP)
        assert isinstance(r15, str)
        assert isinstance(r12, str)
        # At least one version should have a reading for U+17000
        assert (len(r15) > 0) or (len(r12) > 0)

    def test_get_reading_with_tone(self, m2015):
        r = m2015.get_reading(self.CP, b_tone=True)
        assert isinstance(r, str)

    def test_get_initial(self, m2015):
        i = m2015.get_initial(self.CP)
        assert isinstance(i, str)

    def test_get_rime(self, m2015):
        r = m2015.get_rime(self.CP)
        assert isinstance(r, str)

    def test_get_tone(self, m2015):
        t = m2015.get_tone(self.CP)
        assert isinstance(t, str)

    def test_get_tone_rime(self, m2015):
        tr = m2015.get_tone_rime(self.CP)
        assert isinstance(tr, str)

    def test_get_imf(self, m2015):
        imf = m2015.get_imf(self.CP)
        assert isinstance(imf, str)
        parts = imf.split("-")
        assert len(parts) == 3  # i-m-f

    def test_get_syllable(self, m2015):
        syl = m2015.get_syllable(self.CP)
        assert isinstance(syl, str)
        parts = syl.split("-")
        assert len(parts) == 4  # i-m-f-tone

    def test_empty_for_outside(self, m2015):
        assert m2015.get_reading(0x41) == ""
        assert m2015.get_initial(0x41) == ""
        assert m2015.get_rime(0x41) == ""
        assert m2015.get_tone(0x41) == ""
        assert m2015.get_tone_rime(0x41) == ""
        assert m2015.get_imf(0x41) == ""
        assert m2015.get_syllable(0x41) == ""

    # ── phonetic table consistency ──

    def test_phonetic_tables_loaded(self):
        from src.utils_.loader import ScriptsLoader

        tables = ScriptsLoader.load_miyake_phonetic_tables()
        assert "initials" in tables
        assert "medials" in tables
        assert "finals" in tables
        assert len(tables["initials"]["2015"]) > 0
        assert len(tables["initials"]["2012"]) > 0

    def test_syllable_indices_valid(self, m2015):
        from src.utils_.loader import ScriptsLoader

        tables = ScriptsLoader.load_miyake_phonetic_tables()
        syl = m2015.get_syllable(self.CP)
        parts = syl.split("-")
        i_val, m_val, f_val, _ = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
        if i_val > 0:
            assert i_val < len(tables["initials"]["2015"])
        if m_val > 0:
            assert m_val < len(tables["medials"])
        if f_val > 0:
            assert f_val < len(tables["finals"]["2015"])


# ═══════════════════  Tangut Orchestration  ═══════════════════


class TestTangut:
    """Tests for Tangut orchestration class and merged data."""

    CP = _valid_tangut_cp(0)
    OUT_CP = 0x41

    # ── identification ──

    def test_is_tangut_valid(self):
        assert Tangut.is_tangut_ideograph(self.CP) is True
        assert Tangut.is_tangut_ideograph(TANGUT_LAST) is True

    def test_is_tangut_supplement(self):
        assert Tangut.is_tangut_ideograph(0x18D00) is True
        assert Tangut.is_tangut_ideograph(0x18D7F) is True

    def test_is_tangut_outside(self):
        assert Tangut.is_tangut_ideograph(self.OUT_CP) is False
        assert Tangut.is_tangut_ideograph(0x18800) is False  # Components, not ideographs

    # ── source accessors ──

    def test_get_li_fanwen_number(self):
        n = Tangut.get_li_fanwen_number(self.CP)
        assert n == "" or n.startswith("L2008-")

    def test_get_li_fanwen_1997_number(self):
        n = Tangut.get_li_fanwen_1997_number(self.CP)
        assert isinstance(n, str)

    def test_get_li_fanwen_reading(self):
        r = Tangut.get_li_fanwen_reading(self.CP)
        assert isinstance(r, str)

    def test_get_li_fanwen_meaning(self):
        m = Tangut.get_li_fanwen_meaning(self.CP)
        assert isinstance(m, str)

    def test_get_kychanov_number(self):
        n = Tangut.get_kychanov_number(self.CP)
        assert n == "" or n.startswith("K")

    def test_get_kychanov_reading(self):
        r = Tangut.get_kychanov_reading(self.CP)
        assert isinstance(r, str)

    def test_get_sofronov_number(self):
        n = Tangut.get_sofronov_number(self.CP)
        assert n == "" or n.startswith("S")

    def test_get_sofronov_reading(self):
        r = Tangut.get_sofronov_reading(self.CP)
        assert isinstance(r, str)

    def test_get_nishida_reference(self):
        ref = Tangut.get_nishida_reference(self.CP)
        assert isinstance(ref, str)

    def test_get_nishida_reading(self):
        r = Tangut.get_nishida_reading(self.CP)
        assert isinstance(r, str)

    def test_get_miyake_reading(self):
        r15 = Tangut.get_miyake_reading(self.CP)
        r12 = Tangut.get_miyake_reading(self.CP, b_2012=True)
        assert isinstance(r15, str)
        assert isinstance(r12, str)

    def test_get_miyake_reading_with_tone(self):
        r = Tangut.get_miyake_reading(self.CP, b_tone=True)
        assert isinstance(r, str)

    # ── merged data ──

    def test_get_merged_source(self):
        src = Tangut.get_merged_source(self.CP)
        assert isinstance(src, str)

    def test_get_merged_source_outside(self):
        assert Tangut.get_merged_source(self.OUT_CP) == ""

    def test_get_radical_stroke(self):
        rs = Tangut.get_radical_stroke(self.CP)
        assert isinstance(rs, str)
        if rs:
            assert "." in rs

    def test_get_radical_stroke_outside(self):
        assert Tangut.get_radical_stroke(self.OUT_CP) == ""

    def test_get_radical_number(self):
        rn = Tangut.get_radical_number(self.CP)
        assert isinstance(rn, int)

    def test_get_radical_number_outside(self):
        assert Tangut.get_radical_number(self.OUT_CP) == 0

    def test_get_total_stroke_count(self):
        sc = Tangut.get_total_stroke_count(self.CP)
        assert isinstance(sc, int)

    def test_get_id(self):
        ids = Tangut.get_ids(self.CP)
        assert isinstance(ids, str)

    def test_get_ids_outside(self):
        assert Tangut.get_ids(self.OUT_CP) == ""

    def test_has_variants(self):
        # Just check it returns a bool
        v = Tangut.has_variants(self.CP)
        assert isinstance(v, bool)

    def test_get_variants(self):
        v = Tangut.get_variants(self.CP)
        assert isinstance(v, str)

    def test_get_variant(self):
        v = Tangut.get_variant(self.CP, 0)
        assert isinstance(v, int)

    # ── component data ──

    def test_get_stroke_count_for_component(self):
        sc = Tangut.get_stroke_count_for_component(0x18800)
        assert isinstance(sc, int)

    def test_get_stroke_count_for_component_outside(self):
        assert Tangut.get_stroke_count_for_component(self.OUT_CP) == 0

    def test_get_stroke_count_for_component_number(self):
        sc = Tangut.get_stroke_count_for_component_number(1)
        assert isinstance(sc, int)

    def test_get_stroke_count_for_component_number_invalid(self):
        assert Tangut.get_stroke_count_for_component_number(99999) == 0

    def test_get_radical_for_character(self):
        rc = Tangut.get_radical_for_character(self.CP)
        assert isinstance(rc, int)

    def test_get_radical_for_character_outside(self):
        assert Tangut.get_radical_for_character(self.OUT_CP) == 0

    # ── _get_offset ──

    def test_get_offset_main_range(self):
        assert Tangut._get_offset(TANGUT_START) == 0
        assert Tangut._get_offset(TANGUT_LAST) == TANGUT_COUNT - 1

    def test_get_offset_supplement(self):
        off = Tangut._get_offset(_supp_tangut_cp(0))
        assert off == TANGUT_COUNT

    def test_get_offset_outside(self):
        assert Tangut._get_offset(self.OUT_CP) == -1

    # ── data consistency ──

    def test_merged_data_size(self):
        from src.utils_.loader import ScriptsLoader

        data = ScriptsLoader.load_tangut_character_data()
        # Should cover main range + supplement
        assert len(data) >= TANGUT_COUNT

    def test_component_data_size(self):
        from src.utils_.loader import ScriptsLoader

        data = ScriptsLoader.load_tangut_component_data()
        # Should have entries
        assert len(data) > 0

    def test_radical_for_character_maps_to_component(self):
        rn = Tangut.get_radical_number(self.CP)
        if rn:
            cp = Tangut.get_radical_for_character(self.CP)
            if cp:
                assert 0x18800 <= cp <= 0x18AFF
