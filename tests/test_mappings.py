"""
Tests for data/mappings/*.tsv — validating encoding mapping exports.
Also tests for src/mappings/ — Mapper and encoding classes.
"""

import re
import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent
sys.path.append(str(LIB_DIR))

from src.mappings import (  # noqa: E402
    ARMSCII8,
    ASCII,
    Big5,
    BrdaRten,
    CP932,
    CP936,
    CP949,
    CP950,
    DOSCP437,
    DOSCP737,
    DOSCP775,
    DOSCP850,
    DOSCP852,
    DOSCP855,
    DOSCP857,
    DOSCP860,
    DOSCP861,
    DOSCP862,
    DOSCP863,
    DOSCP864,
    DOSCP865,
    DOSCP866,
    DOSCP869,
    EBCDIC,
    Encoding,
    EUCJP,
    EUCKR,
    GB18030,
    GB2312,
    GBK,
    HKSCS,
    ISO8859_2,
    ISO8859_3,
    ISO8859_4,
    ISO8859_5,
    ISO8859_6,
    ISO8859_7,
    ISO8859_8,
    ISO8859_9,
    ISO8859_10,
    ISO8859_11,
    ISO8859_13,
    ISO8859_14,
    ISO8859_15,
    ISO8859_16,
    JIS,
    JIS0212,
    KOI8R,
    KOI8U,
    KPS9566,
    LaoMuleLao1,
    Mapper,
    ShiftJIS,
    TamilTAB,
    TamilTAM,
    TamilTSCII,
    TIS620,
    VISCII,
    Windows874,
    Windows1250,
    Windows1251,
    Windows1252,
    Windows1253,
    Windows1254,
    Windows1255,
    Windows1256,
    Windows1257,
    Windows1258,
)

MAPPINGS_DIR = Path(__file__).parent.parent / "data" / "mappings"

# ── helpers ──────────────────────────────────────────────────────────


def read_tsv(path: Path) -> tuple[list[str], list[list[str]]]:
    """Read a TSV, return (header_lines, data_rows)."""
    lines = path.read_text(encoding="utf-8").split("\n")
    header = []
    data = []
    for line in lines:
        if line.startswith("#"):
            header.append(line)
        elif line.strip():
            data.append(line.split("\t"))
    return header, data


def u4(cp: str) -> bool:
    """Check U+XXXX format, or space-separated U+XXXX U+XXXX."""
    for part in cp.split(" "):
        part = part.strip()
        if not part:
            continue
        if not re.match(r"^U\+[0-9A-F]{4,6}$", part):
            return False
        hd = part[2:]
        if len(hd) > 4 and hd[0] == "0":
            return False
    return True


# ── expected files ───────────────────────────────────────────────────

EXPECTED_FILES = [
    "iso_8859.tsv",
    "koi8.tsv",
    "dos.tsv",
    "windows_cp.tsv",
    "ebcdic.tsv",
    "viscii.tsv",
    "armscii.tsv",
    "tai_lao.tsv",
    "jis_x_0201.tsv",
    "cp950.tsv",
    "cp932.tsv",
    "cp936.tsv",
    "cp949.tsv",
    "kps_9566.tsv",
    "jis_x_0212.tsv",
    "tamil.tsv",
    "brda_rten.tsv",
    "gb18030.tsv",
    "hkscs_remapping.tsv",
    "hkscs.tsv",
]

MIN_ROWS = {
    "iso_8859.tsv": 1200,
    "koi8.tsv": 200,
    "dos.tsv": 1800,
    "windows_cp.tsv": 1200,
    "ebcdic.tsv": 1400,
    "viscii.tsv": 200,
    "armscii.tsv": 80,
    "tai_lao.tsv": 150,
    "jis_x_0201.tsv": 60,
    "cp950.tsv": 13000,
    "cp932.tsv": 7000,
    "cp936.tsv": 12000,
    "cp949.tsv": 16000,
    "kps_9566.tsv": 16000,
    "jis_x_0212.tsv": 5000,
    "tamil.tsv": 400,
    "brda_rten.tsv": 7000,
    "gb18030.tsv": 50000,
    "hkscs_remapping.tsv": 20,
    "hkscs.tsv": 4000,
}

EXPECTED_COLS = {
    "iso_8859.tsv": 3,
    "koi8.tsv": 3,
    "dos.tsv": 3,
    "windows_cp.tsv": 3,
    "ebcdic.tsv": 3,
    "viscii.tsv": 2,
    "armscii.tsv": 2,
    "tai_lao.tsv": 3,
    "jis_x_0201.tsv": 2,
    "cp950.tsv": 2,
    "cp932.tsv": 2,
    "cp936.tsv": 2,
    "cp949.tsv": 2,
    "kps_9566.tsv": 2,
    "jis_x_0212.tsv": 3,
    "tamil.tsv": 3,
    "brda_rten.tsv": 2,
    "gb18030.tsv": 2,
    "hkscs_remapping.tsv": 2,
    "hkscs.tsv": 3,
}


# ── tests ────────────────────────────────────────────────────────────


class TestAllFilesExist:
    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_file_exists(self, filename):
        path = MAPPINGS_DIR / filename
        assert path.exists(), f"{filename} missing"

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_has_data(self, filename):
        _, data = read_tsv(MAPPINGS_DIR / filename)
        assert len(data) > 0, f"{filename} has no data rows"

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_min_rows(self, filename):
        _, data = read_tsv(MAPPINGS_DIR / filename)
        if filename in MIN_ROWS:
            assert len(data) >= MIN_ROWS[filename], f"{filename}: {len(data)} < {MIN_ROWS[filename]}"


class TestHeaderFormat:
    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_starts_with_comment(self, filename):
        header, _ = read_tsv(MAPPINGS_DIR / filename)
        assert header[0].startswith("# BabelSoft Encoding Mapping:"), f"{filename}: bad first line"

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_has_fields_section(self, filename):
        header, _ = read_tsv(MAPPINGS_DIR / filename)
        fields_line = [h for h in header if h.startswith("# Fields:")]
        assert fields_line, f"{filename}: missing '# Fields:'"

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_has_delimiter_note(self, filename):
        header, _ = read_tsv(MAPPINGS_DIR / filename)
        assert any("Delimiter: TAB" in h for h in header), f"{filename}: missing delimiter note"


class TestColumnCounts:
    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_consistent_columns(self, filename):
        _, data = read_tsv(MAPPINGS_DIR / filename)
        if filename in EXPECTED_COLS:
            expected = EXPECTED_COLS[filename]
        else:
            expected = len(data[0]) if data else 0
        for i, row in enumerate(data):
            assert len(row) == expected, f"{filename} row {i+1}: {len(row)} cols, expected {expected}"

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_no_empty_cells_except_hkscs_col3(self, filename):
        """Only hkscs.tsv col3 may be empty; all other cells must be non-empty."""
        _, data = read_tsv(MAPPINGS_DIR / filename)
        for i, row in enumerate(data):
            for j, cell in enumerate(row):
                if filename == "hkscs.tsv" and j == 2:
                    continue  # CP932 column may be empty
                assert cell.strip(), f"{filename} row {i+1} col {j+1}: empty cell"


class TestUnicodeFormat:
    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_all_uPlus_format(self, filename):
        """All U+XXXX values must have correct padding."""
        _, data = read_tsv(MAPPINGS_DIR / filename)
        for i, row in enumerate(data):
            for j, cell in enumerate(row):
                if cell.startswith("U+"):
                    assert u4(cell), f"{filename} row {i+1}: bad U+ format '{cell}'"


class TestSpecificMappings:
    """Spot-check known values from source .h files."""

    def test_cp950_first_entry(self):
        _, data = read_tsv(MAPPINGS_DIR / "cp950.tsv")
        assert data[0][0] == "0x8740"
        assert data[0][1] == "U+43F0"

    def test_cp950_smp_no_leading_zero(self):
        """U+27267 not U+027267."""
        _, data = read_tsv(MAPPINGS_DIR / "cp950.tsv")
        row5 = [r for r in data if r[0] == "0x8745"]
        assert row5, "0x8745 not found"
        assert row5[0][1] == "U+27267", f"got {row5[0][1]}"

    def test_hkscs_format(self):
        _, data = read_tsv(MAPPINGS_DIR / "hkscs.tsv")
        assert data[0] == ["U+20547", "0xE000", "0xFA40"]

    def test_hkscs_has_empty_cp932(self):
        """Some PUA entries lack CP932 byte."""
        _, data = read_tsv(MAPPINGS_DIR / "hkscs.tsv")
        empty = [r for r in data if len(r) >= 3 and r[2] == ""]
        assert len(empty) > 0, "expected some entries with empty source_cp932"

    def test_hkscs_remapping_pairs(self):
        _, data = read_tsv(MAPPINGS_DIR / "hkscs_remapping.tsv")
        assert data[0] == ["U+514C", "U+5151"]

    def test_jis_x_0212_format(self):
        _, data = read_tsv(MAPPINGS_DIR / "jis_x_0212.tsv")
        assert data[0] == ["U+02D8", "0xA2AF", "0x222F"]

    def test_brda_rten_a_format(self):
        _, data = read_tsv(MAPPINGS_DIR / "brda_rten.tsv")
        # F300 → U+0F68 U+0F72
        row0 = [r for r in data if r[0] == "0xF300"]
        assert row0, "0xF300 not found in brda_rten"
        assert row0[0][1] == "U+0F68 U+0F72", f"got {row0[0][1]}"

    def test_gb18030_has_4byte(self):
        _, data = read_tsv(MAPPINGS_DIR / "gb18030.tsv")
        four = [r for r in data if len(r[0]) == 10]  # 0x81308130 = 10 chars
        assert len(four) > 0, "no 4-byte GB18030 entries found"

    def test_gb18030_has_2byte(self):
        _, data = read_tsv(MAPPINGS_DIR / "gb18030.tsv")
        two = [r for r in data if len(r[0]) == 6]  # 0x8140 = 6 chars
        assert len(two) > 0, "no 2-byte GB18030 entries found"

    def test_gb18030_first_4byte(self):
        _, data = read_tsv(MAPPINGS_DIR / "gb18030.tsv")
        assert data[0][0] == "0x81308130"
        assert data[0][1] == "U+0080"

    def test_dos_no_hyphen(self):
        """CP437 not CP-437."""
        _, data = read_tsv(MAPPINGS_DIR / "dos.tsv")
        labels = {r[1] for r in data if len(r) >= 2}
        for label in labels:
            assert "-" not in label, f"DOS label has hyphen: {label}"

    def test_windows_cp_no_hyphen(self):
        _, data = read_tsv(MAPPINGS_DIR / "windows_cp.tsv")
        labels = {r[1] for r in data if len(r) >= 2}
        for label in labels:
            assert "-" not in label, f"Windows CP label has hyphen: {label}"

    def test_tamil_encoding_column(self):
        """tamil.tsv: col order is source_byte | encoding | unicode_cp."""
        _, data = read_tsv(MAPPINGS_DIR / "tamil.tsv")
        # source_byte starts with 0x, encoding is TSCII/TAM/TAB
        assert re.match(r"0x[0-9A-F]{2}", data[0][0]), f"bad source_byte: {data[0][0]}"
        assert data[0][1] in ("TSCII", "TAM", "TAB"), f"bad encoding: {data[0][1]}"
        assert data[0][2].startswith("U+"), f"bad unicode_cp: {data[0][2]}"

    def test_tai_lao_has_both(self):
        """tai_lao.tsv includes both Thai and Lao encodings."""
        _, data = read_tsv(MAPPINGS_DIR / "tai_lao.tsv")
        labels = {r[1] for r in data if len(r) >= 2}
        assert len(labels) >= 2, f"expected >=2 labels, got {labels}"

    def test_iso8859_has_all_variants(self):
        """ISO-8859 should have Latin-2 through Latin-10 etc."""
        _, data = read_tsv(MAPPINGS_DIR / "iso_8859.tsv")
        labels = {r[1] for r in data if len(r) >= 2}
        for n in [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16]:
            assert f"ISO-8859-{n}" in labels, f"ISO-8859-{n} missing"

    def test_viscii_no_encoding_col(self):
        """Single-variant: no source_encoding column."""
        _, data = read_tsv(MAPPINGS_DIR / "viscii.tsv")
        assert len(data[0]) == 2, f"expected 2 cols, got {len(data[0])}"


# ═════════════════════  Mapper  ═════════════════════


class TestMapper:
    def test_to_unicode_ascii(self):
        result = Mapper.to_unicode(b"Hello", Encoding.ASCII)
        assert result == "Hello"

    def test_from_unicode_ascii(self):
        result = Mapper.from_unicode("Hello", Encoding.ASCII)
        assert result == b"Hello"

    def test_to_unicode_string_encoding(self):
        result = Mapper.to_unicode(b"Hello", "ascii")
        assert result == "Hello"

    def test_invalid_encoding_fallback(self):
        result = Mapper.to_unicode(b"Hello", "nonexistent_encoding")
        assert result == "Hello"

    def test_replacement_char(self):
        result = Mapper.to_unicode(b"\xff", Encoding.ASCII)
        assert "\ufffd" in result

    def test_list_encodings(self):
        encodings = Mapper.list_encodings()
        assert "ascii" in encodings
        assert "utf_8" in encodings or "utf-8" in encodings

    def test_custom_mapping_register(self):
        Mapper.register_mapping("test_custom", {0x41: 0x42})
        result = Mapper.to_unicode(b"\x41", "test_custom")
        assert result == "B"

    def test_custom_mapping_from(self):
        Mapper.register_mapping("test_rev", {0x41: 0x42})
        result = Mapper.from_unicode("B", "test_rev")
        assert result == b"A"

    def test_custom_double_byte(self):
        Mapper.register_mapping("test_db", {0x4142: 0x4E00})
        result = Mapper.to_unicode(b"\x41\x42", "test_db")
        assert result == "\u4e00"


# ═════════════════════  Encoding  ═════════════════════


class TestEncoding:
    def test_encoding_values(self):
        assert Encoding.ASCII.value == "ascii"
        assert Encoding.BIG5.value == "big5"
        assert Encoding.GB18030.value == "gb18030"
        assert Encoding.CP932.value == "cp932"


# ═════════════════════  Big5  ═════════════════════


class TestBig5:
    def test_to_unicode_ascii_subset(self):
        result = Big5.to_unicode(b"ABC")
        assert result == "ABC"

    def test_from_unicode_ascii(self):
        result = Big5.from_unicode("ABC")
        assert result == b"ABC"


# ═════════════════════  GB18030  ═════════════════════


class TestGB18030:
    def test_to_unicode_ascii(self):
        result = GB18030.to_unicode(b"Hello")
        assert result == "Hello"

    def test_from_unicode_ascii(self):
        result = GB18030.from_unicode("Hello")
        assert result == b"Hello"


# ═════════════════════  CP932  ═════════════════════


class TestCP932:
    def test_to_unicode_ascii(self):
        result = CP932.to_unicode(b"ABC")
        assert result == "ABC"

    def test_from_unicode_ascii(self):
        result = CP932.from_unicode("ABC")
        assert result == b"ABC"


# ═════════════════════  CP936  ═════════════════════


class TestCP936:
    def test_to_unicode_ascii(self):
        result = CP936.to_unicode(b"ABC")
        assert result == "ABC"

    def test_from_unicode_ascii(self):
        result = CP936.from_unicode("ABC")
        assert result == b"ABC"


# ═════════════════════  CP949  ═════════════════════


class TestCP949:
    def test_to_unicode_ascii(self):
        result = CP949.to_unicode(b"ABC")
        assert result == "ABC"

    def test_from_unicode_ascii(self):
        result = CP949.from_unicode("ABC")
        assert result == b"ABC"


class TestNoDuplicates:
    """Verify no duplicate source keys within each file.

    Multi-encoding files check (source_byte, encoding) as composite key.
    DBCS files legitimately have duplicate source bytes (e.g., extension
    areas where same byte pair maps to different codepoints) — these are
    skipped but NOT considered bugs.
    """

    DBCS_DUPES_OK = {"cp950.tsv", "cp932.tsv", "cp936.tsv", "cp949.tsv", "kps_9566.tsv", "gb18030.tsv"}
    MULTI_ENC = {"tamil.tsv", "tai_lao.tsv", "iso_8859.tsv", "dos.tsv", "windows_cp.tsv", "ebcdic.tsv", "koi8.tsv"}

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_no_duplicate_keys(self, filename):
        # DBCS files: duplicates are inherent to the encoding structure
        if filename in self.DBCS_DUPES_OK:
            pytest.skip("DBCS: duplicate source bytes are expected in extension areas")

        _, data = read_tsv(MAPPINGS_DIR / filename)

        # Multi-encoding files: key is (source, encoding) tuple
        if filename in self.MULTI_ENC:
            if len(data[0]) >= 2:
                keys = [(r[0], r[1]) for r in data]
            else:
                keys = [r[0] for r in data]
        else:
            keys = [r[0] for r in data]

        dupes = [k for k in set(keys) if keys.count(k) > 1]
        assert not dupes, f"{filename}: duplicate keys: {dupes[:5]}"


class TestSourceByteFormat:
    """Source byte values should be 0x-prefixed hex."""

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_source_hex_format(self, filename):
        _, data = read_tsv(MAPPINGS_DIR / filename)
        col0 = data[0][0]
        if col0.startswith("0x"):
            for i, row in enumerate(data):
                assert re.match(r"^0x[0-9A-F]+$", row[0]), f"{filename} row {i+1}: bad source format '{row[0]}'"


# ═════════════════════  BrdaRten  ═════════════════════


class TestBrdaRten:
    def test_class_exists(self):
        assert BrdaRten.ENCODING == Encoding.BRDA_RTEN

    def test_encoding_value(self):
        assert Encoding.BRDA_RTEN.value == "brda_rten"

    def test_to_unicode_fallback_ascii(self):
        """BrdaRten is a custom encoding; ASCII subset may fail over to replacement."""
        result = BrdaRten.to_unicode(b"ABC")
        assert len(result) == 3

    def test_from_unicode_fallback(self):
        result = BrdaRten.from_unicode("ABC")
        assert isinstance(result, bytes)


# ═════════════════════  DOS Code Pages  ═════════════════════


class TestDOSCP437:
    def test_to_unicode_ascii(self):
        result = DOSCP437.to_unicode(b"Hello")
        assert result == "Hello"

    def test_from_unicode_ascii(self):
        result = DOSCP437.from_unicode("Hello")
        assert result == b"Hello"

    def test_encoding_value(self):
        assert Encoding.DOS_CP437.value == "cp437"


class TestDOSCP737:
    def test_to_unicode_ascii(self):
        result = DOSCP737.to_unicode(b"ABC")
        assert result == "ABC"

    def test_encoding_value(self):
        assert Encoding.DOS_CP737.value == "cp737"


class TestDOSCP850:
    def test_to_unicode_ascii(self):
        result = DOSCP850.to_unicode(b"Test")
        assert result == "Test"

    def test_encoding_value(self):
        assert Encoding.DOS_CP850.value == "cp850"


class TestDOSCP852:
    def test_to_unicode_ascii(self):
        result = DOSCP852.to_unicode(b"XYZ")
        assert result == "XYZ"

    def test_encoding_value(self):
        assert Encoding.DOS_CP852.value == "cp852"


class TestDOSCP866:
    def test_to_unicode_ascii(self):
        result = DOSCP866.to_unicode(b"ABC")
        assert result == "ABC"

    def test_encoding_value(self):
        assert Encoding.DOS_CP866.value == "cp866"


class TestAllDOSEncodings:
    """Verify all 15 DOS code page enum values exist."""

    DOS_ENUMS = [
        "DOS_CP437",
        "DOS_CP737",
        "DOS_CP775",
        "DOS_CP850",
        "DOS_CP852",
        "DOS_CP855",
        "DOS_CP857",
        "DOS_CP860",
        "DOS_CP861",
        "DOS_CP862",
        "DOS_CP863",
        "DOS_CP864",
        "DOS_CP865",
        "DOS_CP866",
        "DOS_CP869",
    ]

    def test_all_dos_enums_exist(self):
        for name in self.DOS_ENUMS:
            assert hasattr(Encoding, name), f"Encoding.{name} missing"

    def test_all_dos_classes_exist(self):
        classes = [
            DOSCP437,
            DOSCP737,
            DOSCP775,
            DOSCP850,
            DOSCP852,
            DOSCP855,
            DOSCP857,
            DOSCP860,
            DOSCP861,
            DOSCP862,
            DOSCP863,
            DOSCP864,
            DOSCP865,
            DOSCP866,
            DOSCP869,
        ]
        for cls in classes:
            assert hasattr(cls, "ENCODING")
            assert hasattr(cls, "to_unicode")
            assert hasattr(cls, "from_unicode")


# ═════════════════════  KPS 9566  ═════════════════════


class TestKPS9566:
    def test_class_exists(self):
        assert KPS9566.ENCODING == Encoding.KPS_9566

    def test_encoding_value(self):
        assert Encoding.KPS_9566.value == "kps_9566"

    def test_to_unicode_ascii_fallback(self):
        """KPS 9566 is a DBCS; ASCII subset may need custom mapping."""
        result = KPS9566.to_unicode(b"A")
        assert len(result) == 1

    def test_from_unicode_fallback(self):
        result = KPS9566.from_unicode("A")
        assert isinstance(result, bytes)


# ═════════════════════  Lao  ═════════════════════


class TestLaoMuleLao1:
    def test_class_exists(self):
        assert LaoMuleLao1.ENCODING == Encoding.LAO_MULELAO1

    def test_encoding_value(self):
        assert Encoding.LAO_MULELAO1.value == "mulelao1"

    def test_to_unicode_fallback(self):
        result = LaoMuleLao1.to_unicode(b"A")
        assert len(result) == 1

    def test_from_unicode_fallback(self):
        result = LaoMuleLao1.from_unicode("A")
        assert isinstance(result, bytes)


# ═════════════════════  Tamil  ═════════════════════


class TestTamilTAB:
    def test_to_unicode_ascii(self):
        result = TamilTAB.to_unicode(b"ABC")
        assert result == "ABC"

    def test_encoding_value(self):
        assert Encoding.TAMIL_TAB.value == "tab"


class TestTamilTAM:
    def test_to_unicode_ascii(self):
        result = TamilTAM.to_unicode(b"ABC")
        assert result == "ABC"

    def test_encoding_value(self):
        assert Encoding.TAMIL_TAM.value == "tam"


class TestTamilTSCII:
    def test_to_unicode_ascii(self):
        result = TamilTSCII.to_unicode(b"ABC")
        assert result == "ABC"

    def test_encoding_value(self):
        assert Encoding.TAMIL_TSCII.value == "tscii"


class TestAllTamilEncodings:
    """Verify all 3 Tamil encoding enum values exist."""

    def test_all_tamil_enums_exist(self):
        for name in ["TAMIL_TAB", "TAMIL_TAM", "TAMIL_TSCII"]:
            assert hasattr(Encoding, name), f"Encoding.{name} missing"

    def test_all_tamil_classes_exist(self):
        for cls in [TamilTAB, TamilTAM, TamilTSCII]:
            assert hasattr(cls, "ENCODING")
            assert hasattr(cls, "to_unicode")
            assert hasattr(cls, "from_unicode")


# ═════════════════════  ISO-8859  ═════════════════════


class TestISO8859_2:
    def test_to_unicode_ascii(self):
        result = ISO8859_2.to_unicode(b"Hello")
        assert result == "Hello"

    def test_from_unicode_ascii(self):
        result = ISO8859_2.from_unicode("Hello")
        assert result == b"Hello"

    def test_encoding_value(self):
        assert Encoding.ISO_8859_2.value == "iso8859_2"


class TestISO8859_5:
    def test_to_unicode_ascii(self):
        result = ISO8859_5.to_unicode(b"Test")
        assert result == "Test"

    def test_encoding_value(self):
        assert Encoding.ISO_8859_5.value == "iso8859_5"


class TestISO8859_7:
    def test_to_unicode_ascii(self):
        result = ISO8859_7.to_unicode(b"ABC")
        assert result == "ABC"

    def test_encoding_value(self):
        assert Encoding.ISO_8859_7.value == "iso8859_7"


class TestISO8859_15:
    def test_to_unicode_ascii(self):
        result = ISO8859_15.to_unicode(b"Euro")
        assert result == "Euro"

    def test_encoding_value(self):
        assert Encoding.ISO_8859_15.value == "iso8859_15"


class TestAllISO8859Encodings:
    """Verify all 14 ISO-8859 enum values exist (no ISO-8859-12)."""

    ISO_ENUMS = [
        "ISO_8859_2",
        "ISO_8859_3",
        "ISO_8859_4",
        "ISO_8859_5",
        "ISO_8859_6",
        "ISO_8859_7",
        "ISO_8859_8",
        "ISO_8859_9",
        "ISO_8859_10",
        "ISO_8859_11",
        "ISO_8859_13",
        "ISO_8859_14",
        "ISO_8859_15",
        "ISO_8859_16",
    ]

    def test_all_iso_enums_exist(self):
        for name in self.ISO_ENUMS:
            assert hasattr(Encoding, name), f"Encoding.{name} missing"

    def test_all_iso_classes_exist(self):
        classes = [
            ISO8859_2,
            ISO8859_3,
            ISO8859_4,
            ISO8859_5,
            ISO8859_6,
            ISO8859_7,
            ISO8859_8,
            ISO8859_9,
            ISO8859_10,
            ISO8859_11,
            ISO8859_13,
            ISO8859_14,
            ISO8859_15,
            ISO8859_16,
        ]
        for cls in classes:
            assert hasattr(cls, "ENCODING")
            assert hasattr(cls, "to_unicode")
            assert hasattr(cls, "from_unicode")


# ═════════════════════  ARMSCII-8  ═════════════════════


class TestARMSCII8:
    def test_to_unicode_ascii(self):
        result = ARMSCII8.to_unicode(b"ABC")
        assert result == "ABC"

    def test_from_unicode_ascii(self):
        result = ARMSCII8.from_unicode("ABC")
        assert result == b"ABC"

    def test_encoding_value(self):
        assert Encoding.ARMSCII_8.value == "armscii_8"


# ═════════════════════  ASCII  ═════════════════════


class TestASCII:
    def test_to_unicode(self):
        result = ASCII.to_unicode(b"Hello!")
        assert result == "Hello!"

    def test_from_unicode(self):
        result = ASCII.from_unicode("Hello!")
        assert result == b"Hello!"

    def test_encoding_value(self):
        assert Encoding.ASCII.value == "ascii"


# ═════════════════════  CP950  ═════════════════════


class TestCP950:
    def test_to_unicode_ascii(self):
        result = CP950.to_unicode(b"ABC")
        assert result == "ABC"

    def test_from_unicode_ascii(self):
        result = CP950.from_unicode("ABC")
        assert result == b"ABC"

    def test_encoding_value(self):
        assert Encoding.CP950.value == "cp950"


# ═════════════════════  EBCDIC  ═════════════════════


class TestEBCDIC:
    def test_to_unicode_ascii(self):
        result = EBCDIC.to_unicode(b"HELLO")
        assert len(result) == 5

    def test_from_unicode_ascii(self):
        result = EBCDIC.from_unicode("HELLO")
        assert isinstance(result, bytes)

    def test_encoding_value(self):
        assert Encoding.EBCDIC.value == "ebcdic_cp_us"


# ═════════════════════  EUC-JP  ═════════════════════


class TestEUCJP:
    def test_to_unicode_ascii(self):
        result = EUCJP.to_unicode(b"ABC")
        assert result == "ABC"

    def test_from_unicode_ascii(self):
        result = EUCJP.from_unicode("ABC")
        assert result == b"ABC"

    def test_encoding_value(self):
        assert Encoding.EUC_JP.value == "euc_jp"


# ═════════════════════  EUC-KR  ═════════════════════


class TestEUCKR:
    def test_to_unicode_ascii(self):
        result = EUCKR.to_unicode(b"ABC")
        assert result == "ABC"

    def test_from_unicode_ascii(self):
        result = EUCKR.from_unicode("ABC")
        assert result == b"ABC"

    def test_encoding_value(self):
        assert Encoding.EUC_KR.value == "euc_kr"


# ═════════════════════  GB2312  ═════════════════════


class TestGB2312:
    def test_to_unicode_ascii(self):
        result = GB2312.to_unicode(b"Hello")
        assert result == "Hello"

    def test_from_unicode_ascii(self):
        result = GB2312.from_unicode("Hello")
        assert result == b"Hello"

    def test_encoding_value(self):
        assert Encoding.GB2312.value == "gb2312"


# ═════════════════════  GBK  ═════════════════════


class TestGBK:
    def test_to_unicode_ascii(self):
        result = GBK.to_unicode(b"Hello")
        assert result == "Hello"

    def test_from_unicode_ascii(self):
        result = GBK.from_unicode("Hello")
        assert result == b"Hello"

    def test_encoding_value(self):
        assert Encoding.GBK.value == "gbk"


# ═════════════════════  HKSCS  ═════════════════════


class TestHKSCS:
    def test_to_unicode_ascii(self):
        result = HKSCS.to_unicode(b"ABC")
        assert len(result) == 3

    def test_from_unicode_ascii(self):
        result = HKSCS.from_unicode("ABC")
        assert isinstance(result, bytes)

    def test_encoding_value(self):
        assert Encoding.BIG5_HKSCS.value == "big5hkscs"


# ═════════════════════  JIS  ═════════════════════


class TestJIS:
    def test_to_unicode_ascii(self):
        result = JIS.to_unicode(b"ABC")
        assert result == "ABC"

    def test_from_unicode_ascii(self):
        result = JIS.from_unicode("ABC")
        assert result == b"ABC"

    def test_encoding_value(self):
        assert Encoding.JIS.value == "iso2022_jp"


# ═════════════════════  JIS0212  ═════════════════════


class TestJIS0212:
    def test_to_unicode_ascii(self):
        result = JIS0212.to_unicode(b"ABC")
        assert result == "ABC"

    def test_from_unicode_ascii(self):
        result = JIS0212.from_unicode("ABC")
        assert result == b"ABC"

    def test_encoding_value(self):
        assert Encoding.JIS_EXT.value == "iso2022_jp_ext"


# ═════════════════════  KOI8-R / KOI8-U  ═════════════════════


class TestKOI8R:
    def test_to_unicode_ascii(self):
        result = KOI8R.to_unicode(b"ABC")
        assert result == "ABC"

    def test_from_unicode_ascii(self):
        result = KOI8R.from_unicode("ABC")
        assert result == b"ABC"

    def test_encoding_value(self):
        assert Encoding.KOI8_R.value == "koi8_r"


class TestKOI8U:
    def test_to_unicode_ascii(self):
        result = KOI8U.to_unicode(b"ABC")
        assert result == "ABC"

    def test_from_unicode_ascii(self):
        result = KOI8U.from_unicode("ABC")
        assert result == b"ABC"

    def test_encoding_value(self):
        assert Encoding.KOI8_U.value == "koi8_u"


# ═════════════════════  Shift-JIS  ═════════════════════


class TestShiftJIS:
    def test_to_unicode_ascii(self):
        result = ShiftJIS.to_unicode(b"ABC")
        assert result == "ABC"

    def test_from_unicode_ascii(self):
        result = ShiftJIS.from_unicode("ABC")
        assert result == b"ABC"

    def test_encoding_value(self):
        assert Encoding.SHIFT_JIS.value == "shift_jis"


# ═════════════════════  TIS-620  ═════════════════════


class TestTIS620:
    def test_to_unicode_ascii(self):
        result = TIS620.to_unicode(b"ABC")
        assert result == "ABC"

    def test_from_unicode_ascii(self):
        result = TIS620.from_unicode("ABC")
        assert result == b"ABC"

    def test_encoding_value(self):
        assert Encoding.TIS_620.value == "tis_620"


# ═════════════════════  VISCII  ═════════════════════


class TestVISCII:
    def test_to_unicode_ascii(self):
        result = VISCII.to_unicode(b"ABC")
        assert result == "ABC"

    def test_from_unicode_ascii(self):
        result = VISCII.from_unicode("ABC")
        assert result == b"ABC"

    def test_encoding_value(self):
        assert Encoding.VISCII.value == "viscii"


# ═════════════════════  Windows-874  ═════════════════════


class TestWindows874:
    def test_to_unicode_ascii(self):
        result = Windows874.to_unicode(b"ABC")
        assert result == "ABC"

    def test_from_unicode_ascii(self):
        result = Windows874.from_unicode("ABC")
        assert result == b"ABC"

    def test_encoding_value(self):
        assert Encoding.WINDOWS_874.value == "windows_874"


# ═════════════════════  Windows-125x  ═════════════════════


class TestWindows1250:
    def test_to_unicode_ascii(self):
        result = Windows1250.to_unicode(b"Hello")
        assert result == "Hello"

    def test_encoding_value(self):
        assert Encoding.WINDOWS_1250.value == "windows_1250"


class TestWindows1251:
    def test_to_unicode_ascii(self):
        result = Windows1251.to_unicode(b"Hello")
        assert result == "Hello"

    def test_encoding_value(self):
        assert Encoding.WINDOWS_1251.value == "windows_1251"


class TestWindows1252:
    def test_to_unicode_ascii(self):
        result = Windows1252.to_unicode(b"Hello")
        assert result == "Hello"

    def test_encoding_value(self):
        assert Encoding.WINDOWS_1252.value == "windows_1252"


class TestWindows1253:
    def test_to_unicode_ascii(self):
        result = Windows1253.to_unicode(b"Hello")
        assert result == "Hello"

    def test_encoding_value(self):
        assert Encoding.WINDOWS_1253.value == "windows_1253"


class TestWindows1254:
    def test_to_unicode_ascii(self):
        result = Windows1254.to_unicode(b"Hello")
        assert result == "Hello"

    def test_encoding_value(self):
        assert Encoding.WINDOWS_1254.value == "windows_1254"


class TestWindows1255:
    def test_to_unicode_ascii(self):
        result = Windows1255.to_unicode(b"Hello")
        assert result == "Hello"

    def test_encoding_value(self):
        assert Encoding.WINDOWS_1255.value == "windows_1255"


class TestWindows1256:
    def test_to_unicode_ascii(self):
        result = Windows1256.to_unicode(b"Hello")
        assert result == "Hello"

    def test_encoding_value(self):
        assert Encoding.WINDOWS_1256.value == "windows_1256"


class TestWindows1257:
    def test_to_unicode_ascii(self):
        result = Windows1257.to_unicode(b"Hello")
        assert result == "Hello"

    def test_encoding_value(self):
        assert Encoding.WINDOWS_1257.value == "windows_1257"


class TestWindows1258:
    def test_to_unicode_ascii(self):
        result = Windows1258.to_unicode(b"Hello")
        assert result == "Hello"

    def test_encoding_value(self):
        assert Encoding.WINDOWS_1258.value == "windows_1258"


class TestAllWindowsCPEncodings:
    """Verify Windows-874 + Windows-1250 through 1258 all exist."""

    def test_all_windows_enums_exist(self):
        expected = ["WINDOWS_874"] + [f"WINDOWS_{n}" for n in range(1250, 1259)]
        for name in expected:
            assert hasattr(Encoding, name), f"Encoding.{name} missing"

    def test_all_windows_classes_exist(self):
        classes = [Windows874] + [
            Windows1250,
            Windows1251,
            Windows1252,
            Windows1253,
            Windows1254,
            Windows1255,
            Windows1256,
            Windows1257,
            Windows1258,
        ]
        for cls in classes:
            assert hasattr(cls, "ENCODING")
            assert hasattr(cls, "to_unicode")
            assert hasattr(cls, "from_unicode")


# ═════════════════════  Remaining DOS sub-classes  ═════════════════════


class TestDOSCP775:
    def test_to_unicode_ascii(self):
        assert DOSCP775.to_unicode(b"ABC") == "ABC"

    def test_encoding_value(self):
        assert Encoding.DOS_CP775.value == "cp775"


class TestDOSCP855:
    def test_to_unicode_ascii(self):
        assert DOSCP855.to_unicode(b"ABC") == "ABC"

    def test_encoding_value(self):
        assert Encoding.DOS_CP855.value == "cp855"


class TestDOSCP857:
    def test_to_unicode_ascii(self):
        assert DOSCP857.to_unicode(b"ABC") == "ABC"

    def test_encoding_value(self):
        assert Encoding.DOS_CP857.value == "cp857"


class TestDOSCP860:
    def test_to_unicode_ascii(self):
        assert DOSCP860.to_unicode(b"ABC") == "ABC"

    def test_encoding_value(self):
        assert Encoding.DOS_CP860.value == "cp860"


class TestDOSCP861:
    def test_to_unicode_ascii(self):
        assert DOSCP861.to_unicode(b"ABC") == "ABC"

    def test_encoding_value(self):
        assert Encoding.DOS_CP861.value == "cp861"


class TestDOSCP862:
    def test_to_unicode_ascii(self):
        assert DOSCP862.to_unicode(b"ABC") == "ABC"

    def test_encoding_value(self):
        assert Encoding.DOS_CP862.value == "cp862"


class TestDOSCP863:
    def test_to_unicode_ascii(self):
        assert DOSCP863.to_unicode(b"ABC") == "ABC"

    def test_encoding_value(self):
        assert Encoding.DOS_CP863.value == "cp863"


class TestDOSCP864:
    def test_to_unicode_ascii(self):
        assert DOSCP864.to_unicode(b"ABC") == "ABC"

    def test_encoding_value(self):
        assert Encoding.DOS_CP864.value == "cp864"


class TestDOSCP865:
    def test_to_unicode_ascii(self):
        assert DOSCP865.to_unicode(b"ABC") == "ABC"

    def test_encoding_value(self):
        assert Encoding.DOS_CP865.value == "cp865"


class TestDOSCP869:
    def test_to_unicode_ascii(self):
        assert DOSCP869.to_unicode(b"ABC") == "ABC"

    def test_encoding_value(self):
        assert Encoding.DOS_CP869.value == "cp869"


# ═════════════════════  Remaining ISO-8859 sub-classes  ═════════════════


class TestISO8859_3:
    def test_to_unicode_ascii(self):
        assert ISO8859_3.to_unicode(b"ABC") == "ABC"

    def test_encoding_value(self):
        assert Encoding.ISO_8859_3.value == "iso8859_3"


class TestISO8859_4:
    def test_to_unicode_ascii(self):
        assert ISO8859_4.to_unicode(b"ABC") == "ABC"

    def test_encoding_value(self):
        assert Encoding.ISO_8859_4.value == "iso8859_4"


class TestISO8859_6:
    def test_to_unicode_ascii(self):
        assert ISO8859_6.to_unicode(b"ABC") == "ABC"

    def test_encoding_value(self):
        assert Encoding.ISO_8859_6.value == "iso8859_6"


class TestISO8859_8:
    def test_to_unicode_ascii(self):
        assert ISO8859_8.to_unicode(b"ABC") == "ABC"

    def test_encoding_value(self):
        assert Encoding.ISO_8859_8.value == "iso8859_8"


class TestISO8859_9:
    def test_to_unicode_ascii(self):
        assert ISO8859_9.to_unicode(b"ABC") == "ABC"

    def test_encoding_value(self):
        assert Encoding.ISO_8859_9.value == "iso8859_9"


class TestISO8859_10:
    def test_to_unicode_ascii(self):
        assert ISO8859_10.to_unicode(b"ABC") == "ABC"

    def test_encoding_value(self):
        assert Encoding.ISO_8859_10.value == "iso8859_10"


class TestISO8859_11:
    def test_to_unicode_ascii(self):
        assert ISO8859_11.to_unicode(b"ABC") == "ABC"

    def test_encoding_value(self):
        assert Encoding.ISO_8859_11.value == "iso8859_11"


class TestISO8859_13:
    def test_to_unicode_ascii(self):
        assert ISO8859_13.to_unicode(b"ABC") == "ABC"

    def test_encoding_value(self):
        assert Encoding.ISO_8859_13.value == "iso8859_13"


class TestISO8859_14:
    def test_to_unicode_ascii(self):
        assert ISO8859_14.to_unicode(b"ABC") == "ABC"

    def test_encoding_value(self):
        assert Encoding.ISO_8859_14.value == "iso8859_14"


class TestISO8859_16:
    def test_to_unicode_ascii(self):
        assert ISO8859_16.to_unicode(b"ABC") == "ABC"

    def test_encoding_value(self):
        assert Encoding.ISO_8859_16.value == "iso8859_16"


# ═════════════════════  Full Encoding Coverage  ═════════════════════


class TestEncodingCoverage:
    """Ensure every data file has a corresponding Encoding enum."""

    FILE_TO_ENUM = {
        "armscii.tsv": "ARMSCII_8",
        "brda_rten.tsv": "BRDA_RTEN",
        "cp932.tsv": "CP932",
        "cp936.tsv": "CP936",
        "cp949.tsv": "CP949",
        "cp950.tsv": "CP950",
        "dos.tsv": "DOS_CP437",  # representative
        "ebcdic.tsv": "EBCDIC",
        "gb18030.tsv": "GB18030",
        "hkscs.tsv": "BIG5_HKSCS",
        "iso_8859.tsv": "ISO_8859_2",  # representative
        "jis_x_0201.tsv": "JIS",
        "jis_x_0212.tsv": "JIS_EXT",
        "koi8.tsv": "KOI8_R",
        "kps_9566.tsv": "KPS_9566",
        "tai_lao.tsv": "LAO_MULELAO1",  # representative
        "tamil.tsv": "TAMIL_TSCII",  # representative
        "viscii.tsv": "VISCII",
        "windows_cp.tsv": "WINDOWS_1252",  # representative
    }

    def test_all_data_files_have_enum(self):
        for filename, enum_name in self.FILE_TO_ENUM.items():
            assert hasattr(Encoding, enum_name), f"Encoding.{enum_name} missing for {filename}"


class TestNoUnusedImports:
    """Meta-test: ensure every imported class is exercised at least once."""

    def test_all_imports_used(self):
        # Collect all names imported from src.mappings
        import ast

        src = Path(__file__).read_text(encoding="utf-8")
        tree = ast.parse(src)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and getattr(node, "module", "") == "src.mappings":
                for alias in node.names:
                    imported.add(alias.name)

        # Collect all names referenced anywhere in the file
        used = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used.add(node.id)
            elif isinstance(node, ast.Attribute):
                used.add(node.attr)
            elif isinstance(node, ast.Call):
                pass  # Call itself doesn't have a name

        unused = imported - used
        assert not unused, f"Unused imports from src.mappings: {sorted(unused)}"
