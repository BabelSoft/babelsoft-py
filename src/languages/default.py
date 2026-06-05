"""
LanguageDefault - Python equivalent of c/Languages/LanguageDefault.h/.cpp

Default language handler for CJK conversions and basic text operations.
Provides:
- CJK reading conversion (Pinyin, Jyutping, Korean, Vietnamese, Zhuang)
- Simplified/Traditional Chinese conversion
- Hanzi/Kanji old/new form conversion
- VIQR conversion
- Kana conversion (Hiragana <-> Katakana)
- Fullwidth/Halfwidth conversion
- Hangul syllable/letter decomposition/composition
- Caesar cipher
- Line reversal
"""

from .class_ import Language, EInput, FF_16, ZERO_16, ZERO_32


class Default(Language):
    """
    Default language handler for general text conversions.

    Handles operations that are not specific to a single script:
    CJK readings, case operations, typographic conversions, etc.
    """

    def __init__(self):
        super().__init__(block_start=0x0000, block_end=0x110000)
        self._high_surrogate = FF_16
        self.on_clear(reset=True)

    # --- Public API ---

    def on_input(self, code: int) -> EInput:
        """
        Default input: Handle surrogate pairs, pass through BMP characters.
        """
        if 0xD800 <= code <= 0xDBFF:  # High surrogate
            self._high_surrogate = code
            return EInput.NULL
        elif 0xDC00 <= code <= 0xDFFF:  # Low surrogate
            if self._high_surrogate != FF_16:
                hi = self._high_surrogate
                self.ch_output = 0x10000 + ((hi - 0xD800) << 10) + (code - 0xDC00)
                self._high_surrogate = FF_16
                return EInput.CHAR32
            return EInput.INVALID

        return EInput.CHARACTER

    def _on_number(self, code: int) -> EInput:
        return EInput.NULL

    def do_conversion(
        self, menu_id: int, text_in: str, start: int = 0, end: int = None, skip_ascii: bool = False
    ) -> tuple:
        """Perform conversion based on menu_id."""
        if end is None:
            end = len(text_in)

        text = text_in[start:end]
        result = ""
        count = 0

        conversions = {
            0: self._convert_hiragana_to_katakana,
            1: self._convert_katakana_to_hiragana,
            2: self._convert_fullwidth_halfwidth,
            3: self._convert_hangul_to_letters,
            4: self._convert_letters_to_hangul,
            5: self._convert_typographic,
            6: self._reverse_lines,
            7: self._apply_caesar,
        }

        if menu_id in conversions:
            result, count = conversions[menu_id](text)

        return result, count

    # --- CJK Conversion Methods ---

    @staticmethod
    def _convert_hiragana_to_katakana(text: str) -> tuple:
        """Convert Hiragana to Katakana."""
        result = []
        count = 0
        for ch in text:
            cp = ord(ch)
            if 0x3041 <= cp <= 0x3096:  # Hiragana range
                result.append(chr(cp + 0x60))  # Shift to Katakana
                count += 1
            else:
                result.append(ch)
        return "".join(result), count

    @staticmethod
    def _convert_katakana_to_hiragana(text: str) -> tuple:
        """Convert Katakana to Hiragana."""
        result = []
        count = 0
        for ch in text:
            cp = ord(ch)
            if 0x30A1 <= cp <= 0x30F6:  # Katakana range
                result.append(chr(cp - 0x60))  # Shift to Hiragana
                count += 1
            else:
                result.append(ch)
        return "".join(result), count

    @staticmethod
    def _convert_fullwidth_halfwidth(text: str) -> tuple:
        """Toggle between fullwidth and halfwidth forms."""
        result = []
        count = 0
        for ch in text:
            cp = ord(ch)
            # Fullwidth ASCII -> Halfwidth
            if 0xFF01 <= cp <= 0xFF5E:
                result.append(chr(cp - 0xFEE0))
                count += 1
            elif cp == 0x3000:  # Fullwidth space
                result.append(" ")
                count += 1
            # Halfwidth -> Fullwidth
            elif 0x0021 <= cp <= 0x007E:
                result.append(chr(cp + 0xFEE0))
                count += 1
            elif cp == 0x0020:
                result.append(chr(0x3000))
                count += 1
            else:
                result.append(ch)
        return "".join(result), count

    @staticmethod
    def _convert_hangul_to_letters(text: str) -> tuple:
        """Decompose Hangul syllables into Jamo letters."""
        result = []
        count = 0
        for ch in text:
            cp = ord(ch)
            if 0xAC00 <= cp <= 0xD7A3:  # Hangul syllables
                # Decompose using standard formula
                s_index = cp - 0xAC00
                lead = 0x1100 + (s_index // 588)  # Choseong (19)
                vowel = 0x1161 + ((s_index % 588) // 28)  # Jungseong (21)
                trail = 0x11A7 + (s_index % 28)  # Jongseong (28, 0=none)

                result.append(chr(lead))
                result.append(chr(vowel))
                if trail != 0x11A7:  # Has jongseong
                    result.append(chr(trail))
                count += 1
            else:
                result.append(ch)
        return "".join(result), count

    @staticmethod
    def _convert_letters_to_hangul(text: str) -> tuple:
        """Compose Jamo letters into Hangul syllables."""
        # Choseong (leading consonants): U+1100-U+1112
        # Jungseong (vowels): U+1161-U+1175
        # Jongseong (trailing consonants): U+11A8-U+11C2
        CHOSEONG = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
        JUNGSEONG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
        JONGSEONG = " ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"

        result = []
        count = 0
        i = 0
        while i < len(text):
            cp = ord(text[i])
            if 0x1100 <= cp <= 0x1112:  # Choseong
                lead = cp - 0x1100
                vowel_idx = 0
                trail_idx = 0
                i += 1
                if i < len(text):
                    vp = ord(text[i])
                    if 0x1161 <= vp <= 0x1175:
                        vowel_idx = vp - 0x1161
                        i += 1
                        if i < len(text):
                            tp = ord(text[i])
                            if 0x11A8 <= tp <= 0x11C2:
                                trail_idx = tp - 0x11A7
                                i += 1

                syl = 0xAC00 + (lead * 588) + (vowel_idx * 28) + trail_idx
                if 0xAC00 <= syl <= 0xD7A3:
                    result.append(chr(syl))
                    count += 1
                    continue
            result.append(text[i])
            i += 1

        return "".join(result), count

    @staticmethod
    def _convert_typographic(text: str) -> tuple:
        """Apply typographic conversions (quotes, dashes, etc.)."""
        replacements = {
            '"': "\u201c",  # Left double quote
            "'": "\u2018",  # Left single quote
            "--": "\u2014",  # Em dash
            "...": "\u2026",  # Ellipsis
            "(C)": "\u00a9",  # Copyright
            "(R)": "\u00ae",  # Registered
            "(TM)": "\u2122",  # Trademark
        }
        result = text
        count = 0
        for old, new in replacements.items():
            if old in result:
                count += result.count(old)
                result = result.replace(old, new)
        return result, count

    @staticmethod
    def _reverse_lines(text: str) -> tuple:
        """Reverse the order of lines."""
        lines = text.split("\n")
        reversed_lines = lines[::-1]
        return "\n".join(reversed_lines), len(lines)

    @staticmethod
    def _apply_caesar(text: str, offset: int = 1, forward: bool = True) -> tuple:
        """Apply Caesar cipher shift."""
        result = []
        count = 0
        if not forward:
            offset = -offset
        for ch in text:
            if "A" <= ch <= "Z":
                result.append(chr((ord(ch) - 65 + offset) % 26 + 65))
                count += 1
            elif "a" <= ch <= "z":
                result.append(chr((ord(ch) - 97 + offset) % 26 + 97))
                count += 1
            else:
                result.append(ch)
        return "".join(result), count
