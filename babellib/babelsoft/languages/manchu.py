"""
LanguageManchu - Python equivalent of c/Languages/LanguageManchu.h/.cpp

Handles Manchu script (Mongolian block Unicode) input via Latin transcription.
Converts Latin letters to Manchu/Mongolian Unicode characters with proper
vowel harmony and contextual form selection.
"""

from typing import ClassVar

from .class_ import MAX_MONGOLIAN_WORD, ZERO_16, EInput, Language


class StepType:
    NULL = 0
    INITIAL = 1
    MEDIAL = 2


class VowelType:
    NEUTRAL = 0
    BACK = 1
    FRONT = 2


class Manchu(Language):
    """
    Manchu language input method.

    Converts Latin transcription input to Manchu script Unicode characters
    in the Mongolian block (U+1800-U+18AF). Supports vowel harmony rules
    and contextual letter form selection.
    """

    # --- Static Data Tables ---

    TABLE_PUNCTUATION: ClassVar[list[int]] = [
        0x7C,  # | Vertical Line
        0x2C,  # , Comma
        0x2E,  # . Full Stop
        0x3A,  # : Colon
        0x20,  #   Space
        0x24,  # $ Dollar
        0x25,  # % Percent
    ]

    TABLE_PUNCTUATION_MAP: ClassVar[list[int]] = [
        0x1801,  # Manchu Ellipsis
        0x1808,  # Manchu Comma
        0x1809,  # Manchu Full Stop
        0x1804,  # Manchu Colon
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
        [0x75, 0x75],  # uu
        [0x41, 0xFF],  # A (long a)
        [0x49, 0xFF],  # I (long i)
    ]

    TABLE_VOWELS_MAP: ClassVar[list[int]] = [
        0x1820,  # a
        0x185D,  # e
        0x1873,  # i
        0x1823,  # o
        0x1860,  # u
        0x1861,  # uu
        0x1887,  # A (long a)
        0x1888,  # I (long i)
    ]

    TABLE_CONSONANTS: ClassVar[list[list[int]]] = [
        [0x6E, 0xFF],  # n
        [0x6E, 0x67],  # ng
        [0x6B, 0xFF],  # k
        [0x67, 0xFF],  # g
        [0x68, 0xFF],  # h
        [0x62, 0xFF],  # b
        [0x70, 0xFF],  # p
        [0x73, 0xFF],  # s
        [0x78, 0xFF],  # x (sh)
        [0x74, 0xFF],  # t
        [0x64, 0xFF],  # d
        [0x6C, 0xFF],  # l
        [0x6D, 0xFF],  # m
        [0x63, 0xFF],  # c
        [0x6A, 0xFF],  # j
        [0x79, 0xFF],  # y
        [0x72, 0xFF],  # r
        [0x66, 0xFF],  # f
        [0x77, 0xFF],  # w
        [0x6B, 0x68],  # k' (kh)
        [0x67, 0x68],  # g' (gh)
        [0x68, 0x68],  # h' (hh)
        [0x74, 0x73],  # ts (c)
        [0x64, 0x7A],  # dz (z)
        [0x7A, 0x68],  # zh (j)
        [0x63, 0x68],  # ch (c)
    ]

    TABLE_CONSONANTS_MAP: ClassVar[list[int]] = [
        0x1828,  # n
        0x1829,  # ng
        0x1874,  # k
        0x1864,  # g
        0x1865,  # h
        0x182A,  # b
        0x1866,  # p
        0x1830,  # s
        0x1831,  # x
        0x1868,  # t
        0x1869,  # d
        0x182F,  # l
        0x182E,  # m
        0x1834,  # c
        0x1835,  # j
        0x1836,  # y
        0x1837,  # r
        0x1876,  # f
        0x1838,  # w
        0x183A,  # k'
        0x186C,  # g'
        0x186D,  # h'
        0x186E,  # ts
        0x186F,  # dz
        0x1871,  # zh
        0x1877,  # ch (zhi)
    ]

    TABLE_TRANSCRIPTION_LETTERS: ClassVar[list[str]] = [
        "\u0160", "\u0161", "\u010C", "\u010D", "z", "\u0158", "\u0159",
        "'", "\u016A", "\u016B", "\u2010", "\u2011", "'", '"', "^", "\u030C",
    ]
    TABLE_TRANSCRIPTION_MAP: ClassVar[list[tuple[int, int]]] = [
        (0x78, 0), (0x78, 0), (0x74, 0x73), (0x74, 0x73), (0x64, 0x7A),
        (0x7A, 0x72), (0x7A, 0x72), (0x68, 0), (0x75, 0x75), (0x75, 0x75),
        (0x2D, 0), (0x2D, 0), (0, 0), (0, 0), (0, 0), (0, 0),
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
        """Get the accumulated Manchu word output."""
        result = ""
        for i in range(self._word_pos):
            if self._word[i]:
                result += chr(self._word[i])
        self.on_clear()
        return result

    def on_clear(self, reset: bool = False) -> None:
        """Clear Manchu input state."""
        super().on_clear(reset)
        self._vowel_type = VowelType.NEUTRAL
        self._is_consonant = False
        self._is_vowel = False
        self._hanging_consonant = False
        self._hanging_vowel = False
        self._word_pos = 0
        self._word = [ZERO_16] * MAX_MONGOLIAN_WORD

    def on_input(self, code: int) -> EInput:
        """
        Process character input for Manchu Latin transcription.
        Converts ASCII Latin letters to Mongolian block Unicode.
        """
        if self._word_pos >= MAX_MONGOLIAN_WORD:
            return EInput.FINISHED

        ch = code

        if self._step == StepType.NULL:
            # Special characters mapping
            special_map = {
                0x2B: 0x1807,  # + = Sibe Syllable Boundary Marker
                0x2D: 0x202F,  # - = Narrow No-Break Space
                0x2F: 0x200C,  # / = ZNWJ
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
                if self._word_pos:
                    self._word_pos += 1
                    return EInput.FINISHED
                self.ch_output = self._word[self._word_pos]
                return EInput.CHARACTER

            if self._is_vowel_check(ch) or self._is_consonant_check(ch):
                self._word_pos += 1
                self._step = StepType.INITIAL
                return EInput.IN_PROGRESS

            return EInput.INVALID

        elif self._step == StepType.INITIAL:
            # Disallow initial "ng"
            if self._previous_input == 0x6E and ch == 0x67:
                return EInput.INVALID

            self._step = StepType.MEDIAL
            # Fall through

        # MEDIAL step
        if self._step == StepType.MEDIAL:
            # Special characters in medial position
            special_map = {
                0x2B: 0x1807,  # +
                0x2D: 0x202F,  # -
                0x2F: 0x200C,  # /
                0x5F: 0x200D,  # _
                0x7E: 0x180A,  # ~
                0x27: 0x180B,  # '
                0x22: 0x180C,  # "
                0x5E: 0x180D,  # ^
            }

            if ch in special_map:
                self._word[self._word_pos] = special_map[ch]
                self._word_pos += 1
                self._hanging_vowel = False
                self._hanging_consonant = False
                return EInput.IN_PROGRESS

            # w must be followed by "a" or "e"
            prev = self._word[self._word_pos - 1] if self._word_pos > 0 else 0
            if prev == 0x1838 and ch not in (0x61, 0x65):
                return EInput.INVALID

            # y must not be followed by "i"
            if prev == 0x1836 and ch == 0x69:
                return EInput.INVALID

            # Handle special "i" after s/ts -> sy/tsy
            if ch == 0x79 and prev in (0x1830, 0x186E):  # 'y' after SA or TSA
                self._word[self._word_pos] = 0x185F
                self._is_consonant = False
                self._is_vowel = True
                self._hanging_consonant = False
                self._hanging_vowel = True
                self._vowel_type = VowelType.NEUTRAL
                self._word_pos += 1
                return EInput.IN_PROGRESS

            # Check for punctuation at word end
            final_letters = {
                0x1864,
                0x1865,
                0x1866,
                0x1869,
                0x1835,
                0x1836,
                0x1838,
                0x1876,
                0x183A,
                0x186C,
                0x186D,
                0x186E,
                0x186F,
                0x1870,
                0x1871,
                0x1877,
            }
            if prev not in final_letters and self._is_punctuation(ch):
                self._word_pos += 1
                return EInput.FINISHED

            # Handle hanging vowel
            if self._hanging_vowel:
                self._word_pos -= 1
                if self._is_vowel_check(ch, self._previous_input):
                    self._word_pos += 1
                    return EInput.IN_PROGRESS
                self._word_pos += 1

            # Handle hanging consonant
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

    def on_return(self) -> EInput:
        return EInput.FINISHED

    def do_conversion(
        self, menu_id: int, text_in: str, start: int = 0, end: int | None = None, skip_ascii: bool = False
    ) -> tuple:
        """
        Convert Latin transcription to Manchu script.

        Returns:
            Tuple of (converted_text, count).
        """
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
        """Check if character is Manchu punctuation."""
        for i, pc in enumerate(self.TABLE_PUNCTUATION):
            if pc == code:
                if self._word_pos < MAX_MONGOLIAN_WORD:
                    self._word[self._word_pos] = self.TABLE_PUNCTUATION_MAP[i]
                self._hanging_vowel = False
                self._hanging_consonant = False
                return True
        return False

    def _is_vowel_check(self, code1: int, code2: int = 0xFF) -> bool:
        """Check if character(s) form a valid Manchu vowel."""
        for i, v in enumerate(self.TABLE_VOWELS):
            if v[0] == code1 and v[1] == code2:
                if self._word_pos < MAX_MONGOLIAN_WORD:
                    self._word[self._word_pos] = self.TABLE_VOWELS_MAP[i]
                self._is_consonant = False
                self._is_vowel = True
                self._hanging_consonant = False
                self._hanging_vowel = True

                if code1 in (0x61, 0x65, 0x6F) or code2 in (0x69, 0x75):
                    self._hanging_vowel = False

                if code1 in (0x61, 0x6F) or code2 == 0x75:
                    self._vowel_type = VowelType.BACK
                elif code1 == 0x65:
                    self._vowel_type = VowelType.FRONT
                elif code1 in (0x69, 0x75) or code2 == 0x75:
                    self._vowel_type = VowelType.NEUTRAL

                return True
        return False

    def _is_consonant_check(self, code1: int, code2: int = 0xFF) -> bool:
        """Check if character(s) form a valid Manchu consonant."""
        for i, c in enumerate(self.TABLE_CONSONANTS):
            if c[0] == code1 and c[1] == code2:
                if self._word_pos < MAX_MONGOLIAN_WORD:
                    self._word[self._word_pos] = self.TABLE_CONSONANTS_MAP[i]
                self._is_consonant = True
                self._is_vowel = False
                self._hanging_vowel = False
                self._hanging_consonant = True

                # These consonant clusters don't hang
                if code2 in (0x67, 0x68, 0x72, 0x73):
                    self._hanging_consonant = False
                if code2 in (0x47, 0x48, 0x54, 0x44):
                    self._hanging_consonant = False

                return True
        return False
