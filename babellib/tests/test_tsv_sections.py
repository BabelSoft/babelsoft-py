"""Tests for the block-based TSV reader used by the collation/transliteration tables."""

import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent
sys.path.append(str(LIB_DIR))

from babelsoft.utils_.parser import TsvParser


def test_get_sections_splits_blocks(tmp_path: Path) -> None:
    path = tmp_path / "tables.tsv"
    path.write_text(
        "# file header\n"
        "\n"
        "[first]\n"
        "# a\tb\n"
        "U+0000\t0x0000\n"
        "\n"
        "[second]\n"
        "# a\tb\tc\n"
        "x\ty\tz\n",
        encoding="utf-8",
    )

    sections = TsvParser.get_sections(path)

    assert list(sections) == ["first", "second"]
    assert sections["first"] == [["U+0000", "0x0000"]]
    assert sections["second"] == [["x", "y", "z"]]


def test_get_sections_keeps_empty_and_space_fields(tmp_path: Path) -> None:
    path = tmp_path / "tables.tsv"
    path.write_text(
        "[keys]\n"
        '# wylie\tvalue\n""\tU+0F68\n" "\tU+0F0B\n"#"\tU+0F05\n',
        encoding="utf-8",
    )

    assert TsvParser.get_sections(path)["keys"] == [['""', "U+0F68"], ['" "', "U+0F0B"], ['"#"', "U+0F05"]]


def test_get_sections_rejects_rows_outside_a_block(tmp_path: Path) -> None:
    path = tmp_path / "tables.tsv"
    path.write_text("stray\trow\n[block]\n# a\nb\n", encoding="utf-8")

    with pytest.raises(ValueError, match="outside a \\[section\\]"):
        TsvParser.get_sections(path)


def test_get_tsv_still_strips_plain_tables(tmp_path: Path) -> None:
    path = tmp_path / "plain.tsv"
    path.write_text("# header\n\n  U+A000\t13.2  \n", encoding="utf-8")

    assert TsvParser.get_tsv(path) == [["U+A000", "13.2"]]
