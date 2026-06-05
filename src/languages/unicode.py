"""
LanguageUnicode - Python equivalent of c/Languages/LanguageUnicode.h/.cpp

Handles Unicode text operations:
- Normalization (NFD, NFC, NFKD, NFKC)
- Case conversion (upper, lower, title, toggle, fold)
- Entity/NCR/UCN/UTF conversion
- Character property-based operations
"""

import unicodedata
from .class_ import Language, EInput, FF_16, ZERO_16, ZERO_32


class Unicode(Language):
    """
    Unicode text operations class.

    Provides:
    - Unicode normalization forms (NFD, NFC, NFKD, NFKC)
    - Case conversion with locale-aware rules
    - Entity/NCR/UCN/Perl escape conversion
    - UTF-8/16/32 byte code conversion
    - Diacritic stripping and ignorable removal
    - CJK compatibility ideograph conversion
    """

    def __init__(self):
        super().__init__(block_start=0x0000, block_end=0x110000)
        self.on_clear(reset=True)

    # --- Public Static API ---

    @staticmethod
    def to_nfd(text: str) -> str:
        """Convert to Normalization Form D (canonical decomposition)."""
        return unicodedata.normalize("NFD", text)

    @staticmethod
    def to_nfc(text: str) -> str:
        """Convert to Normalization Form C (canonical composition)."""
        return unicodedata.normalize("NFC", text)

    @staticmethod
    def to_nfkd(text: str) -> str:
        """Convert to Normalization Form KD (compatibility decomposition)."""
        return unicodedata.normalize("NFKD", text)

    @staticmethod
    def to_nfkc(text: str) -> str:
        """Convert to Normalization Form KC (compatibility composition)."""
        return unicodedata.normalize("NFKC", text)

    @staticmethod
    def to_upper(text: str) -> str:
        """Convert text to uppercase."""
        return text.upper()

    @staticmethod
    def to_lower(text: str) -> str:
        """Convert text to lowercase."""
        return text.lower()

    @staticmethod
    def to_title(text: str) -> str:
        """Convert text to titlecase."""
        return text.title()

    @staticmethod
    def toggle_case(text: str) -> str:
        """Toggle case of each character."""
        return text.swapcase()

    @staticmethod
    def fold_case(text: str) -> str:
        """Apply Unicode case folding."""
        return unicodedata.normalize("NFKC", text.casefold())

    # --- Conversion methods ---

    @staticmethod
    def convert_to_ncr(text: str) -> str:
        """Convert Unicode to Numeric Character References (&#xXXXX;)."""
        result = []
        for ch in text:
            cp = ord(ch)
            if cp > 0x7F:
                result.append(f"&#x{cp:X};")
            else:
                result.append(ch)
        return "".join(result)

    @staticmethod
    def convert_from_ncr(text: str) -> str:
        """Convert Numeric Character References to Unicode."""
        import re

        def replace_ncr(match):
            hex_val = match.group(1)
            return chr(int(hex_val, 16))

        return re.sub(r"&#[xX]([0-9a-fA-F]+);", replace_ncr, text)

    @staticmethod
    def convert_to_ucn(text: str) -> str:
        """Convert Unicode to Universal Character Names (\\uXXXX)."""
        result = []
        for ch in text:
            cp = ord(ch)
            if cp > 0x7F:
                if cp <= 0xFFFF:
                    result.append(f"\\u{cp:04X}")
                else:
                    result.append(f"\\U{cp:08X}")
            else:
                result.append(ch)
        return "".join(result)

    @staticmethod
    def convert_from_ucn(text: str) -> str:
        """Convert Universal Character Names to Unicode."""
        import re

        def replace_ucn(match):
            return chr(int(match.group(1), 16))

        result = re.sub(r"\\[uU]([0-9a-fA-F]{4,8})", replace_ucn, text)
        return result

    @staticmethod
    def convert_to_uPlus(text: str) -> str:
        """Convert Unicode to U+XXXX format."""
        result = []
        for ch in text:
            cp = ord(ch)
            if cp <= 0xFFFF:
                result.append(f"U+{cp:04X}")
            else:
                result.append(f"U+{cp:06X}")
        return " ".join(result)

    @staticmethod
    def convert_from_uPlus(text: str) -> str:
        """Convert U+XXXX format to Unicode."""
        import re

        def replace_uPlus(match):
            return chr(int(match.group(1), 16))

        return re.sub(r"[Uu]\+([0-9a-fA-F]{4,6})", replace_uPlus, text)

    @staticmethod
    def convert_to_utf8_bytes(text: str, octal: bool = False) -> str:
        """Convert text to UTF-8 byte representation."""
        result = []
        encoded = text.encode("utf-8")
        for byte in encoded:
            if octal:
                result.append(f"\\{byte:03o}")
            else:
                result.append(f"\\x{byte:02X}")
        return "".join(result)

    @staticmethod
    def convert_from_utf8_bytes(text: str) -> str:
        """Convert escaped byte sequence to Unicode."""
        import re

        def replace_byte(match):
            return bytes([int(match.group(1), 16)])

        # Simple implementation for \\xHH format
        hex_bytes = re.findall(r"\\x([0-9a-fA-F]{2})", text)
        try:
            byte_data = bytes(int(b, 16) for b in hex_bytes)
            return byte_data.decode("utf-8", errors="replace")
        except (ValueError, UnicodeDecodeError):
            return text

    @staticmethod
    def strip_diacritics(text: str) -> str:
        """Remove combining diacritical marks from text."""
        return "".join(ch for ch in unicodedata.normalize("NFD", text) if not unicodedata.combining(ch))

    @staticmethod
    def strip_ignorables(text: str) -> str:
        """Remove default-ignorable code points."""
        ignorables = {
            0x00AD,  # SOFT HYPHEN
            0x034F,  # COMBINING GRAPHEME JOINER
            0x061C,  # ARABIC LETTER MARK
            0x200B,
            0x200C,
            0x200D,
            0x200E,
            0x200F,  # ZW spaces/joins
            0x2028,
            0x2029,  # LINE/PARAGRAPH SEPARATOR
            0x202A,
            0x202B,
            0x202C,
            0x202D,
            0x202E,  # Bidi controls
            0x2060,
            0x2061,
            0x2062,
            0x2063,
            0x2064,  # WJ & invisibles
            0xFEFF,  # BOM/ZWNBS
            0xFFF9,
            0xFFFA,
            0xFFFB,  # Interlinear annotations
        }
        return "".join(ch for ch in text if ord(ch) not in ignorables)

    @staticmethod
    def convert_cjk_compat_to_unified(text: str) -> str:
        """Convert CJK Compatibility Ideographs to their Unified equivalents."""
        result = []
        for ch in text:
            cp = ord(ch)
            # CJK Compatibility Ideographs: U+F900-U+FAFF
            if 0xF900 <= cp <= 0xFAFF:
                # Use unicodedata decomposition
                decomp = unicodedata.decomposition(ch)
                if decomp:
                    try:
                        unified = chr(int(decomp.split()[0], 16))
                        result.append(unified)
                        continue
                    except (ValueError, IndexError):
                        pass
            result.append(ch)
        return "".join(result)

    @staticmethod
    def convert_half_to_full(text: str) -> str:
        """Convert halfwidth characters to fullwidth."""
        result = []
        for ch in text:
            cp = ord(ch)
            if 0x0021 <= cp <= 0x007E:
                result.append(chr(cp - 0x0020 + 0xFF00))
            elif cp == 0x0020:
                result.append(chr(0x3000))
            else:
                result.append(ch)
        return "".join(result)

    @staticmethod
    def convert_full_to_half(text: str) -> str:
        """Convert fullwidth characters to halfwidth."""
        result = []
        for ch in text:
            cp = ord(ch)
            if 0xFF01 <= cp <= 0xFF5E:
                result.append(chr(cp - 0xFF00 + 0x0020))
            elif cp == 0x3000:
                result.append(" ")
            else:
                result.append(ch)
        return "".join(result)

    # --- Instance methods ---

    def on_input(self, code: int) -> EInput:
        """Default Unicode input: pass through."""
        self.ch_output = code
        return EInput.CHARACTER

    def do_conversion(
        self, menu_id: int, text_in: str, start: int = 0, end: int = None, skip_ascii: bool = False
    ) -> tuple:
        """Perform Unicode conversion based on menu_id."""
        if end is None:
            end = len(text_in)

        text = text_in[start:end]
        result = ""
        count = 0

        # Map menu_id to conversion function
        conversions = {
            0: self.to_nfd,
            1: self.to_nfc,
            2: self.to_nfkd,
            3: self.to_nfkc,
            4: self.to_upper,
            5: self.to_lower,
            6: self.to_title,
            7: self.toggle_case,
            8: self.fold_case,
            9: self.convert_to_ncr,
            10: self.convert_from_ncr,
            11: self.strip_diacritics,
            12: self.strip_ignorables,
            13: self.convert_cjk_compat_to_unified,
            14: self.convert_half_to_full,
            15: self.convert_full_to_half,
        }

        if menu_id in conversions:
            result = conversions[menu_id](text)
            count = len(text)

        return result, count
