"""Focused regression tests for the Extended Wylie Tibetan port."""

from babelsoft.languages.tibetan import Tibetan


def codepoints(text: str) -> list[int]:
    return [ord(character) for character in text]


def convert(text: str, *, start: int = 0, end: int | None = None) -> tuple[str, int]:
    return Tibetan().do_conversion(0, text, start, end)


def test_reference_tables_include_full_cpp_mappings() -> None:
    assert len(Tibetan.TABLE_INITIALS) == 584
    assert len(Tibetan.TABLE_SUBJOINS) == 38
    assert len(Tibetan.TABLE_MEDIALS) == 17
    assert len(Tibetan.TABLE_FINALS) == 32
    assert len(Tibetan.TABLE_PUNCTUATION) == 25
    assert ("brgy", 0x92, 0x24, 0x02) in Tibetan.TABLE_INITIALS


def test_simple_and_compound_initials_use_cpp_mappings() -> None:
    converted, _ = convert("ka")
    assert codepoints(converted) == [0x0F40]

    converted, _ = convert("brgyad")
    assert codepoints(converted) == [0x0F56, 0x0F62, 0x0F92, 0x0FB1, 0x0F51]


def test_subjoined_letters_and_long_vowels() -> None:
    converted, _ = convert("k+yI")
    assert codepoints(converted) == [0x0F40, 0x0FB1, 0x0F71, 0x0F72]

    converted, _ = convert("k+y+r+w")
    assert codepoints(converted) == [0x0F40, 0x0FB1, 0x0FB2, 0x0FAD]


def test_final_sequences_and_nga_shad_punctuation() -> None:
    converted, count = convert("sngags")
    assert codepoints(converted) == [0x0F66, 0x0F94, 0x0F42, 0x0F66]
    assert count == 0

    converted, count = convert("nga/")
    assert codepoints(converted) == [0x0F44, 0x0F0C, 0x0F0D]
    assert count == 1


def test_punctuation_multicharacters_no_tsheg_and_counts() -> None:
    converted, _ = convert("ka.ka")
    assert codepoints(converted) == [0x0F40, 0x0F40]

    converted, _ = convert("//")
    assert codepoints(converted) == [0x0F0E]

    converted, _ = convert("~X")
    assert codepoints(converted) == [0x0F35]

    converted, _ = convert("ka ")
    assert codepoints(converted) == [0x0F40, 0x0F0B]


def test_forced_prefix_brackets_and_tsa_phru() -> None:
    converted, _ = convert("g.a")
    assert codepoints(converted) == [0x0F42, 0x0F68]

    converted, _ = convert("[abc]")
    assert converted == "abc"

    converted, _ = convert("^")
    assert codepoints(converted) == [0x0F68, 0x0F39]

    converted, _ = convert("k^")
    assert codepoints(converted) == [0x0F40, 0x0F39]


def test_conversion_respects_input_range() -> None:
    converted, _ = convert("xkaya", start=1, end=3)
    assert codepoints(converted) == [0x0F40]
