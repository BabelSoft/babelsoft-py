"""Focused completeness tests for the Yi data port from LanguageYi.cpp."""

from babelsoft.languages.yi import (
    RADICAL_FIRST,
    SYLLABLE_COUNT,
    SYLLABLE_FIRST,
    Yi,
)


def test_cpp_reference_tables_are_complete():
    assert len(Yi.TABLE_YI_SYLLABLES) == 1165 == SYLLABLE_COUNT
    assert len(Yi.TABLE_YI_INDEX) == 46
    assert Yi.TABLE_YI_INDEX[0] == SYLLABLE_FIRST
    assert Yi.TABLE_YI_INDEX[-1] == SYLLABLE_FIRST + SYLLABLE_COUNT
    assert len(Yi.TABLE_YI_LATIN_INITIALS) == len(Yi.TABLE_YI_IPA_INITIALS) == 45
    assert len(Yi.TABLE_YI_LATIN_MEDIALS) == len(Yi.TABLE_YI_IPA_MEDIALS) == 11
    assert len(Yi.TABLE_YI_LATIN_FINALS) == len(Yi.TABLE_YI_IPA_FINALS) == 5
    assert len(Yi.RADICAL_NAMES) == 55


def test_syllable_names_ipa_tones_and_conversion_match_cpp_samples():
    assert Yi.get_character_name(0xA000) == "it"
    assert Yi.get_ipa(0xA000) == "i\u2075\u2075"
    assert Yi.get_tone(0xA000) == 1

    assert Yi.get_character_name(0xA016) == "bit"
    assert Yi.get_character_name(0xA48C) == "yyr"
    assert Yi.get_ipa(0xA48C)

    yi = Yi()
    assert yi.do_conversion(0, chr(0xA000) + chr(0xA016)) == ("itbit", 2)
    assert yi.do_conversion(1, chr(0xA000)) == ("i\u2075\u2075", 1)
    assert yi.do_conversion(2, "bit") == (chr(0xA016), 1)


def test_radical_names_use_cpp_transcriptions_and_append_space():
    assert Yi.get_character_name(RADICAL_FIRST) == "qot"
    assert Yi.get_character_name(RADICAL_FIRST, add_space=True) == "qot "


def test_all_reference_syllables_have_names_and_tone_values():
    for code_point in range(SYLLABLE_FIRST, SYLLABLE_FIRST + SYLLABLE_COUNT):
        assert Yi.get_character_name(code_point), f"missing name for U+{code_point:04X}"
        assert isinstance(Yi.get_ipa(code_point), str)
        assert 0 <= Yi.get_tone(code_point) <= 4
