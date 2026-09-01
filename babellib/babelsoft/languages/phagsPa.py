"""
LanguagePhagsPa - Python equivalent of c/Languages/LanguagePhagsPa.h/.cpp

Handles Phags-pa script input via Latin transcription.
Converts Latin letters to Phags-pa Unicode characters (U+A840-U+A87F).
"""

from .class_ import Language, EInput, FF_16, ZERO_16, MAX_MONGOLIAN_WORD


class StepType:
    NULL = 0
    INITIAL = 1
    MEDIAL = 2


class VowelType:
    NEUTRAL = 0
    BACK = 1
    FRONT = 2


class PhagsPa(Language):
    """
    Phags-pa language input method.

    Converts Latin transcription to Phags-pa Unicode characters.
    Based on the same pattern as Manchu/Mongolian with Phags-pa-specific tables.
    """

    TABLE_PUNCTUATION = [
        0x7C,  # | Vertical Line
        0x2C,  # , Comma
        0x2E,  # . Full Stop
        0x3A,  # : Colon
        0x20,  #   Space
    ]

    TABLE_PUNCTUATION_MAP = [
        0x1801,  # Ellipsis
        0x1802,  # Comma
        0x1803,  # Full Stop
        0x1804,  # Colon
        0x0020,  # Space
    ]

    TABLE_VOWELS = [
        [0x61, 0xFF],  # a
        [0x65, 0xFF],  # e
        [0x69, 0xFF],  # i
        [0x6F, 0xFF],  # o
        [0x75, 0xFF],  # u
        [0x65, 0x65],  # ee
        [0x69, 0x69],  # ii
        [0x75, 0x75],  # uu
        [0x6F, 0x6F],  # oo
    ]

    TABLE_VOWELS_MAP = [
        0xA85E,  # a
        0xA85F,  # e
        0xA860,  # i
        0xA861,  # o
        0xA862,  # u
        0xA863,  # ee
        0xA864,  # ii
        0xA865,  # uu
        0xA866,  # oo
    ]

    TABLE_CONSONANTS = [
        [0x6B, 0xFF],  # k
        [0x6B, 0x68],  # kh
        [0x67, 0xFF],  # g
        [0x6E, 0x67],  # ng
        [0x63, 0xFF],  # c
        [0x63, 0x68],  # ch
        [0x6A, 0xFF],  # j
        [0x6E, 0x79],  # ny
        [0x74, 0xFF],  # t
        [0x74, 0x68],  # th
        [0x64, 0xFF],  # d
        [0x6E, 0xFF],  # n
        [0x70, 0xFF],  # p
        [0x70, 0x68],  # ph
        [0x62, 0xFF],  # b
        [0x6D, 0xFF],  # m
        [0x74, 0x73],  # ts
        [0x74, 0x73, 0x68],  # tsh
        [0x64, 0x7A],  # dz
        [0x77, 0xFF],  # w
        [0x7A, 0xFF],  # z
        [0x7A, 0x68],  # zh
        [0x79, 0xFF],  # y
        [0x72, 0xFF],  # r
        [0x6C, 0xFF],  # l
        [0x73, 0xFF],  # s
        [0x73, 0x68],  # sh
        [0x68, 0xFF],  # h
        [0x71, 0xFF],  # q
        [0x78, 0xFF],  # x
        [0x66, 0xFF],  # f
    ]

    TABLE_CONSONANTS_MAP = [
        0xA840,  # k
        0xA841,  # kh
        0xA842,  # g
        0xA843,  # ng
        0xA844,  # c
        0xA845,  # ch
        0xA846,  # j
        0xA847,  # ny
        0xA848,  # t
        0xA849,  # th
        0xA84A,  # d
        0xA84B,  # n
        0xA84C,  # p
        0xA84D,  # ph
        0xA84E,  # b
        0xA84F,  # m
        0xA850,  # ts
        0xA851,  # tsh
        0xA852,  # dz
        0xA853,  # w
        0xA854,  # z
        0xA855,  # zh
        0xA856,  # y
        0xA857,  # r
        0xA858,  # l
        0xA859,  # s
        0xA85A,  # sh
        0xA85B,  # h
        0xA85C,  # q
        0xA85D,  # x
        0xA867,  # f
    ]

    def __init__(self):
        super().__init__(block_start=0xA840, block_end=0xA880)

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
        """Get the accumulated Phags-pa word output."""
        result = ""
        for i in range(self._word_pos):
            if self._word[i]:
                result += chr(self._word[i])
        self.on_clear()
        return result

    def on_clear(self, reset: bool = False) -> None:
        """Clear Phags-pa input state."""
        super().on_clear(reset)
        self._vowel_type = VowelType.NEUTRAL
        self._is_consonant = False
        self._is_vowel = False
        self._hanging_consonant = False
        self._hanging_vowel = False
        self._word_pos = 0
        self._word = [ZERO_16] * MAX_MONGOLIAN_WORD

    def on_input(self, code: int) -> EInput:
        """Process character input for Phags-pa Latin transcription."""
        if self._word_pos >= MAX_MONGOLIAN_WORD:
            return EInput.FINISHED

        ch = code

        if self._step == StepType.NULL:
            special_map = {
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
            if self._previous_input == 0x6E and ch == 0x67:
                return EInput.INVALID
            self._step = StepType.MEDIAL

        # MEDIAL
        if self._step == StepType.MEDIAL:
            special_map = {
                0x2D: 0x202F,
                0x2F: 0x200C,
                0x5F: 0x200D,
                0x7E: 0x180A,
                0x27: 0x180B,
                0x22: 0x180C,
                0x5E: 0x180D,
            }

            if ch in special_map:
                self._word[self._word_pos] = special_map[ch]
                self._word_pos += 1
                self._hanging_vowel = False
                self._hanging_consonant = False
                return EInput.IN_PROGRESS

            prev = self._word[self._word_pos - 1] if self._word_pos > 0 else 0
            if prev in (0x1871, 0x1877) and ch != 0x69:
                return EInput.INVALID

            if self._hanging_vowel:
                self._word_pos -= 1
                if self._is_vowel_check(ch, self._previous_input):
                    self._word_pos += 1
                    return EInput.IN_PROGRESS
                self._word_pos += 1

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
        self, menu_id: int, text_in: str, start: int = 0, end: int = None, skip_ascii: bool = False
    ) -> tuple:
        """Convert Latin transcription to Phags-pa script."""
        if end is None:
            end = len(text_in)

        self.on_clear(reset=True)
        result = ""

        for i in range(start, end):
            ch = text_in[i]
            code = ord(ch)

            if "A" <= ch <= "Z":
                code += 0x20
                ch = chr(code)

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
                return True
        return False
