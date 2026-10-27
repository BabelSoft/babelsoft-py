"""
LanguageMongolian - Python equivalent of c/Languages/LanguageMongolian.h/.cpp

Handles Mongolian script (Mongolian block Unicode) input via Latin transcription.
Converts Latin letters to Mongolian Unicode characters with proper vowel harmony
and contextual form selection.
"""

from typing import ClassVar

from .class_ import MAX_MONGOLIAN_WORD, ZERO_16, EInput, Language

# Mongolian digits offset
MONGOLIAN_DIGITS = 0x1810


class StepType:
    NULL = 0
    INITIAL = 1
    MEDIAL = 2


class VowelType:
    NEUTRAL = 0
    BACK = 1
    FRONT = 2


class Mongolian(Language):
    """
    Mongolian language input method.

    Converts Latin transcription to traditional Mongolian script Unicode.
    Supports vowel harmony, number input, and contextual form selection.
    """

    TABLE_PUNCTUATION: ClassVar[list[int]] = [
        0x40,  # @ Commercial At
        0x23,  # # Hash
        0x26,  # & Ampersand
        0x7C,  # | Vertical Line
        0x2C,  # , Comma
        0x2E,  # . Full Stop
        0x3A,  # : Colon
        0x2A,  # * Asterisk
        0x20,  #   Space
        0x24,  # $ Dollar
        0x25,  # % Percent
    ]

    TABLE_PUNCTUATION_MAP: ClassVar[list[int]] = [
        0x0F04,  # @ = Tibetan yig mgo mdun ma
        0x0F05,  # # = Tibetan yig mgo sgab ma
        0x1800,  # Mongolian Birga
        0x1801,  # Mongolian Ellipsis
        0x1802,  # Mongolian Comma
        0x1803,  # Mongolian Full Stop
        0x1804,  # Mongolian Colon
        0x1805,  # Mongolian Four Dots
        0x0020,  # Space (End of Word)
        0x1885,  # baluda
        0x1886,  # triple baluda
    ]

    TABLE_VOWELS: ClassVar[list[list[int]]] = [
        [0x61, 0xFF],  # a
        [0x65, 0xFF],  # e
        [0x69, 0xFF],  # i
        [0x6F, 0xFF],  # o
        [0x75, 0xFF],  # u
        [0x6F, 0x65],  # oe
        [0x75, 0x65],  # ue
        [0x65, 0x65],  # ee
        [0x41, 0xFF],  # A (long a)
        [0x49, 0xFF],  # I (long i)
        [0x55, 0xFF],  # U (long u)
    ]

    TABLE_VOWELS_MAP: ClassVar[list[int]] = [
        0x1820,  # a
        0x1821,  # e
        0x1822,  # i
        0x1823,  # o
        0x1824,  # u
        0x1825,  # oe
        0x1826,  # ue
        0x1827,  # ee
        0x1887,  # A
        0x1888,  # I
        0x18A6,  # U
    ]

    TABLE_CONSONANTS: ClassVar[list[list[int]]] = [
        [0x6E, 0xFF],  # n
        [0x6E, 0x67],  # ng
        [0x62, 0xFF],  # b
        [0x70, 0xFF],  # p
        [0x71, 0xFF],  # q
        [0x67, 0xFF],  # g
        [0x6D, 0xFF],  # m
        [0x6C, 0xFF],  # l
        [0x73, 0xFF],  # s
        [0x78, 0xFF],  # x
        [0x74, 0xFF],  # t
        [0x64, 0xFF],  # d
        [0x63, 0xFF],  # c
        [0x6A, 0xFF],  # j
        [0x79, 0xFF],  # y
        [0x72, 0xFF],  # r
        [0x77, 0xFF],  # w
        [0x66, 0xFF],  # f
        [0x6B, 0xFF],  # k
        [0x7A, 0xFF],  # z
        [0x68, 0xFF],  # h
        [0x6C, 0x68],  # lh
        [0x7A, 0x68],  # zh
        [0x63, 0x68],  # ch
    ]

    TABLE_CONSONANTS_MAP: ClassVar[list[int]] = [
        0x1828,  # n
        0x1829,  # ng
        0x182A,  # b
        0x182B,  # p
        0x182C,  # q
        0x182D,  # g
        0x182E,  # m
        0x182F,  # l
        0x1830,  # s
        0x1831,  # x
        0x1832,  # t
        0x1833,  # d
        0x1834,  # c
        0x1835,  # j
        0x1836,  # y
        0x1837,  # r
        0x1838,  # w
        0x1839,  # f
        0x183A,  # k (qa/ga group)
        0x183B,  # z
        0x183C,  # h
        0x1840,  # lh
        0x1841,  # zh
        0x1842,  # ch
    ]

    TABLE_TRANSCRIPTION_LETTERS: ClassVar[list[str]] = [
        "\u010C", "\u010D", "\u01F0", "\u0160", "\u0161", "k", "\u03B3", "\u0194",
        "\u0263", "v", "\u00D6", "\u00F6", "\u00DC", "\u00FC", "\u2010", "\u2011",
        "'", '"', "^", "\u030C",
    ]
    TABLE_TRANSCRIPTION_MAP: ClassVar[list[tuple[int, int]]] = [
        (0x63, 0), (0x63, 0), (0x6A, 0), (0x78, 0), (0x78, 0), (0x71, 0),
        (0x67, 0), (0x67, 0), (0x77, 0), (0x77, 0), (0x6F, 0x65), (0x6F, 0x65),
        (0x75, 0x65), (0x75, 0x65), (0x2D, 0), (0x2D, 0), (0, 0), (0, 0), (0, 0), (0, 0),
    ]

    def __init__(self):
        super().__init__(block_start=0x1800, block_end=0x18B0)

        self._vowel_type = VowelType.NEUTRAL
        self._is_consonant = False
        self._is_vowel = False
        self._hanging_consonant = False
        self._hanging_vowel = False
        self._word_pos = 0
        self._word = [ZERO_16] * MAX_MONGOLIAN_WORD

        self.on_clear(reset=True)

    # --- Public API ---

    def get_output_string(self) -> str:
        """Get the accumulated Mongolian word output."""
        result = ""
        for i in range(self._word_pos):
            if self._word[i]:
                result += chr(self._word[i])
        self.on_clear()
        return result

    def on_clear(self, reset: bool = False) -> None:
        """Clear Mongolian input state."""
        super().on_clear(reset)
        self._vowel_type = VowelType.NEUTRAL
        self._is_consonant = False
        self._is_vowel = False
        self._hanging_consonant = False
        self._hanging_vowel = False
        self._word_pos = 0
        self._word = [ZERO_16] * MAX_MONGOLIAN_WORD

    def on_input(self, code: int) -> EInput:
        """Process character input for Mongolian Latin transcription."""
        if self._word_pos >= MAX_MONGOLIAN_WORD:
            return EInput.FINISHED

        ch = code

        if self._step == StepType.NULL:
            # Special characters
            special_map = {
                0x2B: 0x180E,  # + = MVS (Mongolian Vowel Separator)
                0x2D: 0x202F,  # - = NNBSP
                0x2F: 0x200C,  # / = ZWNJ
                0x5F: 0x200D,  # _ = ZWJ
                0x7E: 0x180A,  # ~ = Nirugu
                0x27: 0x180B,  # ' = FVS1
                0x22: 0x180C,  # " = FVS2
                0x5E: 0x180D,  # ^ = FVS3
            }

            if ch in special_map:
                self.ch_output = special_map[ch]
                return EInput.CHARACTER

            if self._is_punctuation(ch):
                self.ch_output = self._word[self._word_pos]
                return EInput.CHARACTER

            if self._is_vowel_check(ch) or self._is_consonant_check(ch):
                self._word_pos += 1
                self._step = StepType.INITIAL
                return EInput.IN_PROGRESS

            return EInput.INVALID

        elif self._step == StepType.INITIAL:
            if self._previous_input == 0x6E and ch == 0x67:
                return EInput.INVALID
            self._step = StepType.MEDIAL

        # MEDIAL step
        if self._step == StepType.MEDIAL:
            special_map = {
                0x2B: 0x180E,
                0x2D: 0x202F,
                0x2F: 0x200C,
                0x5F: 0x200D,
                0x7E: 0x180A,
                0x27: 0x180B,
                0x22: 0x180C,
                0x5E: 0x180D,
            }

            if ch in special_map:
                # + (MVS) only allowed after certain letters
                if ch == 0x2B:
                    prev = self._word[self._word_pos - 1] if self._word_pos > 0 else 0
                    allowed = {0x1828, 0x182E, 0x182F, 0x1830, 0x1836, 0x1837, 0x1838}
                    if prev in allowed:
                        self._word[self._word_pos] = 0x180E
                        self._word_pos += 1
                        self._hanging_vowel = False
                        self._hanging_consonant = False
                        return EInput.IN_PROGRESS
                    elif prev in {0x182C, 0x182D, 0x1835}:
                        if self._vowel_type != VowelType.FRONT:
                            self._word[self._word_pos] = 0x180E
                            self._word_pos += 1
                            self._hanging_vowel = False
                            self._hanging_consonant = False
                            return EInput.IN_PROGRESS
                    return EInput.INVALID
                else:
                    self._word[self._word_pos] = special_map[ch]
                    self._word_pos += 1
                    self._hanging_vowel = False
                    self._hanging_consonant = False
                    return EInput.IN_PROGRESS

            # zh/ch must be followed by "i"
            prev = self._word[self._word_pos - 1] if self._word_pos > 0 else 0
            if prev in (0x1841, 0x1842) and ch != 0x69:
                return EInput.INVALID

            # Punctuation after final letters
            final_ok = {0x1836, 0x1840, 0x1841, 0x1842}
            if prev not in final_ok and self._is_punctuation(ch):
                self._word_pos += 1
                return EInput.FINISHED

            # MVS followed by a/e
            if prev == 0x180E:
                if ch == 0x61 and self._vowel_type != VowelType.FRONT:
                    self._word[self._word_pos] = 0x1820
                    self._word_pos += 1
                    return EInput.FINISHED
                elif ch == 0x65 and self._vowel_type != VowelType.BACK:
                    self._word[self._word_pos] = 0x1821
                    self._word_pos += 1
                    return EInput.FINISHED
                return EInput.INVALID

            # Hanging vowel
            if self._hanging_vowel:
                self._word_pos -= 1
                if self._is_vowel_check(ch, self._previous_input):
                    self._word_pos += 1
                    return EInput.IN_PROGRESS
                self._word_pos += 1

            # Hanging consonant
            if self._hanging_consonant:
                self._word_pos -= 1
                if self._is_consonant_check(ch, self._previous_input):
                    self._word_pos += 1
                    return EInput.IN_PROGRESS
                self._word_pos += 1

            if self._is_vowel_check(ch) or self._is_consonant_check(ch):
                self._word_pos += 1
                return EInput.IN_PROGRESS

        return EInput.INVALID

    def _on_number(self, code: int) -> EInput:
        """Convert ASCII digit to Mongolian digit."""
        if 0x30 <= code <= 0x39:
            self.ch_output = code - 0x30 + MONGOLIAN_DIGITS
            return EInput.CHARACTER
        return EInput.NULL

    def on_return(self) -> EInput:
        return EInput.FINISHED

    def do_conversion(
        self, menu_id: int, text_in: str, start: int = 0, end: int | None = None, skip_ascii: bool = False
    ) -> tuple:
        """Convert Latin transcription to Mongolian script."""
        if end is None:
            end = len(text_in)

        self.on_clear(reset=True)
        result = ""

        for ch in self._expand_transcription(text_in[start:end]):
            e_result = self.on_char(ch)

            if e_result == EInput.IN_PROGRESS:
                continue
            elif e_result == EInput.INVALID:
                result += self.get_output_string()
                self.on_clear()
                e_result = self.on_char(ch)
                if e_result == EInput.INVALID:
                    result += ch
            elif e_result == EInput.CHARACTER:
                result += ch
            elif e_result == EInput.FINISHED:
                result += self.get_output_string()

        result += self.get_output_string()
        return result, 0

    @classmethod
    def _expand_transcription(cls, text: str) -> str:
        transcription = dict(zip(cls.TABLE_TRANSCRIPTION_LETTERS, cls.TABLE_TRANSCRIPTION_MAP, strict=True))
        converted_input = []
        for ch in text:
            if "A" <= ch <= "Z":
                ch = ch.lower()
            mapped = transcription.get(ch)
            if mapped is None:
                converted_input.append(ch)
            else:
                converted_input.extend(chr(code) for code in mapped if code)
        return "".join(converted_input)

    # --- Private Helpers ---

    def _is_punctuation(self, code: int) -> bool:
        for i, pc in enumerate(self.TABLE_PUNCTUATION):
            if pc == code:
                if self._word_pos < MAX_MONGOLIAN_WORD:
                    self._word[self._word_pos] = self.TABLE_PUNCTUATION_MAP[i]
                self._hanging_vowel = False
                self._hanging_consonant = False
                return True
        return False

    def _is_vowel_check(self, code1: int, code2: int = 0xFF) -> bool:
        for i, v in enumerate(self.TABLE_VOWELS):
            if v[0] == code1 and v[1] == code2:
                if self._word_pos < MAX_MONGOLIAN_WORD:
                    self._word[self._word_pos] = self.TABLE_VOWELS_MAP[i]
                self._is_consonant = False
                self._is_vowel = True
                self._hanging_consonant = False
                self._hanging_vowel = True

                if code1 in (0x61, 0x69) or code2 == 0x65:
                    self._hanging_vowel = False

                if code1 in (0x61, 0x6F, 0x75):
                    self._vowel_type = VowelType.BACK
                elif code1 == 0x65 or code2 == 0x65:
                    self._vowel_type = VowelType.FRONT
                elif code1 == 0x41 or code2 == 0x49:
                    self._vowel_type = VowelType.NEUTRAL

                return True
        return False

    def _is_consonant_check(self, code1: int, code2: int = 0xFF) -> bool:
        for i, c in enumerate(self.TABLE_CONSONANTS):
            if c[0] == code1 and c[1] == code2:
                if self._word_pos < MAX_MONGOLIAN_WORD:
                    self._word[self._word_pos] = self.TABLE_CONSONANTS_MAP[i]
                self._is_consonant = True
                self._is_vowel = False
                self._hanging_vowel = False
                self._hanging_consonant = True

                if code2 in (0x67, 0x68, 0x72, 0x73):
                    self._hanging_consonant = False
                if code2 in (0x47, 0x48, 0x54, 0x44):
                    self._hanging_consonant = False

                return True
        return False
