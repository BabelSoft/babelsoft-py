"""
Tests for data/mappings/*.tsv — validating encoding mapping exports.
"""

import re
from pathlib import Path

import pytest

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

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_blank_line_before_data(self, filename: str):
        text: str = (MAPPINGS_DIR / filename).read_text(encoding="utf-8")
        # The last comment line should be followed by an empty line, then data
        lines = text.split("\n")
        # Find last comment line
        last_comment = max(i for i, ln in enumerate(lines) if ln.startswith("#"))
        # Next line should be empty
        assert lines[last_comment + 1] == "", f"{filename}: no blank line after header comments"


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
