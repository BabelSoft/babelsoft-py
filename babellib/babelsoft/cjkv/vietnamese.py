"""Vietnamese (Quốc Ngữ) reading lookup for CJK characters.

Mirrors the C++ Vietnamese class from Vietnamese.h/Vietnamese.cpp.
Includes VIQR encoding support.
"""

from __future__ import annotations

from collections import defaultdict
from typing import ClassVar

from babelsoft.cjkv.lookup import Lookup
from babelsoft.utils_.dirs import Dirs
from babelsoft.utils_.parser import TsvParser, parse_codepoint


class Vietnamese(Lookup):
    """Vietnamese (Quốc Ngữ) reading lookup for CJK characters."""

    # ── VIQR Mapping Table (mirrors C++ TableVIQR) ──
    # Maps Unicode codepoint -> (VIQR char 1, VIQR char 2, VIQR char 3)
    _viqr_table: ClassVar[list[tuple[int, str]]] = [
        # Format: (unicode_cp, viqr1, viqr2, viqr3) - viqr values are ASCII+0x20 offsets
        (0x00C0, "A`"),  # À
        (0x00C1, "A'"),  # Á
        (0x00C2, "A^"),  # Â
        (0x00C3, "A~"),  # Ã
        (0x00C8, "E`"),  # È
        (0x00C9, "E'"),  # É
        (0x00CA, "E^"),  # Ê
        (0x00CC, "I`"),  # Ì
        (0x00CD, "I'"),  # Í
        (0x00D2, "O`"),  # Ò
        (0x00D3, "O'"),  # Ó
        (0x00D4, "O^"),  # Ô
        (0x00D5, "O~"),  # Õ
        (0x00D9, "U`"),  # Ù
        (0x00DA, "U'"),  # Ú
        (0x00DD, "Y'"),  # Ý
        (0x00E0, "a`"),  # à
        (0x00E1, "a'"),  # á
        (0x00E2, "a^"),  # â
        (0x00E3, "a~"),  # ã
        (0x00E8, "e`"),  # è
        (0x00E9, "e'"),  # é
        (0x00EA, "e^"),  # ê
        (0x00EC, "i`"),  # ì
        (0x00ED, "i'"),  # í
        (0x00F2, "o`"),  # ò
        (0x00F3, "o'"),  # ó
        (0x00F4, "o^"),  # ô
        (0x00F5, "o~"),  # õ
        (0x00F9, "u`"),  # ù
        (0x00FA, "u'"),  # ú
        (0x00FD, "y'"),  # ý
        (0x0102, "A("),  # Ă
        (0x0103, "a("),  # ă
        (0x0110, "DD"),  # Đ
        (0x0111, "dd"),  # đ
        (0x0128, "I~"),  # Ĩ
        (0x0129, "i~"),  # ĩ
        (0x0168, "U~"),  # Ũ
        (0x0169, "u~"),  # ũ
        (0x01A0, "O+"),  # Ơ
        (0x01A1, "o+"),  # ơ
        (0x01AF, "U+"),  # Ư
        (0x01B0, "u+"),  # ư
        (0x1EA0, "A."),  # Ạ
        (0x1EA1, "a."),  # ạ
        (0x1EA2, "A?"),  # Ả
        (0x1EA3, "a?"),  # ả
        (0x1EA4, "A^'"),  # Ấ
        (0x1EA5, "a^'"),  # ấ
        (0x1EA6, "A^`"),  # Ầ
        (0x1EA7, "a^`"),  # ầ
        (0x1EA8, "A^?"),  # Ẩ
        (0x1EA9, "a^?"),  # ẩ
        (0x1EAA, "A^~"),  # Ẫ
        (0x1EAB, "a^~"),  # ẫ
        (0x1EAC, "A^."),  # Ậ
        (0x1EAD, "a^."),  # ậ
        (0x1EAE, "A('"),  # Ắ
        (0x1EAF, "a('"),  # ắ
        (0x1EB0, "A(`"),  # Ằ
        (0x1EB1, "a(`"),  # ằ
        (0x1EB2, "A(?"),  # Ẳ
        (0x1EB3, "a(?"),  # ẳ
        (0x1EB4, "A(~"),  # Ẵ
        (0x1EB5, "a(~"),  # ẵ
        (0x1EB6, "A(."),  # Ặ
        (0x1EB7, "a(."),  # ặ
        (0x1EB8, "E."),  # Ẹ
        (0x1EB9, "e."),  # ẹ
        (0x1EBA, "E?"),  # Ẻ
        (0x1EBB, "e?"),  # ẻ
        (0x1EBC, "E~"),  # Ẽ
        (0x1EBD, "e~"),  # ẽ
        (0x1EBE, "E^'"),  # Ế
        (0x1EBF, "e^'"),  # ế
        (0x1EC0, "E^`"),  # Ề
        (0x1EC1, "e^`"),  # ề
        (0x1EC2, "E^?"),  # Ể
        (0x1EC3, "e^?"),  # ể
        (0x1EC4, "E^~"),  # Ễ
        (0x1EC5, "e^~"),  # ễ
        (0x1EC6, "E^."),  # Ệ
        (0x1EC7, "e^."),  # ệ
        (0x1EC8, "I?"),  # Ỉ
        (0x1EC9, "i?"),  # ỉ
        (0x1ECA, "I."),  # Ị
        (0x1ECB, "i."),  # ị
        (0x1ECC, "O."),  # Ọ
        (0x1ECD, "o."),  # ọ
        (0x1ECE, "O?"),  # Ỏ
        (0x1ECF, "o?"),  # ỏ
        (0x1ED0, "O^'"),  # Ố
        (0x1ED1, "o^'"),  # ố
        (0x1ED2, "O^`"),  # Ồ
        (0x1ED3, "o^`"),  # ồ
        (0x1ED4, "O^?"),  # Ổ
        (0x1ED5, "o^?"),  # ổ
        (0x1ED6, "O^~"),  # Ỗ
        (0x1ED7, "o^~"),  # ỗ
        (0x1ED8, "O^."),  # Ộ
        (0x1ED9, "o^."),  # ộ
        (0x1EDA, "O+'"),  # Ớ
        (0x1EDB, "o+'"),  # ớ
        (0x1EDC, "O+`"),  # Ờ
        (0x1EDD, "o+`"),  # ờ
        (0x1EDE, "O+?"),  # Ở
        (0x1EDF, "o+?"),  # ở
        (0x1EE0, "O+~"),  # Ỡ
        (0x1EE1, "o+~"),  # ỡ
        (0x1EE2, "O+."),  # Ợ
        (0x1EE3, "o+."),  # ợ
        (0x1EE4, "U."),  # Ụ
        (0x1EE5, "u."),  # ụ
        (0x1EE6, "U?"),  # Ủ
        (0x1EE7, "u?"),  # ủ
        (0x1EE8, "U+'"),  # Ứ
        (0x1EE9, "u+'"),  # ứ
        (0x1EEA, "U+`"),  # Ừ
        (0x1EEB, "u+`"),  # ừ
        (0x1EEC, "U+?"),  # Ử
        (0x1EED, "u+?"),  # ử
        (0x1EEE, "U+~"),  # Ữ
        (0x1EEF, "u+~"),  # ữ
        (0x1EF0, "U+."),  # Ự
        (0x1EF1, "u+."),  # ự
        (0x1EF2, "Y`"),  # Ỳ
        (0x1EF3, "y`"),  # ỳ
        (0x1EF4, "Y."),  # Ỵ
        (0x1EF5, "y."),  # ỵ
        (0x1EF6, "Y?"),  # Ỷ
        (0x1EF7, "y?"),  # ỷ
        (0x1EF8, "Y~"),  # Ỹ
        (0x1EF9, "y~"),  # ỹ
    ]

    # Build reverse index: viqr_str -> unicode_cp
    _viqr_to_unicode: ClassVar[dict[str, int]] = {}
    _viqr_initialized: ClassVar[bool] = False

    # ── Cached reading data ──
    _data_loaded: ClassVar[bool] = False
    _readings: ClassVar[dict[int, list[str]]] = {}

    @classmethod
    def _init_viqr(cls) -> None:
        """Initialize VIQR lookup tables."""
        if cls._viqr_initialized:
            return
        cls._viqr_initialized = True
        for unicode_cp, viqr_str in cls._viqr_table:
            cls._viqr_to_unicode[viqr_str] = unicode_cp

    @classmethod
    def _load_data(cls) -> None:
        """Load Vietnamese reading data from TSV file (lazy, once)."""
        if cls._data_loaded:
            return
        cls._data_loaded = True

        raw: defaultdict[int, list[str]] = defaultdict(list)

        for row in TsvParser.get_tsv(Dirs.BABELSOFT / "cjk_readings.tsv"):
            if len(row) < 3 or row[1] != "kVietnamese":
                continue
            cp = parse_codepoint(row[0])
            for reading in row[2].split():
                raw[cp].append(reading)

        cls._readings = dict(raw)

    @classmethod
    def is_viqr(cls, ch: int) -> bool:
        """Check if a character is a VIQR-encoded Vietnamese character."""
        cls._init_viqr()
        # VIQR characters are printable ASCII (0x21-0x7E) and some extended
        return 0x21 <= ch <= 0x7E

    @classmethod
    def unicode_to_viqr(cls, ch: int) -> str:
        """Convert a Unicode Vietnamese character to VIQR encoding."""
        cls._init_viqr()
        if 0x00C0 <= ch <= 0x1EF9:
            for unicode_cp, viqr_str in cls._viqr_table:
                if unicode_cp > ch:
                    break
                if unicode_cp == ch:
                    return viqr_str
        # Non-Vietnamese character: use as-is (offset by 0x20)
        return chr(ch - 0x20) if 0x21 <= ch <= 0x7E else chr(ch)

    @classmethod
    def viqr_to_unicode(cls, ch1: int, ch2: int, ch3: int) -> tuple[int, int, int, int]:
        """Convert VIQR-encoded characters to Unicode.

        Returns:
            Tuple of (unicode_cp, remaining_ch1, remaining_ch2, remaining_ch3).
        """
        cls._init_viqr()

        # Check for 3-char VIQR first
        key3 = chr(ch1) + chr(ch2) + chr(ch3)
        if key3 in cls._viqr_to_unicode:
            return (cls._viqr_to_unicode[key3], 0, 0, 0)

        # Check for 2-char VIQR
        key2 = chr(ch1) + chr(ch2)
        if key2 in cls._viqr_to_unicode:
            return (cls._viqr_to_unicode[key2], ch3, 0, 0)

        # No VIQR match: use ch1 as-is
        return (ch1, ch2, ch3, 0)

    @classmethod
    def viqr_to_text(cls, text: str) -> str:
        """Decode a whole VIQR-encoded string into Unicode Vietnamese.

        Greedy longest-match (3, then 2, then 1 character); characters without
        a VIQR spelling are copied through unchanged.
        """
        cls._init_viqr()
        out: list[str] = []
        i = 0
        n = len(text)
        while i < n:
            for size in (3, 2, 1):
                if i + size <= n:
                    cp = cls._viqr_to_unicode.get(text[i : i + size])
                    if cp is not None:
                        out.append(chr(cp))
                        i += size
                        break
            else:
                out.append(text[i])
                i += 1
        return "".join(out)

    @classmethod
    def _get_viqr_reading(cls, unicode_str: str) -> str:
        """Convert a Unicode Vietnamese reading string to VIQR encoding."""
        result = []
        for ch in unicode_str:
            cp = ord(ch)
            if cp < 0x7E:
                result.append(chr(cp - 0x20))
            else:
                result.append(cls.unicode_to_viqr(cp))
        return "".join(result)

    @classmethod
    def get_vietnamese_for_char(
        cls,
        cp: int,
        *,
        use_viqr: bool = False,
        first_reading_only: bool = False,
        separator: str = ", ",
    ) -> str:
        """Get Vietnamese (Quốc Ngữ) reading(s) for a CJK character.

        Args:
            cp: Unicode codepoint of the CJK character.
            use_viqr: If True, return VIQR-encoded readings.
            first_reading_only: If True, return only the first reading.
            separator: Separator string between multiple readings.

        Returns:
            Comma-separated Vietnamese reading string, or empty string if not found.
        """
        cls._load_data()
        entries = cls._readings.get(cp)
        if not entries:
            return ""

        result_parts: list[str] = []

        for reading in entries:
            if use_viqr:
                text = cls._get_viqr_reading(reading)
                if not cls._upper_case_readings:
                    text = text.lower()
            else:
                text = reading
                if cls._upper_case_readings:
                    text = text.upper()

            result_parts.append(text)

            if first_reading_only:
                break

        return separator.join(result_parts)
