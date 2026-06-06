"""
Mappings — character encoding conversion tables (ported from c/Mappings/)

Provides conversion between legacy encodings and Unicode for:
Big5, GB18030, CP932/CP936/CP949, JIS, EUC, EBCDIC, KOI8,
VISCII, ARMSCII, and other encodings.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Encoding(Enum):
    """Supported legacy encodings."""

    ASCII = "ascii"
    BIG5 = "big5"
    BIG5_HKSCS = "big5hkscs"
    CP932 = "cp932"  # Shift-JIS
    CP936 = "cp936"  # GBK
    CP949 = "cp949"  # Korean EUC
    CP950 = "cp950"  # Big5 (Microsoft)
    EUC_JP = "euc_jp"
    EUC_KR = "euc_kr"
    GB18030 = "gb18030"
    GB2312 = "gb2312"
    GBK = "gbk"
    JIS = "iso2022_jp"
    JIS_EXT = "iso2022_jp_ext"
    SHIFT_JIS = "shift_jis"
    KOI8_R = "koi8_r"
    KOI8_U = "koi8_u"
    EBCDIC = "ebcdic_cp_us"
    VISCII = "viscii"
    ARMSCII_8 = "armscii_8"
    TIS_620 = "tis_620"  # Thai
    WINDOWS_874 = "windows_874"
    WINDOWS_1250 = "windows_1250"
    WINDOWS_1251 = "windows_1251"
    WINDOWS_1252 = "windows_1252"
    WINDOWS_1253 = "windows_1253"
    WINDOWS_1254 = "windows_1254"
    WINDOWS_1255 = "windows_1255"
    WINDOWS_1256 = "windows_1256"
    WINDOWS_1257 = "windows_1257"
    WINDOWS_1258 = "windows_1258"


@dataclass
class MappingResult:
    """Result of a character mapping operation."""

    codepoint: int
    is_valid: bool
    is_fallback: bool = False


class Mapper:
    """Unicode ↔ legacy encoding mapper."""

    # Custom mapping tables (extended beyond Python's built-in codecs)
    _CUSTOM_MAPS: dict[str, dict[int, int]] = {}
    _CUSTOM_REVERSE: dict[str, dict[int, int]] = {}

    @classmethod
    def register_mapping(cls, name: str, to_unicode: dict[int, int]) -> None:
        """Register a custom byte-to-Unicode mapping."""
        cls._CUSTOM_MAPS[name] = to_unicode
        cls._CUSTOM_REVERSE[name] = {v: k for k, v in to_unicode.items()}

    @classmethod
    def to_unicode(cls, byte_seq: bytes, encoding: Encoding | str) -> str:
        """Convert bytes from a legacy encoding to Unicode."""
        enc = encoding.value if isinstance(encoding, Encoding) else encoding

        if enc in cls._CUSTOM_MAPS:
            result: list[str] = []
            table = cls._CUSTOM_MAPS[enc]
            i = 0
            while i < len(byte_seq):
                b = byte_seq[i]
                # Try double-byte first (for CJK encodings)
                if i + 1 < len(byte_seq):
                    db = (b << 8) | byte_seq[i + 1]
                    if db in table:
                        result.append(chr(table[db]))
                        i += 2
                        continue
                if b in table:
                    result.append(chr(table[b]))
                else:
                    result.append(chr(0xFFFD))  # Replacement character
                i += 1
            return "".join(result)

        # Fall back to Python built-in codec
        try:
            return byte_seq.decode(enc, errors="replace")
        except (LookupError, UnicodeDecodeError):
            return byte_seq.decode("ascii", errors="replace")

    @classmethod
    def from_unicode(cls, text: str, encoding: Encoding | str) -> bytes:
        """Convert Unicode text to a legacy encoding."""
        enc = encoding.value if isinstance(encoding, Encoding) else encoding

        if enc in cls._CUSTOM_REVERSE:
            result: list[int] = []
            rev = cls._CUSTOM_REVERSE[enc]
            for ch in text:
                cp = ord(ch)
                if cp in rev:
                    b = rev[cp]
                    if b > 0xFF:
                        result.append((b >> 8) & 0xFF)
                        result.append(b & 0xFF)
                    else:
                        result.append(b)
                else:
                    result.append(0x3F)  # '?'
            return bytes(result)

        try:
            return text.encode(enc, errors="replace")
        except (LookupError, UnicodeEncodeError):
            return text.encode("ascii", errors="replace")

    @classmethod
    def get_unicode_for_byte(cls, byte_val: int, encoding: Encoding | str) -> int:
        """Map a single byte (or double-byte) to a Unicode codepoint."""
        enc = encoding.value if isinstance(encoding, Encoding) else encoding
        if enc in cls._CUSTOM_MAPS and byte_val in cls._CUSTOM_MAPS[enc]:
            return cls._CUSTOM_MAPS[enc][byte_val]
        return 0

    @classmethod
    def get_byte_for_unicode(cls, cp: int, encoding: Encoding | str) -> int:
        """Map a Unicode codepoint to a byte value."""
        enc = encoding.value if isinstance(encoding, Encoding) else encoding
        if enc in cls._CUSTOM_REVERSE and cp in cls._CUSTOM_REVERSE[enc]:
            return cls._CUSTOM_REVERSE[enc][cp]
        return 0

    @classmethod
    def list_encodings(cls) -> list[str]:
        """List all available encodings (built-in + custom)."""
        import encodings

        aliases = encodings.aliases.aliases
        builtins = set(aliases.keys()) | set(aliases.values())
        customs = set(cls._CUSTOM_MAPS.keys())
        return sorted(builtins | customs)


# ─── Specific encoding helpers ────────────────────────────────────────


class Big5:
    """Big5 ↔ Unicode conversion helpers."""

    ENCODING = Encoding.BIG5

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, Big5.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, Big5.ENCODING)


class GB18030:
    """GB18030 ↔ Unicode conversion helpers."""

    ENCODING = Encoding.GB18030

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, GB18030.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, GB18030.ENCODING)


class CP932:
    """CP932 (Shift-JIS) ↔ Unicode conversion helpers."""

    ENCODING = Encoding.CP932

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, CP932.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, CP932.ENCODING)


class CP936:
    """CP936 (GBK) ↔ Unicode conversion helpers."""

    ENCODING = Encoding.CP936

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, CP936.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, CP936.ENCODING)


class CP949:
    """CP949 (Korean EUC) ↔ Unicode conversion helpers."""

    ENCODING = Encoding.CP949

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, CP949.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, CP949.ENCODING)
