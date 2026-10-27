"""Regression tests for the bundled UCA and locale tailoring data."""

import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent
sys.path.append(str(LIB_DIR))

from babelsoft.unicode.uca import UCA, Locale, SortOptions, SortType, VariableWeighting


def _uca(**options: object) -> UCA:
    return UCA(SortOptions(**options))


def test_canonical_equivalents_have_equal_keys():
    composed = _uca()
    decomposed = _uca()
    composed.set_string("\u00e9")
    decomposed.set_string("e\u0301")
    assert composed.compare(decomposed) == 0


def test_spanish_ch_is_a_contraction():
    standard = _uca()
    spanish = _uca(locale=Locale.SPANISH)
    for sorter in (standard, spanish):
        ch = _uca(locale=sorter._so.locale)
        cz = _uca(locale=sorter._so.locale)
        ch.set_string("ch")
        cz.set_string("cz")
        if sorter._so.locale == Locale.SPANISH:
            assert ch.compare(cz) > 0
        else:
            assert ch.compare(cz) < 0


def test_cldr_uses_its_own_primary_weights():
    ducet = _uca(sort_type=SortType.UCA)
    cldr = _uca(sort_type=SortType.CLDR)
    ducet.set_string("a")
    cldr.set_string("a")
    assert ducet.get_sort_key() != cldr.get_sort_key()


def test_shifted_variable_weighting_uses_a_fourth_level():
    sorter = _uca(variable_weighting=VariableWeighting.SHIFTED)
    sorter.set_string("a-b")
    assert sorter._collation_levels == 4
    assert sorter._sort_key.count(0) == 4


def test_implicit_cjk_characters_have_sort_keys():
    for character in ("\u4e00", "\U00020000"):
        sorter = _uca()
        sorter.set_string(character)
        assert sorter.get_sort_key_bytes()


def test_tibetan_locale_uses_tibetan_collation():
    tibetan = _uca(locale=Locale.TIBETAN)
    tibetan.set_string("\u0f40")
    assert tibetan.get_sort_key_bytes()
