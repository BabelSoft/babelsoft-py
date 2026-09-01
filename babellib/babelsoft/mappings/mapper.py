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
    # BrdaRten Tibetan
    BRDA_RTEN = "brda_rten"
    # DOS / OEM code pages
    DOS_CP437 = "cp437"
    DOS_CP737 = "cp737"
    DOS_CP775 = "cp775"
    DOS_CP850 = "cp850"
    DOS_CP852 = "cp852"
    DOS_CP855 = "cp855"
    DOS_CP857 = "cp857"
    DOS_CP860 = "cp860"
    DOS_CP861 = "cp861"
    DOS_CP862 = "cp862"
    DOS_CP863 = "cp863"
    DOS_CP864 = "cp864"
    DOS_CP865 = "cp865"
    DOS_CP866 = "cp866"
    DOS_CP869 = "cp869"
    # KPS 9566 Korean
    KPS_9566 = "kps_9566"
    # Lao
    LAO_MULELAO1 = "mulelao1"
    # Tamil
    TAMIL_TAB = "tab"
    TAMIL_TAM = "tam"
    TAMIL_TSCII = "tscii"
    # ISO-8859 variants (Latin-1 = iso8859_1 is built-in via latin_1)
    ISO_8859_2 = "iso8859_2"
    ISO_8859_3 = "iso8859_3"
    ISO_8859_4 = "iso8859_4"
    ISO_8859_5 = "iso8859_5"
    ISO_8859_6 = "iso8859_6"
    ISO_8859_7 = "iso8859_7"
    ISO_8859_8 = "iso8859_8"
    ISO_8859_9 = "iso8859_9"
    ISO_8859_10 = "iso8859_10"
    ISO_8859_11 = "iso8859_11"
    ISO_8859_13 = "iso8859_13"
    ISO_8859_14 = "iso8859_14"
    ISO_8859_15 = "iso8859_15"
    ISO_8859_16 = "iso8859_16"


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


class HKSCS:
    """Hong Kong Supplementary Character Set (Big5-HKSCS) ↔ Unicode."""

    ENCODING = Encoding.BIG5_HKSCS

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, HKSCS.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, HKSCS.ENCODING)


class JIS:
    """JIS (ISO-2022-JP) ↔ Unicode conversion helpers."""

    ENCODING = Encoding.JIS

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, JIS.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, JIS.ENCODING)


class JIS0212:
    """JIS X 0212 supplement ↔ Unicode conversion helpers."""

    ENCODING = Encoding.JIS_EXT

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, JIS0212.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, JIS0212.ENCODING)


class EUCJP:
    """EUC-JP ↔ Unicode conversion helpers."""

    ENCODING = Encoding.EUC_JP

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, EUCJP.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, EUCJP.ENCODING)


class EUCKR:
    """EUC-KR ↔ Unicode conversion helpers."""

    ENCODING = Encoding.EUC_KR

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, EUCKR.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, EUCKR.ENCODING)


class ShiftJIS:
    """Shift-JIS ↔ Unicode conversion helpers."""

    ENCODING = Encoding.SHIFT_JIS

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, ShiftJIS.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, ShiftJIS.ENCODING)


class GB2312:
    """GB2312 ↔ Unicode conversion helpers."""

    ENCODING = Encoding.GB2312

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, GB2312.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, GB2312.ENCODING)


class GBK:
    """GBK ↔ Unicode conversion helpers."""

    ENCODING = Encoding.GBK

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, GBK.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, GBK.ENCODING)


class KOI8R:
    """KOI8-R (Russian) ↔ Unicode conversion helpers."""

    ENCODING = Encoding.KOI8_R

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, KOI8R.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, KOI8R.ENCODING)


class KOI8U:
    """KOI8-U (Ukrainian) ↔ Unicode conversion helpers."""

    ENCODING = Encoding.KOI8_U

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, KOI8U.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, KOI8U.ENCODING)


class EBCDIC:
    """EBCDIC ↔ Unicode conversion helpers."""

    ENCODING = Encoding.EBCDIC

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, EBCDIC.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, EBCDIC.ENCODING)


class VISCII:
    """VISCII (Vietnamese) ↔ Unicode conversion helpers."""

    ENCODING = Encoding.VISCII

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, VISCII.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, VISCII.ENCODING)


class ARMSCII8:
    """ARMSCII-8 (Armenian) ↔ Unicode conversion helpers."""

    ENCODING = Encoding.ARMSCII_8

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, ARMSCII8.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, ARMSCII8.ENCODING)


class TIS620:
    """TIS-620 (Thai) ↔ Unicode conversion helpers."""

    ENCODING = Encoding.TIS_620

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, TIS620.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, TIS620.ENCODING)


class Windows874:
    """Windows-874 (Thai) ↔ Unicode conversion helpers."""

    ENCODING = Encoding.WINDOWS_874

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, Windows874.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, Windows874.ENCODING)


class Windows1250:
    """Windows-1250 (Central European) ↔ Unicode."""

    ENCODING = Encoding.WINDOWS_1250

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, Windows1250.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, Windows1250.ENCODING)


class Windows1251:
    """Windows-1251 (Cyrillic) ↔ Unicode."""

    ENCODING = Encoding.WINDOWS_1251

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, Windows1251.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, Windows1251.ENCODING)


class Windows1252:
    """Windows-1252 (Western European) ↔ Unicode."""

    ENCODING = Encoding.WINDOWS_1252

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, Windows1252.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, Windows1252.ENCODING)


class Windows1253:
    """Windows-1253 (Greek) ↔ Unicode."""

    ENCODING = Encoding.WINDOWS_1253

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, Windows1253.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, Windows1253.ENCODING)


class Windows1254:
    """Windows-1254 (Turkish) ↔ Unicode."""

    ENCODING = Encoding.WINDOWS_1254

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, Windows1254.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, Windows1254.ENCODING)


class Windows1255:
    """Windows-1255 (Hebrew) ↔ Unicode."""

    ENCODING = Encoding.WINDOWS_1255

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, Windows1255.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, Windows1255.ENCODING)


class Windows1256:
    """Windows-1256 (Arabic) ↔ Unicode."""

    ENCODING = Encoding.WINDOWS_1256

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, Windows1256.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, Windows1256.ENCODING)


class Windows1257:
    """Windows-1257 (Baltic) ↔ Unicode."""

    ENCODING = Encoding.WINDOWS_1257

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, Windows1257.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, Windows1257.ENCODING)


class Windows1258:
    """Windows-1258 (Vietnamese) ↔ Unicode."""

    ENCODING = Encoding.WINDOWS_1258

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, Windows1258.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, Windows1258.ENCODING)


class ASCII:
    """ASCII ↔ Unicode conversion helpers."""

    ENCODING = Encoding.ASCII

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, ASCII.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, ASCII.ENCODING)


class CP950:
    """CP950 (Microsoft Big5 variant) ↔ Unicode conversion helpers."""

    ENCODING = Encoding.CP950

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, CP950.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, CP950.ENCODING)


# ─── BrdaRten (Tibetan) ────────────────────────────────────────────


class BrdaRten:
    """BrdaRten Tibetan encoding (GB/T 20542-2006) ↔ Unicode."""

    ENCODING = Encoding.BRDA_RTEN

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, BrdaRten.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, BrdaRten.ENCODING)


# ─── DOS / OEM code pages ──────────────────────────────────────────


class DOSCP437:
    """DOS CP437 (US) ↔ Unicode."""

    ENCODING = Encoding.DOS_CP437

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, DOSCP437.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, DOSCP437.ENCODING)


class DOSCP737:
    """DOS CP737 (Greek) ↔ Unicode."""

    ENCODING = Encoding.DOS_CP737

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, DOSCP737.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, DOSCP737.ENCODING)


class DOSCP775:
    """DOS CP775 (Baltic) ↔ Unicode."""

    ENCODING = Encoding.DOS_CP775

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, DOSCP775.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, DOSCP775.ENCODING)


class DOSCP850:
    """DOS CP850 (Western Europe) ↔ Unicode."""

    ENCODING = Encoding.DOS_CP850

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, DOSCP850.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, DOSCP850.ENCODING)


class DOSCP852:
    """DOS CP852 (Central Europe) ↔ Unicode."""

    ENCODING = Encoding.DOS_CP852

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, DOSCP852.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, DOSCP852.ENCODING)


class DOSCP855:
    """DOS CP855 (Cyrillic) ↔ Unicode."""

    ENCODING = Encoding.DOS_CP855

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, DOSCP855.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, DOSCP855.ENCODING)


class DOSCP857:
    """DOS CP857 (Turkish) ↔ Unicode."""

    ENCODING = Encoding.DOS_CP857

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, DOSCP857.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, DOSCP857.ENCODING)


class DOSCP860:
    """DOS CP860 (Portuguese) ↔ Unicode."""

    ENCODING = Encoding.DOS_CP860

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, DOSCP860.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, DOSCP860.ENCODING)


class DOSCP861:
    """DOS CP861 (Icelandic) ↔ Unicode."""

    ENCODING = Encoding.DOS_CP861

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, DOSCP861.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, DOSCP861.ENCODING)


class DOSCP862:
    """DOS CP862 (Hebrew) ↔ Unicode."""

    ENCODING = Encoding.DOS_CP862

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, DOSCP862.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, DOSCP862.ENCODING)


class DOSCP863:
    """DOS CP863 (Canadian French) ↔ Unicode."""

    ENCODING = Encoding.DOS_CP863

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, DOSCP863.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, DOSCP863.ENCODING)


class DOSCP864:
    """DOS CP864 (Arabic) ↔ Unicode."""

    ENCODING = Encoding.DOS_CP864

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, DOSCP864.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, DOSCP864.ENCODING)


class DOSCP865:
    """DOS CP865 (Nordic) ↔ Unicode."""

    ENCODING = Encoding.DOS_CP865

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, DOSCP865.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, DOSCP865.ENCODING)


class DOSCP866:
    """DOS CP866 (Cyrillic) ↔ Unicode."""

    ENCODING = Encoding.DOS_CP866

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, DOSCP866.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, DOSCP866.ENCODING)


class DOSCP869:
    """DOS CP869 (Greek) ↔ Unicode."""

    ENCODING = Encoding.DOS_CP869

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, DOSCP869.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, DOSCP869.ENCODING)


# ─── KPS 9566 (Korean) ─────────────────────────────────────────────


class KPS9566:
    """KPS 9566-2003 (Korean) ↔ Unicode."""

    ENCODING = Encoding.KPS_9566

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, KPS9566.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, KPS9566.ENCODING)


# ─── Lao ────────────────────────────────────────────────────────────


class LaoMuleLao1:
    """MULELAO-1 (Lao) ↔ Unicode."""

    ENCODING = Encoding.LAO_MULELAO1

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, LaoMuleLao1.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, LaoMuleLao1.ENCODING)


# ─── Tamil ──────────────────────────────────────────────────────────


class TamilTAB:
    """TAB (Tamil) ↔ Unicode."""

    ENCODING = Encoding.TAMIL_TAB

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, TamilTAB.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, TamilTAB.ENCODING)


class TamilTAM:
    """TAM (Tamil) ↔ Unicode."""

    ENCODING = Encoding.TAMIL_TAM

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, TamilTAM.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, TamilTAM.ENCODING)


class TamilTSCII:
    """TSCII (Tamil) ↔ Unicode."""

    ENCODING = Encoding.TAMIL_TSCII

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, TamilTSCII.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, TamilTSCII.ENCODING)


# ─── ISO-8859 variants ─────────────────────────────────────────────


class ISO8859_2:
    """ISO-8859-2 (Latin-2, Central European) ↔ Unicode."""

    ENCODING = Encoding.ISO_8859_2

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, ISO8859_2.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, ISO8859_2.ENCODING)


class ISO8859_3:
    """ISO-8859-3 (Latin-3, South European) ↔ Unicode."""

    ENCODING = Encoding.ISO_8859_3

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, ISO8859_3.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, ISO8859_3.ENCODING)


class ISO8859_4:
    """ISO-8859-4 (Latin-4, North European) ↔ Unicode."""

    ENCODING = Encoding.ISO_8859_4

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, ISO8859_4.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, ISO8859_4.ENCODING)


class ISO8859_5:
    """ISO-8859-5 (Cyrillic) ↔ Unicode."""

    ENCODING = Encoding.ISO_8859_5

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, ISO8859_5.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, ISO8859_5.ENCODING)


class ISO8859_6:
    """ISO-8859-6 (Arabic) ↔ Unicode."""

    ENCODING = Encoding.ISO_8859_6

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, ISO8859_6.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, ISO8859_6.ENCODING)


class ISO8859_7:
    """ISO-8859-7 (Greek) ↔ Unicode."""

    ENCODING = Encoding.ISO_8859_7

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, ISO8859_7.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, ISO8859_7.ENCODING)


class ISO8859_8:
    """ISO-8859-8 (Hebrew) ↔ Unicode."""

    ENCODING = Encoding.ISO_8859_8

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, ISO8859_8.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, ISO8859_8.ENCODING)


class ISO8859_9:
    """ISO-8859-9 (Latin-5, Turkish) ↔ Unicode."""

    ENCODING = Encoding.ISO_8859_9

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, ISO8859_9.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, ISO8859_9.ENCODING)


class ISO8859_10:
    """ISO-8859-10 (Latin-6, Nordic) ↔ Unicode."""

    ENCODING = Encoding.ISO_8859_10

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, ISO8859_10.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, ISO8859_10.ENCODING)


class ISO8859_11:
    """ISO-8859-11 (Thai) ↔ Unicode."""

    ENCODING = Encoding.ISO_8859_11

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, ISO8859_11.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, ISO8859_11.ENCODING)


class ISO8859_13:
    """ISO-8859-13 (Latin-7, Baltic Rim) ↔ Unicode."""

    ENCODING = Encoding.ISO_8859_13

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, ISO8859_13.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, ISO8859_13.ENCODING)


class ISO8859_14:
    """ISO-8859-14 (Latin-8, Celtic) ↔ Unicode."""

    ENCODING = Encoding.ISO_8859_14

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, ISO8859_14.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, ISO8859_14.ENCODING)


class ISO8859_15:
    """ISO-8859-15 (Latin-9, Euro) ↔ Unicode."""

    ENCODING = Encoding.ISO_8859_15

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, ISO8859_15.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, ISO8859_15.ENCODING)


class ISO8859_16:
    """ISO-8859-16 (Latin-10, Southeast Europe) ↔ Unicode."""

    ENCODING = Encoding.ISO_8859_16

    @staticmethod
    def to_unicode(data: bytes) -> str:
        return Mapper.to_unicode(data, ISO8859_16.ENCODING)

    @staticmethod
    def from_unicode(text: str) -> bytes:
        return Mapper.from_unicode(text, ISO8859_16.ENCODING)
